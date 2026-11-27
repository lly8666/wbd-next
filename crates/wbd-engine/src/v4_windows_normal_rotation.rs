//! Normal make-before-break on the original Wintun RX/TX workers.
//! Linux PLAN028 current/candidate/retiring ordering, adapted to one
//! WinXDP carrier and one pinned Windows OS/WAL anchor. No steady Go I/O.
use super::*;
use super::super::cold_port::NativeColdPort;
const IDLE:u32=0;
const COLD:u32=1;
const PROBE:u32=2;
const PROMOTE:u32=3;
const TX_SWITCHED:u32=4;
const GRACE:u32=5;
const ABORT:u32=6;
const ABORT_TX:u32=7;

#[derive(Clone)]
pub(super) struct NormalPath{
    pub(super) cfg:WbdWinNativeAttachV1,
    pub(super) lane:Arc<Mutex<Entry>>,
    pub(super) counters:Arc<Counters>,
    pub(super) sack:bool,
}
struct Paths{
    current:NormalPath,
    candidate:Option<NormalPath>,
    retiring:Option<NormalPath>,
    grace:Duration,
    deadline:Option<Instant>,
}
pub(super) struct NormalRotation{
    transport:NativeColdPort,
    phase:AtomicU32,
    paths:Mutex<Paths>,
    root:Arc<Counters>,
    current_id:AtomicU64,
    candidate_id:AtomicU64,
    retiring_id:AtomicU64,
    last_retired:AtomicU64,
    last_promoted:AtomicU64,
}
impl NormalRotation{
    pub(super) fn new(initial:NormalPath)->Self{
        let id=initial.cfg.owner;
        Self{transport:NativeColdPort::new(initial.cfg.rx_capture,[initial.cfg.local_port,0,0,0]),
            phase:AtomicU32::new(IDLE),root:Arc::clone(&initial.counters),
            paths:Mutex::new(Paths{current:initial,candidate:None,retiring:None,
                grace:Duration::ZERO,deadline:None}),current_id:AtomicU64::new(id),
            candidate_id:AtomicU64::new(0),retiring_id:AtomicU64::new(0),
            last_retired:AtomicU64::new(0),last_promoted:AtomicU64::new(0)}
    }
    fn phase(&self)->u32{self.phase.load(Ordering::Acquire)}
    pub(super) fn owns(&self,h:u64)->bool{
        h!=0&&[&self.current_id,&self.candidate_id,&self.retiring_id].iter()
            .any(|x|x.load(Ordering::Acquire)==h)
    }
    pub(super) fn begin(&self,port:u16)->Result<(),i32>{
        let paths=self.paths.lock().map_err(|_|BAD_STAGE)?;
        if self.phase()!=IDLE||port==paths.current.cfg.local_port{return Err(BAD_STAGE)}
        self.transport.begin(port)?;
        self.phase.store(COLD,Ordering::Release);Ok(())
    }
    // Go has joined the selected original TLS association's cold reader
    // before calling Stage. Its new epoch is NOT the product WAL epoch.
    fn stage(&self,owner:u64,entry:Arc<Mutex<Entry>>,port:u16,
        tx_seq:u32,rx_seq:u32,sack:bool)->Result<(),i32>{
        let mut p=self.paths.lock().map_err(|_|BAD_STAGE)?;
        if self.phase()!=COLD||self.transport.port.load(Ordering::Acquire)!=u32::from(port)||
            owner==p.current.cfg.owner||tx_seq==0||rx_seq==0{return Err(INVALID)}
        let mut cfg=p.current.cfg;
        let old=p.current.lane.lock().map_err(|_|BAD_STAGE)?;
        let mut e=entry.lock().map_err(|_|BAD_STAGE)?;
        if e.role_server||e.feature7||e.game_group.is_some()||e.authenticated_epoch==cfg.epoch||
            !v3_ready(&e,e.authenticated_epoch,cfg.luid,cfg.ifindex)||
            e.path_mtu!=old.path_mtu||e.path_mtu_is_outer!=old.path_mtu_is_outer||
            e.record_wire_limit!=old.record_wire_limit||e.peer_mss<old.peer_mss||
            e.m2.is_none(){return Err(INVALID)}
        cfg.owner=owner;cfg.epoch=e.authenticated_epoch;
        cfg.local_port=port;cfg.initial_tx_seq=tx_seq;cfg.initial_rx_seq=rx_seq;
        // Original Normal authenticated client Health sends its existing
        // cold burst; Linux promotes the new server /32 after real M4 RX.
        e.m2.as_mut().ok_or(BAD_STAGE)?.health.arm_client_cold_ready(m2_clock().0);
        drop(e);drop(old);
        let next=NormalPath{cfg,lane:entry,counters:Arc::new(Counters::new(rx_seq,tx_seq)),sack};
        p.candidate=Some(next);
        self.candidate_id.store(owner,Ordering::Release);
        self.phase.store(PROBE,Ordering::Release);Ok(())
    }
    fn candidate(&self)->Result<Option<NormalPath>,i32>{
        Ok(self.paths.lock().map_err(|_|BAD_STAGE)?.candidate.clone())
    }
    fn candidate_ready(&self,port:u16)->Result<bool,i32>{
        if self.phase()!=PROBE{return Ok(false)}
        let p=self.candidate()?.ok_or(BAD_STAGE)?;
        if p.cfg.local_port!=port{return Err(INVALID)}
        if p.counters.feedback_outer_bytes.load(Ordering::Acquire)==0{return Ok(false)}
        let e=p.lane.lock().map_err(|_|BAD_STAGE)?;
        let m=e.m2.as_ref().ok_or(BAD_STAGE)?;
        // No old lane or TCP ACK can authorize this distinct epoch.
        Ok(!m.health.peer_retired()&&m.health.last_authenticated_age_ns(m2_clock().0).is_some())
    }
    fn request_promote(&self,port:u16,grace_ms:u32)->Result<u64,i32>{
        if !(10000..=20000).contains(&grace_ms)||!self.candidate_ready(port)?{return Err(BAD_STAGE)}
        let mut p=self.paths.lock().map_err(|_|BAD_STAGE)?;
        if self.phase()!=PROBE{return Err(BAD_STAGE)}
        let id=p.candidate.as_ref().ok_or(BAD_STAGE)?.cfg.owner;
        p.grace=Duration::from_millis(u64::from(grace_ms));
        self.phase.store(PROMOTE,Ordering::Release);Ok(id)
    }
    /// TX owner changes at a settled batch boundary; no prior ACK, repair
    /// or old RX completion is a gate for fresh business on the successor.
    pub(super) fn tx_turn(&self,npf:&mut NativeTx,ip_id:&mut u16,
        wake_rx:&WakeEvent)->Result<(Option<NormalPath>,bool),i32>{
        match self.phase(){
            COLD=>{self.transport.send_one(npf)?;Ok((None,false))},
            PROBE=>{
                let p=self.candidate()?.ok_or(BAD_STAGE)?;
                let copied=send_control(&p.cfg,&p.lane,npf,&p.counters,ip_id)?;
                Ok((None,copied))
            },
            PROMOTE=>{
                let mut p=self.paths.lock().map_err(|_|BAD_STAGE)?;
                let next=p.candidate.take().ok_or(BAD_STAGE)?;
                let old=std::mem::replace(&mut p.current,next.clone());
                self.retiring_id.store(old.cfg.owner,Ordering::Release);
                self.current_id.store(next.cfg.owner,Ordering::Release);
                self.candidate_id.store(0,Ordering::Release);
                p.retiring=Some(old);
                // Grace starts at actual TX publication, not at timer due
                // or candidate TLS start. RX observes this same deadline.
                p.deadline=Some(Instant::now()+p.grace);
                self.phase.store(TX_SWITCHED,Ordering::Release);
                drop(p);let _=wake_rx.wake();
                Ok((Some(next),true))
            },
            ABORT=>{self.phase.store(ABORT_TX,Ordering::Release);let _=wake_rx.wake();Ok((None,false))},
            _=>Ok((None,false)),
        }
    }
    pub(super) fn probe_wait_ms(&self)->u32{
        if self.phase()!=PROBE{return u32::MAX}
        let Ok(Some(p))=self.candidate()else{return u32::MAX};
        let Ok(e)=p.lane.lock()else{return u32::MAX};
        e.m2.as_ref().and_then(|m|m.health.next_tx_deadline()).map_or(u32::MAX,|d|
            d.saturating_sub(m2_clock().0).div_ceil(1_000_000).max(1).min(u64::from(u32::MAX-1)) as u32)
    }
    fn rx_candidate(&self)->Result<Option<NormalPath>,i32>{
        let p=self.paths.lock().map_err(|_|BAD_STAGE)?;
        Ok(if self.phase()==TX_SWITCHED{Some(p.current.clone())}else{p.candidate.clone()})
    }
    fn finish_rx_switch(&self,port:u16)->Result<(),i32>{
        self.transport.detach(port)?;
        let p=self.paths.lock().map_err(|_|BAD_STAGE)?;
        self.last_promoted.store(p.current.cfg.owner,Ordering::Release);
        self.phase.store(GRACE,Ordering::Release);
        eprintln!("WBD_WINDOWS_NORMAL_MBB_PROMOTED old_owner={} new_owner={} old_rx_alive=1 same_wintun=1 grace_ms={}",
            self.retiring_id.load(Ordering::Acquire),p.current.cfg.owner,p.grace.as_millis());
        Ok(())
    }
    fn retire_due(&self)->bool{
        self.phase()==GRACE&&self.paths.lock().is_ok_and(|p|p.deadline.is_some_and(|d|Instant::now()>=d))
    }
    fn finish_retirement(&self)->Result<(),i32>{
        let mut p=self.paths.lock().map_err(|_|BAD_STAGE)?;
        let old=p.retiring.take().ok_or(BAD_STAGE)?;
        unsafe{wbd_platform::windows_xdp_rx::cold_change_port(self.transport.raw_rx,old.cfg.local_port,false)}
            .map_err(|_|BAD_STAGE)?;
        self.fold(&old.counters);
        p.deadline=None;
        self.retiring_id.store(0,Ordering::Release);
        self.last_retired.store(old.cfg.owner,Ordering::Release);
        self.phase.store(IDLE,Ordering::Release);
        eprintln!("WBD_WINDOWS_NORMAL_MBB_OLD_RX_RETIRED owner={} old_port={} native_rx_joined=1",
            old.cfg.owner,old.cfg.local_port);
        Ok(())
    }
    fn finish_abort(&self)->Result<(),i32>{
        let mut p=self.paths.lock().map_err(|_|BAD_STAGE)?;
        if let Some(c)=p.candidate.take(){
            self.transport.close(c.cfg.local_port)?;
            self.fold(&c.counters);
        }else{return Err(BAD_STAGE)}
        self.candidate_id.store(0,Ordering::Release);
        self.phase.store(IDLE,Ordering::Release);Ok(())
    }
    pub(super) fn rx_wait_ms(&self)->u32{
        if matches!(self.phase(),PROBE|PROMOTE|TX_SWITCHED)&&
            self.transport.rx.lock().is_ok_and(|q|!q.is_empty()){return 1}
        if self.phase()!=GRACE{return u32::MAX}
        self.paths.lock().ok().and_then(|p|p.deadline).map_or(u32::MAX,|d|
            d.saturating_duration_since(Instant::now()).as_millis().max(1).min(u128::from(u32::MAX-1)) as u32)
    }
    fn fold(&self,c:&Arc<Counters>){
        if Arc::ptr_eq(c,&self.root){return}
        // Only after RX/TX have relinquished this path. Preserve original
        // lifetime business and wire accounting across arbitrary renewals.
        macro_rules! add{($($f:ident),*)=>{$(
            self.root.$f.fetch_add(c.$f.load(Ordering::Relaxed),Ordering::Relaxed);
        )*}}
        add!(tx_copied,cipher_outside_lock,rx_delivered,rx_tx_notify_attempts,
            post_ingress_direct_to_rx,tx_after_rx,rejected,skipped_ipv6,fresh_outer_bytes,
            startup_pad_npf_bytes,startup_pad_npf_records,feedback_outer_bytes,
            repair_outer_bytes,repair_uncertain_bytes,pure_ack_outer_bytes,repair_packets);
    }
    pub(super) fn snapshot(&self)->WbdWinNativeStatsV1{
        let Ok(p)=self.paths.lock()else{return self.root.snapshot()};
        let mut out=self.root.snapshot();
        for path in std::iter::once(&p.current).chain(p.candidate.iter()).chain(p.retiring.iter()){
            if Arc::ptr_eq(&path.counters,&self.root){continue}
            let c=path.counters.snapshot();
            out.tx_copied+=c.tx_copied;out.rx_delivered+=c.rx_delivered;
            out.tx_after_rx+=c.tx_after_rx;out.rejected+=c.rejected;
        }
        out
    }
    pub(super) fn mark_stop(&self){
        if let Ok(p)=self.paths.lock(){
            for path in std::iter::once(&p.current).chain(p.candidate.iter()).chain(p.retiring.iter()){
                path.counters.stopping.store(true,Ordering::Release);
            }
        }
    }
    pub(super) fn finish_stop(&self){
        if let Ok(p)=self.paths.lock(){
            for path in std::iter::once(&p.current).chain(p.candidate.iter()).chain(p.retiring.iter()){
                self.fold(&path.counters);
            }
        }
    }
}
struct RxPath{path:NormalPath,ack:PresentationAck}
impl RxPath{
    fn new(path:NormalPath)->Self{
        let ack=PresentationAck::new(path.cfg.initial_rx_seq);Self{path,ack}
    }
    fn receive(&mut self,packet:&[u8],tun:&mut WintunTx,plain:&mut [u8;MAX_IPV4],
        wake:&WakeEvent,dns:Option<&Arc<Mutex<TunnelDnsMap>>>)->Result<(),i32>{
        let cfg=&self.path.cfg;
        let trusted=TrustedRx{tuple:Ipv4Tuple{src_ip:&cfg.peer_ip,dst_ip:&cfg.local_ip,
            src_port:cfg.peer_port,dst_port:cfg.local_port},
            persona:PacketPersona::Legacy,mtu:cfg.path_mtu as usize,authenticated_options:None};
        let Ok(data)=parse_data_packet_fast(packet,trusted)else{return Ok(())};
        if open_and_deliver(cfg,&self.path.lane,tun,&self.path.counters,&mut self.ack,
            data.seq32,data.ciphertext,plain,false,dns)?{
            flush_tx_wake(wake,&self.path.counters);
        }
        Ok(())
    }
}
#[derive(Default)]
pub(super) struct RotationRx{candidate:Option<RxPath>,retiring:Option<RxPath>}
impl RotationRx{
    pub(super) fn turn(&mut self,r:&NormalRotation,cfg:&mut WbdWinNativeAttachV1,
        lane:&mut Arc<Mutex<Entry>>,counters:&mut Arc<Counters>,ack:&mut PresentationAck,
        sack:&mut bool,tun:&mut WintunTx,plain:&mut [u8;MAX_IPV4],wake:&WakeEvent,
        dns:Option<&Arc<Mutex<TunnelDnsMap>>>)->Result<bool,i32>{
        let phase=r.phase();
        if matches!(phase,PROBE|PROMOTE|TX_SWITCHED){
            if self.candidate.is_none(){
                if let Some(p)=r.rx_candidate()?{self.candidate=Some(RxPath::new(p));}
            }
            if let Some(p)=self.candidate.as_mut(){
                for _ in 0..32{
                    let frame=r.transport.rx.lock().map_err(|_|BAD_STAGE)?.pop_front();
                    let Some(frame)=frame else{break};
                    if let Some(ipv4)=io::ethernet_ipv4(&frame){p.receive(ipv4,tun,plain,wake,dns)?;}
                }
            }
        }
        if r.phase()==TX_SWITCHED&&r.transport.rx.lock().map_err(|_|BAD_STAGE)?.is_empty(){
            let Some(next)=self.candidate.take()else{return Ok(false)};
            let old=NormalPath{cfg:*cfg,lane:Arc::clone(lane),counters:Arc::clone(counters),sack:*sack};
            let old_ack=std::mem::replace(ack,next.ack);
            *cfg=next.path.cfg;*lane=next.path.lane;*counters=next.path.counters;*sack=next.path.sack;
            self.retiring=Some(RxPath{path:old,ack:old_ack});
            r.finish_rx_switch(cfg.local_port)?;return Ok(true)
        }
        if r.retire_due(){self.retiring.take();r.finish_retirement()?;}
        if r.phase()==ABORT_TX{self.candidate.take();r.finish_abort()?;}
        Ok(false)
    }
    pub(super) fn other(&mut self,r:&NormalRotation,active:u16,packet:&[u8],frame:&[u8],
        tun:&mut WintunTx,plain:&mut [u8;MAX_IPV4],wake:&WakeEvent,
        dns:Option<&Arc<Mutex<TunnelDnsMap>>>)->Result<bool,i32>{
        if packet.len()<20||packet[9]!=6{return Ok(false)}
        let off=usize::from(packet[0]&15)*4;
        let Some(p)=packet.get(off+2..off+4)else{return Ok(false)};
        let port=u16::from_be_bytes([p[0],p[1]]);
        if port==active{return Ok(false)}
        for path in self.candidate.iter_mut().chain(self.retiring.iter_mut()){
            if path.path.cfg.local_port==port{
                path.receive(packet,tun,plain,wake,dns)?;return Ok(true)
            }
        }
        // During TLS (or one genuine RX batch racing Stage) only the
        // distinct reserved port enters the shared bounded cold mailbox.
        r.transport.offer_rx(port,frame);Ok(true)
    }
}
fn get(h:u64)->Result<(Arc<NormalRotation>,Arc<WakeEvent>,Arc<WakeEvent>),i32>{
    let map=active().lock().map_err(|_|BAD_STAGE)?;
    let s=map.get(&h).ok_or(UNKNOWN)?;
    if s.counters.stopping.load(Ordering::Acquire)||s.counters.worker_error.load(Ordering::Acquire)!=0{
        return Err(BAD_STAGE)
    }
    Ok((s.rotation.clone().ok_or(INVALID)?,Arc::clone(&s.tx_notify),Arc::clone(&s.rx_notify)))
}
fn wake_both(tx:&WakeEvent,rx:&WakeEvent)->Result<(),i32>{
    tx.wake().map_err(|_|BAD_STAGE)?;rx.wake().map_err(|_|BAD_STAGE)?;Ok(())
}
#[no_mangle]
pub extern "C" fn wbd_m0_win_normal_candidate_port(h:u64,port:u16,add:u32)->i32{
    let (r,tx,rx)=match get(h){Ok(v)=>v,Err(e)=>return e};
    let result=(||->Result<(),i32>{
        if add==1{return r.begin(port)}
        if add!=0||r.transport.port.load(Ordering::Acquire)!=u32::from(port){return Err(INVALID)}
        if r.phase()==COLD{
            r.transport.close(port)?;r.phase.store(IDLE,Ordering::Release);return Ok(())
        }
        if r.phase()!=PROBE{return Err(BAD_STAGE)}
        r.phase.store(ABORT,Ordering::Release);wake_both(&tx,&rx)?;
        let until=Instant::now()+Duration::from_secs(4);
        while r.phase()!=IDLE{
            if Instant::now()>=until{return Err(STOP_INCOMPLETE)}
            thread::sleep(Duration::from_millis(10));
        }
        Ok(())
    })();
    result.map_or_else(|e|e,|()|OK)
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_normal_candidate_read(h:u64,port:u16,dst:*mut u8,cap:usize)->i32{
    if dst.is_null()||cap==0||cap>4096{return -1}
    let Ok((r,_,_))=get(h)else{return -1};
    if r.phase()!=COLD{return -1}
    r.transport.read(port,unsafe{std::slice::from_raw_parts_mut(dst,cap)})
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_normal_candidate_write(h:u64,port:u16,frame:*const u8,len:usize)->i32{
    if frame.is_null()||len<54||len>2304{return -1}
    let Ok((r,tx,_))=get(h)else{return -1};
    if r.phase()!=COLD{return -1}
    r.transport.write(port,unsafe{std::slice::from_raw_parts(frame,len)},&tx)
}
#[no_mangle]
pub extern "C" fn wbd_m0_win_normal_candidate_stage(h:u64,owner:u64,port:u16,tx_seq:u32,rx_seq:u32,sack:u32)->i32{
    if sack>1{return INVALID}
    let entry=match lookup(owner){Ok(v)=>v,Err(e)=>return e};
    let (r,tx,rx)=match get(h){Ok(v)=>v,Err(e)=>return e};
    match r.stage(owner,entry,port,tx_seq,rx_seq,sack==1).and_then(|()|wake_both(&tx,&rx)){
        Ok(())=>OK,Err(e)=>e,
    }
}
#[no_mangle]
pub extern "C" fn wbd_m0_win_normal_candidate_ready(h:u64,port:u16)->i32{
    let Ok((r,_,_))=get(h)else{return -1};
    r.candidate_ready(port).map_or(-1,i32::from)
}
#[no_mangle]
pub extern "C" fn wbd_m0_win_normal_candidate_promote(h:u64,port:u16,grace_ms:u32)->i32{
    let (r,tx,rx)=match get(h){Ok(v)=>v,Err(e)=>return e};
    let id=match r.request_promote(port,grace_ms){Ok(v)=>v,Err(e)=>return e};
    if let Err(e)=wake_both(&tx,&rx){return e}
    let until=Instant::now()+Duration::from_secs(4);
    while r.last_promoted.load(Ordering::Acquire)!=id{
        if Instant::now()>=until{return STOP_INCOMPLETE}
        thread::sleep(Duration::from_millis(10));
    }
    OK
}
#[no_mangle]
pub extern "C" fn wbd_m0_win_normal_candidate_retired(h:u64,owner:u64)->i32{
    let Ok((r,_,_))=get(h)else{return -1};
    i32::from(owner!=0&&r.last_retired.load(Ordering::Acquire)==owner)
}
