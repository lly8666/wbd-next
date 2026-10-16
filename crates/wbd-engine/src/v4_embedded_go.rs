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
use wbd_codec::record_frame::FIXED_WIRE_OVERHEAD;
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
use wbd_platform::linux_raw_carrier::{ScopedRawIpv4Rx,ScopedRawIpv4Tx};
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
use wbd_platform::linux_tun_sink::ScopedTunSink;
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
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    workers:Option<LoopWorkers>,
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    counters:Arc<LoopCounts>,
    arena:Arena,phase:u32,
    rx_boundary:u32,wire_limit:u16,staged_count:u32,staged_bytes:u32,
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    flow:crate::v4_protected_handoff::GoFlow,
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    raw_rx:Option<Arc<ScopedRawIpv4Rx>>,
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    raw_tx:Option<ScopedRawIpv4Tx>,
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    tun_sink:Option<Arc<ScopedTunSink>>,
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
        workers:None,
        #[cfg(all(target_arch="x86_64",target_env="gnu"))]
        counters:Arc::new(LoopCounts::default()),
        #[cfg(all(target_arch="x86_64",target_env="gnu"))]
        raw_rx:None,
        #[cfg(all(target_arch="x86_64",target_env="gnu"))]
        raw_tx:None,
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
    // Leave registry unlocked while joining. Driver handles and owner slabs
    // cannot be released while either Rust worker still references them.
    #[cfg(all(target_arch="x86_64",target_env="gnu"))]
    {
        let workers={
            let Ok(mut reg)=registry().lock()else{return BAD_STAGE};
            let Some(e)=reg.entries.get_mut(&handle)else{return UNKNOWN};
            if e.phase!=PH_ACTIVE && e.phase!=PH_STOPPING && e.phase!=PH_STOPPED{
                return BAD_STAGE
            }
            let w=e.workers.take();
            if let Some(ref w)=w{w.shutdown.store(true,Ordering::Release)}
            w
        };
        if let Some(w)=workers{
            let rx=w.rx.join();
            let tx=w.tx.join();
            if rx.is_err()||tx.is_err(){return STOP_INCOMPLETE}
        }
    }
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
    e.raw_rx=Some(Arc::new(driver));OK
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
    e.tun_sink=Some(Arc::new(tun));OK
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


