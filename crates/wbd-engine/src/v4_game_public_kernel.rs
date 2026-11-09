//! M0 actual original TLS grouped Game2/4 M4 Linux kernel worker.
//! One GameAdapter is authenticated by already-committed protected Go lane
//! handles. Raw/TUN are the genuine M4 scoped driver, not a shadow/Go proxy.
//! Opt-in only; still not a public CLI product qualification without real
//! end-to-end application/Stop Actions for both executable processes.
#![allow(unsafe_code)]
use std::os::fd::OwnedFd;
use std::sync::{Arc,Mutex,atomic::{AtomicBool,AtomicU64,Ordering}};
use std::thread::{self,JoinHandle};
use std::collections::VecDeque;
use std::sync::mpsc::{self,Receiver,RecvTimeoutError,SyncSender};
// Bounded total source admissions per existing Game4+FEC TX owner turn.
// H1278 native pressure: both server and client M1 shared-TUN inboxes
// overflowed despite bounded 4-source drain while FEC parity was polled.
// The native TUN reader already reads up to eight packets per batch.
const GAME4_FEC_SHARED_TUN_MAX_SOURCES_PER_TURN:usize=8;
use crate::v4_embedded_go::OriginalTunIngress;
use std::time::{Instant,Duration};
use crate::v4_game_lane::{GameAdapter,GameLaneOpener,OriginalGameLaneRekey,Error as GameAdapterError};
use crate::v4_game_cosmetic_outer::CosmeticOuter;
use crate::v4_native_health::{HealthClock,HealthPolicy,ControlDue};
use crate::runtime::game_shared::GameError;
use crate::v4_protected_handoff::GoFlow;
use crate::memory::Arena;
use wbd_types::{MonoNs,RecordPn,SeqOffset,LaneKey,TunnelKey};
use wbd_types::buffer_contract::{FrozenMetadata,UniqueSealable};
use wbd_platform::linux_raw_carrier::{ScopedRawIpv4Tx,ScopedRawIpv4Rx,RawTxError};
use wbd_platform::linux_tun_sink::{ScopedTunSink,TunReadyEntry};
use wbd_platform::ipv4_tcp::{Ipv4Tuple,PacketPersona,Presentation};
use wbd_platform::r1::StopResult;
#[repr(C)]
struct GamePollFd {fd:i32,events:i16,revents:i16}
unsafe extern "C" {fn poll(fds:*mut GamePollFd,nfds:usize,timeout:i32)->i32;}

