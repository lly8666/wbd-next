//! FEC2 R5-M1-014: owner-local, bounded short-block formation and parity work.
//! Scheduling ONLY.  M3 owns wire/math, M0 owns admission/ABI and per-lane seal.
//! A source is offered to the caller immediately, before being retained for FEC.
//! No worker threads, codec, second send queue, or per-lane payload copies.
#![forbid(unsafe_code)]
use std::collections::VecDeque;
use std::ops::Range;
use std::sync::{Arc, atomic::{AtomicUsize, Ordering}};
use wbd_types::{ConfigRevision, MonoNs};
use wbd_types::buffer_contract::{checked_wire_range, UniqueSealable};
use crate::memory::UniqueBuffer;

pub const SOURCE_MAX: usize = 16;
pub const PENDING_BYTES_DEFAULT: usize = 2 * 1024 * 1024;
const RATE_SAMPLE_NS: u64 = 250_000_000;
const RTT_REFRESH_NS: u64 = 2_000_000_000;
const MAX_JOBS: usize = 8192;
const SOURCE_OVERHEAD: usize = 48;
const JOB_OVERHEAD: usize = 128;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Class { Small, Medium, Mtu }
impl Class {
    fn index(self) -> usize { match self { Self::Small => 0, Self::Medium => 1, Self::Mtu => 2 } }
    fn of(len: usize) -> Self {
        if len <= 256 { Self::Small } else if len <= 512 { Self::Medium } else { Self::Mtu }
    }
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FecMode { Off, Normal, Game }
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Profile { Light, Mild, Medium, Balanced, High, Strong, Maximum }
impl Profile {
    pub fn redundancy(self, k: u8) -> u8 {
        let (n, d) = match self {
            Self::Light => (1,8), Self::Mild => (1,4), Self::Medium => (3,8),
            Self::Balanced => (1,2), Self::High => (3,4),
            Self::Strong => (1,1), Self::Maximum => (5,4)
        };
        (((k as u16 * n + d - 1) / d).min(20)) as u8
    }
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FecError { Stopped, InvalidWindow, Oversize, Exhausted, ClockRollback, StalePolicy }
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SourceTicket {
    pub block_id: u64, pub index: u8, pub class: Class,
    pub revision: ConfigRevision, pub deadline: MonoNs,
}
pub struct SourceFirstReady<'a> {
    pub ticket: Option<SourceTicket>, pub frame: &'a [u8],
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Accepted {
    pub ticket: Option<SourceTicket>, pub fec_retained: bool,
    pub source_enqueued: bool, pub closed_full: bool,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Limits { pub pending_bytes: usize, pub pending_jobs: usize, pub max_frame: usize }
impl Limits {
    pub fn valid(self) -> bool {
        self.pending_bytes > JOB_OVERHEAD && self.pending_bytes <= 128 * 1024 * 1024 &&
        self.pending_jobs > 0 && self.pending_jobs <= MAX_JOBS &&
        self.max_frame > 0 && self.max_frame <= 65535
    }
}
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct ClassStats {
    pub accepted: u64, pub source_not_ready: u64, pub closed: u64,
    pub full: u64, pub partial: u64, pub k_hist: [u64;17],
    pub r_planned: u64, pub r_sent: u64, pub expired_jobs: u64,
    pub pressure_jobs: u64, pub pressure_sources: u64,
    pub age_max_ns: u64, pub unknown_capacity: u64,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct OwnerReport {
    pub classes: [ClassStats;3], pub open_bytes: usize,
    pub charged_bytes: usize, pub outstanding_jobs: usize,
    pub queued_jobs: usize, pub stopped: bool,
}
struct Source {
    buffer: UniqueBuffer, window: Range<usize>,
}
impl Source {
    fn bytes(&mut self) -> &[u8] { &self.buffer.writable()[self.window.clone()] }
}
struct Open {
    block_id: u64, first: MonoNs, deadline: MonoNs,
    revision: ConfigRevision, profile: Profile, sources: Vec<Source>, charge: usize,
}
#[derive(Default)]
struct Rate {
    window_start: Option<MonoNs>, count: u64, lambda_q16: Option<u64>,
}
impl Rate {
    fn accepted(&mut self, at: MonoNs) {
        let Some(start) = self.window_start else {
            self.window_start = Some(at);
            self.count = 1;
            return;
        };
        if at.0 < start.0 { return; }
        self.count = self.count.saturating_add(1);
        let dt = at.0 - start.0;
        if dt >= RATE_SAMPLE_NS {
            let sample = ((self.count as u128 * 1_000_000_000u128 * 65_536) / dt as u128)
                .min(u64::MAX as u128) as u64;
            self.lambda_q16 = Some(match self.lambda_q16 {
                Some(old) => ((old as u128 * 3 + sample as u128) / 4) as u64,
                None => sample,
            });
            self.window_start = Some(at);
            self.count = 0;
        }
    }
}
#[derive(Default)]
struct Charge {
    bytes: AtomicUsize, jobs: AtomicUsize,
}
/// Once moved out of the owner's bounded queue the original source slabs
/// remain on loan. Drop (even after Stop) releases only this job's charge;
/// an independently held driver/record loan remains protected by Arena.
pub struct ParityJob {
    pub block_id: u64, pub class: Class, pub first: MonoNs,
    pub closed_at: MonoNs, pub expire_at: MonoNs,
    pub revision: ConfigRevision, pub k: u8, pub r: u8,
    sources: Vec<Source>, charge: usize, ledger: Arc<Charge>,
}
impl ParityJob {
    pub fn source(&mut self, index: usize) -> Option<&[u8]> {
        self.sources.get_mut(index).map(Source::bytes)
    }
    /// Borrow the one-copy sources for M3 encode_into. Stack-only references.
    pub fn with_sources<R>(&mut self, encode: impl FnOnce(&[&[u8]]) -> R) -> R {
        let count = self.sources.len();
        let mut refs: [&[u8]; SOURCE_MAX] = [&[]; SOURCE_MAX];
        for (dst, source) in refs.iter_mut().zip(self.sources.iter_mut()) {
            *dst = source.bytes();
        }
        encode(&refs[..count])
    }
    pub fn source_count(&self) -> usize { self.sources.len() }
    pub fn charge_bytes(&self) -> usize { self.charge }
}
impl Drop for ParityJob {
    fn drop(&mut self) {
        self.ledger.bytes.fetch_sub(self.charge, Ordering::AcqRel);
        self.ledger.jobs.fetch_sub(1, Ordering::AcqRel);
    }
}
pub struct Fec2Owner {
    mode: FecMode, profile: Profile, revision: ConfigRevision,
    limits: Limits, rtt_ns: Option<u64>, last_rtt_at: Option<MonoNs>,
    next_block: u64, open: [Option<Open>;3], open_bytes: usize,
    rate: [Rate;3], pending: VecDeque<ParityJob>,
    ledger: Arc<Charge>, stats: [ClassStats;3],
    stopping: bool, last_clock: MonoNs,
}
impl Fec2Owner {
    pub fn new(mode: FecMode, profile: Profile, revision: ConfigRevision, limits: Limits) -> Option<Self> {
        if !limits.valid() { return None; }
        Some(Self {
            mode, profile, revision, limits, rtt_ns: None, last_rtt_at: None,
            next_block: 1, open: std::array::from_fn(|_| None),
            open_bytes: 0, rate: std::array::from_fn(|_| Rate::default()),
            pending: VecDeque::with_capacity(limits.pending_jobs),
            ledger: Arc::new(Charge::default()),
            stats: [ClassStats::default();3], stopping: false, last_clock: MonoNs(0)
        })
    }
    fn clock(&mut self, now: MonoNs) -> Result<(), FecError> {
        if self.stopping { return Err(FecError::Stopped); }
        if now.0 < self.last_clock.0 { return Err(FecError::ClockRollback); }
        self.last_clock = now;
        Ok(())
    }
    /// Pre-filtered trusted RTTs of CURRENT eligible lanes only. Game takes
    /// the minimum, not the slowest; absent/invalid samples use startup caps.
    /// Updating RTT or rate NEVER extends an existing open block.
    pub fn trusted_rtt(&mut self, samples_ns: &[Option<u64>], now: MonoNs) -> Result<bool,FecError> {
        self.clock(now)?;
        if self.last_rtt_at.is_some_and(|at| now.0 - at.0 < RTT_REFRESH_NS) { return Ok(false); }
        self.rtt_ns = samples_ns.iter().filter_map(|x| *x).filter(|x| *x > 0).min();
        self.last_rtt_at = Some(now);
        Ok(true)
    }
    fn cap_ns(&self) -> u64 {
        match (self.mode, self.rtt_ns) {
            (FecMode::Game, Some(rtt)) => (rtt/8).clamp(4_000_000,12_000_000),
            (FecMode::Game, None) => 8_000_000,
            (_, Some(rtt)) => (rtt/4).clamp(8_000_000,24_000_000),
            (_, None) => 16_000_000,
        }
    }
    pub fn deadline_span_ns(&self, class: Class) -> u64 {
        let (min, startup) = match self.mode {
            FecMode::Game => (2_000_000,3_000_000),
            _ => (4_000_000,6_000_000),
        };
        let cap = self.cap_ns();
        let Some(lambda) = self.rate[class.index()].lambda_q16 else { return startup.min(cap); };
        if lambda == 0 || (lambda as u128 * cap as u128) < 65_536u128 * 1_000_000_000u128 {
            return min;
        }
        ((22_500_000_000u128 * 65_536u128 / lambda as u128)
            .min(u64::MAX as u128) as u64).clamp(min, cap)
    }
    fn new_id(&mut self) -> Result<u64,FecError> {
        let id = self.next_block;
        self.next_block = self.next_block.checked_add(1).ok_or(FecError::Exhausted)?;
        Ok(id)
    }
    fn total_bytes(&self) -> usize {
        self.open_bytes.saturating_add(self.ledger.bytes.load(Ordering::Acquire))
    }
    fn can_retain(&self, extra: usize) -> bool {
        extra <= self.limits.pending_bytes.saturating_sub(self.total_bytes())
    }
    /// Old parity has bounded *post-close* lifetime regardless of block T.
    /// This queue is just pre-encode owner-held work; once M3 finishes, call
    /// existing TxOwner::offer_parity for independent ready-byte DRR service.
    fn expire(&mut self, now: MonoNs) {
        while self.pending.front().is_some_and(|j| now.0 > j.expire_at.0) {
            let job = self.pending.pop_front().unwrap();
            self.stats[job.class.index()].expired_jobs += 1;
        }
    }
    fn close(&mut self, class: Class, now: MonoNs, full: bool) {
        let idx = class.index();
        let Some(open) = self.open[idx].take() else { return; };
        self.open_bytes -= open.charge;
        let k = open.sources.len() as u8;
        let r = open.profile.redundancy(k);
        let st = &mut self.stats[idx];
        st.closed += 1;
        st.k_hist[k as usize] += 1;
        st.r_planned += r as u64;
        st.age_max_ns = st.age_max_ns.max(now.0.saturating_sub(open.first.0));
        if full { st.full += 1; } else { st.partial += 1; }
        // Queue pressure never blocks a fresh source. The group is canceled
        // and its retained plaintext is dropped, never silently grown.
        self.expire(now);
        if self.pending.len() >= self.limits.pending_jobs ||
            self.ledger.jobs.load(Ordering::Acquire) >= self.limits.pending_jobs ||
            !self.can_retain(open.charge) {
            self.stats[idx].pressure_jobs += 1;
            self.stats[idx].unknown_capacity += 1;
            return;
        }
        self.ledger.bytes.fetch_add(open.charge, Ordering::AcqRel);
        self.ledger.jobs.fetch_add(1, Ordering::AcqRel);
        let age = match self.mode { FecMode::Game => 5_000_000, _ => 10_000_000 };
        self.pending.push_back(ParityJob {
            block_id: open.block_id, class, first: open.first,
            closed_at: now, expire_at: MonoNs(now.0.saturating_add(age)),
            revision: open.revision, k, r, sources: open.sources,
            charge: open.charge, ledger: Arc::clone(&self.ledger)
        });
    }
    pub fn on_due(&mut self, now: MonoNs) -> Result<usize,FecError> {
        self.clock(now)?;
        let mut closed=0;
        for c in [Class::Small,Class::Medium,Class::Mtu] {
            if self.open[c.index()].as_ref().is_some_and(|b| now.0 >= b.deadline.0) {
                self.close(c,now,false);closed+=1;
            }
        }
        self.expire(now);
        Ok(closed)
    }
    pub fn next_deadline(&self) -> Option<MonoNs> {
        self.open.iter().filter_map(|o| o.as_ref().map(|b|b.deadline))
            .chain(self.pending.front().map(|b|MonoNs(b.expire_at.0.saturating_add(1))))
            .min_by_key(|t|t.0)
    }
    pub fn change_policy(&mut self,mode:FecMode,profile:Profile,revision:ConfigRevision,
        max_frame:usize,now:MonoNs)->Result<(),FecError> {
        self.clock(now)?;
        if max_frame == 0 || max_frame > 65535 { return Err(FecError::Oversize); }
        if revision.0 < self.revision.0 ||
            (revision == self.revision &&
                (mode != self.mode || profile != self.profile ||
                 max_frame != self.limits.max_frame)) {
            return Err(FecError::StalePolicy);
        }
        if revision == self.revision { return Ok(()); }
        for c in [Class::Small,Class::Medium,Class::Mtu] {
            self.close(c,now,false);
        }
        self.mode=mode;self.profile=profile;self.revision=revision;
        self.limits.max_frame=max_frame;
        Ok(())
    }
    /// Only synchronous producer-side first-ready: the callback may seal
    /// once PER qualified lane, or hand a fully sealed source to TxOwner.
    /// It cannot retain this borrow. One original slab is retained, never a
    /// per-lane plaintext copy. GameTx/ActiveLaneSnapshot remain authoritative
    /// for the actual multi-lane dispatch/dedup and admission policy.
    pub fn push_source<F>(&mut self,mut buffer:UniqueBuffer,window:Range<usize>,
        now:MonoNs,mut send:F)->Result<Accepted,(FecError,UniqueBuffer)>
    where F:FnMut(SourceFirstReady<'_>)->bool {
        if let Err(e)=self.clock(now) { return Err((e,buffer)); }
        let valid=match checked_wire_range(buffer.writable().len(),window) {
            Ok(w) if !w.is_empty()=>w, _=>return Err((FecError::InvalidWindow,buffer)),
        };
        if valid.len()>self.limits.max_frame {return Err((FecError::Oversize,buffer));}
        if self.mode==FecMode::Off {
            let enqueued=send(SourceFirstReady{ticket:None,frame:&buffer.writable()[valid]});
            return Ok(Accepted{ticket:None,fec_retained:false,
                source_enqueued:enqueued,closed_full:false});
        }
        let class=Class::of(valid.len());
        let idx=class.index();
        if self.open[idx].as_ref().is_some_and(|b|now.0>=b.deadline.0) {
            self.close(class,now,false);
        }
        if self.open[idx].is_none() {
            let id=match self.new_id() {Ok(id)=>id,Err(e)=>return Err((e,buffer))};
            self.open[idx]=Some(Open {
                block_id:id,first:now,
                deadline:MonoNs(now.0.saturating_add(self.deadline_span_ns(class))),
                revision:self.revision,profile:self.profile,
                sources:Vec::with_capacity(SOURCE_MAX),charge:JOB_OVERHEAD
            });
            self.open_bytes+=JOB_OVERHEAD;
        }
        let charge=buffer.writable().len().saturating_add(SOURCE_OVERHEAD);
        // Admission pressure must be decided BEFORE publishing the source
        // index: an unretained index>=k would be invalid on the wire.
        if !self.can_retain(charge) {
            if self.open[idx].as_ref().is_some_and(|o|!o.sources.is_empty()) {
                self.close(class,now,false);
            } else if let Some(vacant)=self.open[idx].take() {
                self.open_bytes-=vacant.charge;
            }
            // Avoid a zero-source block. Give this valid systematic its own
            // unique singleton block ID, with r_sent=0 and capacity UNKNOWN.
            let id=match self.new_id(){Ok(id)=>id,Err(e)=>return Err((e,buffer))};
            let ticket=SourceTicket{block_id:id,index:0,class,
                revision:self.revision,deadline:now};
            let enqueued=send(SourceFirstReady{ticket:Some(ticket),
                frame:&buffer.writable()[valid]});
            let st=&mut self.stats[idx];
            st.accepted+=1;
            st.pressure_sources+=1;
            st.unknown_capacity+=1;
            st.closed+=1;
            st.partial+=1;
            st.k_hist[1]+=1;
            if !enqueued{st.source_not_ready+=1;}
            self.rate[idx].accepted(now);
            return Ok(Accepted{ticket:Some(ticket),fec_retained:false,
                source_enqueued:enqueued,closed_full:false});
        }
        let open=self.open[idx].as_ref().unwrap();
        let ticket=SourceTicket{
            block_id:open.block_id,index:open.sources.len() as u8,
            class,revision:open.revision,deadline:open.deadline
        };
        let enqueued=send(SourceFirstReady{ticket:Some(ticket),
            frame:&buffer.writable()[valid.clone()]});
        self.stats[idx].accepted+=1;
        if !enqueued { self.stats[idx].source_not_ready+=1; }
        self.rate[idx].accepted(now);
        let open=self.open[idx].as_mut().unwrap();
        open.sources.push(Source{buffer,window:valid});
        open.charge+=charge;
        self.open_bytes+=charge;
        let retained=true;
        let full=retained && self.open[idx].as_ref()
            .is_some_and(|b|b.sources.len()==SOURCE_MAX);
        if full {self.close(class,now,true);}
        Ok(Accepted{ticket:Some(ticket),fec_retained:retained,
            source_enqueued:enqueued,closed_full:full})
    }
    /// Oldest *closed* class first. Fresh send scheduling remains in
    /// existing TxOwner and is never waiting on this optional auxiliary job.
    pub fn take_parity(&mut self,now:MonoNs)->Result<Option<ParityJob>,FecError> {
        self.clock(now)?;
        self.expire(now);
        Ok(self.pending.pop_front())
    }
    /// Only confirmed first transmissions count as r_sent. A driver-prefix
    /// uncertain outcome is NOT confirmed; mark capacity unknown separately.
    pub fn finish_parity(&mut self,job:ParityJob,sent:u8,capacity_known:bool) {
        let idx=job.class.index();
        self.stats[idx].r_sent+=sent.min(job.r) as u64;
        if !capacity_known {self.stats[idx].unknown_capacity+=1;}
        drop(job);
    }
    pub fn stop(&mut self) {
        if self.stopping{return;}
        self.stopping=true;
        self.open=std::array::from_fn(|_|None);
        self.open_bytes=0;
        self.pending.clear();
        // External ParityJob and any separately sealed driver loans still
        // own their slabs. No timeout can force them back into the arena.
    }
    pub fn report(&self)->OwnerReport {
        OwnerReport{classes:self.stats,open_bytes:self.open_bytes,
            charged_bytes:self.total_bytes(),
            outstanding_jobs:self.ledger.jobs.load(Ordering::Acquire),
            queued_jobs:self.pending.len(),stopped:self.stopping}
    }
}

#[cfg(test)]
#[path = "fec2_owner_tests.rs"]
mod tests;
