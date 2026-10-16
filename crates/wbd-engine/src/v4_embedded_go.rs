//! Opt-in, non-_test in-process Go→Rust V4 control adapter.
//! This uses the ordinary ProtectedScopedOwner (real M1/M3 AEAD/PN).
//! It is NOT a standalone credential validator: only package-private Go
//! code after verified TLS credentials may call the feature-gated adapter.
//! Never distribute the feature-enabled shared library as a public installer.
//! Default production ABI features stay zero; M4 driver-held stop NOT_RUN.
#![allow(clippy::missing_safety_doc)]
use std::collections::BTreeMap;
use std::sync::{Mutex,OnceLock};
use wbd_types::MonoNs;
use wbd_types::buffer_contract::UniqueSealable;
use crate::memory::Arena;
use crate::cold_v4::{UntrustedColdV4,COLD_V4_LEN};
use crate::v4_protected_handoff::{PrivateGoV4Handoff,HANDOFF_V1_LEN};
use crate::v4_owner_crypto::{ProtectedScopedOwner,NormalOffReceive};
use wbd_codec::record_frame::FIXED_WIRE_OVERHEAD;
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
use wbd_platform::linux_raw_carrier::ScopedRawIpv4Rx;
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
use wbd_platform::linux_tun_sink::ScopedTunSink;
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
use wbd_platform::ipv4_tcp::{Ipv4Tuple,PacketPersona};
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
use std::os::fd::BorrowedFd;
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
use std::time::Instant;
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
use wbd_platform::r1::StopResult;
use crate::runtime::early_rx::EarlyAccepted;
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
struct Entry{
    owner:ProtectedScopedOwner,normal:NormalOffReceive,
    arena:Arena,phase:u32,
    rx_boundary:u32,wire_limit:u16,staged_count:u32,staged_bytes:u32,
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    flow:crate::v4_protected_handoff::GoFlow,
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    raw_rx:Option<ScopedRawIpv4Rx>,
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    tun_sink:Option<ScopedTunSink>,
}
struct Registry{generation:u32,entries:BTreeMap<u64,Entry>}
fn registry()->&'static Mutex<Registry>{
    static R:OnceLock<Mutex<Registry>>=OnceLock::new();
    R.get_or_init(||Mutex::new(Registry{generation:1,entries:BTreeMap::new()}))
}
fn prepare(cold:&[u8],command:&[u8])->Result<u64,i32>{
    let handoff=PrivateGoV4Handoff::decode(command).map_err(|_|INVALID)?;
    let data=UntrustedColdV4::parse(cold).map_err(|_|INVALID)?;
    if !data.identity().server{return Err(INVALID)}
    let mut r=registry().lock().map_err(|_|BAD_STAGE)?;
    if r.entries.len()>=MAX_SESSIONS{return Err(FULL)}
    let generation=r.generation;
    r.generation=generation.checked_add(1).ok_or(FULL)?;
    let handle=(u64::from(generation)<<32)|0x5742;
    let owner=handoff.prepare_scoped_owner(&data,generation,handle)
        .map_err(|_|INVALID)?;
    let link_mtu=usize::from(data.identity().server_limit)
        .checked_sub(FIXED_WIRE_OVERHEAD).ok_or(INVALID)?;
    let normal=NormalOffReceive::new_for_owner(&owner,link_mtu,link_mtu)
        .map_err(|_|INVALID)?;
    let arena=Arena::new(generation,32,2048,32,1_000_000)
        .map_err(|_|FULL)?;
    r.entries.insert(handle,Entry{
        owner,normal,arena,phase:PH_PREPARED,rx_boundary:handoff.rx_boundary,
        wire_limit:data.identity().server_limit,staged_count:0,staged_bytes:0,
        #[cfg(all(target_arch="x86_64",target_env="gnu"))]
        flow:handoff.flow,
        #[cfg(all(target_arch="x86_64",target_env="gnu"))]
        raw_rx:None,
        #[cfg(all(target_arch="x86_64",target_env="gnu"))]
        tun_sink:None,
    });
    Ok(handle)
}
fn stage(handle:u64,seq:u32,payload:&[u8])->i32{
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    let Some(e)=r.entries.get_mut(&handle)else{return UNKNOWN};
    if e.phase!=PH_PREPARED{return BAD_STAGE}
    let len=payload.len();
    let max=u32::from(e.wire_limit)*64;
    let delta=seq.wrapping_sub(e.rx_boundary);
    if len==0||len>usize::from(e.wire_limit)||e.staged_count>=MAX_EARLY
       ||e.staged_bytes.saturating_add(len as u32)>u32::from(e.wire_limit)*MAX_EARLY
       ||delta>=max||delta.saturating_add(len as u32)>max{return INVALID}
    let Ok(mut slab)=e.arena.allocate()else{return FULL};
    slab.writable()[..len].copy_from_slice(payload);
    match e.owner.offer_early(slab,0..len,u64::from(e.rx_boundary)+u64::from(delta),MonoNs(0)){
        Ok(EarlyAccepted::Staged)=>{e.staged_count+=1;e.staged_bytes+=len as u32;OK}
        _=>INVALID
    }
}
fn commit(handle:u64,count:u32,bytes:u32,tx_boundary:u32)->i32{
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    let Some(e)=r.entries.get_mut(&handle)else{return UNKNOWN};
    if e.phase!=PH_PREPARED{return BAD_STAGE}
    if count!=e.staged_count||bytes!=e.staged_bytes||count>MAX_EARLY
       ||bytes>u32::from(e.wire_limit)*MAX_EARLY{return INVALID}
    // Only Go's private callback after protected reply and successful
    // DetachTransition knows the exact post-reply SenderNext boundary.
    if e.owner.commit_after_detach(tx_boundary).is_err(){return BAD_STAGE}
    e.phase=PH_ACTIVE;
    OK
}
fn abort(handle:u64)->i32{
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    let Some(e)=r.entries.get(&handle)else{return UNKNOWN};
    if e.phase==PH_ACTIVE{return OK} // Go defer after commit
    if e.phase!=PH_PREPARED{return BAD_STAGE}
    let Some(mut e)=r.entries.remove(&handle)else{return UNKNOWN};
    let _=e.owner.stop();OK
}
fn stop(handle:u64)->i32{
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    let Some(e)=r.entries.get_mut(&handle)else{return UNKNOWN};
    if e.phase==PH_STOPPED{return OK}
    if e.phase!=PH_ACTIVE&&e.phase!=PH_STOPPING{return BAD_STAGE}
    // Stop the REAL M4 raw driver and TUN sink before quiescing original
    // M1 owner. Both were opened on the same verified generation, never
    // inferred from cold248. A live in-flight kernel borrow must stay held.
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    {
        if let Some(ref raw)=e.raw_rx {raw.begin_stop()}
        if let Some(ref tun)=e.tun_sink {tun.begin_stop()}
    }
    let Ok(retired)=e.owner.stop()else{return BAD_STAGE};
    let mut drained=retired.ready.batch_handles_released();
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    {
        if let Some(ref raw)=e.raw_rx{
            drained &= raw.stop_until(Instant::now())==StopResult::Drained;
        }
        if let Some(ref tun)=e.tun_sink{
            drained &= tun.stop_until(Instant::now())==StopResult::Drained;
        }
    }
    if !drained{
        e.phase=PH_STOPPING;return STOP_INCOMPLETE
    }
    e.phase=PH_STOPPED;OK
}
fn release(handle:u64)->i32{
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    let Some(e)=r.entries.get(&handle)else{return UNKNOWN};
    if e.phase!=PH_STOPPED{return BAD_STAGE}
    r.entries.remove(&handle);OK
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_prepare(
    cold:*const u8,cold_len:usize,cmd:*const u8,cmd_len:usize,out:*mut u64
)->i32{
    if cold.is_null()||cmd.is_null()||out.is_null()
        ||cold_len!=COLD_V4_LEN||cmd_len!=HANDOFF_V1_LEN{return INVALID}
    let cold=unsafe{std::slice::from_raw_parts(cold,cold_len)};
    let cmd=unsafe{std::slice::from_raw_parts(cmd,cmd_len)};
    match prepare(cold,cmd){Ok(h)=>{unsafe{out.write(h)};OK},Err(e)=>e}
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_stage(
    h:u64,seq:u32,data:*const u8,len:usize
)->i32{
    if data.is_null()||len==0||len>2048{return INVALID}
    let b=unsafe{std::slice::from_raw_parts(data,len)};
    stage(h,seq,b)
}
#[no_mangle]
pub extern "C" fn wbd_m0_embedded_go_commit(h:u64,n:u32,bytes:u32,tx:u32)->i32{
    commit(h,n,bytes,tx)
}
#[no_mangle]
pub extern "C" fn wbd_m0_embedded_go_abort(h:u64)->i32{abort(h)}
#[no_mangle]
pub extern "C" fn wbd_m0_embedded_go_stop(h:u64)->i32{stop(h)}
#[no_mangle]
pub extern "C" fn wbd_m0_embedded_go_release(h:u64)->i32{release(h)}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_state(h:u64,out:*mut u32)->i32{
    if out.is_null(){return INVALID}
    let Ok(r)=registry().lock()else{return BAD_STAGE};
    let Some(e)=r.entries.get(&h)else{return UNKNOWN};
    unsafe{out.write(e.phase)};OK
}

// The same non-_test Go-verified owner now owns BOTH actual M4 device
// handles. No shadow/test engine, no alternate AEAD/PN or delivery route.
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn attach_raw(handle:u64,ifindex:u32)->i32{
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    let Some(e)=r.entries.get_mut(&handle)else{return UNKNOWN};
    if e.phase!=PH_ACTIVE||e.raw_rx.is_some(){return BAD_STAGE}
    let Ok(driver)=ScopedRawIpv4Rx::open("lo",ifindex,(handle>>32) as u32)
    else{return INVALID};
    e.raw_rx=Some(driver);OK
}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn attach_tun(handle:u64,fd:i32,name:&str)->i32{
    if fd<3{return INVALID}
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    let Some(e)=r.entries.get_mut(&handle)else{return UNKNOWN};
    if e.phase!=PH_ACTIVE||e.tun_sink.is_some(){return BAD_STAGE}
    // Borrow only for dup(): Rust owns its duplicate, Go owns original FD.
    let Ok(dup)=unsafe{BorrowedFd::borrow_raw(fd)}.try_clone_to_owned()
    else{return INVALID};
    let Ok(tun)=ScopedTunSink::from_owned_fd(dup,(handle>>32) as u32,name)
    else{return INVALID};
    e.tun_sink=Some(tun);OK
}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn raw_to_tun(handle:u64)->Result<(u32,u32),i32>{
    let mut r=registry().lock().map_err(|_|BAD_STAGE)?;
    let e=r.entries.get_mut(&handle).ok_or(UNKNOWN)?;
    if e.phase!=PH_ACTIVE{return Err(BAD_STAGE)}
    let raw=e.raw_rx.as_ref().ok_or(BAD_STAGE)?;
    let tun=e.tun_sink.as_ref().ok_or(BAD_STAGE)?;
    let f=e.flow;
    let tuple=Ipv4Tuple{
        src_ip:&f.client_ip,dst_ip:&f.server_ip,
        src_port:f.client_port,dst_port:f.server_port,
    };
    let slab=e.arena.allocate().map_err(|_|FULL)?;
    e.owner.receive_scoped_raw_into_owner(
        raw,slab,tuple,PacketPersona::Legacy,
        u64::from(e.rx_boundary),MonoNs(0),
    ).map_err(|_|INVALID)?;
    let (returned,report,delivered,failed)=e.owner.drain_normal_off_to_tun(
        &mut e.normal,tun,MonoNs(0),Vec::with_capacity(32),
    ).map_err(|_|BAD_STAGE)?;
    drop(returned);
    e.arena.drain_returns();
    if report.completed!=1||report.authenticated.link_ready!=1||
       delivered!=1||failed!=0{return Err(INVALID)}
    Ok((delivered,failed))
}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
#[no_mangle]
pub extern "C" fn wbd_m0_embedded_go_attach_raw_rx(h:u64,ifindex:u32)->i32{
    attach_raw(h,ifindex)
}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_attach_tun(
    h:u64,fd:i32,name:*const u8,len:usize
)->i32{
    if name.is_null()||len==0||len>15{return INVALID}
    let raw=unsafe{std::slice::from_raw_parts(name,len)};
    let Ok(name)=std::str::from_utf8(raw)else{return INVALID};
    attach_tun(h,fd,name)
}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_raw_to_tun(
    h:u64,out_ok:*mut u32,out_failed:*mut u32
)->i32{
    if out_ok.is_null()||out_failed.is_null(){return INVALID}
    match raw_to_tun(h){
        Ok((ok,failed))=>{unsafe{out_ok.write(ok);out_failed.write(failed)};OK}
        Err(e)=>e,
    }
}

#[cfg(test)]
mod tests{
    use super::*;
    #[test]
    fn m0_embedded_go_private_control_rejects_unknown_and_null(){
        assert_eq!(unsafe{wbd_m0_embedded_go_prepare(
            std::ptr::null(),COLD_V4_LEN,std::ptr::null(),HANDOFF_V1_LEN,
            std::ptr::null_mut())},INVALID);
        assert_eq!(stage(0x5742,1,&[1]),UNKNOWN);
        assert_eq!(commit(0x5742,0,0,3),UNKNOWN);
        assert_eq!(stop(0x5742),UNKNOWN);
        assert_eq!(release(0x5742),UNKNOWN);
    }
}