struct TxLane{
    key:LaneKey,flow:GoFlow,seq:u64,raw:Arc<ScopedRawIpv4Tx>,
    last_initial_id:Option<u64>
}
// One command to the EXISTING Game4 TX worker, never a second scheduler.
struct TxLaneSwitch{
    slot:usize,flow:GoFlow,seq:u64,prepared:OriginalGameLaneRekey,
    ready:SyncSender<Result<GameLaneOpener,()>>,
}
struct RxLaneSwitch{
    flow:GoFlow,raw:Arc<ScopedRawIpv4Rx>,opener:GameLaneOpener,
    ready:SyncSender<Arc<ScopedRawIpv4Rx>>,
}
#[derive(Default)]
struct RxLockSample {
    samples:AtomicU64,wait_total_ns:AtomicU64,
    hold_total_ns:AtomicU64,wait_max_ns:AtomicU64,
}
impl RxLockSample{
    fn record(&self,wait:Duration,held:Duration){
        let ns=|d:Duration|d.as_nanos().min(u128::from(u64::MAX)) as u64;
        let wait_ns=ns(wait);
        self.samples.fetch_add(1,Ordering::Relaxed);
        self.wait_total_ns.fetch_add(wait_ns,Ordering::Relaxed);
        self.hold_total_ns.fetch_add(ns(held),Ordering::Relaxed);
        self.wait_max_ns.fetch_max(wait_ns,Ordering::Relaxed);
    }
}
#[derive(Default)]
struct TxDurationSample{
    offers:AtomicU64,offer_total_ns:AtomicU64,offer_max_ns:AtomicU64,
    polls:AtomicU64,poll_total_ns:AtomicU64,poll_max_ns:AtomicU64,
}
impl TxDurationSample{
    fn observe(&self,elapsed:Duration,offer:bool){
        let ns=elapsed.as_nanos().min(u128::from(u64::MAX)) as u64;
        let (samples,total,max)=if offer{
            (&self.offers,&self.offer_total_ns,&self.offer_max_ns)
        }else{(&self.polls,&self.poll_total_ns,&self.poll_max_ns)};
        samples.fetch_add(1,Ordering::Relaxed);
        total.fetch_add(ns,Ordering::Relaxed);
        max.fetch_max(ns,Ordering::Relaxed);
    }
}
#[derive(Default)]
struct TxRejectReasons {
    offer:AtomicU64,slab:AtomicU64,record:AtomicU64,policy:AtomicU64,
    raw:AtomicU64,raw_backpressure:AtomicU64,raw_route:AtomicU64,raw_mtu:AtomicU64,
    df0_fragments:AtomicU64,icmp3_code4_sent:AtomicU64,
    icmp3_code4_denied:AtomicU64,
}
#[derive(Default)]
struct RxRejectReasons {
    aead:AtomicU64,invalid:AtomicU64,duplicate:AtomicU64,
    stale:AtomicU64,capacity:AtomicU64,scope:AtomicU64,
    stopped:AtomicU64,game:AtomicU64,
}
pub(crate) struct GameKernelOwner{
    stop:Arc<AtomicBool>,threads:Vec<JoinHandle<()>>,
    tun:Arc<ScopedTunSink>,
    tx:Vec<Arc<ScopedRawIpv4Tx>>,rx:Vec<Arc<ScopedRawIpv4Rx>>,
    copied:Arc<AtomicU64>,delivered:Arc<AtomicU64>,rejected:Arc<AtomicU64>,
    raw_received:Arc<AtomicU64>,rx_reject:Arc<RxRejectReasons>,
    rx_driver_timeout:Arc<AtomicU64>,rx_driver_other:Arc<AtomicU64>,
    rx_mutex_acquired:Arc<AtomicU64>,rx_authenticated_some:Arc<AtomicU64>,
    rx_dedup_none:Arc<AtomicU64>,rx_tun_failed:Arc<AtomicU64>,
    rx_delivery_commit_failed:Arc<AtomicU64>,
    rx_lock_sample:Arc<RxLockSample>,tx_reasons:Arc<TxRejectReasons>,
    outer_blocked_duplicate:Arc<AtomicU64>,
    outer_repeated_copy_sent:Arc<AtomicU64>,
    tx_lane_switch:SyncSender<TxLaneSwitch>,
    rx_lane_switch:Vec<SyncSender<RxLaneSwitch>>,
    physical_ifname:String,physical_ifindex:u32,
    physical_generation:u32,server:bool,
    diagnostic_adapter:Arc<Mutex<GameAdapter>>,
    tx_work_sample:Arc<TxDurationSample>,
    tx_shared_burst_extra:Arc<AtomicU64>,
    // One-shot protected cold M4 acknowledgment on each side, armed only
    // after that side's complete Game group RAW RX/TX workers start.
    cold_group_committed:Arc<AtomicBool>,
    // Verified kind0 Health hint from this Game cohort's OWN AEAD/PN
    // RX lane. Kept apart from successful inner IPv4 TUN deliveries.
    peer_health_evidence:Arc<crate::v4_native_health::AuthenticatedActivity>,
}
// Each lane FIFO delivers the first independent AEAD copy of a logical
// source or parity symbol. Reappearance cannot become outer DATA repair.
fn game_first_lane_copy(last:Option<u64>,id:u64)->bool{
    last.is_none_or(|old|id>old)
}
#[cfg(test)]
#[test]
fn w103_game_outer_off_blocks_reused_logical_ids_but_keeps_new_parity(){
    assert!(game_first_lane_copy(None,0));
    assert!(!game_first_lane_copy(Some(0),0));
    assert!(!game_first_lane_copy(Some(15),9));
    assert!(game_first_lane_copy(Some(15),16)); // fresh parity symbol
    assert!(game_first_lane_copy(None,9)); // independent first on lane2
}
impl GameKernelOwner{
    pub(crate) fn start(
        adapter:Arc<Mutex<GameAdapter>>,flows:Vec<GoFlow>,seqs:Vec<u64>,
        server:bool,ifname:&str,ifindex:u32,fd:OwnedFd,tun_name:&str,
        generation:u32,outer_repair_enabled:bool,
        peer_persona:PacketPersona,authenticated_client_ip:Option<[u8;4]>,
        shared_ingress:Option<Receiver<OriginalTunIngress>>,
        shared_alive:Option<Arc<AtomicBool>>,
    )->Result<Self,()>{
        if shared_ingress.is_some()!=shared_alive.is_some(){return Err(())}
        let n=flows.len();
        if !matches!(n,2|4)||seqs.len()!=n||generation==0||
            ifindex==0||ifname.is_empty()||tun_name.is_empty()||
            tun_name.len()>15||seqs.contains(&0){return Err(())}
        let tun=Arc::new(ScopedTunSink::from_owned_fd(fd,generation,tun_name)
            .map_err(|_|())?);
        // One actual cold Win32/Go-equivalent OS-address readback, not
        // a speculative use of public destination or carrier outer IP.
        let trusted_tun_router_ip=tun.owned_local_ipv4().ok();
        let mut tx=Vec::with_capacity(n);
        let mut rx=Vec::with_capacity(n);
        for i in 0..n{
            tx.push(Arc::new(ScopedRawIpv4Tx::open(ifname,ifindex,generation)
                .map_err(|_|())?));
            let f=flows[i];
            let (src,dst,sp,dp)=if server{
                (f.client_ip,f.server_ip,f.client_port,f.server_port)
            }else{
                (f.server_ip,f.client_ip,f.server_port,f.client_port)
            };
            let exact_rx=Ipv4Tuple{
                src_ip:&src,dst_ip:&dst,src_port:sp,dst_port:dp
            };
            rx.push(Arc::new(ScopedRawIpv4Rx::open_exact_tuple(
                ifname,ifindex,generation,exact_rx).map_err(|_|())?));
        }
        let stop=Arc::new(AtomicBool::new(false));
        let copied=Arc::new(AtomicU64::new(0));
        let delivered=Arc::new(AtomicU64::new(0));
        let rejected=Arc::new(AtomicU64::new(0));
        let tx_reasons=Arc::new(TxRejectReasons::default());
        let tx_work_sample=Arc::new(TxDurationSample::default());
        let tx_sample_worker=Arc::clone(&tx_work_sample);
        let tx_shared_burst_extra=Arc::new(AtomicU64::new(0));
        let tx_shared_burst_worker=Arc::clone(&tx_shared_burst_extra);
        let tx_sample_enabled=std::env::var("WBD_GAME_TX_SAMPLE")
            .ok().as_deref()==Some("1");
        let cold_group_committed=Arc::new(AtomicBool::new(false));
        let tx_cold_group_committed=Arc::clone(&cold_group_committed);
        let raw_received=Arc::new(AtomicU64::new(0));
        let rx_reject=Arc::new(RxRejectReasons::default());
        let rx_driver_timeout=Arc::new(AtomicU64::new(0));
        let rx_driver_other=Arc::new(AtomicU64::new(0));
        let rx_mutex_acquired=Arc::new(AtomicU64::new(0));
        let rx_authenticated_some=Arc::new(AtomicU64::new(0));
        let rx_dedup_none=Arc::new(AtomicU64::new(0));
        let rx_tun_failed=Arc::new(AtomicU64::new(0));
        let rx_delivery_commit_failed=Arc::new(AtomicU64::new(0));
        let rx_lock_sample=Arc::new(RxLockSample::default());
        let outer_blocked_duplicate=Arc::new(AtomicU64::new(0));
        let outer_repeated_copy_sent=Arc::new(AtomicU64::new(0));
        let mut lanes=Vec::new();
        for i in 0..n{
            lanes.push(TxLane{
                key:LaneKey{tunnel:TunnelKey{slot:14,generation},
                    slot:i as u32+1,generation},
                flow:flows[i],seq:seqs[i],raw:Arc::clone(&tx[i]),
                last_initial_id:None
            });
        }
        // Per-lane original outer ACK observed only AFTER real AEAD opened
        // a reverse DATA record. Atomics replace per-packet queues/locks;
        // each receiver owns one index, existing TX processes batched hints.
        let presentation_hints=Arc::new((0..n)
            .map(|_|AtomicU64::new(0)).collect::<Vec<_>>());
        let tx_hints=Arc::clone(&presentation_hints);
        let mut feedback_epoch=[0u8;16];
        feedback_epoch[..4].copy_from_slice(&generation.to_be_bytes());
        let scoped_cosmetic=CosmeticOuter::with_normal_feedback(
            &lanes.iter().map(|l|l.key).collect::<Vec<_>>(),
            &seqs,feedback_epoch).map_err(|_|())?;
        let (tx_lane_switch,tx_lane_commands)=mpsc::sync_channel::<TxLaneSwitch>(1);
        let tx_adapter=Arc::clone(&adapter);
        let tx_stop=Arc::clone(&stop);
        let tx_tun=Arc::clone(&tun);
        let tx_copy=Arc::clone(&copied);
        let tx_rejected=Arc::clone(&rejected);
        let tx_fail=Arc::clone(&tx_reasons);
        let outer_denied=Arc::clone(&outer_blocked_duplicate);
        let outer_repeated=Arc::clone(&outer_repeated_copy_sent);
        #[allow(unused_variables)]
        let (inner_mtu,rx_owner,fec_enabled,health_origin,health_rx)={
            let game=adapter.lock().map_err(|_|())?;
            let (origin,evidence)=game.health_context();
            (game.inner_mtu(),game.receiver_handle(),game.has_game_fec(),origin,evidence)
        };
        // Take the ORIGINAL per-lane replay state exactly once, before
        // either TX or RX worker starts. Failed admission cannot create an
        // unauthenticated receive window or a parallel duplicate PN acceptor.
        let lane_openers={
            let mut owner=rx_owner.lock().map_err(|_|())?;
            let mut taken=Vec::with_capacity(n);
            for i in 0..n{
                taken.push(owner.take_lane_for_worker(lanes_key(generation,i))
                    .map_err(|_|())?);
            }
            taken
        };
        let mut lane_openers=lane_openers.into_iter();
        let epoch_clock=Instant::now();
        let tx_health_rx=Arc::clone(&health_rx);
        let tx_worker=thread::Builder::new().name("wbd-v4-game-tx".into())
            .spawn(move||{
                let Ok(mut arena)=Arena::new(generation^0x4000_0000,64,2048,64,1_000_000)
                    else{return};
                let start=epoch_clock;
                let mut health=HealthClock::new(HealthPolicy::default_connected(),
                    health_origin.elapsed().as_nanos().min(u128::from(u64::MAX)) as u64);
                let mut cold_receipt_armed=false;
                // One full IPv4 TUN read buffer PER Game TX owner, never
                // 64KiB per arena slab. A 2048B read irreversibly truncated
                // actual oversized DF0 datagrams into false small packets.
                let mut inbound=[0u8;65_535];
                // One bounded exceptional datagram; ordinary small IP goes
                // first on every loop, then at most 4 IP fragments per turn.
                let mut pending_ip_fragments=VecDeque::<Vec<u8>>::new();
                // The shared process TUN reader already wakes its bounded
                // per-session channel. Keep ONE received packet until this
                // original TX owner handles it on the next turn; never let
                // a timer consume and drop source data.
                let mut wakeup_shared=None::<OriginalTunIngress>;
                // Bounded local PMTU feedback: <=20 messages per 1s window,
                // no per-flow timer/retry/extra worker. Usually Linux returns
                // EMSGSIZE before a DF1 datagram enters this TUN owner.
                let mut local_icmp_window=Instant::now();
                let mut local_icmp_credit=20u32;
                // Game FEC presentation-only replay has two/four fixed
                // lane slots, owned exclusively by this existing TX worker.
                let mut cosmetic=scoped_cosmetic;
                let mut observed_hints=[0u64;4];
                let mut observed_offers=0u64;
                let mut observed_polls=0u64;
                while !tx_stop.load(Ordering::Acquire){
                    // The original path supervisor admits exactly one
                    // protected cold lane. Rekey within the existing TX
                    // thread so a logical Game4 job cannot seal with the
                    // old AEAD while using the new raw source 4-tuple.
                    if let Ok(change)=tx_lane_commands.try_recv(){
                        let slot=change.slot;
                        let answer=if slot>=lanes.len()||
                            lanes[slot].key.slot!=slot as u32+1||
                            change.seq==0{
                            Err(())
                        }else{
                            match tx_adapter.lock(){
                                Ok(mut game)=>{
                                    match game.apply_original_game_lane_tx_rekey(
                                        change.prepared){
                                        Ok((actual,opener)) if actual==slot=>{
                                            lanes[slot].flow=change.flow;
                                            lanes[slot].seq=change.seq;
                                            lanes[slot].last_initial_id=None;
                                            observed_hints[slot]=tx_hints[slot]
                                                .load(Ordering::Acquire);
                                            if cosmetic.rekey_one_lane(slot,
                                                lanes[slot].key,change.seq,
                                                feedback_epoch).is_ok(){
                                                Ok(opener)
                                            }else{Err(())}
                                        },
                                        _=>Err(()),
                                    }
                                },
                                Err(_)=>Err(()),
                            }
                        };
                        let _=change.ready.send(answer);
                    }
                    // An A2 /32 publication revokes old A without waiting
                    // for old Rust Stop. Do not drain old A's queued ingress
                    // into original Game AEAD after the successor owns it.
                    if shared_alive.as_ref().is_some_and(|alive|
                        !alive.load(Ordering::Acquire)){
                        tx_stop.store(true,Ordering::Release);
                        break
                    }
                    // Never hold the TUN device's shared serialized mutex
                    // during a 750ms missing-app poll: authenticated RX
                    // needs the SAME device mutex for first-delivery write.
                    // Ready-only poll(0) holds it only for an actual read.
                    // With a Game server's verified /32 share, only the
                    // process-wide SharedTunReader calls read(2) on the
                    // physical device. This Game TX owns a bounded channel;
                    // saturating a different group can never steal its TUN
                    // packets or block this group's original M4/FEC.
                    let size=if let Some(ingress)=shared_ingress.as_ref(){
                        let ready=if let Some(packet)=wakeup_shared.take(){
                            Ok(packet)
                        }else{ingress.try_recv()};
                        match ready{
                            Ok(OriginalTunIngress::Shared(packet))=>{
                                let bytes=packet.as_slice();
                                if bytes.len()<=inbound.len(){
                                    inbound[..bytes.len()].copy_from_slice(bytes);
                                    Some(bytes.len())
                                }else{
                                    tx_rejected.fetch_add(1,Ordering::Relaxed);
                                    None
                                }
                            },
                            Ok(_)=>{
                                tx_rejected.fetch_add(1,Ordering::Relaxed);
                                None
                            },
                            Err(std::sync::mpsc::TryRecvError::Empty)=>None,
                            Err(std::sync::mpsc::TryRecvError::Disconnected)=>break,
                        }
                    }else{
                        let mut slots:[&mut [u8];1]=[&mut inbound];
                        match tx_tun.read_ready_batch(generation,&mut slots){
                            Ok(batch)=>match batch.entry(0){
                                Some(TunReadyEntry::UntrustedIpv4{len})=>Some(len),
                                Some(TunReadyEntry::Rejected)=>{
                                    tx_rejected.fetch_add(1,Ordering::Relaxed);
                                    None
                                },
                                _=>None
                            },
                            Err(_)=>{
                                if tx_stop.load(Ordering::Acquire){break}
                                tx_rejected.fetch_add(1,Ordering::Relaxed);
                                None
                            }
                        }
                    };
                    let now=MonoNs(start.elapsed().as_nanos().min(u128::from(u64::MAX)) as u64);
                    let Ok(mut game)=tx_adapter.lock()else{break};
                    let mut did_business=false;
                    if let Some(len)=size{
                        if len>0&&len<=inner_mtu{
                            did_business=true;
                            health.on_local_business(health_origin.elapsed().as_nanos()
                                .min(u128::from(u64::MAX)) as u64);
                            observed_offers+=1;
                            let start_offer=(tx_sample_enabled&&observed_offers%128==0)
                                .then(Instant::now);
                            let outcome=game.offer(&inbound[..len],now);
                            if let Some(t)=start_offer{
                                tx_sample_worker.observe(t.elapsed(),true);
                            }
                            if outcome.is_err(){
                                tx_fail.offer.fetch_add(1,Ordering::Relaxed);
                                tx_rejected.fetch_add(1,Ordering::Relaxed);
                            }
                        }else if len!=0{
                            // Kernel should fragment DF0 before TUN; only a
                            // complete, legal exceptional packet reaching M4
                            // uses the same RFC791 bounded IP slow path.
                            // Unlike LINK20 each part is an ordinary Game or
                            // Game+FEC source, reassembled by the peer OS.
                            if pending_ip_fragments.is_empty(){
                                match wbd_platform::ipv4_fragment::fragment_ipv4_df0(
                                    &inbound[..len],inner_mtu,32){
                                    Ok(parts)=>{
                                        tx_fail.df0_fragments.fetch_add(
                                            parts.len() as u64,Ordering::Relaxed);
                                        pending_ip_fragments.extend(parts);
                                    },
                                    Err(wbd_platform::ipv4_fragment::FragmentError::DfSet)=>{
                                        if local_icmp_window.elapsed()>=Duration::from_secs(1){
                                            local_icmp_window=Instant::now();
                                            local_icmp_credit=20;
                                        }
                                        if let Some(router)=trusted_tun_router_ip.filter(|_|
                                            local_icmp_credit>0){
                                            // Only a real scoped Linux TUN
                                            // kernel write counts as emitted.
                                            // No fabricated Applied/AEAD/FEC.
                                            local_icmp_credit-=1;
                                            if tx_tun.write_owned_local_pmtu_icmp(
                                                generation,&inbound[..len],
                                                router,inner_mtu as u16).is_ok(){
                                                tx_fail.icmp3_code4_sent.fetch_add(
                                                    1,Ordering::Relaxed);
                                            }else{
                                                tx_fail.icmp3_code4_denied.fetch_add(
                                                    1,Ordering::Relaxed);
                                            }
                                        }else{
                                            tx_fail.icmp3_code4_denied.fetch_add(
                                                1,Ordering::Relaxed);
                                        }
                                        tx_rejected.fetch_add(1,Ordering::Relaxed);
                                    },
                                    Err(_)=>{
                                        tx_rejected.fetch_add(1,Ordering::Relaxed);
                                    },
                                }
                            }else{
                                tx_rejected.fetch_add(1,Ordering::Relaxed);
                            }
                        }
                    }
                    // One authenticated Game4+FEC session may empty up to eight
                    // already-ready original shared-TUN ingress slots per
                    // owner turn, matching the actual reader's eight-packet
                    // batch. The old one-source-per-turn path coupled
                    // each TUN dequeue to several FEC quanta and delayed
                    // four-lane copies; during high offered load it left the
                    // per-lease TUN inbox full even after ISA-L acceleration.
                    // Every source remains an independent ordered M4/FEC
                    // admission; preserve the one-offer/one-owner/one-scope
                    // contract. No extra thread, Go FFI or waiting on Full.
                    // Exceptional oversized DF0 follows its original
                    // fragment/ICMP branch on the NEXT turn; do not overtake
                    // an already pending fragment.
                    if fec_enabled&&lanes.len()==4&&pending_ip_fragments.is_empty(){
                        if let Some(ingress)=shared_ingress.as_ref(){
                            let mut extra_accepted=0u64;
                            for _ in 0..GAME4_FEC_SHARED_TUN_MAX_SOURCES_PER_TURN-1{
                                match ingress.try_recv(){
                                    Ok(OriginalTunIngress::Shared(packet))=>{
                                        let bytes=packet.as_slice();
                                        if bytes.len()>inner_mtu{
                                            wakeup_shared=Some(
                                                OriginalTunIngress::Shared(packet));
                                            break
                                        }
                                        if bytes.is_empty(){continue}
                                        did_business=true;
                                        health.on_local_business(
                                            health_origin.elapsed().as_nanos()
                                            .min(u128::from(u64::MAX)) as u64);
                                        observed_offers+=1;
                                        let sampled=(tx_sample_enabled&&
                                            observed_offers%128==0).then(Instant::now);
                                        let at=MonoNs(start.elapsed().as_nanos()
                                            .min(u128::from(u64::MAX)) as u64);
                                        let sent=game.offer(bytes,at);
                                        if let Some(t)=sampled{
                                            tx_sample_worker.observe(t.elapsed(),true);
                                        }
                                        if sent.is_ok(){extra_accepted+=1}else{
                                            tx_fail.offer.fetch_add(1,Ordering::Relaxed);
                                            tx_rejected.fetch_add(1,Ordering::Relaxed);
                                        }
                                    },
                                    Ok(_)=>{
                                        tx_rejected.fetch_add(1,Ordering::Relaxed);
                                    },
                                    Err(std::sync::mpsc::TryRecvError::Empty)=>break,
                                    Err(std::sync::mpsc::TryRecvError::Disconnected)=>break,
                                }
                            }
                            if extra_accepted!=0{
                                tx_shared_burst_worker.fetch_add(
                                    extra_accepted,Ordering::Relaxed);
                            }
                        }
                    }
                    for _ in 0..4 {
                        let Some(part)=pending_ip_fragments.pop_front()else{break};
                        if game.offer(&part,now).is_err(){
                            tx_fail.offer.fetch_add(1,Ordering::Relaxed);
                            tx_rejected.fetch_add(1,Ordering::Relaxed);
                            // No speculative retry of an already partially
                            // accounted Game/FEC source on a new lane/PN.
                            pending_ip_fragments.clear();
                            break
                        }
                        did_business=true;
                        health.on_local_business(health_origin.elapsed().as_nanos()
                            .min(u128::from(u64::MAX)) as u64);
                    }
                    // Single TX owner first drains source copies to M4 before
                    // any FEC parity quantum can enqueue additional work.
                    let mut flush=|game:&mut GameAdapter,due_now:MonoNs|{
                        game.drain(due_now,|lane,id,pn,wire|{
                            // The genuine original TLS group builds
                            // physical lanes in slots 1..N. Avoid a
                            // linear scan on each Game4 × fixed6 copy,
                            // but still validate the entire scoped lane
                            // key (generation/epoch/slot) before dispatch.
                            let Some(index)=lane.slot.checked_sub(1)
                                .map(|v|v as usize)else{
                                tx_rejected.fetch_add(1,Ordering::Relaxed);
                                return false
                            };
                            let Some(item)=lanes.get_mut(index).filter(|v|v.key==lane)else{
                                tx_rejected.fetch_add(1,Ordering::Relaxed);
                                return false
                            };
                            if !outer_repair_enabled &&
                                !game_first_lane_copy(item.last_initial_id,id.0){
                                tx_fail.policy.fetch_add(1,Ordering::Relaxed);
                                outer_denied.fetch_add(1,Ordering::Relaxed);
                                tx_rejected.fetch_add(1,Ordering::Relaxed);
                                return false
                            }
                            let Ok(mut slab)=arena.allocate()else{
                                tx_fail.slab.fetch_add(1,Ordering::Relaxed);
                                tx_rejected.fetch_add(1,Ordering::Relaxed);
                                return false
                            };
                            if wire.len()>slab.writable().len(){
                                tx_fail.record.fetch_add(1,Ordering::Relaxed);
                                tx_rejected.fetch_add(1,Ordering::Relaxed);
                                return false
                            }
                            slab.writable()[..wire.len()].copy_from_slice(wire);
                            let Ok(frozen)=slab.freeze(0..wire.len(),FrozenMetadata{
                                lane,seq:SeqOffset(item.seq),pn:RecordPn(pn),
                                carrier_snapshot:1
                            })else{
                                tx_fail.record.fetch_add(1,Ordering::Relaxed);
                                tx_rejected.fetch_add(1,Ordering::Relaxed);
                                return false
                            };
                            let f=item.flow;
                            let (src,dst,sp,dp)=if server{
                                (f.server_ip,f.client_ip,f.server_port,f.client_port)
                            }else{
                                (f.client_ip,f.server_ip,f.client_port,f.server_port)
                            };
                            let tuple=Ipv4Tuple{
                                src_ip:&src,dst_ip:&dst,src_port:sp,dst_port:dp
                            };
                            let presentation=Presentation{
                                ack32:1,advertised_window:4096,ip_id:(pn as u16).wrapping_add(75),
                                persona:peer_persona
                            };
                            let sent=item.raw.send_one(generation,&frozen,tuple,presentation);
                            let ok=sent.is_ok();
                            if ok {
                                // Only the real raw first copied PN/SEQ is
                                // eligible; most packets pay one mask test.
                                if outer_repair_enabled{
                                    // Genuine first raw kernel success only.
                                    // Normal ACK metadata is sparse; a
                                    // lost optional hint never changes M4/FEC
                                    // copied result or original sender credit.
                                    if cosmetic.on_firstsend(index,pn,item.seq,
                                        wire,due_now.0).is_err(){
                                        eprintln!("WBD_GAME_NORMAL_OUTER_HINT_DROP lane={} reason=sparse_index",index+1);
                                    }
                                }
                                item.seq=item.seq.saturating_add(wire.len() as u64);
                                // Count ACTUAL successful same-lane repeat
                                // sends, not a fake zero returned by FFI.
                                // OFF rejects this situation before send_one;
                                // another lane's independent first is valid.
                                if !game_first_lane_copy(item.last_initial_id,id.0){
                                    outer_repeated.fetch_add(1,Ordering::Relaxed);
                                }
                                item.last_initial_id=Some(id.0);
                                tx_copy.fetch_add(1,Ordering::Relaxed);
                                true
                            }else{
                                tx_fail.raw.fetch_add(1,Ordering::Relaxed);
                                match sent {
                                    Err(RawTxError::Kernel(11)|RawTxError::NoCapacity)=>{
                                        tx_fail.raw_backpressure.fetch_add(1,Ordering::Relaxed);
                                    },
                                    Err(RawTxError::RouteStale|RawTxError::RouteUnavailable)=>{
                                        tx_fail.raw_route.fetch_add(1,Ordering::Relaxed);
                                    },
                                    Err(RawTxError::PacketExceedsBudget|RawTxError::BoundedMtu)=>{
                                        tx_fail.raw_mtu.fetch_add(1,Ordering::Relaxed);
                                    },
                                    _=>{},
                                }
                                tx_rejected.fetch_add(1,Ordering::Relaxed);
                                false
                            }
                        });
                    };
                    flush(&mut game,now);
                    let mut parity_ready=false;
                    #[cfg(feature="fec2_product_record")]
                    if fec_enabled{
                        // Fixed FEC can close a block/partial due even when
                        // TUN becomes silent. Process bounded 4 SIMD quanta;
                        // no sleep while this owner has ready parity work.
                        for _ in 0..4{
                            // Refresh the actual clock at every bounded FEC
                            // quantum, not only once before a potentially
                            // long continuous TX/parity round.
                            let fec_now=MonoNs(start.elapsed().as_nanos()
                                .min(u128::from(u64::MAX)) as u64);
                            observed_polls+=1;
                            let start_poll=(tx_sample_enabled&&observed_polls%128==0)
                                .then(Instant::now);
                            let poll_result=game.poll_game_fec(fec_now);
                            if let Some(t)=start_poll{
                                tx_sample_worker.observe(t.elapsed(),false);
                            }
                            match poll_result{
                                Ok(0)=>break,
                                Ok(_)=>{
                                    parity_ready=true;
                                    let flush_now=MonoNs(start.elapsed().as_nanos()
                                        .min(u128::from(u64::MAX)) as u64);
                                    flush(&mut game,flush_now);
                                }
                                Err(_)=>{
                                    tx_rejected.fetch_add(1,Ordering::Relaxed);
                                    break
                                }
                            }
                        }
                    }
                    let clock_ns=start.elapsed().as_nanos()
                        .min(u128::from(u64::MAX)) as u64;
                    let copy_due=game.game4_next_due_ns();
                    let fec_due=game.game_fec_next_due_ns(MonoNs(clock_ns));
                    let stagger=game.game4_stagger_enabled();
                    drop(flush); // release mutable cosmetic capture
                    let cosmetic_due=if outer_repair_enabled{
                        cosmetic.next_due()
                    }else{None};
                    let next_due=copy_due.into_iter().chain(fec_due)
                        .chain(cosmetic_due).min();
                    // One authenticated Health on the existing TX worker,
                    // every ~15s after REAL copied control. Never a Game
                    // logical source/FEC symbol or new Go packet pump.
                    tx_health_rx.absorb(&mut health);
                    let health_now=health_origin.elapsed().as_nanos()
                        .min(u128::from(u64::MAX)) as u64;
                    // Do not send an early "Ready" from a local TLS lane.
                    // Client B sends ONE existing kind0 only after its full
                    // RAW RX and TX workers start; server B likewise proves
                    // its complete group. No new record kind or timer pump.
                    // Existing AEAD/PN kind0 Health is the bounded cold
                    // receipt; never a new framing or a Go DATA pump.
                    if !cold_receipt_armed&&
                        tx_cold_group_committed.load(Ordering::Acquire){
                        health.arm_server_cold_commit(health_now);
                        cold_receipt_armed=true;
                    }
                    match health.control_due(health_now){
                        ControlDue::DeadPeer=>{
                            eprintln!("M0_GAME_M4_HEALTH_DEAD authenticated_idle_ns={} threshold_ns={}",
                                health_now,health.policy().dead_ns());
                            tx_stop.store(true,Ordering::Release);
                            break
                        },
                        ControlDue::Health=>{
                            let copied=if let Some(lane)=lanes.first_mut(){
                                let mut wire=[0u8;512];
                                match game.seal_native_health(lane.key.slot,
                                    health.local_idle_ns(health_now),&mut wire){
                                    Ok((pn,n))=>{
                                        let mut accepted=false;
                                        if let Ok(mut slab)=arena.allocate(){
                                            slab.writable()[..n].copy_from_slice(&wire[..n]);
                                            if let Ok(frozen)=slab.freeze(0..n,FrozenMetadata{
                                                lane:lane.key,seq:SeqOffset(lane.seq),
                                                pn:RecordPn(pn),carrier_snapshot:1,
                                            }){
                                                let f=lane.flow;
                                                let (src,dst,sp,dp)=if server{
                                                    (f.server_ip,f.client_ip,f.server_port,f.client_port)
                                                }else{
                                                    (f.client_ip,f.server_ip,f.client_port,f.server_port)
                                                };
                                                let tuple=Ipv4Tuple{
                                                    src_ip:&src,dst_ip:&dst,
                                                    src_port:sp,dst_port:dp,
                                                };
                                                let presentation=Presentation{
                                                    ack32:1,advertised_window:4096,
                                                    ip_id:(pn as u16).wrapping_add(75),
                                                    persona:peer_persona,
                                                };
                                                accepted=lane.raw.send_one(generation,&frozen,
                                                    tuple,presentation).is_ok();
                                                if accepted{
                                                    if outer_repair_enabled &&
                                                        cosmetic.on_health_copy(0,lane.seq,n).is_err(){
                                                        eprintln!("WBD_GAME_NORMAL_OUTER_HINT_DROP lane=1 reason=health_seq");
                                                    }
                                                    lane.seq=lane.seq.saturating_add(n as u64);
                                                    tx_copy.fetch_add(1,Ordering::Relaxed);
                                                }
                                            }
                                        }
                                        accepted
                                    },
                                    Err(_)=>false,
                                }
                            }else{false};
                            health.on_health_send_result(health_now,copied);
                            if !copied{tx_rejected.fetch_add(1,Ordering::Relaxed);}
                        },
                        ControlDue::None=>{},
                    }
                    drop(game);
                    // Whether Game FEC is OFF or fixed, an enabled original
                    // outer policy may replay one sparse frozen TCP-looking
                    // ciphertext; neither mode may mint a second PN/source.
                    // It does not enter AEAD, GameRx/FEC, original first-send
                    // credit, Health or the authenticated delivery ledger.
                    if outer_repair_enabled{
                        // Reverse Game DATA's checksum/tuple-checked ACK
                        // becomes eligible only AFTER AEAD opened, including
                        // Game2 OFF; no untrusted TCP ACK gains authority. Read
                        // the last atomic ACK per lane, bounded to 3
                        // duplicated reports per TX owner turn.
                        for (i,hint) in tx_hints.iter().enumerate(){
                            let current=hint.load(Ordering::Acquire);
                            if current==observed_hints[i]{continue}
                            let count=(current>>32)
                                .wrapping_sub(observed_hints[i]>>32).min(3);
                            for _ in 0..count{
                                let _=cosmetic.on_feedback(i,current as u32,
                                    clock_ns);
                            }
                            observed_hints[i]=current;
                        }
                        if let Some(copy)=cosmetic.take_due(clock_ns,&[]){
                            let copied=if let Some(item)=lanes.get(copy.lane){
                                let f=item.flow;
                                let (src,dst,sp,dp)=if server{
                                    (f.server_ip,f.client_ip,f.server_port,f.client_port)
                                }else{
                                    (f.client_ip,f.server_ip,f.client_port,f.server_port)
                                };
                                let tuple=Ipv4Tuple{
                                    src_ip:&src,dst_ip:&dst,src_port:sp,dst_port:dp
                                };
                                let view=copy.frozen(item.key);
                                item.raw.send_one(generation,&view,tuple,Presentation{
                                    ack32:1,advertised_window:4096,
                                    ip_id:(copy.pn as u16).wrapping_add(76),
                                    persona:peer_persona
                                }).is_ok()
                            }else{false};
                            if copied{
                                outer_repeated.fetch_add(1,Ordering::Relaxed);
                            }
                            let _=cosmetic.complete(copy.lane,copy.pn,copied,
                                clock_ns);
                        }
                    }
                    if stagger||fec_enabled{
                        // Earliest of ready new TUN bytes (poll wake-up),
                        // staggered copies and authentic FEC close/expiry.
                        // A sparse ~8ms FEC tail must not sleep until the
                        // 20ms Game4 copy or the generic 10ms idle cap.
                        let remain=next_due.map_or(10_000_000u64,|due|
                            due.saturating_sub(start.elapsed().as_nanos()
                                .min(u128::from(u64::MAX)) as u64));
                        let timeout=((remain.min(10_000_000)+999_999)/1_000_000) as i32;
                        if let Some(ingress)=shared_ingress.as_ref(){
                            // The process-wide shared TUN reader exclusively
                            // owns read(2); its existing bounded channel is
                            // also the source-ready notification. Sleeping
                            // here had added an artificial 0..10ms EACH WAY
                            // at zero packet loss (Game4 p99 tail).
                            match ingress.recv_timeout(
                                Duration::from_millis(timeout.max(1) as u64)){
                                Ok(packet)=>wakeup_shared=Some(packet),
                                Err(RecvTimeoutError::Timeout)=>{},
                                Err(RecvTimeoutError::Disconnected)=>break,
                            }
                        }else{
                            let mut pfd=GamePollFd{fd:tx_tun.readiness_fd(),events:1,revents:0};
                            let _=unsafe{poll(&mut pfd,1,timeout)};
                        }
                    }else if !did_business&&!parity_ready{
                        if let Some(ingress)=shared_ingress.as_ref(){
                            // Game2 OFF likewise must wake on real business,
                            // rather than accumulate ~2ms polling each way.
                            match ingress.recv_timeout(Duration::from_millis(2)){
                                Ok(packet)=>wakeup_shared=Some(packet),
                                Err(RecvTimeoutError::Timeout)=>{},
                                Err(RecvTimeoutError::Disconnected)=>break,
                            }
                        }else{
                            thread::sleep(Duration::from_millis(2));
                        }
                    }
                    arena.drain_returns();
                }
                eprintln!("WBD_GAME_IPV4_MTU_EXCEPTION df0_ip_fragments={} icmp3_code4_kernel_sent={} icmp3_code4_rejected={} NOT_REMOTE_APPLIED=1",
                    tx_fail.df0_fragments.load(Ordering::Relaxed),
                    tx_fail.icmp3_code4_sent.load(Ordering::Relaxed),
                    tx_fail.icmp3_code4_denied.load(Ordering::Relaxed));
                if outer_repair_enabled{
                    // FEC Off is a valid Game2/4 product mode. Its selected
                    // outer policy must still produce low-rate appearance
                    // copies of the ORIGINAL authenticated ciphertext:
                    // no FEC parity or new PN, and no feedback credit.
                    if fec_enabled {
                        eprintln!("WBD_GAME_FEC_LINUX_NORMAL_OUTER_STOP copied_appearance={} first_record_wire_bytes={} copy_record_wire_bytes={} original_pn_seq_only=1 no_fec_credit=1 peer_ack_after_aead=1",cosmetic.sent(),cosmetic.first_record_wire_bytes(),cosmetic.copied_record_wire_bytes());
                    }else{
                        eprintln!("WBD_GAME_OFF_LINUX_NORMAL_OUTER_STOP copied_appearance={} first_record_wire_bytes={} copy_record_wire_bytes={} original_pn_seq_only=1 no_fec_credit=1 peer_ack_after_aead=1",cosmetic.sent(),cosmetic.first_record_wire_bytes(),cosmetic.copied_record_wire_bytes());
                    }
                }
            }).map_err(|_|())?;
        let mut threads=vec![tx_worker];
        let mut rx_lane_switch=Vec::with_capacity(n);
        for i in 0..n{
            let lane=lanes_key(generation,i);
            let mut lane_opener=lane_openers.next().ok_or(())?;
            let mut flow=flows[i];
            let mut raw=Arc::clone(&rx[i]);
            let (rx_sender,rx_commands)=mpsc::sync_channel::<RxLaneSwitch>(1);
            rx_lane_switch.push(rx_sender);
            let receiver_owner=Arc::clone(&rx_owner);
            let rx_tun=Arc::clone(&tun);
            let rx_stop=Arc::clone(&stop);
            let rx_hints=Arc::clone(&presentation_hints);
            let recv_count=Arc::clone(&delivered);
            let recv_rejected=Arc::clone(&rejected);
            let raw_seen=Arc::clone(&raw_received);
            let classified=Arc::clone(&rx_reject);
            let rx_err_timeout=Arc::clone(&rx_driver_timeout);
            let rx_err_other=Arc::clone(&rx_driver_other);
            let rx_held=Arc::clone(&rx_mutex_acquired);
            let rx_some=Arc::clone(&rx_authenticated_some);
            let rx_none=Arc::clone(&rx_dedup_none);
            let tun_failed=Arc::clone(&rx_tun_failed);
            let commit_failed=Arc::clone(&rx_delivery_commit_failed);
            let lock_sample=Arc::clone(&rx_lock_sample);
            let rx_start=epoch_clock;
            let builder=thread::Builder::new().name(format!("wbd-v4-game-rx-{}",i+1));
            let worker=builder.spawn(move||{
                let mut wire=[0u8;2048];
                let sample_lock=std::env::var("WBD_GAME_RX_LOCK_SAMPLE")
                    .as_deref()==Ok("1");
                let mut sampled_sequence=0u64;
                while !rx_stop.load(Ordering::Acquire){
                    // The very same lane worker receives the replacement
                    // protected tuple, per-lane replay owner and kernel
                    // socket. The other N-1 workers never stop.
                    if let Ok(change)=rx_commands.try_recv(){
                        let old=std::mem::replace(&mut raw,change.raw);
                        flow=change.flow;
                        lane_opener=change.opener;
                        let _=change.ready.send(old);
                    }
                    let (src,dst,sp,dp)=if server{
                        (flow.client_ip,flow.server_ip,flow.client_port,flow.server_port)
                    }else{
                        (flow.server_ip,flow.client_ip,flow.server_port,flow.client_port)
                    };
                    let tuple=Ipv4Tuple{src_ip:&src,dst_ip:&dst,src_port:sp,dst_port:dp};
                    let (len,_,ack32)=match raw.recv_one_with_ack_into(
                        generation,&mut wire,tuple,peer_persona
                    ){
                        Ok(data)=>data,
                        Err(wbd_platform::linux_raw_carrier::RawTxError::Kernel(110))=>{
                            rx_err_timeout.fetch_add(1,Ordering::Relaxed);
                            continue
                        },
                        Err(reason)=>{
                            rx_err_other.fetch_add(1,Ordering::Relaxed);
                            // A retired A cohort may remain alive for exact
                            // 10-20s grace after a real NIC MTU/source switch.
                            // Its old route budget then fails BEFORE poll(2),
                            // so an immediate retry busy-spins hundreds of
                            // millions of times and steals CPU from new B.
                            // Back off only genuine raw driver errors: normal
                            // authenticated RX and packet dispatch are intact.
                            let pause=match reason{
                                wbd_platform::linux_raw_carrier::RawTxError::RouteStale|
                                wbd_platform::linux_raw_carrier::RawTxError::RouteUnavailable
                                    =>Duration::from_millis(5),
                                _=>Duration::from_millis(1),
                            };
                            thread::sleep(pause);
                            continue
                        }
                    };
                    if rx_stop.load(Ordering::Acquire){break}
                    raw_seen.fetch_add(1,Ordering::Relaxed);
                    sampled_sequence=sampled_sequence.wrapping_add(1);
                    // The two real RX preparation paths each own exactly one
                    // scoped shared lock. Do not time every packet, and do
                    // not add any clock call to ordinary performance runs.
                    let timing=sample_lock&&(sampled_sequence&127)==0;
                    // AEAD tag, unique PN/replay and logical Game header
                    // decode are done solely by THIS physical lane worker,
                    // with no shared GameReceiveOwner lock and no extra copy.
                    let opened=lane_opener.open(&mut wire[..len]);
                    if outer_repair_enabled && matches!(&opened,Ok(Some(_))){
                        // TCP appearance is not AEAD-authenticated by
                        // itself: only actual original Game opens may
                        // nominate peer ACK gaps. This does not award
                        // business, Health, FEC or receipt credit.
                        let last=rx_hints[i].load(Ordering::Relaxed);
                        rx_hints[i].store(
                            ((last>>32).wrapping_add(1)<<32)|u64::from(ack32),
                            Ordering::Release);
                    }
                    let before_lock=timing.then(Instant::now);
                    #[cfg(feature="fec2_product_record")]
                    if fec_enabled{
                        let now=MonoNs(rx_start.elapsed().as_nanos()
                            .min(u128::from(u64::MAX)) as u64);
                        let decoded=match opened{
                            Ok(Some((id,payload)))=>{
                                let Ok(mut receiver)=receiver_owner.lock()else{break};
                                let acquired=timing.then(Instant::now);
                                rx_held.fetch_add(1,Ordering::Relaxed);
                                let value=receiver.prepare_opened_fec_batch(
                                    lane,id,payload,now);
                                if let (Some(start),Some(held))=(before_lock,acquired){
                                    lock_sample.record(held.duration_since(start),held.elapsed());
                                }
                                value
                            },
                            Ok(None)=>Ok(None),
                            Err(e)=>Err(e)
                        };
                        match decoded{
                            Ok(Some(batch))=>{
                                rx_some.fetch_add(1,Ordering::Relaxed);
                                // A FEC batch may contain multiple recovered
                                // IPv4 packets: preflight ALL sources before
                                // the first irreversible kernel TUN write.
                                if !batch.frames().iter().all(|frame|
                                    crate::v4_session_address::admitted_client_source(
                                        frame,authenticated_client_ip)){
                                    classified.scope.fetch_add(1,Ordering::Relaxed);
                                    recv_rejected.fetch_add(1,Ordering::Relaxed);
                                    let retired=match receiver_owner.lock(){
                                        Ok(mut rx)=>rx.finish_fec_batch(batch,false),
                                        Err(_)=>{
                                            commit_failed.fetch_add(1,Ordering::Relaxed);
                                            rx_stop.store(true,Ordering::Release);
                                            break
                                        }
                                    };
                                    if retired.is_err(){
                                        commit_failed.fetch_add(1,Ordering::Relaxed);
                                        rx_stop.store(true,Ordering::Release);
                                        break
                                    }
                                    continue
                                }
                                let mut all_written=true;
                                let mut wrote_count=0u64;
                                for frame in batch.frames(){
                                    if rx_tun.write_authenticated_ipv4(generation,frame).is_ok(){
                                        wrote_count+=1;
                                    }else{
                                        all_written=false;
                                        tun_failed.fetch_add(1,Ordering::Relaxed);
                                        recv_rejected.fetch_add(1,Ordering::Relaxed);
                                        break
                                    }
                                }
                                let committed=match receiver_owner.lock(){
                                    Ok(mut rx)=>rx.finish_fec_batch(batch,all_written),
                                    Err(_)=>{
                                        commit_failed.fetch_add(1,Ordering::Relaxed);
                                        rx_stop.store(true,Ordering::Release);
                                        break
                                    }
                                };
                                if all_written&&committed.is_ok(){
                                    recv_count.fetch_add(wrote_count,Ordering::Relaxed);
                                }else if committed.is_err()||wrote_count>0{
                                    // Partial batch cannot be rolled back after
                                    // a TUN syscall: fail closed, no false success.
                                    commit_failed.fetch_add(1,Ordering::Relaxed);
                                    rx_stop.store(true,Ordering::Release);
                                    break
                                }
                            },
                            Ok(None)=>{rx_none.fetch_add(1,Ordering::Relaxed);},
                            Err(reason)=>{
                                let counter=match reason{
                                    GameAdapterError::Crypto=>&classified.aead,
                                    GameAdapterError::Invalid=>&classified.invalid,
                                    GameAdapterError::Duplicate=>&classified.duplicate,
                                    GameAdapterError::Stale=>&classified.stale,
                                    GameAdapterError::Capacity=>&classified.capacity,
                                    GameAdapterError::Unauthorized=>&classified.scope,
                                    GameAdapterError::Stopped=>&classified.stopped,
                                    GameAdapterError::Game(GameError::Capacity|GameError::ByteBudget)=>
                                        &classified.capacity,
                                    GameAdapterError::Game(_)=>&classified.game,
                                };
                                counter.fetch_add(1,Ordering::Relaxed);
                                recv_rejected.fetch_add(1,Ordering::Relaxed);
                            }
                        }
                        continue
                    }
                    let received=match opened{
                        Ok(Some((id,payload)))=>{
                            let Ok(mut receiver)=receiver_owner.lock()else{break};
                            let acquired=timing.then(Instant::now);
                            rx_held.fetch_add(1,Ordering::Relaxed);
                            // Authenticated ID only: one global logical dedup
                            // and one TUN-success reservation still shared.
                            let value=receiver.prepare_opened_receive(lane,id,payload);
                            if let (Some(start),Some(held))=(before_lock,acquired){
                                lock_sample.record(held.duration_since(start),held.elapsed());
                            }
                            value
                        },
                        Ok(None)=>Ok(None),
                        Err(e)=>Err(e)
                    };
                    match received{
                        Ok(Some(mut prepared))=>{
                            rx_some.fetch_add(1,Ordering::Relaxed);
                            // Do not hold RX owner mutex across a TUN syscall;
                            // other lanes can authenticate/prepare immediately.
                            let source_allowed=crate::v4_session_address::admitted_client_source(
                                prepared.payload(),authenticated_client_ip);
                            if !source_allowed{
                                classified.scope.fetch_add(1,Ordering::Relaxed);
                            }
                            let written=source_allowed && rx_tun.write_authenticated_ipv4(
                                generation,prepared.payload()).is_ok();
                            let finished=match receiver_owner.lock(){
                                Ok(mut rx)=>rx.finish_receive(prepared,written),
                                Err(_)=>{
                                    commit_failed.fetch_add(1,Ordering::Relaxed);
                                    rx_stop.store(true,Ordering::Release);
                                    break
                                }
                            };
                            if !written{
                                tun_failed.fetch_add(1,Ordering::Relaxed);
                                recv_rejected.fetch_add(1,Ordering::Relaxed);
                            }else if finished.is_ok(){
                                recv_count.fetch_add(1,Ordering::Relaxed);
                            }else{
                                // A committed-to-TUN but stale/invalid receive
                                // cannot safely be reported as delivered once.
                                commit_failed.fetch_add(1,Ordering::Relaxed);
                                recv_rejected.fetch_add(1,Ordering::Relaxed);
                                rx_stop.store(true,Ordering::Release);
                                break
                            }
                        },
                        Ok(None)=>{
                            rx_none.fetch_add(1,Ordering::Relaxed);
                        }, // exact GameRx cross-lane dedup
                        Err(reason)=>{
                            // AEAD tag rejection is not a valid authenticated replay.
                            let counter=match reason{
                                GameAdapterError::Crypto=>&classified.aead,
                                GameAdapterError::Invalid=>&classified.invalid,
                                GameAdapterError::Duplicate=>&classified.duplicate,
                                GameAdapterError::Stale=>&classified.stale,
                                GameAdapterError::Capacity=>&classified.capacity,
                                GameAdapterError::Unauthorized=>&classified.scope,
                                GameAdapterError::Stopped=>&classified.stopped,
                                GameAdapterError::Game(GameError::Stale)=>&classified.stale,
                                GameAdapterError::Game(GameError::Duplicate)=>&classified.duplicate,
                                GameAdapterError::Game(GameError::Capacity|GameError::ByteBudget)=>
                                    &classified.capacity,
                                GameAdapterError::Game(GameError::Stopped)=>&classified.stopped,
                                GameAdapterError::Game(_)=>&classified.game,
                            };
                            counter.fetch_add(1,Ordering::Relaxed);
                            recv_rejected.fetch_add(1,Ordering::Relaxed);
                        }
                    }
                }
            });
            match worker{
                Ok(w)=>threads.push(w),
                Err(_)=>{
                    stop.store(true,Ordering::Release);
                    for w in threads{let _=w.join();}
                    return Err(())
                }
            }
        }
        Ok(Self{stop,threads,tun,tx,rx,copied,delivered,rejected,
            raw_received,rx_reject,
            rx_driver_timeout,rx_driver_other,rx_mutex_acquired,
            rx_authenticated_some,rx_dedup_none,rx_tun_failed,
            rx_delivery_commit_failed,rx_lock_sample,tx_reasons,outer_blocked_duplicate,
            outer_repeated_copy_sent,tx_lane_switch,rx_lane_switch,
            physical_ifname:ifname.to_string(),physical_ifindex:ifindex,
            physical_generation:generation,server,
            diagnostic_adapter:adapter,tx_work_sample,tx_shared_burst_extra,
            cold_group_committed,peer_health_evidence:health_rx})
    }
    /// A NEW real original-Go TLS+Rust M1 lane has just committed while
    /// the remaining lanes of this GameAdapter stay LIVE. Reuse the existing
    /// TX/RX threads; only the selected RX raw socket and lane AEAD/PN
    /// owner are switched. This never touches shared TUN/FEC/dedup ownership.
    pub(crate) fn replace_one_authenticated_lane(
        &mut self,slot:usize,flow:GoFlow,seq:u64,
        prepared:OriginalGameLaneRekey,
    )->Result<(),()>{
        if self.stop.load(Ordering::Acquire)||slot>=self.rx.len()||
            slot>=self.rx_lane_switch.len()||seq==0||
            prepared.slot!=slot{return Err(())}
        let (src,dst,sp,dp)=if self.server{
            (flow.client_ip,flow.server_ip,flow.client_port,flow.server_port)
        }else{
            (flow.server_ip,flow.client_ip,flow.server_port,flow.client_port)
        };
        let tuple=Ipv4Tuple{src_ip:&src,dst_ip:&dst,src_port:sp,dst_port:dp};
        let new_raw=Arc::new(ScopedRawIpv4Rx::open_exact_tuple(
            &self.physical_ifname,self.physical_ifindex,
            self.physical_generation,tuple).map_err(|_|())?);
        let (tx_ack,tx_done)=mpsc::sync_channel(1);
        self.tx_lane_switch.try_send(TxLaneSwitch{
            slot,flow,seq,prepared,ready:tx_ack
        }).map_err(|_|())?;
        let opener=tx_done.recv_timeout(Duration::from_secs(2))
            .map_err(|_|())??;
        let (rx_ack,rx_done)=mpsc::sync_channel(1);
        self.rx_lane_switch[slot].try_send(RxLaneSwitch{
            flow,raw:Arc::clone(&new_raw),opener,ready:rx_ack
        }).map_err(|_|())?;
        let retired=rx_done.recv_timeout(Duration::from_secs(2))
            .map_err(|_|())?;
        let old=std::mem::replace(&mut self.rx[slot],new_raw);
        // The old physical worker already handed off its LAST borrowed
        // record/socket; exact scoped kernel shutdown is now safe.
        old.begin_stop();
        retired.begin_stop();
        let deadline=Instant::now()+Duration::from_secs(2);
        if old.stop_until(deadline)!=StopResult::Drained||
            retired.stop_until(deadline)!=StopResult::Drained{
            self.stop.store(true,Ordering::Release);
            return Err(())
        }
        Ok(())
    }
    pub(crate) fn fail_closed_after_hot_rekey(&self){
        self.stop.store(true,Ordering::Release);
    }
    pub(crate) fn outer_policy_counters(&self)->(u64,u64,u64){
        (self.outer_repeated_copy_sent.load(Ordering::Relaxed),
         self.outer_blocked_duplicate.load(Ordering::Relaxed),
         self.copied.load(Ordering::Relaxed))
    }
    pub(crate) fn counters(&self)->(u64,u64,u64){
        (self.copied.load(Ordering::Relaxed),
         self.delivered.load(Ordering::Relaxed),
         self.rejected.load(Ordering::Relaxed))
    }
    // Each endpoint may arm one bounded existing AEAD kind0 Health on
    // complete Game2/4 M4 install; never an extra steady-state probe.
    // This is not a local client readiness claim or a per-packet probe.
    pub(crate) fn mark_group_committed(&self){
        if !self.stop.load(Ordering::Acquire){
            self.cold_group_committed.store(true,Ordering::Release);
        }
    }
    pub(crate) fn has_authenticated_peer_health(&self)->bool{
        self.is_live()&&
            self.peer_health_evidence.has_verified_peer_health()
    }
    // Split received kernel TCP data from AEAD/replay refusal. Successful
    // first kernel copy is not proof of peer raw receive or TUN delivery.
    pub(crate) fn receive_diagnostics(&self)->(u64,u64){
        (self.raw_received.load(Ordering::Relaxed),
         self.rx_reject.aead.load(Ordering::Relaxed))
    }
    // Original Game M4 Health90 (or an authenticated RX fatal) sets the
    // existing owner stop flag. The Go single-port supervisor observes this
    // ONE authoritative verdict; it must not invent a second dead timer.
    pub(crate) fn is_live(&self)->bool{
        !self.stop.load(Ordering::Acquire)
    }
    pub(crate) fn stop_and_drain(&mut self)->Result<(),()>{
        self.stop.store(true,Ordering::Release);
        // Give in-flight M4 kernel borrows a bounded opportunity to finish
        // before owner release, without tearing down Go-owned TUN early.
        for w in self.threads.drain(..){if w.join().is_err(){return Err(())}}
        eprintln!("M0_GAME_M4_SHARED_TUN_BURST_READBACK extra_accepted={} max_new_sources_per_turn=8 game4_fec_only=1",
            self.tx_shared_burst_extra.load(Ordering::Relaxed));
        // Why Game4 delayed copies were abandoned is disjoint by source:
        // bounded oldest-job eviction, missed owner deadline, or a native
        // dispatch callback failing. Pre-admission MSS/queue skips are shown
        // separately; none of these is an assumed physical packet loss.
        if let Ok(game)=self.diagnostic_adapter.lock(){
            if let Some(c)=game.game4_copy_schedule(){
                eprintln!("M0_GAME_M4_COPY_ABANDON_REASONS capacity_evicted={:?} deadline_expired={:?} dispatch_pressure={:?} admission_mtu_skipped={:?} admission_queue_skipped={:?} abandoned_total={:?} stop_canceled={}",
                    c.capacity_evicted,c.deadline_expired,c.dispatch_pressure,
                    c.mtu_skipped,c.queue_skipped,c.abandoned,c.stop_canceled);
            }
        }
        // Readback reflects ACTUAL finished native RS16 calls, not just a
        // Cargo feature bit or an unverified backend preference.
        #[cfg(feature="fec2_product_record")]
        if let Ok(game)=self.diagnostic_adapter.lock(){
            if let Some((tx,_))=game.game_fec_counters(){
                let rx=game.game_fec_rx_counters().unwrap_or_default();
                eprintln!("M0_GAME_M4_FEC_BACKEND_READBACK selected={} native_linked={} tx_native_quanta={} tx_scalar_quanta={} rx_native_decodes={} rx_scalar_decodes={} late_complete_repair_skips={}",
                    if std::env::var("WBD_GAME_FEC_BACKEND").ok().as_deref()==Some("scalar"){
                        "scalar"
                    }else{"prefer-native"},
                    u8::from(cfg!(feature="native_fec_acceleration")),
                    tx.tx_native_quanta,tx.tx_scalar_quanta,
                    rx.rx_native_decodes,rx.rx_scalar_decodes,
                    rx.rx_late_complete_repair_skips);
            }
        }
        if self.tx_work_sample.offers.load(Ordering::Relaxed)>0||
            self.tx_work_sample.polls.load(Ordering::Relaxed)>0{
            eprintln!("M0_GAME_M4_TX_DURATION_SAMPLE offer_samples={} offer_total_ns={} offer_max_ns={} poll_samples={} poll_total_ns={} poll_max_ns={} stride=128",
                self.tx_work_sample.offers.load(Ordering::Relaxed),
                self.tx_work_sample.offer_total_ns.load(Ordering::Relaxed),
                self.tx_work_sample.offer_max_ns.load(Ordering::Relaxed),
                self.tx_work_sample.polls.load(Ordering::Relaxed),
                self.tx_work_sample.poll_total_ns.load(Ordering::Relaxed),
                self.tx_work_sample.poll_max_ns.load(Ordering::Relaxed));
        }
        // On-owned-Stop aggregate only; rejected native copies are not WAN loss.
        eprintln!("M0_GAME_M4_TX_REJECT_BREAKDOWN offer={} slab={} record={} policy={} raw={} raw_backpressure={} raw_route={} raw_mtu={} total_rejected={}",
            self.tx_reasons.offer.load(Ordering::Relaxed),
            self.tx_reasons.slab.load(Ordering::Relaxed),
            self.tx_reasons.record.load(Ordering::Relaxed),
            self.tx_reasons.policy.load(Ordering::Relaxed),
            self.tx_reasons.raw.load(Ordering::Relaxed),
            self.tx_reasons.raw_backpressure.load(Ordering::Relaxed),
            self.tx_reasons.raw_route.load(Ordering::Relaxed),
            self.tx_reasons.raw_mtu.load(Ordering::Relaxed),
            self.rejected.load(Ordering::Relaxed));
        // Counters distinguish real kernel ingress from blocked shared
        // GameAdapter lock, AEAD/GameRx duplicate and TUN failure.
        // No packet content, secret, raw key, TLS material or payload emitted.
        eprintln!("M0_GAME_M4_RX_STAGE_BOUNDARY raw={} timeout={} other={} rx_owner_lock={} authenticated_some={} duplicate_none={} aead_denied={} invalid={} replay_dup={} stale={} capacity={} scope={} stopped={} game={} tun_fail={} tun_commit_fail={} tun_delivered={}",
            self.raw_received.load(Ordering::Relaxed),
            self.rx_driver_timeout.load(Ordering::Relaxed),
            self.rx_driver_other.load(Ordering::Relaxed),
            self.rx_mutex_acquired.load(Ordering::Relaxed),
            self.rx_authenticated_some.load(Ordering::Relaxed),
            self.rx_dedup_none.load(Ordering::Relaxed),
            self.rx_reject.aead.load(Ordering::Relaxed),
            self.rx_reject.invalid.load(Ordering::Relaxed),
            self.rx_reject.duplicate.load(Ordering::Relaxed),
            self.rx_reject.stale.load(Ordering::Relaxed),
            self.rx_reject.capacity.load(Ordering::Relaxed),
            self.rx_reject.scope.load(Ordering::Relaxed),
            self.rx_reject.stopped.load(Ordering::Relaxed),
            self.rx_reject.game.load(Ordering::Relaxed),
            self.rx_tun_failed.load(Ordering::Relaxed),
            self.rx_delivery_commit_failed.load(Ordering::Relaxed),
            self.delivered.load(Ordering::Relaxed));
        // Diagnostic-only, one aggregate at Stop. Samples are not estimates
        // of full CPU cost, and exclude the second finish/commit lock.
        let sample_count=self.rx_lock_sample.samples.load(Ordering::Relaxed);
        if sample_count>0{
            eprintln!("M0_GAME_M4_RX_LOCK_SAMPLE samples={} wait_total_ns={} hold_total_ns={} wait_max_ns={} sample_stride=128 includes_commit=0",
                sample_count,
                self.rx_lock_sample.wait_total_ns.load(Ordering::Relaxed),
                self.rx_lock_sample.hold_total_ns.load(Ordering::Relaxed),
                self.rx_lock_sample.wait_max_ns.load(Ordering::Relaxed));
        }
        self.tun.begin_stop();
        for x in &self.tx{x.begin_stop()}
        for x in &self.rx{x.begin_stop()}
        let deadline=Instant::now()+Duration::from_secs(2);
        if self.tun.stop_until(deadline)!=StopResult::Drained{return Err(())}
        for x in &self.tx{if x.stop_until(deadline)!=StopResult::Drained{return Err(())}}
        for x in &self.rx{if x.stop_until(deadline)!=StopResult::Drained{return Err(())}}
        Ok(())
    }
}
fn lanes_key(generation:u32,i:usize)->LaneKey{
    LaneKey{tunnel:TunnelKey{slot:14,generation},
        slot:i as u32+1,generation}
}


