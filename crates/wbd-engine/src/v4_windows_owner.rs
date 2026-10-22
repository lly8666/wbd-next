//! Windows-only developer-opt-in half of the *original* credential-checked
//! Go V4 -> Rust private owner handoff. NO Windows product network activation.
//! The caller must be the same-process original Go post-TLS callback; valid
//! cold248/WBGH bytes alone are NOT credentials or a kernel driver lease.
//! This module reuses the normal M1/M3 ProtectedScopedOwner, not fake crypto.
#![cfg(all(target_os="windows",feature="m0_v4_embedded_go"))]
use std::collections::{BTreeMap,VecDeque};
use std::sync::{Arc,Mutex,OnceLock};
use std::time::Instant;
use crate::cold_v4::{UntrustedColdV4,COLD_V4_LEN};
#[path = "v4_windows_game_owner.rs"]
mod game;
#[cfg(feature="fec2_product_record")]
#[path = "v4_windows_fec2_owner.rs"]
mod fec2;
use crate::v4_protected_handoff::{PrivateGoV4Handoff,HANDOFF_V1_LEN};
use crate::v4_owner_crypto::ProtectedScopedOwner;
use crate::memory::{Arena,FrozenRecord};
use crate::runtime::early_rx::EarlyAccepted;
use crate::runtime::{TxDispatch,RxPacket};
use wbd_types::{MonoNs,RecordPn};
use wbd_types::buffer_contract::{UniqueSealable,FrozenRecordHandle};
use wbd_codec::path_budget::{FrameBudget,FrameBudgetInput,FecReservation};
use wbd_codec::link_fec_wire::{inspect_link,LinkMode,LinkView};
use wbd_codec::record_frame::FIXED_WIRE_OVERHEAD;
use wbd_recovery::{BudgetDirection,WireDirection,ReceiptConfig,ReceiptState,ReceiptRouteScope,ReceiptOpenFacts,ReceiptPage,ScopedAuthenticatedReceipt,GlobalRepairAllocator,GlobalRepairConfig,RepairBudgetConfig};

const OK:i32=0;
const INVALID:i32=1;
const UNKNOWN:i32=2;
const BAD_STAGE:i32=3;
const FULL:i32=4;
const STOP_INCOMPLETE:i32=5;
const MAX_SESSIONS:usize=16;
// Genuine AEAD+unique-PN kind1 receives pending exact M2 route binding.
const MAX_AUTHENTICATED_KIND1:usize=32;
// Original M1 arena has 64 slots: hold at most 48 DATA shadows + one
// pending first-send while leaving room for RX and authentic control.
const MAX_M2_FROZEN:usize=48;
const M2_HARD_EXPIRY_NS:u64=2_000_000_000;
const MAX_EARLY:u32=32;
const PH_PREPARED:u32=1;
const PH_ACTIVE:u32=2;
const PH_STOPPED:u32=3;
const PH_STOPPING:u32=4;
const ABI_V1:u32=1;
const HANDLE_KIND:u64=0x574Eu64; // not a generic public engine token
// Explicitly 0: even an authenticated native Rust owner without a trusted
// Windows M4 device and OS WFP/route readback has not APPLIED a product.
const PRODUCT_APPLIED:u32=0;

