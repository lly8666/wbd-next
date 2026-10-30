//! R2 per-logical-direction pure 1s repair byte quota and burst pacing.
//!
//! An owner keeps ONE ledger for all lanes of the same tunnel/direction.
//! F is only confirmed first-transmission outer IP+TCP+record bytes (including
//! initial parity/Game copies), never control/ACK, and never unknown sends.
//! R includes reserved, accepted, and uncertain repair outer-wire bytes.
//! No socket, clock reads, PN allocation, seal, or fresh-queue admission here.
//!
//! Engine/M0 must share a *process-wide* sparse allowance across distinct
//! clients, apply actual carrier/MSS byte accounting and call ReceiptState's
//! preflight immediately before dispatch. This local ledger cannot certify
//! those integration properties or a live product.
use std::collections::BTreeMap;
use wbd_types::buffer_contract::{BufferOrigin, FrozenRecordHandle};
use wbd_types::{LaneKey, MonoNs, RecordPn, TunnelKey};
use crate::receipt::{RepairCandidate, RepairSendResult};

const SECOND_NS: u64 = 1_000_000_000;
const SPARSE_FLOOR_BYTES: u64 = 32_768;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum WireDirection { ClientToServer, ServerToClient }

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct BudgetDirection {
    pub tunnel: TunnelKey,
    pub direction: WireDirection,
}
#[derive(Clone, Copy, Debug)]
pub struct RepairBudgetConfig {
    /// Effective outer carrier MTU, not inner payload bytes.
    pub outer_mtu: u64,
    /// Absolute non-network memory/traffic safety ceiling each second.
    pub max_repair_bytes_per_epoch: u64,
    pub max_pending_reservations: usize,
    pub max_pending_bytes: u64,
    /// Bounded local syscall completion deadline. <= 1s to retain
    /// at most current+previous epoch accounts; timeout is uncertain.
    pub io_timeout_ns: u64,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum BudgetError {
    InvalidConfig,
    InvalidFrame,
    WrongTunnel,
    BackwardClock,
    ExpiredCandidate,
    DuplicateCandidate,
    NoCapacity,
    QuotaExhausted,
    BurstPaced,
    StaleReservation,
    IdExhausted,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd)]
pub struct ReservationId(u64);
impl ReservationId {
    pub fn get(self) -> u64 { self.0 }
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct BudgetSnapshot {
    pub epoch: u64,
    pub fresh_confirmed_bytes: u64,
    /// Count includes uncompleted reservations, Accepted, and Uncertain.
    pub charged_repair_bytes: u64,
    pub epoch_repair_limit: u64,
    pub pending_count: usize,
    pub pending_bytes: u64,
    pub pacer_tokens: u64,
    pub pacer_burst_limit: u64,
    pub overdue_uncertain_bytes: u64,
    pub overdue_uncertain_count: u64,
}
#[derive(Clone, Copy)]
struct Epoch {
    number: u64,
    fresh: u64,
    charged: u64,
}
impl Epoch {
    fn new(number: u64) -> Self { Self { number, fresh: 0, charged: 0 } }
}
#[derive(Clone, Copy, Eq, PartialEq)]
struct CandidateKey {
    lane: LaneKey,
    pn: RecordPn,
    origin: BufferOrigin,
    retry_epoch: u32,
}
#[derive(Clone, Copy)]
struct Pending {
    key: CandidateKey,
    epoch: u64,
    wire_bytes: u64,
    // Exact token debit. Only an explicit NotSent may refund it.
    pacer_debit: u64,
    timeout: MonoNs,
}
/// Intentionally O(number_of_pending_reservations) only for rare completion
/// timeout cleanup; the count/byte bounds are explicit.
pub struct RepairBudget {
    direction: BudgetDirection,
    cfg: RepairBudgetConfig,
    current: Epoch,
    previous: Option<Epoch>,
    pending: BTreeMap<ReservationId, Pending>,
    pending_bytes: u64,
    next_id: u64,
    last_now: MonoNs,
    tokens: u64,
    fractional_token_ns: u128,
    /// Lost/overdue completions are conservatively charged across future
    /// epochs until this ledger is retired, never turned into free credit.
    overdue_uncertain_bytes: u64,
    overdue_uncertain_count: u64,
    opportunistic_v3: bool,
}
impl RepairBudget {
    pub fn new(direction: BudgetDirection, cfg: RepairBudgetConfig, now: MonoNs)
        -> Result<Self, BudgetError>
    {
        if cfg.outer_mtu == 0 || cfg.outer_mtu.checked_mul(8).is_none()
            || cfg.max_repair_bytes_per_epoch < SPARSE_FLOOR_BYTES
            || cfg.max_pending_reservations == 0 || cfg.max_pending_bytes < cfg.outer_mtu
            || cfg.io_timeout_ns == 0 || cfg.io_timeout_ns > SECOND_NS
        {
            return Err(BudgetError::InvalidConfig);
        }
        Ok(Self {
            direction, current: Epoch::new(now.0 / SECOND_NS), previous: None,
            tokens: cfg.outer_mtu * 8, cfg,
            pending: BTreeMap::new(), pending_bytes: 0, next_id: 0,
            last_now: now, fractional_token_ns: 0,
            overdue_uncertain_bytes: 0, overdue_uncertain_count: 0,
            opportunistic_v3: false,
        })
    }

