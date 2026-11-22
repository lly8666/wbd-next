//! B40 original Game2/off M4 on Android's *existing* Bionic RAW/TUN.
//! One authenticated GameAdapter owns both AEAD/PN lanes, one native TUN
//! reader, two per-lane original M3 RX openers, and an owned joined Stop.
//! No Java/Go DATA callbacks, private protocol or separate source scheduler.
#![allow(unsafe_code)]
use std::io;
use std::os::fd::OwnedFd;
use std::sync::{Arc,Mutex,atomic::{AtomicBool,AtomicU32,AtomicU64,Ordering}};
use std::thread::{self,JoinHandle};
use std::time::{Duration,Instant};
use wbd_types::{LaneKey,TunnelKey,MonoNs};
use wbd_platform::android_root_io::{AndroidOwnedTun,AndroidWorkerWake};
use wbd_platform::ipv4_tcp::{self,Ipv4Tuple,PacketPersona,Presentation};
use wbd_platform::r1::StopResult;
use crate::v4_game_lane::{GameAdapter,GameLaneOpener,GameReceiveOwner};
use crate::v4_native_health::{HealthClock,HealthPolicy,ControlDue};
use crate::v4_presentation_ack::{NativePresentationAck,presentation_ack_only_due};
use crate::v4_session_address::{admitted_client_source,admitted_client_destination};
use super::{AndroidPhysicalScope,AndroidGameRawLane};
use crate::v4_android_game_cold::OriginalGameColdLane;

