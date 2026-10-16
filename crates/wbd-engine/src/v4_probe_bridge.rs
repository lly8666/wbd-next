//! M0 TEST-ONLY *inactive* native Go/Rust bridge. No production feature or
//! authenticated C ABI is published. A caller-supplied 248-byte bundle is
//! merely a candidate, even if structurally valid; ONLY the private Go
//! credential-checked callsite is a potential future positive authority.
//! This probe owns a NEW ScopedOwner generation in Rust and exercises stage,
//! commit and stop transitions, but it does NOT install business AEAD/FEC.
#![allow(clippy::missing_safety_doc)]

use std::collections::BTreeMap;
use std::sync::{Mutex, OnceLock};

use wbd_types::{LaneKey, TunnelKey, MonoNs};
use wbd_types::buffer_contract::UniqueSealable;
use crate::memory::Arena;
use crate::runtime::early_rx::EarlyAccepted;
use crate::cold_v4::{ColdIdentity, ExpectedRustOwner, UntrustedColdV4, COLD_V4_LEN};
use crate::v4_owner_crypto::{ProtectedScopedOwner,NormalOffReceive};
use wbd_codec::record_frame::FIXED_WIRE_OVERHEAD;
use wbd_codec::path_budget::{FrameBudget,FrameBudgetInput,FecReservation};
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
use std::net::Ipv4Addr;
use wbd_types::buffer_contract::FrozenRecordHandle;
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
use std::net::{UdpSocket,SocketAddrV4};
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
use wbd_platform::linux_driver_outcome_lease::ScopedUdpOwner;
use crate::runtime::RxPacket;
use crate::runtime::generation::LoanBatch;

const OK: i32 = 0;
const INVALID: i32 = 1;
const UNKNOWN: i32 = 2;
const BAD_STAGE: i32 = 3;
const FULL: i32 = 4;
const STOP_INCOMPLETE: i32 = 5;
const LINK_PENDING: i32 = 6;
const MAX_PROBES: usize = 16;
const MAX_EARLY: u32 = 64;
const PH_PREPARED: u32 = 1;
const PH_COMMITTED: u32 = 2;
const PH_STOPPED: u32 = 3;
const PH_STOPPING: u32 = 4;

struct Probe {
    owner: ProtectedScopedOwner,
    normal:NormalOffReceive,
    arena: Arena,
    phase: u32,
    rx_boundary: u32,
    staged_count:u32,
    staged_bytes:u32,
    drained:bool,
    held_rx:Option<LoanBatch<RxPacket>>,
    cold_identity: ColdIdentity,
    peer_mss:u16,
    peer_mss_advertised:bool,
    kernel_rx:Option<ScopedUdpOwner>,
}

struct Probes {
    next_generation: u32,
    slots: BTreeMap<u64, Probe>,
}

fn registry() -> &'static Mutex<Probes> {
    static INSTANCE: OnceLock<Mutex<Probes>> = OnceLock::new();
    INSTANCE.get_or_init(|| Mutex::new(Probes {
        next_generation: 1,
        slots: BTreeMap::new(),
    }))
}

