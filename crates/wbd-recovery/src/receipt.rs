//! Pure R2 authenticated-receipt / shadow state. No clock reads, socket,
//! payload mutation, new PN allocation, or encryption. M0 owns the actual
//! M3 opened-record -> AuthenticatedReceipt trust-boundary adapter.
use std::collections::{BTreeMap, BTreeSet};
use wbd_types::buffer_contract::{BufferOrigin, FrozenRecordHandle};
use wbd_types::{DataError, LaneKey, LimitedResource, MonoNs, RecordPn};

const PAGE_BITS: u64 = 256;
const MAX_PAGES: usize = 8;
const MAX_POLL_CANDIDATES: usize = 32;
const QUEUE_LIFETIME_NS: u64 = 20_000_000;
const MIN_REORDER_NS:u64=2_000_000;
const MAX_REORDER_NS:u64=20_000_000;
const FEEDBACK_ALLOWANCE_NS:u64=10_000_000;
const MIN_PTO_VARIATION_NS:u64=4_000_000;
pub const OUTER_REPAIR_ATTEMPT_LIMIT:u64=1;
const MAX_RETAIN_NS:u64=1_500_000_000;
const V3_GAP_MIN_NS:u64=20_000_000;
const V3_GAP_MAX_NS:u64=100_000_000;
const V3_FEEDBACK_MARGIN_NS:u64=20_000_000;

