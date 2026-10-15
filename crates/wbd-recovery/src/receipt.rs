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
    dispatch_by: MonoNs,
    frozen: H,
}
impl<H: FrozenRecordHandle> RepairCandidate<H> {
    pub fn pn(&self) -> RecordPn { self.pn }
    pub fn retry_epoch(&self) -> u32 { self.retry_epoch }
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
}
struct Entry<H: FrozenRecordHandle> {
    frozen: H,
    last_sent: MonoNs,
    hard_expiry: MonoNs,
    repair_attempts: u8,
    retry_epoch: u32,
    missing_reported: bool,
    rearm_at: MonoNs,
    queued: Option<Queued>,
    indexed_wake: Option<u64>,
    // Last-sent key in the independent lazy-free RACK eligibility index.
    indexed_rack: Option<u64>,
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
    // Dynamic RACK: key by original send time, never a stale RTT-derived
    // deadline. A new positive witness changes only three scalar witnesses.
    rack_index: BTreeSet<(u64, RecordPn)>,
    #[cfg(test)]
    last_receipt_index_ops: usize,
    #[cfg(test)]
    last_timer_index_pops: usize,
    last_report_seq: Option<u32>,
    witnesses: Vec<Witness>, // latest three distinct, verified data sends
    rack_ack_ns: Option<u64>,
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
            rack_index: BTreeSet::new(),
            #[cfg(test)]
            last_receipt_index_ops: 0,
            #[cfg(test)]
            last_timer_index_pops: 0,
            last_report_seq: None,
            witnesses: Vec::with_capacity(3), rack_ack_ns: None,
        })
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
            retry_epoch: 0, missing_reported: false, rearm_at: at, queued: None,
            indexed_wake: None, indexed_rack: None,
        });
        self.expiry_index.insert((hard_expiry.0, meta.pn));
        self.refresh_wake(meta.pn);
        Ok(())
    }


    /// The ordinary queued/PTO/rearm wake is independent of changing RACK
    /// witness RTTs. Only entry-local changes touch this ordered index.
    fn base_due_at(&self, e: &Entry<H>) -> MonoNs {
        MonoNs(e.last_sent.0.saturating_add(self.config.pto_ns)
            .max(e.rearm_at.0))
    }
    fn wake_at(&self, e: &Entry<H>) -> Option<u64> {
        if let Some(q) = &e.queued { Some(q.until.0) }
        else if e.repair_attempts < 2 && e.retry_epoch < u32::MAX {
            Some(self.base_due_at(e).0)
        } else { None }
    }
    /// RACK can make an entry earlier ONLY before its first repair, when
    /// a fresh negative report exists and its original rearm is unchanged.
    /// A NotSent rearm is now+PTO after its due send: it cannot be accelerated
    /// by an old witness. A charged Uncertain/Accepted attempt is excluded.
    fn rack_member(&self, e: &Entry<H>) -> Option<u64> {
        (e.queued.is_none() && e.missing_reported && e.repair_attempts == 0
            && e.retry_epoch < u32::MAX && e.rearm_at <= e.last_sent)
            .then_some(e.last_sent.0)
    }
    /// Refresh one entry's two indexes, returning the number of real tree
    /// mutations. No retained tombstones, no hot global reindex.
    fn refresh_wake(&mut self, pn: RecordPn) -> usize {
        let (old_wake,old_rack)={
            let e=self.entries.get(&pn).expect("indexed entry");
            (e.indexed_wake,e.indexed_rack)
        };
        let mut operations=0;
        if let Some(at)=old_wake {
            assert!(self.wake_index.remove(&(at,pn)));
            operations+=1;
        }
        if let Some(at)=old_rack {
            assert!(self.rack_index.remove(&(at,pn)));
            operations+=1;
        }
        let (wake,rack)={
            let e=self.entries.get(&pn).expect("indexed entry");
            (self.wake_at(e),self.rack_member(e))
        };
        let e=self.entries.get_mut(&pn).expect("indexed entry");
        e.indexed_wake=wake;
        e.indexed_rack=rack;
        if let Some(at)=wake {
            assert!(self.wake_index.insert((at,pn)));
            operations+=1;
        }
        if let Some(at)=rack {
            assert!(self.rack_index.insert((at,pn)));
            operations+=1;
        }
        operations
    }
    fn remove_indexes(&mut self, pn: RecordPn, e: &Entry<H>,
        expiry_popped: bool) -> usize
    {
        let mut ops=0;
        if !expiry_popped {
            assert!(self.expiry_index.remove(&(e.hard_expiry.0,pn)));
            ops+=1;
        }
        if let Some(at)=e.indexed_wake {
            assert!(self.wake_index.remove(&(at,pn)));
            ops+=1;
        }
        if let Some(at)=e.indexed_rack {
            assert!(self.rack_index.remove(&(at,pn)));
            ops+=1;
        }
        ops
    }
    /// RACK's third/newest witness threshold defines a prefix of original
    /// send times. The first index node is earliest among that prefix, so
    /// comparing its dynamic due time against the PTO head is sufficient.
    /// Witness updates change no index nodes (O(3) witness observations).
    fn rack_head(&self) -> Option<(u64, RecordPn)> {
        if self.witnesses.len()!=3 { return None; }
        let ack=self.rack_ack_ns?;
        let &(sent,pn)=self.rack_index.first()?;
        if sent>=self.witnesses[0].sent_at.0 {return None;}
        let delta=ack.saturating_add(self.config.reorder_window_ns)
            .min(self.config.pto_ns);
        Some((sent.saturating_add(delta),pn))
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
        let mut index_ops=0usize;
        for page in &receipt.pages {
            let base = page.base_pn.0;
            if base > receipt.largest.0 { continue; }
            let end = base.saturating_add(255).min(receipt.largest.0);
            for pn in base..=end {
                let key=RecordPn(pn);
                if page.received(pn) {
                    if let Some(entry)=self.entries.remove(&key) {
                        index_ops+=self.remove_indexes(key,&entry,false);
                        let within_lifetime=now<entry.hard_expiry;
                        if fresh && within_lifetime && entry.repair_attempts==0 {
                            self.rack_ack_ns=Some(now.elapsed_since(entry.last_sent).max(1));
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
                        if now<e.hard_expiry && !e.missing_reported {
                            e.missing_reported=true;
                            dirty.push(key);
                        }
                    }
                }
            }
        }
        for key in dirty {index_ops+=self.refresh_wake(key);}
        #[cfg(test)]
        { self.last_receipt_index_ops=index_ops; }
        #[cfg(not(test))]
        let _=index_ops;
        Ok(releases)
    }

    fn observe_witness(&mut self, witness: Witness) {
        if self.witnesses.iter().any(|w| w.pn == witness.pn) { return; }
        self.witnesses.push(witness);
        self.witnesses.sort_by_key(|w| (w.sent_at, w.pn));
        if self.witnesses.len() > 3 { self.witnesses.remove(0); }
    }

    /// Called with an injected monotonic clock. At most 32 candidates per
    /// poll, each queued once. Next poll can handle remaining due records.
    pub fn on_timer(&mut self, now: MonoNs) -> PollResult<H> {
        let mut releases=Vec::new();
        let mut candidates=Vec::with_capacity(MAX_POLL_CANDIDATES);
        #[cfg(test)]
        { self.last_timer_index_pops=0; }
        // Expiry is independent of candidate throttling: a monotonic jump
        // releases every expired shadow once, with work proportional only
        // to the expired entries, never a scan of still-live shadows.
        while let Some(&(expiry,pn))=self.expiry_index.first() {
            if expiry>now.0 {break;}
            self.expiry_index.pop_first();
            let entry=self.entries.remove(&pn).expect("expiry index synchronized");
            self.remove_indexes(pn,&entry,true);
            #[cfg(test)]
            { self.last_timer_index_pops+=1; }
            releases.push(Release {
                pn,reason:ReleaseReason::HardExpired,frozen:entry.frozen
            });
        }
        // The independently indexed RACK prefix head competes with the
        // queued/PTO head. Both are O(log N) index events, at most 32 total.
        // On a RACK event the other (PTO) key is removed eagerly below.
        let mut wake_events=0usize;
        while candidates.len()<MAX_POLL_CANDIDATES
            && wake_events<MAX_POLL_CANDIDATES
        {
            let base=self.wake_index.first().copied();
            let rack=self.rack_head();
            let (wake,pn,is_rack)=match (base,rack) {
                (Some((at,pn)),Some((rat,rpn))) if rat<at
                    =>(rat,rpn,true),
                (Some((at,pn)),_) =>(at,pn,false),
                (None,Some((rat,rpn))) =>(rat,rpn,true),
                (None,None) =>break,
            };
            if wake>now.0 {break;}
            wake_events+=1;
            if is_rack {
                let sent=self.entries.get(&pn)
                    .expect("RACK owner present").indexed_rack
                    .expect("RACK membership");
                assert!(self.rack_index.remove(&(sent,pn)));
                self.entries.get_mut(&pn).expect("RACK owner present")
                    .indexed_rack=None;
            } else {
                self.wake_index.pop_first();
                let e=self.entries.get_mut(&pn).expect("wake index synchronized");
                assert_eq!(e.indexed_wake,Some(wake));
                e.indexed_wake=None;
            }
            #[cfg(test)]
            { self.last_timer_index_pops+=1; }
            let entry=self.entries.get_mut(&pn).expect("indexed owner present");
            if entry.queued.as_ref().is_some_and(|q| now>=q.until) {
                entry.queued=None;
                entry.rearm_at=MonoNs(now.0.saturating_add(self.config.pto_ns));
            } else {
                assert!(entry.queued.is_none() && entry.repair_attempts<2);
                entry.retry_epoch+=1;
                let until=MonoNs(entry.hard_expiry.0.min(
                    now.0.saturating_add(QUEUE_LIFETIME_NS)));
                entry.queued=Some(Queued {epoch:entry.retry_epoch,until});
                candidates.push(RepairCandidate {
                    pn,origin:entry.frozen.origin(),retry_epoch:entry.retry_epoch,
                    dispatch_by:until,frozen:entry.frozen.clone()
                });
            }
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
                && e.repair_attempts < 2
        })
    }

    pub fn on_send_result(&mut self, candidate: &RepairCandidate<H>,
        result: RepairSendResult, now: MonoNs) -> Result<(), DataError>
    {
        if !self.preflight(candidate, now) { return Err(DataError::Stale); }
        let e = self.entries.get_mut(&candidate.pn).expect("preflight verified");
        e.queued = None;
        match result {
            RepairSendResult::Accepted | RepairSendResult::Uncertain => {
                e.repair_attempts += 1;
                e.last_sent = now;
                e.missing_reported = false; // same old bitmap cannot fast-retry
                e.rearm_at = MonoNs(now.0.saturating_add(self.config.pto_ns));
            }
            RepairSendResult::NotSent => {
                // No attempt charged; avoid a same-tick infinite requeue.
                e.rearm_at = MonoNs(now.0.saturating_add(self.config.pto_ns));
            }
        }
        self.refresh_wake(candidate.pn);
        Ok(())
    }

    pub fn next_deadline(&self) -> Option<MonoNs> {
        let hard=self.expiry_index.first().map(|&(at,_)|at);
        let wake=self.wake_index.first().map(|&(at,_)|at);
        let rack=self.rack_head().map(|(at,_)|at);
        hard.into_iter().chain(wake).chain(rack).min().map(MonoNs)
    }
    #[cfg(test)]
    pub(crate) fn last_timer_index_pops(&self)->usize {
        self.last_timer_index_pops
    }
    #[cfg(test)]
    pub(crate) fn last_receipt_index_ops(&self)->usize {
        self.last_receipt_index_ops
    }
    pub fn outstanding(&self) -> usize { self.entries.len() }
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
    fn r2_uncertain_counts_attempts_no_same_evidence_double_retry_original_cipher() {
        let mut s = state(2, 100);
        let original = frozen(8);
        let shared = original.bytes.clone();
        s.on_sent(original, MonoNs(0), MonoNs(500)).unwrap();
        let first = s.on_timer(MonoNs(100)).candidates.remove(0);
        assert!(s.preflight(&first, MonoNs(100)));
        assert!(Arc::ptr_eq(&first.frozen.bytes, &shared));
        assert_eq!(first.frozen.metadata.pn, RecordPn(8));
        s.on_send_result(&first, RepairSendResult::Uncertain, MonoNs(100)).unwrap();
        assert_eq!(s.on_send_result(&first, RepairSendResult::Accepted, MonoNs(101)),
            Err(DataError::Stale));
        assert!(s.on_timer(MonoNs(101)).candidates.is_empty());
        assert!(s.on_timer(MonoNs(199)).candidates.is_empty());
        let second = s.on_timer(MonoNs(200)).candidates.remove(0);
        assert!(Arc::ptr_eq(&second.frozen.bytes, &shared));
        assert_ne!(second.retry_epoch, first.retry_epoch);
        s.on_send_result(&second, RepairSendResult::Accepted, MonoNs(200)).unwrap();
        assert!(s.on_timer(MonoNs(300)).candidates.is_empty());
        assert_eq!(s.on_timer(MonoNs(500)).releases.len(), 1);
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
    fn r2_queue_timeout_revokes_old_candidate_and_rearms_boundedly() {
        let mut s = state(2, 10);
        add(&mut s, 4, 0, 100_000_000);
        let old = s.on_timer(MonoNs(10)).candidates.remove(0);
        assert!(s.preflight(&old, MonoNs(20_000_009)));
        assert!(!s.preflight(&old, MonoNs(20_000_011)));
        assert!(s.on_timer(MonoNs(20_000_011)).candidates.is_empty());
        assert!(s.on_timer(MonoNs(20_000_020)).candidates.is_empty());
        let renewed = s.on_timer(MonoNs(20_000_021)).candidates.remove(0);
        assert_ne!(renewed.retry_epoch(), old.retry_epoch());
        assert_eq!(s.on_send_result(&old, RepairSendResult::Accepted, MonoNs(20_000_021)),
            Err(DataError::Stale));
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
        assert_eq!(s.on_timer(MonoNs(100)).releases.len(), 40);
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
        let expire=s.on_timer(MonoNs(1_000));
        assert!(expire.candidates.is_empty());
        assert_eq!(expire.releases.len(),N as usize);
        assert_eq!(s.last_timer_index_pops(),N as usize);
        assert!(expire.releases.iter().all(|r|r.reason==ReleaseReason::HardExpired));
        assert_eq!(s.outstanding(),0);
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
    fn r2_burst_queued_timeout_and_ack_preserve_exact_index_and_no_retry() {
        let mut s=state(35,10);
        for pn in 0..35 {add(&mut s,pn,0,100_000_000);}
        let mut first=s.on_timer(MonoNs(10)).candidates;
        assert_eq!(first.len(),32);
        let old=first.remove(0);
        assert!(s.on_receipt(&receipt(1,0,vec![page(0,&[0])]),MonoNs(11))
            .unwrap().iter().any(|r|r.pn==RecordPn(0)));
        assert!(!s.preflight(&old,MonoNs(12)));
        assert_eq!(s.on_send_result(&old,RepairSendResult::Accepted,MonoNs(12)),
            Err(DataError::Stale));
        let second=s.on_timer(MonoNs(20)).candidates;
        assert_eq!(second.len(),3);
        assert_eq!(s.last_timer_index_pops(),3);
        assert!(s.on_timer(MonoNs(21)).candidates.is_empty());
        assert_eq!(s.last_timer_index_pops(),0);
        // Existing 31 remaining queued candidates time out at 20m+10.
        // The three queued at t=20 have a different, later dispatch window.
        let expired_queues=s.on_timer(MonoNs(20_000_011));
        assert!(expired_queues.candidates.is_empty());
        assert_eq!(s.wake_index.len(),s.outstanding());
        assert_eq!(s.expiry_index.len(),s.outstanding());
        assert_eq!(s.outstanding(),34);
        assert_eq!(s.last_timer_index_pops(),31);
        let later=s.on_timer(MonoNs(20_000_021)).candidates;
        assert_eq!(later.len(),29); // 3 newer queued time out, 29 earlier due
        assert_eq!(s.last_timer_index_pops(),32);
        assert_eq!(s.outstanding(),34);
    }

    #[test]
    fn r2_burst_10000_queued_timeouts_are_also_index_budgeted() {
        const N:u64=10_000;
        let mut s=state(N as usize,10);
        for pn in 0..N {add(&mut s,pn,0,100_000_000);}
        for _ in 0..313 {s.on_timer(MonoNs(10));}
        let mut popped=0usize;
        let mut ticks=0usize;
        while popped<N as usize {
            let r=s.on_timer(MonoNs(20_000_011));
            assert!(r.candidates.is_empty());
            assert!(r.releases.is_empty());
            let n=s.last_timer_index_pops();
            assert!(n>0 && n<=32);
            popped+=n;
            ticks+=1;
        }
        assert_eq!(ticks,313);
        assert_eq!(s.wake_index.len(),N as usize);
        assert_eq!(s.expiry_index.len(),N as usize);
        assert_eq!(s.outstanding(),N as usize);
        assert_eq!(s.on_timer(MonoNs(20_000_011)).candidates.len(),0);
        assert_eq!(s.last_timer_index_pops(),0);
        // Dead queued tokens cannot be resurrected: only new epoch candidates
        // become dispatchable after the explicitly bounded rearm timer.
        assert_eq!(s.on_timer(MonoNs(20_000_021)).candidates.len(),32);
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


    /// Build 10k actual frozen shadow entries and mark all as missing through
    /// bounded 8-page receipts; add 33 independently timestamped positive
    /// witness records in disjoint receipt pages. Fake monotonic only.
    fn r2_rack_10k_missing_fixture() -> ReceiptState<FakeFrozen> {
        const N:u64=10_000;
        let mut s=state((N+33) as usize,1_000);
        for pn in 0..N {add(&mut s,pn,1_000,1_000_000);}
        for j in 0..33 {
            add(&mut s,25_600+j*256,1_001,1_000_000);
        }
        let mut seq=1;
        for batch in (0..40).collect::<Vec<_>>().chunks(8) {
            let pages=batch.iter().map(|i|page((*i as u64)*256,&[])).collect();
            s.on_receipt(&receipt(seq,34_000,pages),MonoNs(1_002)).unwrap();
            assert!(s.last_receipt_index_ops()<=8*256*3);
            seq+=1;
        }
        assert_eq!(s.rack_index.len(),N as usize);
        assert_eq!(s.wake_index.len(),(N+33) as usize);
        assert_eq!(s.next_deadline(),Some(MonoNs(2_000)));
        s
    }

    #[test]
    fn r2_rack_10k_positive_witness_1_32_33_no_full_reindex() {
        const N:usize=10_000;
        let mut s=r2_rack_10k_missing_fixture();
        for j in 0..33 {
            let pn=25_600+j*256;
            let now=1_100+j;
            let released=s.on_receipt(
                &receipt(100+j as u32,34_000,vec![page(pn,&[pn])]),
                MonoNs(now)
            ).unwrap();
            assert_eq!(released.len(),1);
            assert_eq!(released[0].pn,RecordPn(pn));
            assert_eq!(released[0].reason,ReleaseReason::ReceivedByPeer);
            // Only the two index nodes owned by the ACKed witness changed.
            assert!(s.last_receipt_index_ops()<=4,
                "no witness-triggered O(10000) shadow reindex");
            assert_eq!(s.rack_index.len(),N);
            assert_eq!(s.expiry_index.len(),N+32-j as usize);
            assert_eq!(s.wake_index.len(),N+32-j as usize);
            if j<2 {
                assert_eq!(s.next_deadline(),Some(MonoNs(2_000)));
            } else {
                // Equal original witness send times remain strictly newer
                // than the 10k originals; newest receipt RTT is now-1001.
                assert_eq!(s.next_deadline(),Some(MonoNs(now+4)));
            }
            if j==0 || j==31 || j==32 {
                assert_eq!(s.outstanding(),N+32-j as usize);
            }
        }
        assert_eq!(s.witnesses.len(),3);
        assert_eq!(s.next_deadline(),Some(MonoNs(1_136)));
        let none=s.on_timer(MonoNs(1_135));
        assert_eq!(none.candidates.len(),0);
        assert_eq!(s.last_timer_index_pops(),0);
        let batch=s.on_timer(MonoNs(1_136));
        assert_eq!(batch.candidates.len(),32);
        assert_eq!(s.last_timer_index_pops(),32);
        assert_eq!(batch.candidates[0].pn(),RecordPn(0));
        assert_eq!(s.rack_index.len(),N-32);
        assert_eq!(s.expiry_index.len(),N);
        assert_eq!(s.wake_index.len(),N);
        assert_eq!(batch.next_deadline,Some(MonoNs(1_136)));
        assert!(s.on_timer(MonoNs(1_136)).candidates.len()<=32);
    }

    #[test]
    fn r2_rack_10k_positive_32_then_33_eager_ack_not_replayed() {
        let mut s=state(10_033,10_000);
        for pn in 0..10_000 {add(&mut s,pn,1_000,20_000);}
        for j in 0..33 {add(&mut s,20_000+j,1_001,20_000);}
        for k in 0..5 {
            let pages=(k*8..(k*8+8)).map(|i|page((i as u64)*256,&[])).collect();
            s.on_receipt(&receipt(1+k as u32,21_000,pages),MonoNs(1_002)).unwrap();
        }
        let pins:(Vec<u64>,Vec<u64>)=(
            (20_000..20_032).collect(),vec![20_032]);
        let first=s.on_receipt(&receipt(6,21_000,
            vec![page(19_968,&pins.0)]),MonoNs(1_101)).unwrap();
        assert_eq!(first.len(),32);
        assert!(s.last_receipt_index_ops()<=130);
        assert_eq!(s.witnesses.len(),3);
        assert_eq!(s.rack_index.len(),10_001); // last witness now negative
        assert_eq!(s.next_deadline(),Some(MonoNs(1_105)));
        let last=s.on_receipt(&receipt(7,21_000,
            vec![page(19_968,&pins.1)]),MonoNs(1_111)).unwrap();
        assert_eq!(last.len(),1);
        assert!(s.last_receipt_index_ops()<=4);
        assert_eq!(s.rack_index.len(),10_000);
        // The old 1105 wake was never stored; latest ACK changes it to1115.
        assert_eq!(s.next_deadline(),Some(MonoNs(1_115)));
        assert!(s.on_timer(MonoNs(1_114)).candidates.is_empty());
        assert_eq!(s.on_timer(MonoNs(1_115)).candidates.len(),32);
        // Old replay cannot re-add ACKed record or manufacture fresh witness.
        assert!(s.on_receipt(&receipt(6,21_000,
            vec![page(19_968,&pins.0)]),MonoNs(1_115))
            .unwrap().is_empty());
        assert_eq!(s.last_receipt_index_ops(),0);
    }

    #[test]
    fn r2_rack_10k_witness_clock_jump_hard_expiry_no_stale_nodes() {
        let mut s=r2_rack_10k_missing_fixture();
        for j in 0..3 {
            let pn=25_600+j*256;
            s.on_receipt(&receipt(50+j as u32,34_000,
                vec![page(pn,&[pn])]),MonoNs(1_100+j)).unwrap();
        }
        assert_eq!(s.rack_index.len(),10_000);
        let res=s.on_timer(MonoNs(1_000_000));
        assert_eq!(res.releases.len(),10_030); // 10k + 30 still-unacked witnesses
        assert!(res.releases.iter().all(|r|r.reason==ReleaseReason::HardExpired));
        assert!(res.candidates.is_empty());
        assert_eq!(s.outstanding(),0);
        assert!(s.rack_index.is_empty());
        assert!(s.wake_index.is_empty());
        assert!(s.expiry_index.is_empty());
        assert_eq!(s.next_deadline(),None);
        assert_eq!(s.last_timer_index_pops(),10_030);
        assert!(s.on_timer(MonoNs(1_000_001)).releases.is_empty());
        assert_eq!(s.last_timer_index_pops(),0);
    }

    #[test]
    fn r2_rack_notsent_rearm_does_not_promote_old_bitmap_early() {
        let mut s=state(4,100);
        add(&mut s,1,1_000,5_000);
        s.on_receipt(&receipt(1,1,vec![page(0,&[])]),MonoNs(1_010))
            .unwrap();
        assert_eq!(s.rack_index.len(),1);
        let old=s.on_timer(MonoNs(1_100)).candidates.remove(0);
        assert!(s.preflight(&old,MonoNs(1_100)));
        s.on_send_result(&old,RepairSendResult::NotSent,MonoNs(1_100))
            .unwrap();
        assert!(s.rack_index.is_empty());
        assert_eq!(s.next_deadline(),Some(MonoNs(1_200)));
        for j in 0..3 {
            add(&mut s,10+j,1_101,5_000);
            s.on_receipt(&receipt(2+j as u32,20,
                vec![page(0,&[10+j])]),MonoNs(1_105+j)).unwrap();
        }
        assert_eq!(s.rack_index.len(),0);
        assert_eq!(s.next_deadline(),Some(MonoNs(1_200)));
        assert!(s.on_timer(MonoNs(1_199)).candidates.is_empty());
        assert_eq!(s.on_timer(MonoNs(1_200)).candidates.len(),1);
        assert_eq!(s.on_send_result(&old,RepairSendResult::Accepted,
            MonoNs(1_200)),Err(DataError::Stale));
    }

}
