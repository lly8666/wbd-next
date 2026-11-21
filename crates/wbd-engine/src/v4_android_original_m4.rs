//! ARM64 Bionic kernel I/O binding for the ORIGINAL protected Go V4 owner.
//! Uses the same Rust M1 FrozenRecord, M3 AEAD/unique PN, Normal/off LINK,
//! HealthClock and owned lease. No new crypto/TLS, Go per-packet path, VPN,
//! fake-IP, protocol, or silent fallback to Android's default Network.
//!
//! One bounded RX and one bounded TX readiness worker. Idle kernel poll is
//! interrupted by two owned eventfds at Stop. Entry's original M1/M3 owner
//! is synchronized for these small nonblocking turns; finer RX/TX ownership
//! splitting and full M3 jumbo/FEC scheduling are separate product gates.
#![cfg(all(target_os="android",any(target_arch="aarch64",target_arch="x86_64")))]
use super::{Entry,session,PH_ACTIVE,PH_STOPPING,OK,INVALID,UNKNOWN,BAD_STAGE,FULL};
use crate::v4_native_health::{AuthenticatedActivity,HealthClock,HealthPolicy,ControlDue};
use crate::runtime::{TxDispatch,RxPacket};
use wbd_types::buffer_contract::UniqueSealable;
use wbd_codec::link_fec_wire::{
    LinkPacketPlan,LinkMode,LINK_MAGIC,MAX_LOGICAL_DATAGRAM,
};
use wbd_platform::android_root_io::{
    AndroidBoundRawRx,AndroidBoundRawTx,AndroidOwnedTun,AndroidWorkerWake,
    AndroidBoundPhysicalDnsUdp,
};
use wbd_platform::ipv4_tcp::{
    Ipv4Tuple,Presentation,PacketPersona,build_presentation_ack,
};
use crate::v4_presentation_ack::presentation_ack_only_due;
#[cfg(feature="fec2_product_record")]
use crate::v4_owner_crypto::NormalOffReport;
#[cfg(feature="fec2_product_record")]
use super::OriginalQualityTx;
use wbd_codec::record_frame::FIXED_WIRE_OVERHEAD;
#[cfg(feature="fec2_product_record")]
use crate::v4_android_ipv4_mtu::{can_fragment,fragment,header_len,fragmentation_needed};
use wbd_types::MonoNs;
use std::sync::{Arc,Mutex,OnceLock,atomic::{AtomicBool,AtomicU32,AtomicU64,Ordering}};
use std::thread::{self,JoinHandle};
use std::time::{Duration,Instant};

