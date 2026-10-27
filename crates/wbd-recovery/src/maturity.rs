//! PLAN-008 M2: *observation*, not RACK, loss repair or a second controller.
//! The sole sender owner emits one FINAL first-send kernel outcome per DATA PN.
//! M0 supplies only reverse-control facts AFTER real AEAD/open and replay
//! validation. Never infer sent count from RX, kernel Accepted != peer receipt.
//! Mature event-time windows are 2s and 8s. Unknown is not zero loss.
use std::collections::{BTreeMap,VecDeque};
use wbd_types::{LaneKey,MonoNs,RecordPn};
use crate::receipt::{ReceiptRouteScope,ScopedAuthenticatedReceipt};
const SHORT_NS:u64=2_000_000_000;
const LONG_NS:u64=8_000_000_000;
const MAX_DUE_PER_POLL:usize=64;

#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub enum FirstSendKind { Data, Control }
/// FINAL platform outcome for one originally sealed PN. An Uncertain
/// original cannot later become a second fresh DATA sample by retrying it.
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub enum FirstSendOutcome {
    Accepted { pn:RecordPn, wire_bytes:u64 },
    DefinitelyNotSent { pn:RecordPn },
    Uncertain { pn:RecordPn, wire_bytes:u64 },
}
impl FirstSendOutcome {
    fn pn(self)->RecordPn {
        match self {Self::Accepted{pn,..}|Self::DefinitelyNotSent{pn}|
            Self::Uncertain{pn,..}=>pn}
    }
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub enum MaturityError { InvalidConfig,WrongScope,ClockReversed,DuplicateOrOld,Stopped,
    CapacityLimited,ClockOverflow,InvalidWireBytes }
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct MaturityConfig { pub max_live_data:usize }

#[derive(Clone,Copy,Debug,Default,Eq,PartialEq)]
pub struct MatureWindow {
    /// Source denominator: positive local kernel FIRST-send completions only.
    pub first_sent:u64,
    pub first_sent_wire_bytes:u64,
    /// Positive authentic DATA receipt before the deadline and no prior
    /// possible repair/FEC recovery; only this is unambiguous first delivery.
    pub unambiguous_positive:u64,
    pub positive_wire_bytes:u64,
    /// Explicitly covered bitmap zero, no positive within deadline.
    pub covered_missing:u64,
    pub missing_wire_bytes:u64,
    /// Authenticated positive with a prior possible repair/recovery; do not
    /// count as first-send success or invent loss.
    pub repaired_or_ambiguous:u64,
    pub ambiguous_wire_bytes:u64,
    /// No authentic bitmap coverage by the maturity deadline: UNKNOWN.
    pub uncovered:u64,
    pub uncovered_wire_bytes:u64,
    /// Authenticated positive first-copy confirmation latency. Includes
    /// feedback schedule; not a fabricated repair-shadow RTT sample.
    pub positive_confirmation_lag_ns:u64,
    pub positive_confirmation_samples:u64,
}
impl MatureWindow {
    /// Must hold for both packet counts and wire bytes; if coverage is
    /// insufficient, M0 cannot manufacture a line-loss percentage.
    pub fn conserved(&self)->bool {
        self.first_sent==self.unambiguous_positive.saturating_add(
            self.covered_missing).saturating_add(self.repaired_or_ambiguous)
            .saturating_add(self.uncovered) &&
        self.first_sent_wire_bytes==self.positive_wire_bytes.saturating_add(
            self.missing_wire_bytes).saturating_add(self.ambiguous_wire_bytes)
            .saturating_add(self.uncovered_wire_bytes)
    }
    pub fn covered(&self)->u64 {
        self.unambiguous_positive.saturating_add(self.covered_missing)
            .saturating_add(self.repaired_or_ambiguous)
    }
    fn add(&mut self,e:&Entry,deadline:u64) {
        self.first_sent=self.first_sent.saturating_add(1);
        self.first_sent_wire_bytes=self.first_sent_wire_bytes.saturating_add(e.wire_bytes);
        let received=e.positive_at.is_some_and(|t|t<=deadline);
        let missing=e.negative_at.is_some_and(|t|t<=deadline);
        let ambiguous=e.possible_recovery_at.is_some_and(|t|
            received && t<=e.positive_at.unwrap_or(u64::MAX));
        if received && ambiguous {
            self.repaired_or_ambiguous=self.repaired_or_ambiguous.saturating_add(1);
            self.ambiguous_wire_bytes=self.ambiguous_wire_bytes.saturating_add(e.wire_bytes);
        } else if received {
            self.unambiguous_positive=self.unambiguous_positive.saturating_add(1);
            self.positive_wire_bytes=self.positive_wire_bytes.saturating_add(e.wire_bytes);
            if let Some(at)=e.positive_at {
                self.positive_confirmation_lag_ns=self.positive_confirmation_lag_ns
                    .saturating_add(at.saturating_sub(e.first_at));
                self.positive_confirmation_samples=self.positive_confirmation_samples
                    .saturating_add(1);
            }
        } else if missing {
            self.covered_missing=self.covered_missing.saturating_add(1);
            self.missing_wire_bytes=self.missing_wire_bytes.saturating_add(e.wire_bytes);
        } else {
            self.uncovered=self.uncovered.saturating_add(1);
            self.uncovered_wire_bytes=self.uncovered_wire_bytes.saturating_add(e.wire_bytes);
        }
    }
}
#[derive(Clone,Copy,Debug,Default,Eq,PartialEq)]
pub struct ObservationCounters {
    pub definitely_not_sent:u64,
    pub uncertain_originals:u64,
    pub uncertain_wire_bytes:u64,
    pub excluded_control:u64,
    /// Accepted DATA could not be tracked; controller MUST treat interval
    /// as capacity-limited, never valid "no loss" evidence.
    pub capacity_censored:u64,
    pub capacity_censored_bytes:u64,
}
#[derive(Clone,Copy,Debug,Default,Eq,PartialEq)]
pub struct MaturityPoll {
    pub window_2s:MatureWindow,
    pub window_8s:MatureWindow,
    pub processed:usize,
    pub next_deadline:Option<MonoNs>,
    pub capacity_limited:bool,
}
#[derive(Clone,Copy,Debug,Default,Eq,PartialEq)]
pub struct MaturityStop {
    pub censored_live:u64,
    pub censored_wire_bytes:u64,
    pub had_capacity_limit:bool,
}
#[derive(Clone,Debug)]
struct Entry {
    first_at:u64,wire_bytes:u64,
    positive_at:Option<u64>,negative_at:Option<u64>,
    possible_recovery_at:Option<u64>,short_done:bool
}
pub struct MatureFirstSend {
    route:ReceiptRouteScope,
    cfg:MaturityConfig,
    entries:BTreeMap<RecordPn,Entry>,
    // Monotonic first-send time guarantees sorted expiry timestamps.
    // FIFO indexes avoid per-packet BTreeSet insertion/allocation cost.
    short:VecDeque<(u64,RecordPn)>,
    long:VecDeque<(u64,RecordPn)>,
    clock:u64,
    retired_high:Option<RecordPn>,
    report_seq:Option<u32>,
    counters:ObservationCounters,
    stopped:bool,
}
impl MatureFirstSend {
    pub fn new(route:ReceiptRouteScope,cfg:MaturityConfig,start:MonoNs)
        ->Result<Self,MaturityError>{
        if cfg.max_live_data==0||cfg.max_live_data>524_288{
            return Err(MaturityError::InvalidConfig);
        }
        Ok(Self{route,cfg,entries:BTreeMap::new(),short:VecDeque::new(),
            long:VecDeque::new(),clock:start.0,retired_high:None,
            report_seq:None,counters:ObservationCounters::default(),stopped:false})
    }
    fn check_clock(&mut self,now:MonoNs)->Result<(),MaturityError>{
        if self.stopped{return Err(MaturityError::Stopped);}
        if now.0<self.clock{return Err(MaturityError::ClockReversed);}
        self.clock=now.0;
        Ok(())
    }
    pub fn counters(&self)->ObservationCounters{self.counters}
    pub fn live_records(&self)->usize{self.entries.len()}
    /// Real live metadata cap, not a preallocated payload cache.
    pub fn max_live_data(&self)->usize{self.cfg.max_live_data}
    pub fn timer_nodes(&self)->usize{self.short.len()+self.long.len()}
    pub fn next_deadline(&self)->Option<MonoNs>{
        [self.short.front().map(|&(t,_)|t),self.long.front().map(|&(t,_)|t)]
            .into_iter().flatten().min().map(MonoNs)
    }
    /// Never called for repair/fec copy, and only after local kernel has
    /// resolved the first attempt's FINAL status. Unknown/not-sent excluded
    /// from the actual accepted denominator, retained in counters only.
    pub fn on_first_send(&mut self,lane:LaneKey,kind:FirstSendKind,
        outcome:FirstSendOutcome,now:MonoNs)->Result<(),MaturityError>{
        self.check_clock(now)?;
        if lane!=self.route.outbound_lane(){return Err(MaturityError::WrongScope);}
        if kind==FirstSendKind::Control {
            self.counters.excluded_control=self.counters.excluded_control.saturating_add(1);
            return Ok(());
        }
        let pn=outcome.pn();
        if !self.route.contains_data_pn(pn) {return Err(MaturityError::WrongScope);}
        if self.entries.contains_key(&pn)||
            self.retired_high.is_some_and(|floor|pn<=floor) {
            return Err(MaturityError::DuplicateOrOld);
        }
        match outcome {
            FirstSendOutcome::DefinitelyNotSent{..}=>{
                self.counters.definitely_not_sent=self.counters.definitely_not_sent.saturating_add(1);
                Ok(())
            }
            FirstSendOutcome::Uncertain{wire_bytes,..}=>{
                if wire_bytes==0{return Err(MaturityError::InvalidWireBytes);}
                self.counters.uncertain_originals=self.counters.uncertain_originals.saturating_add(1);
                self.counters.uncertain_wire_bytes=self.counters.uncertain_wire_bytes.saturating_add(wire_bytes);
                Ok(())
            }
            FirstSendOutcome::Accepted{wire_bytes,..}=>{
                if wire_bytes==0{return Err(MaturityError::InvalidWireBytes);}
                let end2=now.0.checked_add(SHORT_NS).ok_or(MaturityError::ClockOverflow)?;
                let end8=now.0.checked_add(LONG_NS).ok_or(MaturityError::ClockOverflow)?;
                if self.entries.len()==self.cfg.max_live_data {
                    self.counters.capacity_censored=self.counters.capacity_censored.saturating_add(1);
                    self.counters.capacity_censored_bytes=self.counters.capacity_censored_bytes.saturating_add(wire_bytes);
                    return Err(MaturityError::CapacityLimited);
                }
                self.entries.insert(pn,Entry{
                    first_at:now.0,wire_bytes,positive_at:None,negative_at:None,
                    possible_recovery_at:None,short_done:false
                });
                self.short.push_back((end2,pn));
                self.long.push_back((end8,pn));
                Ok(())
            }
        }
    }
    /// Accepted/Uncertain original-cipher repair or recovered FEC source
    /// makes positive receipt attribution ambiguous. DefinitelyNotSent
    /// repair is NOT a possible delivered copy.
    pub fn on_possible_recovery(&mut self,lane:LaneKey,pn:RecordPn,
        result:crate::RepairSendResult,now:MonoNs)->Result<(),MaturityError>{
        self.check_clock(now)?;
        if lane!=self.route.outbound_lane(){return Err(MaturityError::WrongScope);}
        if result!=crate::RepairSendResult::NotSent {
            if let Some(e)=self.entries.get_mut(&pn){
                e.possible_recovery_at.get_or_insert(now.0);
            }
        }
        Ok(())
    }
    /// Only post-AEAD/replay checked reverse-control observations, constructed
    /// by M0 through ScopedAuthenticatedReceipt::checked_after_open. A bitmap
    /// zero counts only if that page is actually present and report_seq is new.
    /// Positives from stale reports remain valid witness; no RX count is
    /// permitted to create or enlarge the first-send denominator.
    pub fn on_authenticated_receipt(&mut self,scoped:&ScopedAuthenticatedReceipt,
        now:MonoNs)->Result<(),MaturityError>{
        self.check_clock(now)?;
        if scoped.route()!=self.route{return Err(MaturityError::WrongScope);}
        let r=scoped.receipt();
        let fresh=self.report_seq.is_none_or(|old|
            {let d=r.report_seq().wrapping_sub(old);d!=0&&d<0x8000_0000});
        if fresh{self.report_seq=Some(r.report_seq());}
        for page in r.pages(){
            let base=page.base_pn.0;
            let end=base.saturating_add(255).min(r.largest_data_pn().0);
            if base>end {continue;}
            for (&pn,e) in self.entries.range_mut(RecordPn(base)..=RecordPn(end)){
                let offset=pn.0-base;
                let positive=(page.bitmap[(offset/8) as usize]&(1u8<<(offset%8)))!=0;
                if positive {e.positive_at.get_or_insert(now.0);}
                else if fresh {e.negative_at.get_or_insert(now.0);}
            }
        }
        Ok(())
    }
    /// Bounded deadline indexing, not a per-packet Go callback. Events can
    /// arrive and on_due can be called late: classify against each original
    /// event-time deadline, never retroactively use an 8s ACK for the 2s bin.
    pub fn on_due(&mut self,now:MonoNs)->Result<MaturityPoll,MaturityError>{
        self.check_clock(now)?;
        let mut out=MaturityPoll{capacity_limited:self.counters.capacity_censored!=0,..MaturityPoll::default()};
        for _ in 0..MAX_DUE_PER_POLL{
            let a=self.short.front().copied().map(|(t,pn)|(t,pn,true));
            let b=self.long.front().copied().map(|(t,pn)|(t,pn,false));
            let Some((due,pn,is_short))=[a,b].into_iter().flatten()
                .min_by_key(|&(t,p,short)|(t,p,!short)) else {break;};
            if due>now.0{break;}
            if is_short {
                assert_eq!(self.short.pop_front(),Some((due,pn)));
                let e=self.entries.get_mut(&pn).expect("short index owner");
                debug_assert!(!e.short_done);
                e.short_done=true;
                out.window_2s.add(e,due);
            }else {
                assert_eq!(self.long.pop_front(),Some((due,pn)));
                let e=self.entries.remove(&pn).expect("long index owner");
                // on_due must not erase an entry whose 2s window remains.
                debug_assert!(e.short_done);
                out.window_8s.add(&e,due);
                if self.retired_high.is_none_or(|old|pn>old){
                    self.retired_high=Some(pn);
                }
            }
            out.processed+=1;
        }
        out.next_deadline=self.next_deadline();
        Ok(out)
    }
    /// Stop discards still-unmatured observations as CENSORED, not samples
    /// with zero missing. No late receipt/old epoch can reactivate this state.
    pub fn stop(&mut self,now:MonoNs)->Result<MaturityStop,MaturityError>{
        self.check_clock(now)?;
        let out=MaturityStop{
            censored_live:self.entries.len() as u64,
            censored_wire_bytes:self.entries.values().fold(0u64,|n,e|n.saturating_add(e.wire_bytes)),
            had_capacity_limit:self.counters.capacity_censored!=0,
        };
        self.entries.clear();self.short.clear();self.long.clear();
        self.stopped=true;
        Ok(out)
    }
}


#[cfg(test)]
mod tests {
    use super::*;
    use wbd_types::TunnelKey;
    use crate::receipt::{ReceiptOpenFacts,ReceiptPage,ScopedAuthenticatedReceipt};
    use crate::{WireDirection,RepairSendResult};