fn probe_prepare(raw: &[u8], boundary: u32, peer_mss:u16,
    peer_mss_advertised:bool,
) -> Result<u64, i32> {
    // This remains test-only. The private Go V4 authenticated callsite
    // supplies the MSS observed from the original association SYN; a caller
    // cannot enlarge it later by choosing a different Tx FrameBudget.
    if peer_mss<64 || (!peer_mss_advertised && peer_mss!=536){
        return Err(INVALID)
    }
    let data = UntrustedColdV4::parse(raw).map_err(|_| INVALID)?;
    let identity = data.identity();
    if !identity.server { return Err(INVALID); }
    let mut state = registry().lock().map_err(|_| BAD_STAGE)?;
    if state.slots.len() >= MAX_PROBES { return Err(FULL); }
    let generation = state.next_generation;
    state.next_generation = generation.checked_add(1).ok_or(FULL)?;
    let lane = LaneKey {
        tunnel: TunnelKey {slot: 1, generation},
        slot: u32::from(identity.go_lane_id),
        generation,
    };
    let expected = ExpectedRustOwner {
        lane, owner_generation:generation, logical_epoch:identity.logical_epoch,
        tunnel_id:identity.tunnel_id, go_lane_id:identity.go_lane_id,
        server:true,
    };
    // The real production-compiled composition now installs BOTH
    // ScopedOwner queues and two AEAD directions as ONE prepared owner.
    // This FFI is test-tagged only, never independent authentication.
    let handle = (u64::from(generation) << 32) | 0x5642;
    let owner=ProtectedScopedOwner::prepare_from_protected_go(
        &data,&expected,handle,boundary,peer_mss,peer_mss_advertised,
    ).map_err(|_| INVALID)?;
    // Probe supplies the maximum safe LINK budget from the authenticated
    // record limit, NOT a production path MTU/MSS. Real M4 must pass its
    // effective FrameBudget, and product qualification remains NOT_RUN.
    let link_mtu=usize::from(identity.server_limit)
        .checked_sub(FIXED_WIRE_OVERHEAD).ok_or(INVALID)?;
    let normal=NormalOffReceive::new_for_owner(&owner,link_mtu,link_mtu)
        .map_err(|_|INVALID)?;
    // Only the test harness uses this bounded arena to copy incoming FakeTCP
    // bytes; the future production adapter will supply existing owner slabs.
    let Ok(arena)=Arena::new(generation,32,2048,32,1_000_000) else {return Err(INVALID)};
    state.slots.insert(handle, Probe {
        owner,normal,arena,phase:PH_PREPARED,rx_boundary:boundary,
        staged_count:0,staged_bytes:0,drained:false,held_rx:None,cold_identity:identity,
        peer_mss,peer_mss_advertised,kernel_rx:None,
    });
    // No caller byte pointer is retained, and no production AEAD opener,
    // receiver route, positive FecOrigin or ABI feature was activated.
    Ok(handle)
}
// This stages the ACTUAL Go-owned DetachTransition packet bytes, but remains
// a test-only inert RX queue: NOT AEAD authentication and NOT a production lane.
fn probe_stage(handle:u64,seq:u32,bytes:&[u8])->i32 {
    let Ok(mut state)=registry().lock() else {return BAD_STAGE};
    let Some(p)=state.slots.get_mut(&handle) else {return UNKNOWN};
    if p.phase!=PH_PREPARED || p.drained{return BAD_STAGE;}
    let len=bytes.len();
    if len==0 || len>usize::from(p.cold_identity.server_limit) ||
       p.staged_count>=32 || p.staged_bytes.checked_add(len as u32).is_none(){
        return INVALID;
    }
    // TCP sequence wraps; use bounded signed-ahead distance only. Never
    // reinterpret a pre-boundary or opposite-half serial as fresh early RX.
    let distance=seq.wrapping_sub(p.rx_boundary);
    if distance>u32::from(p.cold_identity.server_limit).saturating_mul(MAX_EARLY) {
        return INVALID;
    }
    let Ok(mut buffer)=p.arena.allocate() else {return FULL};
    buffer.writable()[..len].copy_from_slice(bytes);
    match p.owner.offer_early(buffer,0..len,
        u64::from(p.rx_boundary)+u64::from(distance),MonoNs(0)) {
        Ok(EarlyAccepted::Staged)=>{
            p.staged_count+=1;p.staged_bytes+=len as u32;OK
        }
        Ok(EarlyAccepted::Ready)=>BAD_STAGE,
        Err(_)=>INVALID,
    }
}

// Read immutable-in-this-phase bytes WHILE the LoanBatch still owns them.
// recycle() destroys the bytes; a hash after recycle would be meaningless.
fn summarize_borrowed_rx(batch:&LoanBatch<RxPacket>)->(u32,u32,u64){
    let mut count=0u32;
    let mut len=0u32;
    let mut digest=0xcbf29ce484222325u64;
    for packet in batch.as_slice(){
        count+=1;
        let data=&packet.buffer.m0_inert_probe_bytes()[packet.wire.clone()];
        len+=data.len() as u32;
        for byte in data {
            digest=(digest^u64::from(*byte)).wrapping_mul(0x100000001b3);
        }
    }
    (count,len,digest)
}
// B04 owner-only Stop/late-loan probe: the actual Rust-owned RX buffers stay
// borrowed through Stop. This is NOT an M4 kernel or production driver lease.
fn probe_hold_rx(handle:u64)->Result<(u32,u32,u64),i32>{
    let Ok(mut state)=registry().lock() else{return Err(BAD_STAGE)};
    let Some(p)=state.slots.get_mut(&handle) else{return Err(UNKNOWN)};
    if p.phase!=PH_COMMITTED||p.drained||p.held_rx.is_some(){return Err(BAD_STAGE)}
    let batch=p.owner.drain_rx(MonoNs(0),Vec::with_capacity(32))
        .map_err(|_|BAD_STAGE)?;
    let summary=summarize_borrowed_rx(&batch);
    if summary.0!=p.staged_count||summary.1!=p.staged_bytes{return Err(BAD_STAGE)}
    p.drained=true;
    p.held_rx=Some(batch);
    Ok(summary)
}
fn probe_return_held_rx(handle:u64)->i32{
    let Ok(mut state)=registry().lock() else{return BAD_STAGE};
    let Some(p)=state.slots.get_mut(&handle) else{return UNKNOWN};
    if p.phase!=PH_STOPPING{return BAD_STAGE}
    let Some(batch)=p.held_rx.take() else{return BAD_STAGE};
    drop(batch); // original generation loan ledger is decremented ONCE
    OK
}

