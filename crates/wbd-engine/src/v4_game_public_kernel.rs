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
use crate::v4_game_lane::GameAdapter;
use crate::v4_protected_handoff::GoFlow;
use crate::memory::Arena;
use wbd_types::{MonoNs,RecordPn,SeqOffset,LaneKey,TunnelKey};
use wbd_types::buffer_contract::{FrozenMetadata,UniqueSealable};
use wbd_platform::linux_raw_carrier::{ScopedRawIpv4Tx,ScopedRawIpv4Rx};
use wbd_platform::linux_tun_sink::ScopedTunSink;
use wbd_platform::ipv4_tcp::{Ipv4Tuple,PacketPersona,Presentation};
use wbd_platform::r1::StopResult;

struct TxLane{
    key:LaneKey,flow:GoFlow,seq:u64,raw:Arc<ScopedRawIpv4Tx>
}
pub(crate) struct GameKernelOwner{
    stop:Arc<AtomicBool>,threads:Vec<JoinHandle<()>>,
    tun:Arc<ScopedTunSink>,
    tx:Vec<Arc<ScopedRawIpv4Tx>>,rx:Vec<Arc<ScopedRawIpv4Rx>>,
    copied:Arc<AtomicU64>,delivered:Arc<AtomicU64>,rejected:Arc<AtomicU64>,
    raw_received:Arc<AtomicU64>,authenticated_rejected:Arc<AtomicU64>,
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
            rx.push(Arc::new(ScopedRawIpv4Rx::open(ifname,ifindex,generation)
                .map_err(|_|())?));
        }
        let stop=Arc::new(AtomicBool::new(false));
        let copied=Arc::new(AtomicU64::new(0));
        let delivered=Arc::new(AtomicU64::new(0));
        let rejected=Arc::new(AtomicU64::new(0));
        let raw_received=Arc::new(AtomicU64::new(0));
        let authenticated_rejected=Arc::new(AtomicU64::new(0));
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
        let tx_worker=thread::Builder::new().name("wbd-v4-game-tx".into())
            .spawn(move||{
                let Ok(mut arena)=Arena::new(generation^0x4000_0000,64,2048,64,1_000_000)
                    else{return};
                let start=Instant::now();
                let mut inbound=[0u8;2048];
                while !tx_stop.load(Ordering::Acquire){
                    let Ok(len)=tx_tun.read_ipv4_into(generation,&mut inbound)else{
                        continue // bounded kernel poll, not a busy spin
                    };
                    if len==0||len>1200{
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
            let auth_denied=Arc::clone(&authenticated_rejected);
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
                    let Ok((len,_))=raw.recv_one_into(
                        generation,&mut wire,tuple,PacketPersona::Legacy
                    )else{continue};
                    if rx_stop.load(Ordering::Acquire){break}
                    raw_seen.fetch_add(1,Ordering::Relaxed);
                    let received={
                        let Ok(mut game)=client_rx_adapter.lock()else{break};
                        game.receive(lane,wire[..len].to_vec())
                    };
                    match received{
                        Ok(Some(plaintext))=>{
                            if rx_tun.write_authenticated_ipv4(generation,&plaintext).is_ok(){
                                recv_count.fetch_add(1,Ordering::Relaxed);
                            }else{recv_rejected.fetch_add(1,Ordering::Relaxed);}
                        },
                        Ok(None)=>{}, // exact GameRx cross-lane dedup
                        Err(_)=>{
                            auth_denied.fetch_add(1,Ordering::Relaxed);
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
            raw_received,authenticated_rejected})
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
         self.authenticated_rejected.load(Ordering::Relaxed))
    }
    pub(crate) fn stop_and_drain(&mut self)->Result<(),()>{
        self.stop.store(true,Ordering::Release);
        // Give in-flight M4 kernel borrows a bounded opportunity to finish
        // before owner release, without tearing down Go-owned TUN early.
        for w in self.threads.drain(..){if w.join().is_err(){return Err(())}}
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