    fn lane()->LaneKey{
        LaneKey{tunnel:TunnelKey{slot:7,generation:11},slot:3,generation:2}
    }
    fn pinned()->ReceiptRouteScope{
        ReceiptRouteScope::checked(
            lane(),LaneKey{slot:4,..lane()},WireDirection::ClientToServer,[3;16],
            (RecordPn(0),RecordPn(100_000)),(RecordPn(200_000),RecordPn(200_100))
        ).unwrap()
    }
    fn open(scope:ReceiptRouteScope, seq:u32, largest:u64,
        pages:Vec<ReceiptPage>)->ScopedAuthenticatedReceipt {
        ScopedAuthenticatedReceipt::checked_after_open(scope,ReceiptOpenFacts{
            verified_reverse_lane:LaneKey{slot:4,..scope.outbound_lane()},
            verified_reverse_direction:WireDirection::ServerToClient,
            verified_tunnel_epoch:[3;16],control_record_pn:RecordPn(200_000),
        },RecordPn(largest),seq,pages).unwrap()
    }
    fn state(cap:usize)->MatureFirstSend{
        MatureFirstSend::new(pinned(),MaturityConfig{max_live_data:cap},MonoNs(0)).unwrap()
    }
    fn accepted(s:&mut MatureFirstSend,pn:u64,wire_bytes:u64,at:u64){
        s.on_first_send(lane(),FirstSendKind::Data,
            FirstSendOutcome::Accepted{pn:RecordPn(pn),wire_bytes},MonoNs(at)).unwrap();
    }
    fn page(base:u64,positives:&[u64])->ReceiptPage{
        let mut bitmap=[0;32];
        for &pn in positives {
            let n=(pn-base) as usize;
            bitmap[n/8]|=1u8<<(n%8);
        }
        ReceiptPage{base_pn:RecordPn(base),bitmap}
    }

