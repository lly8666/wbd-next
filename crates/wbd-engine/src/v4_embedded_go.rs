//! Opt-in, non-_test in-process Go→Rust V4 control adapter.
//! This uses the ordinary ProtectedScopedOwner (real M1/M3 AEAD/PN).
//! It is NOT a standalone credential validator: only package-private Go
//! code after verified TLS credentials may call the feature-gated adapter.
//! Never distribute the feature-enabled shared library as a public installer.
//! Default production ABI features stay zero; M4 driver-held stop NOT_RUN.
#![allow(clippy::missing_safety_doc)]
use std::collections::BTreeMap;
use std::sync::{Mutex,OnceLock,Arc,atomic::{AtomicBool,AtomicU64,Ordering}};
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
use std::thread::{self,JoinHandle};
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
use std::ffi::c_int;
use wbd_types::MonoNs;
use wbd_types::buffer_contract::UniqueSealable;
use crate::memory::Arena;
use crate::cold_v4::{UntrustedColdV4,COLD_V4_LEN};
use crate::v4_protected_handoff::{PrivateGoV4Handoff,HANDOFF_V1_LEN};
use crate::v4_owner_crypto::{ProtectedScopedOwner,NormalOffReceive};
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
use crate::v4_owner_crypto::ScopedLinuxBudget;
use wbd_codec::record_frame::FIXED_WIRE_OVERHEAD;
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
use wbd_codec::link_fec_wire::{LinkPacketPlan,LinkMode};
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
use wbd_platform::linux_raw_carrier::{ScopedRawIpv4Rx,ScopedRawIpv4Tx};
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
use wbd_platform::linux_tun_sink::{ScopedTunSink,TunReadyEntry,TunError};
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
use wbd_platform::ipv4_tcp::{Ipv4Tuple,PacketPersona,Presentation};
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
use std::os::fd::BorrowedFd;
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
use std::time::Instant;
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
use std::net::Ipv4Addr;
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
use wbd_platform::r1::StopResult;
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
use wbd_platform::rx_ipv4_tcp::extend_seq32;
use crate::runtime::early_rx::EarlyAccepted;
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
use crate::runtime::RxPacket;
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
use crate::runtime::TxDispatch;
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
use std::time::Duration;
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
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
struct WorkerRouteBudget {
    scoped:ScopedLinuxBudget,
    observed_at:Instant,
    ifindex:u32,
    destination:Ipv4Addr,
    revision:u64,
    route_event_revision:u64,
}
struct Entry{
    generation:u32,
    owner:ProtectedScopedOwner,normal:Option<NormalOffReceive>,
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    tx_route:Option<WorkerRouteBudget>,
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    tx_route_revision:u64,
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    raw_tx_lease_mtu:u32,
    // Generation/epoch-scoped, never wrap into an active fragment ID.
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    next_link_packet_id:u32,
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    workers:Option<LoopWorkers>,
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    joining:bool,
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    counters:Arc<LoopCounts>,
    arena:Arena,phase:u32,
    rx_boundary:u32,wire_limit:u16,staged_count:u32,staged_bytes:u32,
    // Extended only after this same-session AEAD+PN opener admits real data.
    // The fixed Go bootstrap boundary cannot serve as the seq32 anchor forever.
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    rx_seq_anchor:u64,
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    flow:crate::v4_protected_handoff::GoFlow,
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    raw_rx:Option<Arc<ScopedRawIpv4Rx>>,
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    raw_tx:Option<Arc<ScopedRawIpv4Tx>>,
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    tun_sink:Option<Arc<ScopedTunSink>>,
}
// Global registry only handles lifetime lookup. Once the original
// authenticated Go control starts perpetual workers, RX's actual AEAD+PN,
// LINK and M1 arena are MOVED to RX; this Entry guards TX/control only.
struct Registry{generation:u32,entries:BTreeMap<u64,Arc<Mutex<Entry>>>}
fn registry()->&'static Mutex<Registry>{
    static R:OnceLock<Mutex<Registry>>=OnceLock::new();
    R.get_or_init(||Mutex::new(Registry{generation:1,entries:BTreeMap::new()}))
}
fn session(handle:u64)->Result<Arc<Mutex<Entry>>,i32>{
    let r=registry().lock().map_err(|_|BAD_STAGE)?;
    r.entries.get(&handle).cloned().ok_or(UNKNOWN)
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
    let arena=Arena::new(generation,128,2048,128,1_000_000)
        .map_err(|_|FULL)?;
    r.entries.insert(handle,Arc::new(Mutex::new(Entry{
        generation,owner,normal:Some(normal),arena,phase:PH_PREPARED,rx_boundary:handoff.rx_boundary,
        #[cfg(all(target_arch="x86_64",target_env="gnu"))]
        rx_seq_anchor:u64::from(handoff.rx_boundary),
        wire_limit:data.identity().server_limit,staged_count:0,staged_bytes:0,
        #[cfg(all(target_arch="x86_64",target_env="gnu"))]
        flow:handoff.flow,
        #[cfg(all(target_arch="x86_64",target_env="gnu"))]
        tx_route:None,
        #[cfg(all(target_arch="x86_64",target_env="gnu"))]
        tx_route_revision:0,
        #[cfg(all(target_arch="x86_64",target_env="gnu"))]
        raw_tx_lease_mtu:0,
        #[cfg(all(target_arch="x86_64",target_env="gnu"))]
        next_link_packet_id:1,
        #[cfg(all(target_arch="x86_64",target_env="gnu"))]
        workers:None,
        #[cfg(all(target_arch="x86_64",target_env="gnu"))]
        joining:false,
        #[cfg(all(target_arch="x86_64",target_env="gnu"))]
        counters:Arc::new(LoopCounts::default()),
        #[cfg(all(target_arch="x86_64",target_env="gnu"))]
        raw_rx:None,
        #[cfg(all(target_arch="x86_64",target_env="gnu"))]
        raw_tx:None,
        #[cfg(all(target_arch="x86_64",target_env="gnu"))]
        tun_sink:None,
    })));
    Ok(handle)
}
fn stage(handle:u64,seq:u32,payload:&[u8])->i32{
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_PREPARED{return BAD_STAGE}
    let len=payload.len();
    let max=u32::from(e.wire_limit)*64;
    let delta=seq.wrapping_sub(e.rx_boundary);
    if len==0||len>usize::from(e.wire_limit)||e.staged_count>=MAX_EARLY
       ||e.staged_bytes.saturating_add(len as u32)>u32::from(e.wire_limit)*MAX_EARLY
       ||delta>=max||delta.saturating_add(len as u32)>max{return INVALID}
    let Ok(mut slab)=e.arena.allocate()else{return FULL};
    slab.writable()[..len].copy_from_slice(payload);
    let boundary=e.rx_boundary;
    match e.owner.offer_early(slab,0..len,u64::from(boundary)+u64::from(delta),MonoNs(0)){
        Ok(EarlyAccepted::Staged)=>{e.staged_count+=1;e.staged_bytes+=len as u32;OK}
        _=>INVALID
    }
}
fn commit(handle:u64,count:u32,bytes:u32,tx_boundary:u32)->i32{
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
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
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if e.phase==PH_ACTIVE{return OK} // Go defer after commit
    if e.phase!=PH_PREPARED{return BAD_STAGE}
    // Terminal before unlink, including for racing cloned references.
    let _=e.owner.stop();
    e.phase=PH_STOPPED;
    drop(e);
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    if r.entries.get(&handle).is_some_and(|x|Arc::ptr_eq(x,&cell)){
        r.entries.remove(&handle);
    }
    OK
}
fn stop(handle:u64)->i32{
    // Leave registry unlocked while joining. Driver handles and owner slabs
    // cannot be released while either Rust worker still references them.
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    {
        let Ok(cell)=session(handle)else{return UNKNOWN};
        let workers={
            let Ok(mut e)=cell.lock()else{return BAD_STAGE};
            if e.phase==PH_STOPPED{return OK}
            if e.phase!=PH_ACTIVE && e.phase!=PH_STOPPING{return BAD_STAGE}
            if e.joining{return STOP_INCOMPLETE}
            let w=e.workers.take();
            if let Some(ref w)=w{
                w.shutdown.store(true,Ordering::Release);
                e.joining=true;
            }
            e.phase=PH_STOPPING;
            w
        };
        if let Some(w)=workers{
            let rx=w.rx.join();
            let tx=w.tx.join();
            if rx.is_err()||tx.is_err(){
                // A failed join cannot authorize driver/slab retirement.
                return STOP_INCOMPLETE
            }
            let Ok(mut e)=cell.lock()else{return BAD_STAGE};
            e.joining=false;
        }
    }
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if e.phase==PH_STOPPED{return OK}
    if e.phase!=PH_ACTIVE&&e.phase!=PH_STOPPING{return BAD_STAGE}
    // Stop the REAL M4 raw driver and TUN sink before quiescing original
    // M1 owner. Both were opened on the same verified generation, never
    // inferred from cold248. A live in-flight kernel borrow must stay held.
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    {
        if let Some(ref raw)=e.raw_rx {raw.begin_stop()}
        if let Some(ref raw)=e.raw_tx {raw.begin_stop()}
        if let Some(ref tun)=e.tun_sink {tun.begin_stop()}
    }
    let Ok(retired)=e.owner.stop()else{return BAD_STAGE};
    let mut drained=retired.ready.batch_handles_released();
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    {
        if let Some(ref raw)=e.raw_rx{
            drained &= raw.stop_until(Instant::now())==StopResult::Drained;
        }
        if let Some(ref raw)=e.raw_tx{
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
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_STOPPED{return BAD_STAGE}
    drop(e);
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    if r.entries.get(&handle).is_some_and(|x|Arc::ptr_eq(x,&cell)){
        r.entries.remove(&handle);
    }
    OK
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
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    unsafe{out.write(e.phase)};OK
}

// The same non-_test Go-verified owner now owns BOTH actual M4 device
// handles. No shadow/test engine, no alternate AEAD/PN or delivery route.
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn attach_raw(handle:u64,ifindex:u32)->i32{
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.raw_rx.is_some(){return BAD_STAGE}
    let Ok(driver)=ScopedRawIpv4Rx::open("lo",ifindex,(handle>>32) as u32)
    else{return INVALID};
    e.raw_rx=Some(Arc::new(driver));OK
}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn attach_tun(handle:u64,fd:i32,name:&str)->i32{
    if fd<3{return INVALID}
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.tun_sink.is_some(){return BAD_STAGE}
    // Borrow only for dup(): Rust owns its duplicate, Go owns original FD.
    let Ok(dup)=unsafe{BorrowedFd::borrow_raw(fd)}.try_clone_to_owned()
    else{return INVALID};
    let Ok(tun)=ScopedTunSink::from_owned_fd(dup,(handle>>32) as u32,name)
    else{return INVALID};
    e.tun_sink=Some(Arc::new(tun));OK
}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn raw_to_tun(handle:u64)->Result<(u32,u32),i32>{
    let cell=session(handle)?;
    let mut guard=cell.lock().map_err(|_|BAD_STAGE)?;
    let e:&mut Entry=&mut guard;
    if e.phase!=PH_ACTIVE||e.workers.is_some(){return Err(BAD_STAGE)}
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
    let normal=e.normal.as_mut().ok_or(BAD_STAGE)?;
    let (returned,report,delivered,failed)=e.owner.drain_normal_off_to_tun(
        normal,tun,MonoNs(0),Vec::with_capacity(32),
    ).map_err(|_|BAD_STAGE)?;
    drop(returned);
    e.arena.drain_returns();
    // A valid authenticated fragment is deliberately NOT a business packet.
    // Keep the M3 reassembly slot for the next raw record; pending must never
    // write a partial IP datagram to TUN or be counted as a failed delivery.
    if report.authenticated.link_ready!=1 || failed!=0 || report.malformed!=0
        || report.discarded!=0{return Err(INVALID)}
    if report.completed==1 && delivered==1 && report.pending==0{
        return Ok((delivered,failed))
    }
    if report.pending==1 && report.completed==0 && delivered==0{
        return Ok((0,0))
    }
    Err(INVALID)
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


/// Reverse app path using SAME protected generation, non-_test normal Rust
/// LINK AEAD/PN, and real Linux M4 ScopedTunSink/ScopedRawIpv4Tx objects.
/// One trusted Go session tuple and original Tx boundary; never resynthesize
/// keys/seq/PN in the FFI or in Go. Driver is retained through Stop.
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn tun_to_raw(handle:u64,ifindex:u32)->Result<(u64,u32,u32,u32),i32>{
    let cell=session(handle)?;
    let mut guard=cell.lock().map_err(|_|BAD_STAGE)?;
    let e:&mut Entry=&mut guard;
    if e.phase!=PH_ACTIVE||e.workers.is_some(){return Err(BAD_STAGE)}
    let tun=e.tun_sink.as_ref().ok_or(BAD_STAGE)?;
    let flow=e.flow;
    if e.raw_tx.is_none(){
        let driver=ScopedRawIpv4Tx::open("lo",ifindex,(handle>>32) as u32)
            .map_err(|_|INVALID)?;
        let observed=wbd_platform::linux_packet_preflight::observe_interface_mtu(
            "lo",ifindex).map_err(|_|INVALID)?;
        e.raw_tx_lease_mtu=observed.kernel_mtu;
        e.raw_tx=Some(Arc::new(driver));
    }
    let route=e.owner.observe_linux_normal_off_route_budget(
        "lo",ifindex,Ipv4Addr::from(flow.client_ip)
    ).map_err(|_|INVALID)?;
    let slab=e.arena.allocate().map_err(|_|FULL)?;
    let (pn,seq,_wire_len,app_len)=e.owner.seal_tun_ipv4_normal_off(
        tun,slab,&route,15,MonoNs(0)
    ).map_err(|_|INVALID)?;
    let raw=e.raw_tx.as_ref().ok_or(BAD_STAGE)?;
    let tuple=Ipv4Tuple{
        src_ip:&flow.server_ip,dst_ip:&flow.client_ip,
        src_port:flow.server_port,dst_port:flow.client_port,
    };
    let presentation=Presentation{
        ack32:1,advertised_window:4096,ip_id:43,
        persona:PacketPersona::Legacy,
    };
    let full=e.owner.submit_scoped_raw_tx(raw,tuple,presentation,MonoNs(0))
        .map_err(|_|BAD_STAGE)?;
    e.arena.drain_returns();
    Ok((pn,seq,u32::try_from(full).map_err(|_|INVALID)?,
        u32::try_from(app_len).map_err(|_|INVALID)?))
}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_tun_to_raw(
    handle:u64,ifindex:u32,pn:*mut u64,seq:*mut u32,
    packet_len:*mut u32,app_len:*mut u32,
)->i32{
    if pn.is_null()||seq.is_null()||packet_len.is_null()||
        app_len.is_null(){return INVALID}
    match tun_to_raw(handle,ifindex){
        Ok((p,s,wire,app))=>{
            unsafe{pn.write(p);seq.write(s);
                packet_len.write(wire);app_len.write(app)};
            OK
        }
        Err(e)=>e,
    }
}


// Development-only perpetual owner processing, never a parallel crypto
// implementation. Two independent Rust kernel-readiness threads; Go app
// sender and receiver do not call per-packet RX/TX helpers. The READY poll
// is outside the shared registry lock. Subsequent owner admission, AEAD/PN,
// Normal/off and kernel driver send use the exact existing Rust functions.
// Unrelated raw TCP is discarded by M4; RX's actual mutable opener/PN,
// reassembly and arena belong to RX alone after Go Detach, not Entry.
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
#[repr(C)]
struct PollFd {fd:c_int,events:i16,revents:i16}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
unsafe extern "C" {fn poll(fds:*mut PollFd,count:usize,timeout:c_int)->c_int;}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
#[derive(Default)]
struct LoopCounts {
    rx:AtomicU64,tx:AtomicU64,rx_error:AtomicU64,tx_error:AtomicU64,
    tx_dropped:AtomicU64,tx_uncertain:AtomicU64,tx_backpressure:AtomicU64,
    route_refresh:AtomicU64,
    rx_thread_cpu_ns:AtomicU64,tx_thread_cpu_ns:AtomicU64,
}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
struct LoopWorkers{
    shutdown:Arc<AtomicBool>,
    rx:JoinHandle<()>,
    tx:JoinHandle<()>,
    route_events:Arc<wbd_platform::linux_route_events::RouteEvents>,
}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
#[repr(C)]
struct ClockTimespec {seconds:i64,nanoseconds:i64}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
unsafe extern "C" {
    fn clock_gettime(clock_id:c_int,raw:*mut ClockTimespec)->c_int;
}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn owner_thread_cpu_ns()->u64{
    let mut sample=ClockTimespec{seconds:0,nanoseconds:0};
    // Linux CLOCK_THREAD_CPUTIME_ID=3, measures ONLY this original Rust
    // worker's CPU, excluding Go injector/receiver goroutines and sleeps.
    if unsafe{clock_gettime(3,&mut sample)}!=0{return 0}
    u64::try_from(sample.seconds).unwrap_or(0).saturating_mul(1_000_000_000)
        .saturating_add(u64::try_from(sample.nanoseconds).unwrap_or(0))
}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn loop_now()->MonoNs{
    static START:OnceLock<Instant>=OnceLock::new();
    MonoNs(START.get_or_init(Instant::now).elapsed().as_nanos().min(u64::MAX as u128) as u64)
}
// Bounded M1 arena return servicing inside one authenticated DATA turn.
// Only Stop/report/quiescence/control paths may drain every outstanding item;
// an arbitrarily long backlog must not monopolize the per-session TX/RX lock.
// Arena::allocate already drains at most 64 before making a new loan.
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
const M0_DATA_RETURN_TURN_CAP:usize=64;
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn drain_data_turn_returns(arena:&mut Arena)->usize{
    arena.drain_returns_bounded(M0_DATA_RETURN_TURN_CAP)
}

// Do not hold global registry lock while M4 RX preflight ignores unrelated
// RST/ACK or polls for up to 750ms. M4 receives directly into the already
// allocated ORIGINAL M1 UniqueBuffer via recvmmsg and checks trusted tuple and
// TCP checksum. On reentry the ONLY decrypt/PN/LINK/TUN path is the original
// Rust ScopedOwner. Stop joins worker before owner/slab/driver retirement.
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
// Only a successfully authenticated (AEAD and unique PN) Normal/off LINK
// admission may advance the seq32 reference. A raw TCP tuple/checksum/seq
// is not proof: an attacker could otherwise jump the 64-bit high-water mark.
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn authenticated_rx_anchor(anchor:u64,absolute_seq:u64,wire_len:usize,
    admitted_link:u32)->Option<u64>{
    if admitted_link!=1{return Some(anchor)}
    let end=absolute_seq.checked_add(u64::try_from(wire_len).ok()?)?;
    Some(anchor.max(end))
}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn background_raw_once(
    owner:&mut crate::v4_owner_crypto::ProtectedBackgroundRx,
    arena:&mut Arena,anchor:&mut u64,
    flow:crate::v4_protected_handoff::GoFlow,generation:u32,
    raw:&ScopedRawIpv4Rx,tun:&ScopedTunSink,stop:&AtomicBool,
    rx_pending:&mut Vec<crate::memory::UniqueBuffer>,
)->Result<u32,i32>{
    // The SAME original Go credential-derived AEAD+PN opener and M3 LINK
    // table are now owned by RX, not re-initialized or cloned. RX never
    // locks Entry / TX during normal packets, ready or Stop detection.
    while rx_pending.len()<32{
        match arena.allocate(){
            Ok(slab)=>rx_pending.push(slab),
            Err(_)=>break,
        }
    }
    if rx_pending.is_empty(){return Err(FULL)}
    let tuple=Ipv4Tuple{
        src_ip:&flow.client_ip,dst_ip:&flow.server_ip,
        src_port:flow.client_port,dst_port:flow.server_port,
    };
    let slot_count=rx_pending.len();
    let mut slots:[&mut [u8];32]=std::array::from_fn(|_|&mut [][..]);
    for (dst,slab) in slots.iter_mut().zip(rx_pending.iter_mut()){
        *dst=slab.writable();
    }
    let batch=raw.receive_kernel_multimsg(
        generation,&mut slots[..slot_count],tuple,PacketPersona::Legacy
    ).map_err(|_|INVALID)?;
    drop(slots);
    if stop.load(Ordering::Acquire){return Err(BAD_STAGE)}
    if batch.observed==0{return Err(INVALID)}
    let mut delivered_total=0u32;
    // Unused preposted original M1 slabs persist in this RX worker; used
    // ones return through the same bounded per-arena return path.
    for (i,slab) in rx_pending.drain(..batch.observed).enumerate(){
        let (len,seq)=match batch.entry(i){
            Some(wbd_platform::linux_raw_carrier::RawReadyEntry::Unauthenticated{
                cipher_len,seq32
            })=>(cipher_len,seq32),
            _=>{drop(slab);continue},
        };
        if stop.load(Ordering::Acquire){break}
        let absolute=match extend_seq32(*anchor,seq){
            Ok(n)=>n,Err(_)=>{drop(slab);continue}
        };
        // Exactly one actual M3 opener and unique replay PN bitmap.
        let receipt=owner.consume_original(slab,len,tun,loop_now());
        let Some(next)=authenticated_rx_anchor(
            *anchor,absolute,len,receipt.authenticated_link
        )else{continue};
        *anchor=next;
        if receipt.failed==0{
            delivered_total=delivered_total.saturating_add(receipt.delivered);
        }
    }
    arena.drain_returns_bounded(M0_DATA_RETURN_TURN_CAP);
    if delivered_total==0{return Err(INVALID)}
    Ok(delivered_total)
}
// Independently wait for the REAL TUN application RX OUTSIDE registry lock.
// Only original owner grants route-bound budget, seals AEAD/PN and submits
// original frozen M1 record through genuine scoped M4 raw TX.
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
#[derive(Debug,Default,Clone,Copy,Eq,PartialEq)]
struct TxTurnCompletion{
    copied:u32,definitely_unsent:u32,uncertain:u32,
    backpressure:bool,failed:bool,invalidate_route:bool,
}
// The only completion translation on the original authenticated TX path.
// Exactly the kernel-copied prefix counts, the untouched suffix is dropped
// by the existing bounded owner drain; an uncertain record is NEVER retried.
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn classify_tx_turn(report:Option<&wbd_platform::linux_batch::KernelSendReport>,
    ready:usize,seal_failed:bool)->TxTurnCompletion{
    use wbd_platform::linux_batch::KernelSendSignal as S;
    let sent=report.map_or(0,|r|r.outcome.accepted_prefix.min(ready));
    let uncertain=usize::from(report.is_some_and(|r|
        r.outcome.uncertain_index==Some(sent) && sent<ready));
    let failed=seal_failed || report.is_none_or(|r|
        r.outcome.error.is_some()||r.signal!=S::None||sent!=ready);
    TxTurnCompletion{
        copied:sent as u32,
        definitely_unsent:ready.saturating_sub(sent+uncertain) as u32,
        uncertain:uncertain as u32,
        backpressure:report.is_some_and(|r|r.signal==S::Backpressure),
        failed,
        // Path/device/actual MTU exception only. Ordinary EAGAIN, partial
        // errno-unavailable, or uncertain completion says nothing definite
        // about route change; per-record preflight rejects never invalidate.
        invalidate_route:report.is_some_and(|r|matches!(r.signal,
            S::RouteUnavailable|S::DeviceUnavailable|S::MtuExceeded)),
    }
}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn raw_driver_reopen_on_route_change(
    has_cache:bool,previous_refresh_count:u64,observed_mtu:u32,lease_mtu:u32
)->bool{
    // A genuine 65536->1500 MTU shrink MUST continue to reject this
    // authenticated generation, even if the smaller packet would fit.
    // Only after M4 has actually failed and M0 invalidated its route cache,
    // and the trusted kernel observation has recovered to the original
    // lease capacity, may this owner install a fresh same-generation FD.
    !has_cache && previous_refresh_count!=0 && lease_mtu!=0
        && observed_mtu>=lease_mtu
}
// The original M1 arena holds ALL slabs for one LINK packet BEFORE the
// first original owner AEAD/PN/Seq and TX admission. On any bad stride,
// capacity shortage or invalid packet ID the local Vec drops every slab;
// no partial packet is ever queued due to fragment materialization failure.
// This remains a bounded 32-record SAME-turn staging step, NOT yet 64KiB
// cross-turn scheduling or atomic kernel sendmmsg completion.
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn stage_bounded_original_link(
    arena:&mut Arena, source:&[u8],frame_mtu:usize,
    packet_id:u32,available_records:usize
)->Result<Vec<(crate::memory::UniqueBuffer,usize)>,i32>{
    let mut plan=LinkPacketPlan::new(
        source,frame_mtu,LinkMode::FixedOff,packet_id
    ).map_err(|_|INVALID)?;
    let count=plan.total_frames();
    if count==0 || count>available_records || count>32{return Err(FULL)}
    let mut staged=Vec::with_capacity(count);
    for _ in 0..count{
        let part=plan.issue_next(frame_mtu).map_err(|_|INVALID)?
            .ok_or(INVALID)?;
        // Acquire the full bounded loan set before consuming ANY PN. On
        // allocation error earlier slabs simply return to this same arena.
        let mut slot=arena.allocate().map_err(|_|FULL)?;
        let end=14usize.checked_add(part.len()).ok_or(INVALID)?;
        if end>slot.writable().len(){return Err(INVALID)}
        slot.writable()[14..end].copy_from_slice(&part);
        staged.push((slot,part.len()));
    }
    if plan.issue_next(frame_mtu).map_err(|_|INVALID)?.is_some(){
        return Err(INVALID)
    }
    Ok(staged)
}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn background_tun_once(cell:&Mutex<Entry>,tun:&ScopedTunSink,
    stop:&AtomicBool,ifindex:u32,tx_storage:&mut Vec<TxDispatch>,
    pending:&mut Vec<(crate::memory::UniqueBuffer,usize)>,
    ready_records:&mut Vec<crate::memory::FrozenRecord>,
    presentations:&mut Vec<Presentation>,
    events:&wbd_platform::linux_route_events::RouteEvents)->Result<TxTurnCompletion,i32>{
    // The caller has ALREADY polled the first TUN packet. Never wait for
    // batch fill: one sparse packet is sealed/submitted immediately.
    // The stack-owned vectors are reserved once per worker (not per DATA).
    pending.clear();
    ready_records.clear();
    presentations.clear();
    let started=Instant::now();
    let generation={
        let mut e=cell.lock().map_err(|_|BAD_STAGE)?;
        if e.phase!=PH_ACTIVE{return Err(BAD_STAGE)}
        e.generation
    };
    let mut ingress_error=false;
    let mut observed=0usize;
    loop {
        if stop.load(Ordering::Acquire){return Err(BAD_STAGE)}
        let mut slab={
            let mut e=cell.lock().map_err(|_|BAD_STAGE)?;
            if e.phase!=PH_ACTIVE{return Err(BAD_STAGE)}
            match e.arena.allocate(){
                Ok(s)=>s,Err(_)=>{
                    // Preserve packets already read instead of dropping their
                    // ownership and denying a full fresh batch.
                    ingress_error=true;break
                }
            }
        };
        let space=slab.writable().len().checked_sub(14).ok_or(INVALID)?;
        if space<20{return Err(INVALID)}
        // Reuse M4's existing poll(0)+O_NONBLOCK read. The single reader
        // only borrows the shared TUN mutex for an immediately ready read:
        // after filtering IPv6/invalid L3, no wait under the writer's lock.
        let read={
            let mut slots=[&mut slab.writable()[14..]];
            tun.read_ready_batch(generation,&mut slots)
        };
        observed+=1;
        match read {
            Ok(batch)=>match batch.entry(0) {
                Some(TunReadyEntry::UntrustedIpv4{len})=>pending.push((slab,len)),
                Some(TunReadyEntry::Rejected)=>{drop(slab);},
                _=>{break}, // EAGAIN, EINTR or readiness race: healthy idle
            },
            Err(TunError::Stopped)=>return Err(BAD_STAGE),
            Err(_)=>{ingress_error=true;break},
        }
        // Bound *all observed* frames, including malicious invalid floods.
        if observed>=32 || stop.load(Ordering::Acquire){break}
        // Work budget sampled every eight packets, never by the kernel CPU
        // clock on every DATA. The poll is nonblocking and is the sole gate
        // for another TUN read; no fixed 32-entry latency penalty.
        if pending.len()%8==0 && started.elapsed()>=Duration::from_micros(100){break}
        if !loop_readiness(tun.readiness_fd(),stop,0){break}
    }
    if pending.is_empty(){return if ingress_error{Err(INVALID)}else{Ok(TxTurnCompletion::default())}}
    // Route validation and original M1/M3 AEAD/PN/queue admission occur
    // under the current generation's owner. M4's real sendmmsg follows
    // OUTSIDE Entry lock with an immutable original LoanBatch.
    let (batch,raw,flow,generation,admitted,seal_failed)={
        let mut guard=cell.lock().map_err(|_|BAD_STAGE)?;
        let e:&mut Entry=&mut guard;
        if e.phase!=PH_ACTIVE||stop.load(Ordering::Acquire){return Err(BAD_STAGE)}
        let flow=e.flow;
        let destination=Ipv4Addr::from(flow.client_ip);
        let event=events.snapshot();
        if let Some(cache)=e.tx_route.as_ref(){
            if wbd_platform::linux_route_events::classify(
                cache.route_event_revision,event.revision,cache.observed_at.elapsed()
            )==wbd_platform::linux_route_events::EventRefresh::Defer{
                return Err(INVALID)
            }
        }
        let refresh=e.tx_route.as_ref().is_none_or(|cache|
            cache.observed_at.elapsed()>=Duration::from_secs(1)
            || cache.ifindex!=ifindex || cache.destination!=destination
            || cache.revision!=e.tx_route_revision
            || cache.route_event_revision!=event.revision
        );
        if refresh{
            // M0 owner snapshot refresh alone cannot resurrect M4's
            // deliberately invalidated ScopedRouteBudget, or change the
            // device MTU bound frozen when its raw FD was opened. Reopen the
            // SAME trusted M4 driver, generation and ifindex ONLY on actual
            // link/route revision change or prior invalidation; never on
            // ordinary 1s refresh or DATA. Exact one background TX worker
            // owns this handle, so no other TX batch can be in flight.
            let has_cache=e.tx_route.is_some();
            e.tx_route=None;
            let snapshot=e.owner.observe_linux_normal_off_route_budget(
                "lo",ifindex,destination
            ).map_err(|_|INVALID)?;
            let must_reopen=raw_driver_reopen_on_route_change(
                has_cache,e.tx_route_revision,snapshot.observed_interface_mtu,
                e.raw_tx_lease_mtu
            );
            if must_reopen{
                let fresh=ScopedRawIpv4Tx::open("lo",ifindex,e.generation)
                    .map_err(|_|INVALID)?;
                let old=e.raw_tx.as_ref().ok_or(BAD_STAGE)?;
                // One unique active TX loop: no asynchronous kernel data
                // loan may remain when the old FD is retired. Failure keeps
                // the owner fail-closed, never drops a live borrowed slab.
                if old.outstanding()!=0{return Err(BAD_STAGE)}
                old.begin_stop();
                if old.stop_until(Instant::now())!=StopResult::Drained{
                    return Err(BAD_STAGE)
                }
                e.raw_tx=Some(Arc::new(fresh));
                e.raw_tx_lease_mtu=snapshot.observed_interface_mtu;
            }
            e.tx_route_revision=e.tx_route_revision.checked_add(1).ok_or(FULL)?;
            e.tx_route=Some(WorkerRouteBudget{
                scoped:snapshot,observed_at:Instant::now(),ifindex,destination,
                revision:e.tx_route_revision,route_event_revision:event.revision,
            });
            e.counters.route_refresh.fetch_add(1,Ordering::Relaxed);
        }
        let mut accepted=0usize;
        let mut failed=ingress_error;
        for (mut slab,n) in pending.drain(..){
            if stop.load(Ordering::Acquire){failed=true;break}
            // The NORMAL small-packet path stays unchanged: no LINK20, no
            // packet copy and no extra timer. One oversized real TUN IPv4
            // packet is slow-path fragmented using M3's immutable single-
            // snapshot plan, then EACH frame follows the original M1 owner,
            // real AEAD/PN, scoped raw lease and kernel syscall. Never seal
            // a naked over-budget ordinary frame.
            let frame_mtu=e.tx_route.as_ref().ok_or(BAD_STAGE)?
                .scoped.frame.link_frame_mtu;
            if n<=frame_mtu {
                let scoped=&e.tx_route.as_ref().ok_or(BAD_STAGE)?.scoped;
                let result=e.owner.seal_normal_off_with_worker_snapshot(
                    slab,n,scoped,ifindex,destination,15,loop_now()
                );
                if result.is_ok(){accepted+=1}else{failed=true}
                continue;
            }
            let id=e.next_link_packet_id;
            if id==0 || id==u32::MAX || n>65_535 {
                failed=true;continue;
            }
            let source=&slab.writable()[14..14+n];
            let staged=match stage_bounded_original_link(
                &mut e.arena,source,frame_mtu,id,32usize.saturating_sub(accepted)
            ){
                Ok(all)=>all,
                Err(_)=>{failed=true;continue}
            };
            // All pieces are now present in original generation-scoped M1
            // slots. No short arena or malformed LINK part can publish a
            // prefix before this point; reserve a never-reused logical ID.
            e.next_link_packet_id=id+1;
            for (fragment_slab,part_len) in staged{
                if stop.load(Ordering::Acquire){failed=true;break}
                let scoped=&e.tx_route.as_ref().ok_or(BAD_STAGE)?.scoped;
                let result=e.owner.seal_fragment_with_worker_snapshot(
                    fragment_slab,part_len,scoped,ifindex,destination,
                    15,loop_now()
                );
                if result.is_ok(){accepted+=1}else{failed=true;break}
            }
        }
        if accepted==0{
            drain_data_turn_returns(&mut e.arena);
            return Err(INVALID)
        }
        let raw=Arc::clone(e.raw_tx.as_ref().ok_or(BAD_STAGE)?);
        let available=std::mem::take(tx_storage);
        let batch=match e.owner.drain_tx(loop_now(),available){
            Ok(batch)=>batch,
            Err((_,storage))=>{
                *tx_storage=storage;e.tx_route=None;
                drain_data_turn_returns(&mut e.arena);
                return Err(BAD_STAGE)
            }
        };
        let ready=e.owner.checked_tx_ready(&batch).map_err(|_|BAD_STAGE)?;
        if ready.is_empty() || ready.len()>32 || ready.iter().any(
            |x|x.kind!=crate::runtime::TxKind::Fresh){
            *tx_storage=batch.recycle();
            e.tx_route=None;
            drain_data_turn_returns(&mut e.arena);
            return Err(INVALID)
        }
        // Clone only Arc handles into preallocated metadata, NEVER the
        // plaintext/ciphertext. Both vectors are recycled next turn.
        for x in ready{
            ready_records.push(x.record.clone());
            presentations.push(Presentation{
                ack32:1,advertised_window:4096,ip_id:43,
                persona:PacketPersona::Legacy,
            });
        }
        (batch,raw,flow,e.generation,ready_records.len(),failed)
    };
    let report=if stop.load(Ordering::Acquire){None}else{
        let tuple=Ipv4Tuple{
            src_ip:&flow.server_ip,dst_ip:&flow.client_ip,
            src_port:flow.server_port,dst_port:flow.client_port,
        };
        Some(raw.send_kernel_multimsg(
            generation,ready_records.as_slice(),tuple,presentations.as_slice()
        ))
    };
    ready_records.clear();
    presentations.clear();
    *tx_storage=batch.recycle();
    let mut guard=cell.lock().map_err(|_|BAD_STAGE)?;
    let e:&mut Entry=&mut guard;
    if e.phase!=PH_ACTIVE||stop.load(Ordering::Acquire){
        drain_data_turn_returns(&mut e.arena);
        return Err(BAD_STAGE)
    }
    let finish=classify_tx_turn(report.as_ref(),admitted,seal_failed);
    if finish.invalidate_route{e.tx_route=None}
    drain_data_turn_returns(&mut e.arena);
    // Even when the tail failed, the definite prefix remains copied and
    // accounted. Dropped/uncertain immutable records are only released
    // after synchronous M4 sendmmsg completes; never reseal/reuse PN.
    Ok(finish)
}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn loop_readiness(fd:i32,stop:&AtomicBool,timeout_ms:c_int)->bool{
    if stop.load(Ordering::Acquire){return false}
    let mut p=PollFd{fd,events:1,revents:0};
    // Block only to discover the first ready packet. Further work in the
    // same bounded slice only drains immediately ready packets (timeout 0).
    // Never sleep to fill a batch, and never wait under registry.
    let got=unsafe{poll(&mut p,1,timeout_ms)};
    got>0 && p.revents&1!=0
}

// Accept only a single definitely kernel-copied original FrozenRecord.
// A partial, ambiguous, or backpressured M4 KernelSendReport is never a
// success just because a syscall returned a positive prefix elsewhere.
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn raw_ready_prefix_copied(report:&wbd_platform::linux_batch::KernelSendReport,
    expected:usize)->bool{
    report.outcome.accepted_prefix==expected
        && report.outcome.error.is_none()
        && report.outcome.uncertain_index.is_none()
        && report.signal==wbd_platform::linux_batch::KernelSendSignal::None
}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn raw_one_packet_copied(report:&wbd_platform::linux_batch::KernelSendReport)->bool{
    raw_ready_prefix_copied(report,1)
}

// A single kernel readiness event can service multiple ALREADY ready packets.
// Bounded by both 32 packets and roughly 100us of actual work, so Stop,
// the opposite direction and later control work get regular opportunities.
// The caller owns the packet buffer/driver; no extra packet Vector is built.
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn ready_only_slice(
    stop:&AtomicBool,
    mut next_ready:impl FnMut()->bool,
    mut service:impl FnMut()->bool,
    mut within_budget:impl FnMut()->bool,
)->usize{
    let mut count=0;
    while count<32 && !stop.load(Ordering::Acquire){
        // The caller has already observed one ready packet; never wait
        // again for a first packet or for a larger batch.
        if count!=0 && !next_ready(){break}
        let ok=service();
        count+=1;
        // Sample the monotonic work-slice budget every eight packets, not
        // for every DATA. First-packet/low-rate arrival never waits to batch.
        if !ok || (count%8==0 && !within_budget()){break}
    }
    count
}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn start_loop(handle:u64,ifindex:u32)->i32{
    // One shared Linux link/route listener for all live owner sessions.
    // This is only an invalidation signal; M4 still checks every raw send.
    let events=wbd_platform::linux_route_events::subscribe();
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.workers.is_some(){return BAD_STAGE}
    let (Some(raw),Some(tun))=(e.raw_rx.as_ref(),e.tun_sink.as_ref())
    else{return BAD_STAGE};
    let raw=Arc::clone(raw);
    let tun=Arc::clone(tun);
    let raw_fd=raw.readiness_fd();
    let tun_fd=tun.readiness_fd();
    if e.raw_tx.is_none(){
        let Ok(tx)=ScopedRawIpv4Tx::open("lo",ifindex,(handle>>32) as u32)
        else{return INVALID};
        let Ok(observed)=wbd_platform::linux_packet_preflight::observe_interface_mtu(
            "lo",ifindex) else{return INVALID};
        e.raw_tx_lease_mtu=observed.kernel_mtu;
        e.raw_tx=Some(Arc::new(tx));
    }
    if e.raw_tx_lease_mtu==0{return BAD_STAGE}
    // Build the independent RX arena and move the exact protected opener
    // only after both original raw/TUN devices have been installed. Never
    // allocate a second crypto instance or credential authority.
    let rx_arena_id=e.generation ^ 0x8000_0000;
    if rx_arena_id==0{return FULL}
    let Ok(mut rx_arena)=Arena::new(rx_arena_id,64,2048,64,1_000_000)
    else{return FULL};
    // Preserve pre-Detach early RX bytes. Original M1 32-slot queue is
    // flushed through the SAME opener and LINK table before the move.
    if e.staged_count>0{
        let e:&mut Entry=&mut e;
        let normal=match e.normal.as_mut(){Some(n)=>n,None=>return BAD_STAGE};
        let returned=match e.owner.drain_normal_off_to_tun(
            normal,&tun,loop_now(),Vec::with_capacity(32)){
            Ok((returned,_,_,_))=>returned,
            Err((_,returned))=>{drop(returned);return BAD_STAGE}
        };
        drop(returned);
        drain_data_turn_returns(&mut e.arena);
    }
    let normal=match e.normal.take(){Some(n)=>n,None=>return BAD_STAGE};
    let mut original_rx=match e.owner.detach_background_rx(normal){
        Ok(rx)=>rx,
        Err((_,normal))=>{e.normal=Some(normal);return BAD_STAGE},
    };
    let mut rx_anchor=e.rx_seq_anchor;
    let rx_flow=e.flow;
    let generation=e.generation;
    let shutdown=Arc::new(AtomicBool::new(false));
    let stats=Arc::clone(&e.counters);
    let stop_rx=Arc::clone(&shutdown);
    let stats_rx=Arc::clone(&stats);
    let raw_for_rx=Arc::clone(&raw);
    let tun_for_rx=Arc::clone(&tun);
    let Ok(rx)=thread::Builder::new().name("wbd-original-m4-rx".into())
        .spawn(move||{
            let cpu_origin=owner_thread_cpu_ns();
            let mut last_cpu_sample=Instant::now();
            let mut rx_pending=Vec::<crate::memory::UniqueBuffer>::with_capacity(32);
            while !stop_rx.load(Ordering::Acquire){
                if last_cpu_sample.elapsed()>=Duration::from_millis(100){
                    stats_rx.rx_thread_cpu_ns.store(
                        owner_thread_cpu_ns().saturating_sub(cpu_origin),Ordering::Relaxed);
                    last_cpu_sample=Instant::now();
                }
                if !loop_readiness(raw_fd,&stop_rx,10){continue}
                match background_raw_once(
                    &mut original_rx,&mut rx_arena,&mut rx_anchor,
                    rx_flow,generation,&raw_for_rx,&tun_for_rx,
                    &stop_rx,&mut rx_pending
                ){
                    Ok(n)=>{stats_rx.rx.fetch_add(u64::from(n),Ordering::Relaxed);}
                    Err(_)=>{stats_rx.rx_error.fetch_add(1,Ordering::Relaxed);}
                }
            }
            // No outstanding kernel borrow after the synchronous call,
            // and STOP joins this thread before retiring original drivers.
            rx_pending.clear();
            rx_arena.drain_returns_bounded(M0_DATA_RETURN_TURN_CAP);
            stats_rx.rx_thread_cpu_ns.store(
                owner_thread_cpu_ns().saturating_sub(cpu_origin),Ordering::Relaxed);
        })
    else{
        // The original RX state was consumed by the attempted spawn; fail
        // closed and require normal Stop rather than resurrecting keys.
        e.phase=PH_STOPPING;
        return INVALID
    };
    let stop_tx=Arc::clone(&shutdown);
    let tx_events=Arc::clone(&events);
    let tx_cell=Arc::clone(&cell);
    let Ok(tx)=thread::Builder::new().name("wbd-original-m4-tx".into())
        .spawn(move||{
            let cpu_origin=owner_thread_cpu_ns();
            let mut last_cpu_sample=Instant::now();
            let mut tx_storage=Vec::<TxDispatch>::with_capacity(32);
            let mut tx_pending=Vec::<(crate::memory::UniqueBuffer,usize)>::with_capacity(32);
            let mut tx_records=Vec::<crate::memory::FrozenRecord>::with_capacity(32);
            let mut tx_presentations=Vec::<Presentation>::with_capacity(32);
            while !stop_tx.load(Ordering::Acquire){
                if last_cpu_sample.elapsed()>=Duration::from_millis(100){
                    stats.tx_thread_cpu_ns.store(
                        owner_thread_cpu_ns().saturating_sub(cpu_origin),Ordering::Relaxed);
                    last_cpu_sample=Instant::now();
                }
                if !loop_readiness(tun_fd,&stop_tx,10){continue}
                let slice_start=Instant::now();
                match background_tun_once(
                    &tx_cell,&tun,&stop_tx,ifindex,&mut tx_storage,
                    &mut tx_pending,&mut tx_records,&mut tx_presentations,
                    &tx_events
                ){
                    Ok(done)=>{
                        stats.tx.fetch_add(u64::from(done.copied),Ordering::Relaxed);
                        stats.tx_dropped.fetch_add(u64::from(done.definitely_unsent),Ordering::Relaxed);
                        stats.tx_uncertain.fetch_add(u64::from(done.uncertain),Ordering::Relaxed);
                        if done.backpressure{stats.tx_backpressure.fetch_add(1,Ordering::Relaxed);}
                        if done.failed{stats.tx_error.fetch_add(1,Ordering::Relaxed);}
                    }
                    Err(_)=>{stats.tx_error.fetch_add(1,Ordering::Relaxed);}
                }
                let _=slice_start;
            }
            stats.tx_thread_cpu_ns.store(
                owner_thread_cpu_ns().saturating_sub(cpu_origin),Ordering::Relaxed);
        })
    else{
        shutdown.store(true,Ordering::Release);
        // No worker may still deliver after a failed second spawn.
        e.phase=PH_STOPPING;
        drop(e);
        let _=rx.join();
        return INVALID
    };
    e.workers=Some(LoopWorkers{shutdown,rx,tx,route_events:events});
    OK
}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
#[no_mangle]
pub extern "C" fn wbd_m0_embedded_go_loop_start(handle:u64,ifindex:u32)->i32{
    start_loop(handle,ifindex)
}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_loop_stats(
    h:u64,rx:*mut u64,tx:*mut u64,rx_err:*mut u64,tx_err:*mut u64)->i32{
    if rx.is_null()||tx.is_null()||rx_err.is_null()||tx_err.is_null(){return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    unsafe{
        rx.write(e.counters.rx.load(Ordering::Relaxed));
        tx.write(e.counters.tx.load(Ordering::Relaxed));
        rx_err.write(e.counters.rx_error.load(Ordering::Relaxed));
        tx_err.write(e.counters.tx_error.load(Ordering::Relaxed));
    }
    OK
}

// Developer-only device netlink witness; event revision is NOT MTU authority.
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_loop_route_events(
    h:u64,out_revision:*mut u64,out_healthy:*mut u32)->i32{
    if out_revision.is_null()||out_healthy.is_null(){return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    let Some(w)=e.workers.as_ref()else{return BAD_STAGE};
    let snapshot=w.route_events.snapshot();
    unsafe{
        out_revision.write(snapshot.revision);
        out_healthy.write(u32::from(snapshot.healthy));
    }
    OK
}

// Developer-mode per-worker *actual Linux thread CPU time* for 10s+60s
// receipt. Combined process CPU includes Go sender/reader; independent
// exact user-vs-kernel attribution within that residual is NOT available.
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_loop_route_refresh(
    handle:u64,out:*mut u64)->i32{
    if out.is_null(){return INVALID}
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    unsafe{out.write(e.counters.route_refresh.load(Ordering::Relaxed))}
    OK
}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_loop_thread_cpu(
    h:u64,rx_ns:*mut u64,tx_ns:*mut u64)->i32{
    if rx_ns.is_null()||tx_ns.is_null(){return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    unsafe{
        rx_ns.write(e.counters.rx_thread_cpu_ns.load(Ordering::Relaxed));
        tx_ns.write(e.counters.tx_thread_cpu_ns.load(Ordering::Relaxed));
    }
    OK
}

// Query the real M1/M3 original Rust owner Route/PeerMSS budget after the
// credential-verified private Go control Commit and exact M4 interface bind.
// This value is NOT a cold-self-attested cap or a way to mutate the budget.
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_observed_tx_ipv4_mtu(
    h:u64,ifindex:u32,out:*mut u32)->i32{
    if out.is_null(){return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.tun_sink.is_none()||e.raw_rx.is_none(){
        return BAD_STAGE
    }
    let route=e.owner.observe_linux_normal_off_route_budget(
        "lo",ifindex,Ipv4Addr::from(e.flow.client_ip));
    let Ok(route)=route else{return INVALID};
    let Ok(limit)=u32::try_from(route.frame.single_business_payload_mtu)
    else{return INVALID};
    if limit<28{return INVALID}
    unsafe{out.write(limit)};
    OK
}
#[cfg(test)]
mod tests{
    use super::*;
    #[test]
    fn ready_only_batch_0_1_32_33_and_failure_do_not_wait(){
        use std::cell::Cell;
        let stop=AtomicBool::new(false);
        let count=Cell::new(0usize);
        let polls=Cell::new(0usize);
        // First packet never has to poll a second time. A solitary ready
        // packet terminates immediately at the nonblocking next probe.
        let n=ready_only_slice(&stop,||{polls.set(polls.get()+1);false},
            ||{count.set(count.get()+1);true},||true);
        assert_eq!((n,count.get(),polls.get()),(1,1,1));
        for offered in [1usize,32,33] {
            let complete=Cell::new(0usize);
            let n=ready_only_slice(&stop,
                ||complete.get()<offered,
                ||{complete.set(complete.get()+1);true},
                ||true);
            assert_eq!(n,offered.min(32));
            assert_eq!(complete.get(),offered.min(32));
        }
        let complete=Cell::new(0usize);
        let n=ready_only_slice(&stop,||true,||{
            complete.set(complete.get()+1);
            complete.get()!=3
        },||true);
        assert_eq!((n,complete.get()),(3,3)); // error ends burst
        let n=ready_only_slice(&stop,||true,||true,||false);
        assert_eq!(n,8); // budget is checked once per eight packets
        stop.store(true,Ordering::Release);
        let n=ready_only_slice(&stop,||panic!("unexpected poll"),
            ||panic!("unexpected packet"),||true);
        assert_eq!(n,0);
    }
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    #[test]
    fn r1_m0_live_authenticated_seq32_anchor_wrap_and_untrusted_no_advance(){
        // Same helper and wbd-platform::extend_seq32 used by background_raw_once:
        // Go bootstrap is near wrap and each accepted original LINK frame
        // advances the trusted reference without a real 2GiB allocation.
        let initial=0xffff_ff00u64;
        let first=extend_seq32(initial,0xffff_ff00).unwrap();
        let crossed=authenticated_rx_anchor(initial,first,0x200,1).unwrap();
        assert_eq!(crossed,0x1_0000_0100);
        assert_eq!(extend_seq32(crossed,0x100),Ok(crossed));
        let next=extend_seq32(crossed,0x100).unwrap();
        let ahead=authenticated_rx_anchor(crossed,next,0x180,1).unwrap();
        assert_eq!(ahead,0x1_0000_0280);
        // These exact same apparent seq32 bits must remain high-generation
        // candidates even after advancing >half-space beyond the old Go base.
        let far=0x1_8000_1000u64;
        assert!(far-initial>0x8000_0000);
        assert_ne!(extend_seq32(initial,far as u32),Ok(far));
        assert_eq!(extend_seq32(far,far as u32),Ok(far));
        // Untrusted and replay packets cannot poison the owner anchor.
        assert_eq!(authenticated_rx_anchor(ahead,far,512,0),Some(ahead));
        assert_eq!(authenticated_rx_anchor(ahead,far,512,2),Some(ahead));
        assert_eq!(authenticated_rx_anchor(ahead,ahead-128,64,1),Some(ahead));
        assert_eq!(authenticated_rx_anchor(ahead,u64::MAX,2,1),None);
        assert_eq!(extend_seq32(0,0x8000_0000),
            Err(wbd_platform::rx_ipv4_tcp::SeqExtendError::HalfSpaceAmbiguous));
    }
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    #[test]
    fn m0_link_materialization_never_admits_half_packet_on_arena_failure(){
        // Actual M1 unique loans + original M3 LINK20 planner. A synthetic
        // 1500B logical input needs THREE fixed-600B framed slabs.
        let original=(0..1500usize).map(|i|(i%251) as u8).collect::<Vec<_>>();
        let mut small=Arena::new(141,2,2048,2,16_000).unwrap();
        assert_eq!(stage_bounded_original_link(
            &mut small,&original,600,41,32).err(),Some(FULL));
        // Both preallocated loans were returned; zero actual owner seals or
        // AEAD packet-number commits could have occurred.
        small.drain_returns();
        assert_eq!(small.report().loaned,0);
        assert_eq!(stage_bounded_original_link(
            &mut small,&original,600,41,2).err(),Some(FULL));
        small.drain_returns();
        assert_eq!(small.report().loaned,0);

        let mut full=Arena::new(142,4,2048,4,32_000).unwrap();
        let staged=stage_bounded_original_link(
            &mut full,&original,600,41,3).unwrap();
        assert_eq!(staged.len(),3);
        assert_eq!(full.report().loaned,3);
        let parts=staged.iter().map(|(slot,n)|slot.origin()).collect::<Vec<_>>();
        assert_eq!(parts.len(),3);
        let mut table=Vec::new();
        for (mut slot,n) in staged{
            let bytes=slot.writable()[14..14+n].to_vec();
            assert!(matches!(
                wbd_codec::link_fec_wire::inspect_link(
                    &bytes,600,LinkMode::FixedOff
                ),
                Ok(wbd_codec::link_fec_wire::LinkView::Fragment(_))
            ));
            table.push(bytes);
        }
        assert_eq!(table.len(),3);
        for (index,wire) in table.iter().enumerate(){
            let wbd_codec::link_fec_wire::LinkView::Fragment(frag)=
                wbd_codec::link_fec_wire::inspect_link(
                    wire,600,LinkMode::FixedOff
                ).unwrap() else{panic!("not a LINK fragment")};
            assert_eq!(usize::from(frag.index),index);
            assert_eq!(usize::from(frag.count),3);
            assert_eq!(frag.packet_id,41);
        }
        full.drain_returns();
        assert_eq!(full.report().loaned,0);
        assert_eq!(stage_bounded_original_link(
            &mut full,&original,600,0,3).err(),Some(INVALID));
        assert_eq!(stage_bounded_original_link(
            &mut full,&original,20,41,3).err(),Some(INVALID));
        assert_eq!(full.report().loaned,0);
    }
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    #[test]
    fn r1_m0_original_data_return_budget_yields_at_64_128_33(){
        // Exactly the M1 owner slab and ReturnPath used in authenticated
        // real Linux data, not a synthetic stand-in or another lock.
        let mut arena=Arena::new(31,128,256,32,256_000).unwrap();
        let loans=(0..128).map(|_|arena.allocate().unwrap()).collect::<Vec<_>>();
        drop(loans); // mpsc(32) + bounded fallback; 128 real unique loans.
        assert_eq!(drain_data_turn_returns(&mut arena),64);
        assert_eq!(drain_data_turn_returns(&mut arena),64);
        assert_eq!(drain_data_turn_returns(&mut arena),0);
        assert_eq!(arena.report().loaned,0);
        let loans=(0..33).map(|_|arena.allocate().unwrap()).collect::<Vec<_>>();
        drop(loans);
        assert_eq!(drain_data_turn_returns(&mut arena),33);
        assert_eq!(drain_data_turn_returns(&mut arena),0);
        assert_eq!(arena.report().loaned,0);
        // Control / Stop still uses the full drain and retirement fence.
        let stopped=arena.stop();
        assert_eq!(stopped.loaned,0);
    }
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    #[test]
    fn m0_route_refresh_rearms_real_m4_only_after_change_or_invalidation(){
        assert!(!raw_driver_reopen_on_route_change(false,0,65536,65536));
        assert!(!raw_driver_reopen_on_route_change(true,3,65536,65536));
        assert!(!raw_driver_reopen_on_route_change(false,3,1500,65536));
        assert!(raw_driver_reopen_on_route_change(false,3,65536,65536));
        assert!(raw_driver_reopen_on_route_change(false,3,65536,1500));
        assert!(!raw_driver_reopen_on_route_change(false,3,65536,0));
    }
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    #[test]
    fn m0_tx_turn_completion_preserves_prefix_tail_and_typed_path(){
        use wbd_platform::linux_batch::{KernelSendSignal as S,KernelSendReport};
        use wbd_platform::{TxBatchOutcome,TxError};
        let full=KernelSendReport{outcome:TxBatchOutcome::copied_all(32),signal:S::None};
        assert_eq!(classify_tx_turn(Some(&full),32,false),
            TxTurnCompletion{copied:32,..Default::default()});
        assert_eq!(classify_tx_turn(Some(&KernelSendReport{outcome:TxBatchOutcome::copied_all(0),signal:S::None}),0,false),
            TxTurnCompletion::default());
        let examples=[
            (1,0,None,S::Backpressure,0,1,0,true,false),
            (32,5,None,S::PartialErrnoUnavailable,5,27,0,false,false),
            (33,32,None,S::Backpressure,32,1,0,true,false),
            (32,5,Some(5),S::AmbiguousCompletion,5,26,1,false,false),
            (32,7,None,S::MtuExceeded,7,25,0,false,true),
            (32,0,None,S::PreflightRejected,0,32,0,false,false),
            (32,0,None,S::DeviceUnavailable,0,32,0,false,true),
            (32,0,None,S::RouteUnavailable,0,32,0,false,true),
            (32,0,None,S::Stopping,0,32,0,false,false),
        ];
        for (total,prefix,unknown,signal,copied,dropped,uncertain,backpressure,invalidate) in examples {
            let report=KernelSendReport{
                outcome:TxBatchOutcome{accepted_prefix:prefix,
                    uncertain_index:unknown,error:Some(if unknown.is_some(){
                        TxError::IoUncertain
                    }else if backpressure{TxError::WouldBlock}else{TxError::IoFailed})},
                signal
            };
            let done=classify_tx_turn(Some(&report),total,false);
            assert_eq!((done.copied,done.definitely_unsent,done.uncertain,
                done.backpressure,done.invalidate_route),
                (copied,dropped,uncertain,backpressure,invalidate));
            assert!(done.failed);
            assert_eq!(done.copied+done.definitely_unsent+done.uncertain,total as u32);
        }
        assert!(classify_tx_turn(Some(&full),32,true).failed);
    }
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    #[test]
    fn m0_raw_original_owner_kernel_prefix_and_uncertain_never_conflate(){
        use wbd_platform::linux_batch::{KernelSendSignal,KernelSendReport};
        use wbd_platform::{TxBatchOutcome,TxError};
        let full=KernelSendReport{
            outcome:TxBatchOutcome::copied_all(1),
            signal:KernelSendSignal::None,
        };
        assert!(raw_one_packet_copied(&full));
        for (outcome,signal) in [
            (TxBatchOutcome{accepted_prefix:0,uncertain_index:None,
                error:Some(TxError::WouldBlock)},KernelSendSignal::Backpressure),
            (TxBatchOutcome{accepted_prefix:0,uncertain_index:None,
                error:Some(TxError::IoFailed)},KernelSendSignal::MtuExceeded),
            (TxBatchOutcome{accepted_prefix:0,uncertain_index:None,
                error:Some(TxError::IoFailed)},KernelSendSignal::DeviceUnavailable),
            (TxBatchOutcome{accepted_prefix:0,uncertain_index:Some(0),
                error:Some(TxError::IoUncertain)},KernelSendSignal::AmbiguousCompletion),
            (TxBatchOutcome{accepted_prefix:1,uncertain_index:None,
                error:Some(TxError::WouldBlock)},KernelSendSignal::None),
        ]{
            assert!(!raw_one_packet_copied(&KernelSendReport{outcome,signal}));
        }
    }
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