// An independent test-only digest of the bytes physically received by
// Rust's owned RX slabs after Detach; this does not decrypt or deliver traffic.
fn probe_drain(handle:u64)->Result<(u32,u32,u64),i32> {
    let Ok(mut state)=registry().lock() else {return Err(BAD_STAGE)};
    let Some(p)=state.slots.get_mut(&handle) else {return Err(UNKNOWN)};
    if p.phase!=PH_COMMITTED||p.drained{return Err(BAD_STAGE)}
    let batch=p.owner.drain_rx(MonoNs(0),Vec::with_capacity(32))
        .map_err(|_|BAD_STAGE)?;
    let (count,len,digest)=summarize_borrowed_rx(&batch);
    // Normal drain relinquishes the loan before Stop; the separate held-RX
    // path below proves that Stop cannot free a batch still with its driver.
    drop(batch);
    if count!=p.staged_count||len!=p.staged_bytes{return Err(BAD_STAGE)}
    p.drained=true;
    Ok((count,len,digest))
}

fn probe_commit(handle:u64,early_count:u32,early_bytes:u32,tx_boundary:u32) -> i32 {
    let Ok(mut state)=registry().lock() else {return BAD_STAGE};
    let Some(probe)=state.slots.get_mut(&handle) else {return UNKNOWN};
    if probe.phase!=PH_PREPARED {return BAD_STAGE}
    let max_wire=u32::from(probe.cold_identity.server_limit);
    if early_count>32 || early_count!=probe.staged_count ||
       early_bytes!=probe.staged_bytes ||
       early_bytes>max_wire.saturating_mul(32) ||
       (early_count==0 && early_bytes!=0) ||
       (early_count>0 && early_bytes<early_count) {
        return INVALID;
    }
    // The Go protected reply and FakeTCP Detach were completed by the
    // private Go caller. Rust now moves all already-copied early bytes from
    // its staged, bounded owner into its inert RX, atomically.
    if probe.owner.commit_after_detach(tx_boundary).is_err(){return BAD_STAGE}
    probe.phase=PH_COMMITTED;
    OK
}
fn probe_abort(handle:u64)->i32 {
    let Ok(mut state)=registry().lock() else {return BAD_STAGE};
    let Some(p)=state.slots.get(&handle) else {return UNKNOWN};
    if p.phase==PH_COMMITTED {return OK} // Go defer abort after commit is benign
    if p.phase!=PH_PREPARED {return BAD_STAGE}
    if let Some(mut p)=state.slots.remove(&handle) {
        let _=p.owner.stop();
        return OK;
    }
    UNKNOWN
}
fn probe_stop(handle:u64)->i32 {
    let Ok(mut state)=registry().lock() else {return BAD_STAGE};
    let Some(p)=state.slots.get_mut(&handle) else {return UNKNOWN};
    if p.phase==PH_STOPPED {return OK}
    if p.phase!=PH_COMMITTED && p.phase!=PH_STOPPING {return BAD_STAGE}
    if let Some(ref driver)=p.kernel_rx {driver.begin_stop()}
    let Ok(retired)=p.owner.stop() else {return BAD_STAGE};
    if !retired.ready.batch_handles_released(){
        p.phase=PH_STOPPING;
        return STOP_INCOMPLETE; // no forced free, quiesced claim or release
    }
    p.phase=PH_STOPPED;
    OK
}
fn probe_release(handle:u64)->i32 {
    let Ok(mut state)=registry().lock() else {return BAD_STAGE};
    match state.slots.get(&handle) {
        None=>UNKNOWN,
        Some(p) if p.phase!=PH_STOPPED=>BAD_STAGE,
        Some(_)=>{state.slots.remove(&handle);OK},
    }
}
// Only after real ScopedOwner admission; copies Go's encrypted test wire into
// one Rust owner slab and invokes the normal-build authenticated RX batch path.
// The observation is a digest of the *complete reconstructed application
// candidate*; neither a platform I/O nor product capability.
fn probe_open_unique(handle:u64,wire:&[u8])->Result<(u64,u8,u64),i32>{
    let Ok(mut state)=registry().lock() else {return Err(BAD_STAGE)};
    let Some(p)=state.slots.get_mut(&handle) else {return Err(UNKNOWN)};
    if p.phase!=PH_COMMITTED {return Err(BAD_STAGE)}
    if wire.is_empty()||wire.len()>usize::from(p.cold_identity.server_limit){
        return Err(INVALID)
    }
    // Ingest through EXACTLY the same normal-build ScopedOwner RX queue
    // as the eventual driver reader. This test feature only supplies the
    // Go-produced encrypted wire; it has no independent AEAD/delivery path.
    let mut buffer=p.arena.allocate().map_err(|_|FULL)?;
    buffer.writable()[..wire.len()].copy_from_slice(wire);
    p.owner.offer_after_active(buffer,0..wire.len(),
        u64::from(p.rx_boundary),MonoNs(0)).map_err(|_|INVALID)?;
    let mut observation=None;
    let (recycled,report)=p.owner.drain_normal_off(
        &mut p.normal,MonoNs(0),Vec::with_capacity(32),|pn,payload|{
            let digest=payload.iter().fold(0xcbf29ce484222325u64,
                |hash,byte|(hash^u64::from(*byte)).wrapping_mul(0x100000001b3));
            observation=Some((pn,0,digest));
        }).map_err(|_|BAD_STAGE)?;
    drop(recycled);
    if report.completed==1 && report.authenticated.link_ready==1 {
        observation.ok_or(INVALID)
    }else if report.pending==1 && report.authenticated.link_ready==1{
        Err(LINK_PENDING)
    }else{Err(INVALID)}
}