    #[test]
    fn r2_plan008_maturity_2s_8s_event_time_holes_and_late_covered_receipts(){
        let mut s=state(6);
        for pn in [1,2,3,4,260] {accepted(&mut s,pn,100,0);}
        s.on_authenticated_receipt(&open(pinned(),1,260,vec![page(0,&[1])]),
            MonoNs(1_000_000_000)).unwrap();
        // Poll is intentionally late: the 3s positives must not rewrite 2s.
        s.on_authenticated_receipt(&open(pinned(),2,260,
            vec![page(0,&[1,2]),page(256,&[260])]),MonoNs(3_000_000_000)).unwrap();
        let mut a=MatureWindow::default();
        let mut b=MatureWindow::default();
        while s.next_deadline().is_some() {
            let r=s.on_due(MonoNs(8_000_000_000)).unwrap();
            assert!(r.processed<=64 && r.processed>0);
            accumulate(&mut a,r.window_2s);
            accumulate(&mut b,r.window_8s);
        }
        assert_eq!(a.first_sent,5);
        assert_eq!(a.unambiguous_positive,1);
        assert_eq!(a.covered_missing,3);
        assert_eq!(a.uncovered,1);
        assert_eq!(a.first_sent_wire_bytes,500);
        assert!(a.conserved());
        assert_eq!(b.unambiguous_positive,3);
        assert_eq!(b.covered_missing,2);
        assert_eq!(b.uncovered,0);
        assert!(b.conserved());
        assert_eq!(s.live_records(),0);
    }