#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct AdaptiveTimingSnapshot{
    pub samples:u64,pub srtt_ns:u64,pub rttvar_ns:u64,pub recent_rtt_ns:u64,
    pub reorder_window_ns:u64,pub pto_ns:u64,pub cache_ns:u64,
}
#[derive(Clone,Copy,Debug,Default,Eq,PartialEq)]
pub struct ReceiptDiagnosticSnapshot{
    pub candidate_first:u64,pub candidate_retry:u64,
    pub acked_attempt0:u64,pub acked_attempt1:u64,pub acked_attempt2:u64,
    pub expired_attempt0:u64,pub expired_attempt1:u64,pub expired_attempt2:u64,
    pub late_positive_expired:u64,
    pub repair_accepted_retired:u64,pub repair_uncertain_retired:u64,
    pub repair_abandoned_retired:u64,pub max_queue_age_ns:u64,
}
#[derive(Clone,Copy)]
struct AdaptiveTiming{
    samples:u64,srtt_ns:u64,rttvar_ns:u64,recent_rtt_ns:u64,
}
impl AdaptiveTiming{
    fn new(bootstrap_rtt_ns:u64,bootstrap_rttvar_ns:u64)->Result<Self,DataError>{
        if bootstrap_rtt_ns==0||bootstrap_rttvar_ns==0{return Err(DataError::Malformed)}
        Ok(Self{samples:0,srtt_ns:bootstrap_rtt_ns,
            rttvar_ns:bootstrap_rttvar_ns,recent_rtt_ns:bootstrap_rtt_ns})
    }
    fn observe(&mut self,sample_ns:u64){
        let sample=sample_ns.max(1);
        if self.samples==0{
            self.srtt_ns=sample;
            self.rttvar_ns=(sample/4).clamp(1_000_000,20_000_000);
        }else{
            let delta=self.srtt_ns.abs_diff(sample);
            self.rttvar_ns=self.rttvar_ns.saturating_mul(3)
                .saturating_add(delta)/4;
            self.srtt_ns=self.srtt_ns.saturating_mul(7)
                .saturating_add(sample)/8;
        }
        self.recent_rtt_ns=sample;
        self.samples=self.samples.saturating_add(1);
    }
    fn snapshot(&self)->AdaptiveTimingSnapshot{
        let r=self.srtt_ns.max(self.recent_rtt_ns).max(1);
        let w=(r/32).clamp(MIN_REORDER_NS,MAX_REORDER_NS);
        let variation=self.rttvar_ns.saturating_mul(4)
            .max(w.saturating_mul(2)).max(MIN_PTO_VARIATION_NS);
        let pto=r.saturating_add(variation).saturating_add(FEEDBACK_ALLOWANCE_NS);
        // Single-repair policy: retain only long enough to launch the
        // unique repair opportunity. ACK/repair completion retires earlier.
        let cache=pto.saturating_add(100_000_000)
            .max(r.saturating_add(r/4).saturating_add(100_000_000))
            .min(MAX_RETAIN_NS);
        AdaptiveTimingSnapshot{samples:self.samples,srtt_ns:self.srtt_ns,
            rttvar_ns:self.rttvar_ns,recent_rtt_ns:self.recent_rtt_ns,
            reorder_window_ns:w,pto_ns:pto,cache_ns:cache}
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ReceiptPage {
    pub base_pn: RecordPn,
    pub bitmap: [u8; 32],
}
impl ReceiptPage {
    fn received(&self, pn: u64) -> bool {
        let offset = pn - self.base_pn.0;
        (self.bitmap[(offset / 8) as usize] & (1 << (offset % 8))) != 0
    }
}

/// Only the caller that has *successfully authenticated and opened* the
/// reverse-direction record may construct this type. This function does not
/// authenticate bytes: passing wire data directly is a trust-boundary bug.
/// M0 must bind the verified lane/epoch to the recovery lane at integration.
#[derive(Clone, Debug)]
pub struct AuthenticatedReceipt {
    lane: LaneKey,
    largest: RecordPn,
    report_seq: u32,
    pages: Vec<ReceiptPage>,
}
impl AuthenticatedReceipt {
    /// Lane is provided only after the M0-verified authenticated open.
    pub fn verified_lane(&self) -> LaneKey { self.lane }
    // Exact M2-011 read-only scoped maturity accessors. Never an AEAD
    // authenticator, allocator, or change to proven main RACK/PTO gates.
    pub fn largest_data_pn(&self)->RecordPn{self.largest}
    pub fn report_seq(&self)->u32{self.report_seq}
    pub fn pages(&self)->&[ReceiptPage]{&self.pages}
    pub fn after_authenticated_open(
        verified_lane: LaneKey,
        largest_data_pn: RecordPn,
        report_seq: u32,
        pages: Vec<ReceiptPage>,
    ) -> Result<Self, DataError> {
        if pages.len() > MAX_PAGES {
            return Err(DataError::Malformed);
        }
        let mut previous = None;
        for page in &pages {
            let base = page.base_pn.0;
            if base % PAGE_BITS != 0 || previous.is_some_and(|p| base <= p) {
                return Err(DataError::Malformed);
            }
            previous = Some(base);
            for (byte_index, byte) in page.bitmap.iter().enumerate() {
                if *byte == 0 { continue; }
                for bit in 0..8 {
                    if byte & (1 << bit) != 0
                        && base + (byte_index as u64) * 8 + bit > largest_data_pn.0
                    {
                        return Err(DataError::Malformed);
                    }
                }
            }
        }
        Ok(Self { lane: verified_lane, largest: largest_data_pn, report_seq, pages })
    }
}


/// Session policy pinned by M0 independently from the inbound receipt.
/// Pure data comparison only: NOT an authenticated session constructor.
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct ReceiptRouteScope {
    outbound_lane:LaneKey,
    reverse_lane:LaneKey,
    outbound_direction:crate::budget::WireDirection,
    tunnel_epoch:[u8;16],
    first_data_pn:RecordPn,
    last_data_pn:RecordPn,
    first_control_pn:RecordPn,
    last_control_pn:RecordPn,
}
impl ReceiptRouteScope {
    pub fn checked(
        outbound_lane:LaneKey,reverse_lane:LaneKey,
        outbound_direction:crate::budget::WireDirection,
        tunnel_epoch:[u8;16],
        data_pns:(RecordPn,RecordPn),control_pns:(RecordPn,RecordPn)
    )->Result<Self,DataError> {
        if outbound_lane.tunnel!=reverse_lane.tunnel ||
            tunnel_epoch==[0u8;16] || data_pns.0>data_pns.1 ||
            control_pns.0>control_pns.1 {
            return Err(DataError::Malformed);
        }
        Ok(Self {outbound_lane,reverse_lane,outbound_direction,tunnel_epoch,
            first_data_pn:data_pns.0,last_data_pn:data_pns.1,
            first_control_pn:control_pns.0,last_control_pn:control_pns.1})
    }
    pub fn outbound_lane(&self)->LaneKey {self.outbound_lane}
    pub fn outbound_direction(&self)->crate::budget::WireDirection {self.outbound_direction}
    pub fn contains_data_pn(&self,pn:RecordPn)->bool {
        pn>=self.first_data_pn && pn<=self.last_data_pn
    }
    fn reverse_direction(&self)->crate::budget::WireDirection {
        use crate::budget::WireDirection::{ClientToServer,ServerToClient};
        match self.outbound_direction {ClientToServer=>ServerToClient,ServerToClient=>ClientToServer}
    }
    fn matches_open(&self,opened:ReceiptOpenFacts)->bool {
        opened.verified_reverse_lane==self.reverse_lane &&
        opened.verified_reverse_direction==self.reverse_direction() &&
        opened.verified_tunnel_epoch==self.tunnel_epoch &&
        opened.control_record_pn>=self.first_control_pn &&
        opened.control_record_pn<=self.last_control_pn
    }
}
/// Caller-supplied observations from M0 after AEAD, PN replay and trusted
/// session lookup; plain public values cannot themselves establish trust.
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct ReceiptOpenFacts {
    pub verified_reverse_lane:LaneKey,
    pub verified_reverse_direction:crate::budget::WireDirection,
    pub verified_tunnel_epoch:[u8;16],
    pub control_record_pn:RecordPn,
}
/// Parsed authenticated receipt bound to the independent pinned route.
/// This type checks scope but performs NO cryptographic verification.
pub struct ScopedAuthenticatedReceipt {
    route:ReceiptRouteScope,
    receipt:AuthenticatedReceipt,
}
impl ScopedAuthenticatedReceipt {
    pub fn checked_after_open(
        pinned:ReceiptRouteScope,opened:ReceiptOpenFacts,
        largest_data_pn:RecordPn,report_seq:u32,pages:Vec<ReceiptPage>
    )->Result<Self,DataError> {
        if !pinned.matches_open(opened) || !pinned.contains_data_pn(largest_data_pn) {
            return Err(DataError::Stale);
        }
        // Positive bitmap bits outside the independent session PN scope
        // cannot retire a shadow even when largest_data_pn is valid.
        for page in &pages {
            for (byte_index,byte) in page.bitmap.iter().enumerate() {
                for bit in 0..8 {
                    if (*byte & (1u8<<bit))!=0 {
                        let pn=page.base_pn.0.checked_add((byte_index*8+bit) as u64)
                            .ok_or(DataError::Malformed)?;
                        if !pinned.contains_data_pn(RecordPn(pn)) {
                            return Err(DataError::Stale);
                        }
                    }
                }
            }
        }
        let receipt=AuthenticatedReceipt::after_authenticated_open(
            pinned.outbound_lane,largest_data_pn,report_seq,pages)?;
        Ok(Self {route:pinned,receipt})
    }
    pub fn route(&self)->ReceiptRouteScope {self.route}
    pub fn receipt(&self)->&AuthenticatedReceipt {&self.receipt}
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ReleaseReason {
    ReceivedByPeer,
    HardExpired,
}
pub struct Release<H: FrozenRecordHandle> {
    pub pn: RecordPn,
    pub reason: ReleaseReason,
    pub frozen: H,
}
/// This is the *same* frozen ciphertext handle and the *same* PN as initial
/// send; consumer must preflight before dispatch. No seal/PN API exists here.
pub struct RepairCandidate<H: FrozenRecordHandle> {
    pn: RecordPn,
    origin: BufferOrigin,
    retry_epoch: u32,
    // Actual network repair attempts already consumed before THIS candidate.
    // This is owner state, not caller input; budget uses it only to prioritize
    // the first repair while preflight rechecks the same entry stage.
    repair_attempt_stage: u8,
    dispatch_by: MonoNs,
    frozen: H,
}
impl<H: FrozenRecordHandle> RepairCandidate<H> {
    pub fn pn(&self) -> RecordPn { self.pn }
    pub fn retry_epoch(&self) -> u32 { self.retry_epoch }
    pub fn repair_attempt_stage(&self) -> u8 { self.repair_attempt_stage }
    pub fn dispatch_by(&self) -> MonoNs { self.dispatch_by }
    pub fn frozen(&self) -> &H { &self.frozen }
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RepairSendResult {
    Accepted,
    Uncertain, // consumes an attempt; never treated as definitely not sent
    NotSent,
}
pub struct PollResult<H: FrozenRecordHandle> {
    pub releases: Vec<Release<H>>,
    pub candidates: Vec<RepairCandidate<H>>,
    pub next_deadline: Option<MonoNs>,
}
#[derive(Clone, Copy, Debug)]
pub struct ReceiptConfig {
    pub max_shadow_entries: usize,
    pub pto_ns: u64,
    pub reorder_window_ns: u64,
}
struct Queued {
    epoch: u32,
    until: MonoNs,
    started: MonoNs,
}
struct Entry<H: FrozenRecordHandle> {
    frozen: H,
    last_sent: MonoNs,
    hard_expiry: MonoNs,
    repair_attempts: u8,
    retry_epoch: u32,
    missing_reported: bool,
    negative_since: Option<MonoNs>,
    queued: Option<Queued>,
    indexed_wake: Option<u64>,
}
#[derive(Clone, Copy)]
struct Witness {
    pn: RecordPn,
    sent_at: MonoNs,
}
pub struct ReceiptState<H: FrozenRecordHandle> {
    lane: LaneKey,
    config: ReceiptConfig,
    entries: BTreeMap<RecordPn, Entry<H>>,
    // One exact index node per shadow; no lazy tombstone pile after ACK/stop.
    expiry_index: BTreeSet<(u64, RecordPn)>,
    wake_index: BTreeSet<(u64, RecordPn)>,
    #[cfg(test)]
    last_timer_index_pops: usize,
    last_report_seq: Option<u32>,
    witnesses: Vec<Witness>, // latest three distinct, verified data sends
    rack_ack_ns: Option<u64>,
    adaptive:Option<AdaptiveTiming>,
    opportunistic_v3:bool,
    diagnostics:ReceiptDiagnosticSnapshot,
}
fn serial_newer(seq: u32, prev: u32) -> bool {
    let d = seq.wrapping_sub(prev);
    d != 0 && d < (1 << 31)
}
impl<H: FrozenRecordHandle> ReceiptState<H> {
    /// Owner identity including tunnel and lane generation.
    pub fn lane(&self) -> LaneKey { self.lane }
    pub fn new(lane: LaneKey, config: ReceiptConfig) -> Result<Self, DataError> {
        if config.max_shadow_entries == 0 || config.pto_ns == 0 {
            return Err(DataError::Malformed);
        }
        Ok(Self {
            lane, config, entries: BTreeMap::new(),
            expiry_index: BTreeSet::new(), wake_index: BTreeSet::new(),
            #[cfg(test)]
            last_timer_index_pops: 0,
            last_report_seq: None,
            witnesses: Vec::with_capacity(3), rack_ack_ns: None,adaptive:None,
            opportunistic_v3:false,diagnostics:ReceiptDiagnosticSnapshot::default(),
        })
    }
    pub fn enable_adaptive_timing(&mut self,bootstrap_rtt_ns:u64,
        bootstrap_rttvar_ns:u64)->Result<(),DataError>{
        if !self.entries.is_empty(){return Err(DataError::Malformed)}
        self.adaptive=Some(AdaptiveTiming::new(bootstrap_rtt_ns,bootstrap_rttvar_ns)?);
        Ok(())
    }
    /// Opt-in v3 only; historical v2 component tests retain their old timers.
    pub fn enable_opportunistic_v3(&mut self)->Result<(),DataError>{
        if !self.entries.is_empty(){return Err(DataError::Malformed)}
        self.opportunistic_v3=true;
        Ok(())
    }
    fn v3_guard_ns(&self)->u64{
        self.adaptive.map_or(V3_GAP_MIN_NS,|x|
            x.rttvar_ns.saturating_mul(4).clamp(V3_GAP_MIN_NS,V3_GAP_MAX_NS))
    }
    pub fn timing_snapshot(&self)->Option<AdaptiveTimingSnapshot>{
        self.adaptive.map(|x|x.snapshot())
    }
    pub fn diagnostic_snapshot(&self)->ReceiptDiagnosticSnapshot{
        self.diagnostics
    }
    fn effective_pto_ns(&self)->u64{
        self.adaptive.map_or(self.config.pto_ns,|x|x.snapshot().pto_ns)
    }
    fn effective_reorder_ns(&self)->u64{
        self.adaptive.map_or(self.config.reorder_window_ns,
            |x|x.snapshot().reorder_window_ns)
    }
    pub fn on_sent_adaptive(&mut self,frozen:H,at:MonoNs)->Result<(),DataError>{
        let Some(t)=self.timing_snapshot()else{return Err(DataError::Malformed)};
        let cache=if self.opportunistic_v3 {
            let r=t.srtt_ns.max(t.recent_rtt_ns);
            r.saturating_add(r/2).saturating_add(t.rttvar_ns.saturating_mul(4))
                .saturating_add(100_000_000).clamp(250_000_000,MAX_RETAIN_NS)
        }else{t.cache_ns};
        self.on_sent(frozen,at,MonoNs(at.0.saturating_add(cache)))
    }

    /// Register only an already frozen, actually submitted data record.
    /// Burned/control PN have no entry and therefore cannot become loss.
    pub fn on_sent(&mut self, frozen: H, at: MonoNs, hard_expiry: MonoNs)
        -> Result<(), DataError>
    {
        let meta = frozen.metadata();
        if meta.lane != self.lane || hard_expiry <= at { return Err(DataError::Malformed); }
        if self.entries.contains_key(&meta.pn) { return Err(DataError::Duplicate); }
        if self.entries.len() == self.config.max_shadow_entries {
            return Err(DataError::NoCapacity(LimitedResource::ShadowBytes));
        }
        self.entries.insert(meta.pn, Entry {
            frozen, last_sent: at, hard_expiry, repair_attempts: 0,
            retry_epoch: 0, missing_reported: false,negative_since:None,queued: None,
            indexed_wake: None,
        });
        self.expiry_index.insert((hard_expiry.0, meta.pn));
        self.refresh_wake(meta.pn);
        Ok(())
    }


    /// Index only the next owned wake event; hard expiry is independent.
    /// This key is always removed on ACK, expiry or a state transition.
    fn wake_at(&self, e: &Entry<H>) -> Option<u64> {
        if let Some(q) = &e.queued { Some(q.until.0) }
        else if e.repair_attempts < OUTER_REPAIR_ATTEMPT_LIMIT as u8
            && e.retry_epoch < u32::MAX
            && (!self.opportunistic_v3 || e.negative_since.is_some()) {
            Some(self.due_at(e).0)
        } else { None }
    }
    fn refresh_wake(&mut self, pn: RecordPn) {
        let old = self.entries.get(&pn).expect("indexed entry").indexed_wake;
        if let Some(at) = old { assert!(self.wake_index.remove(&(at, pn))); }
        let next = self.wake_at(self.entries.get(&pn).expect("indexed entry"));
        self.entries.get_mut(&pn).expect("indexed entry").indexed_wake=next;
        if let Some(at) = next { assert!(self.wake_index.insert((at, pn))); }
    }
    fn remove_indexes(&mut self, pn: RecordPn, entry: &Entry<H>, expiry_popped: bool) {
        if !expiry_popped { assert!(self.expiry_index.remove(&(entry.hard_expiry.0,pn))); }
        if let Some(at)=entry.indexed_wake {
            assert!(self.wake_index.remove(&(at,pn)));
        }
    }
    /// Positive bitmap bits may release once even from an old report.
    /// Only new report_seq can establish negative evidence or RTT witnesses.
    /// Unreported pages, PN > largest and absent/control/burned PN do nothing.
    pub fn on_receipt(&mut self, receipt: &AuthenticatedReceipt, now: MonoNs)
        -> Result<Vec<Release<H>>, DataError>
    {
        if receipt.lane != self.lane { return Err(DataError::Stale); }
        let fresh = self.last_report_seq.is_none_or(|v| serial_newer(receipt.report_seq, v));
        if fresh { self.last_report_seq = Some(receipt.report_seq); }
        let mut releases = Vec::new();
        let mut dirty = Vec::new();
        let mut timing_sample=None::<u64>;
        // Only a later verified positive DATA PN within a fresh receipt can
        // witness a missing DATA bit. Unknown/stale feedback never arms repair.
        let newest_positive=if fresh && self.opportunistic_v3 {
            receipt.pages.iter().flat_map(|page|{
                let base=page.base_pn.0;
                (0..256).filter_map(move |bit|{
                    let pn=base+bit;
                    (pn<=receipt.largest.0 && page.received(pn)).then_some(pn)
                })
            }).max()
        }else{None};
        for page in &receipt.pages {
            let base = page.base_pn.0;
            if base > receipt.largest.0 { continue; }
            let end = base.saturating_add(255).min(receipt.largest.0);
            for pn in base..=end {
                let key=RecordPn(pn);
                if page.received(pn) {
                    if let Some(entry)=self.entries.remove(&key) {
                        self.remove_indexes(key,&entry,false);
                        let within_lifetime=now<entry.hard_expiry;
                        let bucket=usize::from(entry.repair_attempts.min(2));
                        if within_lifetime{
                            match bucket{
                                0=>self.diagnostics.acked_attempt0=self.diagnostics.acked_attempt0.saturating_add(1),
                                1=>self.diagnostics.acked_attempt1=self.diagnostics.acked_attempt1.saturating_add(1),
                                _=>self.diagnostics.acked_attempt2=self.diagnostics.acked_attempt2.saturating_add(1),
                            }
                        }else{
                            match bucket{
                                0=>self.diagnostics.expired_attempt0=self.diagnostics.expired_attempt0.saturating_add(1),
                                1=>self.diagnostics.expired_attempt1=self.diagnostics.expired_attempt1.saturating_add(1),
                                _=>self.diagnostics.expired_attempt2=self.diagnostics.expired_attempt2.saturating_add(1),
                            }
                            self.diagnostics.late_positive_expired=
                                self.diagnostics.late_positive_expired.saturating_add(1);
                        }
                        if fresh && within_lifetime && entry.repair_attempts==0 {
                            let sample=now.elapsed_since(entry.last_sent).max(1);
                            timing_sample=Some(timing_sample.map_or(sample,|old|old.min(sample)));
                            self.observe_witness(Witness {pn:key,sent_at:entry.last_sent});
                        }
                        releases.push(Release {
                            pn:key,
                            reason:if within_lifetime {
                                ReleaseReason::ReceivedByPeer
                            } else {ReleaseReason::HardExpired},
                            frozen:entry.frozen
                        });
                    }
                } else if fresh {
                    if let Some(e)=self.entries.get_mut(&key) {
                        if now<e.hard_expiry && !e.missing_reported
                            && (!self.opportunistic_v3 ||
                                newest_positive.is_some_and(|later|later>pn)) {
                            e.missing_reported=true;
                            e.negative_since=Some(now);
                            dirty.push(key);
                        }
                    }
                }
            }
        }
        if let Some(sample)=timing_sample{
            self.rack_ack_ns=Some(sample);
            if let Some(adaptive)=self.adaptive.as_mut(){adaptive.observe(sample);}
        }
        // Never scan every shadow on an ACK/RTT update. Re-index only
        // entries whose loss evidence changed in this authenticated report.
        for key in dirty {self.refresh_wake(key);}
        Ok(releases)
    }

    fn observe_witness(&mut self, witness: Witness) {
        if self.witnesses.iter().any(|w| w.pn == witness.pn) { return; }
        self.witnesses.push(witness);
        self.witnesses.sort_by_key(|w| (w.sent_at, w.pn));
        if self.witnesses.len() > 3 { self.witnesses.remove(0); }
    }

    fn due_at(&self, entry: &Entry<H>) -> MonoNs {
        if self.opportunistic_v3 {
            let Some(negative)=entry.negative_since else {
                return entry.hard_expiry;
            };
            let srtt=self.adaptive.map_or(self.config.pto_ns,|x|
                x.srtt_ns.max(x.recent_rtt_ns));
            let guard=self.v3_guard_ns();
            return MonoNs(entry.last_sent.0.saturating_add(srtt)
                .saturating_add(guard).saturating_add(V3_FEEDBACK_MARGIN_NS)
                .max(negative.0.saturating_add(guard)));
        }
        let pto = entry.last_sent.0.saturating_add(self.effective_pto_ns());
        let mut due = pto;
        if entry.repair_attempts == 0 && entry.missing_reported
            && self.witnesses.iter().filter(|w| w.sent_at > entry.last_sent).count() == 3
        {
            if let Some(rack_ack) = self.rack_ack_ns {
                due = due.min(entry.last_sent.0.saturating_add(rack_ack)
                    .saturating_add(self.effective_reorder_ns()));
            }
        }
        MonoNs(due)
    }

    /// Called with an injected monotonic clock. At most 32 expiry/queue
    /// events and at most 32 new repair candidates are handled per owner turn.
    /// There is no full-table scan and no second network-repair timer.
    pub fn on_timer(&mut self, now: MonoNs) -> PollResult<H> {
        let mut releases=Vec::new();
        let mut candidates=Vec::with_capacity(MAX_POLL_CANDIDATES);
        #[cfg(test)]
        { self.last_timer_index_pops=0; }

        let mut owner_events=0usize;
        while owner_events<MAX_POLL_CANDIDATES {
            let Some(&(expiry,pn))=self.expiry_index.first() else {break;};
            if expiry>now.0 {break;}
            self.expiry_index.pop_first();
            let entry=self.entries.remove(&pn).expect("expiry index synchronized");
            self.remove_indexes(pn,&entry,true);
            self.diagnostics.expired_attempt0=
                self.diagnostics.expired_attempt0.saturating_add(1);
            owner_events+=1;
            #[cfg(test)]
            { self.last_timer_index_pops+=1; }
            releases.push(Release {
                pn,reason:ReleaseReason::HardExpired,frozen:entry.frozen
            });
        }

        while candidates.len()<MAX_POLL_CANDIDATES
            && owner_events<MAX_POLL_CANDIDATES
        {
            let Some(&(wake,pn))=self.wake_index.first() else {break;};
            if wake>now.0 {break;}
            owner_events+=1;
            self.wake_index.pop_first();
            #[cfg(test)]
            { self.last_timer_index_pops+=1; }

            let timed_out={
                let entry=self.entries.get_mut(&pn).expect("wake index synchronized");
                assert_eq!(entry.indexed_wake,Some(wake));
                entry.indexed_wake=None;
                entry.queued.as_ref().and_then(|q|
                    (now>=q.until).then_some(q.started))
            };
            if let Some(started)=timed_out {
                let entry=self.entries.remove(&pn).expect("queued entry present");
                assert!(self.expiry_index.remove(&(entry.hard_expiry.0,pn)));
                self.diagnostics.repair_abandoned_retired=
                    self.diagnostics.repair_abandoned_retired.saturating_add(1);
                self.diagnostics.max_queue_age_ns=self.diagnostics.max_queue_age_ns
                    .max(now.elapsed_since(started));
                continue;
            }

            {
                let entry=self.entries.get_mut(&pn).expect("wake entry present");
                assert!(entry.queued.is_none()
                    && entry.repair_attempts<OUTER_REPAIR_ATTEMPT_LIMIT as u8);
                entry.retry_epoch=entry.retry_epoch.checked_add(1)
                    .expect("queue generation exhausted before PN");
                let until=MonoNs(entry.hard_expiry.0.min(
                    now.0.saturating_add(QUEUE_LIFETIME_NS)));
                entry.queued=Some(Queued {
                    epoch:entry.retry_epoch,until,started:now
                });
                candidates.push(RepairCandidate {
                    pn,origin:entry.frozen.origin(),retry_epoch:entry.retry_epoch,
                    repair_attempt_stage:0,dispatch_by:until,
                    frozen:entry.frozen.clone()
                });
            }
            self.diagnostics.candidate_first=
                self.diagnostics.candidate_first.saturating_add(1);
            self.refresh_wake(pn);
        }
        PollResult {releases,candidates,next_deadline:self.next_deadline()}
    }

    /// Prevent ACK-vs-dispatch races. Engine must call this immediately before
    /// passing the original frozen handle to the driver (and then record the
    /// actual Accepted/NotSent/Uncertain result).
    pub fn preflight(&self, candidate: &RepairCandidate<H>, now: MonoNs) -> bool {
        self.entries.get(&candidate.pn).is_some_and(|e| {
            e.frozen.origin() == candidate.origin
                && e.queued.as_ref().is_some_and(|q|
                    q.epoch == candidate.retry_epoch
                        && q.until == candidate.dispatch_by
                        && now <= q.until && now < e.hard_expiry)
                && candidate.repair_attempt_stage == 0
                && e.repair_attempts < OUTER_REPAIR_ATTEMPT_LIMIT as u8
        })
    }

    /// Hard quota/pressure denial retires only the repair payload shadow.
    /// It is NOT an ACK and does not alter independent receipt/replay history.
    pub fn on_quota_exhausted(&mut self,candidate:&RepairCandidate<H>,
        now:MonoNs)->Result<(),DataError>{
        if !self.preflight(candidate,now){return Err(DataError::Stale)}
        let entry=self.entries.remove(&candidate.pn).expect("preflight verified");
        self.remove_indexes(candidate.pn,&entry,false);
        let started=entry.queued.as_ref().map_or(now,|q|q.started);
        self.diagnostics.repair_abandoned_retired=
            self.diagnostics.repair_abandoned_retired.saturating_add(1);
        self.diagnostics.max_queue_age_ns=self.diagnostics.max_queue_age_ns
            .max(now.elapsed_since(started));
        Ok(())
    }

    /// Completion of the unique network repair opportunity is terminal for
    /// payload retention. Accepted and Uncertain both consume that opportunity;
    /// NotSent abandons it in this minimal product path.
    pub fn on_send_result(&mut self, candidate: &RepairCandidate<H>,
        result: RepairSendResult, now: MonoNs) -> Result<(), DataError>
    {
        if !self.preflight(candidate, now) { return Err(DataError::Stale); }
        let entry=self.entries.remove(&candidate.pn).expect("preflight verified");
        self.remove_indexes(candidate.pn,&entry,false);
        let started=entry.queued.as_ref().map_or(now,|q|q.started);
        self.diagnostics.max_queue_age_ns=self.diagnostics.max_queue_age_ns
            .max(now.elapsed_since(started));
        match result {
            RepairSendResult::Accepted=>{
                self.diagnostics.repair_accepted_retired=
                    self.diagnostics.repair_accepted_retired.saturating_add(1);
            }
            RepairSendResult::Uncertain=>{
                self.diagnostics.repair_uncertain_retired=
                    self.diagnostics.repair_uncertain_retired.saturating_add(1);
            }
            RepairSendResult::NotSent=>{
                self.diagnostics.repair_abandoned_retired=
                    self.diagnostics.repair_abandoned_retired.saturating_add(1);
            }
        }
        Ok(())
    }

    pub fn next_deadline(&self) -> Option<MonoNs> {
        let hard=self.expiry_index.first().map(|&(at,_)|at);
        let wake=self.wake_index.first().map(|&(at,_)|at);
        hard.into_iter().chain(wake).min().map(MonoNs)
    }
    #[cfg(test)]
    pub(crate) fn last_timer_index_pops(&self)->usize {
        self.last_timer_index_pops
    }
    pub fn outstanding(&self) -> usize { self.entries.len() }
    pub fn is_opportunistic_v3(&self)->bool{self.opportunistic_v3}
    pub fn policy_limits(&self)->(u64,usize,u64){
        (OUTER_REPAIR_ATTEMPT_LIMIT,self.config.max_shadow_entries,MAX_RETAIN_NS)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;
    use wbd_types::buffer_contract::FrozenMetadata;
    use wbd_types::{BufferKey, SeqOffset, TunnelKey};

    #[derive(Clone)]
    struct FakeFrozen {
        bytes: Arc<Vec<u8>>,
        origin: BufferOrigin,
        metadata: FrozenMetadata,
    }
    impl FrozenRecordHandle for FakeFrozen {
        fn origin(&self) -> BufferOrigin { self.origin }
        fn metadata(&self) -> FrozenMetadata { self.metadata }
        fn bytes(&self) -> &[u8] { self.bytes.as_slice() }
    }
    fn lane() -> LaneKey {
        LaneKey { tunnel: TunnelKey { slot: 1, generation: 3 }, slot: 2, generation: 4 }
    }
    fn frozen(pn: u64) -> FakeFrozen {
        FakeFrozen {
            bytes: Arc::new(vec![7, 8, 9, 10]),
            origin: BufferOrigin { owner_arena: 1,
                key: BufferKey { slot: pn as u32, generation: 7 } },
            metadata: FrozenMetadata { lane: lane(), pn: RecordPn(pn),
                seq: SeqOffset(pn * 20), carrier_snapshot: 99 },
        }
    }
    fn state(max: usize, pto: u64) -> ReceiptState<FakeFrozen> {
        ReceiptState::new(lane(), ReceiptConfig {
            max_shadow_entries: max, pto_ns: pto, reorder_window_ns: 5,
        }).unwrap()
    }
    fn page(base: u64, set: &[u64]) -> ReceiptPage {
        let mut bitmap = [0; 32];
        for pn in set {
            let off = pn - base;
            bitmap[(off / 8) as usize] |= 1 << (off % 8);
        }
        ReceiptPage { base_pn: RecordPn(base), bitmap }
    }
    fn receipt(seq: u32, largest: u64, pages: Vec<ReceiptPage>) -> AuthenticatedReceipt {
        AuthenticatedReceipt::after_authenticated_open(lane(), RecordPn(largest), seq, pages).unwrap()
    }
    fn add(s: &mut ReceiptState<FakeFrozen>, pn: u64, at: u64, expiry: u64) {
        s.on_sent(frozen(pn), MonoNs(at), MonoNs(expiry)).unwrap();
    }

    #[test]
    fn r2_adaptive_authenticated_rtt_drives_single_repair_retain_without_unbounded_retry(){
        let mut s=state(8,80_000_000);
        s.enable_adaptive_timing(650_000_000,20_000_000).unwrap();
        let boot=s.timing_snapshot().unwrap();
        assert_eq!((boot.reorder_window_ns,boot.pto_ns,boot.cache_ns),
            (20_000_000,740_000_000,912_500_000));
        s.on_sent_adaptive(frozen(1),MonoNs(0)).unwrap();
        assert_eq!(s.on_receipt(&receipt(1,1,vec![page(0,&[1])]),
            MonoNs(400_000_000)).unwrap().len(),1);
        let learned=s.timing_snapshot().unwrap();
        assert_eq!((learned.srtt_ns,learned.rttvar_ns,learned.reorder_window_ns,
            learned.pto_ns,learned.cache_ns),
            (400_000_000,20_000_000,12_500_000,490_000_000,600_000_000));
        s.on_sent_adaptive(frozen(2),MonoNs(410_000_000)).unwrap();
        assert_eq!(s.next_deadline(),Some(MonoNs(900_000_000)));
        let one=s.on_timer(MonoNs(900_000_000)).candidates.remove(0);
        s.on_send_result(&one,RepairSendResult::Accepted,MonoNs(900_000_000)).unwrap();
        assert_eq!(s.outstanding(),0);
        assert_eq!(s.next_deadline(),None);
        assert!(s.on_timer(MonoNs(1_500_000_000)).candidates.is_empty());
        assert!(s.on_receipt(&receipt(2,2,vec![page(0,&[2])]),
            MonoNs(1_000_000_000)).unwrap().is_empty());
        let d=s.diagnostic_snapshot();
        assert_eq!(d.repair_accepted_retired,1);
        assert_eq!(d.candidate_retry,0);
    }

    #[test]
    fn r2_single_repair_completion_release_race_is_idempotent(){
        let mut s=state(8,10);
        let original=frozen(7);
        let shared=original.bytes.clone();
        s.on_sent(original,MonoNs(0),MonoNs(100)).unwrap();
        let c=s.on_timer(MonoNs(10)).candidates.remove(0);
        assert!(s.preflight(&c,MonoNs(10)));
        s.on_send_result(&c,RepairSendResult::Uncertain,MonoNs(11)).unwrap();
        assert_eq!(s.outstanding(),0);
        assert!(s.on_timer(MonoNs(100)).releases.is_empty());
        assert!(s.on_receipt(&receipt(1,7,vec![page(0,&[7])]),MonoNs(20))
            .unwrap().is_empty());
        assert_eq!(s.on_send_result(&c,RepairSendResult::Accepted,MonoNs(12)),
            Err(DataError::Stale));
        drop(c);
        assert_eq!(Arc::strong_count(&shared),1);
        let d=s.diagnostic_snapshot();
        assert_eq!(d.repair_uncertain_retired,1);
        assert_eq!(d.repair_accepted_retired,0);
        assert_eq!(d.candidate_retry,0);
    }

    #[test]
    fn r2_single_repair_diagnostics_no_second_network_attempt(){
        let mut s=state(8,10);
        add(&mut s,1,0,100);
        assert_eq!(s.on_receipt(&receipt(1,1,vec![page(0,&[1])]),MonoNs(5))
            .unwrap().len(),1);
        add(&mut s,2,100,200);
        let one=s.on_timer(MonoNs(110)).candidates.remove(0);
        s.on_send_result(&one,RepairSendResult::Accepted,MonoNs(110)).unwrap();
        add(&mut s,3,200,205);
        assert_eq!(s.on_timer(MonoNs(205)).releases.len(),1);
        let d=s.diagnostic_snapshot();
        assert_eq!((d.candidate_first,d.candidate_retry),(1,0));
        assert_eq!((d.acked_attempt0,d.acked_attempt1,d.acked_attempt2),(1,0,0));
        assert_eq!((d.expired_attempt0,d.expired_attempt1,d.expired_attempt2),(1,0,0));
        assert_eq!(d.repair_accepted_retired,1);
    }

    #[test]
    fn r2_pn_holes_control_burned_and_unreported_page_never_invent_loss() {
        let mut s = state(16, 1_000);
        for (pn, time) in [(10, 0), (14, 1), (18, 2), (19, 3), (20, 4), (300, 5)] {
            add(&mut s, pn, time, 2_000);
        }
        // PN11..13,15..17 are burned/control; page 256 is unreported.
        let report = receipt(1, 300, vec![page(0, &[18, 19, 20])]);
        let released = s.on_receipt(&report, MonoNs(100)).unwrap();
        assert_eq!(released.len(), 3);
        assert!(released.iter().all(|r| r.reason == ReleaseReason::ReceivedByPeer));
        assert!(s.on_timer(MonoNs(100)).candidates.is_empty()); // R_ack + W not reached
        let c = s.on_timer(MonoNs(102)).candidates;
        assert_eq!(c.iter().map(|c| c.pn.0).collect::<Vec<_>>(), vec![10, 14]);
        assert!(!c.iter().any(|c| c.pn.0 == 300));
    }

    #[test]
    fn r2_duplicate_old_report_late_positive_and_serial_wrap_release_once() {
        let mut s = state(8, 1_000);
        add(&mut s, 5, 1, 500);
        add(&mut s, 6, 2, 500);
        s.on_receipt(&receipt(u32::MAX, 6, vec![page(0, &[])]), MonoNs(10)).unwrap();
        assert!(s.on_receipt(&receipt(u32::MAX, 6, vec![page(0, &[5])]), MonoNs(11))
            .unwrap().iter().any(|r| r.pn == RecordPn(5)));
        assert!(s.on_receipt(&receipt(u32::MAX, 6, vec![page(0, &[5])]), MonoNs(12))
            .unwrap().is_empty());
        // An older bitmap can still release 6, but cannot introduce witnesses.
        let done = s.on_receipt(&receipt(u32::MAX - 1, 6, vec![page(0, &[6])]),
            MonoNs(13)).unwrap();
        assert_eq!(done.len(), 1);
        assert!(s.witnesses.is_empty());
        assert_eq!(s.outstanding(), 0);
        assert!(serial_newer(0, u32::MAX));
        assert!(!serial_newer(u32::MAX, 0));
    }

    #[test]
    fn r2_hard_expiry_precedes_late_ack_and_releases_once() {
        let mut s = state(3, 10);
        add(&mut s, 1, 1, 20);
        assert_eq!(s.on_receipt(&receipt(1, 1, vec![page(0, &[1])]), MonoNs(20))
            .unwrap()[0].reason, ReleaseReason::HardExpired);
        assert!(s.on_timer(MonoNs(21)).releases.is_empty());
        add(&mut s, 2, 1, 15);
        let poll = s.on_timer(MonoNs(15));
        assert_eq!(poll.releases.len(), 1);
        assert_eq!(poll.releases[0].reason, ReleaseReason::HardExpired);
        assert_eq!(s.outstanding(), 0);
    }

    #[test]
    fn r2_uncertain_consumes_unique_repair_and_releases_shadow(){
        let mut s=state(2,100);
        let original=frozen(8);
        let shared=original.bytes.clone();
        s.on_sent(original,MonoNs(0),MonoNs(500)).unwrap();
        let first=s.on_timer(MonoNs(100)).candidates.remove(0);
        assert!(Arc::ptr_eq(&first.frozen.bytes,&shared));
        s.on_send_result(&first,RepairSendResult::Uncertain,MonoNs(100)).unwrap();
        assert_eq!(s.outstanding(),0);
        assert!(s.on_timer(MonoNs(500)).releases.is_empty());
        assert_eq!(s.on_send_result(&first,RepairSendResult::Accepted,MonoNs(101)),
            Err(DataError::Stale));
        drop(first);
        assert_eq!(Arc::strong_count(&shared),1);
    }

    #[test]
    fn r2_ack_between_candidate_and_dispatch_cancels_repair() {
        let mut s = state(2, 10);
        add(&mut s, 2, 0, 100);
        let c = s.on_timer(MonoNs(10)).candidates.remove(0);
        assert_eq!(s.on_receipt(&receipt(1, 2, vec![page(0, &[2])]), MonoNs(11))
            .unwrap().len(), 1);
        assert!(!s.preflight(&c, MonoNs(12)));
        assert_eq!(s.on_send_result(&c, RepairSendResult::Accepted, MonoNs(12)),
            Err(DataError::Stale));
    }

    #[test]
    fn r2_quota_exhausted_releases_repair_shadow_without_faking_ack(){
        let mut s=state(2,10);
        add(&mut s,4,0,100);
        let c=s.on_timer(MonoNs(10)).candidates.remove(0);
        s.on_quota_exhausted(&c,MonoNs(10)).unwrap();
        assert_eq!(s.outstanding(),0);
        assert!(s.on_timer(MonoNs(99)).candidates.is_empty());
        assert!(s.on_receipt(&receipt(1,4,vec![page(0,&[4])]),MonoNs(20))
            .unwrap().is_empty());
        assert_eq!(s.diagnostic_snapshot().repair_abandoned_retired,1);
    }

    #[test]
    fn r2_queue_timeout_retires_payload_without_second_timer(){
        let mut s=state(2,10);
        add(&mut s,4,0,100_000_000);
        let old=s.on_timer(MonoNs(10)).candidates.remove(0);
        assert!(s.preflight(&old,MonoNs(20_000_009)));
        assert!(!s.preflight(&old,MonoNs(20_000_011)));
        assert!(s.on_timer(MonoNs(20_000_011)).candidates.is_empty());
        assert_eq!(s.outstanding(),0);
        assert_eq!(s.on_send_result(&old,RepairSendResult::Accepted,
            MonoNs(20_000_011)),Err(DataError::Stale));
        assert_eq!(s.diagnostic_snapshot().repair_abandoned_retired,1);
    }

    #[test]
    fn r2_invalid_bits_scope_and_stale_feedback_cannot_release_or_create_gap() {
        assert_eq!(AuthenticatedReceipt::after_authenticated_open(
            lane(), RecordPn(3), 1, vec![page(0, &[4])]).unwrap_err(), DataError::Malformed);
        assert_eq!(AuthenticatedReceipt::after_authenticated_open(
            lane(), RecordPn(300), 1, vec![page(256, &[]), page(0, &[])])
            .unwrap_err(), DataError::Malformed);
        let mut s = state(4, 100);
        add(&mut s, 1, 0, 1_000);
        let different = LaneKey { slot: 99, ..lane() };
        let wrong = AuthenticatedReceipt::after_authenticated_open(
            different, RecordPn(1), 1, vec![page(0, &[1])]).unwrap();
        assert_eq!(s.on_receipt(&wrong, MonoNs(5)).err(), Some(DataError::Stale));
        assert_eq!(s.outstanding(), 1);
        s.on_receipt(&receipt(10, 1, vec![]), MonoNs(6)).unwrap();
        s.on_receipt(&receipt(9, 1, vec![page(0, &[])]), MonoNs(7)).unwrap();
        assert!(!s.entries.get(&RecordPn(1)).unwrap().missing_reported);
    }

    #[test]
    fn r2_bounded_shadow_and_32_candidates_per_tick_failed_send_no_charge() {
        let mut s = state(40, 10);
        for pn in 0..40 { add(&mut s, pn, 0, 100); }
        assert!(matches!(s.on_sent(frozen(40), MonoNs(0), MonoNs(100)),
            Err(DataError::NoCapacity(LimitedResource::ShadowBytes))));
        let first = s.on_timer(MonoNs(10));
        assert_eq!(first.candidates.len(), 32);
        let remaining = s.on_timer(MonoNs(10));
        assert_eq!(remaining.candidates.len(), 8);
        let c = &first.candidates[0];
        s.on_send_result(c, RepairSendResult::NotSent, MonoNs(10)).unwrap();
        assert!(s.on_timer(MonoNs(10)).candidates.is_empty());
        let mut expired=0usize;
        while s.outstanding()!=0 {
            let p=s.on_timer(MonoNs(100));
            assert!(p.releases.len()<=32);
            expired+=p.releases.len();
        }
        assert_eq!(expired,39);
    }

    #[test]
    fn r2_burst_indexed_0_1_32_33_deadlines_without_table_rescan() {
        let mut empty=state(1,10);
        assert_eq!(empty.next_deadline(),None);
        assert!(empty.on_timer(MonoNs(10)).candidates.is_empty());
        assert_eq!(empty.last_timer_index_pops(),0);
        add(&mut empty,1,0,100);
        assert_eq!(empty.next_deadline(),Some(MonoNs(10)));
        assert_eq!(empty.on_timer(MonoNs(9)).candidates.len(),0);
        assert_eq!(empty.last_timer_index_pops(),0);
        let c=empty.on_timer(MonoNs(10)).candidates;
        assert_eq!(c.len(),1);
        assert_eq!(empty.last_timer_index_pops(),1);
        assert!(empty.preflight(&c[0],MonoNs(10)));
        assert!(empty.on_timer(MonoNs(10)).candidates.is_empty());
        assert_eq!(empty.last_timer_index_pops(),0);
        let mut full=state(33,10);
        for pn in 0..33 {add(&mut full,pn,0,100);}
        assert_eq!(full.on_timer(MonoNs(10)).candidates.len(),32);
        assert_eq!(full.last_timer_index_pops(),32);
        assert_eq!(full.on_timer(MonoNs(10)).candidates.len(),1);
        assert_eq!(full.last_timer_index_pops(),1);
        assert!(full.on_timer(MonoNs(10)).candidates.is_empty());
        assert_eq!(full.last_timer_index_pops(),0);
        assert_eq!(full.expiry_index.len(),33);
        assert_eq!(full.wake_index.len(),33);
    }

    #[test]
    fn r2_burst_10000_due_drained_32_per_poll_counted_index_only() {
        const N:u64=10_000;
        let mut s=state(N as usize,10);
        for pn in 0..N {add(&mut s,pn,0,100_000_000);}
        assert_eq!(s.expiry_index.len(),N as usize);
        assert_eq!(s.wake_index.len(),N as usize);
        assert_eq!(s.next_deadline(),Some(MonoNs(10)));
        let mut observed=vec![false;N as usize];
        let mut accepted=0usize;
        let mut polls=0usize;
        while accepted<N as usize {
            let poll=s.on_timer(MonoNs(10));
            polls+=1;
            assert!(poll.releases.is_empty());
            assert!(!poll.candidates.is_empty());
            assert!(poll.candidates.len()<=32);
            assert!(s.last_timer_index_pops()<=32,
                "no full table scan per fake clock owner tick");
            for c in &poll.candidates {
                let at=c.pn().0 as usize;
                assert!(!observed[at],"candidate duplicated within one epoch");
                observed[at]=true;
                assert!(s.preflight(c,MonoNs(10)));
            }
            accepted+=poll.candidates.len();
            assert!(polls<400);
        }
        assert_eq!(polls,313); // 312*32 + 16, no 10k-per-tick rescans
        assert_eq!(accepted,N as usize);
        assert!(observed.into_iter().all(|yes|yes));
        assert!(s.on_timer(MonoNs(10)).candidates.is_empty());
        assert_eq!(s.last_timer_index_pops(),0);
        assert_eq!(s.expiry_index.len(),N as usize);
        assert_eq!(s.wake_index.len(),N as usize);
    }

    #[test]
    fn r2_burst_10000_hard_expiry_after_clock_jump_no_retained_tombstones() {
        const N:u64=10_000;
        let mut s=state(N as usize,50);
        for pn in 0..N {add(&mut s,pn,0,1_000);}
        assert_eq!(s.next_deadline(),Some(MonoNs(50)));
        let mut released=0usize;
        let mut ticks=0usize;
        while s.outstanding()!=0 {
            let expire=s.on_timer(MonoNs(1_000));
            assert!(expire.candidates.is_empty());
            assert!(expire.releases.len()<=32);
            assert!(s.last_timer_index_pops()<=32);
            assert!(expire.releases.iter().all(|r|r.reason==ReleaseReason::HardExpired));
            released+=expire.releases.len();
            ticks+=1;
        }
        assert_eq!(released,N as usize);
        assert_eq!(ticks,313);
        assert!(s.expiry_index.is_empty());
        assert!(s.wake_index.is_empty());
        assert_eq!(s.next_deadline(),None);
        assert!(s.on_timer(MonoNs(1_001)).releases.is_empty());
        assert_eq!(s.last_timer_index_pops(),0);
        assert_eq!(s.on_receipt(&receipt(1,N-1,vec![page(0,&[3])]),MonoNs(1_002))
            .unwrap().len(),0);
        assert!(s.expiry_index.is_empty());
        assert!(s.wake_index.is_empty());
    }

    #[test]
    fn r2_burst_queued_timeouts_retire_payload_in_bounded_owner_turns() {
        let mut s=state(35,10);
        for pn in 0..35 {add(&mut s,pn,0,100_000_000);}
        let first=s.on_timer(MonoNs(10)).candidates;
        assert_eq!(first.len(),32);
        let second=s.on_timer(MonoNs(10)).candidates;
        assert_eq!(second.len(),3);
        assert_eq!(s.outstanding(),35);
        let mut ticks=0usize;
        while s.outstanding()!=0 {
            let p=s.on_timer(MonoNs(20_000_011));
            assert!(p.candidates.is_empty());
            assert!(p.releases.is_empty());
            assert!(s.last_timer_index_pops()<=32);
            ticks+=1;
            assert!(ticks<4);
        }
        assert_eq!(ticks,2);
        assert!(s.expiry_index.is_empty());
        assert!(s.wake_index.is_empty());
        assert_eq!(s.diagnostic_snapshot().repair_abandoned_retired,35);
    }

    #[test]
    fn r2_burst_10000_queued_timeouts_retire_without_rescan_or_rearm() {
        const N:u64=10_000;
        let mut s=state(N as usize,10);
        for pn in 0..N {add(&mut s,pn,0,100_000_000);}
        for _ in 0..313 {s.on_timer(MonoNs(10));}
        let mut ticks=0usize;
        while s.outstanding()!=0 {
            let p=s.on_timer(MonoNs(20_000_011));
            assert!(p.candidates.is_empty());
            assert!(p.releases.is_empty());
            assert!(s.last_timer_index_pops()>0 && s.last_timer_index_pops()<=32);
            ticks+=1;
            assert!(ticks<400);
        }
        assert_eq!(ticks,313);
        assert!(s.wake_index.is_empty());
        assert!(s.expiry_index.is_empty());
        assert_eq!(s.diagnostic_snapshot().repair_abandoned_retired,N);
        assert!(s.on_timer(MonoNs(20_000_021)).candidates.is_empty());
    }

    #[test]
    fn r2_burst_stale_generation_and_fresh_shadow_independent() {
        let mut old=state(33,10);
        for pn in 0..33 {add(&mut old,pn,0,100_000);}
        let stale=old.on_timer(MonoNs(10)).candidates.remove(0);
        assert_eq!(old.outstanding(),33);
        let another_lane=LaneKey{generation:lane().generation+1,..lane()};
        let mut new=ReceiptState::new(another_lane,ReceiptConfig {
            max_shadow_entries:33,pto_ns:10,reorder_window_ns:5
        }).unwrap();
        let mut fresh=frozen(100);
        fresh.metadata.lane=another_lane;
        new.on_sent(fresh,MonoNs(11),MonoNs(100_000)).unwrap();
        assert_eq!(new.on_send_result(&stale,RepairSendResult::NotSent,MonoNs(12)),
            Err(DataError::Stale));
        assert_eq!(new.on_timer(MonoNs(20)).candidates.len(),0);
        assert_eq!(new.on_timer(MonoNs(21)).candidates.len(),1);
        assert_eq!(new.last_timer_index_pops(),1);
        assert_eq!(new.outstanding(),1);
    }

}
