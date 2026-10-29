//! PLAN026 Game2/4 genuine Npcap/Wintun native two-worker handoff.
//! Original independent Go TLS lanes and the SINGLE Linux GameAdapter
//! remain the sole cryptographic/FEC authorities. Go has no steady packet
//! callbacks. Every M4 outcome is an actual Npcap driver receipt.
use super::*;
use std::sync::atomic::{AtomicBool,AtomicI32,AtomicU32,AtomicU64,Ordering};
use std::sync::{Arc,Mutex,OnceLock};
use std::collections::{BTreeMap,VecDeque};
use std::thread::{self,JoinHandle};
use wbd_platform::windows_native_io::{
    self as io,NpcapRx,NpcapTx,NpcapFns,WintunRx,WintunTx,
    WintunFns,WakeEvent,ReadResult,WaitResult,
};
use wbd_platform::ipv4_tcp::{
    build_bytes,Ipv4Tuple,Presentation,PacketPersona,
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
fn send_records(group:u64,cfg:&WbdWinNativeAttachV1,
    owner:&Arc<Mutex<game::WinGameGroup>>,
    lanes:&[LaneConfig],npf:&mut [NpcapTx],c:&GameCounters,
    records:Vec<game::WbdWindowsGameRecordV4>,ip_id:&mut u16,
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
        let outcome=npf[idx].send_batch(&[frame]);
        let copied=outcome.accepted_prefix==1;
        // Settle this exact original Linux GameAdapter staged ticket
        // AFTER the real Npcap success/unknown/not-sent result. No Go
        // fake receipt, no inferred application ACK.
        let rc={
            let mut g=owner.lock().map_err(|_|BAD_STAGE)?;
            game::game_m4_result_group(&mut g,group,r.lane,r.logical_id,r.pn,copied)
        };
        if rc!=OK{return Err(rc)}
        if copied{
            c.tx_seq[idx].fetch_add(r.length,Ordering::Release);
            c.ack_sent[idx].store(ack,Ordering::Release);
            c.tx.fetch_add(1,Ordering::Relaxed);
            if c.rx.load(Ordering::Acquire)>0{c.after.fetch_add(1,Ordering::Relaxed);}
        }
        if outcome.error.is_some()||outcome.uncertain_index.is_some(){
            return Err(BAD_STAGE)
        }
    }
    Ok(total)
}
fn send_ack(cfg:&WbdWinNativeAttachV1,lanes:&[LaneConfig],
    npf:&mut [NpcapTx],c:&GameCounters,ip_id:&mut u16,
)->Result<(),i32>{
    for (i,l) in lanes.iter().enumerate(){
        let ack=c.ack[i].load(Ordering::Acquire);
        if ack==c.ack_sent[i].load(Ordering::Acquire){continue}
        let mut scratch=[0u8;FRAME_CAP];
        let frame=wire_frame(cfg,l,c.tx_seq[i].load(Ordering::Acquire),
            ack,&[],*ip_id,&mut scratch)?;
        *ip_id=ip_id.wrapping_add(1);
        let status=npf[i].send_batch(&[frame]);
        if status.accepted_prefix==1{
            c.ack_sent[i].store(ack,Ordering::Release)
        }
        if status.error.is_some(){return Err(BAD_STAGE)}
    }
    Ok(())
}
fn tx_loop(cfg:WbdWinGameNativeAttachV3,lanes:Vec<LaneConfig>,
    group:Arc<Mutex<game::WinGameGroup>>,
    mut tun:WintunRx,mut npf:Vec<NpcapTx>,stop:Arc<WakeEvent>,
    wake:Arc<WakeEvent>,c:Arc<GameCounters>,
)->i32{
    let mut bytes=[0u8;MAX_IPV4];let mut id=1u16;
    loop{
        if c.stop.load(Ordering::Acquire){return OK}
        let mut did_work=false;
        for _ in 0..8{
            if c.stop.load(Ordering::Acquire){return OK}
            match tun.read(&mut bytes){
                Ok(ReadResult::Frame(n))=>{
                    let records=match group.lock(){
                        Ok(mut g)=>game::offer_records_native(&mut g,cfg.group,&bytes[..n]),
                        Err(_)=>return BAD_STAGE,
                    };
                    let rows=match records{Ok(v)=>v,Err(INVALID)=>{
                        c.rejected.fetch_add(1,Ordering::Relaxed);continue
                    },Err(e)=>return e};
                    if send_records(cfg.group,&cfg.first,&group,&lanes,&mut npf,
                        &c,rows,&mut id).is_err(){return BAD_STAGE}
                    did_work=true;
                }
                Ok(ReadResult::NoPacket|ReadResult::EndOfStream)=>break,
                Ok(ReadResult::Skipped)=>{
                    c.rejected.fetch_add(1,Ordering::Relaxed);
                }
                Err(_)=>return BAD_STAGE,
            }
        }
        // Same Game4 scheduler/FEC parity owner as original Linux.
        // One bounded due pass, no Go per-packet polling.
        let due=match group.lock(){
            Ok(mut g)=>game::native_game_due(&mut g,cfg.group,16),
            Err(_)=>return BAD_STAGE,
        };
        match due{
            Ok(rows) if !rows.is_empty()=>{
                if send_records(cfg.group,&cfg.first,&group,&lanes,
                    &mut npf,&c,rows,&mut id).is_err(){return BAD_STAGE}
                did_work=true;
            },
            Err(rc)=>return rc,
            _=>{},
        }
        if send_ack(&cfg.first,&lanes,&mut npf,&c,&mut id).is_err(){
            return BAD_STAGE
        }
        if did_work{continue}
        let timeout={
            let group=match group.lock(){Ok(g)=>g,Err(_)=>return BAD_STAGE};
            let (now,due)=game::native_game_wait_deadline(&group);
            game_wait_timeout_ms(now,due)
        };
        match io::wait_ready(&[stop.handle(),tun.event(),wake.handle()],timeout){
            Ok(WaitResult::Ready(0))=>return OK,
            Ok(WaitResult::Ready(1|2)|WaitResult::Timeout)=>{},
            _=>return BAD_STAGE,
        }
    }
}
fn receive_one(cfg:&WbdWinGameNativeAttachV3,
    group:&Arc<Mutex<game::WinGameGroup>>,tun:&mut WintunTx,
    c:&GameCounters,ledgers:&mut [AckLedger],lane:usize,seq:u32,wire:&[u8],
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
            let frame=game::receive_group(&mut g,cfg.group,(lane+1) as u32,wire)?;
            (frame.into_iter().collect(),false)
        }
    };
    let total=frames.len();
    let mut copied=0u32;
    let mut failed=false;
    for frame in frames{
        if tun.deliver_authenticated(&frame).is_err(){failed=true;break}
        copied+=1;c.rx.fetch_add(1,Ordering::Release);
    }
    if pending{
        let mut g=group.lock().map_err(|_|BAD_STAGE)?;
        let rc=game::finish_fec_group(&mut g,(lane+1) as u32,copied);
        if rc!=OK{return Err(rc)}
    }
    if failed||copied as usize!=total{return Err(BAD_STAGE)}
    // The group game opener already verified independent original
    // authenticated AEAD/PN, so presentation ACK can only follow that.
    let ack=ledgers[lane].verified(seq,wire.len());
    c.ack[lane].store(ack,Ordering::Release);
    Ok(())
}
fn rx_loop(cfg:WbdWinGameNativeAttachV3,lanes:Vec<LaneConfig>,
    group:Arc<Mutex<game::WinGameGroup>>,mut tun:WintunTx,
    mut npf:Vec<NpcapRx>,stop:Arc<WakeEvent>,wake:Arc<WakeEvent>,
    tx_wake:Arc<WakeEvent>,early:Arc<Mutex<VecDeque<(usize,u32,Vec<u8>)>>>,
    c:Arc<GameCounters>,
)->i32{
    let mut ledgers:Vec<AckLedger>=lanes.iter().map(|x|AckLedger::new(x.rx_seq)).collect();
    let events=match npf.iter().map(|x|x.event()).collect::<Result<Vec<_>,_>>(){
        Ok(e)=>e,Err(_)=>return BAD_STAGE,
    };
    let mut handles=vec![stop.handle(),wake.handle()];
    handles.extend_from_slice(&events);
    let mut frame=[0u8;NPF_CAP];
    loop{
        if c.stop.load(Ordering::Acquire){return OK}
        // Drain real Go TLS->Rust handoff backlog before new Npcap records.
        loop{
            let row=match early.lock(){Ok(mut q)=>q.pop_front(),Err(_)=>return BAD_STAGE};
            let Some((i,seq,wire))=row else{break};
            match receive_one(&cfg,&group,&mut tun,&c,&mut ledgers,i,seq,&wire){
                Ok(())=>{let _=tx_wake.wake();},
                Err(INVALID)=>{c.rejected.fetch_add(1,Ordering::Relaxed);},
                Err(e)=>return e,
            }
        }
        match io::wait_ready(&handles,u32::MAX){
            Ok(WaitResult::Ready(0))=>return OK,
            Ok(WaitResult::Ready(_))=>{},
            _=>return BAD_STAGE,
        }
        let mut verified=false;
        // One RX thread and one shared Wintun, read each lane fairly.
        for (i,rx) in npf.iter_mut().enumerate(){
            for _ in 0..32{
                if c.stop.load(Ordering::Acquire){return OK}
                let n=match rx.read(&mut frame){
                    Ok(ReadResult::Frame(n))=>n,
                    Ok(ReadResult::Skipped)=>continue,
                    Ok(ReadResult::NoPacket)=>break,
                    Ok(ReadResult::EndOfStream)|Err(_)=>return BAD_STAGE,
                };
                let Some(ipv4)=io::ethernet_ipv4(&frame[..n])else{continue};
                let l=&lanes[i];
                let trusted=TrustedRx{
                    tuple:Ipv4Tuple{
                        src_ip:&cfg.first.peer_ip,dst_ip:&cfg.first.local_ip,
                        src_port:l.peer_port,dst_port:l.local_port,
                    },
                    persona:PacketPersona::Legacy,mtu:cfg.first.path_mtu as usize,
                    authenticated_options:None,
                };
                let Ok(p)=parse_data_packet(ipv4,trusted)else{continue};
                match receive_one(&cfg,&group,&mut tun,&c,&mut ledgers,
                    i,p.seq32,p.ciphertext){
                    Ok(())=>verified=true,
                    Err(INVALID)=>{c.rejected.fetch_add(1,Ordering::Relaxed);},
                    Err(e)=>return e,
                }
            }
        }
        if verified{let _=tx_wake.wake();}
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
    fn game_ack_ledger_copies_only_actual_gap_closure(){
        let mut a=AckLedger::new(1000);
        assert_eq!(a.verified(1200,100),1000);
        assert_eq!(a.verified(1000,200),1300);
        assert_eq!(a.verified(1300,200),1500);
        assert_eq!(a.verified(1000,100),1500);
    }
}