// The SAME original protected TLS lane and M1 FrozenRecord handles are
// authoritative. Fresh shadow admission is only after the synchronous real
// Npcap pcap_sendpacket return; TCP cumulative ACK cannot call this owner.
struct WindowsOriginalM2 {
    shadow:ReceiptState<FrozenRecord>,
    pending:BTreeMap<RecordPn,FrozenRecord>,
    direction:BudgetDirection,
    route:ReceiptRouteScope,
}
fn m2_clock()->MonoNs{
    static START:OnceLock<Instant>=OnceLock::new();
    let elapsed=START.get_or_init(Instant::now).elapsed().as_nanos();
    MonoNs(elapsed.min(u128::from(u64::MAX)) as u64)
}
fn m2_global()->&'static Mutex<GlobalRepairAllocator>{
    static GLOBAL:OnceLock<Mutex<GlobalRepairAllocator>>=OnceLock::new();
    GLOBAL.get_or_init(||Mutex::new(GlobalRepairAllocator::new(
        GlobalRepairConfig{
            max_bytes_per_epoch:131_072,max_directions:32,
            max_grant_bytes:32_768,max_grant_lifetime_ns:50_000_000,
            max_pending:128,max_pending_bytes:131_072,
        },MonoNs(0)).expect("bounded M2 process allocator")))
}
fn m2_arm_entry(e:&mut Entry,epoch:[u8;16],luid:u64,ifindex:u32)->Result<(),i32>{
    if !v3_ready(e,epoch,luid,ifindex)||e.m2.is_some()||e.feature7 {
        return Err(BAD_STAGE)
    }
    let (lane,protected_epoch)=e.owner.normal_firstsend_identity().ok_or(BAD_STAGE)?;
    if protected_epoch!=epoch{return Err(INVALID)}
    let outbound=if e.role_server{WireDirection::ServerToClient}
        else{WireDirection::ClientToServer};
    let direction=BudgetDirection{tunnel:lane.tunnel,direction:outbound};
    let all=(RecordPn(0),RecordPn(u64::MAX));
    let route=ReceiptRouteScope::checked(lane,lane,outbound,epoch,all,all)
        .map_err(|_|INVALID)?;
    let shadow=ReceiptState::new(lane,ReceiptConfig{
        max_shadow_entries:MAX_M2_FROZEN,pto_ns:80_000_000,
        reorder_window_ns:15_000_000,
    }).map_err(|_|INVALID)?;
    let now=m2_clock();
    let mut g=m2_global().lock().map_err(|_|BAD_STAGE)?;
    g.register(direction,RepairBudgetConfig{
        outer_mtu:u64::from(e.path_mtu).saturating_add(54),
        max_repair_bytes_per_epoch:65_536,max_pending_reservations:128,
        max_pending_bytes:131_072,io_timeout_ns:100_000_000,
    },now).map_err(|_|BAD_STAGE)?;
    if g.bind_receipt_route(direction,route,now).is_err(){
        let _=g.retire_tunnel(lane.tunnel,now);
        return Err(BAD_STAGE)
    }
    e.m2=Some(WindowsOriginalM2{
        shadow,pending:BTreeMap::new(),direction,route,
    });
    Ok(())
}
fn m2_kernel_firstsend_entry(e:&mut Entry,epoch:[u8;16],luid:u64,
    ifindex:u32,pn:u64,seq:u32,wire_len:usize,sent:u32,
)->Result<u32,i32>{
    if !v3_ready(e,epoch,luid,ifindex)||sent>1{return Err(INVALID)}
    let m=e.m2.as_mut().ok_or(BAD_STAGE)?;
    let key=RecordPn(pn);
    let row=m.pending.get(&key).ok_or(INVALID)?;
    if row.metadata().pn!=key||row.metadata().seq.0 as u32!=seq
        ||row.bytes().len()!=wire_len {return Err(INVALID)}
    let frozen=m.pending.remove(&key).ok_or(INVALID)?;
    if sent==0{return Ok(0)}
    // The caller's synchronous pcap_sendpacket success is a copied
    // kernel submission, NEVER proof of remote peer delivery.
    let now=m2_clock();
    let bytes=wire_len.checked_add(54).ok_or(INVALID)? as u64;
    let mut global=m2_global().lock().map_err(|_|BAD_STAGE)?;
    global.on_fresh_accepted(m.direction,bytes,now).map_err(|_|BAD_STAGE)?;
    m.shadow.on_sent(frozen,now,MonoNs(now.0.saturating_add(M2_HARD_EXPIRY_NS)))
        .map_err(|_|FULL)?;
    Ok(m.shadow.outstanding() as u32)
}
fn m2_authenticated_kind1_entry(e:&mut Entry,reverse_pn:u64,
    receipt:&wbd_codec::Receipt,
)->Result<u32,i32>{
    let m=e.m2.as_mut().ok_or(BAD_STAGE)?;
    let now=m2_clock();
    let opened=ReceiptOpenFacts{
        verified_reverse_lane:m.route.outbound_lane(),
        verified_reverse_direction:if e.role_server {
            WireDirection::ClientToServer
        }else{WireDirection::ServerToClient},
        verified_tunnel_epoch:e.authenticated_epoch,
        control_record_pn:RecordPn(reverse_pn),
    };
    let pages=receipt.pages.iter().map(|p|ReceiptPage{
        base_pn:RecordPn(p.base_pn),bitmap:p.bitmap,
    }).collect();
    let scoped=ScopedAuthenticatedReceipt::checked_after_open(
        m.route,opened,RecordPn(receipt.largest_data_pn),
        receipt.report_seq,pages,
    ).map_err(|_|INVALID)?;
    let mut global=m2_global().lock().map_err(|_|BAD_STAGE)?;
    let releases=global.observe_scoped_receipt(
        m.direction,&mut m.shadow,&scoped,now
    ).map_err(|_|INVALID)?;
    Ok(releases.len() as u32)
}
struct Entry {
    generation:u32,
    phase:u32,
    role_server:bool,
    rx_boundary:u32,
    rx_unwrapped_high:u64, // original Go Detach boundary, serial wrap safe
    limit:u16,
    count:u32,
    bytes:u32,
    owner:ProtectedScopedOwner,
    arena:Arena,
    // Returned M1 loan containers are re-used across bounded records.
    // Packet ownership still lives in the original generation arena.
    tx_scratch:Vec<TxDispatch>,
    rx_scratch:Vec<RxPacket>,
    // Only the exact original Go TLS-derived M3 opener can append here.
    // This is a bounded M2 ingress staging lane, NOT an ACK or a repair grant.
    authenticated_kind1:VecDeque<(u64,wbd_codec::Receipt)>,
    m2:Option<WindowsOriginalM2>,
    authenticated_epoch:[u8;16],
    peer_mss:u16,
    peer_mss_advertised:bool,
    record_wire_limit:usize,
    // Real pinned Win32 interface MTU, enrolled after M4 Wintun Hold.
    path_mtu:u16,
    device:Option<ScopedWindowsWintunIdentity>,
    feature7:bool,
    game_cold:Option<UntrustedColdV4>,
    game_group:Option<u64>,
    #[cfg(feature="fec2_product_record")]
    fec2_rx:Option<crate::v4_fec2_live_rx::Fec2LiveRx>,
}
// An original-Go-verified WintunReservation.Hold on the actual native OS
// adapter is REQUIRED before this private record can be created. This C ABI
// cannot itself open or validate a Wintun and does NOT grant OS Apply.
#[derive(Clone,Copy)]
struct ScopedWindowsWintunIdentity {
    luid:u64,ifindex:u32,quiesced:bool,
}
#[derive(Default)]
struct Registry {
    generation:u32,
    entries:BTreeMap<u64,Arc<Mutex<Entry>>>,
    game_groups:BTreeMap<u64,Arc<Mutex<game::WinGameGroup>>>,
}
static REGISTRY:OnceLock<Mutex<Registry>>=OnceLock::new();
fn registry()->&'static Mutex<Registry>{
    REGISTRY.get_or_init(||Mutex::new(Registry{generation:1,entries:BTreeMap::new(),game_groups:BTreeMap::new()}))
}
fn allocate(r:&mut Registry, cold:&[u8],command:&[u8],server:bool)->Result<u64,i32>{
    if r.entries.len()>=MAX_SESSIONS{return Err(FULL)}
    let handoff=PrivateGoV4Handoff::decode(command).map_err(|_|INVALID)?;
    // Feature7 is admitted only by explicit Rust FEC2 test-channel build.
    // This is a cryptographic lane candidate, never a WFP/OS Applied grant.
    if handoff.negotiated_features!=3 &&
       !(cfg!(feature="fec2_product_record") && handoff.negotiated_features==7){
        return Err(INVALID)
    }
    let parsed=UntrustedColdV4::parse(cold).map_err(|_|INVALID)?;
    if parsed.identity().server!=server{return Err(INVALID)}
    let identity=parsed.identity();
    let generation=r.generation;
    if generation==0{return Err(FULL)}
    let next=generation.checked_add(1).ok_or(FULL)?;
    let handle=(u64::from(generation)<<32)|HANDLE_KIND;
    if r.entries.contains_key(&handle){return Err(FULL)}
    let owner=handoff.prepare_scoped_owner_for_side(
        &parsed,generation,handle,server).map_err(|_|INVALID)?;
    let arena=Arena::new(generation,64,2048,64,1_000_000).map_err(|_|FULL)?;
    let rx_limit=if server{parsed.identity().server_limit}
        else{parsed.identity().client_limit};
    let record_wire_limit=usize::from(if server{
        parsed.identity().client_limit
    }else{parsed.identity().server_limit});
    r.generation=next;
    r.entries.insert(handle,Arc::new(Mutex::new(Entry{
        generation,phase:PH_PREPARED,role_server:server,
        rx_boundary:handoff.rx_boundary,
        rx_unwrapped_high:u64::from(handoff.rx_boundary),
        limit:rx_limit,count:0,bytes:0,
        owner,arena,tx_scratch:Vec::with_capacity(8),rx_scratch:Vec::with_capacity(8),
        authenticated_kind1:VecDeque::with_capacity(MAX_AUTHENTICATED_KIND1),m2:None,
        authenticated_epoch:identity.logical_epoch,
        peer_mss:handoff.peer_mss,
        peer_mss_advertised:handoff.peer_mss_advertised,
        record_wire_limit,path_mtu:0,device:None,
        feature7:handoff.negotiated_features==7,
        game_cold:if handoff.negotiated_features==7{Some(parsed)}else{None},
        game_group:None,
        #[cfg(feature="fec2_product_record")]
        fec2_rx:None,
    })));
    Ok(handle)
}
fn stage(r:&mut Registry,h:u64,seq:u32,bytes:&[u8])->i32{
    let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    if e.phase!=PH_PREPARED{return BAD_STAGE}
    let len=bytes.len();
    let delta=seq.wrapping_sub(e.rx_boundary);
    let max=u32::from(e.limit).saturating_mul(MAX_EARLY);
    if len==0||len>usize::from(e.limit)||e.count>=MAX_EARLY
        ||e.bytes.saturating_add(len as u32)>max
        ||delta>=max||delta.saturating_add(len as u32)>max{return INVALID}
    let Ok(mut slab)=e.arena.allocate()else{return FULL};
    slab.writable()[..len].copy_from_slice(bytes);
    let absolute=u64::from(e.rx_boundary)+u64::from(delta);
    match e.owner.offer_early(slab,0..len,absolute,MonoNs(0)){
        Ok(EarlyAccepted::Staged)=>{
            e.count+=1;
            e.bytes+=len as u32;
            OK
        }
        _=>INVALID
    }
}
fn commit(r:&mut Registry,h:u64,count:u32,total:u32,tx_boundary:u32)->i32{
    let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    if e.phase!=PH_PREPARED{return BAD_STAGE}
    if count!=e.count||total!=e.bytes||count>MAX_EARLY{return INVALID}
    // Only original protected reply / Detach owns the actual SenderNext.
    if e.owner.commit_after_detach(tx_boundary).is_err(){return BAD_STAGE}
    e.phase=PH_ACTIVE;
    OK
}
fn bind_wintun(r:&mut Registry,h:u64,epoch:[u8;16],luid:u64,ifindex:u32)->i32{
    if luid==0||ifindex==0||epoch==[0;16]{return INVALID}
    let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.device.is_some(){return BAD_STAGE}
    if epoch!=e.authenticated_epoch{return INVALID}
    e.device=Some(ScopedWindowsWintunIdentity{luid,ifindex,quiesced:false});
    OK
}
// Control plane only: Go verified this CURRENT Win32 Wintun and reads OS MTU.
fn set_path_mtu(r:&mut Registry,h:u64,epoch:[u8;16],luid:u64,
    ifindex:u32,mtu:u16)->Result<u32,i32>{
    if !(576..=2048).contains(&mtu){return Err(INVALID)}
    let lane=r.entries.get(&h).ok_or(UNKNOWN)?;
    let mut e=lane.lock().map_err(|_|BAD_STAGE)?;
    if e.phase!=PH_ACTIVE||e.authenticated_epoch!=epoch||
        !e.device.is_some_and(|d|!d.quiesced&&d.luid==luid&&d.ifindex==ifindex)||
        e.path_mtu!=0 {return Err(BAD_STAGE)}
    e.path_mtu=mtu;
    // Feature7 must reserve enough room for BOTH canonical FEC2
    // 10B source and 12B+2B protected-symbol repair, never return the
    // larger Normal/off packet ceiling and fail in the live seal path.
    let business=normal_off_windows_budget(&e).ok().and_then(|b|
        if e.feature7 {
            b.record_payload_mtu.checked_sub(wbd_codec::fec_v2::RECORD_RESERVATION)
        }else{Some(b.single_business_payload_mtu)}
    );
    match business {
        Some(n) if n>=20=>Ok(n as u32),
        _=>{e.path_mtu=0;Err(INVALID)},
    }
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v4_bind_real_path_mtu(
    h:u64,epoch:*const u8,epoch_len:usize,luid:u64,ifindex:u32,
    mtu:u32,out:*mut u32,
)->i32{
    if out.is_null()||mtu>2048{return INVALID}
    let Some(exact)=v3_epoch(epoch,epoch_len)else{return INVALID};
    let Ok(mut registry)=registry().lock()else{return BAD_STAGE};
    match set_path_mtu(&mut registry,h,exact,luid,ifindex,mtu as u16){
        Ok(bound)=>{unsafe{out.write(bound)};OK},
        Err(e)=>e,
    }
}
fn quiesce_wintun(r:&mut Registry,h:u64,epoch:[u8;16],luid:u64,ifindex:u32)->i32{
    let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE{return BAD_STAGE}
    if epoch!=e.authenticated_epoch{return INVALID}
    let Some(device)=e.device.as_mut()else{return BAD_STAGE};
    if luid!=device.luid||ifindex!=device.ifindex{
        return INVALID
    }
    device.quiesced=true;
    OK
}
fn stop(r:&mut Registry,h:u64)->i32{
    let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    if e.phase==PH_STOPPED{return OK}
    if e.phase!=PH_ACTIVE&&e.phase!=PH_STOPPING{return BAD_STAGE}
    if e.game_group.is_some(){return STOP_INCOMPLETE}
    // Keep authenticated crypto owner alive if M4's current Wintun hold
    // has not ended its packet workers and completed the exact close fence.
    if e.device.is_some_and(|d|!d.quiesced){return STOP_INCOMPLETE}
    e.phase=PH_STOPPING;
    if let Some(m)=e.m2.take(){
        // Return original M1 frozen clones and retire the exact global
        // direction before original owner retirement. No late kernel sender.
        let Ok(mut global)=m2_global().lock()else{return STOP_INCOMPLETE};
        if global.retire_tunnel(m.direction.tunnel,m2_clock()).is_err(){
            return STOP_INCOMPLETE
        }
        drop(m);
    }
    let Ok(retired)=e.owner.stop()else{return STOP_INCOMPLETE};
    if !retired.ready.batch_handles_released(){return STOP_INCOMPLETE}
    #[cfg(feature="fec2_product_record")]
    if let Some(mut rx)=e.fec2_rx.take(){rx.stop()}
    // This STOP receipt covers Rust owner loans alone, never claims native
    // Windows WFP/TUN/route Stop; the product gate is permanently false.
    e.authenticated_kind1.clear();
    e.phase=PH_STOPPED;
    OK
}
fn abort(r:&mut Registry,h:u64)->i32{
    let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
    let Ok(e)=lane.lock()else{return BAD_STAGE};
    // A half-prepared owner holds no published DATA or native device lease.
    // A failed original protected TLS/transition must discard this generation
    // rather than ever making a forged Detach/Stop look successful.
    if e.phase!=PH_PREPARED{return BAD_STAGE}
    drop(e);
    r.entries.remove(&h);
    OK
}
fn release(r:&mut Registry,h:u64)->i32{
    let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
    let Ok(e)=lane.lock()else{return BAD_STAGE};
    if e.phase!=PH_STOPPED{return BAD_STAGE}
    drop(e);
    r.entries.remove(&h);
    OK
}
#[repr(C)]
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub struct WbdOriginalWindowsOwnerStateV1 {
    pub abi_version:u32,
    pub struct_size:u32,
    pub generation:u32,
    pub phase:u32,
    pub role_server:u32,
    pub product_applied:u32,
    pub kernel_loans_drained:u32,
    pub reserved:u32,
}
#[no_mangle]
pub extern "C" fn wbd_m0_win_owner_v1_query(
    out:*mut WbdOriginalWindowsOwnerStateV1,out_size:u32)->i32{
    if out.is_null()||out_size!=std::mem::size_of::<WbdOriginalWindowsOwnerStateV1>() as u32{
        return INVALID
    }
    unsafe{out.write(WbdOriginalWindowsOwnerStateV1{
        abi_version:ABI_V1,struct_size:out_size,generation:0,phase:0,
        role_server:0,product_applied:PRODUCT_APPLIED,
        kernel_loans_drained:0,reserved:0
    })}
    OK
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v1_prepare(
    cold:*const u8,cold_len:usize,command:*const u8,command_len:usize,
    server:u32,out:*mut u64,
)->i32{
    if cold.is_null()||command.is_null()||out.is_null()
        ||cold_len!=COLD_V4_LEN||command_len!=HANDOFF_V1_LEN||server>1{return INVALID}
    // SAFETY: restricted developer FFI requires caller-owned contiguous
    // buffers of exactly these checked fixed lengths, valid for this call.
    let c=unsafe{std::slice::from_raw_parts(cold,cold_len)};
    let cmd=unsafe{std::slice::from_raw_parts(command,command_len)};
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    match allocate(&mut r,c,cmd,server==1){
        Ok(h)=>{unsafe{out.write(h)};OK},Err(e)=>e
    }
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v1_stage(
    h:u64,seq:u32,data:*const u8,len:usize,
)->i32{
    if data.is_null()||len==0||len>2048{return INVALID}
    let bytes=unsafe{std::slice::from_raw_parts(data,len)};
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    stage(&mut r,h,seq,bytes)
}
#[no_mangle]
pub extern "C" fn wbd_m0_win_owner_v1_abort(h:u64)->i32{
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    abort(&mut r,h)
}
#[no_mangle]
pub extern "C" fn wbd_m0_win_owner_v1_commit(
    h:u64,staged_count:u32,staged_bytes:u32,exact_go_sender_next:u32,
)->i32{
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    commit(&mut r,h,staged_count,staged_bytes,exact_go_sender_next)
}
#[no_mangle]
pub extern "C" fn wbd_m0_win_owner_v1_state(
    h:u64,out:*mut WbdOriginalWindowsOwnerStateV1,out_size:u32,
)->i32{
    if out.is_null()||out_size!=std::mem::size_of::<WbdOriginalWindowsOwnerStateV1>() as u32{
        return INVALID
    }
    let Ok(r)=registry().lock()else{return BAD_STAGE};
    let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
    let Ok(e)=lane.lock()else{return BAD_STAGE};
    unsafe{out.write(WbdOriginalWindowsOwnerStateV1{
        abi_version:ABI_V1,struct_size:out_size,generation:e.generation,
        phase:e.phase,role_server:u32::from(e.role_server),
        product_applied:PRODUCT_APPLIED,
        kernel_loans_drained:u32::from(e.phase==PH_STOPPED),reserved:0
    })}
    OK
}
// All v2 device calls are bounded, fixed-size and private to SAME-PROCESS
// original-Go post-credential callback. A token/record is not proof of WFP,
// real OS applied network, packet TX or M4 Stop; product_applied stays zero.
#[repr(C)]
#[derive(Clone,Copy)]
pub struct WbdWindowsDeviceFenceV2{
    pub abi_version:u32,
    pub struct_size:u32,
    pub generation:u32,
    pub bound:u32,
    pub quiesced:u32,
    pub product_applied:u32,
    pub ifindex:u32,
    pub reserved:u32,
    pub luid:u64,
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v2_bind_wintun(
    h:u64,epoch:*const u8,epoch_len:usize,luid:u64,ifindex:u32,
)->i32{
    if epoch.is_null()||epoch_len!=16{return INVALID}
    let mut exact=[0u8;16];
    exact.copy_from_slice(unsafe{std::slice::from_raw_parts(epoch,16)});
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    bind_wintun(&mut r,h,exact,luid,ifindex)
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v2_quiesce_wintun(
    h:u64,epoch:*const u8,epoch_len:usize,luid:u64,ifindex:u32,
)->i32{
    if epoch.is_null()||epoch_len!=16{return INVALID}
    let mut exact=[0u8;16];
    exact.copy_from_slice(unsafe{std::slice::from_raw_parts(epoch,16)});
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    quiesce_wintun(&mut r,h,exact,luid,ifindex)
}
#[no_mangle]
pub extern "C" fn wbd_m0_win_owner_v2_device_state(
    h:u64,out:*mut WbdWindowsDeviceFenceV2,out_size:u32,
)->i32{
    if out.is_null()||out_size!=std::mem::size_of::<WbdWindowsDeviceFenceV2>() as u32{
        return INVALID
    }
    let Ok(r)=registry().lock()else{return BAD_STAGE};
    let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
    let Ok(e)=lane.lock()else{return BAD_STAGE};
    let (bound,quiesced,ifindex,luid)=match e.device{
        Some(d)=>(1,u32::from(d.quiesced),d.ifindex,d.luid),
        None=>(0,0,0,0)
    };
    unsafe{out.write(WbdWindowsDeviceFenceV2{
        abi_version:2,struct_size:out_size,generation:e.generation,
        bound,quiesced,product_applied:PRODUCT_APPLIED,ifindex,reserved:0,luid
    })}
    OK
}
#[no_mangle]
pub extern "C" fn wbd_m0_win_owner_v1_stop(h:u64)->i32{
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    stop(&mut r,h)
}
#[no_mangle]
pub extern "C" fn wbd_m0_win_owner_v1_release(h:u64)->i32{
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    release(&mut r,h)
}

// This read-only ABI binds public Windows mode claims to the actual native
// dataplane implementation. Bits: Normal=1, Fixed=2, Auto=4, Game2=8,
// Game4=16. Linux feature tests do not enable Windows modes.
#[repr(C)]
pub struct WbdWindowsV4ModeCapabilities {
    pub version:u32,
    pub size:u32,
    pub supported_modes:u32,
    pub authenticated_lanes:u32,
    pub reserved:u32,
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v4_mode_capabilities(
    out:*mut WbdWindowsV4ModeCapabilities,size:u32,
)->i32{
    if out.is_null()||size!=std::mem::size_of::<WbdWindowsV4ModeCapabilities>() as u32{
        return INVALID
    }
    unsafe{out.write(WbdWindowsV4ModeCapabilities{
        version:4,size,supported_modes:1,authenticated_lanes:1,reserved:0,
    })};
    OK
}
// V3 is deliberately a private RECORD boundary, not a Windows OS Applied
// decision. The source of the real credentials is the existing original-Go
// protected callback that issued this handle, never these C bytes alone.
// Real OS pinned Wintun MTU + original Go TLS MSS, shared FrameBudget.
// No arbitrary conservative 576/512 cap on the live packet path.
fn normal_off_windows_budget(e:&Entry)->Result<FrameBudget,i32>{
    if e.path_mtu<576{return Err(INVALID)}
    let mtu=usize::from(e.path_mtu);
    FrameBudget::derive(FrameBudgetInput{
        connection_mtu:mtu,local_packet_mtu:mtu,
        ipv4_header_len:20,tcp_header_len:20,
        peer_mss:if e.peer_mss_advertised {Some(e.peer_mss)} else {None},
        record_wire_limit:e.record_wire_limit,
        fec:FecReservation::FixedOff,game:false,
    }).map_err(|_|INVALID)
}
fn v3_ready(e:&Entry,epoch:[u8;16],luid:u64,ifindex:u32)->bool{
    e.phase==PH_ACTIVE && e.authenticated_epoch==epoch &&
    e.device.is_some_and(|d|!d.quiesced && d.luid==luid && d.ifindex==ifindex)
}
fn v3_seal_entry(e:&mut Entry,epoch:[u8;16],luid:u64,
    ifindex:u32,ipv4:&[u8],out:&mut [u8]
)->Result<(usize,u32,u64),i32>{
    if !v3_ready(e,epoch,luid,ifindex)||ipv4.len()<20||
        ipv4[0]>>4!=4 || ipv4.len()>2048 || out.len()<ipv4.len()+FIXED_WIRE_OVERHEAD{
        return Err(INVALID)
    }
    let budget=normal_off_windows_budget(e)?;
    if e.m2.as_ref().is_some_and(|m|
        m.shadow.outstanding()+m.pending.len()>=MAX_M2_FROZEN) {
        return Err(FULL)
    }
    if ipv4.len()>budget.single_business_payload_mtu ||
        ipv4[0]&15<5{return Err(INVALID)}
    let mut slab=e.arena.allocate().map_err(|_|FULL)?;
    slab.writable()[14..14+ipv4.len()].copy_from_slice(ipv4);
    let (pn,seq,used)=e.owner.seal_normal_off_one(
        slab,ipv4.len(),budget,0,MonoNs(0)).map_err(|_|BAD_STAGE)?;
    // Copy only the SAME M1 immutable FrozenRecord into the caller's bounded
    // carrier buffer while its genuine LoanBatch remains borrowed; recycle
    // generation-scoped loans on *every* path, including rejected batches.
    let tx_storage=std::mem::take(&mut e.tx_scratch);
    let batch=match e.owner.drain_tx(MonoNs(0),tx_storage){
        Ok(batch)=>batch,
        Err((_,storage))=>{e.tx_scratch=storage;return Err(BAD_STAGE)}
    };
    let accepted=(||{
        let ready=e.owner.checked_tx_ready(&batch).map_err(|_|BAD_STAGE)?;
        if ready.len()!=1 || ready[0].record.bytes().len()!=used {
            return Err(BAD_STAGE)
        }
        if let Some(m)=e.m2.as_mut(){
            let original=&ready[0].record;
            if original.metadata().pn!=RecordPn(pn) ||
                original.metadata().seq.0 as u32!=seq ||
                m.pending.insert(RecordPn(pn),original.clone()).is_some() {
                return Err(BAD_STAGE)
            }
        }
        out[..used].copy_from_slice(ready[0].record.bytes());
        Ok((used,seq,pn))
    })();
    e.tx_scratch=batch.recycle();
    accepted
}
// Unfold exact captured TCP serial bytes against this original-Go-verified
// owner only. No arbitrary wrapped seq can claim a different generation.
fn m0_tcp_unwrap(e:&Entry,seq:u32,len:usize)->Result<u64,i32>{
    let anchor=e.rx_unwrapped_high;
    let base=(anchor&!0xffff_ffff)|u64::from(seq);
    let next=base.saturating_add(1u64<<32);
    let earlier=base.checked_sub(1u64<<32);
    let distance=|x:u64|anchor.max(x)-anchor.min(x);
    let mut choice=base;
    if distance(next)<distance(choice){choice=next}
    if let Some(x)=earlier{
        if distance(x)<distance(choice){choice=x}
    }
    // Original TCP receive window is 128 KiB; M3 PN/replay remains
    // independently authoritative. This does not create an ACK receipt.
    if distance(choice)>128*1024 ||
        choice<u64::from(e.rx_boundary) ||
        choice.checked_add(len as u64).is_none(){
        return Err(INVALID)
    }
    Ok(choice)
}
fn v5_open_record_entry(e:&mut Entry,epoch:[u8;16],luid:u64,
    ifindex:u32,seq:u32,wire:&[u8],out:&mut [u8]
)->Result<(usize,u32,u64),i32>{
    if !v3_ready(e,epoch,luid,ifindex)||
        wire.len()<=FIXED_WIRE_OVERHEAD || wire.len()>2048 ||
        out.len()<wire.len(){return Err(INVALID)}
    let mut slab=e.arena.allocate().map_err(|_|FULL)?;
    slab.writable()[..wire.len()].copy_from_slice(wire);
    let unfolded=m0_tcp_unwrap(e,seq,wire.len())?;
    e.owner.offer_after_active(slab,0..wire.len(),unfolded,MonoNs(0))
        .map_err(|_|INVALID)?;
    let mut len=0usize;
    let mut valid=false;
    let mut opened_data_pn=None;
    let mut opened_kind1=None;
    let rx_storage=std::mem::take(&mut e.rx_scratch);
    let draining=e.owner.drain_windows_authenticated_kind1(
        MonoNs(0),rx_storage,|pn,link|{
            // No unauthenticated DATA, replay, HEALTH or fragmented LINK
            // can reach a Windows kernel packet sink from this v3 boundary.
            // Fragmentation will be installed with the complete M3 table.
            if matches!(inspect_link(link,wire.len(),LinkMode::FixedOff),
                Ok(LinkView::Ordinary(_))) &&
                link.len()>=20 && link[0]>>4==4 &&
                link[0]&15>=5 && link.len()<=out.len(){
                out[..link.len()].copy_from_slice(link);
                len=link.len();valid=true;opened_data_pn=Some(pn);
            }
        },|pn,receipt|{opened_kind1=Some((pn,receipt))});
    let (storage,report)=match draining{
        Ok(v)=>v,
        Err((_,scratch))=>{e.rx_scratch=scratch;return Err(BAD_STAGE)}
    };
    e.rx_scratch=storage;
    if valid && report.link_ready==1 && report.rejected==0
        && report.control_ready==0 {
        e.rx_unwrapped_high=e.rx_unwrapped_high.max(unfolded+wire.len() as u64);
        Ok((len,1,opened_data_pn.ok_or(INVALID)?))
    }
    // Only after the SAME original protected M3 AEAD and replay admission
    // can this typed kind1 enter the bounded staging lane. It does not yet
    // authorize shadow retirement or Go TCP carrier receipt.
    else if report.link_ready==0&&report.control_ready==1&&report.rejected==0 {
        let Some((pn,receipt))=opened_kind1 else{return Err(INVALID)};
        if e.authenticated_kind1.len()>=MAX_AUTHENTICATED_KIND1 {
            return Err(FULL)
        }
        if e.m2.is_some(){
            // Only real M3-authenticated kind1 can retire previously
            // Npcap-confirmed FrozenRecord shadows. No raw Go TCP ACK.
            m2_authenticated_kind1_entry(e,pn,&receipt)?;
        }else{
            e.authenticated_kind1.push_back((pn,receipt));
        }
        e.rx_unwrapped_high=e.rx_unwrapped_high.max(unfolded+wire.len() as u64);
        Ok((0,2,pn)) // kind1 is not an IPv4 packet or M2 shadow-release grant
    } else {Err(INVALID)}
}
// Existing v3 semantics remain data-only: even authenticated control may not
// be reinterpreted as application IPv4 when a legacy caller uses this ABI.
fn v3_open_entry(e:&mut Entry,epoch:[u8;16],luid:u64,
    ifindex:u32,seq:u32,wire:&[u8],out:&mut [u8]
)->Result<usize,i32>{
    let (size,kind,_pn)=v5_open_record_entry(e,epoch,luid,ifindex,seq,wire,out)?;
    if kind==1 {Ok(size)} else {Err(INVALID)}
}
// Test helper; each production FFI clones a session Arc while the
// registry mutex is briefly held, then releases it before AEAD and loans.
fn v3_seal_one(r:&Registry,h:u64,epoch:[u8;16],luid:u64,
    ifindex:u32,ipv4:&[u8],out:&mut [u8],
)->Result<(usize,u32,u64),i32>{
    let lane=r.entries.get(&h).ok_or(UNKNOWN)?;
    let mut e=lane.lock().map_err(|_|BAD_STAGE)?;
    v3_seal_entry(&mut e,epoch,luid,ifindex,ipv4,out)
}
fn v3_open_one(r:&Registry,h:u64,epoch:[u8;16],luid:u64,
    ifindex:u32,seq:u32,wire:&[u8],out:&mut [u8],
)->Result<usize,i32>{
    let lane=r.entries.get(&h).ok_or(UNKNOWN)?;
    let mut e=lane.lock().map_err(|_|BAD_STAGE)?;
    v3_open_entry(&mut e,epoch,luid,ifindex,seq,wire,out)
}
fn v5_open_record_one(r:&Registry,h:u64,epoch:[u8;16],luid:u64,
    ifindex:u32,seq:u32,wire:&[u8],out:&mut [u8]
)->Result<(usize,u32,u64),i32>{
    let lane=r.entries.get(&h).ok_or(UNKNOWN)?;
    let mut e=lane.lock().map_err(|_|BAD_STAGE)?;
    v5_open_record_entry(&mut e,epoch,luid,ifindex,seq,wire,out)
}
fn v3_epoch(ptr:*const u8,len:usize)->Option<[u8;16]>{
    if ptr.is_null()||len!=16{return None}
    let mut epoch=[0;16];
    epoch.copy_from_slice(unsafe{std::slice::from_raw_parts(ptr,16)});
    Some(epoch)
}
// A transport-layer Go driver still must prove the native Wintun OS
// ownership/route readback before using this wire on an actual socket.
// Epoch/luid/index are checked AGAINST an already bound Rust owner; passing
// them as params cannot bind or grant an unauthorized device.
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v3_seal_normal_off(
    h:u64,epoch:*const u8,epoch_len:usize,luid:u64,ifindex:u32,
    ipv4:*const u8,ipv4_len:usize,out:*mut u8,capacity:usize,
    used:*mut usize,seq:*mut u32,pn:*mut u64,
)->i32{
    if ipv4.is_null()||out.is_null()||used.is_null()||seq.is_null()||
        pn.is_null()||ipv4_len<20||ipv4_len>2048||
        capacity<ipv4_len+FIXED_WIRE_OVERHEAD||capacity>65535{return INVALID}
    let Some(exact)=v3_epoch(epoch,epoch_len)else{return INVALID};
    // No mutable-aliasing FFI: input and output must not overlap.
    let src_start=ipv4 as usize;let dst_start=out as usize;
    if src_start.checked_add(ipv4_len).is_none_or(|end|
        dst_start<end && src_start<dst_start.saturating_add(capacity)){return INVALID}
    let data=unsafe{std::slice::from_raw_parts(ipv4,ipv4_len)};
    let dst=unsafe{std::slice::from_raw_parts_mut(out,capacity)};
    let lane={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
        Arc::clone(lane)
    };
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    match v3_seal_entry(&mut e,exact,luid,ifindex,data,dst){
        Ok((n,s,p))=>{
            unsafe{used.write(n);seq.write(s);pn.write(p)};OK
        },
        Err(e)=>e,
    }
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v3_open_normal_off(
    h:u64,epoch:*const u8,epoch_len:usize,luid:u64,ifindex:u32,
    seq:u32,wire:*const u8,wire_len:usize,out:*mut u8,capacity:usize,
    used:*mut usize,
)->i32{
    if wire.is_null()||out.is_null()||used.is_null()||
        wire_len<=FIXED_WIRE_OVERHEAD||wire_len>2048||
        capacity<wire_len||capacity>65535{return INVALID}
    let Some(exact)=v3_epoch(epoch,epoch_len)else{return INVALID};
    let src_start=wire as usize;let dst_start=out as usize;
    if src_start.checked_add(wire_len).is_none_or(|end|
        dst_start<end && src_start<dst_start.saturating_add(capacity)){return INVALID}
    let data=unsafe{std::slice::from_raw_parts(wire,wire_len)};
    let dst=unsafe{std::slice::from_raw_parts_mut(out,capacity)};
    let lane={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
        Arc::clone(lane)
    };
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    match v3_open_entry(&mut e,exact,luid,ifindex,seq,data,dst){
        Ok(n)=>{unsafe{used.write(n)};OK},Err(e)=>e,
    }
}


// V6 firstsend callback is valid only for the SAME activated, OS Wintun
// epoch. Every callback matches exact original frozen PN/SEQ/len. Status 1
// means actual Npcap pcap_sendpacket returned success, not remote Applied.
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v6_arm_original_m2(
    h:u64,epoch:*const u8,epoch_len:usize,luid:u64,ifindex:u32
)->i32{
    let Some(exact)=v3_epoch(epoch,epoch_len)else{return INVALID};
    let lane={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
        Arc::clone(lane)
    };
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    match m2_arm_entry(&mut e,exact,luid,ifindex){
        Ok(())=>OK,Err(err)=>err
    }
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v6_report_npcap_firstsend(
    h:u64,epoch:*const u8,epoch_len:usize,luid:u64,ifindex:u32,
    pn:u64,seq:u32,wire_len:usize,sent:u32,outstanding:*mut u32
)->i32{
    if outstanding.is_null()||wire_len<FIXED_WIRE_OVERHEAD||wire_len>2048{
        return INVALID
    }
    let Some(exact)=v3_epoch(epoch,epoch_len)else{return INVALID};
    let lane={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
        Arc::clone(lane)
    };
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    match m2_kernel_firstsend_entry(
        &mut e,exact,luid,ifindex,pn,seq,wire_len,sent
    ){
        Ok(n)=>{unsafe{outstanding.write(n)};OK},
        Err(err)=>err
    }
}

// V5 returns TYPE only after the SAME real original M3 AEAD + unique PN
// opener. Kind 1=verified business IPv4, 2=verified canonical M2 kind1;
// kind2 is STAGED in the Rust owner and cannot authorize shadow release
// until a separately scoped M2 recovery state consumes it.
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v5_open_data_or_kind1(
    h:u64,epoch:*const u8,epoch_len:usize,luid:u64,ifindex:u32,
    seq:u32,wire:*const u8,wire_len:usize,out:*mut u8,capacity:usize,
    used:*mut usize,kind:*mut u32,pn:*mut u64,
)->i32{
    if wire.is_null()||out.is_null()||used.is_null()||kind.is_null()||
        pn.is_null()||wire_len<=FIXED_WIRE_OVERHEAD||wire_len>2048||
        capacity<wire_len||capacity>65535{return INVALID}
    let Some(exact)=v3_epoch(epoch,epoch_len)else{return INVALID};
    let src_start=wire as usize;let dst_start=out as usize;
    if src_start.checked_add(wire_len).is_none_or(|end|
        dst_start<end && src_start<dst_start.saturating_add(capacity)){return INVALID}
    let data=unsafe{std::slice::from_raw_parts(wire,wire_len)};
    let dst=unsafe{std::slice::from_raw_parts_mut(out,capacity)};
    let lane={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
        Arc::clone(lane)
    };
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    match v5_open_record_entry(&mut e,exact,luid,ifindex,seq,data,dst){
        Ok((n,k,p)) if k==1||k==2=>{
            unsafe{used.write(n);kind.write(k);pn.write(p)};OK
        },
        Ok(_)=>INVALID,
        Err(err)=>err,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn cold(server:bool)->[u8;COLD_V4_LEN]{
        let mut a=[0;COLD_V4_LEN];
        a[..4].copy_from_slice(b"WBCO");
        a[4..6].copy_from_slice(&1u16.to_be_bytes());
        a[6..8].copy_from_slice(&(COLD_V4_LEN as u16).to_be_bytes());
        a[8]=u8::from(server);a[9]=1;a[10]=1;
        a[12..28].fill(1);a[28..44].fill(2);
        a[44..60].fill(3);a[60..62].copy_from_slice(&1400u16.to_be_bytes());
        a[62..64].copy_from_slice(&1400u16.to_be_bytes());
        a[64..96].fill(4);a[96..172].fill(5);a[172..].fill(6);
        a
    }
    fn cmd()->[u8;HANDOFF_V1_LEN]{
        let mut a=[0;HANDOFF_V1_LEN];
        a[..4].copy_from_slice(b"WBGH");
        a[4..6].copy_from_slice(&1u16.to_be_bytes());
        a[6..8].copy_from_slice(&(HANDOFF_V1_LEN as u16).to_be_bytes());
        a[8..12].copy_from_slice(&[10,25,0,2]);
        a[12..16].copy_from_slice(&[10,25,0,1]);
        a[16..18].copy_from_slice(&41001u16.to_be_bytes());
        a[18..20].copy_from_slice(&443u16.to_be_bytes());
        a[20..24].copy_from_slice(&500u32.to_be_bytes());
        a[24..26].copy_from_slice(&1360u16.to_be_bytes());
        a[26]=1;a
    }
    #[test]
    fn m0_windows_owner_real_native_prepare_commit_stop_generation_scoped(){
        let mut r=Registry{generation:11,entries:BTreeMap::new(),game_groups:BTreeMap::new()};
        let h=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        assert_eq!(h>>32,11);
        assert_eq!(r.entries[&h].lock().unwrap().phase,PH_PREPARED);
        assert_eq!(commit(&mut r,h,1,9,800),INVALID);
        assert_eq!(stop(&mut r,h),BAD_STAGE);
        assert_eq!(release(&mut r,h),BAD_STAGE);
        assert_eq!(commit(&mut r,h,0,0,800),OK);
        assert_eq!(r.entries[&h].lock().unwrap().phase,PH_ACTIVE);
        assert_eq!(commit(&mut r,h,0,0,800),BAD_STAGE);
        assert_eq!(stop(&mut r,h),OK);
        assert_eq!(stop(&mut r,h),OK);
        assert_eq!(r.entries[&h].lock().unwrap().phase,PH_STOPPED);
        assert_eq!(release(&mut r,h),OK);
        assert_eq!(commit(&mut r,h,0,0,801),UNKNOWN);
        let prepared=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        assert_eq!(abort(&mut r,prepared),OK);
        assert_eq!(abort(&mut r,prepared),UNKNOWN);
        let newer=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        assert_ne!(newer,h);
        assert_eq!(stop(&mut r,h),UNKNOWN);
        assert_eq!(r.entries[&newer].lock().unwrap().phase,PH_PREPARED);
    }
    #[test]
    fn m0_windows_owner_role_fec2_bad_handoff_stale_and_prevent_public_apply(){
        let mut r=Registry{generation:3,entries:BTreeMap::new(),game_groups:BTreeMap::new()};
        assert_eq!(allocate(&mut r,&cold(true),&cmd(),false),Err(INVALID));
        assert_eq!(allocate(&mut r,&cold(false),&cmd(),true),Err(INVALID));
        let mut bad=cmd();bad[27]=1;
        assert_eq!(allocate(&mut r,&cold(false),&bad,false),Err(INVALID));
        bad=cmd();bad[4..6].copy_from_slice(&2u16.to_be_bytes());
        bad[27..29].copy_from_slice(&7u16.to_be_bytes());
        let feature7=allocate(&mut r,&cold(false),&bad,false);
        if cfg!(feature="fec2_product_record"){
            let candidate=feature7.expect("feature7 candidate scope");
            assert_eq!(abort(&mut r,candidate),OK);
        }else{assert_eq!(feature7,Err(INVALID));}
        assert_eq!(PRODUCT_APPLIED,0);
        let good=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        assert_eq!(stage(&mut r,good,500,&[]),INVALID);
        assert_eq!(stage(&mut r,good,500,&[0u8;9]),OK);
        assert_eq!(commit(&mut r,good,0,0,900),INVALID);
        assert_eq!(commit(&mut r,good,1,9,900),OK);
        assert_eq!(abort(&mut r,good),BAD_STAGE);
        assert_eq!(stage(&mut r,good,500,&[0u8;9]),BAD_STAGE);
        assert_eq!(stop(&mut r,good),OK);
        assert_eq!(release(&mut r,good),OK);
    }
    #[test]
    fn m0_windows_authenticated_generation_real_wintun_lease_stop_fence_and_stale(){
        let mut r=Registry{generation:91,entries:BTreeMap::new(),game_groups:BTreeMap::new()};
        let h=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        // cold fixture uses [28..44] as logical_epoch; [44..60] is incarnation.
        let exact=[2u8;16];
        assert_eq!(bind_wintun(&mut r,h,exact,123,77),BAD_STAGE);
        assert_eq!(commit(&mut r,h,0,0,901),OK);
        assert_eq!(bind_wintun(&mut r,h,[0;16],123,77),INVALID);
        assert_eq!(bind_wintun(&mut r,h,[9;16],123,77),INVALID);
        assert_eq!(bind_wintun(&mut r,h,exact,0,77),INVALID);
        assert_eq!(bind_wintun(&mut r,h,exact,123,77),OK);
        assert_eq!(bind_wintun(&mut r,h,exact,123,77),BAD_STAGE);
        assert_eq!(stop(&mut r,h),STOP_INCOMPLETE);
        assert_eq!(release(&mut r,h),BAD_STAGE);
        assert_eq!(quiesce_wintun(&mut r,h,[9;16],123,77),INVALID);
        assert_eq!(quiesce_wintun(&mut r,h,exact,124,77),INVALID);
        assert_eq!(quiesce_wintun(&mut r,h,exact,123,78),INVALID);
        assert_eq!(stop(&mut r,h),STOP_INCOMPLETE);
        assert_eq!(quiesce_wintun(&mut r,h,exact,123,77),OK);
        assert_eq!(stop(&mut r,h),OK);
        assert_eq!(release(&mut r,h),OK);
        assert_eq!(quiesce_wintun(&mut r,h,exact,123,77),UNKNOWN);
        let next=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        assert_ne!(h,next);
        assert_eq!(bind_wintun(&mut r,h,exact,123,77),UNKNOWN);
        assert_eq!(PRODUCT_APPLIED,0);
    }

    #[test]
    fn m0_windows_owner_v3_real_m1_m3_aead_pn_replay_and_generation(){
        let mut r=Registry{generation:101,entries:BTreeMap::new(),game_groups:BTreeMap::new()};
        let client=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        let server=allocate(&mut r,&cold(true),&cmd(),true).unwrap();
        // Synthetic unit credentials do NOT authorize Windows product;
        // positive record bytes still pass the actual M3 AEAD/PN and M1
        // immutable FrozenRecord/borrowed owner queues (not a mock cipher).
        assert_eq!(commit(&mut r,client,0,0,500),OK);
        assert_eq!(commit(&mut r,server,0,0,500),OK);
        let epoch=[2u8;16];
        assert_eq!(v3_seal_one(&mut r,client,epoch,7,11,&[0x45;40],&mut [0;256]),
            Err(INVALID)); // cannot seal without real original Wintun bind
        assert_eq!(bind_wintun(&mut r,client,epoch,7,11),OK);
        assert_eq!(bind_wintun(&mut r,server,epoch,8,12),OK);
        assert!(set_path_mtu(&mut r,client,epoch,7,11,1400).is_ok());
        assert!(set_path_mtu(&mut r,server,epoch,8,12,1400).is_ok());
        let mut packet=[0u8;40];packet[0]=0x45;packet[2..4].copy_from_slice(&40u16.to_be_bytes());
        packet[8]=64;packet[9]=17;
        let mut encrypted=[0u8;256];
        let (n,seq,pn)=v3_seal_one(&mut r,client,epoch,7,11,&packet,&mut encrypted).unwrap();
        assert_eq!(n,packet.len()+FIXED_WIRE_OVERHEAD);
        assert_eq!(pn,0);
        assert_ne!(&encrypted[..n],packet.as_slice());
        let mut output=[0u8;256];
        let used=v3_open_one(&mut r,server,epoch,8,12,seq,&encrypted[..n],&mut output).unwrap();
        assert_eq!(&output[..used],packet.as_slice());
        assert_eq!(v3_open_one(&mut r,server,epoch,8,12,seq,&encrypted[..n],&mut output),Err(INVALID));
        let mut tampered=encrypted;
        tampered[n-1]^=1;
        assert_eq!(v3_open_one(&mut r,server,epoch,8,12,seq+n as u32,&tampered[..n],&mut output),Err(INVALID));
        assert_eq!(v3_seal_one(&mut r,client,[9;16],7,11,&packet,&mut encrypted),Err(INVALID));
        assert_eq!(v3_seal_one(&mut r,client,epoch,9,11,&packet,&mut encrypted),Err(INVALID));
        // Actual same M1 FrozenRecord/M3 AEAD/PN: beyond the obsolete 512B
        // smoke limit, then a newer authenticated TCP record arriving FIRST.
        // The gap must not make the newer independent business packet wait.
        let mut large=vec![0x42u8;1100];
        large[0]=0x45;large[2..4].copy_from_slice(&1100u16.to_be_bytes());
        large[8]=64;large[9]=17;
        let mut small=[0u8;84];
        small[0]=0x45;small[2..4].copy_from_slice(&84u16.to_be_bytes());
        small[8]=64;small[9]=17;
        let mut big_cipher=[0u8;2048];
        let mut small_cipher=[0u8;2048];
        let (big_len,big_seq,big_pn)=v3_seal_one(
            &r,client,epoch,7,11,&large,&mut big_cipher).unwrap();
        let (short_len,short_seq,short_pn)=v3_seal_one(
            &r,client,epoch,7,11,&small,&mut small_cipher).unwrap();
        assert_eq!(big_len,large.len()+FIXED_WIRE_OVERHEAD);
        assert_eq!(short_seq,big_seq+big_len as u32);
        assert_eq!((big_pn,short_pn),(1,2));
        let mut plaintext=[0u8;2048];
        let first=v3_open_one(&r,server,epoch,8,12,short_seq,
            &small_cipher[..short_len],&mut plaintext).unwrap();
        assert_eq!(&plaintext[..first],small.as_slice());
        assert_eq!(v3_open_one(&r,server,epoch,8,12,short_seq,
            &small_cipher[..short_len],&mut plaintext),Err(INVALID));
        let late=v3_open_one(&r,server,epoch,8,12,big_seq,
            &big_cipher[..big_len],&mut plaintext).unwrap();
        assert_eq!(&plaintext[..late],large.as_slice());

        assert_eq!(quiesce_wintun(&mut r,client,epoch,7,11),OK);
        assert_eq!(v3_seal_one(&mut r,client,epoch,7,11,&packet,&mut encrypted),Err(INVALID));
        assert_eq!(stop(&mut r,client),OK);
        assert_eq!(release(&mut r,client),OK);
        // Registry lookup after the exact generation was released must be UNKNOWN,
        // not an admitted stale record or an already-present inactive session.
        assert_eq!(v3_seal_one(&mut r,client,epoch,7,11,&packet,&mut encrypted),Err(UNKNOWN));
        assert_eq!(quiesce_wintun(&mut r,server,epoch,8,12),OK);
        assert_eq!(stop(&mut r,server),OK);
        assert_eq!(release(&mut r,server),OK);
    }

    #[cfg(feature="fec2_product_record")]
    #[test]
    fn m0_windows_original_m2_only_real_npcap_firstsend_and_authenticated_kind1_retire(){
        use wbd_codec::{ControlTlv,Receipt,ReceiptPage};
        // Use the same production M1 frozen owner and genuine AEAD/PN
        // crypto. Test fixture cold is NOT original TLS and proves no OS
        // public connection, only exact-source recovery state transitions.
        let mut r=Registry{generation:301,entries:BTreeMap::new(),game_groups:BTreeMap::new()};
        let client=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        let server=allocate(&mut r,&cold(true),&cmd(),true).unwrap();
        let epoch=[2u8;16];
        assert_eq!(commit(&mut r,client,0,0,500),OK);
        assert_eq!(commit(&mut r,server,0,0,500),OK);
        assert_eq!(bind_wintun(&mut r,client,epoch,71,91),OK);
        assert_eq!(bind_wintun(&mut r,server,epoch,72,92),OK);
        assert!(set_path_mtu(&mut r,client,epoch,71,91,1400).is_ok());
        assert!(set_path_mtu(&mut r,server,epoch,72,92,1400).is_ok());
        {
            let mut e=r.entries[&client].lock().unwrap();
            assert_eq!(m2_arm_entry(&mut e,[9;16],71,91),Err(BAD_STAGE));
            assert!(m2_arm_entry(&mut e,epoch,71,91).is_ok());
            assert_eq!(m2_arm_entry(&mut e,epoch,71,91),Err(BAD_STAGE));
        }
        let mut ipv4=[0u8;80];ipv4[0]=0x45;
        ipv4[2..4].copy_from_slice(&80u16.to_be_bytes());
        ipv4[8]=64;ipv4[9]=17;
        let mut wire=[0u8;2048];
        let (size,seq,pn)=v3_seal_one(
            &r,client,epoch,71,91,&ipv4,&mut wire).unwrap();
        {
            let e=r.entries[&client].lock().unwrap();
            let m=e.m2.as_ref().unwrap();
            assert_eq!(m.shadow.outstanding(),0); // sealing is NOT kernel send
            assert_eq!(m.pending.len(),1); // same immutable M1 frozen handle
            assert_eq!(m.pending[&RecordPn(pn)].bytes(),&wire[..size]);
        }
        {
            let mut e=r.entries[&client].lock().unwrap();
            assert_eq!(m2_kernel_firstsend_entry(
                &mut e,epoch,71,91,pn,seq,size+1,1),Err(INVALID));
            assert_eq!(m2_kernel_firstsend_entry(
                &mut e,epoch,71,91,pn,seq,size,1),Ok(1));
            assert_eq!(m2_kernel_firstsend_entry(
                &mut e,epoch,71,91,pn,seq,size,1),Err(INVALID));
            assert_eq!(e.m2.as_ref().unwrap().shadow.outstanding(),1);
        }
        // TCP presentation ACK never enters this recovery state.
        let mut bitmap=[0u8;32];bitmap[0]=1;
        let receipt=wbd_codec::encode_control(&[ControlTlv::Receipt(Receipt{
            largest_data_pn:pn,ack_delay_us:0,report_seq:1,
            pages:vec![ReceiptPage{base_pn:0,bitmap}]
        })],512).unwrap();
        let (rseq,rwire)={
            let mut e=r.entries[&server].lock().unwrap();
            let slab=e.arena.allocate().unwrap();
            let budget=normal_off_windows_budget(&e).unwrap();
            let (_,seq,len)=e.owner.seal_original_authenticated_receipt(
                slab,&receipt,budget,0,MonoNs(0)).unwrap();
            let storage=std::mem::take(&mut e.tx_scratch);
            let batch=e.owner.drain_tx(MonoNs(0),storage)
                .unwrap_or_else(|_|panic!("same protected M1 control missing"));
            let out={
                let rows=e.owner.checked_tx_ready(&batch).unwrap();
                assert_eq!(rows.len(),1);
                assert_eq!(rows[0].record.bytes().len(),len);
                rows[0].record.bytes().to_vec()
            };
            e.tx_scratch=batch.recycle();
            (seq,out)
        };
        let mut tamper=rwire.clone();*tamper.last_mut().unwrap()^=1;
        let mut plain=[0u8;2048];
        assert_eq!(v5_open_record_one(&r,client,epoch,71,91,rseq,
            &tamper,&mut plain),Err(INVALID));
        assert_eq!(r.entries[&client].lock().unwrap()
            .m2.as_ref().unwrap().shadow.outstanding(),1);
        assert_eq!(v5_open_record_one(&r,client,epoch,71,91,rseq,
            &rwire,&mut plain),Ok((0,2,0)));
        assert_eq!(r.entries[&client].lock().unwrap()
            .m2.as_ref().unwrap().shadow.outstanding(),0);
        assert_eq!(v5_open_record_one(&r,client,epoch,71,91,rseq,
            &rwire,&mut plain),Err(INVALID)); // PN replay not receipt reapply
        {
            let e=r.entries[&client].lock().unwrap();
            assert!(e.authenticated_kind1.is_empty()); // consumed scoped M2
        }
        assert_eq!(quiesce_wintun(&mut r,client,epoch,71,91),OK);
        assert_eq!(stop(&mut r,client),OK);
        assert_eq!(release(&mut r,client),OK);
        assert_eq!(quiesce_wintun(&mut r,server,epoch,72,92),OK);
        assert_eq!(stop(&mut r,server),OK);
        assert_eq!(release(&mut r,server),OK);
    }

    #[cfg(feature="fec2_product_record")]
    #[test]
    fn m0_windows_original_m3_kind1_aead_unique_pn_stages_only_once_then_stop_retires(){
        use wbd_codec::{ControlTlv,Receipt,ReceiptPage};
        let mut r=Registry{generation:201,entries:BTreeMap::new(),game_groups:BTreeMap::new()};
        let server=allocate(&mut r,&cold(true),&cmd(),true).unwrap();
        let client=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        assert_eq!(commit(&mut r,server,0,0,500),OK);
        assert_eq!(commit(&mut r,client,0,0,500),OK);
        let epoch=[2u8;16];
        assert_eq!(bind_wintun(&mut r,server,epoch,9,13),OK);
        assert_eq!(bind_wintun(&mut r,client,epoch,8,12),OK);
        assert!(set_path_mtu(&mut r,server,epoch,9,13,1400).is_ok());
        assert!(set_path_mtu(&mut r,client,epoch,8,12,1400).is_ok());
        let mut bitmap=[0u8;32];bitmap[0]=1;
        let control= wbd_codec::encode_control(&[ControlTlv::Receipt(Receipt{
            largest_data_pn:0,ack_delay_us:0,report_seq:1,
            pages:vec![ReceiptPage{base_pn:0,bitmap}],
        })],512).unwrap();
        let (seq,pn,wire)={
            let lane=r.entries.get(&server).unwrap();
            let mut e=lane.lock().unwrap();
            let budget=normal_off_windows_budget(&e).unwrap();
            let slab=e.arena.allocate().unwrap();
            let (pn,seq,used)=e.owner.seal_original_authenticated_receipt(
                slab,&control,budget,0,MonoNs(0)).unwrap();
            let storage=std::mem::take(&mut e.tx_scratch);
            let batch=e.owner.drain_tx(MonoNs(0),storage)
                .unwrap_or_else(|_|panic!("actual M1 TX batch must drain"));
            let wire={
                let ready=e.owner.checked_tx_ready(&batch).unwrap();
                assert_eq!(ready.len(),1);
                assert_eq!(ready[0].record.bytes().len(),used);
                ready[0].record.bytes().to_vec()
            };
            e.tx_scratch=batch.recycle();
            (seq,pn,wire)
        };
        assert_eq!(pn,0);
        assert!(wire.len()>FIXED_WIRE_OVERHEAD);
        assert_ne!(&wire[..control.len()],control.as_slice());
        let mut out=[0u8;2048];
        // Legacy v3 boundary publishes business IPv4 ONLY. Exact same
        // replay opener retains the authenticated kind1 for future M2.
        assert_eq!(v5_open_record_one(&r,client,epoch,8,12,seq,&wire,&mut out),
            Ok((0,2,0)));
        {
            let e=r.entries.get(&client).unwrap().lock().unwrap();
            assert_eq!(e.authenticated_kind1.len(),1);
            let (opened_pn,receipt)=e.authenticated_kind1.front().unwrap();
            assert_eq!(*opened_pn,0);
            assert_eq!(receipt.report_seq,1);
            assert_eq!(receipt.pages.len(),1);
            assert_eq!(receipt.pages[0].bitmap[0],1);
        }
        assert_eq!(v3_open_one(&r,client,epoch,8,12,seq,&wire,&mut out),Err(INVALID));
        assert_eq!(r.entries[&client].lock().unwrap().authenticated_kind1.len(),1);
        let mut corrupt=wire.clone();*corrupt.last_mut().unwrap()^=1;
        assert_eq!(v3_open_one(&r,client,epoch,8,12,seq+wire.len() as u32,
            &corrupt,&mut out),Err(INVALID));
        assert_eq!(r.entries[&client].lock().unwrap().authenticated_kind1.len(),1);
        assert_eq!(quiesce_wintun(&mut r,client,epoch,8,12),OK);
        assert_eq!(stop(&mut r,client),OK);
        assert_eq!(r.entries[&client].lock().unwrap().authenticated_kind1.len(),0);
        assert_eq!(release(&mut r,client),OK);
        assert_eq!(quiesce_wintun(&mut r,server,epoch,9,13),OK);
        assert_eq!(stop(&mut r,server),OK);
        assert_eq!(release(&mut r,server),OK);
    }

    #[test]
    fn m0_windows_tcp_sequence_unwrap_gap_wrap_and_future_reject(){
        let mut r=Registry{generation:3,entries:BTreeMap::new(),game_groups:BTreeMap::new()};
        let h=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        let lane=r.entries.get(&h).unwrap();
        let mut e=lane.lock().unwrap();
        e.rx_unwrapped_high=(1u64<<32)-50;
        assert_eq!(m0_tcp_unwrap(&e,30,100).unwrap(),(1u64<<32)+30);
        assert_eq!(m0_tcp_unwrap(&e,u32::MAX-80,40).unwrap(),
            u64::from(u32::MAX-80));
        assert_eq!(m0_tcp_unwrap(&e,200_000,100),Err(INVALID));
        e.rx_unwrapped_high=(1u64<<32)+120;
        assert_eq!(m0_tcp_unwrap(&e,30,40).unwrap(),(1u64<<32)+30);
        assert_eq!(m0_tcp_unwrap(&e,150,40).unwrap(),(1u64<<32)+150);
    }

}
