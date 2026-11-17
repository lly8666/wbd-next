//! ARM64 Bionic kernel I/O binding for the ORIGINAL protected Go V4 owner.
//! Uses the same Rust M1 FrozenRecord, M3 AEAD/unique PN, Normal/off LINK,
//! HealthClock and owned lease. No new crypto/TLS, Go per-packet path, VPN,
//! fake-IP, protocol, or silent fallback to Android's default Network.
//!
//! One bounded RX and one bounded TX readiness worker. Idle kernel poll is
//! interrupted by two owned eventfds at Stop. Entry's original M1/M3 owner
//! is synchronized for these small nonblocking turns; finer RX/TX ownership
//! splitting and full M3 jumbo/FEC scheduling are separate product gates.
#![cfg(all(target_os="android",target_arch="aarch64"))]
use super::{Entry,session,PH_ACTIVE,PH_STOPPING,OK,INVALID,UNKNOWN,BAD_STAGE,FULL};
use crate::v4_native_health::{AuthenticatedActivity,HealthClock,HealthPolicy,ControlDue};
use crate::runtime::{TxDispatch,RxPacket};
use wbd_types::buffer_contract::UniqueSealable;
use wbd_codec::link_fec_wire::{
    LinkPacketPlan,LinkMode,LINK_MAGIC,MAX_LOGICAL_DATAGRAM,
};
use wbd_platform::android_root_io::{
    AndroidBoundRawRx,AndroidBoundRawTx,AndroidOwnedTun,AndroidWorkerWake,
};
use wbd_platform::ipv4_tcp::{Ipv4Tuple,Presentation,PacketPersona};
use wbd_types::MonoNs;
use std::sync::{Arc,Mutex,OnceLock,atomic::{AtomicBool,AtomicU32,AtomicU64,Ordering}};
use std::thread::{self,JoinHandle};
use std::time::{Duration,Instant};