    /// PLAN027: v3 uses 10% of confirmed first-send F for the hard
    /// credit ceiling; 9% pacing remains a conservative smoothing target.
    pub fn enable_opportunistic_v3(&mut self) { self.opportunistic_v3 = true; }
    fn burst_cap(&self) -> u64 { self.cfg.outer_mtu * 8 }
    fn epoch_limit(&self) -> u64 {
        // The 32KiB sparse allowance is a floor, not an additional bonus.
        (self.current.fresh/10)
            .max(SPARSE_FLOOR_BYTES)
            .min(self.cfg.max_repair_bytes_per_epoch)
    }
    fn pace_rate(&self) -> u64 {
        // The previous completed epoch only informs PACING, never transfers
        // its unused byte allowance into the new epoch.
        let recent_f = self.previous.map_or(self.current.fresh,
            |e| e.fresh.max(self.current.fresh));
        (if self.opportunistic_v3 {recent_f.saturating_mul(9)/100}
            else{recent_f/10}).max(SPARSE_FLOOR_BYTES)
    }

    fn advance(&mut self, now: MonoNs) -> Result<(), BudgetError> {
        if now < self.last_now { return Err(BudgetError::BackwardClock); }
        let elapsed = now.0 - self.last_now.0;
        if elapsed > 0 {
            let n = (elapsed as u128) * (self.pace_rate() as u128)
                + self.fractional_token_ns;
            let earned = (n / SECOND_NS as u128).min(u64::MAX as u128) as u64;
            self.tokens = self.tokens.saturating_add(earned).min(self.burst_cap());
            self.fractional_token_ns = if self.tokens == self.burst_cap() {
                0
            } else {
                n % SECOND_NS as u128
            };
        }
        self.last_now = now;
        // A missing completion is never interpreted as DefinitelyNotSent.
        // Remove its bounded pending metadata; retain conservative debit.
        let overdue: Vec<_> = self.pending.iter()
            .filter(|(_, p)| now >= p.timeout)
            .map(|(id, _)| *id).collect();
        for id in overdue {
            let p = self.pending.remove(&id).expect("collected pending id");
            self.pending_bytes -= p.wire_bytes;
            self.overdue_uncertain_bytes =
                self.overdue_uncertain_bytes.saturating_add(p.wire_bytes);
            self.overdue_uncertain_count = self.overdue_uncertain_count.saturating_add(1);
        }
        let epoch = now.0 / SECOND_NS;
        if epoch > self.current.number {
            let old = self.current;
            self.current = Epoch::new(epoch);
            self.previous = if old.number.checked_add(1) == Some(epoch) {
                Some(old)
            } else {
                None
            };
        }
        Ok(())
    }

