//! PLAN026 Game2/4 genuine Npcap/Wintun native two-worker handoff.
//! Original independent Go TLS lanes and the SINGLE Linux GameAdapter
//! remain the sole cryptographic/FEC authorities. Go has no steady packet
//! callbacks. Every M4 outcome is an actual Npcap driver receipt.
use super::*;
use std::sync::atomic::{AtomicBool,AtomicI32,AtomicU32,AtomicU64,Ordering};
use std::sync::{Arc,Mutex,OnceLock};
use std::collections::{BTreeMap,VecDeque};
use std::thread::{self,JoinHandle};
use crate::v4_native_health::{HealthClock,HealthPolicy,ControlDue};
use wbd_platform::windows_native_io::{
    self as io,NpcapRx,NpcapTx,NpcapFns,WintunRx,WintunTx,
    WintunFns,WakeEvent,ReadResult,WaitResult,NativeIoError,
};
use wbd_platform::ipv4_tcp::{
    build_bytes,build_presentation_ack,Ipv4Tuple,Presentation,PacketPersona,
};
use wbd_platform::rx_ipv4_tcp::{parse_data_packet,TrustedRx};
use super::native_runtime::{WbdWinNativeAttachV1,WbdWinNativeStatsV1};
const FRAME_CAP:usize=2304;
const NPF_CAP:usize=65535+64;
const MAX_IPV4:usize=2048;
const EARLY_CAP:usize=256;
// An idle Game2/4 tunnel has no periodic TX timer. Only real Game4/FEC
// deadlines, Npcap-derived ACK wake, new Wintun sources or Stop wake TX.
fn game_wait_timeout_ms(now_ns:u64,next_due_ns:Option<u64>)->u32{
    next_due_ns.map(|due|{
        due.saturating_sub(now_ns).div_ceil(1_000_000)
            .max(1).min(u64::from(u32::MAX-1)) as u32
    }).unwrap_or(u32::MAX)
}
#[repr(C)]
#[derive(Clone,Copy)]
pub struct WbdWinGameExtraLaneV3 {
    pub owner:u64,
    pub initial_tx_seq:u32,
    pub initial_rx_seq:u32,
    pub local_port:u16,
    pub peer_port:u16,
    pub rx_capture:usize,
    pub tx_capture:usize,
    pub npcap:NpcapFns,
}
#[repr(C)]
#[derive(Clone,Copy)]
pub struct WbdWinGameNativeAttachV3{
    pub version:u32,pub size:u32,
    pub group:u64,pub lanes:u32,pub fec:u32,
    pub first:WbdWinNativeAttachV1,
    pub extra:[WbdWinGameExtraLaneV3;3],
}
#[derive(Clone,Copy)]
struct LaneConfig{
    owner:u64,tx_seq:u32,rx_seq:u32,
    local_port:u16,peer_port:u16,
    rx_capture:usize,tx_capture:usize,npcap:NpcapFns,
}
struct GameCounters{
    stop:AtomicBool,err:AtomicI32,tx:AtomicU64,
    rx:AtomicU64,after:AtomicU64,rejected:AtomicU64,
    ack:[AtomicU32;4],ack_sent:[AtomicU32;4],tx_seq:[AtomicU32;4],
}
impl GameCounters{
    fn new(lanes:&[LaneConfig])->Self{
        Self{stop:AtomicBool::new(false),err:AtomicI32::new(0),
            tx:AtomicU64::new(0),rx:AtomicU64::new(0),
            after:AtomicU64::new(0),rejected:AtomicU64::new(0),
            ack:std::array::from_fn(|i|AtomicU32::new(lanes.get(i).map_or(0,|x|x.rx_seq))),
            ack_sent:std::array::from_fn(|i|AtomicU32::new(lanes.get(i).map_or(0,|x|x.rx_seq))),
            tx_seq:std::array::from_fn(|i|AtomicU32::new(lanes.get(i).map_or(0,|x|x.tx_seq))),
        }
    }
    fn snapshot(&self)->WbdWinNativeStatsV1{
        WbdWinNativeStatsV1{
            version:1,size:std::mem::size_of::<WbdWinNativeStatsV1>() as u32,
            tx_copied:self.tx.load(Ordering::Relaxed),
            rx_delivered:self.rx.load(Ordering::Acquire),
            tx_after_rx:self.after.load(Ordering::Relaxed),
            rejected:self.rejected.load(Ordering::Relaxed),
            worker_error:self.err.load(Ordering::Acquire),workers:2,
        }
    }
}
// Pure TCP ACK ledger, NOT M2 applied/retransmit and NOT authentication.
// Only the genuine Rust game opener, after Wintun copy, may call verified.
struct AckLedger{next:u64,holes:Vec<(u64,u64)>}
impl AckLedger{
    fn new(start:u32)->Self{Self{next:u64::from(start),holes:Vec::with_capacity(256)}}
    fn verified(&mut self,seq:u32,len:usize)->u32{
        let base=self.next as u32;
        let diff=i64::from(i32::from_ne_bytes(seq.wrapping_sub(base).to_ne_bytes()));
        if diff < 0{return base}
        let begin=self.next.saturating_add(diff as u64);
        let end=begin.saturating_add(len as u64);
        if end<=self.next{return base}
        if begin<=self.next{self.next=end}
        else if self.holes.len()<256{
            let i=self.holes.partition_point(|(b,_)|*b<=begin);
            self.holes.insert(i,(begin,end));
        }
        while self.holes.first().is_some_and(|(b,_)|*b<=self.next){
            let (_,end)=self.holes.remove(0);
            self.next=self.next.max(end);
        }
        self.next as u32
    }
}
struct GameSession{
    stop:Arc<WakeEvent>,tx_wake:Arc<WakeEvent>,rx_wake:Arc<WakeEvent>,
    early:Arc<Mutex<VecDeque<(usize,u32,Vec<u8>)>>>,
    counters:Arc<GameCounters>,
    tx:JoinHandle<i32>,rx:JoinHandle<i32>,
}
static GAME_NATIVE:OnceLock<Mutex<BTreeMap<u64,GameSession>>>=OnceLock::new();
fn sessions()->&'static Mutex<BTreeMap<u64,GameSession>>{
    GAME_NATIVE.get_or_init(||Mutex::new(BTreeMap::new()))
}
fn configs(c:&WbdWinGameNativeAttachV3)->Result<Vec<LaneConfig>,i32>{
    if c.version!=3||c.size as usize!=std::mem::size_of::<WbdWinGameNativeAttachV3>()||
        !matches!(c.lanes,2|4)||c.group==0||c.fec>1||
        c.first.version!=1||
        c.first.size as usize!=std::mem::size_of::<WbdWinNativeAttachV1>()||
        c.first.wintun_session==0||c.first.wintun_read_event==0||
        c.first.luid==0||c.first.ifindex==0{return Err(INVALID)}
    let mut a=Vec::with_capacity(c.lanes as usize);
    a.push(LaneConfig{
        owner:c.first.owner,tx_seq:c.first.initial_tx_seq,
        rx_seq:c.first.initial_rx_seq,
        local_port:c.first.local_port,peer_port:c.first.peer_port,
        rx_capture:c.first.rx_capture,tx_capture:c.first.tx_capture,
        npcap:c.first.npcap,
    });
    for x in c.extra.iter().take(c.lanes as usize-1){
        a.push(LaneConfig{owner:x.owner,tx_seq:x.initial_tx_seq,
            rx_seq:x.initial_rx_seq,local_port:x.local_port,
            peer_port:x.peer_port,rx_capture:x.rx_capture,
            tx_capture:x.tx_capture,npcap:x.npcap})
    }
    if a.iter().any(|x|x.owner==0||x.rx_capture==0||x.tx_capture==0||
        x.local_port==0||x.peer_port==0){return Err(INVALID)}
    if a.iter().enumerate().any(|(i,x)|
        a.iter().skip(i+1).any(|y|x.owner==y.owner||x.local_port==y.local_port)
    ){return Err(INVALID)}
    Ok(a)
}
fn wire_frame<'a>(cfg:&WbdWinNativeAttachV1,l:&LaneConfig,
    seq:u32,ack:u32,wire:&[u8],id:u16,out:&'a mut [u8;FRAME_CAP],
)->Result<&'a [u8],i32>{
    let packet=build_bytes(Ipv4Tuple{
        src_ip:&cfg.local_ip,dst_ip:&cfg.peer_ip,
        src_port:l.local_port,dst_port:l.peer_port,
    },Presentation{ack32:ack,advertised_window:65535,
        ip_id:id,persona:PacketPersona::Windows11},
        u64::from(seq),wire,None,cfg.path_mtu as usize,&mut out[14..])
        .map_err(|_|INVALID)?;
    let n=14+packet.len();
    out[..6].copy_from_slice(&cfg.next_hop_mac);
    out[6..12].copy_from_slice(&cfg.source_mac);
    out[12..14].copy_from_slice(&0x0800u16.to_be_bytes());
    Ok(&out[..n])
}
// Presentation ACK has NO ciphertext, PN, M2 receipt, or data record.
// The normal wire_frame -> build_bytes path rejects zero-length records
// deliberately. Never relax that validation to send this TCP-only ACK.
fn presentation_ack_frame<'a>(
    tuple:Ipv4Tuple<'_>,source_mac:[u8;6],next_hop_mac:[u8;6],
    seq:u32,ack:u32,ip_id:u16,mtu:usize,out:&'a mut [u8;FRAME_CAP],
)->Result<&'a [u8],i32>{
    let tcp=build_presentation_ack(tuple,seq,ack,ip_id,
        PacketPersona::Windows11,mtu,&mut out[14..]).map_err(|_|INVALID)?;
    let n=14+tcp.len();
    out[..6].copy_from_slice(&next_hop_mac);
    out[6..12].copy_from_slice(&source_mac);
    out[12..14].copy_from_slice(&0x0800u16.to_be_bytes());
    Ok(&out[..n])
}
fn send_records(group:u64,cfg:&WbdWinNativeAttachV1,
    owner:&Arc<Mutex<game::WinGameGroup>>,
    lanes:&[LaneConfig],npf:&mut [NpcapTx],c:&GameCounters,
    records:Vec<game::WbdWindowsGameRecordV4>,ip_id:&mut u16,
    active:&mut [bool],
)->Result<usize,i32>{
    let total=records.len();
    for r in records{
        let idx=usize::try_from(r.lane).map_err(|_|INVALID)?
            .checked_sub(1).ok_or(INVALID)?;
        let l=lanes.get(idx).ok_or(INVALID)?;
        if r.length<32||r.length>1536{return Err(INVALID)}
        let seq=c.tx_seq[idx].load(Ordering::Acquire);
        let ack=c.ack[idx].load(Ordering::Acquire);
        let mut scratch=[0u8;FRAME_CAP];
        let frame=wire_frame(cfg,l,seq,ack,
            &r.wire[..r.length as usize],*ip_id,&mut scratch)?;
        *ip_id=ip_id.wrapping_add(1);
        let outcome=if active[idx]{
            Some(npf[idx].send_batch(&[frame]))
        }else{None};
        let copied=outcome.as_ref().is_some_and(|x|x.accepted_prefix==1);
        // Settle this exact original Linux GameAdapter staged ticket
        // AFTER the real Npcap success/unknown/not-sent result. No Go
        // fake receipt, no inferred application ACK.
        let rc={
            let mut g=owner.lock().map_err(|_|BAD_STAGE)?;
            game::game_m4_result_group(&mut g,group,r.lane,r.logical_id,r.pn,copied)
        };
        if rc!=OK{
            eprintln!("M0_PLAN026_GAME_NATIVE_FIRST_ERROR role=TX stage=game_m4_receipt rc={rc} lane={} copied={copied}",r.lane);
            return Err(rc)
        }
        if copied{
            c.tx_seq[idx].fetch_add(r.length,Ordering::Release);
            c.ack_sent[idx].store(ack,Ordering::Release);
            c.tx.fetch_add(1,Ordering::Relaxed);
            if c.rx.load(Ordering::Acquire)>0{c.after.fetch_add(1,Ordering::Relaxed);}
        }
        if let Some(outcome)=outcome{
            if outcome.error.is_some()||outcome.uncertain_index.is_some(){
                // Only this NPF TX endpoint is untrustworthy. The original
                // staged ticket was already settled using its REAL copied
                // prefix. Keep 2/4-lane siblings sending; all dead is fatal.
                eprintln!("M0_PLAN026_GAME_NATIVE_TX_LANE_RETIRED lane={} stage=npcap_send_driver accepted_prefix={} uncertain_index={:?} error={:?}",r.lane,outcome.accepted_prefix,outcome.uncertain_index,outcome.error);
                let _=retire_game_tx_lane(active,idx);
            }
        }
        if !active.iter().any(|&ok|ok){
            eprintln!("M0_PLAN026_GAME_NATIVE_FIRST_ERROR role=TX stage=all_npcap_send_lanes_retired");
            return Err(BAD_STAGE)
        }
    }
    Ok(total)
}
fn send_ack(cfg:&WbdWinNativeAttachV1,lanes:&[LaneConfig],
    npf:&mut [NpcapTx],c:&GameCounters,ip_id:&mut u16,
    active:&mut [bool],
)->Result<(),i32>{
    for (i,l) in lanes.iter().enumerate(){
        if !active[i]{continue}
        let ack=c.ack[i].load(Ordering::Acquire);
        if ack==c.ack_sent[i].load(Ordering::Acquire){continue}
        let mut scratch=[0u8;FRAME_CAP];
        let frame=presentation_ack_frame(Ipv4Tuple{
            src_ip:&cfg.local_ip,dst_ip:&cfg.peer_ip,
            src_port:l.local_port,dst_port:l.peer_port,
        },cfg.source_mac,cfg.next_hop_mac,
            c.tx_seq[i].load(Ordering::Acquire),ack,*ip_id,
            cfg.path_mtu as usize,&mut scratch)?;
        *ip_id=ip_id.wrapping_add(1);
        let status=npf[i].send_batch(&[frame]);
        if status.accepted_prefix==1{
            c.ack_sent[i].store(ack,Ordering::Release)
        }
        if status.error.is_some()||status.uncertain_index.is_some(){
            eprintln!("M0_PLAN026_GAME_NATIVE_TX_LANE_RETIRED lane={} stage=npcap_ack_send_driver accepted_prefix={} uncertain_index={:?} error={:?}",i+1,status.accepted_prefix,status.uncertain_index,status.error);
            let _=retire_game_tx_lane(active,i);
        }
        if !active.iter().any(|&ok|ok){
            eprintln!("M0_PLAN026_GAME_NATIVE_FIRST_ERROR role=TX stage=all_npcap_ack_lanes_retired");
            return Err(BAD_STAGE)
        }
    }
    Ok(())
}
fn tx_loop(cfg:WbdWinGameNativeAttachV3,lanes:Vec<LaneConfig>,
    group:Arc<Mutex<game::WinGameGroup>>,
    mut tun:WintunRx,mut npf:Vec<NpcapTx>,stop:Arc<WakeEvent>,
    wake:Arc<WakeEvent>,c:Arc<GameCounters>,
)->i32{
    let mut bytes=[0u8;MAX_IPV4];let mut id=1u16;
    // TX and RX capture endpoints have distinct native failure lifetimes.
    // Retiring one local TX handle must never stop another lane's NPF send.
    let mut active=vec![true;npf.len()];
    let (health_origin,health_evidence)={
        let g=match group.lock(){Ok(g)=>g,Err(_)=>return BAD_STAGE};
        game::native_game_health_context(&g)
    };
    let mut health=HealthClock::new(HealthPolicy::default_connected(),
        health_origin.elapsed().as_nanos().min(u128::from(u64::MAX)) as u64);
    loop{
        if c.stop.load(Ordering::Acquire){return OK}
        let mut did_work=false;
        for _ in 0..8{
            if c.stop.load(Ordering::Acquire){return OK}
            match tun.read(&mut bytes){
                Ok(ReadResult::Frame(n))=>{
                    let records=match group.lock(){
                        Ok(mut g)=>game::offer_records_native(&mut g,cfg.group,&bytes[..n]),
                        Err(_)=>{eprintln!("M0_PLAN026_GAME_NATIVE_FIRST_ERROR role=TX stage=offer_lock");return BAD_STAGE},
                    };
                    let rows=match records{Ok(v)=>v,Err(INVALID)=>{
                        c.rejected.fetch_add(1,Ordering::Relaxed);continue
                    },Err(e)=>{eprintln!("M0_PLAN026_GAME_NATIVE_FIRST_ERROR role=TX stage=offer_result rc={e}");return e}};
                    if let Err(rc)=send_records(cfg.group,&cfg.first,&group,&lanes,&mut npf,
                        &c,rows,&mut id,&mut active){eprintln!("M0_PLAN026_GAME_NATIVE_FIRST_ERROR role=TX stage=offer_send_records rc={rc}");return rc}
                    health.on_local_business(health_origin.elapsed().as_nanos()
                        .min(u128::from(u64::MAX)) as u64);
                    did_work=true;
                }
                Ok(ReadResult::NoPacket|ReadResult::EndOfStream)=>break,
                Ok(ReadResult::Skipped)=>{
                    c.rejected.fetch_add(1,Ordering::Relaxed);
                }
                Err(err)=>{
                    eprintln!("M0_PLAN026_GAME_NATIVE_FIRST_ERROR role=TX stage=wintun_read reason={err:?}");
                    return BAD_STAGE
                },
            }
        }
        // Same Game4 scheduler/FEC parity owner as original Linux.
        // One bounded due pass, no Go per-packet polling.
        let due=match group.lock(){
            Ok(mut g)=>game::native_game_due(&mut g,cfg.group,16),
            Err(_)=>{eprintln!("M0_PLAN026_GAME_NATIVE_FIRST_ERROR role=TX stage=due_lock");return BAD_STAGE},
        };
        match due{
            Ok(rows) if !rows.is_empty()=>{
                if let Err(rc)=send_records(cfg.group,&cfg.first,&group,&lanes,
                    &mut npf,&c,rows,&mut id,&mut active){eprintln!("M0_PLAN026_GAME_NATIVE_FIRST_ERROR role=TX stage=due_send_records rc={rc}");return rc}
                did_work=true;
            },
            Err(rc)=>{eprintln!("M0_PLAN026_GAME_NATIVE_FIRST_ERROR role=TX stage=game_native_due rc={rc}");return rc},
            _=>{},
        }
        if let Err(rc)=send_ack(&cfg.first,&lanes,&mut npf,&c,&mut id,&mut active){
            eprintln!("M0_PLAN026_GAME_NATIVE_FIRST_ERROR role=TX stage=send_ack rc={rc}");
            return rc
        }
        // Only unique AEAD-opened inbound Game records/Health refresh
        // the live peer deadline. Raw presentation ACK cannot.
        health_evidence.absorb(&mut health);
        let now_health=health_origin.elapsed().as_nanos()
            .min(u128::from(u64::MAX)) as u64;
        match health.control_due(now_health){
            ControlDue::DeadPeer=>{
                eprintln!("M0_GAME_NATIVE_HEALTH_DEAD age_ns={} threshold_ns={}",
                    now_health,health.policy().dead_ns());
                return BAD_STAGE
            },
            ControlDue::Health=>{
                let Some(index)=active.iter().position(|v|*v)else{return BAD_STAGE};
                let mut wire=[0u8;512];
                let sealed={
                    let mut g=match group.lock(){Ok(g)=>g,Err(_)=>return BAD_STAGE};
                    game::native_game_seal_health(&mut g,(index+1) as u32,
                        health.local_idle_ns(now_health),&mut wire)
                };
                let copied=match sealed{
                    Ok((_pn,n))=>{
                        let mut scratch=[0u8;FRAME_CAP];
                        let seq=c.tx_seq[index].load(Ordering::Acquire);
                        let ack=c.ack[index].load(Ordering::Acquire);
                        match wire_frame(&cfg.first,&lanes[index],seq,ack,
                            &wire[..n],id,&mut scratch){
                            Ok(frame)=>{
                                id=id.wrapping_add(1);
                                let result=npf[index].send_batch(&[frame]);
                                let copied=result.accepted_prefix==1;
                                if copied{
                                    c.tx_seq[index].fetch_add(n as u32,Ordering::Release);
                                    c.ack_sent[index].store(ack,Ordering::Release);
                                    c.tx.fetch_add(1,Ordering::Relaxed);
                                }
                                if result.error.is_some()||result.uncertain_index.is_some(){
                                    let _=retire_game_tx_lane(&mut active,index);
                                }
                                copied
                            },
                            Err(_)=>false,
                        }
                    },
                    Err(_)=>false,
                };
                health.on_health_send_result(now_health,copied);
                if !active.iter().any(|v|*v){return BAD_STAGE}
                // A genuine failed control copy waits >=1s; fresh DATA and
                // parity are independent, never blocked behind Health.
            },
            ControlDue::None=>{},
        }
        if did_work{continue}
        let timeout={
            let group=match group.lock(){Ok(g)=>g,Err(_)=>return BAD_STAGE};
            let (now,due)=game::native_game_wait_deadline(&group);
            let game_timeout=game_wait_timeout_ms(now,due);
            let health_wait=health.next_deadline().map(|at|{
                at.saturating_sub(health_origin.elapsed().as_nanos()
                    .min(u128::from(u64::MAX)) as u64)
                    .div_ceil(1_000_000).max(1).min(u64::from(u32::MAX-1)) as u32
            }).unwrap_or(u32::MAX);
            game_timeout.min(health_wait)
        };
        match io::wait_ready(&[stop.handle(),tun.event(),wake.handle()],timeout){
            Ok(WaitResult::Ready(0))=>return OK,
            Ok(WaitResult::Ready(1|2)|WaitResult::Timeout)=>{},
            Ok(other)=>{
                eprintln!("M0_PLAN026_GAME_NATIVE_FIRST_ERROR role=TX stage=event_wait unexpected={other:?} timeout_ms={timeout}");
                return BAD_STAGE
            },
            Err(err)=>{
                eprintln!("M0_PLAN026_GAME_NATIVE_FIRST_ERROR role=TX stage=event_wait reason={err:?} timeout_ms={timeout}");
                return BAD_STAGE
            },
        }
    }
}
// Authenticated original Linux Game server uses peer_persona=Windows11
// when its opposite Go TLS client is Windows. This persona also governs
// post-handoff Rust raw packets, not just earlier FakeTCP Go handshake.
// A strict frozen peer expectation: never learn persona from wire bytes.
fn trusted_windows_game_rx<'a>(
    peer_ip:&'a [u8;4],local_ip:&'a [u8;4],
    peer_port:u16,local_port:u16,mtu:usize,
)->TrustedRx<'a>{
    TrustedRx{
        tuple:Ipv4Tuple{
            src_ip:peer_ip,dst_ip:local_ip,
            src_port:peer_port,dst_port:local_port,
        },
        persona:PacketPersona::Windows11,
        mtu,authenticated_options:None,
    }
}
// A verified Game-FEC decoder candidate is NOT a Wintun delivery. Keep
// its exact bounded batch while the shared Wintun is temporarily full;
// the original AEAD/PN and FEC decode MUST NOT be replayed on retry.
struct DeferredFec{
    seq:u32,wire_len:usize,copied:u32,frames:Vec<Vec<u8>>,
}
fn receive_one(cfg:&WbdWinGameNativeAttachV3,
    group:&Arc<Mutex<game::WinGameGroup>>,tun:&mut WintunTx,
    c:&GameCounters,ledgers:&mut [AckLedger],
    deferred:&mut [Option<DeferredFec>],lane:usize,seq:u32,wire:&[u8],
)->Result<(),i32>{
    // Original Go TLS-derived GameAdapter M3+PN open and stage happens
    // under ONE group lock; the actual Wintun kernel writes MUST happen
    // outside the group lock or a blocked TUN send would stall every
    // sibling Game4 TX lane. AllCopied is settled only after real kernel
    // results, with exact per-lane prefix on partial failure.
    let (frames,pending)={
        let mut g=group.lock().map_err(|_|BAD_STAGE)?;
        if game::native_game_has_fec(&g){
            game::receive_fec_group(&mut g,cfg.group,(lane+1) as u32,wire)?
        }else{
            let (frame,pending)=game::prepare_off_group(
                &mut g,cfg.group,(lane+1) as u32,wire)?;
            (frame.into_iter().collect(),pending)
        }
    };
    let total=frames.len();
    let mut copied=0u32;
    let mut failed=false;
    let mut backpressure=false;
    for frame in &frames{
        match tun.deliver_authenticated(frame){
            Ok(())=>{copied+=1;c.rx.fetch_add(1,Ordering::Release);},
            Err(NativeIoError::BufferTooSmall)=>{
                // ERROR_BUFFER_OVERFLOW from Wintun AllocateSendPacket:
                // this bounded packet cannot be copied right now. Release
                // its prepared Game first-delivery reservation as NOT copied;
                // later authenticated sibling lanes may still deliver it.
                backpressure=true;break
            },
            Err(err)=>{
                eprintln!("M0_PLAN026_GAME_NATIVE_FIRST_ERROR role=RX stage=shared_wintun_delivery error={err:?}");
                failed=true;break
            },
        }
    }
    if backpressure && pending{
        // The decoder already consumed the unique authenticated symbol.
        // Retiring it now loses recovered source frames permanently, since
        // replay will correctly reject the same original PN. Preserve the
        // remaining payloads and their exact accepted kernel prefix instead.
        let slot=deferred.get_mut(lane).ok_or(INVALID)?;
        if slot.is_some(){return Err(BAD_STAGE)}
        *slot=Some(DeferredFec{
            seq,wire_len:wire.len(),copied,frames
        });
        return Ok(())
    }
    if pending{
        let mut g=group.lock().map_err(|_|BAD_STAGE)?;
        let rc=if game::native_game_has_fec(&g){
            game::finish_fec_group(&mut g,(lane+1) as u32,copied)
        }else{
            game::finish_off_group(&mut g,(lane+1) as u32,copied==1)
        };
        if rc!=OK{return Err(rc)}
    }
    if failed{return Err(BAD_STAGE)}
    if backpressure{
        c.rejected.fetch_add(1,Ordering::Relaxed);
        return Ok(()) // no kernel-delivery ledger, no synthetic TCP ACK
    }
    if copied as usize!=total{return Err(BAD_STAGE)}
    // The group game opener already verified independent original
    // authenticated AEAD/PN, so presentation ACK can only follow that.
    let ack=ledgers[lane].verified(seq,wire.len());
    c.ack[lane].store(ack,Ordering::Release);
    Ok(())
}
// Per-capture retirement never substitutes a shared Wintun or owner Stop.
// A real last-lane loss is terminal. No timers or replacement threads.
fn retire_game_tx_lane(active:&mut [bool],lane:usize)->bool{
    if let Some(slot)=active.get_mut(lane){*slot=false}
    active.iter().any(|&ok|ok)
}
fn retire_game_rx_lane(active:&mut [bool],lane:usize)->bool{
    if let Some(slot)=active.get_mut(lane){*slot=false}
    active.iter().any(|&ok|ok)
}
// Only one RX worker owns all deferred FEC batches. Up to 4 lanes x
// 16 restored frames; never a new decoder, packet seal, or TX timer.
fn flush_deferred_fec(
    group:&Arc<Mutex<game::WinGameGroup>>,tun:&mut WintunTx,
    c:&GameCounters,ledgers:&mut [AckLedger],
    deferred:&mut [Option<DeferredFec>],
)->Result<bool,i32>{
    let mut finished_any=false;
    for (i,slot) in deferred.iter_mut().enumerate(){
        let Some(row)=slot.as_mut()else{continue};
        while (row.copied as usize)<row.frames.len(){
            match tun.deliver_authenticated(&row.frames[row.copied as usize]){
                Ok(())=>{
                    row.copied+=1;
                    c.rx.fetch_add(1,Ordering::Release);
                },
                Err(NativeIoError::BufferTooSmall)=>break,
                Err(err)=>{
                    eprintln!("M0_PLAN027_GAME_FEC_DEFERRED_TUN_FATAL lane={} copied={} error={err:?}",i+1,row.copied);
                    return Err(BAD_STAGE)
                },
            }
        }
        if row.copied as usize==row.frames.len(){
            // Commit Game logical-first delivery only after ALL restored
            // frames have actually passed the original Wintun kernel writer.
            let rc={
                let mut g=group.lock().map_err(|_|BAD_STAGE)?;
                game::finish_fec_group(&mut g,(i+1) as u32,row.copied)
            };
            if rc!=OK{return Err(rc)}
            let ack=ledgers[i].verified(row.seq,row.wire_len);
            c.ack[i].store(ack,Ordering::Release);
            *slot=None;
            finished_any=true;
        }
    }
    Ok(finished_any)
}
fn abort_deferred_fec(group:&Arc<Mutex<game::WinGameGroup>>,
    deferred:&mut [Option<DeferredFec>])->i32{
    let Ok(mut g)=group.lock()else{return BAD_STAGE};
    for (i,slot) in deferred.iter_mut().enumerate(){
        if let Some(row)=slot.take(){
            let rc=game::finish_fec_group(&mut g,(i+1) as u32,row.copied);
            if rc!=OK{return rc}
        }
    }
    OK
}
fn rx_loop(cfg:WbdWinGameNativeAttachV3,lanes:Vec<LaneConfig>,
    group:Arc<Mutex<game::WinGameGroup>>,mut tun:WintunTx,
    mut npf:Vec<NpcapRx>,stop:Arc<WakeEvent>,wake:Arc<WakeEvent>,
    tx_wake:Arc<WakeEvent>,early:Arc<Mutex<VecDeque<(usize,u32,Vec<u8>)>>>,
    c:Arc<GameCounters>,
)->i32{
    let mut ledgers:Vec<AckLedger>=lanes.iter().map(|x|AckLedger::new(x.rx_seq)).collect();
    let mut deferred:Vec<Option<DeferredFec>>=(0..lanes.len()).map(|_|None).collect();
    // A dead Npcap capture is lane-local. Stop/shared Wintun errors remain
    // group-wide. Rebuild the wait set only upon lane retirement (cold path).
    let mut active=vec![true;npf.len()];
    let mut events=vec![0usize;npf.len()];
    for (i,rx) in npf.iter().enumerate(){
        match rx.event(){
            Ok(e)=>events[i]=e,
            Err(err)=>{
                eprintln!("M0_PLAN026_GAME_NATIVE_RX_LANE_RETIRED lane={} stage=event reason={err:?}",i+1);
                active[i]=false;
            },
        }
    }
    if !active.iter().any(|&ok|ok){return BAD_STAGE}
    let mut handles=vec![stop.handle(),wake.handle()];
    for (i,&e) in events.iter().enumerate(){if active[i]&&deferred[i].is_none(){handles.push(e)}};
    let mut frame=[0u8;NPF_CAP];
    loop{
        if c.stop.load(Ordering::Acquire){
            return abort_deferred_fec(&group,&mut deferred)
        }
        match flush_deferred_fec(&group,&mut tun,&c,&mut ledgers,&mut deferred){
            Ok(true)=>{let _=tx_wake.wake();},
            Ok(false)=>{},
            Err(e)=>return e,
        }
        // A backpressured lane must not block sibling original Go TLS
        // handoff records behind it in the bounded early queue. Rotate only
        // the already admitted prefix; no second packet owner or busy loop.
        let queued=match early.lock(){Ok(q)=>q.len(),Err(_)=>return BAD_STAGE};
        for _ in 0..queued{
            let row=match early.lock(){Ok(mut q)=>q.pop_front(),Err(_)=>return BAD_STAGE};
            let Some((i,seq,wire))=row else{break};
            if deferred.get(i).is_some_and(Option::is_some){
                let Ok(mut q)=early.lock()else{return BAD_STAGE};
                q.push_back((i,seq,wire));continue
            }
            match receive_one(&cfg,&group,&mut tun,&c,&mut ledgers,
                &mut deferred,i,seq,&wire){
                Ok(())=>{let _=tx_wake.wake();},
                Err(INVALID)=>{c.rejected.fetch_add(1,Ordering::Relaxed);},
                Err(e)=>return e,
            }
        }
        // A successfully retried FEC batch can reopen an NPF RX lane in
        // THIS turn. Rebuild the event set BEFORE an infinite wait; keeping
        // last turn's handles would strand a now-healthy lane forever.
        handles.truncate(2);
        for (i,&e) in events.iter().enumerate(){
            if active[i]&&deferred[i].is_none(){handles.push(e)}
        }
        // Never park indefinitely while a real decoded FEC batch is
        // awaiting Wintun capacity; never poll when there is no backlog.
        let timeout=if deferred.iter().any(Option::is_some){5}else{u32::MAX};
        match io::wait_ready(&handles,timeout){
            Ok(WaitResult::Ready(0))=>{
                return abort_deferred_fec(&group,&mut deferred)
            },
            Ok(WaitResult::Ready(_)|WaitResult::Timeout)=>{},
            Ok(other)=>{
                eprintln!("M0_PLAN026_GAME_NATIVE_FIRST_ERROR role=RX stage=event_wait unexpected={other:?}");
                return BAD_STAGE
            },
            Err(err)=>{
                eprintln!("M0_PLAN026_GAME_NATIVE_FIRST_ERROR role=RX stage=event_wait reason={err:?}");
                return BAD_STAGE
            },
        }
        let mut verified=false;
        // One RX thread and one shared Wintun, read each lane fairly.
        for (i,rx) in npf.iter_mut().enumerate(){
            if !active[i]||deferred[i].is_some(){continue}
            for _ in 0..32{
                if c.stop.load(Ordering::Acquire){
                    return abort_deferred_fec(&group,&mut deferred)
                }
                let n=match rx.read(&mut frame){
                    Ok(ReadResult::Frame(n))=>n,
                    Ok(ReadResult::Skipped)=>continue,
                    Ok(ReadResult::NoPacket)=>break,
                    Ok(ReadResult::EndOfStream)=>{
                        eprintln!("M0_PLAN026_GAME_NATIVE_RX_LANE_RETIRED lane={} stage=npcap_read reason=EndOfStream",i+1);
                        let _=retire_game_rx_lane(&mut active,i);break
                    },
                    Err(err)=>{
                        eprintln!("M0_PLAN026_GAME_NATIVE_RX_LANE_RETIRED lane={} stage=npcap_read reason={err:?}",i+1);
                        let _=retire_game_rx_lane(&mut active,i);break
                    },
                };
                let Some(ipv4)=io::ethernet_ipv4(&frame[..n])else{continue};
                let l=&lanes[i];
                let trusted=trusted_windows_game_rx(
                    &cfg.first.peer_ip,&cfg.first.local_ip,
                    l.peer_port,l.local_port,cfg.first.path_mtu as usize,
                );
                let Ok(p)=parse_data_packet(ipv4,trusted)else{continue};
                match receive_one(&cfg,&group,&mut tun,&c,&mut ledgers,
                    &mut deferred,i,p.seq32,p.ciphertext){
                    Ok(())=>verified=true,
                    Err(INVALID)=>{c.rejected.fetch_add(1,Ordering::Relaxed);},
                    Err(e)=>return e,
                }
            }
        }
        if verified{let _=tx_wake.wake();}
        // All lanes lost is a genuine terminal group failure; a single
        // inactive Npcap RX handle must NOT stop sibling genuine copies.
        if !active.iter().any(|&ok|ok){
            eprintln!("M0_PLAN026_GAME_NATIVE_FIRST_ERROR role=RX stage=all_npcap_lanes_retired");
            return BAD_STAGE
        }
        // A retired capture is no longer a valid WaitForMultipleObjects
        // handle. Preserve Stop and original Go early-wake in every set.
        handles.truncate(2);
        for (i,&e) in events.iter().enumerate(){
            if active[i]&&deferred[i].is_none(){handles.push(e)}
        }
    }
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_game_native_v3_start(
    ptr:*const WbdWinGameNativeAttachV3,
)->i32{
    if ptr.is_null(){return INVALID}
    let cfg=unsafe{*ptr};
    let lanes=match configs(&cfg){Ok(v)=>v,Err(e)=>return e};
    let group=match game::native_game_group(cfg.group,cfg.first.epoch,
        cfg.first.luid,cfg.first.ifindex,lanes.len(),&lanes.iter().map(|x|x.owner).collect::<Vec<_>>()){
        Ok(v)=>v,Err(e)=>return e,
    };
    {
        let g=match group.lock(){Ok(v)=>v,Err(_)=>return BAD_STAGE};
        if game::native_game_has_fec(&g)!=(cfg.fec==1){return INVALID}
    }
    let (tun_rx,tun_tx)=match unsafe{io::split_borrowed_wintun(
        cfg.first.wintun_session,cfg.first.wintun_read_event,cfg.first.wintun)}{
        Ok(v)=>v,Err(_)=>return BAD_STAGE,
    };
    let mut captures=Vec::with_capacity(lanes.len());
    let mut senders=Vec::with_capacity(lanes.len());
    for l in &lanes{
        let rx=match unsafe{NpcapRx::from_borrowed(l.rx_capture,l.npcap)}{
            Ok(v)=>v,Err(_)=>return BAD_STAGE
        };
        if rx.event().is_err(){return BAD_STAGE}
        let tx=match unsafe{NpcapTx::from_borrowed(l.tx_capture,l.npcap)}{
            Ok(v)=>v,Err(_)=>return BAD_STAGE
        };
        captures.push(rx);senders.push(tx);
    }
    let stop=match WakeEvent::new(){Ok(v)=>Arc::new(v),Err(_)=>return BAD_STAGE};
    let tx_wake=match WakeEvent::new_auto(){Ok(v)=>Arc::new(v),Err(_)=>return BAD_STAGE};
    let rx_wake=match WakeEvent::new_auto(){Ok(v)=>Arc::new(v),Err(_)=>return BAD_STAGE};
    let counters=Arc::new(GameCounters::new(&lanes));
    let early=Arc::new(Mutex::new(VecDeque::with_capacity(EARLY_CAP)));
    let mut sessions=match sessions().lock(){Ok(v)=>v,Err(_)=>return BAD_STAGE};
    if sessions.contains_key(&cfg.group){return BAD_STAGE}
    let tx_group=Arc::clone(&group);
    let tx_stop=Arc::clone(&stop);
    let tx_notify=Arc::clone(&tx_wake);
    let tx_counters=Arc::clone(&counters);
    let tx_lanes=lanes.clone();
    let tx=match thread::Builder::new().name("wbd-game-native-tx".into()).spawn(move||{
        let rc=tx_loop(cfg,tx_lanes,tx_group,tun_rx,senders,
            Arc::clone(&tx_stop),tx_notify,Arc::clone(&tx_counters));
        if rc!=OK{
            eprintln!("M0_PLAN026_GAME_NATIVE_FIRST_ERROR role=TX stage=worker_exit rc={rc}");
            tx_counters.err.store(rc,Ordering::Release);
            let _=tx_stop.wake();
        }
        rc
    }){Ok(t)=>t,Err(_)=>return BAD_STAGE};
    let rx_stop=Arc::clone(&stop);
    let rx_group=Arc::clone(&group);
    let rx_notify=Arc::clone(&rx_wake);
    let wake_tx=Arc::clone(&tx_wake);
    let rx_counter=Arc::clone(&counters);
    let rx_early=Arc::clone(&early);
    let rx=match thread::Builder::new().name("wbd-game-native-rx".into()).spawn(move||{
        let rc=rx_loop(cfg,lanes,rx_group,tun_tx,captures,
            Arc::clone(&rx_stop),rx_notify,wake_tx,rx_early,
            Arc::clone(&rx_counter));
        if rc!=OK{
            eprintln!("M0_PLAN026_GAME_NATIVE_FIRST_ERROR role=RX stage=worker_exit rc={rc}");
            rx_counter.err.store(rc,Ordering::Release);
            let _=rx_stop.wake();
        }
        rc
    }){
        Ok(t)=>t,Err(_)=>{
            counters.stop.store(true,Ordering::Release);
            let _=stop.wake();
            let _=tx.join();
            return BAD_STAGE
        }
    };
    sessions.insert(cfg.group,GameSession{
        stop,tx_wake,rx_wake,early,counters,tx,rx,
    });
    OK
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_game_native_v3_early(
    h:u64,lane:u32,seq:u32,wire:*const u8,len:usize,
)->i32{
    if wire.is_null()||len<32||len>1536{return INVALID}
    let map=match sessions().lock(){Ok(v)=>v,Err(_)=>return BAD_STAGE};
    let Some(s)=map.get(&h)else{return UNKNOWN};
    let Ok(i)=usize::try_from(lane)else{return INVALID};
    if i==0||i>4{return INVALID}
    let mut q=match s.early.lock(){Ok(v)=>v,Err(_)=>return BAD_STAGE};
    if q.len()>=EARLY_CAP{return FULL}
    q.push_back((i-1,seq,unsafe{std::slice::from_raw_parts(wire,len)}.to_vec()));
    drop(q);let _=s.rx_wake.wake();OK
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_game_native_v3_stats(
    h:u64,out:*mut WbdWinNativeStatsV1,
)->i32{
    if out.is_null(){return INVALID}
    let map=match sessions().lock(){Ok(v)=>v,Err(_)=>return BAD_STAGE};
    let Some(s)=map.get(&h)else{return UNKNOWN};
    unsafe{out.write(s.counters.snapshot())};OK
}
#[no_mangle]
pub extern "C" fn wbd_m0_win_game_native_v3_stop(h:u64)->i32{
    let session={
        let mut map=match sessions().lock(){Ok(v)=>v,Err(_)=>return BAD_STAGE};
        let Some(s)=map.remove(&h)else{return UNKNOWN};s
    };
    session.counters.stop.store(true,Ordering::Release);
    let _=session.stop.wake();
    let _=session.tx_wake.wake();let _=session.rx_wake.wake();
    let tx=session.tx.join().unwrap_or(STOP_INCOMPLETE);
    let rx=session.rx.join().unwrap_or(STOP_INCOMPLETE);
    if tx!=OK&&tx!=BAD_STAGE{return tx}
    if rx!=OK&&rx!=BAD_STAGE{return rx}
    OK // all real Wintun+Npcap loans returned before Go Stop/EndSession
}
#[cfg(test)]
mod tests{
    use super::*;
    #[test]
    fn game_v3_rejects_missing_owned_attachment_without_driver_borrow(){
        assert_eq!(unsafe{wbd_m0_win_game_native_v3_start(std::ptr::null())},INVALID);
        assert_eq!(unsafe{wbd_m0_win_game_native_v3_early(
            1,1,100,std::ptr::null(),32)},INVALID);
        assert_eq!(unsafe{wbd_m0_win_game_native_v3_stats(
            1,std::ptr::null_mut())},INVALID);
    }
    #[test]
    fn native_game_idle_waits_for_event_and_stagger_deadline_not_fixed_10ms_poll(){
        assert_eq!(game_wait_timeout_ms(1_000_000,None),u32::MAX);
        assert_eq!(game_wait_timeout_ms(0,Some(4_000_000)),4);
        assert_eq!(game_wait_timeout_ms(0,Some(50_000_000)),50);
        assert_eq!(game_wait_timeout_ms(0,Some(140_000_000)),140);
        assert_eq!(game_wait_timeout_ms(140_000_000,Some(140_000_000)),1);
        assert_eq!(game_wait_timeout_ms(140_000_000,Some(140_000_001)),1);
    }
    #[test]
    fn game_native_npf_rx_accepts_original_linux_server_windows11_persona_only(){
        use wbd_platform::rx_ipv4_tcp::RxError;
        let server=[172,24,106,93];let client=[172,24,96,1];
        let trusted=trusted_windows_game_rx(&server,&client,443,41031,1400);
        assert_eq!(trusted.persona,PacketPersona::Windows11);
        let tuple=Ipv4Tuple{src_ip:&server,dst_ip:&client,
            src_port:443,dst_port:41031};
        let mut scratch=[0u8;256];
        let data=build_bytes(tuple,Presentation{
            ack32:991,advertised_window:4096,ip_id:75,
            persona:PacketPersona::Windows11,
        },u64::from(1234u32),&[8,7,6,5,4],None,1400,&mut scratch)
            .unwrap().to_vec();
        let accepted=parse_data_packet(&data,trusted).unwrap();
        assert_eq!(accepted.seq32,1234);
        assert_eq!(accepted.ciphertext,&[8,7,6,5,4]);
        // SOURCE768 trusted Legacy TTL64 and rejected the real Linux server
        // Windows11 TTL128 live frames after pre-handoff early packets.
        assert_eq!(parse_data_packet(&data,TrustedRx{
            persona:PacketPersona::Legacy,..trusted
        }),Err(RxError::WrongPersona));
        // Do not widen parser to accept any unauthenticated carrier persona.
        let mut other=[0u8;256];
        let legacy=build_bytes(tuple,Presentation{
            ack32:991,advertised_window:4096,ip_id:75,
            persona:PacketPersona::Legacy,
        },u64::from(1234u32),&[8,7,6,5,4],None,1400,&mut other)
            .unwrap().to_vec();
        assert_eq!(parse_data_packet(&legacy,trusted),Err(RxError::WrongPersona));
    }
    #[test]
    fn game_presentation_ack_is_real_empty_payload_tcp_control_not_empty_data(){
        use wbd_platform::ipv4_tcp::PacketError;
        let src=[172,18,80,1];let dst=[172,18,95,17];
        let tuple=Ipv4Tuple{src_ip:&src,dst_ip:&dst,src_port:41031,dst_port:443};
        let src_mac=[0,0x15,0x5d,0xbd,0xd7,0x55];
        let dst_mac=[0,0x15,0x5d,0xc5,0x4c,0x29];
        let mut bytes=[0u8;FRAME_CAP];
        let packet=presentation_ack_frame(tuple,src_mac,dst_mac,
            0x11223344,0x55667788,9,1500,&mut bytes).unwrap();
        assert_eq!(packet.len(),54); // 14 Ethernet + 20 IPv4 + 20 TCP
        assert_eq!(&packet[0..6],&dst_mac);
        assert_eq!(&packet[6..12],&src_mac);
        assert_eq!(&packet[12..14],&[0x08,0x00]);
        assert_eq!(&packet[16..18],&40u16.to_be_bytes());
        assert_eq!(&packet[14+20..14+22],&41031u16.to_be_bytes());
        assert_eq!(&packet[14+22..14+24],&443u16.to_be_bytes());
        assert_eq!(&packet[14+24..14+28],&0x11223344u32.to_be_bytes());
        assert_eq!(&packet[14+28..14+32],&0x55667788u32.to_be_bytes());
        assert_eq!(packet[14+20+13],0x10); // ACK only, not PSH+ACK data
        assert!(packet[14+20+16..14+20+18].iter().any(|&x|x!=0));
        let mut data_scratch=[0u8;256];
        let data=build_bytes(tuple,Presentation{
            ack32:0x55667788,advertised_window:65535,
            ip_id:9,persona:PacketPersona::Windows11,
        },u64::from(0x11223344u32),&[],None,1500,&mut data_scratch);
        assert_eq!(data,Err(PacketError::EmptyRecord));
    }
    #[test]
    fn game_presentation_ack_fails_closed_for_too_small_native_mtu(){
        let src=[172,18,80,1];let dst=[172,18,95,17];
        let mut bytes=[0xa5;FRAME_CAP];
        let result=presentation_ack_frame(Ipv4Tuple{
            src_ip:&src,dst_ip:&dst,src_port:41031,dst_port:443,
        },[1;6],[2;6],1,1,1,39,&mut bytes);
        assert_eq!(result,Err(INVALID));
        assert!(bytes.iter().all(|&x|x==0xa5));
    }
    #[test]
    fn one_tx_npf_driver_failure_keeps_sibling_copy_and_last_loss_is_fatal(){
        let mut active=[true,true,true,true];
        assert!(retire_game_tx_lane(&mut active,0));
        assert_eq!(active,[false,true,true,true]);
        assert!(retire_game_tx_lane(&mut active,2));
        assert!(retire_game_tx_lane(&mut active,1));
        assert!(!retire_game_tx_lane(&mut active,3));
    }
    #[test]
    fn one_npf_capture_failure_keeps_other_game_lanes_and_stop_wait_live(){
        let mut active=[true,true,true,true];
        assert!(retire_game_rx_lane(&mut active,1));
        assert_eq!(active,[true,false,true,true]);
        assert!(retire_game_rx_lane(&mut active,0));
        assert!(retire_game_rx_lane(&mut active,2));
        assert!(!retire_game_rx_lane(&mut active,3)); // all genuinely retired
    }
    #[test]
    fn game_ack_ledger_copies_only_actual_gap_closure(){
        let mut a=AckLedger::new(1000);
        assert_eq!(a.verified(1200,100),1000);
        assert_eq!(a.verified(1000,200),1300);
        assert_eq!(a.verified(1300,200),1500);
        assert_eq!(a.verified(1000,100),1500);
    }
}