#[derive(Default)]
pub(super) struct AndroidOriginalStats{
    pub(super) rx:AtomicU64,pub(super) tx:AtomicU64,
    pub(super) rx_error:AtomicU64,pub(super) tx_error:AtomicU64,
    pub(super) raw_candidates:AtomicU64,pub(super) tx_dropped:AtomicU64,
    pub(super) authenticated_peer_dead:AtomicBool,
    pub(super) peer_preauth_due:AtomicBool,
    pub(super) peer_verified_health:AtomicBool,
    pub(super) scope_invalid:AtomicBool,
    // Read from each true Bionic worker's CLOCK_THREAD_CPUTIME_ID;
    // reported as actual kernel thread CPU, never wall time or a guess.
    rx_cpu_ns:AtomicU64,tx_cpu_ns:AtomicU64,
    ip_id:AtomicU32,
}
pub(super) struct AndroidOriginalWorkers{
    shutdown:Arc<AtomicBool>,
    wake_rx:Arc<AndroidWorkerWake>,wake_tx:Arc<AndroidWorkerWake>,
    rx:JoinHandle<()>,tx:JoinHandle<()>,
}
impl AndroidOriginalWorkers{
    /// Join ALL actual kernel-readiness threads before shared Rust M1/M3
    /// owner Stop or any borrowed RAW/TUN descriptor is retired.
    pub(super) fn stop_and_join(self)->bool{
        self.shutdown.store(true,Ordering::Release);
        let w1=self.wake_rx.signal_stop().is_ok();
        let w2=self.wake_tx.signal_stop().is_ok();
        let rx=self.rx.join().is_ok();
        let tx=self.tx.join().is_ok();
        w1&&w2&&rx&&tx
    }
}
const CLOCK_THREAD_CPUTIME_ID:i32=3;
#[repr(C)]
struct AndroidThreadCpuTime{sec:i64,nsec:i64}
unsafe extern "C"{
    fn clock_gettime(clock_id:i32,out:*mut AndroidThreadCpuTime)->i32;
}
fn thread_cpu_ns()->u64{
    let mut t=AndroidThreadCpuTime{sec:0,nsec:0};
    if unsafe{clock_gettime(CLOCK_THREAD_CPUTIME_ID,&mut t)}!=0 ||
       t.sec<0||!(0..1_000_000_000).contains(&t.nsec){
        return 0
    }
    (t.sec as u64).saturating_mul(1_000_000_000)
        .saturating_add(t.nsec as u64)
}
fn now()->MonoNs{
    static BOOT:OnceLock<Instant>=OnceLock::new();
    let origin=BOOT.get_or_init(Instant::now);
    MonoNs(u64::try_from(origin.elapsed().as_nanos()).unwrap_or(u64::MAX))
}
fn presentation(e:&Entry,stats:&AndroidOriginalStats)->Presentation{
    Presentation{
        ack32:e.android_seq_anchor as u32,
        advertised_window:4096,
        ip_id:stats.ip_id.fetch_add(1,Ordering::Relaxed) as u16,
        persona:PacketPersona::Legacy,
    }
}
fn send_staged(
    e:&mut Entry,raw:&AndroidBoundRawTx,stats:&AndroidOriginalStats,
    storage:&mut Vec<TxDispatch>,scratch:&mut [u8],at:MonoNs,
)->Option<u64>{
    let f=e.flow;
    let tuple=Ipv4Tuple{
        src_ip:&f.client_ip,dst_ip:&f.server_ip,
        src_port:f.client_port,dst_port:f.server_port,
    };
    let p=presentation(e,stats);
    let mtu=match e.android_physical.as_ref(){Some(x)=>x.mtu,None=>return None};
    let result=e.owner.submit_android_raw_ready(
        raw,tuple,p,mtu,at,storage,scratch
    );
    e.arena.drain_returns();
    match result{
        Ok((n,pn)) if n>0=>{
            stats.tx.fetch_add(1,Ordering::Relaxed);
            Some(pn)
        },
        _=>{
            stats.tx_error.fetch_add(1,Ordering::Relaxed);
            stats.tx_dropped.fetch_add(1,Ordering::Relaxed);
            None
        },
    }
}
fn send_authenticated_health(
    e:&mut Entry,raw:&AndroidBoundRawTx,stats:&AndroidOriginalStats,
    storage:&mut Vec<TxDispatch>,scratch:&mut [u8],at:MonoNs,idle_ns:u64,
)->bool{
    let physical=match e.android_physical.as_ref(){Some(x)=>x.mtu,None=>return false};
    let frame=match e.owner.android_normal_off_frame_budget(physical){
        Ok(v)=>v,Err(_)=>return false,
    };
    let limit=frame.record_payload_mtu.min(512);
    let bytes=match crate::v4_native_health::encode_authenticated_health_live(
        idle_ns,None,None,limit
    ){
        Ok(b)=>b,Err(_)=>return false,
    };
    let slab=match e.arena.allocate(){
        Ok(b)=>b,Err(_)=>return false,
    };
    let pn=match e.owner.seal_original_authenticated_receipt(
        slab,&bytes,frame,u64::from(physical),at
    ){
        Ok((pn,_,_))=>pn,
        Err(_)=>{
            e.arena.drain_returns();
            return false
        },
    };
    // A successful kernel copy of some OTHER queued record must never
    // postpone this authenticated HealthClock. Match the original PN.
    send_staged(e,raw,stats,storage,scratch,at)==Some(pn)
}
fn raw_worker(
    cell:Arc<Mutex<Entry>>,shutdown:Arc<AtomicBool>,
    wake:Arc<AndroidWorkerWake>,raw:Arc<AndroidBoundRawRx>,
    tun:Arc<AndroidOwnedTun>,stats:Arc<AndroidOriginalStats>,
    activity:Arc<AuthenticatedActivity>,peer_wake:Arc<AndroidWorkerWake>,
){
    // ONE original-generation M1 slab per kernel read; retain the same
    // one-slot vector across packets, never allocate a Vec in the RX hot path.
    let mut rx_storage:Vec<RxPacket>=Vec::with_capacity(1);
    while !shutdown.load(Ordering::Acquire){
        stats.rx_cpu_ns.store(thread_cpu_ns(),Ordering::Relaxed);
        let ready=wake.wait_readable(raw.readiness_fd(),30_000);
        if shutdown.load(Ordering::Acquire){break}
        let Ok(true)=ready else{
            if ready.is_err(){
                stats.scope_invalid.store(true,Ordering::Release);
                shutdown.store(true,Ordering::Release);
                break
            }
            continue
        };
        for turn in 0..8 {
            if shutdown.load(Ordering::Acquire){break}
            if turn>0&&!wake.wait_readable(raw.readiness_fd(),0).unwrap_or(false){
                break
            }
            let (auth_ns,business_ns,hint,retired,healthy)={
                let Ok(mut e)=cell.lock()else{
                    shutdown.store(true,Ordering::Release);break
                };
                if e.phase!=PH_ACTIVE {break}
                let slab=match e.arena.allocate(){Ok(x)=>x,Err(_)=>break};
                let f=e.flow;
                let tuple=Ipv4Tuple{
                    src_ip:&f.server_ip,dst_ip:&f.client_ip,
                    src_port:f.server_port,dst_port:f.client_port,
                };
                let at=now();
                let anchor=e.android_seq_anchor;
                let read=e.owner.receive_android_raw_into_owner(
                    &raw,slab,tuple,PacketPersona::Legacy,anchor,at
                );
                let (wire_len,absolute)=match read{
                    Ok(v)=>v,
                    Err(_)=>{
                        stats.rx_error.fetch_add(1,Ordering::Relaxed);
                        e.arena.drain_returns();
                        break
                    },
                };
                stats.raw_candidates.fetch_add(1,Ordering::Relaxed);
                let lease=e.client_lease_ipv4;
                let (report,delivered,failed,healthy,hint,retired)={
                    let Entry{owner,normal,..}=&mut *e;
                    let Some(reassembly)=normal.as_mut()else{break};
                    match owner.drain_android_normal_off_to_tun(
                        reassembly,&tun,lease,at,
                        std::mem::take(&mut rx_storage),
                    ){
                        Ok((returned,report,delivered,failed,healthy,hint,retired))=>{
                            rx_storage=returned;
                            (report,delivered,failed,healthy,hint,retired)
                        },
                        Err((_,returned))=>{
                            rx_storage=returned;
                            stats.rx_error.fetch_add(1,Ordering::Relaxed);
                            break
                        }
                    }
                };
                e.arena.drain_returns();
                stats.rx.fetch_add(u64::from(delivered),Ordering::Relaxed);
                stats.rx_error.fetch_add(
                    u64::from(failed)+u64::from(report.malformed)+
                    u64::from(report.discarded)+u64::from(report.authenticated.rejected),
                    Ordering::Relaxed
                );
                let authenticated=report.authenticated.link_ready!=0||healthy;
                if authenticated{
                    e.android_seq_anchor=e.android_seq_anchor.max(
                        absolute.saturating_add(wire_len as u64));
                }
                (
                    if authenticated{at.0}else{0},
                    if delivered>0{at.0}else{0},
                    hint.map(|ns|(at.0,ns)),retired,healthy,
                )
            };
            if auth_ns!=0{
                activity.record_batch(auth_ns,business_ns,hint);
                if healthy {stats.peer_verified_health.store(true,Ordering::Release);}
                if retired {activity.record_peer_retire(auth_ns);}
            }
        }
    }
    stats.rx_cpu_ns.store(thread_cpu_ns(),Ordering::Relaxed);
    if shutdown.load(Ordering::Acquire){
        let _=peer_wake.signal_stop();
    }
}
/// One authenticated logical IPv4 datagram, one fixed original M3
/// LINK20 packet ID and frame stride. Original M1 issues each PN exactly
/// once; a changed scope or uncertain kernel copy RETIRES its remaining
/// tail. Owned only by TX worker, never visible to Go/JNI.
struct PendingAndroidJumbo{
    source:Vec<u8>,packet_id:u32,frame_mtu:usize,
    issued:usize,total:usize,generation:u32,physical_mtu:u32,
}
enum JumboTurn{Copied{done:bool},Deferred,Abandoned}
fn send_android_jumbo_one(
    e:&mut Entry,plan:&mut PendingAndroidJumbo,
    raw:&AndroidBoundRawTx,stats:&AndroidOriginalStats,
    dispatch:&mut Vec<TxDispatch>,wire_scratch:&mut [u8],
    at:MonoNs,
)->JumboTurn{
    let Some(scope)=e.android_physical.as_ref()else{return JumboTurn::Abandoned};
    if e.phase!=PH_ACTIVE||e.generation!=plan.generation||
       scope.mtu!=plan.physical_mtu||plan.issued>=plan.total{
        return JumboTurn::Abandoned
    }
    let Ok(frame)=e.owner.android_normal_off_frame_budget(scope.mtu)
        else{return JumboTurn::Abandoned};
    if frame.link_frame_mtu!=plan.frame_mtu{return JumboTurn::Abandoned}
    // Reserve original M1 ownership BEFORE constructing the next unique
    // fragment. Capacity pressure defers without spending a PN or ID.
    let mut slab=match e.arena.allocate(){
        Ok(x)=>x,
        Err(wbd_types::buffer_contract::BufferContractError::NoCapacity)=>
            return JumboTurn::Deferred,
        Err(_)=>return JumboTurn::Abandoned,
    };
    let Some(cap)=slab.writable().len().checked_sub(14)
        else{return JumboTurn::Abandoned};
    let mut m3=match LinkPacketPlan::new(
        &plan.source,plan.frame_mtu,LinkMode::FixedOff,plan.packet_id
    ){
        Ok(v)=>v,Err(_)=>return JumboTurn::Abandoned,
    };
    if m3.resume_issued(plan.issued).is_err(){
        return JumboTurn::Abandoned
    }
    let max_payload=cap.min(frame.single_business_payload_mtu);
    let emitted=match m3.issue_next_into(
        frame.link_frame_mtu,&mut slab.writable()[14..14+max_payload]
    ){
        Ok(Some(bytes))=>bytes,
        _=>return JumboTurn::Abandoned,
    };
    // The codec emitted exact original LINK20, not a local packet format.
    // Original owner seals AEAD+PN+TCP Seq once into one FrozenRecord.
    let (pn,_,_)=match e.owner.seal_normal_off_fragment_one(
        slab,emitted,frame,u64::from(scope.mtu),at
    ){
        Ok(v)=>v,Err(_)=>return JumboTurn::Abandoned,
    };
    if send_staged(e,raw,stats,dispatch,wire_scratch,at)!=Some(pn){
        return JumboTurn::Abandoned
    }
    plan.issued=m3.issued();
    JumboTurn::Copied{done:plan.issued==plan.total}
}
fn original_complete_ipv4_head(
    head:&[u8],total:usize,lease:[u8;4],
)->bool{
    head.len()>=20&&total>=20&&total<=MAX_LOGICAL_DATAGRAM&&
    head[0]>>4==4&&
    usize::from(head[0]&15)*4>=20&&
    usize::from(head[0]&15)*4<=head.len()&&
    usize::from(u16::from_be_bytes([head[2],head[3]]))==total&&
    crate::v4_session_address::admitted_client_source(head,Some(lease))
}

