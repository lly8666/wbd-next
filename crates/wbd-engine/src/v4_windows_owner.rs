//! Windows-only developer-opt-in half of the *original* credential-checked
//! Go V4 -> Rust private owner handoff. NO Windows product network activation.
//! The caller must be the same-process original Go post-TLS callback; valid
//! cold248/WBGH bytes alone are NOT credentials or a kernel driver lease.
//! This module reuses the normal M1/M3 ProtectedScopedOwner, not fake crypto.
#![cfg(all(target_os="windows",feature="m0_v4_embedded_go"))]
use std::collections::BTreeMap;
use std::sync::{Mutex,OnceLock};
use crate::cold_v4::{UntrustedColdV4,COLD_V4_LEN};
use crate::v4_protected_handoff::{PrivateGoV4Handoff,HANDOFF_V1_LEN};
use crate::v4_owner_crypto::ProtectedScopedOwner;
use crate::memory::Arena;
use crate::runtime::early_rx::EarlyAccepted;
use wbd_types::MonoNs;
use wbd_types::buffer_contract::UniqueSealable;

const OK:i32=0;
const INVALID:i32=1;
const UNKNOWN:i32=2;
const BAD_STAGE:i32=3;
const FULL:i32=4;
const STOP_INCOMPLETE:i32=5;
const MAX_SESSIONS:usize=16;
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