/// Reverse app path using SAME protected generation, non-_test normal Rust
/// LINK AEAD/PN, and real Linux M4 ScopedTunSink/ScopedRawIpv4Tx objects.
/// One trusted Go session tuple and original Tx boundary; never resynthesize
/// keys/seq/PN in the FFI or in Go. Driver is retained through Stop.
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn tun_to_raw(handle:u64,ifindex:u32)->Result<(u64,u32,u32,u32),i32>{
    let mut state=registry().lock().map_err(|_|BAD_STAGE)?;
    let e=state.entries.get_mut(&handle).ok_or(UNKNOWN)?;
    if e.phase!=PH_ACTIVE{return Err(BAD_STAGE)}
    let tun=e.tun_sink.as_ref().ok_or(BAD_STAGE)?;
    let flow=e.flow;
    if e.raw_tx.is_none(){
        let driver=ScopedRawIpv4Tx::open("lo",ifindex,(handle>>32) as u32)
            .map_err(|_|INVALID)?;
        e.raw_tx=Some(driver);
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
// Spurious irrelevant raw TCP traffic can still occupy recv_one_into for up
// to 750ms under the registry lock: this first functional worker is NOT yet
// an independently qualified 10Mbps dual-direction data plane.
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
#[repr(C)]
struct PollFd {fd:c_int,events:i16,revents:i16}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
unsafe extern "C" {fn poll(fds:*mut PollFd,count:usize,timeout:c_int)->c_int;}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
#[derive(Default)]
struct LoopCounts {
    rx:AtomicU64,tx:AtomicU64,rx_error:AtomicU64,tx_error:AtomicU64,
    rx_thread_cpu_ns:AtomicU64,tx_thread_cpu_ns:AtomicU64,
}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
struct LoopWorkers{
    shutdown:Arc<AtomicBool>,
    rx:JoinHandle<()>,
    tx:JoinHandle<()>,
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
// Do not hold global registry lock while M4 RX preflight ignores unrelated
// RST/ACK or polls for up to 750ms. M4 receives directly into the already
// allocated ORIGINAL M1 UniqueBuffer and validates exact trusted tuple and
// TCP checksum. On reentry the ONLY decrypt/PN/LINK/TUN path is the original
// Rust ScopedOwner. Stop joins worker before owner/slab/driver retirement.
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn background_raw_once(handle:u64,raw:&ScopedRawIpv4Rx,stop:&AtomicBool)->Result<u32,i32>{
    let (mut slab,flow,boundary,generation)={
        let mut state=registry().lock().map_err(|_|BAD_STAGE)?;
        let e=state.entries.get_mut(&handle).ok_or(UNKNOWN)?;
        if e.phase!=PH_ACTIVE{return Err(BAD_STAGE)}
        let slab=e.arena.allocate().map_err(|_|FULL)?;
        (slab,e.flow,e.rx_boundary,(handle>>32) as u32)
    };
    let tuple=Ipv4Tuple{
        src_ip:&flow.client_ip,dst_ip:&flow.server_ip,
        src_port:flow.client_port,dst_port:flow.server_port,
    };
    let (len,seq)=raw.recv_one_into(generation,slab.writable(),
        tuple,PacketPersona::Legacy).map_err(|_|INVALID)?;
    if stop.load(Ordering::Acquire){return Err(BAD_STAGE)}
    let absolute=extend_seq32(u64::from(boundary),seq).map_err(|_|INVALID)?;
    let mut state=registry().lock().map_err(|_|BAD_STAGE)?;
    let e=state.entries.get_mut(&handle).ok_or(UNKNOWN)?;
    if e.phase!=PH_ACTIVE||stop.load(Ordering::Acquire){return Err(BAD_STAGE)}
    e.owner.offer_after_active(slab,0..len,absolute,loop_now())
        .map_err(|_|INVALID)?;
    let tun=e.tun_sink.as_ref().ok_or(BAD_STAGE)?;
    let (loan,report,delivered,failed)=e.owner.drain_normal_off_to_tun(
        &mut e.normal,tun,loop_now(),Vec::with_capacity(32))
        .map_err(|_|BAD_STAGE)?;
    drop(loan);
    e.arena.drain_returns();
    if report.completed!=1||failed!=0||delivered!=1{return Err(INVALID)}
    Ok(delivered)
}
// Independently wait for the REAL TUN application RX OUTSIDE registry lock.
// Only original owner grants route-bound budget, seals AEAD/PN and submits
// original frozen M1 record through genuine scoped M4 raw TX.
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn background_tun_once(handle:u64,tun:&ScopedTunSink,
    stop:&AtomicBool,ifindex:u32)->Result<(),i32>{
    let (mut slab,generation)={
        let mut state=registry().lock().map_err(|_|BAD_STAGE)?;
        let e=state.entries.get_mut(&handle).ok_or(UNKNOWN)?;
        if e.phase!=PH_ACTIVE{return Err(BAD_STAGE)}
        let slab=e.arena.allocate().map_err(|_|FULL)?;
        (slab,(handle>>32) as u32)
    };
    let space=slab.writable().len().checked_sub(14).ok_or(INVALID)?;
    if space<20{return Err(INVALID)}
    let n=tun.read_ipv4_into(generation,&mut slab.writable()[14..])
        .map_err(|_|INVALID)?;
    if stop.load(Ordering::Acquire){return Err(BAD_STAGE)}
    let mut state=registry().lock().map_err(|_|BAD_STAGE)?;
    let e=state.entries.get_mut(&handle).ok_or(UNKNOWN)?;
    if e.phase!=PH_ACTIVE||stop.load(Ordering::Acquire){return Err(BAD_STAGE)}
    let flow=e.flow;
    let scoped=e.owner.observe_linux_normal_off_route_budget(
        "lo",ifindex,Ipv4Addr::from(flow.client_ip)).map_err(|_|INVALID)?;
    if n>scoped.frame.single_business_payload_mtu{return Err(INVALID)}
    e.owner.seal_normal_off_with_linux_budget(slab,n,&scoped,15,loop_now())
        .map_err(|_|INVALID)?;
    let raw=e.raw_tx.as_ref().ok_or(BAD_STAGE)?;
    let tuple=Ipv4Tuple{
        src_ip:&flow.server_ip,dst_ip:&flow.client_ip,
        src_port:flow.server_port,dst_port:flow.client_port,
    };
    let presentation=Presentation{
        ack32:1,advertised_window:4096,ip_id:43,
        persona:PacketPersona::Legacy,
    };
    e.owner.submit_scoped_raw_tx(raw,tuple,presentation,loop_now())
        .map_err(|_|BAD_STAGE)?;
    e.arena.drain_returns();
    Ok(())
}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn loop_readiness(fd:i32,stop:&AtomicBool)->bool{
    if stop.load(Ordering::Acquire){return false}
    let mut p=PollFd{fd,events:1,revents:0};
    // bounded responsiveness for Stop; no timed waiting under registry.
    let got=unsafe{poll(&mut p,1,10)};
    got>0 && p.revents&1!=0
}
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
fn start_loop(handle:u64,ifindex:u32)->i32{
    let Ok(mut reg)=registry().lock()else{return BAD_STAGE};
    let Some(e)=reg.entries.get_mut(&handle)else{return UNKNOWN};
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
        e.raw_tx=Some(tx);
    }
    let shutdown=Arc::new(AtomicBool::new(false));
    let stats=Arc::clone(&e.counters);
    let stop_rx=Arc::clone(&shutdown);
    let stats_rx=Arc::clone(&stats);
    let Ok(rx)=thread::Builder::new().name("wbd-original-m4-rx".into())
        .spawn(move||{
            let cpu_origin=owner_thread_cpu_ns();
            while !stop_rx.load(Ordering::Acquire){
                stats_rx.rx_thread_cpu_ns.store(
                    owner_thread_cpu_ns().saturating_sub(cpu_origin),Ordering::Relaxed);
                if !loop_readiness(raw_fd,&stop_rx){continue}
                if stop_rx.load(Ordering::Acquire){break}
                match background_raw_once(handle,&raw,&stop_rx){
                    Ok(n)=>{stats_rx.rx.fetch_add(u64::from(n),Ordering::Relaxed);}
                    Err(_)=>{stats_rx.rx_error.fetch_add(1,Ordering::Relaxed);}
                }
            }
        })
    else{return INVALID};
    let stop_tx=Arc::clone(&shutdown);
    let Ok(tx)=thread::Builder::new().name("wbd-original-m4-tx".into())
        .spawn(move||{
            let cpu_origin=owner_thread_cpu_ns();
            while !stop_tx.load(Ordering::Acquire){
                stats.tx_thread_cpu_ns.store(
                    owner_thread_cpu_ns().saturating_sub(cpu_origin),Ordering::Relaxed);
                if !loop_readiness(tun_fd,&stop_tx){continue}
                if stop_tx.load(Ordering::Acquire){break}
                match background_tun_once(handle,&tun,&stop_tx,ifindex){
                    Ok(_)=>{stats.tx.fetch_add(1,Ordering::Relaxed);}
                    Err(_)=>{stats.tx_error.fetch_add(1,Ordering::Relaxed);}
                }
            }
        })
    else{
        shutdown.store(true,Ordering::Release);
        drop(reg);
        let _=rx.join();
        return INVALID
    };
    e.workers=Some(LoopWorkers{shutdown,rx,tx});
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
    let Ok(reg)=registry().lock()else{return BAD_STAGE};
    let Some(e)=reg.entries.get(&h)else{return UNKNOWN};
    unsafe{
        rx.write(e.counters.rx.load(Ordering::Relaxed));
        tx.write(e.counters.tx.load(Ordering::Relaxed));
        rx_err.write(e.counters.rx_error.load(Ordering::Relaxed));
        tx_err.write(e.counters.tx_error.load(Ordering::Relaxed));
    }
    OK
}

// Developer-mode per-worker *actual Linux thread CPU time* for 10s+60s
// receipt. Combined process CPU includes Go sender/reader; independent
// exact user-vs-kernel attribution within that residual is NOT available.
#[cfg(all(target_arch="x86_64",target_env="gnu"))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_loop_thread_cpu(
    h:u64,rx_ns:*mut u64,tx_ns:*mut u64)->i32{
    if rx_ns.is_null()||tx_ns.is_null(){return INVALID}
    let Ok(reg)=registry().lock()else{return BAD_STAGE};
    let Some(e)=reg.entries.get(&h)else{return UNKNOWN};
    unsafe{
        rx_ns.write(e.counters.rx_thread_cpu_ns.load(Ordering::Relaxed));
        tx_ns.write(e.counters.tx_thread_cpu_ns.load(Ordering::Relaxed));
    }
    OK
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
