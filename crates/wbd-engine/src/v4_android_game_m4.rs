//! B46 original Game2/4-off or fixed Game FEC on Android's Bionic RAW/TUN.
//! One authenticated GameAdapter owns 2/4 AEAD/PN lanes, one native TUN
//! reader, 2/4 independent original M3 RX openers, and an owned joined Stop.
//! No Java/Go DATA callbacks, private protocol or separate source scheduler.
#![allow(unsafe_code)]
use std::io;
use std::os::fd::OwnedFd;
use std::sync::{Arc,Mutex,atomic::{AtomicBool,AtomicU32,AtomicU64,Ordering}};
use std::thread::{self,JoinHandle};
use std::time::{Duration,Instant};
use wbd_types::{LaneKey,TunnelKey,MonoNs};
use wbd_platform::android_root_io::{AndroidOwnedTun,AndroidWorkerWake,AndroidBoundPhysicalDnsUdp};
use wbd_platform::ipv4_tcp::{self,Ipv4Tuple,PacketPersona,Presentation};
use wbd_platform::r1::StopResult;
use crate::v4_game_lane::{GameAdapter,GameLaneOpener,GameReceiveOwner};
use crate::v4_native_health::{HealthClock,HealthPolicy,ControlDue};
use crate::v4_presentation_ack::{NativePresentationAck,presentation_ack_only_due};
use crate::v4_session_address::{admitted_client_source,admitted_client_destination};
use super::{AndroidPhysicalScope,AndroidGameRawLane};
use crate::v4_android_game_cold::OriginalGameColdLane;
use crate::v4_android_dns_udp_flow::{TunnelDnsUdpFlows,MAX_DNS_IPV4_PACKET};
use crate::v4_android_dns_ingress::{observe_ipv4_dns53,Dns53Observation};
use crate::v4_android_dns_physical_flow::{
    PhysicalDnsUdpFlows,MAX_DNS_WIRE,MAX_DNS_REPLY_IPV4
};
use crate::v4_android_cn_dns::CNDnsMatcher;
use crate::v4_android_dns_route::{choose,DnsRoute};
use crate::v4_android_game_schedule::{GameTunBurst,wait_ms,RAW_RX_IDLE_MAX_MS};
use crate::v4_android_ipv4_mtu::{emit_game_ipv4_fragments,fragmentation_needed};