struct Entry {
    generation:u32,
    phase:u32,
    role_server:bool,
    rx_boundary:u32,
    limit:u16,
    count:u32,
    bytes:u32,
    owner:ProtectedScopedOwner,
    arena:Arena,
    authenticated_epoch:[u8;16],
    device:Option<ScopedWindowsWintunIdentity>,
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
    entries:BTreeMap<u64,Entry>,
}
static REGISTRY:OnceLock<Mutex<Registry>>=OnceLock::new();
fn registry()->&'static Mutex<Registry>{
    REGISTRY.get_or_init(||Mutex::new(Registry{generation:1,entries:BTreeMap::new()}))
}
fn allocate(r:&mut Registry, cold:&[u8],command:&[u8],server:bool)->Result<u64,i32>{
    if r.entries.len()>=MAX_SESSIONS{return Err(FULL)}
    let handoff=PrivateGoV4Handoff::decode(command).map_err(|_|INVALID)?;
    // Windows FEC2/Game transport is NOT installed. Never allow metadata
    // capability bit2 to silently switch modes or grant kernel authority.
    if handoff.negotiated_features!=3{return Err(INVALID)}
    let parsed=UntrustedColdV4::parse(cold).map_err(|_|INVALID)?;
    if parsed.identity().server!=server{return Err(INVALID)}
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
    r.generation=next;
    r.entries.insert(handle,Entry{
        generation,phase:PH_PREPARED,role_server:server,
        rx_boundary:handoff.rx_boundary,limit:rx_limit,count:0,bytes:0,
        owner,arena,
        authenticated_epoch:parsed.identity().logical_epoch,
        device:None
    });
    Ok(handle)
}
fn stage(r:&mut Registry,h:u64,seq:u32,bytes:&[u8])->i32{
    let Some(e)=r.entries.get_mut(&h)else{return UNKNOWN};
    if e.phase!=PH_PREPARED{return BAD_STAGE}
    let len=bytes.len();
    let delta=seq.wrapping_sub(e.rx_boundary);
    let max=u32::from(e.limit).saturating_mul(MAX_EARLY);
    if len==0||len>usize::from(e.limit)||e.count>=MAX_EARLY
        ||e.bytes.saturating_add(len as u32)>max
        ||delta>=max||delta.saturating_add(len as u32)>max{return INVALID}
    let Ok(mut slab)=e.arena.allocate()else{return FULL};
    slab.writable()[..len].copy_from_slice(bytes);
    match e.owner.offer_early(slab,0..len,
        u64::from(e.rx_boundary)+u64::from(delta),MonoNs(0)){
        Ok(EarlyAccepted::Staged)=>{
            e.count+=1;
            e.bytes+=len as u32;
            OK
        }
        _=>INVALID
    }
}
fn commit(r:&mut Registry,h:u64,count:u32,total:u32,tx_boundary:u32)->i32{
    let Some(e)=r.entries.get_mut(&h)else{return UNKNOWN};
    if e.phase!=PH_PREPARED{return BAD_STAGE}
    if count!=e.count||total!=e.bytes||count>MAX_EARLY{return INVALID}
    // Only original protected reply / Detach owns the actual SenderNext.
    if e.owner.commit_after_detach(tx_boundary).is_err(){return BAD_STAGE}
    e.phase=PH_ACTIVE;
    OK
}
fn bind_wintun(r:&mut Registry,h:u64,epoch:[u8;16],luid:u64,ifindex:u32)->i32{
    if luid==0||ifindex==0||epoch==[0;16]{return INVALID}
    let Some(e)=r.entries.get_mut(&h)else{return UNKNOWN};
    if e.phase!=PH_ACTIVE||e.device.is_some(){return BAD_STAGE}
    if epoch!=e.authenticated_epoch{return INVALID}
    e.device=Some(ScopedWindowsWintunIdentity{luid,ifindex,quiesced:false});
    OK
}
fn quiesce_wintun(r:&mut Registry,h:u64,epoch:[u8;16],luid:u64,ifindex:u32)->i32{
    let Some(e)=r.entries.get_mut(&h)else{return UNKNOWN};
    if e.phase!=PH_ACTIVE{return BAD_STAGE}
    let Some(device)=e.device.as_mut()else{return BAD_STAGE};
    if epoch!=e.authenticated_epoch||luid!=device.luid||ifindex!=device.ifindex{
        return INVALID
    }
    device.quiesced=true;
    OK
}
fn stop(r:&mut Registry,h:u64)->i32{
    let Some(e)=r.entries.get_mut(&h)else{return UNKNOWN};
    if e.phase==PH_STOPPED{return OK}
    if e.phase!=PH_ACTIVE&&e.phase!=PH_STOPPING{return BAD_STAGE}
    // Keep authenticated crypto owner alive if M4's current Wintun hold
    // has not ended its packet workers and completed the exact close fence.
    if e.device.is_some_and(|d|!d.quiesced){return STOP_INCOMPLETE}
    e.phase=PH_STOPPING;
    let Ok(retired)=e.owner.stop()else{return STOP_INCOMPLETE};
    if !retired.ready.batch_handles_released(){return STOP_INCOMPLETE}
    // This STOP receipt covers Rust owner loans alone, never claims native
    // Windows WFP/TUN/route Stop; the product gate is permanently false.
    e.phase=PH_STOPPED;
    OK
}
fn abort(r:&mut Registry,h:u64)->i32{
    let Some(e)=r.entries.get(&h)else{return UNKNOWN};
    // A half-prepared owner holds no published DATA or native device lease.
    // A failed original protected TLS/transition must discard this generation
    // rather than ever making a forged Detach/Stop look successful.
    if e.phase!=PH_PREPARED{return BAD_STAGE}
    r.entries.remove(&h);
    OK
}
fn release(r:&mut Registry,h:u64)->i32{
    let Some(e)=r.entries.get(&h)else{return UNKNOWN};
    if e.phase!=PH_STOPPED{return BAD_STAGE}
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
    let Some(e)=r.entries.get(&h)else{return UNKNOWN};
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
    let Some(e)=r.entries.get(&h)else{return UNKNOWN};
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
        let mut r=Registry{generation:11,entries:BTreeMap::new()};
        let h=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        assert_eq!(h>>32,11);
        assert_eq!(r.entries[&h].phase,PH_PREPARED);
        assert_eq!(commit(&mut r,h,1,9,800),INVALID);
        assert_eq!(stop(&mut r,h),BAD_STAGE);
        assert_eq!(release(&mut r,h),BAD_STAGE);
        assert_eq!(commit(&mut r,h,0,0,800),OK);
        assert_eq!(r.entries[&h].phase,PH_ACTIVE);
        assert_eq!(commit(&mut r,h,0,0,800),BAD_STAGE);
        assert_eq!(stop(&mut r,h),OK);
        assert_eq!(stop(&mut r,h),OK);
        assert_eq!(r.entries[&h].phase,PH_STOPPED);
        assert_eq!(release(&mut r,h),OK);
        assert_eq!(commit(&mut r,h,0,0,801),UNKNOWN);
        let prepared=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        assert_eq!(abort(&mut r,prepared),OK);
        assert_eq!(abort(&mut r,prepared),UNKNOWN);
        let newer=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        assert_ne!(newer,h);
        assert_eq!(stop(&mut r,h),UNKNOWN);
        assert_eq!(r.entries[&newer].phase,PH_PREPARED);
    }
    #[test]
    fn m0_windows_owner_role_fec2_bad_handoff_stale_and_prevent_public_apply(){
        let mut r=Registry{generation:3,entries:BTreeMap::new()};
        assert_eq!(allocate(&mut r,&cold(true),&cmd(),false),Err(INVALID));
        assert_eq!(allocate(&mut r,&cold(false),&cmd(),true),Err(INVALID));
        let mut bad=cmd();bad[27]=1;
        assert_eq!(allocate(&mut r,&cold(false),&bad,false),Err(INVALID));
        bad=cmd();bad[4..6].copy_from_slice(&2u16.to_be_bytes());
        bad[27..29].copy_from_slice(&7u16.to_be_bytes());
        assert_eq!(allocate(&mut r,&cold(false),&bad,false),Err(INVALID));
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
        let mut r=Registry{generation:91,entries:BTreeMap::new()};
        let h=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        let exact=[3u8;16];
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

}