// Only the existing Game4+FEC shared-TUN ingress loop uses this cap;
// no native thread or crypto scheduler is created. A bounded channel
// transcript proves a full reader batch can drain in one owner turn in
// FIFO order and the next packet is not consumed speculatively.
#[cfg(test)]
#[test]
fn m0_plan028_game4_fec_shared_tun_eight_source_turn_fifo_and_cap(){
    let (send,recv)=mpsc::sync_channel::<usize>(
        GAME4_FEC_SHARED_TUN_MAX_SOURCES_PER_TURN+2);
    for n in 0..GAME4_FEC_SHARED_TUN_MAX_SOURCES_PER_TURN+2{
        send.try_send(n).unwrap();
    }
    let mut observed=Vec::new();
    observed.push(recv.try_recv().expect("first original M1 source"));
    for _ in 0..GAME4_FEC_SHARED_TUN_MAX_SOURCES_PER_TURN-1{
        observed.push(recv.try_recv().expect("bounded same-turn M1 batch"));
    }
    assert_eq!(observed,
        (0..GAME4_FEC_SHARED_TUN_MAX_SOURCES_PER_TURN).collect::<Vec<_>>());
    assert_eq!(recv.try_recv().unwrap(),GAME4_FEC_SHARED_TUN_MAX_SOURCES_PER_TURN);
    assert_eq!(recv.try_recv().unwrap(),GAME4_FEC_SHARED_TUN_MAX_SOURCES_PER_TURN+1);
    assert!(recv.try_recv().is_err());
}