#[no_mangle]
pub unsafe extern "C" fn wbd_m0_test_probe_open_unique(
    handle:u64,wire:*mut u8,len:usize,pn:*mut u64,kind:*mut u32,digest:*mut u64,
)->i32{
    if wire.is_null()||pn.is_null()||kind.is_null()||digest.is_null()||
        len<29||len>2048{return INVALID}
    // Borrowed solely within the C call. Go does not publish decrypted bytes.
    let bytes=unsafe{std::slice::from_raw_parts(wire,len)};
    match probe_open_unique(handle,bytes){
        Ok((number,k,hash))=>{
            unsafe{pn.write(number);kind.write(u32::from(k));digest.write(hash)};
            OK
        }
        Err(e)=>e,
    }
}

// Feature-gated observation of the real normal-build S2C TX. The incoming
// Go packet is copied into ONE actual M1 UniqueBuffer, then sealed with the
// authenticated V4 S2C key and offered through the SAME owner TxOwner.
// This is never a production cold installer or M4 socket sink.
enum ProbeTxBudget {
    Caller {connection_mtu:u16,peer_mss:u16},
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    KernelLoopback {expected_ifindex:u32},
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    KernelRoute{expected_ifindex:u32,destination:Ipv4Addr},
}
fn probe_seal_tx_with_source(handle:u64,packet:&[u8],source:ProbeTxBudget,
    out:&mut [u8],
)->Result<(usize,u64,u32),i32>{
    let Ok(mut state)=registry().lock() else{return Err(BAD_STAGE)};
    let Some(p)=state.slots.get_mut(&handle) else{return Err(UNKNOWN)};
    if p.phase!=PH_COMMITTED || packet.is_empty(){return Err(BAD_STAGE)}
    // The actual normal-build ProtectedScopedOwner must enforce the bound
    // MSS. Do not let the feature-gated probe become the sole authority.
    let (budget,observed_kernel)=match source {
        ProbeTxBudget::Caller{connection_mtu,peer_mss}=>{
            let value=FrameBudget::derive(FrameBudgetInput{
                connection_mtu:usize::from(connection_mtu),
                local_packet_mtu:0,ipv4_header_len:20,tcp_header_len:20,
                peer_mss:if p.peer_mss_advertised {Some(peer_mss)} else {None},
                record_wire_limit:usize::from(p.cold_identity.client_limit),
                fec:FecReservation::FixedOff,game:false,
            }).map_err(|_|INVALID)?;
            (value,None)
        }
        #[cfg(all(target_arch="x86_64",target_env="gnu"))]
        ProbeTxBudget::KernelLoopback{expected_ifindex}=>{
            let v=p.owner.observe_linux_normal_off_budget("lo",expected_ifindex)
                .map_err(|_|INVALID)?;
            (v.frame,Some(v))
        }
        #[cfg(all(target_arch="x86_64",target_env="gnu"))]
        ProbeTxBudget::KernelRoute{expected_ifindex,destination}=>{
            let v=p.owner.observe_linux_normal_off_route_budget(
                "lo",expected_ifindex,destination
            ).map_err(|_|INVALID)?;
            (v.frame,Some(v))
        }
    };
    if packet.len()>budget.single_business_payload_mtu
        || budget.record_wire_mtu>out.len()
        || packet.len()+FIXED_WIRE_OVERHEAD>2048{return Err(INVALID)}
    let mut unique=p.arena.allocate().map_err(|_|FULL)?;
    unique.writable()[14..14+packet.len()].copy_from_slice(packet);
    let (pn,seq,used)=if let Some(ref scope)=observed_kernel {
        p.owner.seal_normal_off_with_linux_budget(
            unique,packet.len(),scope,12,MonoNs(0),
        )
    }else{
        p.owner.seal_normal_off_one(unique,packet.len(),budget,12,MonoNs(0))
    }.map_err(|_|INVALID)?;
    let batch=p.owner.drain_tx(MonoNs(0),Vec::with_capacity(2))
        .map_err(|_|BAD_STAGE)?;
    let checked=p.owner.checked_tx_ready(&batch).map_err(|_|BAD_STAGE)?;
    if checked.len()!=1 || checked[0].record.metadata().pn.0!=pn
        || checked[0].record.metadata().seq.0!=u64::from(seq)
        || checked[0].record.bytes().len()!=used {return Err(BAD_STAGE)}
    out[..used].copy_from_slice(checked[0].record.bytes());
    drop(batch); // Returned only AFTER original generation TX loan releases
    p.arena.drain_returns();
    Ok((used,pn,seq))
}

fn probe_seal_tx(handle:u64,packet:&[u8],connection_mtu:u16,peer_mss:u16,
    out:&mut [u8],
)->Result<(usize,u64,u32),i32>{
    probe_seal_tx_with_source(handle,packet,
        ProbeTxBudget::Caller{connection_mtu,peer_mss},out)
}