#[derive(Default)]
pub(super) struct AndroidOriginalStats{
    pub(super) rx:AtomicU64,pub(super) tx:AtomicU64,
    pub(super) rx_error:AtomicU64,pub(super) tx_error:AtomicU64,
    pub(super) raw_candidates:AtomicU64,pub(super) tx_dropped:AtomicU64,
    // Genuine authenticated M4 business path observations (not browser PASS).
    tun_ipv4_admitted:AtomicU64,tun_ipv4_rejected:AtomicU64,
    business_raw_copied:AtomicU64,business_reverse_tun:AtomicU64,
    // A45 genuine one-reader ingress and return-path classification.
    raw_poll_ready:AtomicU64,raw_parse_failed:AtomicU64,
    raw_authenticated:AtomicU64,raw_auth_rejected:AtomicU64,
    reverse_tun_write_failed:AtomicU64,
    tun_icmp:AtomicU64,tun_tcp:AtomicU64,tun_udp:AtomicU64,
    pub(super) authenticated_peer_dead:AtomicBool,
    pub(super) peer_preauth_due:AtomicBool,
    pub(super) peer_verified_health:AtomicBool,
    pub(super) scope_invalid:AtomicBool,
    // Read from each true Bionic worker's CLOCK_THREAD_CPUTIME_ID;
    // reported as actual kernel thread CPU, never wall time or a guess.
    rx_cpu_ns:AtomicU64,tx_cpu_ns:AtomicU64,
    ip_id:AtomicU32,
    // Actual 40-byte original RAW TCP appearance ACK copies. Not business
    // delivery, M2 receipt or an authenticated peer liveness witness.
    ack_only_copied:AtomicU64,
    // B2c2a transparent ingress observations from the ONE original M4
    // readv. Only bounded metadata; no QNAME log, redirect or extra reader.
    dns_udp53_seen:AtomicU64,dns_tcp53_seen:AtomicU64,
    dns_unready:AtomicU64,
    // Actual original-M4 RAW-copy and authenticated reverse-TUN DNS delivery.
    dns_tunnel_raw_copied:AtomicU64,dns_tunnel_reply_tun:AtomicU64,
    dns_physical_tx:AtomicU64,dns_physical_rx:AtomicU64,
    dns_physical_error:AtomicU64,
    // B6 only actual original M4 socket send, raw copy or TUN write.
    dns_cn_physical_sent:AtomicU64,dns_noncn_tunnel_raw:AtomicU64,
    dns_tcp53_original_raw:AtomicU64,dns_physical_tc_tun:AtomicU64,
    startup_padding_copied_records:AtomicU64,startup_padding_copied_bytes:AtomicU64,
    #[cfg(feature="fec2_product_record")]
    fec2_source_tun:AtomicU64,
    #[cfg(feature="fec2_product_record")]
    fec2_recovered_tun:AtomicU64,
    #[cfg(feature="fec2_product_record")]
    fec2_source_raw:AtomicU64,
    #[cfg(feature="fec2_product_record")]
    fec2_repair_raw:AtomicU64,
    // Actual M3 AEAD+unique-PN FEC2 ingress and authenticated PLAN027
    // low-rate control. Neither proves local Fixed APPLIED.
    #[cfg(feature="fec2_product_record")]
    fec2_unique_symbols:AtomicU64,
    #[cfg(feature="fec2_product_record")]
    fec2_reverse_quality_reports:AtomicU64,
    #[cfg(feature="fec2_product_record")]
    fec2_reverse_quality_signals:AtomicU64,
    // Genuine PLAN027 3s-mature matched source window and exact local
    // revision promotion. Raw decoded kind1 alone never counts as M2.
    #[cfg(feature="fec2_product_record")]
    fec2_mature_quality_matched:AtomicU64,
    #[cfg(feature="fec2_product_record")]
    fec2_m2_applied:AtomicU64,
    #[cfg(feature="fec2_product_record")]
    fixed_ipv4_fragments_raw:AtomicU64,
    #[cfg(feature="fec2_product_record")]
    fixed_df1_pmtu_tun:AtomicU64,
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
        ack32:e.android_presentation_ack.ack(),
        advertised_window:65_535,
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
        Ok((n,pn,seq_end)) if n>0=>{
            // Definite kernel copied original ciphertext only. This is the
            // legal appearance SEQ for later 40B ACK-only, never an M1
            // merely staged reservation.
            e.android_last_copied_seq32=seq_end;
            e.android_last_ack_sent32=p.ack32;
            e.android_last_ack_tx_ns=at.0;
            e.android_ack_pending=e.android_presentation_ack.ack()!=p.ack32;
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
// B12b: original M1 borrowed IPv4 slab -> existing FixedStream source
// -> original M3 AEAD/PN -> SAME Android RAW sendto, with actual copy proof.
#[cfg(feature="fec2_product_record")]
fn send_android_fixed_source(
    e:&mut Entry,slab:crate::memory::UniqueBuffer,n:usize,
    frame:wbd_codec::path_budget::FrameBudget,physical:u32,
    raw:&AndroidBoundRawTx,stats:&AndroidOriginalStats,
    storage:&mut Vec<TxDispatch>,scratch:&mut [u8],at:MonoNs
)->bool{
    use wbd_types::ConfigRevision;
    let Some((profile,rev))=e.android_fec2_pending else{return false};
    if e.protected_features!=7||e.phase!=PH_ACTIVE||n==0{return false}
    let Ok(max)=wbd_codec::fec_v2::max_original_for_record_budget(
        frame.record_payload_mtu
    )else{return false};
    if n>max{return false}
    let Some((_,epoch))=e.owner.normal_firstsend_identity()else{return false};
    let mut stream=match e.android_fec2_tx.take(){
        Some(x) if x.revision()==ConfigRevision(rev)=>x,
        Some(x)=>{e.android_fec2_tx=Some(x);return false},
        None=>match crate::v4_fixed_stream::FixedStream::new(
            profile,rev,frame.record_payload_mtu
        ){Some(x)=>x,None=>return false},
    };
    let result=stream.offer_source(slab,14..14+n,at,|ticket,plain|{
        if ticket.revision!=ConfigRevision(rev){return false}
        let Some(len)=wbd_codec::fec_v2::SOURCE_HEADER.checked_add(plain.len())
            else{return false};
        let mut record=match e.arena.allocate(){Ok(x)=>x,Err(_)=>return false};
        let Some(end)=14usize.checked_add(len)else{return false};
        if end>record.writable().len(){return false}
        if wbd_codec::fec_v2::source_into(
            ticket.block_id,ticket.index,plain,frame.record_payload_mtu,
            &mut record.writable()[14..end]
        ).ok()!=Some(len){return false}
        let (pn,_,_)=match e.owner.seal_fec2_product_one(
            record,len,2,frame,u64::from(physical),epoch,at
        ){Ok(x)=>x,Err(_)=>return false};
        let copied=send_staged(e,raw,stats,storage,scratch,at)==Some(pn);
        if let Some(q)=e.quality_tx.as_mut(){
            // Register the very same original kind2 PN AFTER real RAW M4
            // settlement. Unsent never becomes first-send or loss=zero.
            q.settle_batch(&[(wbd_types::RecordPn(pn),0)],
                usize::from(copied),0,false,true,&[(pn,2,rev)]);
        }
        if copied{
            stats.fec2_source_raw.fetch_add(1,Ordering::Relaxed);
            stats.business_raw_copied.fetch_add(1,Ordering::Relaxed);
        }
        copied
    });
    e.android_fec2_tx=Some(stream);
    e.arena.drain_returns();
    result.is_ok_and(|accepted|accepted.source_enqueued)
}
// One <=4-row RS16 quantum per ready turn, only when fresh DATA was
// handled or no TUN DATA is ready. Original M4 copied/not-sent is final.
#[cfg(feature="fec2_product_record")]
fn send_android_fixed_due(
    e:&mut Entry,frame:wbd_codec::path_budget::FrameBudget,physical:u32,
    raw:&AndroidBoundRawTx,stats:&AndroidOriginalStats,
    storage:&mut Vec<TxDispatch>,scratch:&mut [u8],at:MonoNs
){
    use crate::v4_fixed_stream::DriverProof;
    let Some(mut stream)=e.android_fec2_tx.take()else{return};
    let Some((_,epoch))=e.owner.normal_firstsend_identity()else{
        e.android_fec2_tx=Some(stream);return
    };
    let revision=stream.revision();
    let _=stream.poll_parity_quanta(at,1,|bytes,_block,_row,rev|{
        if rev!=revision{return DriverProof::NotSent}
        let mut record=match e.arena.allocate(){
            Ok(x)=>x,Err(_)=>return DriverProof::NotSent
        };
        let Some(end)=14usize.checked_add(bytes.len())else{
            return DriverProof::NotSent
        };
        if end>record.writable().len(){return DriverProof::NotSent}
        record.writable()[14..end].copy_from_slice(bytes);
        let (pn,_,_)=match e.owner.seal_fec2_product_one(
            record,bytes.len(),3,frame,u64::from(physical),epoch,at
        ){Ok(x)=>x,Err(_)=>return DriverProof::NotSent};
        if send_staged(e,raw,stats,storage,scratch,at)==Some(pn){
            stats.fec2_repair_raw.fetch_add(1,Ordering::Relaxed);
            DriverProof::Copied
        }else{DriverProof::NotSent}
    });
    e.android_fec2_tx=Some(stream);
    e.arena.drain_returns();
}

// PLAN027 original M2 sender: low-rate START/CLOSE is one existing
// authenticated kind1 on the SAME M1/M3/PN and RAW fd. START must be
// definitely copied before counted DATA, CLOSE must include only settled
// source PNs, and an absent report never grants Fixed APPLIED.
#[cfg(feature="fec2_product_record")]
fn send_android_fixed_quality_due(
    e:&mut Entry,raw:&AndroidBoundRawTx,stats:&AndroidOriginalStats,
    storage:&mut Vec<TxDispatch>,scratch:&mut [u8],at:MonoNs,idle_ns:u64
){
    if e.phase!=PH_ACTIVE||e.protected_features!=7||
       e.android_fec2_pending.is_none(){return}
    let Some(next_pn)=e.owner.next_original_record_pn()else{return};
    let Some(signal)=e.quality_tx.as_mut()
        .and_then(|q|q.next_signal(next_pn,at).ok().flatten())else{return};
    let sent=(||->Option<bool>{
        let physical=e.android_physical.as_ref()?.mtu;
        let frame=e.owner.android_normal_off_frame_budget(physical).ok()?;
        let control=crate::v4_native_health::encode_authenticated_low_rate_signal_live(
            idle_ns,signal,frame.record_payload_mtu
        ).ok()?;
        let slab=e.arena.allocate().ok()?;
        let pn=e.owner.seal_original_authenticated_receipt(
            slab,&control,frame,u64::from(physical),at
        ).ok()?.0;
        Some(send_staged(e,raw,stats,storage,scratch,at)==Some(pn))
    })().unwrap_or(false);
    if let Some(q)=e.quality_tx.as_mut(){
        if q.complete_signal(signal,sent,at).is_err(){
            stats.tx_error.fetch_add(1,Ordering::Relaxed);
        }
    }
    e.arena.drain_returns();
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
// Reuse main H2229's authenticated cumulative ACK, coalesced to 10ms.
// No extra socket, JNI callback, M2 receipt, AEAD PN or TUN reader.
fn send_presentation_ack_if_due(
    e:&mut Entry,raw:&AndroidBoundRawTx,stats:&AndroidOriginalStats,
    scratch:&mut [u8],at:MonoNs,
){
    let ack=e.android_presentation_ack.ack();
    if !e.android_ack_pending||ack==e.android_last_ack_sent32{
        e.android_ack_pending=false;
        return
    }
    if !presentation_ack_only_due(
        at.0,e.android_last_ack_tx_ns,ack,e.android_last_ack_sent32
    ){return}
    let Some(scope)=e.android_physical.as_ref()else{return};
    let f=e.flow;
    let tuple=Ipv4Tuple{
        src_ip:&f.client_ip,dst_ip:&f.server_ip,
        src_port:f.client_port,dst_port:f.server_port,
    };
    let built=build_presentation_ack(
        tuple,e.android_last_copied_seq32,ack,
        stats.ip_id.fetch_add(1,Ordering::Relaxed) as u16,
        PacketPersona::Legacy,scope.mtu as usize,scratch
    );
    if let Ok(packet)=built{
        if raw.send_built_outer(e.generation,packet,scope.mtu).is_ok(){
            e.android_last_ack_sent32=ack;
            e.android_ack_pending=false;
            stats.ack_only_copied.fetch_add(1,Ordering::Relaxed);
        }else{
            stats.tx_error.fetch_add(1,Ordering::Relaxed);
        }
    }else{
        stats.tx_error.fetch_add(1,Ordering::Relaxed);
    }
    // Even on a transient send failure the next attempt remains bounded.
    e.android_last_ack_tx_ns=at.0;
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
    let mut dns_reply_scratch=Vec::with_capacity(
        crate::v4_android_dns_udp_flow::MAX_DNS_IPV4_PACKET
    );
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
        stats.raw_poll_ready.fetch_add(1,Ordering::Relaxed);
        // The RAW FD is nonblocking; one wake drains up to eight packets.
        // No extra two-FD poll(0) syscall before each subsequent recvfrom.
        for _ in 0..8 {
            if shutdown.load(Ordering::Acquire){break}
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
                    Err((crate::v4_owner_crypto::ProtectedCryptoError::AndroidWouldBlock,_))=>{
                        e.arena.drain_returns();
                        break
                    },
                    Err(_)=>{
                        stats.raw_parse_failed.fetch_add(1,Ordering::Relaxed);
                        stats.rx_error.fetch_add(1,Ordering::Relaxed);
                        e.arena.drain_returns();
                        break
                    },
                };
                stats.raw_candidates.fetch_add(1,Ordering::Relaxed);
                let lease=e.client_lease_ipv4;
                #[cfg(feature="fec2_product_record")]
                let fixed_requested=e.protected_features==7;
                // B12d: genuine Go TLS Fixed PENDING is enough to RECEIVE
                // authenticated peer source/parity and low-rate M2 controls.
                // Local APPLIED is still a separate, later evidence gate.
                #[cfg(feature="fec2_product_record")]
                let fixed_pending=e.android_fec2_pending;
                let (report,delivered,failed,dns_written,healthy,hint,retired)={
                    let Entry{owner,normal,android_dns_flows,
                        android_dns_hijack_ready,android_dns_physical_ready,android_cn_dns,
                        #[cfg(feature="fec2_product_record")]
                        android_fec2_rx,quality_tx,
                        ..}=&mut *e;
                    let dns_capture=*android_dns_hijack_ready &&
                        (!*android_dns_physical_ready||android_cn_dns.is_some());
                    #[cfg(feature="fec2_product_record")]
                    let result=if fixed_requested{
                        let Some((exact,blocks,_applied))=android_fec2_rx.as_mut()
                            else{break};
                        // B12a's APPLIED-first receive check made authentic
                        // reverse feedback impossible: M2 can only be
                        // witnessed after original verified PENDING ingresses.
                        // This enables just the original AEAD/PN RX/TUN
                        // pipeline, NEVER a sender APPLIED grant or UI mode.
                        if !fixed_pending.is_some_and(|(profile,rev)|
                            profile<=6&&rev>0)||
                           exact.negotiated_features!=7||
                           !exact.direction_s2c{break}
                        let mut report=NormalOffReport::default();
                        let mut delivered=0u32;
                        let mut failed=0u32;
                        let mut dns_written=0u32;
                        let mut healthy=false;
                        let mut hint=None;
                        let mut retired=false;
                        let opened=owner.drain_windows_authenticated_fec2(
                            at,std::mem::take(&mut rx_storage),
                            |_pn,kind,payload|{
                                // M3 already opened this record with the
                                // original unique AEAD/PN replay owner.
                                stats.fec2_unique_symbols.fetch_add(1,Ordering::Relaxed);
                                match blocks.accept_authenticated(*exact,kind,payload,at){
                                    Ok(firsts)=>{
                                        if firsts.is_empty(){
                                            report.pending=report.pending.saturating_add(1)
                                        }
                                        for first in firsts{
                                            report.completed=report.completed.saturating_add(1);
                                            let frame=first.frame.as_slice();
                                            if !crate::v4_session_address::
                                                admitted_client_destination(frame,lease){
                                                failed=failed.saturating_add(1);
                                                continue
                                            }
                                            let mut ip=frame;
                                            let mut rewritten=false;
                                            if dns_capture&&crate::v4_android_dns_udp_flow::
                                                TunnelDnsUdpFlows::is_tunnel_reply_candidate(frame){
                                                if frame.len()>crate::v4_android_dns_udp_flow::
                                                    MAX_DNS_IPV4_PACKET{
                                                    failed=failed.saturating_add(1);
                                                    continue
                                                }
                                                dns_reply_scratch.clear();
                                                dns_reply_scratch.extend_from_slice(frame);
                                                if android_dns_flows.rewrite_reply(
                                                    dns_reply_scratch.as_mut_slice(),
                                                    at.0/1_000_000
                                                ).is_err(){
                                                    failed=failed.saturating_add(1);
                                                    continue
                                                }
                                                ip=dns_reply_scratch.as_slice();
                                                rewritten=true;
                                            }
                                            if tun.write_authenticated_ip(ip).ok()==Some(ip.len()){
                                                delivered=delivered.saturating_add(1);
                                                if first.recovered{
                                                    stats.fec2_recovered_tun.fetch_add(
                                                        1,Ordering::Relaxed
                                                    );
                                                }else{
                                                    stats.fec2_source_tun.fetch_add(
                                                        1,Ordering::Relaxed
                                                    );
                                                }
                                                if rewritten{
                                                    dns_written=dns_written.saturating_add(1)
                                                }
                                            }else{failed=failed.saturating_add(1)}
                                        }
                                    },
                                    Err(reason)=>{
                                        blocks.record_rejection(reason);
                                        report.malformed=report.malformed.saturating_add(1);
                                    },
                                }
                            },
                            |_pn,control|{
                                // Original PLAN027 low-rate M2 envelope:
                                // authenticated kind1 only, not raw TCP ACK,
                                // old per-PN receipts or Go policy intent.
                                if let Some(report)=control.low_rate_quality{
                                    stats.fec2_reverse_quality_reports.fetch_add(
                                        1,Ordering::Relaxed
                                    );
                                    if let Some(q)=quality_tx.as_mut(){
                                        let before=q.counters[10];
                                        q.accept_report(report,at);
                                        // Only original sender history matches
                                        // this AEAD-unique quality window and
                                        // exact copied source PNs. Stale,
                                        // incomplete, unknown or wrong scope
                                        // stay PENDING and count no success.
                                        if q.counters[10]>before{
                                            stats.fec2_mature_quality_matched.fetch_add(
                                                1,Ordering::Relaxed);
                                            if *_applied==0 && q.counters[1]>0 &&
                                               stats.fec2_source_raw.load(Ordering::Relaxed)>0 &&
                                               stats.fec2_repair_raw.load(Ordering::Relaxed)>0 {
                                                if let Some((_,revision))=fixed_pending{
                                                    // Exact same only-once
                                                    // native Go Fixed revision,
                                                    // not a raw receipt flag.
                                                    *_applied=revision;
                                                    stats.fec2_m2_applied.fetch_add(
                                                        1,Ordering::Relaxed);
                                                }
                                            }
                                        }
                                    }
                                }
                                if control.low_rate_signal.is_some(){
                                    stats.fec2_reverse_quality_signals.fetch_add(
                                        1,Ordering::Relaxed
                                    );
                                }
                                healthy=true;
                                hint=control.peer_idle_ns;
                                retired=control.peer_retire;
                            },
                        );
                        match opened{
                            Ok((back,authed))=>{
                                report.authenticated=authed;
                                Ok((back,report,delivered,failed,dns_written,
                                    healthy,hint,retired))
                            },
                            Err(err)=>Err(err),
                        }
                    }else{
                        let Some(reassembly)=normal.as_mut()else{break};
                        owner.drain_android_normal_off_to_tun(
                            reassembly,&tun,lease,at,
                            std::mem::take(&mut rx_storage),
                            android_dns_flows,dns_capture,&mut dns_reply_scratch,
                        )
                    };
                    #[cfg(not(feature="fec2_product_record"))]
                    let result={
                        let Some(reassembly)=normal.as_mut()else{break};
                        owner.drain_android_normal_off_to_tun(
                            reassembly,&tun,lease,at,
                            std::mem::take(&mut rx_storage),
                            android_dns_flows,dns_capture,&mut dns_reply_scratch,
                        )
                    };
                    match result{
                        Ok((returned,report,delivered,failed,dns_written,healthy,hint,retired))=>{
                            rx_storage=returned;
                            (report,delivered,failed,dns_written,healthy,hint,retired)
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
                stats.business_reverse_tun.fetch_add(u64::from(delivered),Ordering::Relaxed);
                stats.dns_tunnel_reply_tun.fetch_add(u64::from(dns_written),Ordering::Relaxed);
                stats.reverse_tun_write_failed.fetch_add(u64::from(failed),Ordering::Relaxed);
                stats.raw_auth_rejected.fetch_add(
                    u64::from(report.authenticated.rejected)+
                    u64::from(report.malformed)+u64::from(report.discarded),
                    Ordering::Relaxed);
                stats.rx_error.fetch_add(
                    u64::from(failed)+u64::from(report.malformed)+
                    u64::from(report.discarded)+u64::from(report.authenticated.rejected),
                    Ordering::Relaxed
                );
                let authenticated=report.authenticated.link_ready!=0||healthy;
                if authenticated{
                    stats.raw_authenticated.fetch_add(1,Ordering::Relaxed);
                    // Keep the main H2229 contiguous presentation ledger
                    // independent from the M1 seq32 high-water extension
                    // anchor. A future authenticated span must NOT ACK a hole.
                    let before=e.android_presentation_ack.ack();
                    let advanced=e.android_presentation_ack.verified(
                        absolute as u32,wire_len
                    );
                    e.android_seq_anchor=e.android_seq_anchor.max(
                        absolute.saturating_add(wire_len as u64));
                    if advanced!=before && !e.android_ack_pending{
                        e.android_ack_pending=true;
                        // One wake for pending ACK; TX owns the 10ms
                        // coalescing deadline and the sole original RAW FD.
                        let _=peer_wake.signal_wake();
                    }
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
    tunnel_dns_query:bool,
    split_noncn_query:bool,tcp53_original:bool,
}
// Fixed/FEC2 has no LINK20 receiver. For an exceptional DF=0 IPv4
// datagram that reached TUN above the Fixed source budget, emit ordinary
// IPv4 fragments as separate ORIGINAL FEC2 kind2 sources. This bounded
// plan is owned by the existing TX worker, not a new reader or queue.
struct PendingAndroidFixedIpv4{
    source:Vec<u8>,offset:usize,generation:u32,physical_mtu:u32,
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

fn count_dns_ingress(stats:&AndroidOriginalStats,
    observed:crate::v4_android_dns_ingress::Dns53Observation
){
    match observed{
        crate::v4_android_dns_ingress::Dns53Observation::UdpQuestion{..}=>{
            stats.dns_udp53_seen.fetch_add(1,Ordering::Relaxed);
        },
        crate::v4_android_dns_ingress::Dns53Observation::TcpPort53=>{
            stats.dns_tcp53_seen.fetch_add(1,Ordering::Relaxed);
        },
        crate::v4_android_dns_ingress::Dns53Observation::Incomplete=>{
            stats.dns_unready.fetch_add(1,Ordering::Relaxed);
        },
        crate::v4_android_dns_ingress::Dns53Observation::NotDns=>{},
    }
}
fn tun_worker(
    cell:Arc<Mutex<Entry>>,shutdown:Arc<AtomicBool>,
    wake:Arc<AndroidWorkerWake>,tun:Arc<AndroidOwnedTun>,
    raw:Arc<AndroidBoundRawTx>,dns:Option<Arc<AndroidBoundPhysicalDnsUdp>>,
    stats:Arc<AndroidOriginalStats>,
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
    // Same original M4 TX thread owns the bounded physical DNS transaction
    // slots and scratch, not a parallel reader or a Go/JNI data callback.
    let mut physical_flows=
        crate::v4_android_dns_physical_flow::PhysicalDnsUdpFlows::default();
    let mut physical_wire=[0u8;
        crate::v4_android_dns_physical_flow::MAX_DNS_WIRE];
    let mut physical_packet=[0u8;
        crate::v4_android_dns_physical_flow::MAX_DNS_REPLY_IPV4];
    let mut pending=None::<PendingAndroidJumbo>;
    #[cfg(feature="fec2_product_record")]
    let mut pending_fixed=None::<PendingAndroidFixedIpv4>;
    let mut next_packet_id=1u32;
    let frame=match cell.lock(){
        Ok(e)=>match e.android_physical.as_ref() {
            Some(s)=>match if e.protected_features==7{
                #[cfg(feature="fec2_product_record")]
                {e.owner.android_fixed_frame_budget(s.mtu)}
                #[cfg(not(feature="fec2_product_record"))]
                {e.owner.android_normal_off_frame_budget(s.mtu)}
            }else{e.owner.android_normal_off_frame_budget(s.mtu)}{
                Ok(value)=>value,
                Err(_)=>{shutdown.store(true,Ordering::Release);return}
            },
            None=>{shutdown.store(true,Ordering::Release);return}
        },
        Err(_)=>{shutdown.store(true,Ordering::Release);return}
    };
    // One cold generation owns the physical MTU/MSS/record budget.
    // The existing 1Hz scope check retires a changed interface/MTU.
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
                    raw.check_scope(&scope.interface,scope.ifindex).is_ok()&&
                    dns.as_ref().is_none_or(|socket|
                        socket.recheck(&scope.interface,scope.ifindex).is_ok())),
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
        // The same TX worker owns appearance ACK and DATA writes, and
        // original Stop joins it before closing the physically bound FD.
        if let Ok(mut e)=cell.lock(){
            if e.phase==PH_ACTIVE{
                send_presentation_ack_if_due(
                    &mut e,&raw,&stats,&mut wire_scratch,at
                );
                #[cfg(feature="fec2_product_record")]
                if e.protected_features==7{
                    send_android_fixed_quality_due(&mut e,&raw,&stats,
                        &mut storage,&mut wire_scratch,at,
                        clock.local_idle_ns(at.0));
                }
            }
        }

        // FEC2 IPv4 DF=0 slow path: source packets are ordinary IPv4
        // fragments, each sealed with its own original M3 PN. Do not
        // read another TUN packet until the bounded plan is settled.
        #[cfg(feature="fec2_product_record")]
        if pending_fixed.is_some(){
            let mut retire=false;
            let mut deferred=false;
            for _ in 0..8{
                if shutdown.load(Ordering::Acquire){break}
                let Ok(mut e)=cell.lock()else{
                    shutdown.store(true,Ordering::Release);break
                };
                let Some(plan)=pending_fixed.as_mut()else{break};
                if e.phase!=PH_ACTIVE||e.protected_features!=7||
                   e.generation!=plan.generation||
                   e.android_physical.as_ref().is_none_or(
                       |p|p.mtu!=plan.physical_mtu){
                    retire=true;break
                }
                let mut slab=match e.arena.allocate(){
                    Ok(x)=>x,
                    Err(wbd_types::buffer_contract::BufferContractError::NoCapacity)=>{
                        deferred=true;break
                    },
                    Err(_)=>{retire=true;break},
                };
                let cap=frame.record_payload_mtu.saturating_sub(
                    wbd_codec::fec_v2::SOURCE_HEADER
                ).min(slab.writable().len().saturating_sub(14));
                let Some((n,end,done))=fragment(
                    &plan.source,plan.offset,cap,
                    &mut slab.writable()[14..],
                )else{
                    stats.tx_error.fetch_add(1,Ordering::Relaxed);
                    stats.tx_dropped.fetch_add(1,Ordering::Relaxed);
                    retire=true;break
                };
                let sent=send_android_fixed_source(
                    &mut e,slab,n,frame,plan.physical_mtu,&raw,&stats,
                    &mut storage,&mut wire_scratch,now()
                );
                if !sent{
                    stats.tx_dropped.fetch_add(1,Ordering::Relaxed);
                    retire=true;break
                }
                plan.offset=end;
                stats.fixed_ipv4_fragments_raw.fetch_add(1,Ordering::Relaxed);
                clock.on_local_business(now().0);
                if done{retire=true;break}
            }
            if retire{
                if let Some(mut finished)=pending_fixed.take(){
                    finished.source.clear();
                    jumbo_spare=finished.source;
                }
            }else if deferred&&!shutdown.load(Ordering::Acquire){
                thread::sleep(Duration::from_millis(1));
            }
            continue
        }

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
                        if done{
                            stats.business_raw_copied.fetch_add(1,Ordering::Relaxed);
                            if let Some(p)=pending.as_ref(){
                                if p.tunnel_dns_query{
                                    stats.dns_tunnel_raw_copied.fetch_add(1,Ordering::Relaxed);
                                }
                                if p.split_noncn_query{
                                    stats.dns_noncn_tunnel_raw.fetch_add(1,Ordering::Relaxed);
                                }
                                if p.tcp53_original{
                                    stats.dns_tcp53_original_raw.fetch_add(1,Ordering::Relaxed);
                                }
                            }
                            retire=true;break
                        }
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
        let ack_due=match cell.lock(){
            Ok(e) if e.phase==PH_ACTIVE&&e.android_ack_pending=>
                if e.android_last_ack_tx_ns==0{at.0}else{
                    e.android_last_ack_tx_ns.saturating_add(10_000_000)
                },
            _=>u64::MAX,
        };
        let mut due=clock.next_deadline()
            .unwrap_or(at.0.saturating_add(30_000_000_000))
            .min(ack_due);
        #[cfg(feature="fec2_product_record")]
        if let Ok(e)=cell.lock(){
            if e.protected_features==7{
                if let Some(t)=e.android_fec2_tx.as_ref().and_then(|x|x.next_deadline()){
                    due=due.min(t.0);
                }
                if let Some(t)=e.quality_tx.as_ref()
                    .and_then(|q|q.next_close_deadline()){
                    due=due.min(t.0);
                }
            }
        }
        let timeout=((due.saturating_sub(at.0)+999_999)/1_000_000)
            .min(1_000).max(1) as i32;
        let readiness=if let Some(socket)=dns.as_ref(){
            wake.wait_tun_and_physical_dns(
                tun.readiness_fd(),socket.readiness_fd(),timeout)
        }else{
            wake.wait_readable(tun.readiness_fd(),timeout).map(|v|(v,false))
        };
        if shutdown.load(Ordering::Acquire){break}
        let (tun_ready,dns_ready)=match readiness{
            Ok(v)=>v,
            Err(_)=>{
                stats.scope_invalid.store(true,Ordering::Release);
                shutdown.store(true,Ordering::Release);
                break
            }
        };
        if dns_ready{
            if let Some(socket)=dns.as_ref(){
                // This is NOT an authenticated remote WBD packet. Only a
                // physically connected 223.5.5.5 socket, an original owned
                // query ID/QNAME and the exact original lease may deliver.
                for _ in 0..8{
                    if shutdown.load(Ordering::Acquire){break}
                    let n=match socket.read_answer(
                        tun.generation(),&mut physical_wire){
                        Ok(n)=>n,
                        Err(err) if err.kind()==std::io::ErrorKind::WouldBlock=>break,
                        Err(_)=>{
                            stats.dns_physical_error.fetch_add(1,Ordering::Relaxed);
                            shutdown.store(true,Ordering::Release);
                            break
                        }
                    };
                    let Ok(e)=cell.lock()else{
                        shutdown.store(true,Ordering::Release);break
                    };
                    if e.phase!=PH_ACTIVE||!e.android_dns_hijack_ready||
                       !e.android_dns_physical_ready{
                        stats.dns_physical_error.fetch_add(1,Ordering::Relaxed);
                        break
                    }
                    let result=physical_flows.receive(
                        &physical_wire[..n],&mut physical_packet,
                        now().0/1_000_000);
                    match result{
                        Ok(len) if e.client_lease_ipv4.is_some_and(|lease|
                            physical_packet[16..20]==lease) &&
                            tun.write_scoped_physical_dns_ip(
                                e.generation,&physical_packet[..len]
                            ).ok()==Some(len)=>{
                            stats.dns_physical_rx.fetch_add(1,Ordering::Relaxed);
                            // Real TC=1 DNS response was injected into the
                            // original App TUN, not proof of later TCP retry.
                            if physical_packet[30]&0x02!=0{
                                stats.dns_physical_tc_tun.fetch_add(1,Ordering::Relaxed);
                            }
                        }
                        _=>{
                            stats.dns_physical_error.fetch_add(1,Ordering::Relaxed);
                        }
                    }
                }
            }
        }
        if !tun_ready{
            #[cfg(feature="fec2_product_record")]
            if let Ok(mut e)=cell.lock(){
                if e.phase==PH_ACTIVE&&e.protected_features==7{
                    if let Some(mtu)=e.android_physical.as_ref().map(|x|x.mtu){
                        send_android_fixed_due(&mut e,frame,mtu,&raw,&stats,
                            &mut storage,&mut wire_scratch,now());
                    }
                }
            }
            continue
        }
        // One sparse normal packet is sent immediately, never held waiting
        // for batch fill. Eight bounded source turns before Health/Stop.
        // TUN adopt() sets O_NONBLOCK. Drain a short bounded burst with
        // readv directly, not a duplicate poll(0) on every packet.
        for _ in 0..8{
            if shutdown.load(Ordering::Acquire){break}
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
            // The precomputed, generation-scoped FrameBudget is Copy.
            // Reserve ONE original M1 loan BEFORE consuming the TUN packet.
            let mut slab=match e.arena.allocate(){
                Ok(v)=>v,Err(_)=>break
            };
            let mut head_cap=frame.single_business_payload_mtu.min(
                slab.writable().len().saturating_sub(14));
            #[cfg(feature="fec2_product_record")]
            if e.protected_features==7{
                head_cap=head_cap.min(frame.record_payload_mtu.saturating_sub(
                    wbd_codec::fec_v2::SOURCE_HEADER
                ));
            }
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
                Err(err) if err.kind()==std::io::ErrorKind::WouldBlock=>{
                    e.arena.drain_returns();
                    break
                },
                Err(_)=>{
                    stats.tx_error.fetch_add(1,Ordering::Relaxed);
                    e.arena.drain_returns();
                    break
                }
            };
            let head_len=n.min(head_cap);
            let head=&slab.writable()[14..14+head_len];
            if !original_complete_ipv4_head(head,n,lease){
                stats.tun_ipv4_rejected.fetch_add(1,Ordering::Relaxed);
                e.arena.drain_returns();
                stats.tx_error.fetch_add(1,Ordering::Relaxed);
                stats.tx_dropped.fetch_add(1,Ordering::Relaxed);
                break
            }
            stats.tun_ipv4_admitted.fetch_add(1,Ordering::Relaxed);
            // Protocol comes from the SAME complete, /32-qualified kernel IP.
            // ICMP proves selected-App inner ping ingress, not echo reply.
            match head[9] {
                1=>{stats.tun_icmp.fetch_add(1,Ordering::Relaxed);},
                6=>{stats.tun_tcp.fetch_add(1,Ordering::Relaxed);},
                17=>{stats.tun_udp.fetch_add(1,Ordering::Relaxed);},
                _=>{},
            }
            // B6: classify complete packets only. For jumbo/EDNS the
            // existing single readv already supplied a scatter tail; do
            // not count that incomplete head as a malformed DNS attempt.
            let escaped=head.starts_with(LINK_MAGIC);
            let dns_observation=if e.android_dns_hijack_ready&&n<=head_cap&&!escaped {
                crate::v4_android_dns_ingress::observe_ipv4_dns53(head,n)
            }else{
                crate::v4_android_dns_ingress::Dns53Observation::NotDns
            };
            if n<=head_cap&&!escaped{count_dns_ingress(&stats,dns_observation)}
            let at=now();
            if n<=head_cap&&!escaped{
                let route=crate::v4_android_dns_route::choose(
                    head,dns_observation,e.android_dns_hijack_ready,
                    e.android_dns_physical_ready,e.android_cn_dns.as_deref());
                if matches!(route,crate::v4_android_dns_route::DnsRoute::PhysicalUDP){
                    // This separate cold gate is UNGRANTABLE until a
                    // complete authenticated original-Go CN selector,
                    // physical UDP/TCP53 and system Resolver ownership
                    // admit exactly the correct name for physical egress.
                    if let Some(socket)=dns.as_ref(){
                        let packet=&slab.writable()[14..14+n];
                        match physical_flows.prepare(
                            packet,&mut physical_wire,at.0/1_000_000){
                            Ok((len,id,new_slot))=>{
                                if socket.send_question(
                                    tun.generation(),&physical_wire[..len]).is_ok(){
                                    stats.dns_physical_tx.fetch_add(1,Ordering::Relaxed);
                                    if e.android_cn_dns.is_some(){
                                        stats.dns_cn_physical_sent.fetch_add(1,Ordering::Relaxed);
                                    }
                                }else{
                                    if new_slot{physical_flows.cancel(id);}
                                    stats.dns_physical_error.fetch_add(1,Ordering::Relaxed);
                                }
                            }
                            Err(_)=>{
                                stats.dns_physical_error.fetch_add(1,Ordering::Relaxed);
                            }
                        }
                    }else{
                        shutdown.store(true,Ordering::Release);
                        stats.scope_invalid.store(true,Ordering::Release);
                    }
                    e.arena.drain_returns();
                    continue
                }
                // Only a completely admitted DNS generation may replace
                // original DNS with 1.1.1.1 on the same loaned M1 slab.
                // No Go/JNI per packet, alternate TUN reader or fallback.
                let mut tunnel_dns_query=false;
                if matches!(route,crate::v4_android_dns_route::DnsRoute::TunnelUDP){
                    let dns_packet=&mut slab.writable()[14..14+n];
                    if e.android_dns_flows.rewrite_query(
                        dns_packet,at.0/1_000_000
                    ).is_err(){
                        e.arena.drain_returns();
                        stats.tx_dropped.fetch_add(1,Ordering::Relaxed);
                        break
                    }
                    tunnel_dns_query=true;
                }
                #[cfg(feature="fec2_product_record")]
                if e.protected_features==7{
                    if send_android_fixed_source(
                        &mut e,slab,n,frame,physical,&raw,&stats,
                        &mut storage,&mut wire_scratch,at
                    ){
                        clock.on_local_business(at.0);
                        if tunnel_dns_query{
                            stats.dns_tunnel_raw_copied.fetch_add(1,Ordering::Relaxed);
                        }
                    }else{stats.tx_dropped.fetch_add(1,Ordering::Relaxed);}
                    continue
                }
                // Common O(1) hot path: original owner AEAD/PN directly
                // over the kernel-filled slab, immutable M4 RAW sendto.
                // Original authenticated M1/M3 padding: bounded by
                // record wire budget, actual slab and physical outer cap.
                // No padding on LINK fragments, Health or physical DNS.
                let ms=at.0/1_000_000;
                let room=frame.record_wire_mtu
                    .min(e.android_startup_pad_wire_limit)
                    .min(slab.writable().len())
                    .saturating_sub(n.saturating_add(FIXED_WIRE_OVERHEAD));
                if e.android_startup_padding.is_some()&&
                   ms.saturating_sub(e.android_startup_pad_gc_ms)>=30_000{
                    if let Some(policy)=e.android_startup_padding.as_mut(){
                        policy.expire_coarse(ms);
                    }
                    e.android_startup_pad_gc_ms=ms;
                }
                let padding=if let Some(policy)=e.android_startup_padding.as_mut(){
                    policy.propose(&slab.writable()[14..14+n],ms,room)
                }else{0};
                match e.owner.seal_android_read_normal_ip(
                    &tun,slab,n,frame,u64::from(physical),Some(lease),at,padding
                ){
                    Ok((pn,_,_,_))=>{
                        if send_staged(
                            &mut e,&raw,&stats,&mut storage,
                            &mut wire_scratch,at
                        )==Some(pn){
                            stats.business_raw_copied.fetch_add(1,Ordering::Relaxed);
                            if padding>0{
                                stats.startup_padding_copied_records.fetch_add(1,Ordering::Relaxed);
                                stats.startup_padding_copied_bytes.fetch_add(
                                    padding as u64,Ordering::Relaxed
                                );
                            }
                            if tunnel_dns_query{
                                stats.dns_tunnel_raw_copied.fetch_add(1,Ordering::Relaxed);
                                if e.android_cn_dns.is_some(){
                                    stats.dns_noncn_tunnel_raw.fetch_add(1,Ordering::Relaxed);
                                }
                            }
                            if matches!(route,crate::v4_android_dns_route::DnsRoute::TCP53OriginalTunnel){
                                stats.dns_tcp53_original_raw.fetch_add(1,Ordering::Relaxed);
                            }
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
            let dns_observation=if e.android_dns_hijack_ready{
                crate::v4_android_dns_ingress::observe_ipv4_dns53(&jumbo_spare,n)
            }else{
                crate::v4_android_dns_ingress::Dns53Observation::NotDns
            };
            count_dns_ingress(&stats,dns_observation);
            let route=crate::v4_android_dns_route::choose(
                &jumbo_spare,dns_observation,e.android_dns_hijack_ready,
                e.android_dns_physical_ready,e.android_cn_dns.as_deref());
            if matches!(route,crate::v4_android_dns_route::DnsRoute::PhysicalUDP){
                if let Some(socket)=dns.as_ref(){
                    match physical_flows.prepare(
                        &jumbo_spare,&mut physical_wire,at.0/1_000_000){
                        Ok((len,id,new_slot))=>{
                            if socket.send_question(
                                tun.generation(),&physical_wire[..len]).is_ok(){
                                stats.dns_physical_tx.fetch_add(1,Ordering::Relaxed);
                                if e.android_cn_dns.is_some(){
                                    stats.dns_cn_physical_sent.fetch_add(1,Ordering::Relaxed);
                                }
                            }else{
                                if new_slot{physical_flows.cancel(id);}
                                stats.dns_physical_error.fetch_add(1,Ordering::Relaxed);
                            }
                        }
                        Err(_)=>{
                            stats.dns_physical_error.fetch_add(1,Ordering::Relaxed);
                        }
                    }
                }else{
                    shutdown.store(true,Ordering::Release);
                    stats.scope_invalid.store(true,Ordering::Release);
                }
                continue
            }
            #[cfg(feature="fec2_product_record")]
            if e.protected_features==7{
                // Fixed does not use Normal LINK20. When a DF=1
                // oversized packet reaches the TUN, tell its originating
                // IPv4 stack the actual local single-source capacity.
                if header_len(&jumbo_spare).is_some()&&jumbo_spare[6]&0x40!=0{
                    let mut icmp=[0u8;128];
                    if let Some(n)=fragmentation_needed(
                        &jumbo_spare,frame.single_business_payload_mtu,&mut icmp
                    ){
                        if tun.write_local_pmtu_icmp_ipv4(
                            e.generation,&icmp[..n]
                        ).ok()==Some(n){
                            stats.fixed_df1_pmtu_tun.fetch_add(1,Ordering::Relaxed);
                        }else{stats.tx_error.fetch_add(1,Ordering::Relaxed);}
                    }
                    stats.tx_dropped.fetch_add(1,Ordering::Relaxed);
                    drop(slab);e.arena.drain_returns();
                    continue
                }
                // DF0 native IPv4 fragment slow-path, including RFC791
                // copy-bit Options and already-fragmented IP input.
                if can_fragment(&jumbo_spare){
                    if matches!(route,crate::v4_android_dns_route::DnsRoute::TunnelUDP)&&
                       e.android_dns_flows.rewrite_query(
                           &mut jumbo_spare,now().0/1_000_000
                       ).is_err(){
                        stats.tx_dropped.fetch_add(1,Ordering::Relaxed);
                        break
                    }
                    pending_fixed=Some(PendingAndroidFixedIpv4{
                        source:std::mem::take(&mut jumbo_spare),
                        offset:0,generation:e.generation,physical_mtu:physical,
                    });
                }else{
                    stats.tx_dropped.fetch_add(1,Ordering::Relaxed);
                }
                drop(slab);
                e.arena.drain_returns();
                break
            }
            // DNS with EDNS can exceed the common slab head; inspect the
            // one already-collected complete IP before M3 fragmentation.
            let mut tunnel_dns_query=false;
            if matches!(route,crate::v4_android_dns_route::DnsRoute::TunnelUDP){
                if e.android_dns_flows.rewrite_query(
                    &mut jumbo_spare,now().0/1_000_000
                ).is_err(){
                    stats.tx_dropped.fetch_add(1,Ordering::Relaxed);
                    break
                }
                tunnel_dns_query=true;
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
                tunnel_dns_query,
                split_noncn_query:tunnel_dns_query&&e.android_cn_dns.is_some(),
                tcp53_original:matches!(route,
                    crate::v4_android_dns_route::DnsRoute::TCP53OriginalTunnel),
            });
            // No second TUN read until this logical datagram is complete
            // or retired. Return the unused original slab before fragments.
            drop(slab);
            e.arena.drain_returns();
            break
        }
        // Fresh business sources first, then at most one parity quantum.
        #[cfg(feature="fec2_product_record")]
        if let Ok(mut e)=cell.lock(){
            if e.phase==PH_ACTIVE&&e.protected_features==7{
                if let Some(mtu)=e.android_physical.as_ref().map(|x|x.mtu){
                    send_android_fixed_due(&mut e,frame,mtu,&raw,&stats,
                        &mut storage,&mut wire_scratch,now());
                }
            }
        }
    }
    physical_flows.stop();
    if let Some(socket)=dns.as_ref(){socket.begin_stop()}
    clock.stopped();
    stats.tx_cpu_ns.store(thread_cpu_ns(),Ordering::Relaxed);
    if shutdown.load(Ordering::Acquire){
        let _=peer_wake.signal_stop();
    }
}
pub(super) fn start(handle:u64,ifindex:u32)->i32{
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    // Feature7 is native-startable ONLY after original Go TLS/Detach,
    // first Fixed PENDING revision, original FEC2 RX, low-rate M2 owner
    // and no unaudited pre-M4 early Normal LINK records. Public Go
    // Fixed/Auto admission remains closed until native product E2E.
    #[cfg(feature="fec2_product_record")]
    let fixed_ready=e.protected_features==7&&
        e.android_fec2_pending.is_some()&&e.quality_tx.is_some()&&
        e.android_fec2_rx.is_some()&&e.staged_count==0;
    #[cfg(not(feature="fec2_product_record"))]
    let fixed_ready=false;
    if e.phase!=PH_ACTIVE||e.server_side||e.android_workers.is_some()||
       e.android_joining||e.client_lease_ipv4.is_none()||
       !(e.protected_features==3||fixed_ready)||
       e.android_physical.as_ref().is_none_or(|p|p.ifindex!=ifindex)||
       e.normal.is_none(){
        return BAD_STAGE
    }
    let (Some(rx),Some(tx),Some(tun))=(
        e.android_raw_rx.as_ref(),e.android_raw_tx.as_ref(),e.android_tun.as_ref()
    )else{return BAD_STAGE};
    let rx=Arc::clone(rx);let tx=Arc::clone(tx);let tun=Arc::clone(tun);
    let Some(scope)=e.android_physical.as_ref()else{return BAD_STAGE};
    let budget=if fixed_ready{
        #[cfg(feature="fec2_product_record")]
        {e.owner.android_fixed_frame_budget(scope.mtu)}
        #[cfg(not(feature="fec2_product_record"))]
        {e.owner.android_normal_off_frame_budget(scope.mtu)}
    }else{e.owner.android_normal_off_frame_budget(scope.mtu)};
    if tx.check_scope(&scope.interface,ifindex).is_err()||budget.is_err(){
        return INVALID
    }
    let dns=if e.android_dns_hijack_ready&&e.android_dns_physical_ready{
        // True original-Go authenticated generation, physical handle and
        // scope are required before *any* DNS socket is opened.
        match AndroidBoundPhysicalDnsUdp::open(
            scope.network_handle,&scope.interface,scope.ifindex,scope.mtu,
            e.flow.client_ip,e.generation
        ){
            Ok(fd)=>Some(Arc::new(fd)),
            Err(_)=>return INVALID,
        }
    }else{None};
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
            let mut dns_reply_scratch=Vec::with_capacity(
                crate::v4_android_dns_udp_flow::MAX_DNS_IPV4_PACKET
            );
            let Entry{owner,normal,android_dns_flows,
                android_dns_hijack_ready,android_dns_physical_ready,android_cn_dns,..}=&mut *e;
            owner.drain_android_normal_off_to_tun(
                normal.as_mut().unwrap(),&tun,lease,at,Vec::with_capacity(32),
                android_dns_flows,*android_dns_hijack_ready &&
                    (!*android_dns_physical_ready||android_cn_dns.is_some()),
                &mut dns_reply_scratch
            )
        };
        match drained{
            Ok((returned,report,delivered,failed,dns_written,healthy,hint,retire))=>{
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
                counters.dns_tunnel_reply_tun.fetch_add(u64::from(dns_written),Ordering::Relaxed);
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
            tx_cell,tx_shutdown,tx_event,tun,tx,dns,tx_stats,activity,policy,tx_peer
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
// Real Go TLS/cold owner only; this cannot enable Fixed/Auto/Game.
#[no_mangle]
pub extern "C" fn wbd_m0_embedded_go_normal_startup_padding_set(
    h:u64,mode:u32,outer_path_mtu:u32
)->i32{
    use crate::v4_client_startup_padding::{StartupMode,TunnelStartupPadding};
    let selected=match mode{
        0=>StartupMode::Off,1=>StartupMode::Tls,2=>StartupMode::Flows,
        _=>return INVALID,
    };
    if !(576..=1500).contains(&outer_path_mtu){return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.server_side||e.protected_features!=3||
       e.android_workers.is_some()||e.android_joining{return BAD_STAGE}
    let Some((_,epoch))=e.owner.normal_firstsend_identity()else{return BAD_STAGE};
    let directional=crate::v4_client_startup_padding::linux_tx_padding_epoch(epoch,false);
    let seed=u64::from_be_bytes(directional[..8].try_into().unwrap_or([0;8]))
        ^u64::from_be_bytes(directional[8..].try_into().unwrap_or([0;8]));
    e.android_startup_padding=if selected==StartupMode::Off{None}else{
        Some(TunnelStartupPadding::new(selected,seed))
    };
    e.android_startup_pad_mode=mode;
    e.android_startup_pad_wire_limit=if mode==0{0}else{
        (outer_path_mtu as usize).saturating_sub(40)
    };
    e.android_startup_pad_gc_ms=0;
    e.android_metrics.startup_padding_copied_records.store(0,Ordering::Relaxed);
    e.android_metrics.startup_padding_copied_bytes.store(0,Ordering::Relaxed);
    OK
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_normal_startup_padding_counters(
    h:u64,mode:*mut u32,records:*mut u64,bytes:*mut u64
)->i32{
    if mode.is_null()||records.is_null()||bytes.is_null(){return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.server_side||e.protected_features!=3{return BAD_STAGE}
    unsafe{
        mode.write(e.android_startup_pad_mode);
        records.write(e.android_metrics.startup_padding_copied_records.load(Ordering::Relaxed));
        bytes.write(e.android_metrics.startup_padding_copied_bytes.load(Ordering::Relaxed));
    }
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
// Read real post-Start original M4 worker counters; no packet body, UID,
// destination or traffic bytes leave the native owner.
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_loop_business_receipts(
    h:u64,tun_admitted:*mut u64,tun_rejected:*mut u64,
    raw_copied:*mut u64,reverse_tun:*mut u64
)->i32{
    if tun_admitted.is_null()||tun_rejected.is_null()||
       raw_copied.is_null()||reverse_tun.is_null(){return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.android_workers.is_none(){return BAD_STAGE}
    let c=&e.android_metrics;
    unsafe{
        tun_admitted.write(c.tun_ipv4_admitted.load(Ordering::Relaxed));
        tun_rejected.write(c.tun_ipv4_rejected.load(Ordering::Relaxed));
        raw_copied.write(c.business_raw_copied.load(Ordering::Relaxed));
        reverse_tun.write(c.business_reverse_tun.load(Ordering::Relaxed));
    }
    OK
}

// A45: classify actual original Android M4 return-path ownership.
// Poll readiness is NOT a parsed peer packet; authenticated is NOT
// business delivery; each source remains an original worker-only counter.
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_loop_return_path_receipts(
    h:u64,poll:*mut u64,parse_failed:*mut u64,parsed:*mut u64,
    auth:*mut u64,rejected:*mut u64,write_failed:*mut u64,
    icmp:*mut u64,tcp:*mut u64,udp:*mut u64
)->i32{
    if poll.is_null()||parse_failed.is_null()||parsed.is_null()||
       auth.is_null()||rejected.is_null()||write_failed.is_null()||
       icmp.is_null()||tcp.is_null()||udp.is_null(){return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.android_workers.is_none(){return BAD_STAGE}
    let c=&e.android_metrics;
    unsafe{
        poll.write(c.raw_poll_ready.load(Ordering::Relaxed));
        parse_failed.write(c.raw_parse_failed.load(Ordering::Relaxed));
        parsed.write(c.raw_candidates.load(Ordering::Relaxed));
        auth.write(c.raw_authenticated.load(Ordering::Relaxed));
        rejected.write(c.raw_auth_rejected.load(Ordering::Relaxed));
        write_failed.write(c.reverse_tun_write_failed.load(Ordering::Relaxed));
        icmp.write(c.tun_icmp.load(Ordering::Relaxed));
        tcp.write(c.tun_tcp.load(Ordering::Relaxed));
        udp.write(c.tun_udp.load(Ordering::Relaxed));
    }
    OK
}

// A47: read the original Android bound RAW TCP socket evidence. No new
// datapath, no M3/replay bypass; the actual original RX FD owns every count.
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_loop_raw_rx_debug(
    h:u64,out:*mut u64,count:usize
)->i32{
    if out.is_null()||count!=22{return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.android_workers.is_none(){return BAD_STAGE}
    let Some(rx)=e.android_raw_rx.as_ref()else{return BAD_STAGE};
    let snap=rx.raw_diagnostic_snapshot();
    unsafe{std::ptr::copy_nonoverlapping(snap.as_ptr(),out,count);}
    OK
}

/// B6 additive read-only M4 routing receipt, no changes to historical
/// A47/B3d/B4 M4 ABI. Increments only after actual OS RAW/UDP/TUN copy.
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_loop_dns_route_receipts(
    h:u64,cn_physical_sent:*mut u64,noncn_tunnel_raw:*mut u64,
    tcp53_original_raw:*mut u64,physical_tc_tun:*mut u64
)->i32{
    if cn_physical_sent.is_null()||noncn_tunnel_raw.is_null()||
       tcp53_original_raw.is_null()||physical_tc_tun.is_null(){return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.android_workers.is_none(){return BAD_STAGE}
    unsafe{
        cn_physical_sent.write(e.android_metrics.dns_cn_physical_sent.load(Ordering::Relaxed));
        noncn_tunnel_raw.write(e.android_metrics.dns_noncn_tunnel_raw.load(Ordering::Relaxed));
        tcp53_original_raw.write(e.android_metrics.dns_tcp53_original_raw.load(Ordering::Relaxed));
        physical_tc_tun.write(e.android_metrics.dns_physical_tc_tun.load(Ordering::Relaxed));
    }
    OK
}

/// B2c2a readonly diagnostics for packets *seen* by the ONE real Rust
/// M4 TUN worker. No answer counts, endpoint validation or delivery claims:
/// hijack_enabled=0 until physical + tunnel DNS backend, reply inversion
/// and Android Resolver proof independently qualify. Caller owns three
/// counters and can read them only while the original worker is alive.
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_loop_dns_ingress_observed(
    h:u64,udp_seen:*mut u64,tcp_seen:*mut u64,
    incomplete:*mut u64,dns_raw_copied:*mut u64,
    dns_reply_tun:*mut u64,physical_tx:*mut u64,
    physical_rx:*mut u64,physical_error:*mut u64,
    hijack_enabled:*mut u32
)->i32{
    if udp_seen.is_null()||tcp_seen.is_null()||incomplete.is_null()||
       dns_raw_copied.is_null()||dns_reply_tun.is_null()||
       physical_tx.is_null()||physical_rx.is_null()||
       physical_error.is_null()||hijack_enabled.is_null(){return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.android_workers.is_none(){return BAD_STAGE}
    unsafe{
        udp_seen.write(e.android_metrics.dns_udp53_seen.load(Ordering::Relaxed));
        tcp_seen.write(e.android_metrics.dns_tcp53_seen.load(Ordering::Relaxed));
        incomplete.write(e.android_metrics.dns_unready.load(Ordering::Relaxed));
        dns_raw_copied.write(e.android_metrics.dns_tunnel_raw_copied.load(Ordering::Relaxed));
        dns_reply_tun.write(e.android_metrics.dns_tunnel_reply_tun.load(Ordering::Relaxed));
        physical_tx.write(e.android_metrics.dns_physical_tx.load(Ordering::Relaxed));
        physical_rx.write(e.android_metrics.dns_physical_rx.load(Ordering::Relaxed));
        physical_error.write(e.android_metrics.dns_physical_error.load(Ordering::Relaxed));
        hijack_enabled.write(0); // Must NEVER claim DNS interception here.
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
/// A physical Network/scope error is NOT evidence of peer Health death.
/// It is a separate terminal session signal: Go MUST withdraw its private
/// app UID route and Stop/join immediately, not wait for dead90 or falsely
/// reauthorize TLS using a fabricated authenticated-peer event.
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_loop_physical_scope_invalid(
    h:u64,invalid:*mut u32,
)->i32{
    if invalid.is_null(){return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.android_workers.is_none(){return BAD_STAGE}
    unsafe{invalid.write(u32::from(
        e.android_metrics.scope_invalid.load(Ordering::Acquire)
    ))};
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

// B12c: actual original Go verified TLS/Detach feature7 Fixed REQUESTED.
// Native reply is PENDING until copied source+parity and genuine reverse M2.
#[cfg(feature="fec2_product_record")]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_fixed_stage_pending(
    h:u64,epoch_ptr:*const u8,len:usize,profile:u8,revision:u64
)->i32{
    if epoch_ptr.is_null()||len!=16||profile>6||revision==0{return INVALID}
    let supplied=unsafe{std::slice::from_raw_parts(epoch_ptr,16)};
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.server_side||e.android_joining||
       e.android_workers.is_some()||e.protected_features!=7||
       e.android_fec2_rx.is_none()||
       e.owner.normal_firstsend_identity().is_none_or(
           |(_,epoch)|epoch.as_slice()!=supplied
       ){return BAD_STAGE}
    // B13 only stages the first Fixed revision. Quiescent Auto reprofile
    // has a separate ownership transition and cannot overwrite this proof.
    if e.android_fec2_pending.is_some()||e.android_fec2_tx.is_some()||
       e.quality_tx.is_some(){return INVALID}
    let Some((lane,verified_epoch))=e.owner.normal_firstsend_identity()
        else{return BAD_STAGE};
    if verified_epoch.as_slice()!=supplied{return BAD_STAGE}
    e.quality_tx=Some(OriginalQualityTx::new(
        lane,verified_epoch,wbd_recovery::WireDirection::ClientToServer
    ));
    e.android_fec2_pending=Some((profile,revision));
    OK
}
#[cfg(feature="fec2_product_record")]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_fixed_pending_readback(
    h:u64,epoch_ptr:*const u8,len:usize,
    profile:*mut u8,revision:*mut u64,applied:*mut u32
)->i32{
    if epoch_ptr.is_null()||len!=16||profile.is_null()||
       revision.is_null()||applied.is_null(){return INVALID}
    let supplied=unsafe{std::slice::from_raw_parts(epoch_ptr,16)};
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.server_side||e.android_joining||
       e.protected_features!=7||e.owner.normal_firstsend_identity().is_none_or(
           |(_,epoch)|epoch.as_slice()!=supplied
       ){return BAD_STAGE}
    let Some((p,r))=e.android_fec2_pending else{return BAD_STAGE};
    // APPLIED is set only by matched 3s mature PLAN027 quality for
    // actual local RAW-copied kind2 source PNs and real same-revision
    // parity copy. A mere authenticated kind1, queue or intent is pending.
    let actual=e.android_fec2_rx.as_ref()
        .map_or(0u32,|(_,_,rev)|u32::from(*rev==r));
    unsafe{profile.write(p);revision.write(r);applied.write(actual)};
    OK
}
// B12c read-only copied native M4 FEC receipts. No per-packet Go callback.
#[cfg(feature="fec2_product_record")]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_fixed_m4_counters(
    h:u64,out:*mut u64,len:usize
)->i32{
    if out.is_null()||len!=9{return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.protected_features!=7{return BAD_STAGE}
    let v=[
        e.android_metrics.fec2_source_raw.load(Ordering::Relaxed),
        e.android_metrics.fec2_repair_raw.load(Ordering::Relaxed),
        e.android_metrics.fec2_source_tun.load(Ordering::Relaxed),
        e.android_metrics.fec2_recovered_tun.load(Ordering::Relaxed),
        e.android_metrics.fec2_unique_symbols.load(Ordering::Relaxed),
        e.android_metrics.fec2_reverse_quality_reports.load(Ordering::Relaxed),
        e.android_metrics.fec2_reverse_quality_signals.load(Ordering::Relaxed),
        e.android_metrics.fec2_mature_quality_matched.load(Ordering::Relaxed),
        e.android_metrics.fec2_m2_applied.load(Ordering::Relaxed),
    ];
    unsafe{std::ptr::copy_nonoverlapping(v.as_ptr(),out,9)};
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

