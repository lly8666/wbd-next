//! M1 R1 bounded TX/RX owner model. No socket, crypto, timer wheel or
//! production scheduling is activated. Explicit monotonic time: no sleeps.
#![forbid(unsafe_code)]
use std::collections::VecDeque;
use std::ops::Range;
use wbd_types::{MonoNs, LaneKey};
use wbd_types::buffer_contract::{checked_wire_range, FrozenRecordHandle, UniqueSealable};
use crate::memory::{FrozenRecord, UniqueBuffer};

/// M1 R1 thread wake/stop proof; NOT a qualified SPSC or OS eventfd.
pub mod wake;
pub mod parity;
pub mod batch;
pub mod rx_batch;
pub mod generation;
pub mod ready_turn;
pub mod directional;
#[cfg(test)] mod generation_release;
#[cfg(test)] mod loan_stop;
pub mod early_rx;
use parity::ParityReady;
pub const OWNER_RUNTIME_READY: bool = false; // Not yet wired into M0 ABI.

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum OfferError { Full, ByteBudget, InvalidWindow, Stopping }

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct QueueLimits {
    pub slots: usize,
    pub bytes: usize,
    pub max_age_ns: u64,
}
impl QueueLimits {
    pub fn valid(self) -> bool {
        self.slots > 0 && self.slots <= 8192 && self.bytes > 0 && self.max_age_ns > 0
    }
    /// Initial sizing rule, NOT a sleep or periodic hot-path resizing policy.
    /// No observed rate yet -> 1024; otherwise 2ms PPS in [64,8192].
    pub fn initial_slots(observed_pps: Option<u64>) -> usize {
        match observed_pps {
            None => 1024,
            Some(pps) => (pps.saturating_mul(2).saturating_add(999) / 1000)
                .clamp(64, 8192) as usize,
        }
    }
}
struct Queued<T> { value: T, now: MonoNs, bytes: usize }
struct Bounded<T> {
    q: VecDeque<Queued<T>>,
    limit: QueueLimits,
    used_bytes: usize,
    expired: usize,
}
impl<T> Bounded<T> {
    fn new(limit: QueueLimits) -> Option<Self> {
        if !limit.valid() { return None; }
        Some(Self {
            q: VecDeque::with_capacity(limit.slots),
            limit, used_bytes: 0, expired: 0,
        })
    }
    fn offer(&mut self, value: T, bytes: usize, now: MonoNs)
        -> Result<(), (OfferError, T)>
    {
        if self.q.len() >= self.limit.slots { return Err((OfferError::Full, value)); }
        if bytes > self.limit.bytes.saturating_sub(self.used_bytes) {
            return Err((OfferError::ByteBudget, value));
        }
        self.used_bytes += bytes;
        self.q.push_back(Queued { value, bytes, now });
        Ok(())
    }
    fn expire(&mut self, now: MonoNs) {
        while self.q.front().is_some_and(|item| {
            now.elapsed_since(item.now) > self.limit.max_age_ns
        }) {
            let item = self.q.pop_front().unwrap();
            self.used_bytes -= item.bytes;
            self.expired += 1;
        }
    }
    fn take(&mut self, now: MonoNs) -> Option<T> {
        self.expire(now);
        self.q.pop_front().map(|item| {
            self.used_bytes -= item.bytes;
            item.value
        })
    }
    fn is_empty(&mut self, now: MonoNs) -> bool {
        self.expire(now);
        self.q.is_empty()
    }
    fn clear(&mut self) -> usize {
        let n = self.q.len();
        self.q.clear();
        self.used_bytes = 0;
        n
    }
    fn len(&self) -> usize { self.q.len() }
    fn used_bytes(&self) -> usize { self.used_bytes }
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TxKind { Fresh, Repair, Parity }
pub enum TxWait { Dispatch(TxDispatch), Returned }
pub struct TxDispatch {
    pub kind: TxKind,
    pub record: FrozenRecord,
}
/// TX has separate quotas: a pending repair cannot consume a fresh slot.
/// Dispatch is ready-only and nonblocking. Every eleventh operation with
/// repair present allows bounded repair progress; fresh always gets first
/// service even when repair queue was populated first.
pub struct TxOwner {
    fresh: Bounded<FrozenRecord>,
    repair: Bounded<FrozenRecord>,
    parity: Option<ParityReady>,
    consecutive_fresh: u8,
    // Parity is FIRST transmission, NOT repair. Debt enforces a bounded
    // configurable parity:systematic service share on already-ready bytes.
    parity_debt:i64,
    parity_weight:u8,
    systematic_weight:u8,
    stopping: bool,
}
impl TxOwner {
    pub fn new(fresh: QueueLimits, repair: QueueLimits) -> Option<Self> {
        Some(Self {
            fresh: Bounded::new(fresh)?, repair: Bounded::new(repair)?,
            parity: None, consecutive_fresh: 0,
            parity_debt:0, parity_weight:0,systematic_weight:1,
            stopping: false,
        })
    }
    /// Off/Normal uses new() and never allocates a parity queue.
    /// Optional FEC has its OWN slots, bytes and age, no fresh HOL.
    pub fn with_parity(
        fresh: QueueLimits, repair: QueueLimits, parity: QueueLimits
    ) -> Option<Self> {
        let mut owner = Self::new(fresh, repair)?;
        owner.parity = Some(ParityReady::new(parity)?);
        owner.parity_weight=20;
        owner.systematic_weight=20;
        Some(owner)
    }
    /// Configure admitted parity FIRST-send service ratio (r systematic k).
    /// The codec owns parity creation and configuration; no parity is minted.
    /// r/k is bounded here; repair remains a separate <=1 in 11 share.
    pub fn with_parity_share(fresh:QueueLimits,repair:QueueLimits,
        parity:QueueLimits,k:u8,r:u8)->Option<Self>{
        if k==0||k>20||r==0||r>k{return None;}
        let mut owner=Self::with_parity(fresh,repair,parity)?;
        owner.parity_weight=r;
        owner.systematic_weight=k;
        Some(owner)
    }
    fn parity_debt_cap(&self)->i64 {
        // Bound deficit by the declared caller-funded queue byte budgets:
        // no deferred unbounded parity credit when parity is temporarily off.
        let parity_bytes=self.parity.as_ref().map_or(1,|p|p.byte_budget());
        let max_bytes=self.fresh.limit.bytes.max(parity_bytes);
        i64::try_from(max_bytes).unwrap_or(i64::MAX/64)
            .saturating_mul(i64::from(self.systematic_weight)).saturating_mul(2)
    }
    pub fn offer_parity(
        &mut self, record: FrozenRecord, now: MonoNs, eligible_at: MonoNs
    ) -> Result<(), (OfferError, FrozenRecord)> {
        if self.stopping { return Err((OfferError::Stopping, record)); }
        match self.parity.as_mut() {
            Some(queue) => queue.offer(record, now, eligible_at),
            None => Err((OfferError::Full, record)),
        }
    }
    pub fn parity_deadline(&mut self, now: MonoNs) -> Option<MonoNs> {
        if self.stopping { return None; }
        self.parity.as_mut().and_then(|q| q.next_deadline(now))
    }
    pub fn parity_state(&self) -> (usize, usize, usize) {
        self.parity.as_ref().map_or((0,0,0),
            |p| (p.len(),p.charged_bytes(),p.expired_count()))
    }
    fn offer(&mut self, kind: TxKind, record: FrozenRecord, at: MonoNs)
        -> Result<(), (OfferError, FrozenRecord)>
    {
        if self.stopping { return Err((OfferError::Stopping, record)); }
        let size = record.bytes().len();
        match kind {
            TxKind::Fresh => self.fresh.offer(record, size, at),
            TxKind::Repair => self.repair.offer(record, size, at),
            TxKind::Parity => unreachable!("parity uses a due-time owner entry"),
        }
    }
    pub fn offer_fresh(&mut self, record: FrozenRecord, at: MonoNs)
        -> Result<(), (OfferError, FrozenRecord)>
    { self.offer(TxKind::Fresh, record, at) }
    pub fn offer_repair(&mut self, record: FrozenRecord, at: MonoNs)
        -> Result<(), (OfferError, FrozenRecord)>
    { self.offer(TxKind::Repair, record, at) }
    pub fn next_ready(&mut self, now: MonoNs) -> Option<TxDispatch> {
        if self.stopping { return None; }
        let has_fresh = !self.fresh.is_empty(now);
        let has_repair = !self.repair.is_empty(now);
        let has_parity = self.parity.as_mut().is_some_and(|p| p.is_ready(now));
        if !has_fresh && !has_repair && !has_parity { return None; }
        // Both systematic and parity are FIRST sends. Under continuous
        // readiness the parity debt issues roughly r/k parity after each
        // systematic, independent of 10:1 REPAIR fairness. Never hold the
        // first systematic behind parity. The debt saturates when a lane
        // cannot send parity rather than accumulating an unbounded burst.
        let first_ready=has_fresh||has_parity;
        let repair_turn=has_repair && (!first_ready||self.consecutive_fresh>=10);
        let kind=if repair_turn {TxKind::Repair}
        else if has_fresh && has_parity {
            let due_bytes=self.parity.as_ref()
                .and_then(|queue|queue.ready_wire_bytes())
                .unwrap_or(1);
            let due_bytes=i64::try_from(due_bytes).unwrap_or(i64::MAX/64);
            if self.parity_debt>=i64::from(self.systematic_weight)
                .saturating_mul(due_bytes) {
                TxKind::Parity
            }else{TxKind::Fresh}
        }else if has_fresh {TxKind::Fresh}
        else{TxKind::Parity};
        let cap=self.parity_debt_cap();
        let record=match kind {
            TxKind::Fresh=>{
                self.consecutive_fresh=self.consecutive_fresh.saturating_add(1);
                let record=self.fresh.take(now).expect("fresh is ready");
                let bytes=i64::try_from(record.bytes().len()).unwrap_or(i64::MAX/64);
                self.parity_debt=self.parity_debt.saturating_add(
                    i64::from(self.parity_weight).saturating_mul(bytes)).min(cap);
                record
            }
            TxKind::Repair=>{
                self.consecutive_fresh=0;
                self.repair.take(now).expect("repair is ready")
            }
            TxKind::Parity=>{
                self.consecutive_fresh=self.consecutive_fresh.saturating_add(1);
                let record=self.parity.as_mut().and_then(|p|p.take_ready(now))
                    .expect("parity is due");
                let bytes=i64::try_from(record.bytes().len()).unwrap_or(i64::MAX/64);
                self.parity_debt=self.parity_debt.saturating_sub(
                    i64::from(self.systematic_weight).saturating_mul(bytes)).max(-cap);
                record
            }
        };
        Some(TxDispatch {kind, record})
    }
    /// Drop all OWNED, unsent handles (including parity), but never free
    /// dispatched/driver-borrowed records. Arena stop waits for last lease.
    pub fn stop(&mut self) -> usize {
        self.stopping = true;
        self.fresh.clear() + self.repair.clear()
            + self.parity.as_mut().map_or(0, |p| p.clear())
    }
    /// Reuses M1's existing SeqCst armed/second-check + std thread token
    /// wake. A fake MonoNs clock drives deterministic deadlines; OS only
    /// parks while no work is eligible. No synchronous parity encode.
    pub fn wait_ready<C, R>(
        &mut self, gate: &wake::WakeGate, now: C, mut returned: R,
    ) -> Option<TxWait>
    where C: Fn() -> MonoNs, R: FnMut() -> bool {
        let outcome = gate.wait_scheduled(now, |at| {
            let event = self.next_ready(at).map(TxWait::Dispatch)
                .or_else(|| returned().then_some(TxWait::Returned));
            let deadline = if event.is_some() { None }
                else { self.parity_deadline(at) };
            (event, deadline)
        });
        if outcome.is_none() { self.stop(); }
        outcome
    }
    pub fn queued(&self) -> (usize, usize) { (self.fresh.len(), self.repair.len()) }
    pub fn used_bytes(&self) -> (usize, usize) {
        (self.fresh.used_bytes(), self.repair.used_bytes())
    }
    pub fn expired(&self) -> (usize, usize) {
        (self.fresh.expired, self.repair.expired)
    }
}
pub struct RxPacket {
    pub buffer: UniqueBuffer,
    pub wire: Range<usize>,
}
impl RxPacket {
    /// In-place bytes for a future M3 authenticated opener. This R1 model
    /// does not authenticate or deliver a business packet.
    pub fn wire_mut(&mut self) -> &mut [u8] {
        &mut self.buffer.writable()[self.wire.clone()]
    }
}
/// RX owns input slabs until the receiver consumes/drops them.
/// Per-item lane data is only an untrusted ingress scheduling hint.
 /// It MUST NOT be used for authenticated identity or business delivery.
 struct QueuedRx {
     packet: RxPacket,
     lane_hint: Option<LaneKey>,
 }
 pub struct RxOwner {
     ready: Bounded<QueuedRx>,
     last_lane: Option<Option<LaneKey>>,
     stopping: bool,
 }
impl RxOwner {
    pub fn new(limits: QueueLimits) -> Option<Self> {
        Some(Self {ready: Bounded::new(limits)?, last_lane: None, stopping: false})
    }
    /// Legacy unscoped ingress stays FIFO. No implied authentication.
    pub fn offer(&mut self, buffer: UniqueBuffer, wire: Range<usize>, at: MonoNs)
        -> Result<(), (OfferError, UniqueBuffer)>
    {
        self.offer_hint(buffer, wire, None, at)
    }
    /// A routing hint from an untrusted receive source. Authentication,
    /// replay and tunnel identity are validated later by their owners.
    pub fn offer_lane(
        &mut self, buffer: UniqueBuffer, wire: Range<usize>,
        lane: LaneKey, at: MonoNs,
    ) -> Result<(), (OfferError, UniqueBuffer)> {
        self.offer_hint(buffer, wire, Some(lane), at)
    }
    fn offer_hint(
        &mut self, mut buffer: UniqueBuffer, wire: Range<usize>,
        lane_hint: Option<LaneKey>, at: MonoNs,
    ) -> Result<(), (OfferError, UniqueBuffer)> {
        if self.stopping { return Err((OfferError::Stopping, buffer)); }
        let valid = match checked_wire_range(buffer.writable().len(), wire) {
            Ok(valid) => valid,
            Err(_) => return Err((OfferError::InvalidWindow, buffer)),
        };
        let bytes = valid.len();
        self.ready.offer(QueuedRx {
            packet: RxPacket {buffer, wire: valid}, lane_hint,
        }, bytes, at).map_err(|(error, item)| (error, item.packet.buffer))
    }
    pub fn take_ready(&mut self, now: MonoNs) -> Option<RxPacket> {
        self.take_ready_where(now, |_| true)
    }
    pub fn stop(&mut self) -> usize {
        self.stopping = true;
        self.ready.clear()
    }
    pub fn queued(&self) -> usize { self.ready.len() }
    pub(crate) fn capacity_remaining(&self)->(usize,usize) {
        (self.ready.limit.slots-self.ready.len(),
         self.ready.limit.bytes-self.ready.used_bytes())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::memory::Arena;
    use wbd_types::{LaneKey, RecordPn, SeqOffset, TunnelKey};
    use wbd_types::buffer_contract::{FrozenMetadata, UniqueSealable};
    fn meta() -> FrozenMetadata {
        FrozenMetadata {
            lane: LaneKey { tunnel: TunnelKey {slot: 9, generation: 2},
                slot: 1, generation: 1 },
            pn: RecordPn(1), seq: SeqOffset(1), carrier_snapshot: 123,
        }
    }
    fn limits(slots: usize, bytes: usize) -> QueueLimits {
        QueueLimits {slots, bytes, max_age_ns: 100}
    }
    fn arena() -> Arena { Arena::new(99, 64, 256, 1, 100_000).unwrap() }
    fn record(a: &mut Arena, v: u8) -> FrozenRecord {
        let mut buf = a.allocate().unwrap();
        buf.writable()[0] = v;
        buf.freeze(0..1, meta()).unwrap()
    }
    #[test]
    fn r1_runtime_capacity_rule_and_bounded_rejection_returns_ownership() {
        assert_eq!(QueueLimits::initial_slots(None), 1024);
        assert_eq!(QueueLimits::initial_slots(Some(1)), 64);
        assert_eq!(QueueLimits::initial_slots(Some(u64::MAX)), 8192);
        assert!(TxOwner::new(limits(8193, 8), limits(1, 8)).is_none());
        let mut a = arena();
        let mut tx = TxOwner::new(limits(2, 2), limits(1, 1)).unwrap();
        tx.offer_fresh(record(&mut a, 1), MonoNs(0)).unwrap();
        tx.offer_fresh(record(&mut a, 2), MonoNs(0)).unwrap();
        let rejected = tx.offer_fresh(record(&mut a, 3), MonoNs(0));
        assert!(matches!(rejected, Err((OfferError::Full, _))));
        assert_eq!(tx.used_bytes(), (2, 0));
        assert_eq!(tx.queued(), (2, 0));
        drop(rejected);
        tx.stop();
        assert_eq!(a.report().loaned, 0);
    }
    #[test]
    fn r1_runtime_fresh_not_blocked_by_full_repair_and_first_packet_ready() {
        let mut a = arena();
        let mut tx = TxOwner::new(limits(4, 4), limits(1, 1)).unwrap();
        tx.offer_repair(record(&mut a, 8), MonoNs(0)).unwrap();
        assert!(matches!(tx.offer_repair(record(&mut a, 9), MonoNs(0)),
            Err((OfferError::Full, _))));
        tx.offer_fresh(record(&mut a, 5), MonoNs(1)).unwrap();
        let first = tx.next_ready(MonoNs(1)).unwrap();
        assert_eq!(first.kind, TxKind::Fresh);
        assert_eq!(first.record.bytes(), &[5]);
        assert_eq!(tx.next_ready(MonoNs(1)).unwrap().kind, TxKind::Repair);
        assert_eq!(tx.queued(), (0, 0));
    }
    #[test]
    fn r1_runtime_repair_progress_after_bounded_fresh_burst() {
        let mut a = arena();
        let mut tx = TxOwner::new(limits(32, 32), limits(1, 1)).unwrap();
        tx.offer_repair(record(&mut a, 9), MonoNs(0)).unwrap();
        for i in 0..20 {
            tx.offer_fresh(record(&mut a, i), MonoNs(0)).unwrap();
        }
        for _ in 0..10 { assert_eq!(tx.next_ready(MonoNs(0)).unwrap().kind, TxKind::Fresh); }
        assert_eq!(tx.next_ready(MonoNs(0)).unwrap().kind, TxKind::Repair);
        assert_eq!(tx.next_ready(MonoNs(0)).unwrap().kind, TxKind::Fresh);
    }
    #[test]
    fn r1_runtime_fake_clock_drops_expired_without_waiting_or_leaking() {
        let mut a = arena();
        let mut tx = TxOwner::new(limits(2, 2), limits(1, 1)).unwrap();
        tx.offer_repair(record(&mut a, 1), MonoNs(0)).unwrap();
        assert!(tx.next_ready(MonoNs(101)).is_none());
        assert_eq!(tx.expired(), (0, 1));
        assert_eq!(a.report().loaned, 0);
        tx.offer_fresh(record(&mut a, 2), MonoNs(102)).unwrap();
        assert_eq!(tx.next_ready(MonoNs(102)).unwrap().kind, TxKind::Fresh);
    }
    #[test]
    fn r1_runtime_rx_owner_stop_and_tx_progress_are_independent() {
        let mut a = arena();
        let mut rx = RxOwner::new(limits(1, 3)).unwrap();
        let mut tx = TxOwner::new(limits(1, 1), limits(1, 1)).unwrap();
        let mut source = a.allocate().unwrap();
        source.writable()[1..4].copy_from_slice(&[1, 2, 3]);
        rx.offer(source, 1..4, MonoNs(0)).unwrap();
        assert!(matches!(rx.offer(a.allocate().unwrap(), 0..1, MonoNs(0)),
            Err((OfferError::Full, _))));
        tx.offer_fresh(record(&mut a, 7), MonoNs(0)).unwrap();
        assert_eq!(tx.next_ready(MonoNs(0)).unwrap().kind, TxKind::Fresh);
        let mut delivered = rx.take_ready(MonoNs(0)).unwrap();
        assert_eq!(delivered.wire_mut(), &[1, 2, 3]);
        drop(delivered);
        assert_eq!(rx.stop(), 0);
        assert!(matches!(rx.offer(a.allocate().unwrap(), 0..1, MonoNs(1)),
            Err((OfferError::Stopping, _))));
        assert_eq!(a.report().loaned, 0);
        assert!(a.stop().stopping);
        assert!(a.quiesced());
    }
}