#[no_mangle]
pub unsafe extern "C" fn wbd_m0_test_probe_seal_normal(
    handle:u64,packet:*const u8,len:usize,connection_mtu:u16,peer_mss:u16,
    out:*mut u8,out_cap:usize,out_len:*mut u32,pn:*mut u64,seq:*mut u32,
)->i32{
    if packet.is_null()||len==0||len>2048||out.is_null()||out_len.is_null()
        ||pn.is_null()||seq.is_null()||out_cap<31||out_cap>2048 {
        return INVALID
    }
    let in_bytes=unsafe{std::slice::from_raw_parts(packet,len)};
    let out_bytes=unsafe{std::slice::from_raw_parts_mut(out,out_cap)};
    match probe_seal_tx(handle,in_bytes,connection_mtu,peer_mss,out_bytes){
        Ok((n,number,start))=>{
            unsafe{out_len.write(n as u32);pn.write(number);seq.write(start)};
            OK
        }
        Err(code)=>code,
    }
}

// C test observer: Linux kernel /sys/class/net/lo/mtu + verified ifindex
// supply the frame budget, while the ordinary Rust owner enforces original
// Go protected SYN MSS and its generation-scoped TxOwner. No actual raw I/O.
#[no_mangle]
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
pub unsafe extern "C" fn wbd_m0_test_probe_seal_linux_observed(
    handle:u64,packet:*const u8,len:usize,ifindex:u32,
    out:*mut u8,out_cap:usize,out_len:*mut u32,pn:*mut u64,seq:*mut u32,
)->i32{
    if packet.is_null()||len==0||len>2048||out.is_null()||out_len.is_null()
        ||pn.is_null()||seq.is_null()||out_cap<31||out_cap>2048 {
        return INVALID
    }
    let raw=unsafe{std::slice::from_raw_parts(packet,len)};
    let output=unsafe{std::slice::from_raw_parts_mut(out,out_cap)};
    match probe_seal_tx_with_source(handle,raw,
        ProbeTxBudget::KernelLoopback{expected_ifindex:ifindex},output){
        Ok((used,num,start))=>{
            unsafe{out_len.write(used as u32);pn.write(num);seq.write(start)};
            OK
        }
        Err(code)=>code,
    }
}

// Test-tagged only: the destination is a candidate route lookup address,
// not a trusted Go session address or a production socket/driver lease.
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_test_probe_seal_linux_route(
    handle:u64,packet:*const u8,len:usize,ifindex:u32,
    destination_be:u32,
    out:*mut u8,out_cap:usize,out_len:*mut u32,pn:*mut u64,seq:*mut u32,
)->i32{
    if packet.is_null()||len==0||len>2048||out.is_null()||out_len.is_null()
        ||pn.is_null()||seq.is_null()||out_cap<31||out_cap>2048 {
        return INVALID
    }
    let source=ProbeTxBudget::KernelRoute{
        expected_ifindex:ifindex,
        destination:Ipv4Addr::from(destination_be.to_be_bytes()),
    };
    let bytes=unsafe{std::slice::from_raw_parts(packet,len)};
    let output=unsafe{std::slice::from_raw_parts_mut(out,out_cap)};
    match probe_seal_tx_with_source(handle,bytes,source,output){
        Ok((used,number,start))=>{
            unsafe{out_len.write(used as u32);pn.write(number);seq.write(start)};
            OK
        }
        Err(e)=>e,
    }
}

/// TEST-ONLY orchestrator for a genuine M4 Linux sendmmsg kernel trip.
/// NO independent crypto or alternate TX queue is implemented here. The
/// normal-build owner seals one record into an M1 slab and submits that
/// SAME scoped frozen TX batch through normal-build M4 ScopedUdpOwner.
/// Go supplies the loopback UDP receiver's port and independently verifies
/// the ciphertext arriving through the kernel. This is NOT raw/TUN app IO.
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn probe_udp_tx(handle:u64,payload:&[u8],ifindex:u32,receive_port:u16)
    ->Result<(u64,u32,u32),i32>{
    if payload.is_empty() || payload.len()>1400 || receive_port==0{
        return Err(INVALID)
    }
    let mut state=registry().lock().map_err(|_|BAD_STAGE)?;
    let p=state.slots.get_mut(&handle).ok_or(UNKNOWN)?;
    if p.phase!=PH_COMMITTED{return Err(BAD_STAGE)}
    let route=p.owner.observe_linux_normal_off_route_budget(
        "lo",ifindex,Ipv4Addr::LOCALHOST
    ).map_err(|_|INVALID)?;
    if payload.len()>route.frame.single_business_payload_mtu{
        return Err(INVALID)
    }
    let mut slab=p.arena.allocate().map_err(|_|FULL)?;
    slab.writable()[14..14+payload.len()].copy_from_slice(payload);
    let (pn,seq,wire_len)=p.owner.seal_normal_off_with_linux_budget(
        slab,payload.len(),&route,15,MonoNs(0)
    ).map_err(|_|INVALID)?;
    // Both are genuine owned kernel sockets, not a Rust plaintext channel.
    let sender=UdpSocket::bind((Ipv4Addr::LOCALHOST,0)).map_err(|_|INVALID)?;
    sender.connect(SocketAddrV4::new(Ipv4Addr::LOCALHOST,receive_port))
        .map_err(|_|INVALID)?;
    let receiver=UdpSocket::bind((Ipv4Addr::LOCALHOST,0)).map_err(|_|INVALID)?;
    let driver=ScopedUdpOwner::new((handle>>32) as u32,sender,receiver)
        .map_err(|_|INVALID)?;
    let result=p.owner.submit_scoped_udp_tx(&driver,MonoNs(0))
        .map_err(|_|BAD_STAGE)?;
    if result.len()!=1||result.accepted_prefix()!=1
        ||result.uncertain_index().is_some()||result.error().is_some(){
        return Err(BAD_STAGE)
    }
    p.arena.drain_returns();
    Ok((pn,seq,u32::try_from(wire_len).map_err(|_|INVALID)?))
}