    #[test]
    fn r2_plan008_missing_whole_block_lost_feedback_and_old_report_positive(){
        let mut s=state(5);
        for pn in 256..261 {accepted(&mut s,pn,120,0);}
        // Entire 5-record block is unobserved at 2s: UNKNOWN, not 5 losses.
        let p=s.on_due(MonoNs(2_000_000_000)).unwrap();
        assert_eq!(p.window_2s.uncovered,5);
        assert_eq!(p.window_2s.covered_missing,0);
        assert!(p.window_2s.conserved());
        s.on_authenticated_receipt(&open(pinned(),10,260,vec![page(256,&[256])]),
            MonoNs(3_000_000_000)).unwrap();
        // Older seq's positive bit is still usable; its zeros CANNOT mark 259.
        s.on_authenticated_receipt(&open(pinned(),9,260,vec![page(256,&[258])]),
            MonoNs(4_000_000_000)).unwrap();
        let old_duplicate=open(pinned(),9,260,vec![page(256,&[258])]);
        s.on_authenticated_receipt(&old_duplicate,MonoNs(4_000_000_000)).unwrap();
        // New report covering PN259 is absent, but earlier fresh seq10 did
        // cover it as zero; all other zero bits are explicit only for seq10.
        let q=s.on_due(MonoNs(8_000_000_000)).unwrap();
        assert_eq!(q.window_8s.first_sent,5);
        assert_eq!(q.window_8s.unambiguous_positive,2);
        assert_eq!(q.window_8s.covered_missing,3);
        assert!(q.window_8s.conserved());
        assert_eq!(s.live_records(),0);
    }