fn tun_worker(
    cell:Arc<Mutex<Entry>>,shutdown:Arc<AtomicBool>,
    wake:Arc<AndroidWorkerWake>,tun:Arc<AndroidOwnedTun>,
    raw:Arc<AndroidBoundRawTx>,stats:Arc<AndroidOriginalStats>,
    activity:Arc<AuthenticatedActivity>,policy:HealthPolicy,
    peer_wake:Arc<AndroidWorkerWake>
){
    let mut clock=HealthClock::new(policy,now().0);
    clock.arm_client_cold_ready(now().0);
    let mut storage:Vec<TxDispatch>=Vec::with_capacity(1);
    let mut wire_scratch=vec![0u8;65_535];
    // One reusable 65KiB overflow iovec and one reusable jumbo source.
    // Common small packets go directly kernel -> M1 slab, with ZERO copy.
    let mut overflow=vec![0u8;MAX_LOGICAL_DATAGRAM];
    let mut jumbo_spare=Vec::<u8>::with_capacity(MAX_LOGICAL_DATAGRAM);
    let mut pending=None::<PendingAndroidJumbo>;
    let mut next_packet_id=1u32;
    let mut last_scope=Instant::now()-Duration::from_secs(2);
    while !shutdown.load(Ordering::Acquire){
        stats.tx_cpu_ns.store(thread_cpu_ns(),Ordering::Relaxed);
        let at=now();
        activity.absorb(&mut clock);
        if clock.preterminal_cold_reauth_due(at.0){
            stats.peer_preauth_due.store(true,Ordering::Release);
        }
        if clock.unhealthy(at.0){
            stats.authenticated_peer_dead.store(true,Ordering::Release);
            shutdown.store(true,Ordering::Release);
            break
        }
        // Exactly the previously selected physical Network. Revalidation
        // is low frequency (1Hz), and loss of scope is terminal, not a
        // fallback to Android's global/default route.
        if last_scope.elapsed()>=Duration::from_secs(1){
            let bound=match cell.lock(){
                Ok(e)=>e.android_physical.as_ref().is_some_and(|scope|
                    raw.check_scope(&scope.interface,scope.ifindex).is_ok()),
                Err(_)=>false,
            };
            if !bound{
                stats.scope_invalid.store(true,Ordering::Release);
                shutdown.store(true,Ordering::Release);
                break
            }
            last_scope=Instant::now();
        }
        if matches!(clock.control_due(at.0),ControlDue::Health){
            let copied=match cell.lock(){
                Ok(mut e) if e.phase==PH_ACTIVE=>send_authenticated_health(
                    &mut e,&raw,&stats,&mut storage,&mut wire_scratch,at,
                    clock.local_idle_ns(at.0)
                ),
                _=>false,
            };
            clock.on_health_send_result(at.0,copied);
        }
        if shutdown.load(Ordering::Acquire){break}

        // Fragment work owns the logical IP packet until all original
        // M3 frames are definitely kernel copied. No fresh TUN read, no
        // interleaved packet IDs, and at most eight sends before Health.
        if pending.is_some(){
            let mut retire=false;
            let mut deferred=false;
            for _ in 0..8{
                if shutdown.load(Ordering::Acquire){break}
                let Ok(mut e)=cell.lock()else{
                    shutdown.store(true,Ordering::Release);break
                };
                if e.phase!=PH_ACTIVE{retire=true;break}
                let at=now();
                let outcome=send_android_jumbo_one(
                    &mut e,pending.as_mut().expect("owned pending"),
                    &raw,&stats,&mut storage,&mut wire_scratch,at,
                );
                match outcome{
                    JumboTurn::Copied{done}=>{
                        clock.on_local_business(at.0);
                        if done{retire=true;break}
                    },
                    JumboTurn::Deferred=>{deferred=true;break},
                    JumboTurn::Abandoned=>{
                        stats.tx_error.fetch_add(1,Ordering::Relaxed);
                        stats.tx_dropped.fetch_add(1,Ordering::Relaxed);
                        retire=true;
                        break
                    },
                }
            }
            if retire{
                if let Some(mut finished)=pending.take(){
                    // Reuse the same bounded jumbo source storage next time;
                    // retired fragments/IDs are never republished.
                    finished.source.clear();
                    jumbo_spare=finished.source;
                }
            }else if deferred && !shutdown.load(Ordering::Acquire){
                thread::sleep(Duration::from_millis(1));
            }
            continue
        }

        let at=now();
        let due=clock.next_deadline()
            .unwrap_or(at.0.saturating_add(30_000_000_000));
        let timeout=((due.saturating_sub(at.0)+999_999)/1_000_000)
            .min(1_000).max(1) as i32;
        let ready=wake.wait_readable(tun.readiness_fd(),timeout);
        if shutdown.load(Ordering::Acquire){break}
        let Ok(true)=ready else{
            if ready.is_err(){
                stats.scope_invalid.store(true,Ordering::Release);
                shutdown.store(true,Ordering::Release);
                break
            }
            continue
        };
        // One sparse normal packet is sent immediately, never held waiting
        // for batch fill. Eight bounded source turns before Health/Stop.
        for turn in 0..8{
            if shutdown.load(Ordering::Acquire){break}
            if turn>0&&!wake.wait_readable(tun.readiness_fd(),0)
                .unwrap_or(false){break}
            let Ok(mut e)=cell.lock()else{
                shutdown.store(true,Ordering::Release);break
            };
            if e.phase!=PH_ACTIVE{break}
            let Some(physical)=e.android_physical.as_ref().map(|s|s.mtu)
                else{break};
            let Some(lease)=e.client_lease_ipv4 else{
                stats.tx_error.fetch_add(1,Ordering::Relaxed);
                shutdown.store(true,Ordering::Release);
                break
            };
            let frame=match e.owner.android_normal_off_frame_budget(physical){
                Ok(x)=>x,Err(_)=>{
                    stats.tx_error.fetch_add(1,Ordering::Relaxed);break
                },
            };
            // Reserve ONE original M1 loan BEFORE consuming the TUN packet.
            let mut slab=match e.arena.allocate(){
                Ok(v)=>v,Err(_)=>break
            };
            let head_cap=frame.single_business_payload_mtu.min(
                slab.writable().len().saturating_sub(14));
            if head_cap<20||head_cap>MAX_LOGICAL_DATAGRAM{
                stats.tx_error.fetch_add(1,Ordering::Relaxed);
                break
            }
            // Linux TUN read() with a small buffer DESTROYS oversized IP.
            // Two kernel iovecs preserve the entire datagram in one syscall.
            // Normal IP: kernel writes directly into the SAME original M1
            // slab [14..] and no user-space memcpy or per-packet Vec occurs.
            let read=tun.read_ip_scatter(
                &mut slab.writable()[14..14+head_cap],
                &mut overflow[..MAX_LOGICAL_DATAGRAM-head_cap],
            );
            let n=match read{
                Ok(x)=>x,
                Err(_)=>{
                    stats.tx_error.fetch_add(1,Ordering::Relaxed);
                    e.arena.drain_returns();
                    break
                }
            };
            let head_len=n.min(head_cap);
            let head=&slab.writable()[14..14+head_len];
            if !original_complete_ipv4_head(head,n,lease){
                e.arena.drain_returns();
                stats.tx_error.fetch_add(1,Ordering::Relaxed);
                stats.tx_dropped.fetch_add(1,Ordering::Relaxed);
                break
            }
            let escaped=head.starts_with(LINK_MAGIC);
            let at=now();
            if n<=head_cap&&!escaped{
                // Common O(1) hot path: original owner AEAD/PN directly
                // over the kernel-filled slab, immutable M4 RAW sendto.
                match e.owner.seal_android_read_normal_ip(
                    &tun,slab,n,frame,u64::from(physical),Some(lease),at
                ){
                    Ok((pn,_,_,_))=>{
                        if send_staged(
                            &mut e,&raw,&stats,&mut storage,
                            &mut wire_scratch,at
                        )==Some(pn){
                            clock.on_local_business(at.0);
                        }
                    },
                    Err(_)=>{
                        e.arena.drain_returns();
                        stats.tx_error.fetch_add(1,Ordering::Relaxed);
                        stats.tx_dropped.fetch_add(1,Ordering::Relaxed);
                        break
                    },
                }
                continue
            }

            // Jumbo or LINK-magic escape is RARE. Copy into one reusable
            // 65KiB buffer, then the ORIGINAL pure M3 LINK20 planner
            // stages bounded fragments into subsequent original M1 loans.
            jumbo_spare.clear();
            jumbo_spare.extend_from_slice(head);
            if n>head_cap{
                jumbo_spare.extend_from_slice(&overflow[..n-head_cap]);
            }
            if jumbo_spare.len()!=n{
                stats.tx_dropped.fetch_add(1,Ordering::Relaxed);
                break
            }
            let Some(packet_id_after)=next_packet_id.checked_add(1)else{
                // A same-generation u32 packet ID must never wrap/reuse.
                stats.tx_error.fetch_add(1,Ordering::Relaxed);
                shutdown.store(true,Ordering::Release);
                break
            };
            let m3=match LinkPacketPlan::new(
                &jumbo_spare,frame.link_frame_mtu,
                LinkMode::FixedOff,next_packet_id,
            ){
                Ok(v)=>v,Err(_)=>{
                    stats.tx_error.fetch_add(1,Ordering::Relaxed);
                    stats.tx_dropped.fetch_add(1,Ordering::Relaxed);
                    break
                },
            };
            let total_frames=m3.total_frames();
            if total_frames==0||total_frames>256{
                stats.tx_dropped.fetch_add(1,Ordering::Relaxed);
                break
            }
            drop(m3); // end immutable borrow before moving source ownership
            let packet_id=next_packet_id;
            next_packet_id=packet_id_after;
            pending=Some(PendingAndroidJumbo{
                source:std::mem::take(&mut jumbo_spare),
                packet_id,frame_mtu:frame.link_frame_mtu,
                issued:0,total:total_frames,
                generation:e.generation,physical_mtu:physical,
            });
            // No second TUN read until this logical datagram is complete
            // or retired. Return the unused original slab before fragments.
            drop(slab);
            e.arena.drain_returns();
            break
        }
    }
    clock.stopped();
    stats.tx_cpu_ns.store(thread_cpu_ns(),Ordering::Relaxed);
    if shutdown.load(Ordering::Acquire){
        let _=peer_wake.signal_stop();
    }
}
pub(super) fn start(handle:u64,ifindex:u32)->i32{
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.server_side||e.android_workers.is_some()||
       e.android_joining||e.client_lease_ipv4.is_none()||
       e.protected_features!=3||
       e.android_physical.as_ref().is_none_or(|p|p.ifindex!=ifindex)||
       e.normal.is_none(){
        return BAD_STAGE
    }
    let (Some(rx),Some(tx),Some(tun))=(
        e.android_raw_rx.as_ref(),e.android_raw_tx.as_ref(),e.android_tun.as_ref()
    )else{return BAD_STAGE};
    let rx=Arc::clone(rx);let tx=Arc::clone(tx);let tun=Arc::clone(tun);
    let Some(scope)=e.android_physical.as_ref()else{return BAD_STAGE};
    if tx.check_scope(&scope.interface,ifindex).is_err()||
       e.owner.android_normal_off_frame_budget(scope.mtu).is_err(){
        return INVALID
    }
    let rx_wake=match AndroidWorkerWake::new(){Ok(v)=>Arc::new(v),Err(_)=>return INVALID};
    let tx_wake=match AndroidWorkerWake::new(){Ok(v)=>Arc::new(v),Err(_)=>return INVALID};
    let activity=Arc::new(AuthenticatedActivity::default());
    let shutdown=Arc::new(AtomicBool::new(false));
    let counters=Arc::clone(&e.android_metrics);
    #[cfg(feature="fec2_product_record")]
    let policy=e.native_health_policy;
    #[cfg(not(feature="fec2_product_record"))]
    let policy=HealthPolicy::default_connected();
    // Preserve authentic early original Go bootstrap DATA before the M4
    // worker starts. Untrusted early bytes still go through original AEAD.
    if e.staged_count>0 {
        let lease=e.client_lease_ipv4;
        let at=now();
        let drained={
            let Entry{owner,normal,..}=&mut *e;
            owner.drain_android_normal_off_to_tun(
                normal.as_mut().unwrap(),&tun,lease,at,Vec::with_capacity(32)
            )
        };
        match drained{
            Ok((returned,report,delivered,failed,healthy,hint,retire))=>{
                drop(returned);
                e.arena.drain_returns();
                let accepted=report.authenticated.link_ready!=0||healthy;
                if accepted{
                    activity.record_batch(at.0,if delivered>0{at.0}else{0},
                        hint.map(|v|(at.0,v)));
                    if healthy{counters.peer_verified_health.store(true,Ordering::Release)}
                    if retire{activity.record_peer_retire(at.0)}
                }
                counters.rx.fetch_add(u64::from(delivered),Ordering::Relaxed);
                counters.rx_error.fetch_add(u64::from(failed),Ordering::Relaxed);
            },
            Err((_,returned))=>{drop(returned);return INVALID},
        }
    }
    let rx_cell=Arc::clone(&cell);
    let rx_shutdown=Arc::clone(&shutdown);
    let rx_event=Arc::clone(&rx_wake);
    let rx_tun=Arc::clone(&tun);
    let rx_stats=Arc::clone(&counters);
    let rx_activity=Arc::clone(&activity);
    let rx_peer=Arc::clone(&tx_wake);
    let rx_handle=match thread::Builder::new().name("wbd-arm64-original-rx".into())
        .spawn(move||raw_worker(
            rx_cell,rx_shutdown,rx_event,rx,rx_tun,rx_stats,rx_activity,rx_peer
        )){
        Ok(v)=>v,Err(_)=>return FULL,
    };
    let tx_cell=Arc::clone(&cell);
    let tx_shutdown=Arc::clone(&shutdown);
    let tx_event=Arc::clone(&tx_wake);
    let tx_stats=Arc::clone(&counters);
    let tx_peer=Arc::clone(&rx_wake);
    let tx_handle=match thread::Builder::new().name("wbd-arm64-original-tx".into())
        .spawn(move||tun_worker(
            tx_cell,tx_shutdown,tx_event,tun,tx,tx_stats,activity,policy,tx_peer
        )){
        Ok(v)=>v,
        Err(_)=>{
            shutdown.store(true,Ordering::Release);
            let _=rx_wake.signal_stop();
            e.phase=PH_STOPPING;
            drop(e);
            let _=rx_handle.join();
            return FULL
        },
    };
    e.android_workers=Some(AndroidOriginalWorkers{
        shutdown,wake_rx:rx_wake,wake_tx:tx_wake,rx:rx_handle,tx:tx_handle
    });
    OK
}
#[no_mangle]
pub extern "C" fn wbd_m0_embedded_go_loop_start(h:u64,ifindex:u32)->i32{
    start(h,ifindex)
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_loop_stats(
    h:u64,rx:*mut u64,tx:*mut u64,rx_err:*mut u64,tx_err:*mut u64
)->i32{
    if rx.is_null()||tx.is_null()||rx_err.is_null()||tx_err.is_null(){return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.android_workers.is_none(){return BAD_STAGE}
    let c=&e.android_metrics;
    unsafe{
        rx.write(c.rx.load(Ordering::Relaxed));
        tx.write(c.tx.load(Ordering::Relaxed));
        rx_err.write(c.rx_error.load(Ordering::Relaxed));
        tx_err.write(c.tx_error.load(Ordering::Relaxed));
    }
    OK
}
/// Authentic Bionic thread CPU time, bounded readback only. No JNI,
/// synthetic CPU estimate, wall-clock duty-cycle or per-record callbacks.
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_loop_thread_cpu(
    h:u64,rx_ns:*mut u64,tx_ns:*mut u64,
)->i32{
    if rx_ns.is_null()||tx_ns.is_null(){return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.android_workers.is_none(){return BAD_STAGE}
    unsafe{
        rx_ns.write(e.android_metrics.rx_cpu_ns.load(Ordering::Relaxed));
        tx_ns.write(e.android_metrics.tx_cpu_ns.load(Ordering::Relaxed));
    }
    OK
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_loop_authenticated_dead(
    h:u64,dead:*mut u32
)->i32{
    if dead.is_null(){return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.android_workers.is_none(){return BAD_STAGE}
    unsafe{dead.write(u32::from(e.android_metrics.authenticated_peer_dead.load(Ordering::Acquire)))};
    OK
}
#[no_mangle]
pub extern "C" fn wbd_m0_embedded_go_loop_authenticated_peer_predead(
    h:u64,predead:*mut u32
)->i32{
    if predead.is_null(){return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.android_workers.is_none(){return BAD_STAGE}
    unsafe{predead.write(u32::from(e.android_metrics.peer_preauth_due.load(Ordering::Acquire)))};
    OK
}
#[no_mangle]
pub extern "C" fn wbd_m0_embedded_go_loop_authenticated_peer_health(
    h:u64,health:*mut u32
)->i32{
    if health.is_null(){return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.android_workers.is_none(){return BAD_STAGE}
    unsafe{health.write(u32::from(e.android_metrics.peer_verified_health.load(Ordering::Acquire)))};
    OK
}
#[cfg(feature="fec2_product_record")]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_public_native_health_config(
    h:u64,epoch_ptr:*const u8,epoch_len:usize,
    keepalive_seconds:u32,dead_seconds:u32,dormant_seconds:u32
)->i32{
    if epoch_ptr.is_null()||epoch_len!=16{return INVALID}
    let epoch=unsafe{std::slice::from_raw_parts(epoch_ptr,epoch_len)};
    let Some(policy)=HealthPolicy::new(
        u64::from(keepalive_seconds)*1_000_000_000,
        u64::from(dead_seconds)*1_000_000_000,
        (dormant_seconds!=0).then_some(u64::from(dormant_seconds)*1_000_000_000)
    )else{return INVALID};
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.android_workers.is_some()||
       e.owner.normal_firstsend_identity().is_none_or(|(_,exact)|exact.as_slice()!=epoch)||
       e.android_raw_rx.is_none()||e.android_tun.is_none(){return BAD_STAGE}
    e.native_health_policy=policy;
    OK
}
#[cfg(feature="fec2_product_record")]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_public_native_health_effective(
    h:u64,epoch_ptr:*const u8,epoch_len:usize,out:*mut u32,count:usize
)->i32{
    if out.is_null()||epoch_ptr.is_null()||epoch_len!=16||count!=3{return INVALID}
    let epoch=unsafe{std::slice::from_raw_parts(epoch_ptr,epoch_len)};
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||
       e.owner.normal_firstsend_identity().is_none_or(|(_,exact)|exact.as_slice()!=epoch){
        return BAD_STAGE
    }
    let p=e.native_health_policy;
    unsafe{
        out.write((p.interval_ns()/1_000_000_000) as u32);
        out.add(1).write((p.dead_ns()/1_000_000_000) as u32);
        out.add(2).write(p.dormant_ns().map_or(0,|x|(x/1_000_000_000) as u32));
    }
    OK
}

// Same original-Go authenticated epoch/revision Normal/off approval used
// by its existing Linux native control bridge, implemented on the original
// Android Entry. This is NOT a missing-FEC/Game ABI stand-in: it strictly
// limits grants to real TLS feature3 and publishes only an OFF revision.
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_normal_off_stage(
    h:u64,epoch_ptr:*const u8,epoch_len:usize,revision:u64
)->i32{
    if epoch_ptr.is_null()||epoch_len!=16||revision==0{return INVALID}
    let epoch=unsafe{std::slice::from_raw_parts(epoch_ptr,16)};
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.android_joining||e.protected_features!=3||
       e.owner.normal_firstsend_identity().is_none_or(
           |(_,exact)|exact.as_slice()!=epoch
       ){return BAD_STAGE}
    if revision<=e.android_off_applied_revision{return INVALID}
    e.android_off_applied_revision=revision;
    OK
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_normal_off_readback(
    h:u64,epoch_ptr:*const u8,epoch_len:usize,out:*mut u64
)->i32{
    if epoch_ptr.is_null()||epoch_len!=16||out.is_null(){return INVALID}
    let epoch=unsafe{std::slice::from_raw_parts(epoch_ptr,16)};
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.android_joining||e.protected_features!=3||
       e.owner.normal_firstsend_identity().is_none_or(
           |(_,exact)|exact.as_slice()!=epoch
       ){return BAD_STAGE}
    unsafe{out.write(e.android_off_applied_revision)};
    OK
}