#[cfg(all(target_arch="x86_64",target_env="gnu"))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_test_probe_send_kernel_udp(
    handle:u64,payload:*const u8,len:usize,ifindex:u32,receive_port:u16,
    out_pn:*mut u64,out_seq:*mut u32,out_wire_len:*mut u32,
)->i32{
    if payload.is_null()||len==0||len>1400||out_pn.is_null()
        ||out_seq.is_null()||out_wire_len.is_null(){return INVALID}
    let bytes=unsafe{std::slice::from_raw_parts(payload,len)};
    match probe_udp_tx(handle,bytes,ifindex,receive_port) {
        Ok((pn,seq,wire_len))=>{
            unsafe{out_pn.write(pn);out_seq.write(seq);out_wire_len.write(wire_len)};
            OK
        }
        Err(e)=>e,
    }
}

/// Bind a REAL Linux UDP receiver once after authenticated Go Detach and
/// owner Commit. The caller sees only a local port, no OS handle or Rust
/// slab. The receiver stays with the ORIGINAL owner until Stop/release.
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn probe_bind_kernel_rx(handle:u64)->Result<u16,i32>{
    let mut state=registry().lock().map_err(|_|BAD_STAGE)?;
    let p=state.slots.get_mut(&handle).ok_or(UNKNOWN)?;
    if p.phase!=PH_COMMITTED || p.kernel_rx.is_some(){return Err(BAD_STAGE)}
    let receiver=UdpSocket::bind((Ipv4Addr::LOCALHOST,0)).map_err(|_|INVALID)?;
    let port=receiver.local_addr().map_err(|_|INVALID)?.port();
    let sender=UdpSocket::bind((Ipv4Addr::LOCALHOST,0)).map_err(|_|INVALID)?;
    sender.connect(SocketAddrV4::new(Ipv4Addr::LOCALHOST,port))
        .map_err(|_|INVALID)?;
    p.kernel_rx=Some(ScopedUdpOwner::new((handle>>32) as u32,
        sender,receiver).map_err(|_|INVALID)?);
    Ok(port)
}
/// M4 recvmmsg directly writes into existing M1 arena UniqueBuffer, then
/// the SAME ScopedOwner owns the borrowed encrypted RX batch, authenticates
/// PN/AEAD, inspects/reassembles M3 LINK and emits a complete-packet digest.
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn probe_kernel_rx_once(handle:u64)->Result<(u64,u64),i32>{
    let mut state=registry().lock().map_err(|_|BAD_STAGE)?;
    let p=state.slots.get_mut(&handle).ok_or(UNKNOWN)?;
    if p.phase!=PH_COMMITTED{return Err(BAD_STAGE)}
    let driver=p.kernel_rx.as_ref().ok_or(BAD_STAGE)?;
    let slab=p.arena.allocate().map_err(|_|FULL)?;
    p.owner.receive_scoped_udp_into_owner(driver,slab,
        u64::from(p.rx_boundary),MonoNs(0)).map_err(|_|INVALID)?;
    let mut completed=None;
    let (storage,report)=p.owner.drain_normal_off(&mut p.normal,
        MonoNs(0),Vec::with_capacity(32),|pn,payload|{
            let digest=payload.iter().fold(0xcbf29ce484222325u64,
                |hash,byte|(hash^u64::from(*byte)).wrapping_mul(0x100000001b3));
            completed=Some((pn,digest));
        }).map_err(|_|BAD_STAGE)?;
    drop(storage);
    p.arena.drain_returns();
    if report.completed==1 && report.authenticated.link_ready==1{
        completed.ok_or(INVALID)
    }else{Err(INVALID)}
}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_test_probe_bind_kernel_rx(
    handle:u64,out_port:*mut u16
)->i32{
    if out_port.is_null(){return INVALID}
    match probe_bind_kernel_rx(handle){
        Ok(port)=>{unsafe{out_port.write(port)};OK}
        Err(err)=>err,
    }
}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_test_probe_receive_kernel_rx(
    handle:u64,out_pn:*mut u64,out_digest:*mut u64
)->i32{
    if out_pn.is_null()||out_digest.is_null(){return INVALID}
    match probe_kernel_rx_once(handle){
        Ok((pn,digest))=>{
            unsafe{out_pn.write(pn);out_digest.write(digest)};OK
        }
        Err(err)=>err,
    }
}

