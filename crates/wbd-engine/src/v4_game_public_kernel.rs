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

struct TxLane{
    key:LaneKey,flow:GoFlow,seq:u64,raw:Arc<ScopedRawIpv4Tx>
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
}
impl GameKernelOwner{
    pub(crate) fn start(
        adapter:Arc<Mutex<GameAdapter>>,flows:Vec<GoFlow>,seqs:Vec<u64>,
        server:bool,ifname:&str,ifindex:u32,fd:OwnedFd,tun_name:&str,
        generation:u32,
    )->Result<Self,()>{
        let n=flows.len();
        if !matches!(n,2|4)||seqs.len()!=n||generation==0||
            ifindex==0||ifname.is_empty()||tun_name.is_empty()||
            tun_name.len()>15||seqs.contains(&0){return Err(())}
        let tun=Arc::new(ScopedTunSink::from_owned_fd(fd,generation,tun_name)
            .map_err(|_|())?);
        let mut tx=Vec::with_capacity(n);
        let mut rx=Vec::with_capacity(n);
        for _ in 0..n{
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
        let mut lanes=Vec::new();
        for i in 0..n{
            lanes.push(TxLane{
                key:LaneKey{tunnel:TunnelKey{slot:14,generation},
                    slot:i as u32+1,generation},
                flow:flows[i],seq:seqs[i],raw:Arc::clone(&tx[i])
            });
        }
        let tx_adapter=Arc::clone(&adapter);
        let tx_stop=Arc::clone(&stop);
        let tx_tun=Arc::clone(&tun);
        let tx_copy=Arc::clone(&copied);
        let tx_rejected=Arc::clone(&rejected);
        let inner_mtu=adapter.lock().map_err(|_|())?.inner_mtu();
        let tx_worker=thread::Builder::new().name("wbd-v4-game-tx".into())
            .spawn(move||{
                let Ok(mut arena)=Arena::new(generation^0x4000_0000,64,2048,64,1_000_000)
                    else{return};
                let start=Instant::now();
                let mut inbound=[0u8;2048];
                while !tx_stop.load(Ordering::Acquire){
                    // Never hold the TUN device's shared serialized mutex
                    // during a 750ms missing-app poll: authenticated RX
                    // needs the SAME device mutex for first-delivery write.
                    // Ready-only poll(0) holds it only for an actual read.
                    let mut slots:[&mut [u8];1]=[&mut inbound];
                    let len=match tx_tun.read_ready_batch(generation,&mut slots){
                        Ok(batch)=>match batch.entry(0){
                            Some(TunReadyEntry::UntrustedIpv4{len})=>len,
                            Some(TunReadyEntry::Rejected)=>{
                                tx_rejected.fetch_add(1,Ordering::Relaxed);
                                continue
                            },
                            _=>{
                                // Bounded 2ms idle wait yields to peer RX/TUN
                                // and limits empty-device wakes to <=500/s.
                                thread::sleep(Duration::from_millis(2));
                                continue
                            }
                        },
                        Err(_)=>{
                            if tx_stop.load(Ordering::Acquire){break}
                            tx_rejected.fetch_add(1,Ordering::Relaxed);
                            thread::sleep(Duration::from_millis(2));
                            continue
                        }
                    };
                    if len==0||len>inner_mtu{
                        tx_rejected.fetch_add(1,Ordering::Relaxed);continue
                    }
                    let now=MonoNs(start.elapsed().as_nanos().min(u128::from(u64::MAX)) as u64);
                    let Ok(mut game)=tx_adapter.lock()else{break};
                    if game.offer(&inbound[..len],now).is_err(){
                        tx_rejected.fetch_add(1,Ordering::Relaxed);continue
                    }
                    game.drain(now,|lane,_,pn,wire|{
                        let Some(item)=lanes.iter_mut().find(|x|x.key==lane) else{
                            tx_rejected.fetch_add(1,Ordering::Relaxed);
                            return false
                        };
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
                            persona:PacketPersona::Legacy
                        };
                        let ok=item.raw.send_one(generation,&frozen,tuple,presentation)
                            .is_ok();
                        if ok {
                            item.seq=item.seq.saturating_add(wire.len() as u64);
                            tx_copy.fetch_add(1,Ordering::Relaxed);
                            true
                        }else{
                            tx_rejected.fetch_add(1,Ordering::Relaxed);
                            false
                        }
                    });
                    arena.drain_returns();
                }
            }).map_err(|_|())?;
        let mut threads=vec![tx_worker];
        for i in 0..n{
            let lane=lanes_key(generation,i);
            let flow=flows[i];
            let raw=Arc::clone(&rx[i]);
            let client_rx_adapter=Arc::clone(&adapter);
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
            let builder=thread::Builder::new().name(format!("wbd-v4-game-rx-{}",i+1));
            let worker=builder.spawn(move||{
                let (src,dst,sp,dp)=if server{
                    (flow.client_ip,flow.server_ip,flow.client_port,flow.server_port)
                }else{
                    (flow.server_ip,flow.client_ip,flow.server_port,flow.client_port)
                };
                let tuple=Ipv4Tuple{src_ip:&src,dst_ip:&dst,src_port:sp,dst_port:dp};
                let mut wire=[0u8;2048];
                while !rx_stop.load(Ordering::Acquire){
                    let (len,_)=match raw.recv_one_into(
                        generation,&mut wire,tuple,PacketPersona::Legacy
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
                    let received={
                        let Ok(mut game)=client_rx_adapter.lock()else{break};
                        rx_held.fetch_add(1,Ordering::Relaxed);
                        game.receive(lane,wire[..len].to_vec())
                    };
                    match received{
                        Ok(Some(plaintext))=>{
                            rx_some.fetch_add(1,Ordering::Relaxed);
                            if rx_tun.write_authenticated_ipv4(generation,&plaintext).is_ok(){
                                recv_count.fetch_add(1,Ordering::Relaxed);
                            }else{
                                tun_failed.fetch_add(1,Ordering::Relaxed);
                                recv_rejected.fetch_add(1,Ordering::Relaxed);
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
            rx_authenticated_some,rx_dedup_none,rx_tun_failed})
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
        eprintln!("M0_GAME_M4_RX_STAGE_BOUNDARY raw={} timeout={} other={} adapter_lock={} authenticated_some={} duplicate_none={} aead_denied={} invalid={} replay_dup={} stale={} capacity={} scope={} stopped={} game={} tun_fail={} tun_delivered={}",
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
            self.delivered.load(Ordering::Relaxed));
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