    /// Fresh send success is reported independently. There is no repair-credit
    /// branch that can stop first transmissions from making progress.
    /// Caller reports *actual accepted bytes*, not an Uncertain send.
    pub fn on_fresh_accepted(&mut self, wire_bytes: u64, now: MonoNs)
        -> Result<(), BudgetError>
    {
        self.advance(now)?;
        self.current.fresh = self.current.fresh.saturating_add(wire_bytes);
        Ok(())
    }

    /// Reserve before a syscall; caller also calls ReceiptState::preflight
    /// immediately before dispatch. A candidate refers to the frozen original
    /// with its unchanged PN/seq/ciphertext, and must not be re-sealed.
    pub fn reserve<H: FrozenRecordHandle>(&mut self,
        candidate: &RepairCandidate<H>, outer_wire_bytes: u64, now: MonoNs)
        -> Result<ReservationId, BudgetError>
    {
        self.advance(now)?;
        let frozen = candidate.frozen();
        let meta = frozen.metadata();
        if meta.lane.tunnel != self.direction.tunnel { return Err(BudgetError::WrongTunnel); }
        if now > candidate.dispatch_by() { return Err(BudgetError::ExpiredCandidate); }
        if meta.pn != candidate.pn()
            || candidate.retry_epoch() == 0
            || outer_wire_bytes == 0 || outer_wire_bytes > self.cfg.outer_mtu
            || outer_wire_bytes < frozen.bytes().len() as u64
        {
            return Err(BudgetError::InvalidFrame);
        }
        let key = CandidateKey {
            lane: meta.lane, pn: candidate.pn(), origin: frozen.origin(),
            retry_epoch: candidate.retry_epoch(),
        };
        if self.pending.values().any(|p| p.key == key) {
            return Err(BudgetError::DuplicateCandidate);
        }
        if self.pending.len() >= self.cfg.max_pending_reservations
            || self.pending_bytes.saturating_add(outer_wire_bytes)
                > self.cfg.max_pending_bytes
        {
            return Err(BudgetError::NoCapacity);
        }
        let available = self.epoch_limit()
            .saturating_sub(self.overdue_uncertain_bytes);
        if outer_wire_bytes > available.saturating_sub(self.current.charged) {
            return Err(BudgetError::QuotaExhausted);
        }
        // Even a first (stage0) one-shot repair must obey the 8-MTU
        // smooth burst cap; fresh records never wait for repair tokens.
        if outer_wire_bytes > self.tokens { return Err(BudgetError::BurstPaced); }
        let pacer_debit=outer_wire_bytes;
        let id = self.next_id.checked_add(1).ok_or(BudgetError::IdExhausted)?;
        self.next_id = id;
        self.current.charged += outer_wire_bytes; // bounded by the epoch cap
        self.tokens -= pacer_debit;
        self.pending_bytes += outer_wire_bytes; // bounded by configured pending limit
        let timeout = MonoNs(now.0.saturating_add(self.cfg.io_timeout_ns));
        self.pending.insert(ReservationId(id), Pending {
            key, epoch: self.current.number, wire_bytes: outer_wire_bytes,
            pacer_debit, timeout,
        });
        Ok(ReservationId(id))
    }

    /// Accepted and Uncertain both consume the reserved amount exactly once.
    /// Only NotSent returns credits to the *original* accounting epoch.
    /// No old-epoch refund is ever credited to the current new epoch.
    pub fn on_send_result(&mut self, id: ReservationId,
        result: RepairSendResult, now: MonoNs) -> Result<(), BudgetError>
    {
        self.advance(now)?;
        let p = self.pending.remove(&id).ok_or(BudgetError::StaleReservation)?;
        self.pending_bytes -= p.wire_bytes;
        if result == RepairSendResult::NotSent {
            if p.epoch == self.current.number {
                self.current.charged -= p.wire_bytes;
            } else if let Some(prev) = &mut self.previous {
                if p.epoch == prev.number { prev.charged -= p.wire_bytes; }
            }
            // Only an explicitly NotSent reservation refunds its token debit.
            self.tokens = self.tokens.saturating_add(p.pacer_debit)
                .min(self.burst_cap());
        }
        Ok(())
    }