pub(super) struct AndroidGameWorkers{
    stop:Arc<AtomicBool>,started:Arc<AtomicBool>,
    wakes:Vec<Arc<AndroidWorkerWake>>,
    threads:Vec<JoinHandle<()>>,tun:Arc<AndroidOwnedTun>,
    raw_tx:Arc<AtomicU64>,raw_rx:Arc<AtomicU64>,
    delivered:Arc<AtomicU64>,rejected:Arc<AtomicU64>,
}
impl AndroidGameWorkers{
    pub(super) fn start(
        adapter:Arc<Mutex<GameAdapter>>,scope:&AndroidPhysicalScope,
        lanes:&[OriginalGameColdLane],raw:&[AndroidGameRawLane],
        lease:[u8;4],fd:OwnedFd,tun_name:&str,generation:u32,
    )->Result<Self,()>{
        // First product data worker is Game2/OFF only. Game4 stagger, FEC,
        // Make-Before-Break and App/Go cold launch remain separately gated.
        if generation==0||lanes.len()!=2||raw.len()!=2||
            scope.mtu<576||tun_name.is_empty(){return Err(())}
        let tun=Arc::new(AndroidOwnedTun::adopt(fd,tun_name,generation)
            .map_err(|_|())?);
        let (rx_owner,inner_mtu,origin,evidence)={
            let game=adapter.lock().map_err(|_|())?;
            if game.has_game_fec(){return Err(())}
            let (origin,evidence)=game.health_context();
            (game.receiver_handle(),game.inner_mtu(),origin,evidence)
        };
        if !(20..=2000).contains(&inner_mtu){return Err(())}
        // Move (never copy) exactly one M3 replay opener to each native
        // raw worker before either TUN or RAW traffic can begin.
        let mut openers=Vec::with_capacity(2);
        {
            let mut rx=rx_owner.lock().map_err(|_|())?;
            for id in 1..=2{
                openers.push(rx.take_lane_for_worker(LaneKey{
                    tunnel:TunnelKey{slot:14,generation},slot:id,generation
                }).map_err(|_|())?);
            }
        }
        let stop=Arc::new(AtomicBool::new(false));
        let started=Arc::new(AtomicBool::new(false));
        let mut wakes=Vec::with_capacity(3);
        for _ in 0..3{wakes.push(Arc::new(AndroidWorkerWake::new().map_err(|_|())?))}
        let raw_tx=Arc::new(AtomicU64::new(0));
        let raw_rx=Arc::new(AtomicU64::new(0));
        let delivered=Arc::new(AtomicU64::new(0));
        let rejected=Arc::new(AtomicU64::new(0));
        let ack=Arc::new(lanes.iter().map(|l|AtomicU32::new(l.rx_seq))
            .collect::<Vec<_>>());
        let seq=Arc::new(lanes.iter().map(|l|AtomicU32::new(l.tx_seq as u32))
            .collect::<Vec<_>>());
        let tx_raw=raw.iter().map(|l|Arc::clone(&l.tx)).collect::<Vec<_>>();
        let tx_flows=lanes.iter().map(|l|l.flow).collect::<Vec<_>>();
        let tx_begin=lanes.iter().map(|l|l.tx_seq).collect::<Vec<_>>();
        let mtu=scope.mtu.min(1500);
        let tx_wake=Arc::clone(&wakes[0]);
        let tx_tun=Arc::clone(&tun);
        let tx_stop=Arc::clone(&stop);
        let tx_started=Arc::clone(&started);
        let tx_adapter=Arc::clone(&adapter);
        let tx_ack=Arc::clone(&ack);
        let tx_seq=Arc::clone(&seq);
        let tx_sent=Arc::clone(&raw_tx);
        let tx_rejected=Arc::clone(&rejected);
        let tx=thread::Builder::new().name("wbd-android-game2-tx".into())
            .spawn(move||{
                let mut source=[0u8;65_535];
                let mut outer=[[0u8;2048];2];
                let mut health_wire=[0u8;2048];
                let mut health_outer=[0u8;2048];
                let mut offsets=tx_begin;
                let mut health=HealthClock::new(
                    HealthPolicy::default_connected(),
                    origin.elapsed().as_nanos().min(u128::from(u64::MAX)) as u64);
                // Cold ready kind0 is emitted only after *both* native RX
                // and the only TUN TX worker have started.
                while !tx_stop.load(Ordering::Acquire)&&
                      !tx_started.load(Ordering::Acquire){
                    thread::yield_now();
                }
                if tx_stop.load(Ordering::Acquire){return}
                let initial=origin.elapsed().as_nanos().min(u128::from(u64::MAX)) as u64;
                health.arm_client_cold_ready(initial);
                while !tx_stop.load(Ordering::Acquire){
                    let now=MonoNs(origin.elapsed().as_nanos().min(u128::from(u64::MAX)) as u64);
                    evidence.absorb(&mut health);
                    match health.control_due(now.0){
                        ControlDue::DeadPeer=>{
                            tx_stop.store(true,Ordering::Release);
                            break
                        },
                        ControlDue::Health=>{
                            let send=match tx_adapter.lock(){
                                Ok(mut game)=>match game.seal_native_health(
                                    1,health.local_idle_ns(now.0),&mut health_wire){
                                    Ok((pn,len))=>{
                                        let f=tx_flows[0];
                                        let tuple=Ipv4Tuple{src_ip:&f.client_ip,
                                            dst_ip:&f.server_ip,
                                            src_port:f.client_port,dst_port:f.server_port};
                                        let presentation=Presentation{
                                            ack32:tx_ack[0].load(Ordering::Acquire),
                                            advertised_window:65_535,ip_id:pn as u16,
                                            persona:PacketPersona::Legacy
                                        };
                                        ipv4_tcp::build_bytes(tuple,presentation,offsets[0],
                                            &health_wire[..len],None,mtu as usize,&mut health_outer)
                                            .ok().and_then(|packet|
                                                tx_raw[0].send_built_outer(
                                                    generation,packet,mtu).ok())
                                            .is_some_and(|n|n==len+40)
                                            .then_some(len)
                                    },
                                    Err(_)=>None,
                                },
                                Err(_)=>None
                            };
                            if let Some(len)=send{
                                offsets[0]=offsets[0].saturating_add(len as u64);
                                tx_seq[0].store(offsets[0] as u32,Ordering::Release);
                                tx_sent.fetch_add(1,Ordering::Relaxed);
                            }
                            health.on_health_send_result(now.0,send.is_some());
                        },
                        ControlDue::None=>{},
                    }
                    // The sole TUN consumer; a full-size scratch prevents
                    // silent truncation of oversized DF/IPv4 packets.
                    let read=tx_tun.read_ip(&mut source);
                    if let Ok(n)=read{
                        if n>0&&n<=inner_mtu &&
                            admitted_client_source(&source[..n],Some(lease)){
                            if let Ok(mut game)=tx_adapter.lock(){
                                if game.offer(&source[..n],now).is_ok(){
                                    let copied=game.drain(now,|lane,_id,pn,wire|{
                                        let i=(lane.slot as usize).saturating_sub(1);
                                        if i>=2{return false}
                                        let f=tx_flows[i];
                                        let tuple=Ipv4Tuple{
                                            src_ip:&f.client_ip,dst_ip:&f.server_ip,
                                            src_port:f.client_port,dst_port:f.server_port};
                                        let appearance=Presentation{
                                            ack32:tx_ack[i].load(Ordering::Acquire),
                                            advertised_window:65_535,ip_id:pn as u16,
                                            persona:PacketPersona::Legacy};
                                        let valid=ipv4_tcp::build_bytes(
                                            tuple,appearance,offsets[i],wire,None,
                                            mtu as usize,&mut outer[i])
                                            .ok().and_then(|packet|
                                                tx_raw[i].send_built_outer(
                                                    generation,packet,mtu).ok())
                                            .is_some_and(|size|size==wire.len()+40);
                                        if valid{
                                            offsets[i]=offsets[i].saturating_add(wire.len() as u64);
                                            tx_seq[i].store(offsets[i] as u32,Ordering::Release);
                                            tx_sent.fetch_add(1,Ordering::Relaxed);
                                        }
                                        valid
                                    });
                                    if copied>0{health.on_local_business(now.0)}
                                }else{tx_rejected.fetch_add(1,Ordering::Relaxed);}
                            }else{break}
                        }else{tx_rejected.fetch_add(1,Ordering::Relaxed);}
                    }else if read.as_ref().err().is_some_and(|e|
                        e.kind()!=io::ErrorKind::WouldBlock){
                        tx_rejected.fetch_add(1,Ordering::Relaxed);
                        tx_stop.store(true,Ordering::Release);
                        break
                    }
                    // No 1ms data poll, no Go goroutine, no per-DATA clock
                    // owner. The same eventfd wakes Stop and TUN readiness.
                    if tx_wake.wait_readable(tx_tun.readiness_fd(),250).is_err(){
                        tx_stop.store(true,Ordering::Release);
                        break
                    }
                }
            }).map_err(|_|())?;
        let mut threads=vec![tx];
        let mut openers=openers.into_iter();
        for i in 0..2{
            let mut opener:GameLaneOpener=openers.next().ok_or(())?;
            let rx_raw=Arc::clone(&raw[i].rx);
            let ack_raw=Arc::clone(&raw[i].tx);
            let rx_tun=Arc::clone(&tun);
            let rx_owner:Arc<Mutex<GameReceiveOwner>>=Arc::clone(&rx_owner);
            let rx_stop=Arc::clone(&stop);
            let rx_started=Arc::clone(&started);
            let rx_wake=Arc::clone(&wakes[1+i]);
            let rx_read=Arc::clone(&raw_rx);
            let rx_delivered=Arc::clone(&delivered);
            let rx_rejected=Arc::clone(&rejected);
            let ack_heads=Arc::clone(&ack);
            let seq_heads=Arc::clone(&seq);
            let f=lanes[i].flow;
            let rx_first=lanes[i].rx_seq;
            let lane=LaneKey{tunnel:TunnelKey{slot:14,generation},
                slot:i as u32+1,generation};
            let result=thread::Builder::new()
                .name(format!("wbd-android-game2-rx-{}",i+1))
                .spawn(move||{
                    let mut wire=[0u8;2048];
                    let mut ack_wire=[0u8;64];
                    let tuple=Ipv4Tuple{
                        src_ip:&f.server_ip,dst_ip:&f.client_ip,
                        src_port:f.server_port,dst_port:f.client_port};
                    let ack_tuple=Ipv4Tuple{
                        src_ip:&f.client_ip,dst_ip:&f.server_ip,
                        src_port:f.client_port,dst_port:f.server_port};
                    let mut ledger=NativePresentationAck::new(rx_first);
                    let clock=Instant::now();
                    let mut last_ack=rx_first;
                    let mut last_ack_ns=0u64;
                    while !rx_stop.load(Ordering::Acquire)&&
                        !rx_started.load(Ordering::Acquire){
                        thread::yield_now();
                    }
                    while !rx_stop.load(Ordering::Acquire){
                        match rx_raw.read_original_record(generation,&mut wire,tuple,
                            PacketPersona::Legacy){
                            Ok((len,seq32))=>{
                                rx_read.fetch_add(1,Ordering::Relaxed);
                                let decrypted=opener.open(&mut wire[..len]);
                                match decrypted{
                                    Ok(Some((id,payload)))=>{
                                        let prepared=match rx_owner.lock(){
                                            Ok(mut owner)=>owner.prepare_opened_receive(
                                                lane,id,payload),
                                            Err(_)=>break,
                                        };
                                        match prepared{
                                            Ok(Some(mut packet))=>{
                                                let accepted=admitted_client_destination(
                                                    packet.payload(),Some(lease));
                                                let written=accepted &&
                                                    rx_tun.write_authenticated_ip(
                                                        packet.payload()).ok()
                                                    ==Some(packet.payload().len());
                                                let settled=match rx_owner.lock(){
                                                    Ok(mut owner)=>owner.finish_receive(packet,written),
                                                    Err(_)=>break,
                                                };
                                                if settled.is_err(){
                                                    rx_stop.store(true,Ordering::Release);
                                                    break
                                                }
                                                if written{
                                                    rx_delivered.fetch_add(1,Ordering::Relaxed);
                                                    let current=ledger.verified(seq32,len);
                                                    ack_heads[i].store(current,Ordering::Release);
                                                    let now_ns=clock.elapsed().as_nanos()
                                                        .min(u128::from(u64::MAX)) as u64;
                                                    if presentation_ack_only_due(now_ns,last_ack_ns,
                                                        current,last_ack){
                                                        if let Ok(ack_packet)=
                                                            ipv4_tcp::build_presentation_ack(
                                                                ack_tuple,seq_heads[i].load(Ordering::Acquire),
                                                                current,(now_ns as u16).wrapping_add(11),
                                                                PacketPersona::Legacy,mtu as usize,&mut ack_wire){
                                                            if ack_raw.send_built_outer(
                                                                generation,ack_packet,mtu).is_ok(){
                                                                last_ack=current;last_ack_ns=now_ns;
                                                            }
                                                        }
                                                    }
                                                }else{
                                                    rx_rejected.fetch_add(1,Ordering::Relaxed);
                                                }
                                            },
                                            Ok(None)=>{},
                                            Err(_)=>{rx_rejected.fetch_add(1,Ordering::Relaxed);},
                                        }
                                    },
                                    Ok(None)=>{}, // original authenticated kind0 Health
                                    Err(_)=>{rx_rejected.fetch_add(1,Ordering::Relaxed);},
                                }
                            },
                            Err(error) if error.kind()==io::ErrorKind::WouldBlock ||
                                error.kind()==io::ErrorKind::InvalidData=>{},
                            Err(_)=>{
                                rx_rejected.fetch_add(1,Ordering::Relaxed);
                                rx_stop.store(true,Ordering::Release);
                                break
                            }
                        }
                        if rx_wake.wait_readable(rx_raw.readiness_fd(),250).is_err(){
                            rx_stop.store(true,Ordering::Release);
                            break
                        }
                    }
                });
            match result {
                Ok(worker)=>threads.push(worker),
                Err(_)=>{
                    stop.store(true,Ordering::Release);
                    for wake in &wakes{let _=wake.signal_stop();}
                    for thread in threads{let _=thread.join();}
                    return Err(())
                }
            }
        }
        started.store(true,Ordering::Release);
        Ok(Self{stop,started,wakes,threads,tun,
            raw_tx,raw_rx,delivered,rejected})
    }
    pub(super) fn counters(&self)->[u64;4]{
        [self.raw_tx.load(Ordering::Relaxed),
         self.raw_rx.load(Ordering::Relaxed),
         self.delivered.load(Ordering::Relaxed),
         self.rejected.load(Ordering::Relaxed)]
    }
    pub(super) fn is_live(&self)->bool{
        self.started.load(Ordering::Acquire)&&
        !self.stop.load(Ordering::Acquire)&&
        self.threads.iter().all(|h|!h.is_finished())
    }
    pub(super) fn stop_and_drain(&mut self)->Result<(),()>{
        self.stop.store(true,Ordering::Release);
        for wake in &self.wakes{let _=wake.signal_stop();}
        let mut panic=false;
        for thread in self.threads.drain(..){
            if thread.join().is_err(){panic=true}
        }
        self.tun.begin_stop();
        let result=self.tun.stop_until(Instant::now()+Duration::from_secs(3));
        if panic||result!=StopResult::Drained{return Err(())}
        Ok(())
    }
}
