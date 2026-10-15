//! Pure R2 authenticated-receipt / shadow state. No clock reads, socket,
//! payload mutation, new PN allocation, or encryption. M0 owns the actual
//! M3 opened-record -> AuthenticatedReceipt trust-boundary adapter.
use std::collections::BTreeMap;
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
            lane, config, entries: BTreeMap::new(), last_report_seq: None,
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
        });
        Ok(())
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
        for page in &receipt.pages {
            let base = page.base_pn.0;
            if base > receipt.largest.0 { continue; }
            let end = (base + 255).min(receipt.largest.0);
            for pn in base..=end {
                let key = RecordPn(pn);
                if page.received(pn) {
                    if let Some(entry) = self.entries.remove(&key) {
                        let within_lifetime = now < entry.hard_expiry;
                        if fresh && within_lifetime && entry.repair_attempts == 0 {
                            self.rack_ack_ns = Some(now.elapsed_since(entry.last_sent).max(1));
                            self.observe_witness(Witness { pn: key, sent_at: entry.last_sent });
                        }
                        releases.push(Release {
                            pn: key,
                            reason: if within_lifetime {
                                ReleaseReason::ReceivedByPeer
                            } else {
                                ReleaseReason::HardExpired
                            },
                            frozen: entry.frozen,
                        });
                    }
                } else if fresh {
                    if let Some(entry) = self.entries.get_mut(&key) {
                        if now < entry.hard_expiry { entry.missing_reported = true; }
                    }
                }
            }
        }
        Ok(releases)
    }

    fn observe_witness(&mut self, witness: Witness) {
        if self.witnesses.iter().any(|w| w.pn == witness.pn) { return; }
        self.witnesses.push(witness);
        self.witnesses.sort_by_key(|w| (w.sent_at, w.pn));
        if self.witnesses.len() > 3 { self.witnesses.remove(0); }
    }

    fn due_at(&self, entry: &Entry<H>) -> MonoNs {
        let pto = entry.last_sent.0.saturating_add(self.config.pto_ns);
        let mut due = pto;
        if entry.repair_attempts == 0 && entry.missing_reported
            && self.witnesses.iter().filter(|w| w.sent_at > entry.last_sent).count() == 3
        {
            if let Some(rack_ack) = self.rack_ack_ns {
                due = due.min(entry.last_sent.0.saturating_add(rack_ack)
                    .saturating_add(self.config.reorder_window_ns));
            }
        }
        MonoNs(due.max(entry.rearm_at.0))
    }

    /// Called with an injected monotonic clock. At most 32 candidates per
    /// poll, each queued once. Next poll can handle remaining due records.
    pub fn on_timer(&mut self, now: MonoNs) -> PollResult<H> {
        let expired: Vec<_> = self.entries.iter()
            .filter(|(_, e)| now >= e.hard_expiry).map(|(pn, _)| *pn).collect();
        let releases = expired.into_iter().map(|pn| {
            let e = self.entries.remove(&pn).expect("entry collected above");
            Release { pn, reason: ReleaseReason::HardExpired, frozen: e.frozen }
        }).collect();
        // A queued candidate which misses its short dispatch window is dead.
        // It cannot stay queued indefinitely or be sent after its TTL.
        for e in self.entries.values_mut() {
            if e.queued.as_ref().is_some_and(|q| now >= q.until) {
                e.queued = None;
                e.rearm_at = MonoNs(now.0.saturating_add(self.config.pto_ns));
            }
        }
        let due: Vec<_> = self.entries.iter()
            .filter(|(_, e)| e.queued.is_none() && e.repair_attempts < 2
                && e.retry_epoch < u32::MAX && now >= self.due_at(e))
            .take(MAX_POLL_CANDIDATES)
            .map(|(pn, _)| *pn).collect();
        let mut candidates = Vec::with_capacity(due.len());
        for pn in due {
            let e = self.entries.get_mut(&pn).expect("due entry present");
            e.retry_epoch += 1;
            let until = MonoNs(e.hard_expiry.0.min(now.0.saturating_add(QUEUE_LIFETIME_NS)));
            e.queued = Some(Queued { epoch: e.retry_epoch, until });
            candidates.push(RepairCandidate {
                pn, origin: e.frozen.origin(), retry_epoch: e.retry_epoch,
                dispatch_by: until, frozen: e.frozen.clone(),
            });
        }
        PollResult { releases, candidates, next_deadline: self.next_deadline() }
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
        Ok(())
    }

    pub fn next_deadline(&self) -> Option<MonoNs> {
        self.entries.values().map(|e| {
            let due = match &e.queued {
                Some(q) => q.until,
                None if e.repair_attempts < 2 && e.retry_epoch < u32::MAX => self.due_at(e),
                None => e.hard_expiry,
            };
            MonoNs(due.0.min(e.hard_expiry.0))
        }).min()
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
}