    /// Detect incomplete send-result callbacks with injected fake time.
    pub fn on_timer(&mut self, now: MonoNs) -> Result<(), BudgetError> {
        self.advance(now)
    }
    pub fn snapshot(&self) -> BudgetSnapshot {
        BudgetSnapshot {
            epoch: self.current.number,
            fresh_confirmed_bytes: self.current.fresh,
            charged_repair_bytes: self.current.charged,
            epoch_repair_limit: self.epoch_limit(),
            pending_count: self.pending.len(), pending_bytes: self.pending_bytes,
            pacer_tokens: self.tokens, pacer_burst_limit: self.burst_cap(),
            overdue_uncertain_bytes: self.overdue_uncertain_bytes,
            overdue_uncertain_count: self.overdue_uncertain_count,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;
    use wbd_types::buffer_contract::{BufferOrigin, FrozenMetadata};
    use wbd_types::{BufferKey, SeqOffset};
    use crate::receipt::{ReceiptConfig, ReceiptState};

    #[derive(Clone)]
    struct FakeFrozen {
        wire: Arc<[u8]>,
        origin: BufferOrigin,
        meta: FrozenMetadata,
    }
    impl FrozenRecordHandle for FakeFrozen {
        fn origin(&self) -> BufferOrigin { self.origin }
        fn metadata(&self) -> FrozenMetadata { self.meta }
        fn bytes(&self) -> &[u8] { &self.wire }
    }
    fn tunnel() -> TunnelKey { TunnelKey { slot: 3, generation: 6 } }
    fn lane() -> LaneKey { LaneKey { tunnel: tunnel(), slot: 9, generation: 1 } }
    fn candidate(pn: u64, due: u64) -> RepairCandidate<FakeFrozen> {
        let mut s = ReceiptState::new(lane(), ReceiptConfig {
            max_shadow_entries: 2, pto_ns: 1, reorder_window_ns: 1,
        }).unwrap();
        let f = FakeFrozen {
            wire: Arc::from([1u8, 2, 3, 4].as_slice()),
            origin: BufferOrigin {owner_arena: 1,
                key: BufferKey {slot: pn as u32,generation: 1}},
            meta: FrozenMetadata {lane: lane(), pn: RecordPn(pn),
                seq: SeqOffset(pn), carrier_snapshot: 1},
        };
        s.on_sent(f, MonoNs(due - 1), MonoNs(due.saturating_add(100_000_000))).unwrap();
        s.on_timer(MonoNs(due)).candidates.remove(0)
    }
    fn cfg(mtu: u64) -> RepairBudgetConfig {
        RepairBudgetConfig {
            outer_mtu: mtu, max_repair_bytes_per_epoch: 1_000_000,
            max_pending_reservations: 128, max_pending_bytes: 1_000_000,
            io_timeout_ns: 1_000_000,
        }
    }
    fn ledger(mtu: u64, at: u64) -> RepairBudget {
        RepairBudget::new(BudgetDirection {
            tunnel: tunnel(), direction: WireDirection::ClientToServer,
        }, cfg(mtu), MonoNs(at)).unwrap()
    }
    #[test]
    fn r2_budget_pacer_eight_mtu_and_unreported_fresh_not_blocked() {
        let mut b = ledger(1500, 0);
        b.enable_opportunistic_v3();
        assert_eq!(b.snapshot().pacer_burst_limit, 12_000);
        for i in 0..8 {
            let c = candidate(i, 2);
            let id = b.reserve(&c, 1500, MonoNs(2)).unwrap();
            b.on_send_result(id, RepairSendResult::Accepted, MonoNs(2)).unwrap();
        }
        assert_eq!(b.snapshot().pacer_tokens, 0);
        // Stage-0 repair may use the existing byte allowance, but cannot
        // create token debt or block a new definitely accepted first send.
        let ninth = candidate(9, 3);
        let id = b.reserve(&ninth, 1500, MonoNs(3)).unwrap();
        b.on_send_result(id, RepairSendResult::Accepted, MonoNs(3)).unwrap();
        assert_eq!(b.snapshot().pacer_tokens, 0);
        b.on_fresh_accepted(500_000, MonoNs(4)).unwrap();
        assert_eq!(b.snapshot().fresh_confirmed_bytes, 500_000);
        assert_eq!(b.snapshot().epoch_repair_limit, 50_000);
        assert_eq!(b.snapshot().charged_repair_bytes, 13_500);
        assert!(b.snapshot().pacer_tokens <= b.snapshot().pacer_burst_limit);
    }
    #[test]
    fn r2_plan027_v3_ten_percent_of_f_and_distinct_total_ratio(){
        let mut b=ledger(60_000,0);
        b.enable_opportunistic_v3();
        b.on_fresh_accepted(1_000_000,MonoNs(1)).unwrap();
        assert_eq!(b.snapshot().epoch_repair_limit,100_000);
        for (pn,size) in [(1,60_000),(2,40_000)]{
            let c=candidate(pn,2);
            let id=b.reserve(&c,size,MonoNs(2)).unwrap();
            b.on_send_result(id,RepairSendResult::Accepted,MonoNs(2)).unwrap();
        }
        let s=b.snapshot();
        assert_eq!(s.charged_repair_bytes,100_000);
        assert_eq!(s.charged_repair_bytes*10,s.fresh_confirmed_bytes);
        let control_bytes=10_000;
        let total=s.fresh_confirmed_bytes+s.charged_repair_bytes+control_bytes;
        assert_eq!(total,1_110_000);
        assert!(s.charged_repair_bytes*10<total);
    }
    #[test]
    fn r2_budget_sparse_32k_absolute_floor_not_percentage_or_sum() {
        let mut b = ledger(4_000, 0);
        assert_eq!(b.snapshot().epoch_repair_limit, 32_768);
        for i in 0..8 {
            let c = candidate(i, 1);
            let id = b.reserve(&c, 4_000, MonoNs(1)).unwrap();
            b.on_send_result(id, RepairSendResult::Accepted, MonoNs(1)).unwrap();
        }
        assert_eq!(b.snapshot().charged_repair_bytes, 32_000);
        // Sufficient tokens do not bypass the byte quota.
        b.on_timer(MonoNs(500_000_001)).unwrap();
        let c = candidate(99, 500_000_001);
        assert_eq!(b.reserve(&c, 1_000, MonoNs(500_000_001)),
            Err(BudgetError::QuotaExhausted));
        // Fresh is not held up by an exhausted repair budget.
        b.on_fresh_accepted(100, MonoNs(500_000_001)).unwrap();
        assert_eq!(b.snapshot().fresh_confirmed_bytes, 100);
        assert_eq!(b.snapshot().epoch_repair_limit, 32_768);
    }
    #[test]
    fn r2_budget_high_rate_ten_percent_integer_and_epoch_absolute_cap() {
        let mut b = ledger(60_000, 0);
        b.on_fresh_accepted(1_000_000, MonoNs(1)).unwrap();
        assert_eq!(b.snapshot().epoch_repair_limit, 100_000);
        for (i, bytes) in [(1, 60_000), (2, 40_000)] {
            let c = candidate(i, 2);
            let id = b.reserve(&c, bytes, MonoNs(2)).unwrap();
            b.on_send_result(id, RepairSendResult::Accepted, MonoNs(2)).unwrap();
        }
        assert_eq!(b.snapshot().charged_repair_bytes, 100_000);
        let c = candidate(3, 2);
        assert_eq!(b.reserve(&c, 1, MonoNs(2)), Err(BudgetError::InvalidFrame));
        assert_eq!(b.reserve(&c, 4, MonoNs(2)), Err(BudgetError::QuotaExhausted));
        b.on_fresh_accepted(30_000, MonoNs(3)).unwrap();
        assert_eq!(b.snapshot().epoch_repair_limit, 103_000);
        let id = b.reserve(&c, 3_000, MonoNs(3)).unwrap();
        b.on_send_result(id, RepairSendResult::Accepted, MonoNs(3)).unwrap();
        assert_eq!(b.snapshot().charged_repair_bytes, 103_000);
    }
    #[test]
    fn r2_budget_uncertain_charged_notsent_refunds_once_and_generation_stays() {
        let mut b = ledger(1500, 0);
        let a = candidate(1, 1);
        let orig_pn = a.frozen().metadata().pn;
        let same_bytes = a.frozen().bytes().to_vec();
        let id = b.reserve(&a, 1400, MonoNs(1)).unwrap();
        assert_eq!(b.reserve(&a, 1400, MonoNs(1)), Err(BudgetError::DuplicateCandidate));
        b.on_send_result(id, RepairSendResult::Uncertain, MonoNs(2)).unwrap();
        assert_eq!(b.on_send_result(id, RepairSendResult::NotSent, MonoNs(3)),
            Err(BudgetError::StaleReservation));
        assert_eq!(b.snapshot().charged_repair_bytes, 1400);
        let other = candidate(2, 4);
        let id2 = b.reserve(&other, 1400, MonoNs(4)).unwrap();
        b.on_send_result(id2, RepairSendResult::NotSent, MonoNs(5)).unwrap();
        assert_eq!(b.snapshot().charged_repair_bytes, 1400);
        assert_eq!(b.snapshot().pending_count, 0);
        assert_eq!(a.frozen().metadata().pn, orig_pn);
        assert_eq!(a.frozen().bytes(), same_bytes);
        assert_eq!(a.frozen().metadata().seq, SeqOffset(1));
    }
    #[test]
    fn r2_budget_boundary_keeps_old_epoch_refunds_out_of_new_quota() {
        let base = 999_999_999;
        let mut b = ledger(1500, base - 1);
        let a = candidate(1, base);
        let id = b.reserve(&a, 1500, MonoNs(base)).unwrap();
        assert_eq!(b.snapshot().charged_repair_bytes, 1500);
        b.on_fresh_accepted(400_000, MonoNs(base)).unwrap();
        b.on_timer(MonoNs(1_000_000_000)).unwrap();
        assert_eq!(b.snapshot().epoch, 1);
        assert_eq!(b.snapshot().fresh_confirmed_bytes, 0);
        assert_eq!(b.snapshot().epoch_repair_limit, 32_768);
        b.on_send_result(id, RepairSendResult::NotSent, MonoNs(1_000_000_001)).unwrap();
        assert_eq!(b.snapshot().charged_repair_bytes, 0);
        assert!(b.snapshot().pacer_tokens <= 12_000);
        let later = candidate(2, 1_000_000_002);
        let new_id = b.reserve(&later, 1500, MonoNs(1_000_000_002)).unwrap();
        b.on_send_result(new_id, RepairSendResult::Accepted, MonoNs(1_000_000_002)).unwrap();
        assert_eq!(b.snapshot().charged_repair_bytes, 1500);
    }
    #[test]
    fn r2_budget_single_repair_stage_uses_existing_epoch_quota_without_second_stage(){
        let mut b=ledger(1500,0);
        for i in 0..8 {
            let c=candidate(i,2);
            assert_eq!(c.repair_attempt_stage(),0);
            let id=b.reserve(&c,1500,MonoNs(2)).unwrap();
            b.on_send_result(id,RepairSendResult::Accepted,MonoNs(2)).unwrap();
        }
        assert_eq!(b.snapshot().charged_repair_bytes,12_000);
        assert_eq!(b.snapshot().pacer_tokens,0);
        let extra=candidate(99,2);
        assert_eq!(extra.repair_attempt_stage(),0);
        assert_eq!(b.reserve(&extra,1500,MonoNs(2)),Err(BudgetError::BurstPaced));
        // Genuine time replenishes the smoothing budget without granting
        // any new ciphertext or extra repair attempt.
        let next=b.reserve(&extra,1500,MonoNs(100_000_002)).unwrap();
        b.on_send_result(next,RepairSendResult::Accepted,MonoNs(100_000_002)).unwrap();
        // Repair accounting never blocks fresh credit acquisition.
        b.on_fresh_accepted(100,MonoNs(3)).unwrap();
        assert_eq!(b.snapshot().fresh_confirmed_bytes,100);
    }

    #[test]
    fn r2_budget_capacity_timeout_conservative_debt_and_clock_reversal() {
        let mut cfg = cfg(1500);
        cfg.max_pending_reservations = 1;
        cfg.max_pending_bytes = 1500;
        cfg.io_timeout_ns = 10;
        let mut b = RepairBudget::new(BudgetDirection {
            tunnel:tunnel(), direction:WireDirection::ServerToClient,
        }, cfg, MonoNs(0)).unwrap();
        let a = candidate(1, 1);
        let id = b.reserve(&a, 1400, MonoNs(1)).unwrap();
        assert_eq!(b.reserve(&candidate(2, 1), 1400, MonoNs(1)),
            Err(BudgetError::NoCapacity));
        b.on_timer(MonoNs(11)).unwrap();
        assert_eq!(b.on_send_result(id, RepairSendResult::NotSent, MonoNs(12)),
            Err(BudgetError::StaleReservation));
        assert_eq!(b.snapshot().pending_count, 0);
        assert_eq!(b.snapshot().overdue_uncertain_count, 1);
        assert_eq!(b.snapshot().overdue_uncertain_bytes, 1400);
        assert_eq!(b.on_fresh_accepted(300, MonoNs(9)), Err(BudgetError::BackwardClock));
        b.on_timer(MonoNs(2_000_000_001)).unwrap();
        assert_eq!(b.snapshot().epoch_repair_limit, 32_768);
        // Legacy unknown syscall remains a conservative charge, never a refund.
        let c = candidate(3, 2_000_000_001);
        let reserved = b.reserve(&c, 1500, MonoNs(2_000_000_001)).unwrap();
        assert_eq!(b.snapshot().overdue_uncertain_bytes, 1400);
        b.on_send_result(reserved, RepairSendResult::Accepted, MonoNs(2_000_000_001)).unwrap();
    }
    #[test]
    fn r2_budget_rejects_bad_config_wrong_tunnel_and_expired_original() {
        let mut config = cfg(1500);
        config.io_timeout_ns = SECOND_NS + 1;
        assert!(matches!(RepairBudget::new(BudgetDirection {
            tunnel:tunnel(),direction:WireDirection::ClientToServer
        },config,MonoNs(0)),Err(BudgetError::InvalidConfig)));
        let mut b = ledger(1500, 0);
        let c = candidate(1, 1);
        assert_eq!(b.reserve(&c, 2000, MonoNs(1)),Err(BudgetError::InvalidFrame));
        assert_eq!(b.reserve(&c, 1500, MonoNs(30_000_000)),
            Err(BudgetError::ExpiredCandidate));
        let another = candidate(2, 30_000_001);
        let d = BudgetDirection { tunnel:TunnelKey{slot:99,generation:1},
            direction:WireDirection::ClientToServer };
        let mut wrong = RepairBudget::new(d,cfg(1500),MonoNs(0)).unwrap();
        assert_eq!(wrong.reserve(&another, 1500, MonoNs(30_000_001)),
            Err(BudgetError::WrongTunnel));
    }
}
