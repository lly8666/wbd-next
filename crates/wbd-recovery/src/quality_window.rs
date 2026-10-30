//! PLAN027: direction-scoped mature quality summaries, not per-record receipts.
//! Pure low-frequency accounting. M0 must provide authenticated, replay-checked
//! reports and actual definitely-sent originals; missing reports mean UNKNOWN.
use wbd_types::{LaneKey,MonoNs,RecordPn};
use crate::budget::WireDirection;

pub const MAX_WINDOW_PNS:u64=1024;
pub const EXPIRE_NS:u64=10_000_000_000;
pub const WIRE_LEN:usize=36;

#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct WindowKey {
    pub lane:LaneKey,pub epoch:[u8;16],pub direction:WireDirection,
    pub id:u64,pub first:RecordPn,pub last:RecordPn,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct ClosedWindow {
    pub key:WindowKey,pub first_sent:u16,pub closed_at:MonoNs,
    pub complete:bool,pub capacity_limited:bool,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct MatureReport {
    pub key:WindowKey,pub received_unique:u16,pub possibly_repaired:u16,
    pub mature:bool,pub complete:bool,pub capacity_limited:bool,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub enum QualityError {
    WrongWindow,InvalidRange,InvalidCounts,Empty,Stale,ClockReversed,
    NotMature,Unknown,InvalidWire,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct LossBounds {pub first:u16,pub lower:u16,pub upper:u16}
impl LossBounds {
    pub fn lower_bps(self)->u32{u32::from(self.lower)*10_000/u32::from(self.first)}
    pub fn upper_bps(self)->u32{u32::from(self.upper)*10_000/u32::from(self.first)}
}
pub fn assess(sent:&ClosedWindow,report:&MatureReport,now:MonoNs)
    ->Result<LossBounds,QualityError>{
    if sent.key!=report.key{return Err(QualityError::WrongWindow);}
    let span=sent.key.last.0.checked_sub(sent.key.first.0)
        .and_then(|v|v.checked_add(1))
        .filter(|&n|n<=MAX_WINDOW_PNS).ok_or(QualityError::InvalidRange)?;
    if sent.first_sent==0{return Err(QualityError::Empty);}
    if u64::from(sent.first_sent)>span||report.received_unique>sent.first_sent
        ||report.possibly_repaired>sent.first_sent {
        return Err(QualityError::InvalidCounts);
    }
    if now.0<sent.closed_at.0{return Err(QualityError::ClockReversed);}
    if now.0-sent.closed_at.0>EXPIRE_NS{return Err(QualityError::Stale);}
    if !report.mature{return Err(QualityError::NotMature);}
    if !sent.complete||!report.complete||sent.capacity_limited
        ||report.capacity_limited{return Err(QualityError::Unknown);}
    let lower=sent.first_sent-report.received_unique;
    let upper=lower.saturating_add(report.possibly_repaired).min(sent.first_sent);
    Ok(LossBounds{first:sent.first_sent,lower,upper})
}

/// Compact 36-byte v2 Quality TLV body. Native AEAD/epoch/lane authentication
/// is mandatory and EXTERNAL; a decoded body is never independent authority.
/// Flags: mature, full coverage, receiver capacity, possible repair.
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct WireReport {
    pub id:u64,pub first:u64,pub last:u64,pub first_sent:u16,
    pub received_unique:u16,pub possibly_repaired:u16,
    pub mature:bool,pub complete:bool,pub capacity_limited:bool,
}
impl WireReport {
    fn valid(self)->Result<(),QualityError>{
        let span=self.last.checked_sub(self.first)
            .and_then(|v|v.checked_add(1))
            .filter(|&v|v<=MAX_WINDOW_PNS).ok_or(QualityError::InvalidRange)?;
        if u64::from(self.first_sent)>span||self.received_unique>self.first_sent
            ||self.possibly_repaired>self.first_sent {
            return Err(QualityError::InvalidCounts);
        }
        Ok(())
    }
    pub fn encode(self)->Result<[u8;WIRE_LEN],QualityError>{
        self.valid()?;
        let mut b=[0u8;WIRE_LEN];
        b[0]=2;
        b[1]=u8::from(self.mature)|u8::from(self.complete)<<1
            |u8::from(self.capacity_limited)<<2
            |u8::from(self.possibly_repaired!=0)<<3;
        b[2..10].copy_from_slice(&self.id.to_be_bytes());
        b[10..18].copy_from_slice(&self.first.to_be_bytes());
        b[18..26].copy_from_slice(&self.last.to_be_bytes());
        b[26..28].copy_from_slice(&self.first_sent.to_be_bytes());
        b[28..30].copy_from_slice(&self.received_unique.to_be_bytes());
        b[30..32].copy_from_slice(&self.possibly_repaired.to_be_bytes());
        Ok(b)
    }
    pub fn decode(b:&[u8])->Result<Self,QualityError>{
        if b.len()!=WIRE_LEN||b[0]!=2||b[1]&!15!=0||
            b[32..].iter().any(|&v|v!=0){return Err(QualityError::InvalidWire);}
        let u64at=|n:usize|{
            let mut a=[0u8;8];a.copy_from_slice(&b[n..n+8]);u64::from_be_bytes(a)
        };
        let u16at=|n:usize|{
            let mut a=[0u8;2];a.copy_from_slice(&b[n..n+2]);u16::from_be_bytes(a)
        };
        let out=Self{id:u64at(2),first:u64at(10),last:u64at(18),
            first_sent:u16at(26),received_unique:u16at(28),
            possibly_repaired:u16at(30),mature:b[1]&1!=0,
            complete:b[1]&2!=0,capacity_limited:b[1]&4!=0};
        if (b[1]&8!=0)!=(out.possibly_repaired!=0){
            return Err(QualityError::InvalidWire);
        }
        out.valid()?;
        Ok(out)
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    use wbd_types::TunnelKey;
    fn key()->WindowKey{WindowKey{
        lane:LaneKey{tunnel:TunnelKey{slot:2,generation:3},slot:4,generation:5},
        epoch:[7;16],direction:WireDirection::ServerToClient,
        id:9,first:RecordPn(100),last:RecordPn(109)}}
    fn pair()->(ClosedWindow,MatureReport){
        let key=key();(ClosedWindow{key,first_sent:10,closed_at:MonoNs(0),
            complete:true,capacity_limited:false},
            MatureReport{key,received_unique:9,possibly_repaired:1,mature:true,
                complete:true,capacity_limited:false})
    }
    #[test]
    fn r2_plan027_quality_mature_bounds_and_wire_roundtrip(){
        let (s,r)=pair();let b=assess(&s,&r,MonoNs(3_500_000_000)).unwrap();
        assert_eq!((b.lower,b.upper,b.lower_bps(),b.upper_bps()),
            (1,2,1000,2000));
        let w=WireReport{id:9,first:100,last:109,first_sent:10,
            received_unique:9,possibly_repaired:1,mature:true,complete:true,
            capacity_limited:false};
        assert_eq!(WireReport::decode(&w.encode().unwrap()),Ok(w));
    }
    #[test]
    fn r2_plan027_quality_unknown_never_zero_and_wrong_epoch_rejected(){
        let (s,r)=pair();let mut q=r;q.key.epoch[0]^=1;
        assert_eq!(assess(&s,&q,MonoNs(1)),Err(QualityError::WrongWindow));
        q=r;q.mature=false;
        assert_eq!(assess(&s,&q,MonoNs(1)),Err(QualityError::NotMature));
        q=r;q.complete=false;
        assert_eq!(assess(&s,&q,MonoNs(1)),Err(QualityError::Unknown));
        q=r;q.capacity_limited=true;
        assert_eq!(assess(&s,&q,MonoNs(1)),Err(QualityError::Unknown));
        assert_eq!(assess(&s,&r,MonoNs(EXPIRE_NS+1)),Err(QualityError::Stale));
        let mut t=s;t.first_sent=0;
        assert_eq!(assess(&t,&r,MonoNs(1)),Err(QualityError::Empty));
    }
    #[test]
    fn r2_plan027_quality_malformed_wire_and_range_fail_closed(){
        let (s,r)=pair();
        let w=WireReport{id:9,first:100,last:109,first_sent:10,
            received_unique:9,possibly_repaired:1,mature:true,complete:true,
            capacity_limited:false};
        let mut b=w.encode().unwrap();b[0]=3;
        assert_eq!(WireReport::decode(&b),Err(QualityError::InvalidWire));
        b=w.encode().unwrap();b[32]=1;
        assert_eq!(WireReport::decode(&b),Err(QualityError::InvalidWire));
        b=w.encode().unwrap();b[1]^=8;
        assert_eq!(WireReport::decode(&b),Err(QualityError::InvalidWire));
        assert_eq!(WireReport{last:1200,..w}.encode(),Err(QualityError::InvalidRange));
        assert_eq!(WireReport{received_unique:11,..w}.encode(),
            Err(QualityError::InvalidCounts));
        let t=ClosedWindow{closed_at:MonoNs(10),..s};
        assert_eq!(assess(&t,&r,MonoNs(9)),Err(QualityError::ClockReversed));
    }
}


/// PLAN027 3-second receiver maturity. Monotonic time belongs to the
/// receiving process; never compare this timestamp with the peer clock.
pub const RECEIVE_MATURE_NS:u64=3_000_000_000;
pub const MAX_RECEIVE_WINDOWS:usize=4;
pub const MAX_CLOSED_SEND_WINDOWS:usize=16;
const WINDOW_WORDS:usize=(MAX_WINDOW_PNS as usize)/64;

/// At most 1024 PN bits in an already-authenticated, scoped Auto window.
/// Updating a unique DATA reception is O(1) with no alloc/scan/FFI.
/// Never feed carrier ACKs, unauthenticated packets or control PNs here.
pub struct ReceiveCounter {
    key:WindowKey,
    opened_at:MonoNs,
    // Maturity starts only after a sender's authenticated window-close
    // announcement, never 3s after an arbitrarily slow first DATA.
    closed_at:Option<MonoNs>,
    sender_first_sent:Option<u16>,
    complete:bool,
    capacity_limited:bool,
    seen:[u64;WINDOW_WORDS],
    possibly_repaired:[u64;WINDOW_WORDS],
    unique:u16,
    repaired:u16,
}
impl ReceiveCounter {
    pub fn new(key:WindowKey,opened_at:MonoNs,
        complete_from_first_data:bool)->Result<Self,QualityError>{
        key.last.0.checked_sub(key.first.0)
            .and_then(|v|v.checked_add(1))
            .filter(|&v|v<=MAX_WINDOW_PNS)
            .ok_or(QualityError::InvalidRange)?;
        Ok(Self{key,opened_at,closed_at:None,sender_first_sent:None,
            complete:complete_from_first_data,
            capacity_limited:false,seen:[0;WINDOW_WORDS],
            possibly_repaired:[0;WINDOW_WORDS],unique:0,repaired:0})
    }
    pub fn key(&self)->WindowKey{self.key}
    /// The remote sender must explicitly close the advertised PN interval.
    /// A missing/late close remains UNKNOWN, not a fabricated loss sample.
    pub fn close(&mut self,now:MonoNs)->Result<(),QualityError>{
        if now.0<self.opened_at.0{return Err(QualityError::ClockReversed)}
        if self.closed_at.is_some(){return Err(QualityError::InvalidRange)}
        self.closed_at=Some(now);
        Ok(())
    }
    /// An authenticated CLOSE carries the sender's definite driver F and
    /// coverage status. Validate before closing; an absent CLOSE never
    /// produces a wire report, even if a local timer has expired.
    pub fn close_announced(&mut self,now:MonoNs,first_sent:u16,
        sender_complete:bool,sender_capacity_limited:bool
    )->Result<(),QualityError>{
        self.close_announced_prefix(self.key.last,now,first_sent,
            sender_complete,sender_capacity_limited)
    }
    /// Sparse windows may CLOSE below the START upper bound only when
    /// there are no verified DATA above the shorter last PN.
    pub fn close_announced_prefix(&mut self,last:RecordPn,now:MonoNs,
        first_sent:u16,sender_complete:bool,sender_capacity_limited:bool
    )->Result<(),QualityError>{
        if last.0<self.key.first.0||last.0>self.key.last.0{
            return Err(QualityError::InvalidRange)
        }
        let span=last.0-self.key.first.0+1;
        if u64::from(first_sent)>span||
            (sender_complete&&sender_capacity_limited){
            return Err(QualityError::InvalidCounts)
        }
        for bit in span as usize..(self.key.last.0-self.key.first.0+1) as usize{
            if self.seen[bit/64]&(1u64<<(bit%64))!=0{
                return Err(QualityError::InvalidCounts)
            }
        }
        self.close(now)?;
        self.key.last=last;
        self.sender_first_sent=Some(first_sent);
        self.complete&=sender_complete;
        self.capacity_limited|=sender_capacity_limited;
        Ok(())
    }
    /// Returns true only for the first authenticated unique DATA in range.
    /// Duplicates and out-of-window PNs cannot create false observations.
    pub fn on_unique_data(&mut self,pn:RecordPn,possibly_repaired:bool)->bool{
        if pn.0<self.key.first.0||pn.0>self.key.last.0{return false}
        let offset=(pn.0-self.key.first.0) as usize;
        let word=offset/64;
        let bit=1u64<<(offset%64);
        if self.seen[word]&bit!=0{return false}
        self.seen[word]|=bit;
        self.unique+=1; // bounded by exactly 1024 positions
        if possibly_repaired{
            self.possibly_repaired[word]|=bit;
            self.repaired+=1;
        }
        true
    }
    /// Local dropped metadata or missed start censors the entire interval;
    /// it must not be exported as a deceptively clean Auto sample.
    pub fn censor_capacity(&mut self){self.capacity_limited=true}
    pub fn mature_report(&self,now:MonoNs)->Result<MatureReport,QualityError>{
        if now.0<self.opened_at.0{return Err(QualityError::ClockReversed)}
        let Some(closed_at)=self.closed_at else{
            return Err(QualityError::NotMature)
        };
        if now.0<closed_at.0{return Err(QualityError::ClockReversed)}
        let elapsed=now.0-closed_at.0;
        if elapsed<RECEIVE_MATURE_NS{return Err(QualityError::NotMature)}
        if elapsed>EXPIRE_NS{return Err(QualityError::Stale)}
        Ok(MatureReport{key:self.key,received_unique:self.unique,
            possibly_repaired:self.repaired,mature:true,
            complete:self.complete,capacity_limited:self.capacity_limited})
    }
    /// Only a sender-announced CLOSE may supply F to a mature v2 summary.
    /// The caller still authenticates the resulting control and binds scope.
    pub fn mature_wire_report(&self,now:MonoNs)->Result<WireReport,QualityError>{
        let first_sent=self.sender_first_sent.ok_or(QualityError::Unknown)?;
        let report=self.mature_report(now)?;
        let wire=WireReport{id:self.key.id,first:self.key.first.0,
            last:self.key.last.0,first_sent,
            received_unique:report.received_unique,
            possibly_repaired:report.possibly_repaired,mature:report.mature,
            complete:report.complete,capacity_limited:report.capacity_limited};
        wire.valid()?;
        Ok(wire)
    }
}

/// One 4-slot RX ring per authenticated lane/epoch/direction, not a packet
/// history. Windows are nonoverlapping and armed before first DATA whenever
/// complete coverage is claimed. Eviction is a missing report (UNKNOWN).
pub struct ReceiveWindows {
    lane:LaneKey,
    epoch:[u8;16],
    direction:WireDirection,
    slots:[Option<ReceiveCounter>;MAX_RECEIVE_WINDOWS],
    next:usize,
    last_id:Option<u64>,
    last_pn:Option<u64>,
    // If authenticated DATA arrived before its START, later START cannot
    // retroactively claim full coverage. One monotone watermark, no bitmap.
    untracked_highest:Option<u64>,
}
impl ReceiveWindows {
    pub fn new(lane:LaneKey,epoch:[u8;16],direction:WireDirection)->Self{
        Self{lane,epoch,direction,
            slots:std::array::from_fn(|_|None),next:0,
            last_id:None,last_pn:None,untracked_highest:None}
    }
    pub fn arm(&mut self,key:WindowKey,now:MonoNs,
        complete_from_first_data:bool)->Result<(),QualityError>{
        if key.lane!=self.lane||key.epoch!=self.epoch||
            key.direction!=self.direction{return Err(QualityError::WrongWindow)}
        if self.last_id.is_some_and(|old|key.id<=old)||
            self.last_pn.is_some_and(|old|key.first.0<=old) {
            return Err(QualityError::InvalidRange)
        }
        let covered=complete_from_first_data &&
            !self.untracked_highest.is_some_and(|pn|pn>=key.first.0);
        let counter=ReceiveCounter::new(key,now,covered)?;
        self.slots[self.next]=Some(counter);
        self.next=(self.next+1)%MAX_RECEIVE_WINDOWS;
        self.last_id=Some(key.id);
        self.last_pn=Some(key.last.0);
        Ok(())
    }
    /// Only after native authentication/unique-PN and DATA classification.
    /// Scans at most four fixed slots, never historical DATA/Receipt pages.
    pub fn on_unique_data(&mut self,pn:RecordPn,repaired:bool)->bool{
        for entry in self.slots.iter_mut().flatten(){
            if entry.on_unique_data(pn,repaired){return true}
        }
        self.untracked_highest=Some(self.untracked_highest.map_or(pn.0,
            |prior|prior.max(pn.0)));
        false
    }
    pub fn close(&mut self,key:WindowKey,now:MonoNs)->Result<(),QualityError>{
        let Some(entry)=self.slots.iter_mut().flatten()
            .find(|entry|entry.key==key)else{return Err(QualityError::WrongWindow)};
        entry.close(now)
    }
    /// Apply only after an AEAD-opened, unique-PN CLOSE for this exact scope.
    pub fn close_announced(&mut self,key:WindowKey,now:MonoNs,
        first_sent:u16,sender_complete:bool,sender_capacity_limited:bool
    )->Result<(),QualityError>{
        if key.lane!=self.lane||key.epoch!=self.epoch||
            key.direction!=self.direction{return Err(QualityError::WrongWindow)}
        let Some(entry)=self.slots.iter_mut().flatten()
            .find(|entry|entry.key.id==key.id&&
                entry.key.first==key.first&&key.last.0<=entry.key.last.0)
            else{return Err(QualityError::WrongWindow)};
        entry.close_announced_prefix(key.last,now,first_sent,
            sender_complete,sender_capacity_limited)?;
        if self.last_id==Some(key.id){self.last_pn=Some(key.last.0)}
        Ok(())
    }
    pub fn censor_capacity(&mut self,key:WindowKey)->Result<(),QualityError>{
        let Some(entry)=self.slots.iter_mut().flatten()
            .find(|entry|entry.key==key)else{return Err(QualityError::WrongWindow)};
        entry.censor_capacity();
        Ok(())
    }
    pub fn report_wire(&self,key:WindowKey,now:MonoNs)
        ->Result<WireReport,QualityError>{
        let Some(entry)=self.slots.iter().flatten()
            .find(|entry|entry.key==key)else{return Err(QualityError::WrongWindow)};
        entry.mature_wire_report(now)
    }
    pub fn report(&self,key:WindowKey,now:MonoNs)
        ->Result<MatureReport,QualityError>{
        let Some(entry)=self.slots.iter().flatten()
            .find(|entry|entry.key==key)else{return Err(QualityError::WrongWindow)};
        entry.mature_report(now)
    }
}


/** Sender-side PLAN027 Auto sampling for a preannounced, nonoverlapping PN
 * interval. Start must be accepted by the driver BEFORE any DATA in range.
 * A local failed/uncertain first send or missing start censors the interval;
 * it must never be counted as WAN loss or silently become a zero-loss sample.
 * This is one fixed 128-byte bitmap, not a per-record receipt/heap queue.
 */
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub enum FirstSendStatus { Accepted, DefinitelyNotSent, Uncertain }

pub struct SendWindowSampler {
    key:WindowKey,
    opened_at:MonoNs,
    start_accepted:bool,
    first_data_seen:bool,
    censored:bool,
    closed:bool,
    seen:[u64;WINDOW_WORDS],
    first_sent:u16,
}
impl SendWindowSampler {
    pub fn new(key:WindowKey,now:MonoNs)->Result<Self,QualityError>{
        key.last.0.checked_sub(key.first.0)
            .and_then(|v|v.checked_add(1))
            .filter(|&n|n<=MAX_WINDOW_PNS)
            .ok_or(QualityError::InvalidRange)?;
        Ok(Self{key,opened_at:now,start_accepted:false,
            first_data_seen:false,censored:false,closed:false,
            seen:[0;WINDOW_WORDS],first_sent:0})
    }
    pub fn key(&self)->WindowKey{self.key}
    /// Nonempty sparse windows may close after two local seconds, provided
    /// the original native owner fenced all M4/NPF outcomes through last PN.
    pub fn timed_close_due(&self,now:MonoNs)->bool{
        self.start_accepted&&self.first_data_seen&&!self.closed&&
        now.0>=self.opened_at.0.saturating_add(2_000_000_000)
    }
    pub fn timed_close_deadline(&self)->Option<MonoNs>{
        (self.start_accepted&&self.first_data_seen&&!self.closed)
            .then_some(MonoNs(self.opened_at.0.saturating_add(2_000_000_000)))
    }
    /// Only a definite driver-accepted authenticated start qualifies. A
    /// delayed start cannot retroactively cover previously emitted DATA.
    pub fn on_start_send_result(&mut self,accepted:bool){
        if self.closed||self.first_data_seen||!accepted{
            self.censored=true;
        }else{
            self.start_accepted=true;
        }
    }
    /// Call once per original DATA's definite/uncertain driver completion.
    /// Repair copies, parity not in this window, and control PNs are excluded.
    /// False means duplicate, out of interval, or already closed.
    pub fn on_first_send(&mut self,pn:RecordPn,status:FirstSendStatus)->bool{
        if self.closed||pn.0<self.key.first.0||pn.0>self.key.last.0{
            return false
        }
        let offset=(pn.0-self.key.first.0) as usize;
        let word=offset/64;
        let bit=1u64<<(offset%64);
        if self.seen[word]&bit!=0{return false}
        self.seen[word]|=bit;
        self.first_data_seen=true;
        if !self.start_accepted{self.censored=true}
        match status{
            FirstSendStatus::Accepted=>self.first_sent+=1,
            FirstSendStatus::DefinitelyNotSent|FirstSendStatus::Uncertain=>{
                self.censored=true;
            }
        }
        true
    }
    pub fn censor_capacity(&mut self){self.censored=true}
    /// Closing is local; the receiver still needs an authenticated close
    /// control and its own 3s maturity. Neither clock crosses machines.
    pub fn close(&mut self,now:MonoNs)->Result<ClosedWindow,QualityError>{
        self.close_prefix(now,self.key.last)
    }
    pub fn close_prefix(&mut self,now:MonoNs,last:RecordPn)
        ->Result<ClosedWindow,QualityError>{
        if self.closed||now.0<self.opened_at.0||
            last.0<self.key.first.0||last.0>self.key.last.0{
            return Err(QualityError::InvalidRange)
        }
        let keep=(last.0-self.key.first.0+1) as usize;
        for bit in keep..(self.key.last.0-self.key.first.0+1) as usize{
            if self.seen[bit/64]&(1u64<<(bit%64))!=0{
                return Err(QualityError::InvalidRange)
            }
        }
        self.closed=true;
        Ok(ClosedWindow{key:WindowKey{last,..self.key},
            first_sent:self.first_sent,closed_at:now,
            complete:self.start_accepted&&!self.censored,
            capacity_limited:self.censored})
    }
}

/// Up to 16 completed, definitely-driver-confirmed first-send windows.
/// A small, report-cadence scan is allowed; never scan it for DATA admission.
/// A missing/evicted/stale report is UNKNOWN rather than zero loss.
pub struct SendHistory {
    lane:LaneKey,epoch:[u8;16],direction:WireDirection,
    slots:[Option<ClosedWindow>;MAX_CLOSED_SEND_WINDOWS],
    next:usize,last_id:Option<u64>,last_pn:Option<u64>,
}
impl SendHistory {
    pub fn new(lane:LaneKey,epoch:[u8;16],direction:WireDirection)->Self{
        Self{lane,epoch,direction,slots:[None;MAX_CLOSED_SEND_WINDOWS],
            next:0,last_id:None,last_pn:None}
    }
    pub fn close(&mut self,window:ClosedWindow)->Result<(),QualityError>{
        if window.key.lane!=self.lane||window.key.epoch!=self.epoch||
            window.key.direction!=self.direction{return Err(QualityError::WrongWindow)}
        if self.last_id.is_some_and(|old|window.key.id<=old)||
            self.last_pn.is_some_and(|old|window.key.first.0<=old) {
            return Err(QualityError::InvalidRange)
        }
        let span=window.key.last.0.checked_sub(window.key.first.0)
            .and_then(|v|v.checked_add(1))
            .filter(|&v|v<=MAX_WINDOW_PNS)
            .ok_or(QualityError::InvalidRange)?;
        if u64::from(window.first_sent)>span{
            return Err(QualityError::InvalidCounts)
        }
        self.slots[self.next]=Some(window);
        self.next=(self.next+1)%MAX_CLOSED_SEND_WINDOWS;
        self.last_id=Some(window.key.id);
        self.last_pn=Some(window.key.last.0);
        Ok(())
    }

    /// Convert an authenticated v2 summary ONLY after the caller has bound
    /// its AEAD-opened lane/epoch/direction to this history. Remote first F
    /// must match our definite driver count, never override local evidence.
    /// Sender-local age; never compare monotone timestamps across hosts.
    pub fn assess_wire_with_age(&self,wire:WireReport,now:MonoNs)
        ->Result<(LossBounds,u64),QualityError>{
        let bounds=self.assess_wire(wire,now)?;
        let sent=self.slots.iter().flatten()
            .find(|x|x.key.id==wire.id&&x.key.first.0==wire.first
                &&x.key.last.0==wire.last)
            .ok_or(QualityError::WrongWindow)?;
        Ok((bounds,now.0-sent.closed_at.0))
    }
    pub fn assess_wire(&self,wire:WireReport,now:MonoNs)
        ->Result<LossBounds,QualityError>{
        wire.valid()?;
        let Some(sent)=self.slots.iter().flatten().find(|sent|
            sent.key.id==wire.id&&sent.key.first.0==wire.first
                &&sent.key.last.0==wire.last)
            else{return Err(QualityError::WrongWindow)};
        if wire.first_sent!=sent.first_sent{return Err(QualityError::InvalidCounts)}
        assess(sent,&MatureReport{key:sent.key,
            received_unique:wire.received_unique,
            possibly_repaired:wire.possibly_repaired,
            mature:wire.mature,complete:wire.complete,
            capacity_limited:wire.capacity_limited},now)
    }
    pub fn assess_report(&self,report:&MatureReport,now:MonoNs)
        ->Result<LossBounds,QualityError>{
        let Some(sent)=self.slots.iter().flatten()
            .find(|sent|sent.key==report.key)else{return Err(QualityError::WrongWindow)};
        assess(sent,report,now)
    }
}

#[cfg(test)]
mod bounded_window_tests {
    use super::*;
    use wbd_types::TunnelKey;
    fn key(id:u64,first:u64)->WindowKey {
        WindowKey{lane:LaneKey{
            tunnel:TunnelKey{slot:2,generation:9},slot:1,generation:4},
            epoch:[9;16],direction:WireDirection::ClientToServer,
            id,first:RecordPn(first),last:RecordPn(first+1023)}
    }
    #[test]
    fn r2_plan027_sparse_prefix_close_rearms_without_pn_hole(){
        let first=key(1,50);
        let mut rx=ReceiveWindows::new(first.lane,first.epoch,first.direction);
        let mut tx=SendHistory::new(first.lane,first.epoch,first.direction);
        let mut sampler=SendWindowSampler::new(first,MonoNs(0)).unwrap();
        sampler.on_start_send_result(true);
        rx.arm(first,MonoNs(0),true).unwrap();
        for pn in 50..114{
            assert!(sampler.on_first_send(RecordPn(pn),FirstSendStatus::Accepted));
            assert!(rx.on_unique_data(RecordPn(pn),false));
        }
        assert!(!sampler.timed_close_due(MonoNs(1_999_999_999)));
        assert!(sampler.timed_close_due(MonoNs(2_000_000_000)));
        let closed=sampler.close_prefix(MonoNs(2_000_000_000),
            RecordPn(113)).unwrap();
        let key=closed.key;
        tx.close(closed).unwrap();
        rx.close_announced(key,MonoNs(2_000_000_001),
            64,true,false).unwrap();
        let report=rx.report_wire(key,MonoNs(5_000_000_001)).unwrap();
        assert_eq!(tx.assess_wire(report,MonoNs(5_000_000_001)).unwrap().lower,0);
        let next=WindowKey{id:2,first:RecordPn(114),
            last:RecordPn(1137),..first};
        rx.arm(next,MonoNs(5_000_000_002),true).unwrap();
        assert!(rx.on_unique_data(RecordPn(114),false));
        assert_eq!(rx.close_announced(first,MonoNs(5_000_000_003),
            64,true,false),Err(QualityError::WrongWindow));
    }
    #[test]
    fn r2_plan027_truncated_close_refuses_higher_verified_data(){
        let k=key(1,200);
        let mut rx=ReceiveWindows::new(k.lane,k.epoch,k.direction);
        rx.arm(k,MonoNs(0),true).unwrap();
        assert!(rx.on_unique_data(RecordPn(250),false));
        let short=WindowKey{last:RecordPn(205),..k};
        assert_eq!(rx.close_announced(short,MonoNs(1),4,true,false),
            Err(QualityError::InvalidCounts));
        assert_eq!(rx.report_wire(k,MonoNs(4_000_000_000)),
            Err(QualityError::NotMature));
        let next=WindowKey{id:2,first:RecordPn(206),
            last:RecordPn(1229),..k};
        assert_eq!(rx.arm(next,MonoNs(4_000_000_001),true),
            Err(QualityError::InvalidRange));
    }
    #[test]
    fn r2_plan027_receiver_1024_bits_matures_3s_no_duplicates(){
        let mut w=ReceiveWindows::new(key(1,0).lane,[9;16],
            WireDirection::ClientToServer);
        w.arm(key(1,0),MonoNs(0),true).unwrap();
        assert!(w.on_unique_data(RecordPn(0),false));
        assert!(!w.on_unique_data(RecordPn(0),true));
        assert!(w.on_unique_data(RecordPn(1023),true));
        assert!(!w.on_unique_data(RecordPn(1024),false));
        w.close(key(1,0),MonoNs(0)).unwrap();
        assert_eq!(w.report(key(1,0),MonoNs(2_999_999_999)),
            Err(QualityError::NotMature));
        let r=w.report(key(1,0),MonoNs(3_000_000_000)).unwrap();
        assert_eq!((r.received_unique,r.possibly_repaired),(2,1));
        let mut h=SendHistory::new(key(1,0).lane,[9;16],
            WireDirection::ClientToServer);
        h.close(ClosedWindow{key:key(1,0),first_sent:3,
            closed_at:MonoNs(1),complete:true,capacity_limited:false}).unwrap();
        let b=h.assess_report(&r,MonoNs(3_000_000_000)).unwrap();
        assert_eq!((b.lower,b.upper),(1,2));
        assert_eq!(w.report(key(1,0),MonoNs(EXPIRE_NS+1)),
            Err(QualityError::Stale));
    }
    #[test]
    fn r2_plan027_four_rx_sixteen_tx_windows_evict_to_unknown(){
        let k=key(1,0);
        let mut rx=ReceiveWindows::new(k.lane,k.epoch,k.direction);
        let mut tx=SendHistory::new(k.lane,k.epoch,k.direction);
        for n in 0..17u64{
            let wk=key(n+1,n*1024);
            rx.arm(wk,MonoNs(0),true).unwrap();
            rx.close(wk,MonoNs(0)).unwrap();
            tx.close(ClosedWindow{key:wk,first_sent:1024,
                closed_at:MonoNs(0),complete:true,capacity_limited:false}).unwrap();
            assert!(rx.on_unique_data(wk.first,false));
        }
        assert_eq!(rx.report(key(1,0),MonoNs(3_000_000_000)),
            Err(QualityError::WrongWindow));
        let latest=rx.report(key(17,16*1024),MonoNs(3_000_000_000)).unwrap();
        assert_eq!(tx.assess_report(&latest,MonoNs(3_000_000_000))
            .unwrap().lower,1023);
        assert_eq!(tx.assess_report(&MatureReport{key:k,..latest},
            MonoNs(3_000_000_000)),Err(QualityError::WrongWindow));
        assert_eq!(rx.arm(key(17,17*1024),MonoNs(0),true),
            Err(QualityError::InvalidRange));
        let mut wrong=key(18,17*1024);wrong.epoch=[8;16];
        assert_eq!(rx.arm(wrong,MonoNs(0),true),
            Err(QualityError::WrongWindow));
    }
    #[test]
    fn r2_plan027_receiver_requires_closed_window_for_maturity(){
        let k=key(1,500);
        let mut rx=ReceiveWindows::new(k.lane,k.epoch,k.direction);
        rx.arm(k,MonoNs(0),true).unwrap();
        assert!(rx.on_unique_data(RecordPn(500),false));
        // 9s since first DATA is not 3s since last possible first-send.
        assert_eq!(rx.report(k,MonoNs(9_000_000_000)),
            Err(QualityError::NotMature));
        assert_eq!(rx.close(k,MonoNs(0)),
            Ok(())); // explicit close at opening is valid
        assert_eq!(rx.close(k,MonoNs(9_000_000_000)),
            Err(QualityError::InvalidRange));
        assert_eq!(rx.report(k,MonoNs(2_999_999_999)),
            Err(QualityError::NotMature));
        let m=rx.report(k,MonoNs(3_000_000_000)).unwrap();
        assert_eq!(m.received_unique,1);
        let mut slow=ReceiveWindows::new(k.lane,k.epoch,k.direction);
        slow.arm(k,MonoNs(1_000_000_000),true).unwrap();
        assert_eq!(slow.close(k,MonoNs(999_999_999)),
            Err(QualityError::ClockReversed));
        slow.close(k,MonoNs(9_000_000_000)).unwrap();
        assert_eq!(slow.report(k,MonoNs(11_999_999_999)),
            Err(QualityError::NotMature));
        assert!(slow.report(k,MonoNs(12_000_000_000)).is_ok());
        assert_eq!(slow.report(k,MonoNs(19_000_000_001)),
            Err(QualityError::Stale));
    }
    #[test]
    fn r2_plan027_partial_or_capacity_window_never_claims_clean(){
        let k=key(1,100);
        let mut rx=ReceiveWindows::new(k.lane,k.epoch,k.direction);
        let mut tx=SendHistory::new(k.lane,k.epoch,k.direction);
        rx.arm(k,MonoNs(50),false).unwrap();
        rx.close(k,MonoNs(50)).unwrap();
        tx.close(ClosedWindow{key:k,first_sent:4,
            closed_at:MonoNs(50),complete:true,capacity_limited:false}).unwrap();
        rx.on_unique_data(RecordPn(100),false);
        let partial=rx.report(k,MonoNs(3_000_000_050)).unwrap();
        assert_eq!(tx.assess_report(&partial,MonoNs(3_000_000_050)),
            Err(QualityError::Unknown));
        rx.censor_capacity(k).unwrap();
        let censored=rx.report(k,MonoNs(3_000_000_050)).unwrap();
        assert!(censored.capacity_limited);
        assert_eq!(tx.assess_report(&censored,MonoNs(3_000_000_050)),
            Err(QualityError::Unknown));
    }
}

#[cfg(test)]
mod plan027_sender_tests {
    use super::*;
    use wbd_types::TunnelKey;
    fn key()->WindowKey{
        WindowKey{lane:LaneKey{tunnel:TunnelKey{slot:7,generation:9},
            slot:2,generation:4},epoch:[8;16],
            direction:WireDirection::ClientToServer,
            id:11,first:RecordPn(200),last:RecordPn(1223)}
    }
    #[test]
    fn r2_plan027_sender_start_before_data_and_actual_driver_f_only(){
        let k=key();
        let mut tx=SendWindowSampler::new(k,MonoNs(0)).unwrap();
        tx.on_start_send_result(true);
        assert!(tx.on_first_send(RecordPn(200),FirstSendStatus::Accepted));
        assert!(!tx.on_first_send(RecordPn(200),FirstSendStatus::Accepted));
        assert!(tx.on_first_send(RecordPn(1223),FirstSendStatus::Accepted));
        assert!(!tx.on_first_send(RecordPn(1224),FirstSendStatus::Accepted));
        let closed=tx.close(MonoNs(2_000_000_000)).unwrap();
        assert_eq!(closed.first_sent,2);
        assert!(closed.complete);
        assert_eq!(tx.close(MonoNs(3_000_000_000)),Err(QualityError::InvalidRange));
        let mut hist=SendHistory::new(k.lane,k.epoch,k.direction);
        hist.close(closed).unwrap();
        let good=WireReport{id:11,first:200,last:1223,first_sent:2,
            received_unique:1,possibly_repaired:1,mature:true,
            complete:true,capacity_limited:false};
        assert_eq!(hist.assess_wire(good,MonoNs(4_000_000_000)),
            Ok(LossBounds{first:2,lower:1,upper:2}));
        assert_eq!(hist.assess_wire(WireReport{first_sent:1,..good},
            MonoNs(4_000_000_000)),Err(QualityError::InvalidCounts));
        assert_eq!(hist.assess_wire(WireReport{id:12,..good},
            MonoNs(4_000_000_000)),Err(QualityError::WrongWindow));
    }
    #[test]
    fn r2_plan027_sender_late_start_local_failure_uncertain_never_wan_loss(){
        let k=key();
        let mut late=SendWindowSampler::new(k,MonoNs(10)).unwrap();
        assert!(late.on_first_send(RecordPn(200),FirstSendStatus::Accepted));
        late.on_start_send_result(true);
        let closed=late.close(MonoNs(20)).unwrap();
        assert_eq!(closed.first_sent,1);
        assert!(!closed.complete);
        let mut hist=SendHistory::new(k.lane,k.epoch,k.direction);
        hist.close(closed).unwrap();
        let report=WireReport{id:11,first:200,last:1223,first_sent:1,
            received_unique:1,possibly_repaired:0,mature:true,
            complete:true,capacity_limited:false};
        assert_eq!(hist.assess_wire(report,MonoNs(21)),Err(QualityError::Unknown));
        let mut local=SendWindowSampler::new(k,MonoNs(10)).unwrap();
        local.on_start_send_result(true);
        assert!(local.on_first_send(RecordPn(200),
            FirstSendStatus::DefinitelyNotSent));
        assert!(local.on_first_send(RecordPn(201),
            FirstSendStatus::Uncertain));
        assert!(local.on_first_send(RecordPn(202),FirstSendStatus::Accepted));
        let closed=local.close(MonoNs(20)).unwrap();
        assert_eq!(closed.first_sent,1);
        assert!(!closed.complete);
        assert!(closed.capacity_limited);
        assert_eq!(SendWindowSampler::new(WindowKey{last:RecordPn(1224),..k},
            MonoNs(0)).err(),Some(QualityError::InvalidRange));
    }
}


#[cfg(test)]
mod plan027_announced_close_tests {
    use super::*;
    use wbd_types::TunnelKey;
    fn key()->WindowKey {
        WindowKey{lane:LaneKey{tunnel:TunnelKey{slot:7,generation:3},
            slot:2,generation:5},epoch:[4;16],
            direction:WireDirection::ClientToServer,
            id:11,first:RecordPn(200),last:RecordPn(1223)}
    }
    #[test]
    fn r2_plan027_closed_receiver_exports_only_sender_matched_mature_wire(){
        let k=key();
        let mut rx=ReceiveWindows::new(k.lane,k.epoch,k.direction);
        rx.arm(k,MonoNs(0),true).unwrap();
        assert!(rx.on_unique_data(RecordPn(200),false));
        assert!(rx.on_unique_data(RecordPn(202),true));
        assert_eq!(rx.report_wire(k,MonoNs(9_000_000_000)),
            Err(QualityError::Unknown));
        rx.close_announced(k,MonoNs(1_000_000_000),3,true,false).unwrap();
        assert_eq!(rx.report_wire(k,MonoNs(3_999_999_999)),
            Err(QualityError::NotMature));
        let wire=rx.report_wire(k,MonoNs(4_000_000_000)).unwrap();
        assert_eq!((wire.first_sent,wire.received_unique,wire.possibly_repaired),
            (3,2,1));
        assert!(wire.complete);
        assert_eq!(WireReport::decode(&wire.encode().unwrap()),Ok(wire));
        let mut tx=SendHistory::new(k.lane,k.epoch,k.direction);
        tx.close(ClosedWindow{key:k,first_sent:3,
            closed_at:MonoNs(1_000_000_000),
            complete:true,capacity_limited:false}).unwrap();
        assert_eq!(tx.assess_wire(wire,MonoNs(4_000_000_000)),
            Ok(LossBounds{first:3,lower:1,upper:2}));
        assert_eq!(rx.report_wire(k,MonoNs(11_000_000_001)),
            Err(QualityError::Stale));
    }
    #[test]
    fn r2_plan027_prestart_data_and_sender_censor_cannot_be_clean(){
        let k=key();
        let mut rx=ReceiveWindows::new(k.lane,k.epoch,k.direction);
        assert!(!rx.on_unique_data(RecordPn(201),false));
        rx.arm(k,MonoNs(1),true).unwrap();
        assert!(rx.on_unique_data(RecordPn(200),false));
        rx.close_announced(k,MonoNs(2),2,true,false).unwrap();
        let wire=rx.report_wire(k,MonoNs(3_000_000_002)).unwrap();
        assert!(!wire.complete);
        let mut tx=SendHistory::new(k.lane,k.epoch,k.direction);
        tx.close(ClosedWindow{key:k,first_sent:2,closed_at:MonoNs(2),
            complete:true,capacity_limited:false}).unwrap();
        assert_eq!(tx.assess_wire(wire,MonoNs(3_000_000_002)),
            Err(QualityError::Unknown));
        let next=WindowKey{id:12,first:RecordPn(1224),
            last:RecordPn(2247),..k};
        rx.arm(next,MonoNs(4),true).unwrap();
        rx.close_announced(next,MonoNs(5),1,false,true).unwrap();
        let censored=rx.report_wire(next,MonoNs(3_000_000_005)).unwrap();
        assert!(!censored.complete&&censored.capacity_limited);
    }
    #[test]
    fn r2_plan027_bad_close_does_not_advance_receiver_maturity(){
        let k=key();
        let mut rx=ReceiveWindows::new(k.lane,k.epoch,k.direction);
        rx.arm(k,MonoNs(0),true).unwrap();
        assert_eq!(rx.close_announced(k,MonoNs(1),1025,true,false),
            Err(QualityError::InvalidCounts));
        assert_eq!(rx.close_announced(k,MonoNs(1),1,true,true),
            Err(QualityError::InvalidCounts));
        assert_eq!(rx.report_wire(k,MonoNs(9_000_000_000)),
            Err(QualityError::Unknown));
        rx.close_announced(k,MonoNs(9_000_000_000),1,true,false).unwrap();
        assert_eq!(rx.report_wire(k,MonoNs(11_999_999_999)),
            Err(QualityError::NotMature));
    }
}