    #[test]
    fn r2_plan008_accepted_only_denominator_unknown_unsent_control_and_capacity(){
        let mut s=state(1);
        accepted(&mut s,1,100,0);
        s.on_first_send(lane(),FirstSendKind::Data,
            FirstSendOutcome::Uncertain{pn:RecordPn(2),wire_bytes:200},
            MonoNs(0)).unwrap();
        s.on_first_send(lane(),FirstSendKind::Data,
            FirstSendOutcome::DefinitelyNotSent{pn:RecordPn(3)},
            MonoNs(0)).unwrap();
        s.on_first_send(lane(),FirstSendKind::Control,
            FirstSendOutcome::Accepted{pn:RecordPn(200_000),wire_bytes:40},
            MonoNs(0)).unwrap();
        assert_eq!(s.on_first_send(lane(),FirstSendKind::Data,
            FirstSendOutcome::Accepted{pn:RecordPn(4),wire_bytes:400},MonoNs(0)),
            Err(MaturityError::CapacityLimited));
        let counts=s.counters();
        assert_eq!(counts.uncertain_originals,1);
        assert_eq!(counts.uncertain_wire_bytes,200);
        assert_eq!(counts.definitely_not_sent,1);
        assert_eq!(counts.excluded_control,1);
        assert_eq!(counts.capacity_censored,1);
        assert_eq!(counts.capacity_censored_bytes,400);
        let a=s.on_due(MonoNs(2_000_000_000)).unwrap();
        assert!(a.capacity_limited);
        assert_eq!(a.window_2s.first_sent,1);
        assert_eq!(a.window_2s.first_sent_wire_bytes,100);
        assert_eq!(a.window_2s.uncovered,1);
        assert!(a.window_2s.conserved());
        let b=s.on_due(MonoNs(8_000_000_000)).unwrap();
        assert_eq!(b.window_8s.uncovered,1);
        assert_eq!(s.live_records(),0);
        assert_eq!(s.timer_nodes(),0);
    }

