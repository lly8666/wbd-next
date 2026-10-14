//! M1 R1 bounded TX/RX owner model. No socket, crypto, timer wheel or
//! production scheduling is activated. Explicit monotonic time: no sleeps.
#![forbid(unsafe_code)]
use std::collections::VecDeque;
use std::ops::Range;
use wbd_types::MonoNs;
use wbd_types::buffer_contract::{checked_wire_range, FrozenRecordHandle, UniqueSealable};
use crate::memory::{FrozenRecord, UniqueBuffer};

/// M1 R1 thread wake/stop proof; NOT a qualified SPSC or OS eventfd.
pub mod wake;
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
pub enum TxKind { Fresh, Repair }
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
    consecutive_fresh: u8,
    stopping: bool,
}
impl TxOwner {
    pub fn new(fresh: QueueLimits, repair: QueueLimits) -> Option<Self> {
        Some(Self {
            fresh: Bounded::new(fresh)?, repair: Bounded::new(repair)?,
            consecutive_fresh: 0, stopping: false,
        })
    }
    fn offer(&mut self, kind: TxKind, record: FrozenRecord, at: MonoNs)
        -> Result<(), (OfferError, FrozenRecord)>
    {
        if self.stopping { return Err((OfferError::Stopping, record)); }
        let size = record.bytes().len();
        match kind {
            TxKind::Fresh => self.fresh.offer(record, size, at),
            TxKind::Repair => self.repair.offer(record, size, at),
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
        let kind = match (has_fresh, has_repair) {
            (false, false) => return None,
            (true, false) => TxKind::Fresh,
            (false, true) => TxKind::Repair,
            (true, true) if self.consecutive_fresh >= 10 => TxKind::Repair,
            (true, true) => TxKind::Fresh,
        };
        let record = match kind {
            TxKind::Fresh => {
                self.consecutive_fresh = self.consecutive_fresh.saturating_add(1);
                self.fresh.take(now).unwrap()
            }
            TxKind::Repair => {
                self.consecutive_fresh = 0;
                self.repair.take(now).unwrap()
            }
        };
        Some(TxDispatch {kind, record})
    }
    /// Cancels unsent handles, but dispatched handles live until consumers
    /// release them; arena stop must still wait for those last returns.
    pub fn stop(&mut self) -> usize {
        self.stopping = true;
        self.fresh.clear() + self.repair.clear()
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
pub struct RxOwner {
    ready: Bounded<RxPacket>,
    stopping: bool,
}
impl RxOwner {
    pub fn new(limits: QueueLimits) -> Option<Self> {
        Some(Self {ready: Bounded::new(limits)?, stopping: false})
    }
    pub fn offer(&mut self, mut buffer: UniqueBuffer, wire: Range<usize>, at: MonoNs)
        -> Result<(), (OfferError, UniqueBuffer)>
    {
        if self.stopping { return Err((OfferError::Stopping, buffer)); }
        let valid = match checked_wire_range(buffer.writable().len(), wire) {
            Ok(valid) => valid,
            Err(_) => return Err((OfferError::InvalidWindow, buffer)),
        };
        let bytes = valid.len();
        self.ready.offer(RxPacket {buffer, wire: valid}, bytes, at)
            .map_err(|(error, packet)| (error, packet.buffer))
    }
    pub fn take_ready(&mut self, now: MonoNs) -> Option<RxPacket> {
        if self.stopping { None } else { self.ready.take(now) }
    }
    pub fn stop(&mut self) -> usize {
        self.stopping = true;
        self.ready.clear()
    }
    pub fn queued(&self) -> usize { self.ready.len() }
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