// All these C symbols are compiled ONLY under m0_v4_probe Linux feature.
// They intentionally do not authenticate caller bytes; production links do
// not contain them and capability reporting always remains features=0.
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_test_probe_prepare(
    bytes:*const u8,len:usize,boundary:u32,peer_mss:u16,
    peer_mss_advertised:u8,out:*mut u64
)->i32 {
    if bytes.is_null()||out.is_null()||len!=COLD_V4_LEN || peer_mss_advertised>1 {return INVALID}
    // SAFETY: input is borrowed strictly for this synchronous call, C Go
    // wrapper supplies a valid length/pointer and holds the backing array.
    let data=unsafe{std::slice::from_raw_parts(bytes,len)};
    match probe_prepare(data,boundary,peer_mss,peer_mss_advertised==1) {
        Ok(handle)=>{
            // SAFETY: out was validated and the C caller owns a u64 slot.
            unsafe{out.write(handle)};
            OK
        },
        Err(e)=>e,
    }
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_test_probe_stage(
    handle:u64,seq:u32,data:*const u8,len:usize
)->i32 {
    if data.is_null()||len==0||len>2048{return INVALID}
    // SAFETY: cgo keeps one Go-owned nonempty []byte alive for this strictly
    // synchronous call; copy occurs before returning to Go.
    let bytes=unsafe{std::slice::from_raw_parts(data,len)};
    probe_stage(handle,seq,bytes)
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_test_probe_drain(
    handle:u64,count:*mut u32,bytes:*mut u32,digest:*mut u64
)->i32 {
    if count.is_null()||bytes.is_null()||digest.is_null(){return INVALID}
    match probe_drain(handle) {
        Ok((n,len,hash))=>{
            // SAFETY: caller supplied valid owned integer output slots.
            unsafe{count.write(n);bytes.write(len);digest.write(hash)};
            OK
        }
        Err(e)=>e,
    }
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_test_probe_hold_rx(
    handle:u64,count:*mut u32,bytes:*mut u32,digest:*mut u64
)->i32 {
    if count.is_null()||bytes.is_null()||digest.is_null(){return INVALID}
    match probe_hold_rx(handle){
        Ok((n,len,hash))=>{
            // SAFETY: caller owns output integer slots.
            unsafe{count.write(n);bytes.write(len);digest.write(hash)};
            OK
        },
        Err(e)=>e,
    }
}
#[no_mangle]
pub extern "C" fn wbd_m0_test_probe_return_held_rx(handle:u64)->i32{
    probe_return_held_rx(handle)
}
#[no_mangle]
pub extern "C" fn wbd_m0_test_probe_commit(handle:u64,n:u32,bytes:u32,tx_boundary:u32)->i32{
    probe_commit(handle,n,bytes,tx_boundary)
}
#[no_mangle]
pub extern "C" fn wbd_m0_test_probe_abort(handle:u64)->i32{
    probe_abort(handle)
}
#[no_mangle]
pub extern "C" fn wbd_m0_test_probe_stop(handle:u64)->i32{
    probe_stop(handle)
}
#[no_mangle]
pub extern "C" fn wbd_m0_test_probe_release(handle:u64)->i32{
    probe_release(handle)
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_test_probe_state(handle:u64,out:*mut u32)->i32 {
    if out.is_null(){return INVALID}
    let Ok(state)=registry().lock() else {return BAD_STAGE};
    let Some(p)=state.slots.get(&handle) else {return UNKNOWN};
    // SAFETY: output pointer checked and owned by the C caller.
    unsafe{out.write(p.phase)};
    OK
}

#[cfg(test)]
mod tests {
    use super::*;
    fn candidate()->[u8;COLD_V4_LEN]{
        let mut b=[0u8;COLD_V4_LEN];
        b[..4].copy_from_slice(b"WBCO");
        b[4..6].copy_from_slice(&1u16.to_be_bytes());
        b[6..8].copy_from_slice(&(COLD_V4_LEN as u16).to_be_bytes());
        b[8]=1;b[9]=1;b[10]=1;
        b[12..28].fill(1);b[28..44].fill(2);b[44..60].fill(3);
        b[60..62].copy_from_slice(&1400u16.to_be_bytes());
        b[62..64].copy_from_slice(&1400u16.to_be_bytes());
        b[64..96].fill(4);b[96..172].fill(5);b[172..].fill(6);
        b
    }
    #[test]
    fn r0_m0_native_probe_local_fresh_generation_and_bounded_phases(){
        let a=candidate();
        let first=probe_prepare(&a,0,1360,true).unwrap();
        // The actual RX/TX ScopedOwner+AEAD object must never expose its
        // RX queue or plaintext before BOTH directions commit.
        assert_eq!(probe_drain(first).err(),Some(BAD_STAGE));
        assert_eq!(probe_prepare(&a,0,63,true).err(),Some(INVALID));
        assert_eq!(probe_prepare(&a,0,1360,false).err(),Some(INVALID));
        // Same internal owner TX cannot seal through uncommitted probe even
        // with a format-valid candidate and explicit synthetic path budget.
        assert_eq!(probe_seal_tx(first,b"pre-commit",1200,1360,&mut [0u8;2048]).err(),
            Some(BAD_STAGE));
        let mut precommit_record=vec![0u8;31];
        assert_eq!(probe_open_unique(first,&mut precommit_record).err(),Some(BAD_STAGE));
        // A self-consistent cold grammar with an impossible wire limit
        // cannot half-install RX when TX construction fails, nor vice versa.
        let mut too_small_rx=a;
        too_small_rx[62..64].copy_from_slice(&1u16.to_be_bytes());
        assert_eq!(probe_prepare(&too_small_rx,0,1360,true).err(),Some(INVALID));
        let mut too_small_tx=a;
        too_small_tx[60..62].copy_from_slice(&1u16.to_be_bytes());
        assert_eq!(probe_prepare(&too_small_tx,0,1360,true).err(),Some(INVALID));
        assert_eq!(probe_drain(first).err(),Some(BAD_STAGE));
        assert_eq!(probe_commit(first,65,65,777),INVALID);
        assert_eq!(probe_commit(first,1,1401*64,777),INVALID);
        assert_eq!(probe_stop(first),BAD_STAGE);
        assert_eq!(probe_commit(first,0,0,777),OK);
        // Directly exercise the NORMAL-BUILD owner guard, not a Go-only
        // argument check: a later path observer cannot widen the SYN cap.
        assert_eq!(probe_seal_tx(first,b"forged-mss",1200,2000,&mut [0u8;2048]).err(),
            Some(INVALID));
        assert_eq!(probe_seal_tx_with_source(first,b"wrong-index",
            ProbeTxBudget::KernelLoopback{expected_ifindex:0},
            &mut [0u8;2048]).err(),Some(INVALID));
        assert_eq!(probe_commit(first,0,0,777),BAD_STAGE);
        assert_eq!(probe_abort(first),OK);
        assert_eq!(probe_stop(first),OK);
        assert_eq!(probe_release(first),OK);
        let second=probe_prepare(&a,100,1360,true).unwrap();
        assert_ne!(first,second);
        assert_eq!(probe_stage(second,99,&[1]),INVALID);
        assert_eq!(probe_stage(second,100,&[11,22,33]),OK);
        assert_eq!(probe_stage(second,103,&[44,55]),OK);
        assert_eq!(probe_commit(second,1,5,777),INVALID); // metadata can't lie
        assert_eq!(probe_commit(second,2,5,777),OK);
        let (n,bytes,digest)=probe_drain(second).unwrap();
        let expected=[11u8,22,33,44,55].iter().fold(0xcbf29ce484222325u64,
            |v,b|(v^u64::from(*b)).wrapping_mul(0x100000001b3));
        assert_eq!((n,bytes,digest),(2,5,expected));
        assert_eq!(probe_drain(second).err(),Some(BAD_STAGE));
        assert_eq!(probe_stop(second),OK);
        assert_eq!(probe_release(second),OK);
        let third=probe_prepare(&a,100,1360,true).unwrap();
        assert_ne!(third,second);
        assert_eq!(probe_abort(third),OK);
        assert_eq!(probe_commit(second,0,0,777),UNKNOWN);
        let mut corrupt=a;corrupt[0]=0;
        assert_eq!(probe_prepare(&corrupt,0,1360,true).err(),Some(INVALID));
        let mut forged_client=a;forged_client[8]=0;
        assert_eq!(probe_prepare(&forged_client,0,1360,true).err(),Some(INVALID));
        // A real Rust-owned early slab remains borrowed across Stop. Old
        // quiescence must be INCOMPLETE while a new generation can progress.
        let fourth=probe_prepare(&a,200,1360,true).unwrap();
        assert_eq!(probe_stage(fourth,200,&[5,6]),OK);
        assert_eq!(probe_commit(fourth,1,2,777),OK);
        assert_eq!(probe_hold_rx(fourth).unwrap().0,1);
        assert_eq!(probe_stop(fourth),STOP_INCOMPLETE);
        assert_eq!(probe_release(fourth),BAD_STAGE);
        let fifth=probe_prepare(&a,300,1360,true).unwrap();
        assert_ne!(fourth,fifth);
        assert_eq!(probe_commit(fifth,0,0,777),OK);
        assert_eq!(probe_stop(fifth),OK);
        assert_eq!(probe_release(fifth),OK);
        assert_eq!(probe_drain(fourth).err(),Some(BAD_STAGE));
        assert_eq!(probe_return_held_rx(fourth),OK);
        assert_eq!(probe_return_held_rx(fourth),BAD_STAGE);
        assert_eq!(probe_stop(fourth),OK);
        assert_eq!(probe_release(fourth),OK);
    }
}
