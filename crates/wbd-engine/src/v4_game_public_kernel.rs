//! M0 actual original TLS grouped Game2/4 M4 Linux kernel worker.
//! One GameAdapter is authenticated by already-committed protected Go lane
//! handles. Raw/TUN are the genuine M4 scoped driver, not a shadow/Go proxy.
//! Opt-in only; still not a public CLI product qualification without real
//! end-to-end application/Stop Actions for both executable processes.
#![allow(unsafe_code)]
use std::os::fd::OwnedFd;
use std::sync::{Arc,Mutex,atomic::{AtomicBool,AtomicU64,Ordering}};
use std::thread::{self,JoinHandle};
use std::time::{Instant,Duration};
use crate::v4_game_lane::{GameAdapter,Error as GameAdapterError};
use crate::runtime::game_shared::GameError;
use crate::v4_protected_handoff::GoFlow;
use crate::memory::Arena;
use wbd_types::{MonoNs,RecordPn,SeqOffset,LaneKey,TunnelKey};
use wbd_types::buffer_contract::{FrozenMetadata,UniqueSealable};
use wbd_platform::linux_raw_carrier::{ScopedRawIpv4Tx,ScopedRawIpv4Rx};
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
    rx_lock_sample:Arc<RxLockSample>,
    outer_blocked_duplicate:Arc<AtomicU64>,
    outer_repeated_copy_sent:Arc<AtomicU64>,
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
        peer_persona:PacketPersona,
    )->Result<Self,()>{
        let n=flows.len();
        if !matches!(n,2|4)||seqs.len()!=n||generation==0||
            ifindex==0||ifname.is_empty()||tun_name.is_empty()||
            tun_name.len()>15||seqs.contains(&0){return Err(())}
        let tun=Arc::new(ScopedTunSink::from_owned_fd(fd,generation,tun_name)
            .map_err(|_|())?);
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
        let tx_adapter=Arc::clone(&adapter);
        let tx_stop=Arc::clone(&stop);
        let tx_tun=Arc::clone(&tun);
        let tx_copy=Arc::clone(&copied);
        let tx_rejected=Arc::clone(&rejected);
        let outer_denied=Arc::clone(&outer_blocked_duplicate);
        let outer_repeated=Arc::clone(&outer_repeated_copy_sent);
        #[allow(unused_variables)]
        let (inner_mtu,rx_owner,fec_enabled)={
            let game=adapter.lock().map_err(|_|())?;
            (game.inner_mtu(),game.receiver_handle(),game.has_game_fec())
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
        let tx_worker=thread::Builder::new().name("wbd-v4-game-tx".into())
            .spawn(move||{
                let Ok(mut arena)=Arena::new(generation^0x4000_0000,64,2048,64,1_000_000)
                    else{return};
                let start=epoch_clock;
                let mut inbound=[0u8;2048];
                while !tx_stop.load(Ordering::Acquire){
                    // Never hold the TUN device's shared serialized mutex
                    // during a 750ms missing-app poll: authenticated RX
                    // needs the SAME device mutex for first-delivery write.
                    // Ready-only poll(0) holds it only for an actual read.
                    let mut slots:[&mut [u8];1]=[&mut inbound];
                    let size=match tx_tun.read_ready_batch(generation,&mut slots){
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
                    };
                    let now=MonoNs(start.elapsed().as_nanos().min(u128::from(u64::MAX)) as u64);
                    let Ok(mut game)=tx_adapter.lock()else{break};
                    let mut did_business=false;
                    if let Some(len)=size{
                        if len>0&&len<=inner_mtu{
                            did_business=true;
                            if game.offer(&inbound[..len],now).is_err(){
                                tx_rejected.fetch_add(1,Ordering::Relaxed);
                            }
                        }else if len!=0{
                            tx_rejected.fetch_add(1,Ordering::Relaxed);
                        }
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
                                outer_denied.fetch_add(1,Ordering::Relaxed);
                                tx_rejected.fetch_add(1,Ordering::Relaxed);
                                return false
                            }
                            let Ok(mut slab)=arena.allocate()else{
                                tx_rejected.fetch_add(1,Ordering::Relaxed);
                                return false
                            };
                            if wire.len()>slab.writable().len(){
                                tx_rejected.fetch_add(1,Ordering::Relaxed);
                                return false
                            }
                            slab.writable()[..wire.len()].copy_from_slice(wire);
                            let Ok(frozen)=slab.freeze(0..wire.len(),FrozenMetadata{
                                lane,seq:SeqOffset(item.seq),pn:RecordPn(pn),
                                carrier_snapshot:1
                            })else{
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
                            let ok=item.raw.send_one(generation,&frozen,tuple,presentation)
                                .is_ok();
                            if ok {
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
                            match game.poll_game_fec(fec_now){
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
                    let next_due=copy_due.into_iter().chain(fec_due).min();
                    let stagger=game.game4_stagger_enabled();
                    drop(flush);drop(game);
                    if stagger||fec_enabled{
                        // Earliest of ready new TUN bytes (poll wake-up),
                        // staggered copies and authentic FEC close/expiry.
                        // A sparse ~8ms FEC tail must not sleep until the
                        // 20ms Game4 copy or the generic 10ms idle cap.
                        let remain=next_due.map_or(10_000_000u64,|due|
                            due.saturating_sub(start.elapsed().as_nanos()
                                .min(u128::from(u64::MAX)) as u64));
                        let timeout=((remain.min(10_000_000)+999_999)/1_000_000) as i32;
                        let mut pfd=GamePollFd{fd:tx_tun.readiness_fd(),events:1,revents:0};
                        let _=unsafe{poll(&mut pfd,1,timeout)};
                    }else if !did_business&&!parity_ready{
                        thread::sleep(Duration::from_millis(2));
                    }
                    arena.drain_returns();
                }
            }).map_err(|_|())?;
        let mut threads=vec![tx_worker];
        for i in 0..n{
            let lane=lanes_key(generation,i);
            let mut lane_opener=lane_openers.next().ok_or(())?;
            let flow=flows[i];
            let raw=Arc::clone(&rx[i]);
            let receiver_owner=Arc::clone(&rx_owner);
            let rx_tun=Arc::clone(&tun);
            let rx_stop=Arc::clone(&stop);
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
                let (src,dst,sp,dp)=if server{
                    (flow.client_ip,flow.server_ip,flow.client_port,flow.server_port)
                }else{
                    (flow.server_ip,flow.client_ip,flow.server_port,flow.client_port)
                };
                let tuple=Ipv4Tuple{src_ip:&src,dst_ip:&dst,src_port:sp,dst_port:dp};
                let mut wire=[0u8;2048];
                let sample_lock=std::env::var("WBD_GAME_RX_LOCK_SAMPLE")
                    .as_deref()==Ok("1");
                let mut sampled_sequence=0u64;
                while !rx_stop.load(Ordering::Acquire){
                    let (len,_)=match raw.recv_one_into(
                        generation,&mut wire,tuple,peer_persona
                    ){
                        Ok(data)=>data,
                        Err(wbd_platform::linux_raw_carrier::RawTxError::Kernel(110))=>{
                            rx_err_timeout.fetch_add(1,Ordering::Relaxed);
                            continue
                        },
                        Err(_)=>{
                            rx_err_other.fetch_add(1,Ordering::Relaxed);
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
                    let before_lock=timing.then(Instant::now);
                    #[cfg(feature="fec2_product_record")]
                    if fec_enabled{
                        let now=MonoNs(rx_start.elapsed().as_nanos()
                            .min(u128::from(u64::MAX)) as u64);
                        let decoded=match opened{
                            Ok((id,payload))=>{
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
                            Err(e)=>Err(e)
                        };
                        match decoded{
                            Ok(Some(batch))=>{
                                rx_some.fetch_add(1,Ordering::Relaxed);
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
                        Ok((id,payload))=>{
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
                        Err(e)=>Err(e)
                    };
                    match received{
                        Ok(Some(mut prepared))=>{
                            rx_some.fetch_add(1,Ordering::Relaxed);
                            // Do not hold RX owner mutex across a TUN syscall;
                            // other lanes can authenticate/prepare immediately.
                            let written=rx_tun.write_authenticated_ipv4(
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
            rx_delivery_commit_failed,rx_lock_sample,outer_blocked_duplicate,
            outer_repeated_copy_sent})
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
    // Split received kernel TCP data from AEAD/replay refusal. Successful
    // first kernel copy is not proof of peer raw receive or TUN delivery.
    pub(crate) fn receive_diagnostics(&self)->(u64,u64){
        (self.raw_received.load(Ordering::Relaxed),
         self.rx_reject.aead.load(Ordering::Relaxed))
    }
    pub(crate) fn stop_and_drain(&mut self)->Result<(),()>{
        self.stop.store(true,Ordering::Release);
        // Give in-flight M4 kernel borrows a bounded opportunity to finish
        // before owner release, without tearing down Go-owned TUN early.
        for w in self.threads.drain(..){if w.join().is_err(){return Err(())}}
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