    #[test]
    fn r2_plan008_repaired_positive_is_ambiguous_notsent_never_taints(){
        let mut s=state(3);
        for pn in 1..4 {accepted(&mut s,pn,100,0);}
        s.on_possible_recovery(lane(),RecordPn(1),RepairSendResult::Accepted,
            MonoNs(500_000_000)).unwrap();
        s.on_possible_recovery(lane(),RecordPn(2),RepairSendResult::NotSent,
            MonoNs(500_000_000)).unwrap();
        s.on_possible_recovery(lane(),RecordPn(3),RepairSendResult::Uncertain,
            MonoNs(500_000_000)).unwrap();
        s.on_authenticated_receipt(&open(pinned(),1,3,vec![page(0,&[1,2,3])]),
            MonoNs(1_000_000_000)).unwrap();
        let a=s.on_due(MonoNs(2_000_000_000)).unwrap();
        assert_eq!(a.window_2s.first_sent,3);
        assert_eq!(a.window_2s.unambiguous_positive,1);
        assert_eq!(a.window_2s.repaired_or_ambiguous,2);
        assert_eq!(a.window_2s.positive_wire_bytes,100);
        assert_eq!(a.window_2s.ambiguous_wire_bytes,200);
        // Exactly one unambiguous verified first-copy positive; previous
        // possible FEC/repair receipt is not a valid RTT/quality sample.
        assert_eq!(a.window_2s.positive_confirmation_samples,1);
        assert_eq!(a.window_2s.positive_confirmation_lag_ns,1_000_000_000);
        assert!(a.window_2s.conserved());
    }

