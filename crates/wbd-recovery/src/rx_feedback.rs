//! Bounded RX receipt scheduler for already authenticated DATA.
//! M0 is responsible for AEAD/replay/lane checks before any call here.
//! This module produces bounded *draft* pages, not a peer-authenticated ACK.
//! It does not seal, allocate PN, access sockets, or block fresh traffic.
use std::collections::BTreeMap;
use wbd_types::{MonoNs, RecordPn};
use crate::receipt::ReceiptPage;

const PAGE_BITS: u64 = 256;
const GAP_NS: u64 = 2_000_000;
const STEADY_NS: u64 = 10_000_000;
const MIN_PAGE_NS: u64 = 2_000_000;
const MAX_REPORT_PAGES: usize = 8;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RxFeedbackConfig {
    pub max_retained_pages: usize,
    pub max_pages_per_report: usize,
    pub retention_ns: u64,
    pub srtt_ns: u64,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FeedbackError { InvalidConfig, StaleDraft }
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FeedbackReceive { First, Duplicate, Late }
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FeedbackSendResult { Accepted, Uncertain, NotSent }

/// Feed into the M3 control encoder; it is NOT independently authenticated.
pub struct FeedbackDraft {
    token: u64,
    report_seq: u32,
    largest_data_pn: RecordPn,
    pages: Vec<ReceiptPage>,
}
impl FeedbackDraft {
    pub fn report_seq(&self) -> u32 { self.report_seq }
    pub fn largest_data_pn(&self) -> RecordPn { self.largest_data_pn }
    pub fn pages(&self) -> &[ReceiptPage] { &self.pages }
}
struct Page {
    bitmap: [u8; 32],
    revision: u64,
    dirty: bool,
    // Initial, repeat, and at most one post-duplicate reassertion.
    emissions: u8,
    duplicate_reassertion_used: bool,
    next_due: Option<MonoNs>,
    last_submit: Option<MonoNs>,
    expires: MonoNs,
}
struct Selected { base: u64, revision: u64 }
struct InFlight { token: u64, selected: Vec<Selected> }

pub struct RxFeedbackState {
    cfg: RxFeedbackConfig,
    pages: BTreeMap<u64, Page>,
    retired_floor: u64,
    retired_all: bool,
    largest: Option<RecordPn>,
    next_seq: u32,
    next_token: u64,
    pending: Option<InFlight>,
    feedback_drop: u64,
}
impl RxFeedbackState {
    pub fn new(cfg: RxFeedbackConfig) -> Result<Self, FeedbackError> {
        if cfg.max_retained_pages == 0 || cfg.max_retained_pages > 4096
            || cfg.max_pages_per_report == 0 || cfg.max_pages_per_report > MAX_REPORT_PAGES
            || cfg.srtt_ns == 0 || cfg.retention_ns <= STEADY_NS {
            return Err(FeedbackError::InvalidConfig);
        }
        Ok(Self {cfg, pages:BTreeMap::new(), retired_floor:0,
            retired_all:false, largest:None, next_seq:0, next_token:1,
            pending:None, feedback_drop:0})
    }
    fn repeat_ns(&self) -> u64 {
        (self.cfg.srtt_ns / 4).clamp(MIN_PAGE_NS,20_000_000)
    }
    fn earliest_after(last: Option<MonoNs>, due: MonoNs) -> MonoNs {
        MonoNs(last.map_or(due.0, |at| due.0.max(at.0.saturating_add(MIN_PAGE_NS))))
    }
    fn retire_oldest(&mut self) {
        let Some((&base,_))=self.pages.first_key_value() else {return};
        let page=self.pages.remove(&base).expect("oldest exists");
        if page.dirty { self.feedback_drop=self.feedback_drop.saturating_add(1); }
        match base.checked_add(PAGE_BITS) {
            Some(floor)=>self.retired_floor=self.retired_floor.max(floor),
            None=>{self.retired_all=true;self.retired_floor=u64::MAX;}
        }
    }
    fn retire_expired(&mut self,now:MonoNs) {
        // Retire only the contiguous oldest page. A newer, expired page
        // cannot retire still-live older data out of order.
        while self.pages.first_key_value().is_some_and(|(_,p)| p.expires<=now) {
            self.retire_oldest();
        }
    }
    /// Only M0's authenticated, fresh DATA ingress may call this.
    /// Duplicates never extend expiry or count as fresh payload delivery.
    pub fn on_authenticated_data(&mut self,pn:RecordPn,now:MonoNs) -> FeedbackReceive {
        self.retire_expired(now);
        let base=pn.0 & !(PAGE_BITS-1);
        if self.retired_all || pn.0<self.retired_floor {return FeedbackReceive::Late;}
        let off=pn.0-base;
        let mask=1u8 << (off%8);
        let idx=(off/8) as usize;
        let gap=self.largest.is_some_and(|prev|
            pn.0<prev.0 || pn.0>prev.0.saturating_add(1));
        if self.largest.is_none_or(|old| pn>old) {self.largest=Some(pn);}
        let delay=if gap {GAP_NS} else {STEADY_NS};
        if !self.pages.contains_key(&base) {
            if self.pages.len()==self.cfg.max_retained_pages {
                // Very late, untracked page cannot evict newer live pages.
                if self.pages.first_key_value().is_some_and(|(&old,_)|base<old) {
                    return FeedbackReceive::Late;
                }
                self.retire_oldest();
            }
            if self.retired_all || pn.0<self.retired_floor {return FeedbackReceive::Late;}
            let mut bitmap=[0u8;32];bitmap[idx]|=mask;
            self.pages.insert(base,Page {bitmap,revision:1,dirty:true,emissions:0,
                duplicate_reassertion_used:false,
                next_due:Some(MonoNs(now.0.saturating_add(delay))),
                last_submit:None,expires:MonoNs(now.0.saturating_add(self.cfg.retention_ns))});
            return FeedbackReceive::First;
        }
        let p=self.pages.get_mut(&base).expect("page present");
        if p.bitmap[idx]&mask!=0 {
            // Two feedback copies may have been lost. A PTO data duplicate
            // may elicit ONE extra page reminder, never infinite ACK traffic.
            if p.emissions==2 && !p.duplicate_reassertion_used && !p.dirty {
                p.duplicate_reassertion_used=true;
                p.dirty=true;
                p.revision=p.revision.saturating_add(1);
                p.next_due=Some(Self::earliest_after(p.last_submit,
                    MonoNs(now.0.saturating_add(MIN_PAGE_NS))));
            }
            return FeedbackReceive::Duplicate;
        }
        p.bitmap[idx]|=mask;
        p.revision=p.revision.saturating_add(1);
        p.dirty=true;
        p.emissions=0;
        p.duplicate_reassertion_used=false;
        let due=Self::earliest_after(p.last_submit,MonoNs(now.0.saturating_add(delay)));
        p.next_due=Some(p.next_due.map_or(due,|old|old.min(due)));
        FeedbackReceive::First
    }
    /// Control/quality/health packets must not cause ACK-of-ACK loops.
    pub fn on_authenticated_control(&mut self,_now:MonoNs) {}
    pub fn retained_pages(&self)->usize {self.pages.len()}
    pub fn feedback_drop(&self)->u64 {self.feedback_drop}
    pub fn retired_floor(&self)->RecordPn {RecordPn(self.retired_floor)}
    pub fn next_deadline(&self)->Option<MonoNs> {
        let expire=self.pages.first_key_value().map(|(_,p)|p.expires);
        let due=if self.pending.is_some(){None}else{
            self.pages.values().filter_map(|p|p.next_due).min()
        };
        expire.into_iter().chain(due).min()
    }
    /// Limit to eight pages; dirty first. Does not clear them until the
    /// caller supplies Accepted/Uncertain/NotSent control send outcome.
    pub fn on_due(&mut self,now:MonoNs)->Option<FeedbackDraft> {
        self.retire_expired(now);
        if self.pending.is_some(){return None;}
        let mut selected=Vec::with_capacity(self.cfg.max_pages_per_report);
        for want_dirty in [true,false] {
            for (&base,p) in &self.pages {
                if selected.len()==self.cfg.max_pages_per_report {break;}
                if p.dirty!=want_dirty || now>=p.expires ||
                    !p.next_due.is_some_and(|due|due<=now) {continue;}
                selected.push(Selected {base,revision:p.revision});
            }
        }
        if selected.is_empty() {return None;}
        let pages=selected.iter().map(|s|ReceiptPage {
            base_pn:RecordPn(s.base),bitmap:self.pages[&s.base].bitmap
        }).collect();
        let token=self.next_token;
        self.next_token=self.next_token.checked_add(1)?; // never wrap candidate identity
        let seq=self.next_seq;
        self.next_seq=self.next_seq.wrapping_add(1);
        self.pending=Some(InFlight{token,selected});
        Some(FeedbackDraft {token,report_seq:seq,
            largest_data_pn:self.largest.expect("due page means prior data"),pages})
    }
    /// Uncertain consumes one report opportunity, but is never interpreted
    /// as evidence that the sender received this draft. NotSent keeps dirty.
    pub fn on_send_result(&mut self,draft:&FeedbackDraft,
        result:FeedbackSendResult,now:MonoNs)->Result<(),FeedbackError> {
        if self.pending.as_ref().is_none_or(|p|p.token!=draft.token) {
            return Err(FeedbackError::StaleDraft);
        }
        let pending=self.pending.take().expect("token checked");
        let repeat_ns=self.repeat_ns();
        for s in pending.selected {
            let Some(page)=self.pages.get_mut(&s.base) else {continue};
            if result==FeedbackSendResult::NotSent {
                self.feedback_drop=self.feedback_drop.saturating_add(1);
                let later=MonoNs(now.0.saturating_add(MIN_PAGE_NS));
                page.next_due=Some(Self::earliest_after(page.last_submit,later));
                continue;
            }
            page.last_submit=Some(now);
            if page.revision==s.revision {
                page.dirty=false;
                page.emissions=page.emissions.saturating_add(1);
                page.next_due=if page.emissions==1 {
                    Some(MonoNs(now.0.saturating_add(repeat_ns)))
                } else {None};
            } else {
                // Changed during in-flight control: never clear newer bits.
                let later=MonoNs(now.0.saturating_add(MIN_PAGE_NS));
                page.next_due=Some(Self::earliest_after(page.last_submit,later));
            }
        }
        Ok(())
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    fn cfg(pages:usize)->RxFeedbackConfig {RxFeedbackConfig{
        max_retained_pages:pages,max_pages_per_report:8,
        retention_ns:100_000_000,srtt_ns:40_000_000}}
    fn bit(d:&FeedbackDraft,pn:u64)->bool {
        d.pages().iter().any(|p|p.base_pn.0==(pn&!255)
            && p.bitmap[((pn&255)/8) as usize]&(1<<((pn&255)%8))!=0)
    }
    #[test]
    fn r2_rx_feedback_control_does_not_elicit_ack_and_steady_ten_ms() {
        let mut x=RxFeedbackState::new(cfg(4)).unwrap();
        x.on_authenticated_control(MonoNs(100));
        assert!(x.on_due(MonoNs(100_000_000)).is_none());
        assert_eq!(x.on_authenticated_data(RecordPn(1),MonoNs(0)),FeedbackReceive::First);
        assert_eq!(x.next_deadline(),Some(MonoNs(10_000_000)));
        assert!(x.on_due(MonoNs(9_999_999)).is_none());
        let d=x.on_due(MonoNs(10_000_000)).unwrap();
        assert!(bit(&d,1));
        x.on_send_result(&d,FeedbackSendResult::Accepted,MonoNs(10_000_000)).unwrap();
        assert!(x.on_due(MonoNs(19_999_999)).is_none());
        let r=x.on_due(MonoNs(20_000_000)).unwrap();
        x.on_send_result(&r,FeedbackSendResult::Uncertain,MonoNs(20_000_000)).unwrap();
        assert!(x.on_due(MonoNs(90_000_000)).is_none());
    }
    #[test]
    fn r2_rx_feedback_gap_two_ms_zero_bits_dirty_priority_eight_pages() {
        let mut x=RxFeedbackState::new(cfg(16)).unwrap();
        for i in 0..10 {x.on_authenticated_data(RecordPn(i*256),MonoNs(0));}
        let d=x.on_due(MonoNs(2_000_000)).unwrap();
        assert_eq!(d.pages().len(),8);
        assert!(!bit(&d,0)&&bit(&d,7*256)&&bit(&d,8*256));
        assert_eq!(d.pages()[0].bitmap[1],0);
        x.on_send_result(&d,FeedbackSendResult::Accepted,MonoNs(2_000_000)).unwrap();
        let d2=x.on_due(MonoNs(2_000_000)).unwrap();
        assert_eq!(d2.pages().len(),1);
        assert!(bit(&d2,9*256));
        x.on_send_result(&d2,FeedbackSendResult::Accepted,MonoNs(2_000_000)).unwrap();
        let p=x.on_due(MonoNs(10_000_000)).unwrap();
        assert!(bit(&p,0));
    }
    #[test]
    fn r2_rx_feedback_two_lost_reports_duplicate_one_reassertion() {
        let mut x=RxFeedbackState::new(cfg(2)).unwrap();
        x.on_authenticated_data(RecordPn(7),MonoNs(0));
        let a=x.on_due(MonoNs(10_000_000)).unwrap();
        x.on_send_result(&a,FeedbackSendResult::Accepted,MonoNs(10_000_000)).unwrap();
        let b=x.on_due(MonoNs(20_000_000)).unwrap();
        x.on_send_result(&b,FeedbackSendResult::Accepted,MonoNs(20_000_000)).unwrap();
        assert_eq!(x.on_authenticated_data(RecordPn(7),MonoNs(30_000_000)),FeedbackReceive::Duplicate);
        assert_eq!(x.on_authenticated_data(RecordPn(7),MonoNs(30_000_001)),FeedbackReceive::Duplicate);
        let c=x.on_due(MonoNs(32_000_000)).unwrap();
        x.on_send_result(&c,FeedbackSendResult::Uncertain,MonoNs(32_000_000)).unwrap();
        assert!(x.on_due(MonoNs(70_000_000)).is_none());
        x.on_due(MonoNs(100_000_001));
        assert_eq!(x.retained_pages(),0);
        assert_eq!(x.on_authenticated_data(RecordPn(7),MonoNs(100_000_002)),FeedbackReceive::Late);
    }
    #[test]
    fn r2_rx_feedback_notsent_keeps_dirty_and_race_merges_bits() {
        let mut x=RxFeedbackState::new(cfg(2)).unwrap();
        x.on_authenticated_data(RecordPn(256),MonoNs(0));
        let old=x.on_due(MonoNs(10_000_000)).unwrap();
        assert_eq!(x.on_authenticated_data(RecordPn(257),MonoNs(11_000_000)),FeedbackReceive::First);
        x.on_send_result(&old,FeedbackSendResult::Accepted,MonoNs(12_000_000)).unwrap();
        assert!(x.on_due(MonoNs(13_999_999)).is_none());
        let merged=x.on_due(MonoNs(14_000_000)).unwrap();
        assert!(bit(&merged,256)&&bit(&merged,257));
        x.on_send_result(&merged,FeedbackSendResult::NotSent,MonoNs(14_000_000)).unwrap();
        assert!(x.on_due(MonoNs(15_999_999)).is_none());
        let retry=x.on_due(MonoNs(16_000_000)).unwrap();
        assert!(bit(&retry,257));
        assert_eq!(x.on_send_result(&merged,FeedbackSendResult::Accepted,MonoNs(16_000_000)),Err(FeedbackError::StaleDraft));
        x.on_send_result(&retry,FeedbackSendResult::Accepted,MonoNs(16_000_000)).unwrap();
        assert!(x.feedback_drop()>0);
    }
    #[test]
    fn r2_rx_feedback_bounded_pages_retirement_and_late_never_recreated() {
        let mut x=RxFeedbackState::new(cfg(2)).unwrap();
        for pn in [5,260,513] {x.on_authenticated_data(RecordPn(pn),MonoNs(0));}
        assert_eq!(x.retained_pages(),2);
        assert_eq!(x.retired_floor(),RecordPn(256));
        assert_eq!(x.on_authenticated_data(RecordPn(5),MonoNs(10)),FeedbackReceive::Late);
        assert!(x.on_due(MonoNs(100_000_001)).is_none());
        assert_eq!(x.retained_pages(),0);
        assert_eq!(x.on_authenticated_data(RecordPn(260),MonoNs(100_000_002)),FeedbackReceive::Late);
    }
    #[test]
    fn r2_rx_feedback_report_seq_wrap_and_33_pages_bounded() {
        let mut x=RxFeedbackState::new(cfg(35)).unwrap();
        x.next_seq=u32::MAX;
        for i in 0..33 {x.on_authenticated_data(RecordPn(i*256),MonoNs(0));}
        assert_eq!(x.retained_pages(),33);
        let a=x.on_due(MonoNs(10_000_000)).unwrap();
        assert_eq!(a.report_seq(),u32::MAX);
        x.on_send_result(&a,FeedbackSendResult::Uncertain,MonoNs(10_000_000)).unwrap();
        let b=x.on_due(MonoNs(10_000_000)).unwrap();
        assert_eq!(b.report_seq(),0);
        assert_eq!(b.pages().len(),8);
        x.on_send_result(&b,FeedbackSendResult::Accepted,MonoNs(10_000_000)).unwrap();
        assert_eq!(RxFeedbackState::new(RxFeedbackConfig{max_pages_per_report:9,..cfg(35)}).err(),Some(FeedbackError::InvalidConfig));
    }
}