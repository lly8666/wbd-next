//! PLAN-008 M2: *observation*, not RACK, loss repair or a second controller.
//! The sole sender owner emits one FINAL first-send kernel outcome per DATA PN.
//! M0 supplies only reverse-control facts AFTER real AEAD/open and replay
//! validation. Never infer sent count from RX, kernel Accepted != peer receipt.
//! Mature event-time windows are 2s and 8s. Unknown is not zero loss.
use std::collections::{BTreeMap,BTreeSet};
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
    short:BTreeSet<(u64,RecordPn)>,
    long:BTreeSet<(u64,RecordPn)>,
    clock:u64,
    retired_high:Option<RecordPn>,
    report_seq:Option<u32>,
    counters:ObservationCounters,
    stopped:bool,
}
impl MatureFirstSend {
    pub fn new(route:ReceiptRouteScope,cfg:MaturityConfig,start:MonoNs)
        ->Result<Self,MaturityError>{
        if cfg.max_live_data==0||cfg.max_live_data>200_000{
            return Err(MaturityError::InvalidConfig);
        }
        Ok(Self{route,cfg,entries:BTreeMap::new(),short:BTreeSet::new(),
            long:BTreeSet::new(),clock:start.0,retired_high:None,
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
    pub fn timer_nodes(&self)->usize{self.short.len()+self.long.len()}
    pub fn next_deadline(&self)->Option<MonoNs>{
        [self.short.first().map(|&(t,_)|t),self.long.first().map(|&(t,_)|t)]
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
                self.short.insert((end2,pn));
                self.long.insert((end8,pn));
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
            let a=self.short.first().copied().map(|(t,pn)|(t,pn,true));
            let b=self.long.first().copied().map(|(t,pn)|(t,pn,false));
            let Some((due,pn,is_short))=[a,b].into_iter().flatten()
                .min_by_key(|&(t,p,short)|(t,p,!short)) else {break;};
            if due>now.0{break;}
            if is_short {
                assert!(self.short.remove(&(due,pn)));
                let e=self.entries.get_mut(&pn).expect("short index owner");
                debug_assert!(!e.short_done);
                e.short_done=true;
                out.window_2s.add(e,due);
            }else {
                assert!(self.long.remove(&(due,pn)));
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