    #[test]
    fn r2_plan008_stop_epoch_generation_and_clock_reversed_stay_isolated(){
        let mut old=state(3);
        accepted(&mut old,1,100,0);
        accepted(&mut old,2,100,0);
        assert_eq!(old.timer_nodes(),4);
        let stop=old.stop(MonoNs(1_000_000_000)).unwrap();
        assert_eq!(stop.censored_live,2);
        assert_eq!(stop.censored_wire_bytes,200);
        assert_eq!(old.timer_nodes(),0);
        assert_eq!(old.on_due(MonoNs(9_000_000_000)),Err(MaturityError::Stopped));
        assert_eq!(old.on_authenticated_receipt(&open(pinned(),1,2,
            vec![page(0,&[1])]),MonoNs(9_000_000_000)),Err(MaturityError::Stopped));

        let newer=LaneKey{tunnel:TunnelKey{generation:12,..lane().tunnel},..lane()};
        let new_scope=ReceiptRouteScope::checked(newer,
            LaneKey{slot:4,..newer},WireDirection::ClientToServer,[4;16],
            (RecordPn(0),RecordPn(100_000)),
            (RecordPn(200_000),RecordPn(200_100))).unwrap();
        let mut current=MatureFirstSend::new(new_scope,MaturityConfig{max_live_data:2},
            MonoNs(1_000_000_000)).unwrap();
        assert_eq!(current.on_first_send(lane(),FirstSendKind::Data,
            FirstSendOutcome::Accepted{pn:RecordPn(1),wire_bytes:100},
            MonoNs(1_000_000_000)),Err(MaturityError::WrongScope));
        assert_eq!(current.on_authenticated_receipt(
            &open(pinned(),1,2,vec![page(0,&[1])]),MonoNs(1_000_000_000)),
            Err(MaturityError::WrongScope));
        assert_eq!(current.on_due(MonoNs(999_999_999)),Err(MaturityError::ClockReversed));
        current.on_first_send(newer,FirstSendKind::Data,
            FirstSendOutcome::Accepted{pn:RecordPn(3),wire_bytes:90},
            MonoNs(1_000_000_000)).unwrap();
        assert_eq!(current.live_records(),1);
    }

    #[test]
    fn r2_plan008_4096_records_128_blocks_bounded_timer_budget_and_conservation(){
        const N:u64=4096;
        let mut s=state(N as usize);
        for pn in 1..=N {accepted(&mut s,pn,96,0);}
        assert_eq!(s.live_records(),N as usize);
        assert_eq!(s.timer_nodes(),2*N as usize);
        // One reported page; 127 complete blocks without any feedback MUST
        // be UNKNOWN, never recorded as a series of fake losses.
        s.on_authenticated_receipt(&open(pinned(),1,N,vec![page(0,&[1])]),
            MonoNs(1_000_000_000)).unwrap();
        let mut bins=(MatureWindow::default(),MatureWindow::default());
        let mut ticks=0usize;
        while s.next_deadline().is_some(){
            let poll=s.on_due(MonoNs(8_000_000_000)).unwrap();
            assert!(poll.processed>0 && poll.processed<=64);
            accumulate(&mut bins.0,poll.window_2s);
            accumulate(&mut bins.1,poll.window_8s);
            ticks+=1;assert!(ticks<=2*N as usize/64+2);
        }
        for b in [bins.0,bins.1]{
            assert_eq!(b.first_sent,N);
            assert_eq!(b.unambiguous_positive,1);
            assert_eq!(b.covered_missing,254);
            assert_eq!(b.uncovered,N-255);
            assert_eq!(b.first_sent_wire_bytes,N*96);
            assert!(b.conserved());
        }
        assert_eq!(s.live_records(),0);
        assert_eq!(s.timer_nodes(),0);
        assert_eq!(s.next_deadline(),None);
        assert_eq!(s.on_first_send(lane(),FirstSendKind::Data,
            FirstSendOutcome::Accepted{pn:RecordPn(1),wire_bytes:96},
            MonoNs(8_000_000_001)),Err(MaturityError::DuplicateOrOld));
    }
    fn accumulate(a:&mut MatureWindow,b:MatureWindow){
        a.first_sent+=b.first_sent;a.first_sent_wire_bytes+=b.first_sent_wire_bytes;
        a.unambiguous_positive+=b.unambiguous_positive;
        a.positive_wire_bytes+=b.positive_wire_bytes;
        a.covered_missing+=b.covered_missing;a.missing_wire_bytes+=b.missing_wire_bytes;
        a.repaired_or_ambiguous+=b.repaired_or_ambiguous;
        a.ambiguous_wire_bytes+=b.ambiguous_wire_bytes;
        a.uncovered+=b.uncovered;a.uncovered_wire_bytes+=b.uncovered_wire_bytes;
    }
}