pub(super) struct AndroidGameWorkers{
    stop:Arc<AtomicBool>,started:Arc<AtomicBool>,
    wakes:Vec<Arc<AndroidWorkerWake>>,
    threads:Vec<JoinHandle<()>>,tun:Arc<AndroidOwnedTun>,
    raw_tx:Arc<AtomicU64>,raw_rx:Arc<AtomicU64>,
    delivered:Arc<AtomicU64>,rejected:Arc<AtomicU64>,
    dns_queries:Arc<AtomicU64>,dns_replies:Arc<AtomicU64>,
    dns_flows:Option<Arc<Mutex<TunnelDnsUdpFlows>>>,
    physical_dns:Option<Arc<AndroidBoundPhysicalDnsUdp>>,
    physical_tx:Arc<AtomicU64>,physical_rx:Arc<AtomicU64>,
    physical_errors:Arc<AtomicU64>,
}
impl AndroidGameWorkers{
    pub(super) fn start(
        adapter:Arc<Mutex<GameAdapter>>,scope:&AndroidPhysicalScope,
        lanes:&[OriginalGameColdLane],raw:&[AndroidGameRawLane],
        lease:[u8;4],fd:OwnedFd,tun_name:&str,generation:u32,
        tunnel_dns:bool,health_seconds:u32,
        physical_dns:bool,upstream:[u8;4],cn:Option<CNDnsMatcher>,tunnel_upstream:[u8;4],
        game_fec_profile:Option<u8>,stagger:u32,
    )->Result<Self,()>{
        // Original Game2/4 off and fixed Game FEC share ONE M4 worker.
        // No new packet protocol, TLS lane, or rotation owner.
        let lane_count=lanes.len();
        if generation==0||!matches!(lane_count,2|4)||raw.len()!=lane_count||
            scope.mtu<576||tun_name.is_empty()||
            !matches!(health_seconds,15|30)||
            (tunnel_dns&&physical_dns)||
            (cn.is_some()&&!physical_dns)||
            game_fec_profile.is_some_and(|p|p>6){return Err(())}
        let tun=Arc::new(AndroidOwnedTun::adopt(fd,tun_name,generation)
            .map_err(|_|())?);
        let (rx_owner,inner_mtu,origin,evidence)={
            let mut game=adapter.lock().map_err(|_|())?;
            if game.has_game_fec(){return Err(())}
            if let Some(profile)=game_fec_profile{
                // Same GameAdapter FEC TX/RX owners used by Linux.
                // Original TLS fixed profile was verified by the Go
                // admission across all 2/4 authenticated group lanes.
                game.enable_game_fec(profile,false).map_err(|_|())?;
            }
            // Original Linux Game4/off wide stagger: 0/4/50/140ms,
            // configured BEFORE the original Rust M4 takes its M3 owners.
            // B45 also drains due copies while TUN is otherwise idle.
            if lane_count==4&&stagger!=0{
                game.configure_game4_stagger_mode(stagger).map_err(|_|())?;
            }
            let (origin,evidence)=game.health_context();
            (game.receiver_handle(),game.inner_mtu(),origin,evidence)
        };
        if !(20..=2000).contains(&inner_mtu){return Err(())}
        // B44: exactly the Normal M4 physically bound UDP53 socket, with
        // the original selected Network and first authenticated Go lane.
        if lanes.iter().any(|l|l.flow.client_ip!=lanes[0].flow.client_ip){
            return Err(())
        }
        let physical_socket=if physical_dns{
            Some(Arc::new(AndroidBoundPhysicalDnsUdp::open(
                scope.network_handle,&scope.interface,scope.ifindex,scope.mtu,
                lanes[0].flow.client_ip,upstream,generation
            ).map_err(|_|())?))
        }else{None};
        // Move (never copy) exactly one M3 replay opener to each native
        // raw worker before either TUN or RAW traffic can begin.
        let mut openers=Vec::with_capacity(lane_count);
        {
            let mut rx=rx_owner.lock().map_err(|_|())?;
            for id in 1..=lane_count{
                openers.push(rx.take_lane_for_worker(LaneKey{
                    tunnel:TunnelKey{slot:14,generation},slot:id as u32,generation
                }).map_err(|_|())?);
            }
        }
        let stop=Arc::new(AtomicBool::new(false));
        let started=Arc::new(AtomicBool::new(false));
        let mut wakes=Vec::with_capacity(1+lane_count);
        for _ in 0..1+lane_count{
            wakes.push(Arc::new(AndroidWorkerWake::new().map_err(|_|())?))
        }
        let raw_tx=Arc::new(AtomicU64::new(0));
        let raw_rx=Arc::new(AtomicU64::new(0));
        let delivered=Arc::new(AtomicU64::new(0));
        let rejected=Arc::new(AtomicU64::new(0));
        // Reuse Normal's bounded DNS transaction map with the original
        // single Game2 TUN reader and two authenticated RAW receivers.
        let dns_flows=(tunnel_dns||cn.is_some())
            .then(||{let mut table=TunnelDnsUdpFlows::default();table.set_upstream(tunnel_upstream);Arc::new(Mutex::new(table))});
        let dns_queries=Arc::new(AtomicU64::new(0));
        let dns_replies=Arc::new(AtomicU64::new(0));
        let physical_tx=Arc::new(AtomicU64::new(0));
        let physical_rx=Arc::new(AtomicU64::new(0));
        let physical_errors=Arc::new(AtomicU64::new(0));
        let health_policy=HealthPolicy::new(u64::from(health_seconds)*1_000_000_000,
            HealthPolicy::DEFAULT_DEAD_NS,None).ok_or(())?;
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
        let tx_dns=dns_flows.as_ref().map(Arc::clone);
        let tx_dns_queries=Arc::clone(&dns_queries);
        let tx_physical=physical_socket.as_ref().map(Arc::clone);
        let tx_physical_tx=Arc::clone(&physical_tx);
        let tx_physical_rx=Arc::clone(&physical_rx);
        let tx_physical_errors=Arc::clone(&physical_errors);
        let tx_cn=cn;
        let tx_dns_capture=tunnel_dns||physical_dns;
        let tx_fec_enabled=game_fec_profile.is_some();
        let tx=thread::Builder::new().name("wbd-android-game-tx".into())
            .spawn(move||{
                let mut source=[0u8;65_535];
                let mut game_ipv4_fragment=[0u8;2_048];
                let mut game_ipv4_icmp=[0u8;128];
                let mut outer=[[0u8;2048];4];
                let mut health_wire=[0u8;2048];
                let mut health_outer=[0u8;2048];
                // Original M4 owns both the app TUN and selected-Network
                // physical DNS socket; no extra socket reader or worker.
                let mut physical_flows=PhysicalDnsUdpFlows::default();
                let mut physical_tcp=crate::v4_android_dns_tcp_fallback::PhysicalDnsTcpFallbacks::default();
                let mut physical_wire=[0u8;MAX_DNS_WIRE];
                let mut physical_packet=[0u8;MAX_DNS_REPLY_IPV4];
                // B59: original Game TX thread also returns large DNS
                // replies through this same single TUN, no extra worker.
                let mut physical_fragment=[0u8;2_048];
                let mut offsets=tx_begin;
                let mut tun_burst=GameTunBurst::default();
                // The original GameAdapter may schedule Game4 later copies.
                // Invoke this SAME native RAW sender both on TUN ingress and
                // when a due copy matures without further App traffic.
                macro_rules! drain_original_game {
                    ($game:expr,$when:expr) => {{
                        $game.drain($when,|lane,_id,pn,wire|{
                                        let i=(lane.slot as usize).saturating_sub(1);
                                        if i>=lane_count{return false}
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
                        })
                    }};
                }
                let mut health=HealthClock::new(
                    health_policy,
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
                    let received_business=matches!(&read,Ok(n) if *n>0);
                    if let Ok(n)=read{
                        if n>0&&admitted_client_source(&source[..n],Some(lease)){
                            // B44 shares Normal's exact DNS classification:
                            // all physical, CN physical/non-CN tunnel, or
                            // all tunnel. TCP/53 stays original Game M1/M3.
                            let observed=if tx_dns_capture{
                                observe_ipv4_dns53(&source[..n],n)
                            }else{Dns53Observation::NotDns};
                            let route=choose(&source[..n],observed,
                                tx_dns_capture,physical_dns,tx_cn.as_ref());
                            if matches!(route,DnsRoute::PhysicalUDP){
                                if let Some(socket)=tx_physical.as_ref(){
                                    match physical_flows.prepare(&source[..n],
                                        &mut physical_wire,now.0/1_000_000){
                                        Ok((len,id,new_slot))=>{
                                            if socket.send_question(
                                                generation,&physical_wire[..len]).is_ok(){
                                                tx_physical_tx.fetch_add(1,Ordering::Relaxed);
                                            }else{
                                                if new_slot{physical_flows.cancel(id);}
                                                tx_physical_errors.fetch_add(1,Ordering::Relaxed);
                                            }
                                        },
                                        Err(_)=>{
                                            tx_physical_errors.fetch_add(1,Ordering::Relaxed);
                                        }
                                    }
                                }else{tx_physical_errors.fetch_add(1,Ordering::Relaxed);}
                            }else{
                            // Same 64-slot original Normal TunnelDnsUdpFlows,
                            // before the genuine GameAdapter seal.
                            let mut dns_rejected=false;
                            if matches!(route,DnsRoute::TunnelUDP){
                                if let Some(ref flows)=tx_dns{
                                    match flows.lock(){
                                        Ok(mut table)=>{
                                            if table.rewrite_query(&mut source[..n],
                                                now.0/1_000_000).is_ok(){
                                                tx_dns_queries.fetch_add(1,Ordering::Relaxed);
                                            }else{dns_rejected=true;}
                                        },
                                        Err(_)=>break,
                                    }
                                }else{dns_rejected=true;}
                            }
                            if dns_rejected{
                                tx_rejected.fetch_add(1,Ordering::Relaxed);
                            }else if n>inner_mtu&&source[6]&0x40!=0{
                                // B57: tell the actual App IPv4 stack its
                                // original Game M3 budget, not a fake DATA ACK.
                                let wrote=fragmentation_needed(
                                    &source[..n],inner_mtu,&mut game_ipv4_icmp
                                ).is_some_and(|len|
                                    tx_tun.write_local_pmtu_icmp_ipv4(
                                        generation,&game_ipv4_icmp[..len]
                                    ).ok()==Some(len));
                                if !wrote{
                                    tx_rejected.fetch_add(1,Ordering::Relaxed);
                                }
                            }else if let Ok(mut game)=tx_adapter.lock(){
                                let accepted=if n<=inner_mtu{
                                    if game.offer(&source[..n],now).is_ok(){
                                        let copied=drain_original_game!(game,now);
                                        if copied>0{health.on_local_business(now.0)}
                                        true
                                    }else{false}
                                }else{
                                    // DF=0 reuses the original RFC791 codec,
                                    // but EVERY fragment goes through THIS
                                    // GameAdapter, unchanged AEAD/PN/RAW.
                                    emit_game_ipv4_fragments(
                                        &source[..n],inner_mtu,
                                        &mut game_ipv4_fragment,|piece|{
                                            if tx_stop.load(Ordering::Acquire){
                                                return false
                                            }
                                            if game.offer(piece,now).is_err(){
                                                return false
                                            }
                                            let copied=drain_original_game!(game,now);
                                            if copied>0{
                                                health.on_local_business(now.0)
                                            }
                                            true
                                        }
                                    ).is_ok()
                                };
                                if !accepted{
                                    tx_rejected.fetch_add(1,Ordering::Relaxed);
                                }
                            }else{break}
                            } // Physical UDP only uses scoped socket, never GameAdapter/M3.
                        }else{tx_rejected.fetch_add(1,Ordering::Relaxed);}
                    }else if read.as_ref().err().is_some_and(|e|
                        e.kind()!=io::ErrorKind::WouldBlock){
                        tx_rejected.fetch_add(1,Ordering::Relaxed);
                        tx_stop.store(true,Ordering::Release);
                        break
                    }
                    // B46: Linux's original fixed Game FEC needs bounded
                    // parity work even when no more App TUN packets arrive.
                    // One existing TX worker owns both FEC and Game4 due
                    // copies, with the same RAW kernel send callback.
                    let mut game_due=None;
                    if lane_count==4||tx_fec_enabled{
                        let when=MonoNs(origin.elapsed().as_nanos()
                            .min(u128::from(u64::MAX)) as u64);
                        if let Ok(mut game)=tx_adapter.lock(){
                            if tx_fec_enabled{
                                for _ in 0..4{
                                    let fec_now=MonoNs(origin.elapsed().as_nanos()
                                        .min(u128::from(u64::MAX)) as u64);
                                    match game.poll_game_fec(fec_now){
                                        Ok(0)=>break,
                                        Ok(_)=>{
                                            let copied=drain_original_game!(game,fec_now);
                                            if copied>0{
                                                health.on_local_business(fec_now.0);
                                            }
                                        },
                                        Err(_)=>{
                                            tx_rejected.fetch_add(1,Ordering::Relaxed);
                                            break
                                        }
                                    }
                                }
                            }
                            let copied=drain_original_game!(game,when);
                            if copied>0{health.on_local_business(when.0)}
                            game_due=game.game4_next_due_ns().into_iter()
                                .chain(game.game_fec_next_due_ns(when)).min();
                        }else{tx_stop.store(true,Ordering::Release);break}
                    }
                    // B55: queued business uses the SAME TUN and real
                    // GameAdapter, with a DNS/Stop event turn every 8 reads.
                    if tun_burst.inline_next(received_business){continue}
                    let poll_now=origin.elapsed().as_nanos()
                        .min(u128::from(u64::MAX)) as u64;
                    let wait_ms=wait_ms(poll_now,health.next_deadline(),game_due);
                    let (mut tcp_interest,tcp_count)=physical_tcp.interests();
                    let wait_ms=physical_tcp.limit_timeout(wait_ms,origin.elapsed().as_millis() as u64);
                    // Same eventfd and physical DNS, plus live TCP fallback FDs only.
                    let ready=if let Some(socket)=tx_physical.as_ref(){
                        if tcp_count==0{
                            tx_wake.wait_tun_and_physical_dns(
                                tx_tun.readiness_fd(),socket.readiness_fd(),wait_ms)
                        }else{
                            tx_wake.wait_tun_and_physical_dns_tcp(tx_tun.readiness_fd(),
                                socket.readiness_fd(),&mut tcp_interest[..tcp_count],wait_ms)
                        }
                    }else{
                        tx_wake.wait_readable(tx_tun.readiness_fd(),wait_ms)
                            .map(|v|(v,false))
                    };
                    let (_,dns_ready)=match ready{
                        Ok(v)=>v,
                        Err(_)=>{
                            tx_rejected.fetch_add(1,Ordering::Relaxed);
                            tx_stop.store(true,Ordering::Release);
                            break
                        }
                    };
                    if tx_stop.load(Ordering::Acquire){break}
                    let mut completed=physical_tcp.ready(&tcp_interest[..tcp_count],
                        origin.elapsed().as_millis() as u64);
                    if dns_ready||!completed.is_empty(){
                        if let Some(socket)=tx_physical.as_ref(){
                            let mut udp_budget=8;
                            for _ in 0..(8+completed.len()){
                                if tx_stop.load(Ordering::Acquire){break}
                                let at_ms=origin.elapsed().as_millis() as u64;
                                let n=if let Some(done)=completed.pop(){
                                    let Some(wire)=physical_flows.tcp_completion_wire(done.ticket,
                                        done.full.as_deref(),&done.truncated,at_ms)else{continue};
                                    physical_wire[..wire.len()].copy_from_slice(wire);wire.len()
                                }else{
                                    if !dns_ready||udp_budget==0{break}
                                    udp_budget-=1;
                                    let n=match socket.read_answer(generation,&mut physical_wire){
                                        Ok(n)=>n,
                                        Err(err) if err.kind()==io::ErrorKind::WouldBlock=>break,
                                        Err(_)=>{
                                            tx_physical_errors.fetch_add(1,Ordering::Relaxed);
                                            tx_stop.store(true,Ordering::Release);
                                            break
                                        }
                                    };
                                    if physical_tcp.try_start(socket,&physical_flows,&physical_wire[..n],at_ms){continue}
                                    n
                                };
                                let result=physical_flows.receive(
                                    &physical_wire[..n],&mut physical_packet,
                                    origin.elapsed().as_millis() as u64);
                                match result{
                                    Ok(len) if physical_packet[16..20]==lease=>{
                                        let delivered=crate::v4_android_dns_physical_flow::
                                            emit_physical_dns_tun_reply(
                                                &mut physical_packet[..len],
                                                inner_mtu,&mut physical_fragment,
                                                |piece,fragmented|{
                                                    let wrote=if fragmented{
                                                        tx_tun.write_scoped_physical_dns_ipv4_fragment(
                                                            generation,piece)
                                                    }else{
                                                        tx_tun.write_scoped_physical_dns_ip(
                                                            generation,piece)
                                                    };
                                                    wrote.ok()==Some(piece.len())
                                                }
                                            ).is_ok();
                                        if delivered{
                                            tx_physical_rx.fetch_add(1,Ordering::Relaxed);
                                        }else{
                                            tx_physical_errors.fetch_add(1,Ordering::Relaxed);
                                        }
                                    },
                                    _=>{
                                        tx_physical_errors.fetch_add(1,Ordering::Relaxed);
                                    }
                                }
                            }
                        }
                    }
                }
                physical_tcp.stop();
                physical_flows.stop();
                if let Some(socket)=tx_physical.as_ref(){socket.begin_stop();}
            }).map_err(|_|())?;
        let mut threads=vec![tx];
        let mut openers=openers.into_iter();
        for i in 0..lane_count{
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
            let rx_dns=dns_flows.as_ref().map(Arc::clone);
            let rx_dns_replies=Arc::clone(&dns_replies);
            let rx_fec_enabled=game_fec_profile.is_some();
            let ack_heads=Arc::clone(&ack);
            let seq_heads=Arc::clone(&seq);
            let f=lanes[i].flow;
            let rx_first=lanes[i].rx_seq;
            let lane=LaneKey{tunnel:TunnelKey{slot:14,generation},
                slot:i as u32+1,generation};
            let result=thread::Builder::new()
                .name(format!("wbd-android-game-rx-{}",i+1))
                .spawn(move||{
                    let mut wire=[0u8;2048];
                    let mut ack_wire=[0u8;64];
                     let mut dns_reply=[0u8;MAX_DNS_IPV4_PACKET];
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
                    let mut raw_burst=GameTunBurst::default();
                    while !rx_stop.load(Ordering::Acquire)&&
                        !rx_started.load(Ordering::Acquire){
                        thread::yield_now();
                    }
                    while !rx_stop.load(Ordering::Acquire){
                        let read=rx_raw.read_original_record(generation,&mut wire,
                            tuple,PacketPersona::Legacy);
                        let raw_received=matches!(&read,Ok((n,_)) if *n>0);
                        match read{
                            Ok((len,seq32))=>{
                                rx_read.fetch_add(1,Ordering::Relaxed);
                                let decrypted=opener.open(&mut wire[..len]);
                                match decrypted{
                                    Ok(Some((id,payload)))=>{
                                        if rx_fec_enabled{
                                            // Original Linux Game FEC RX: per-lane
                                            // AEAD/PN has already opened above.
                                            // One shared decoder may yield up to
                                            // 16 authenticated recovered IP frames.
                                            let fec_now=MonoNs(origin.elapsed().as_nanos()
                                                .min(u128::from(u64::MAX)) as u64);
                                            let prepared=match rx_owner.lock(){
                                                Ok(mut owner)=>owner.prepare_opened_fec_batch(
                                                    lane,id,payload,fec_now),
                                                Err(_)=>break,
                                            };
                                            match prepared{
                                                Ok(Some(mut batch))=>{
                                                    // Preflight ALL recovered frames
                                                    // before any irreversible TUN write.
                                                    // Rewrite DNS directly in FEC-owned
                                                    // slabs: no second packet copies.
                                                    let mut valid=true;
                                                    let mut dns_count=0u64;
                                                    for frame in batch.frames_mut(){
                                                        if !admitted_client_destination(
                                                            frame,Some(lease)){
                                                            valid=false;break
                                                        }
                                                        if let Some(flows)=rx_dns.as_ref(){
                                                            if TunnelDnsUdpFlows::
                                                                is_tunnel_reply_candidate_for(frame,tunnel_upstream){
                                                                if frame.len()>MAX_DNS_IPV4_PACKET{
                                                                    valid=false;break
                                                                }
                                                                match flows.lock(){
                                                                    Ok(mut table)=>{
                                                                        if table.rewrite_reply(
                                                                            frame,
                                                                            origin.elapsed().as_millis() as u64
                                                                        ).is_ok(){
                                                                            dns_count+=1;
                                                                        }else{valid=false;break}
                                                                    },
                                                                    Err(_)=>{
                                                                        rx_stop.store(true,Ordering::Release);
                                                                        valid=false;break
                                                                    },
                                                                }
                                                            }
                                                        }
                                                    }
                                                    let mut all_written=valid;
                                                    let mut wrote=0u64;
                                                    if valid{
                                                        for frame in batch.frames(){
                                                            if rx_tun.write_authenticated_ip(frame)
                                                                .ok()==Some(frame.len()){
                                                                wrote+=1;
                                                            }else{
                                                                all_written=false;
                                                                break
                                                            }
                                                        }
                                                    }
                                                    let settled=match rx_owner.lock(){
                                                        Ok(mut owner)=>owner.finish_fec_batch(
                                                            batch,all_written),
                                                        Err(_)=>break,
                                                    };
                                                    if settled.is_err()||
                                                       (wrote>0&&!all_written){
                                                        // A partial multi-frame TUN batch
                                                        // cannot be rolled back.
                                                        rx_stop.store(true,Ordering::Release);
                                                        break
                                                    }
                                                    if all_written{
                                                        rx_delivered.fetch_add(wrote,Ordering::Relaxed);
                                                        if dns_count>0{
                                                            rx_dns_replies.fetch_add(
                                                                dns_count,Ordering::Relaxed);
                                                        }
                                                        // Even parity-only batches consume
                                                        // the real authenticated TCP record.
                                                        let current=ledger.verified(seq32,len);
                                                        ack_heads[i].store(current,Ordering::Release);
                                                        let now_ns=clock.elapsed().as_nanos()
                                                            .min(u128::from(u64::MAX)) as u64;
                                                        if presentation_ack_only_due(
                                                            now_ns,last_ack_ns,current,last_ack){
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
                                        }else{

                                        let prepared=match rx_owner.lock(){
                                            Ok(mut owner)=>owner.prepare_opened_receive(
                                                lane,id,payload),
                                            Err(_)=>break,
                                        };
                                        match prepared{
                                            Ok(Some(mut packet))=>{
                                                let mut accepted=admitted_client_destination(
                                                    packet.payload(),Some(lease));
                                                // Original M3 AEAD/replay must pass before
                                                // any Game2 DNS reply translation.
                                                let mut dns_len=0usize;
                                                if accepted{
                                                    if let Some(ref flows)=rx_dns{
                                                        if TunnelDnsUdpFlows::is_tunnel_reply_candidate_for(
                                                            packet.payload(),tunnel_upstream){
                                                            let frame=packet.payload();
                                                            if frame.len()>dns_reply.len(){accepted=false}
                                                            else{
                                                                dns_reply[..frame.len()].copy_from_slice(frame);
                                                                match flows.lock(){
                                                                    Ok(mut table)=>{
                                                                        if table.rewrite_reply(
                                                                            &mut dns_reply[..frame.len()],
                                                                            origin.elapsed().as_millis() as u64
                                                                        ).is_ok(){dns_len=frame.len();}
                                                                        else{accepted=false;}
                                                                    },
                                                                    Err(_)=>{rx_stop.store(true,Ordering::Release);accepted=false;},
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                                let ip=if dns_len>0{&dns_reply[..dns_len]}
                                                    else{packet.payload()};
                                                let written=accepted &&
                                                    rx_tun.write_authenticated_ip(ip).ok()==Some(ip.len());
                                                if written&&dns_len>0{
                                                    rx_dns_replies.fetch_add(1,Ordering::Relaxed);
                                                }
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
                        // B56: already-queued original M3 records use
                        // one bounded recv burst, avoiding a poll per record.
                        // One existing Stop eventfd turn every eight reads.
                        if raw_burst.inline_next(raw_received){continue}
                        if rx_wake.wait_readable(
                            rx_raw.readiness_fd(),RAW_RX_IDLE_MAX_MS
                        ).is_err(){
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
            raw_tx,raw_rx,delivered,rejected,dns_queries,dns_replies,dns_flows,
            physical_dns:physical_socket,physical_tx,physical_rx,physical_errors})
    }
    pub(super) fn counters(&self)->[u64;9]{
        [self.raw_tx.load(Ordering::Relaxed),
         self.raw_rx.load(Ordering::Relaxed),
         self.delivered.load(Ordering::Relaxed),
         self.rejected.load(Ordering::Relaxed),
         self.dns_queries.load(Ordering::Relaxed),
         self.dns_replies.load(Ordering::Relaxed),
         self.physical_tx.load(Ordering::Relaxed),
         self.physical_rx.load(Ordering::Relaxed),
         self.physical_errors.load(Ordering::Relaxed)]
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
        // All original Game2 workers have joined; discard only this
        // generation's DNS mapping, without system resolver changes.
        if let Some(flows)=self.dns_flows.take(){
            flows.lock().map_err(|_|())?.stop();
        }
        // The same worker's physical DNS socket is retired only after
        // its real kernel borrows joined, before the borrowed TUN owner.
        if let Some(socket)=self.physical_dns.take(){
            if socket.stop_until(Instant::now()+Duration::from_secs(3))
                !=StopResult::Drained{return Err(())}
        }
        self.tun.begin_stop();
        let result=self.tun.stop_until(Instant::now()+Duration::from_secs(3));
        if panic||result!=StopResult::Drained{return Err(())}
        Ok(())
    }
}
