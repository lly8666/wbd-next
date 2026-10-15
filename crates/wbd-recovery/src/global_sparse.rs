//! R2 process-level repair quota broker. This is an **owner-local** pure
//! state machine, not a globally locked/atomic hotpath. An integration actor
//! may request bounded per-(TunnelKey,direction) grants; no separate client
//! receives a free copy of the sparse 32KiB allowance.
//!
//! All times are injected monotonic nanoseconds. Only *confirmed* data
//! first-transmits add F via RepairBudget; repair reserve/Uncertain/Accepted
//! consume their own per-direction cap AND the process absolute cap. Only
//! definitely NotSent refunds the ORIGINAL epoch; grant expiry/stop never
//! pretends an in-flight or uncertain send was not transmitted.
//!
//! M0 still owns process actor scheduling and the actual verified lane /
//! direction / byte-size mapping. No socket, PN/seal or global mutex here.
use std::collections::BTreeMap;
use crate::budget::{BudgetDirection, BudgetError, RepairBudget, RepairBudgetConfig,
                    ReservationId, WireDirection};
use crate::receipt::{AuthenticatedReceipt, ReceiptRouteScope, ScopedAuthenticatedReceipt, ReceiptState, Release, RepairCandidate, RepairSendResult};
use wbd_types::buffer_contract::FrozenRecordHandle;
use wbd_types::{DataError, MonoNs, TunnelKey};

const SECOND_NS: u64 = 1_000_000_000;

#[derive(Clone, Copy, Debug)]
pub struct GlobalRepairConfig {
    /// Process-wide aggregate hard limit, not multiplied per tunnel or lane.
    pub max_bytes_per_epoch: u64,
    pub max_directions: usize,
    pub max_grant_bytes: u64,
    /// <= one accounting epoch, grants also end at the epoch boundary.
    pub max_grant_lifetime_ns: u64,
    pub max_pending: usize,
    pub max_pending_bytes: u64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GlobalRepairError {
    InvalidConfig,
    NotRegistered,
    AlreadyRegistered,
    DirectionCapacity,
    GrantAlreadyActive,
    InvalidGrant,
    StaleGrant,
    GrantExhausted,
    GlobalCap,
    PendingCapacity,
    ClockReversed,
    ExhaustedId,
    InvalidBatch,
    DuplicateBatchId,
    StaleCandidate,
    WrongReceiptLane,
    WrongReceiptScope,
    Receipt(DataError),
    Local(BudgetError),
}
impl From<BudgetError> for GlobalRepairError {
    fn from(value: BudgetError) -> Self { Self::Local(value) }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd)]
pub struct GrantId(u64);
#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd)]
pub struct GlobalReservationId(u64);

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GrantLease {
    id: GrantId,
    direction: BudgetDirection,
    epoch: u64,
    expires_at: MonoNs,
    bytes: u64,
}
impl GrantLease {
    pub fn id(&self) -> GrantId { self.id }
    pub fn direction(&self) -> BudgetDirection { self.direction }
    pub fn epoch(&self) -> u64 { self.epoch }
    pub fn expires_at(&self) -> MonoNs { self.expires_at }
    pub fn bytes(&self) -> u64 { self.bytes }
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GlobalRepairSnapshot {
    pub epoch: u64,
    pub hard_cap: u64,
    pub held_unused_grants: u64,
    pub charged_repairs: u64,
    pub previous_epoch_charged: u64,
    pub overdue_uncertain_bytes: u64,
    pub overdue_uncertain_count: u64,
    pub registered_directions: usize,
    pub active_grants: usize,
    pub pending: usize,
    pub pending_bytes: u64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd)]
struct DirectionId {
    tunnel_slot: u32,
    tunnel_generation: u32,
    direction: u8,
}
impl DirectionId {
    fn new(d: BudgetDirection) -> Self {
        Self {
            tunnel_slot: d.tunnel.slot,
            tunnel_generation: d.tunnel.generation,
            direction: match d.direction {
                WireDirection::ClientToServer => 0,
                WireDirection::ServerToClient => 1,
            }
        }
    }
    fn tunnel(self) -> TunnelKey {
        TunnelKey { slot: self.tunnel_slot, generation: self.tunnel_generation }
    }
}
struct Grant {
    id: GrantId,
    epoch: u64,
    expiry: MonoNs,
    remaining: u64,
}
struct DirectionAccount {
    local: RepairBudget,
    receipt_route: Option<ReceiptRouteScope>,
    grant: Option<Grant>,
    io_timeout_ns: u64,
}
#[derive(Clone, Copy)]
struct Epoch {
    index: u64,
    held: u64,
    charged: u64,
}
impl Epoch {
    fn new(index: u64) -> Self { Self { index, held: 0, charged: 0 } }
}
#[derive(Clone, Copy)]
struct Pending {
    direction: DirectionId,
    grant_id: GrantId,
    local_id: ReservationId,
    lane: wbd_types::LaneKey,
    pn: wbd_types::RecordPn,
    epoch: u64,
    bytes: u64,
    until: MonoNs,
}

/// Single-owner mutable allocator. Grants let M0 compose an actor with bounded
/// batch admission instead of a mutex per data packet. It does not schedule
/// actual driver sends; ReceiptState::preflight is mandatory at integration.
pub struct GlobalRepairAllocator {
    config: GlobalRepairConfig,
    accounts: BTreeMap<DirectionId, DirectionAccount>,
    current: Epoch,
    previous: Option<Epoch>,
    pending: BTreeMap<GlobalReservationId, Pending>,
    pending_bytes: u64,
    now: MonoNs,
    next_grant: u64,
    next_reservation: u64,
    /// Lost send completion or client departure cannot refund an uncertain
    /// syscall. Hold conservative debt across epochs; an integrator must
    /// explicitly reset the whole stopped process owner to clear such debt.
    overdue_bytes: u64,
    // Current epoch charged already includes these same missing completions.
    // Exclude only this subset from the extra cross-epoch conservative debit.
    overdue_in_current: u64,
    overdue_count: u64,
}

impl GlobalRepairAllocator {
    pub fn new(config: GlobalRepairConfig, now: MonoNs)
        -> Result<Self, GlobalRepairError>
    {
        if config.max_bytes_per_epoch == 0 || config.max_directions == 0
            || config.max_grant_bytes == 0 || config.max_grant_lifetime_ns == 0
            || config.max_grant_lifetime_ns > SECOND_NS
            || config.max_pending == 0 || config.max_pending_bytes == 0
        {
            return Err(GlobalRepairError::InvalidConfig);
        }
        Ok(Self {
            config, accounts: BTreeMap::new(),
            current: Epoch::new(now.0 / SECOND_NS), previous: None,
            pending: BTreeMap::new(), pending_bytes: 0, now,
            next_grant: 0, next_reservation: 0,
            overdue_bytes: 0, overdue_in_current: 0, overdue_count: 0,
        })
    }

    /// Register one direction. Two directions of one TunnelKey have distinct
    /// local F/R 10% ledgers but draw from this SAME process absolute cap.
    pub fn register(&mut self, direction: BudgetDirection,
        local_config: RepairBudgetConfig, now: MonoNs)
        -> Result<(), GlobalRepairError>
    {
        self.advance(now)?;
        let key = DirectionId::new(direction);
        if self.accounts.contains_key(&key) {
            return Err(GlobalRepairError::AlreadyRegistered);
        }
        if self.accounts.len() >= self.config.max_directions {
            return Err(GlobalRepairError::DirectionCapacity);
        }
        let account = DirectionAccount {
            local: RepairBudget::new(direction, local_config, now)?,
            receipt_route: None,
            io_timeout_ns: local_config.io_timeout_ns,
            grant: None,
        };
        self.accounts.insert(key, account);
        Ok(())
    }

    /// Fresh has no reference to grants or repair capacity; it always updates
    /// the local first-transmission ledger, even with all repair quota held.
    pub fn on_fresh_accepted(&mut self, direction: BudgetDirection,
        wire_bytes: u64, now: MonoNs) -> Result<(), GlobalRepairError>
    {
        self.advance(now)?;
        let account = self.accounts.get_mut(&DirectionId::new(direction))
            .ok_or(GlobalRepairError::NotRegistered)?;
        account.local.on_fresh_accepted(wire_bytes, now)?;
        Ok(())
    }

    fn available_global(&self) -> u64 {
        self.config.max_bytes_per_epoch
            .saturating_sub(self.overdue_bytes.saturating_sub(self.overdue_in_current))
            .saturating_sub(self.current.held)
            .saturating_sub(self.current.charged)
    }

    fn advance(&mut self, now: MonoNs) -> Result<(), GlobalRepairError> {
        if now < self.now { return Err(GlobalRepairError::ClockReversed); }
        self.now = now;
        // Timer processing is slow owner work, bounded by registered directions
        // and max_pending, NOT called on every fresh packet by the runtime.
        for a in self.accounts.values_mut() {
            a.local.on_timer(now)?;
        }
        let expired: Vec<_> = self.pending.iter().filter_map(|(id, p)| {
            (now >= p.until).then_some(*id)
        }).collect();
        for id in expired {
            let p = self.pending.remove(&id).expect("expired member exists");
            self.pending_bytes -= p.bytes;
            self.overdue_bytes = self.overdue_bytes.saturating_add(p.bytes);
            if p.epoch == self.current.index {
                self.overdue_in_current = self.overdue_in_current.saturating_add(p.bytes);
            }
            self.overdue_count = self.overdue_count.saturating_add(1);
        }
        let epoch = now.0 / SECOND_NS;
        let mut unclaimed = 0u64;
        for account in self.accounts.values_mut() {
            if account.grant.as_ref().is_some_and(|g| {
                now >= g.expiry || g.epoch != epoch
            }) {
                unclaimed += account.grant.take().expect("grant present").remaining;
            }
        }
        self.current.held -= unclaimed;
        if epoch != self.current.index {
            let old = self.current;
            self.current = Epoch::new(epoch);
            self.overdue_in_current = 0;
            self.previous = if old.index.checked_add(1) == Some(epoch) {
                Some(old)
            } else {
                None
            };
        }
        Ok(())
    }

    /// A grant is a finite reservation of global budget, so 200 registered
    /// idle clients cannot each silently mint their own 32KiB. Unused grants
    /// expire or can be explicitly revoked; submitted bytes never expire
    /// merely because their grant does.
    pub fn grant(&mut self, direction: BudgetDirection, bytes: u64,
        lifetime_ns: u64, now: MonoNs) -> Result<GrantLease, GlobalRepairError>
    {
        self.advance(now)?;
        let key = DirectionId::new(direction);
        let account = self.accounts.get(&key).ok_or(GlobalRepairError::NotRegistered)?;
        if account.grant.is_some() { return Err(GlobalRepairError::GrantAlreadyActive); }
        if bytes == 0 || bytes > self.config.max_grant_bytes
            || lifetime_ns == 0 || lifetime_ns > self.config.max_grant_lifetime_ns
        { return Err(GlobalRepairError::InvalidGrant); }
        if bytes > self.available_global() { return Err(GlobalRepairError::GlobalCap); }
        let next = self.next_grant.checked_add(1).ok_or(GlobalRepairError::ExhaustedId)?;
        let boundary = (self.current.index.saturating_add(1))
            .saturating_mul(SECOND_NS);
        let expiry = MonoNs(now.0.checked_add(lifetime_ns)
            .ok_or(GlobalRepairError::InvalidGrant)?.min(boundary));
        if expiry <= now { return Err(GlobalRepairError::InvalidGrant); }
        self.next_grant = next;
        self.current.held += bytes;
        self.accounts.get_mut(&key).expect("registered").grant = Some(Grant {
            id: GrantId(next), epoch: self.current.index, expiry, remaining: bytes,
        });
        Ok(GrantLease {
            id: GrantId(next), direction, epoch: self.current.index,
            expires_at: expiry, bytes,
        })
    }

    pub fn revoke(&mut self, lease: GrantLease, now: MonoNs)
        -> Result<(), GlobalRepairError>
    {
        self.advance(now)?;
        let acc = self.accounts.get_mut(&DirectionId::new(lease.direction))
            .ok_or(GlobalRepairError::StaleGrant)?;
        if acc.grant.as_ref().is_none_or(|g| g.id != lease.id || g.epoch != lease.epoch) {
            return Err(GlobalRepairError::StaleGrant);
        }
        let remaining = acc.grant.take().expect("validated").remaining;
        self.current.held -= remaining;
        Ok(())
    }

    pub fn reserve<H: FrozenRecordHandle>(&mut self, lease: GrantLease,
        candidate: &RepairCandidate<H>, wire_bytes: u64, now: MonoNs)
        -> Result<GlobalReservationId, GlobalRepairError>
    {
        self.advance(now)?;
        let key = DirectionId::new(lease.direction);
        let acc = self.accounts.get(&key).ok_or(GlobalRepairError::NotRegistered)?;
        let g = acc.grant.as_ref().ok_or(GlobalRepairError::StaleGrant)?;
        if g.id != lease.id || g.epoch != lease.epoch || g.expiry != lease.expires_at
            || lease.epoch != self.current.index
        {
            return Err(GlobalRepairError::StaleGrant);
        }
        if wire_bytes == 0 || wire_bytes > g.remaining {
            return Err(GlobalRepairError::GrantExhausted);
        }
        if self.pending.len() >= self.config.max_pending
            || wire_bytes > self.config.max_pending_bytes.saturating_sub(self.pending_bytes)
        {
            return Err(GlobalRepairError::PendingCapacity);
        }
        let next = self.next_reservation.checked_add(1)
            .ok_or(GlobalRepairError::ExhaustedId)?;
        let until = MonoNs(now.0.checked_add(acc.io_timeout_ns)
            .ok_or(GlobalRepairError::InvalidConfig)?);
        // Account is owned by the one process owner. No global mutex or clone
        // of the original immutable ciphertext is needed for this reservation.
        let local_id = self.accounts.get_mut(&key).expect("registered")
            .local.reserve(candidate, wire_bytes, now)?;
        self.next_reservation = next;
        let grant = self.accounts.get_mut(&key).expect("registered")
            .grant.as_mut().expect("grant verified");
        grant.remaining -= wire_bytes;
        self.current.held -= wire_bytes;
        self.current.charged += wire_bytes;
        self.pending_bytes += wire_bytes;
        self.pending.insert(GlobalReservationId(next), Pending {
            direction: key, grant_id: lease.id, local_id,
            lane: candidate.frozen().metadata().lane, pn: candidate.pn(),
            epoch: self.current.index, bytes: wire_bytes, until,
        });
        Ok(GlobalReservationId(next))
    }

    /// Guard late ACK versus queued candidate before a repair reservation.
    /// M0 must re-check the receipt immediately before the actual syscall.
    pub fn reserve_if_still_missing<H: FrozenRecordHandle>(
        &mut self, lease: GrantLease, shadow: &ReceiptState<H>,
        candidate: &RepairCandidate<H>, wire_bytes: u64, now: MonoNs,
    ) -> Result<GlobalReservationId, GlobalRepairError> {
        if shadow.lane() != candidate.frozen().metadata().lane
            || shadow.lane().tunnel != lease.direction.tunnel
            || !shadow.preflight(candidate, now)
        {
            return Err(GlobalRepairError::StaleCandidate);
        }
        self.reserve(lease, candidate, wire_bytes, now)
    }

    /// Strictly scoped variant of the legacy last-chance preflight. A
    /// caller-supplied scope must equal the owner's previously pinned M0
    /// session binding before any reservation or process cap debit. This
    /// function does NOT cryptographically authenticate the caller-supplied
    /// route and never claims that a kernel Accepted means peer delivery.
    pub fn reserve_scoped_if_still_missing<H: FrozenRecordHandle>(
        &mut self, lease: GrantLease, pinned: ReceiptRouteScope,
        shadow: &ReceiptState<H>, candidate: &RepairCandidate<H>,
        wire_bytes: u64, now: MonoNs,
    ) -> Result<GlobalReservationId, GlobalRepairError> {
        let dir=DirectionId::new(lease.direction);
        if self.accounts.get(&dir).and_then(|a| a.receipt_route)!=Some(pinned)
            || pinned.outbound_lane()!=shadow.lane()
            || pinned.outbound_direction()!=lease.direction.direction
            || !pinned.contains_data_pn(candidate.pn()) {
            return Err(GlobalRepairError::WrongReceiptScope);
        }
        self.reserve_if_still_missing(lease,shadow,candidate,wire_bytes,now)
    }

    /// A typed authenticated receipt can retire a shadow but MUST NOT
    /// refund a repair reservation: the driver might have transmitted it.
    /// M0 owns the post-AEAD trust boundary and external direction binding.
    pub fn observe_authenticated_receipt<H: FrozenRecordHandle>(
        &mut self, direction: BudgetDirection, shadow: &mut ReceiptState<H>,
        receipt: &AuthenticatedReceipt, now: MonoNs,
    ) -> Result<Vec<Release<H>>, GlobalRepairError> {
        if shadow.lane().tunnel != direction.tunnel
            || receipt.verified_lane() != shadow.lane()
        {
            return Err(GlobalRepairError::WrongReceiptLane);
        }
        if !self.accounts.contains_key(&DirectionId::new(direction)) {
            return Err(GlobalRepairError::NotRegistered);
        }
        self.advance(now)?;
        shadow.on_receipt(receipt, now).map_err(GlobalRepairError::Receipt)
    }


    /// Bind the trusted M0-originated session once, before grants/reservations.
    /// A changed epoch or lane must retire the old tunnel then register anew;
    /// never overwrite an active generation containing in-flight callbacks.
    pub fn bind_receipt_route(&mut self,direction:BudgetDirection,
        route:ReceiptRouteScope,now:MonoNs)->Result<(),GlobalRepairError> {
        if route.outbound_lane().tunnel!=direction.tunnel
            || route.outbound_direction()!=direction.direction {
            return Err(GlobalRepairError::WrongReceiptScope);
        }
        self.advance(now)?;
        let key=DirectionId::new(direction);
        let acc=self.accounts.get(&key).ok_or(GlobalRepairError::NotRegistered)?;
        if let Some(old)=acc.receipt_route {
            return if old==route {Ok(())} else {Err(GlobalRepairError::WrongReceiptScope)};
        }
        if acc.grant.is_some() || self.pending.values().any(|p|p.direction==key) {
            return Err(GlobalRepairError::WrongReceiptScope);
        }
        self.accounts.get_mut(&key).expect("registered").receipt_route=Some(route);
        Ok(())
    }

    /// Checked reverse-route receipt; never turns kernel Accepted/TCP ACK into
    /// peer delivery. Requires exact independently pinned session identity.
    pub fn observe_scoped_receipt<H:FrozenRecordHandle>(
        &mut self,direction:BudgetDirection,shadow:&mut ReceiptState<H>,
        scoped:&ScopedAuthenticatedReceipt,now:MonoNs
    )->Result<Vec<Release<H>>,GlobalRepairError> {
        let key=DirectionId::new(direction);
        if self.accounts.get(&key).and_then(|a|a.receipt_route)!=Some(scoped.route())
            || scoped.route().outbound_lane()!=shadow.lane()
            || scoped.route().outbound_direction()!=direction.direction {
            return Err(GlobalRepairError::WrongReceiptScope);
        }
        self.observe_authenticated_receipt(direction,shadow,scoped.receipt(),now)
    }

    /// An ordered mixed-client batch must validate all of its independently
    /// pinned session, generation, direction, lane and PN scopes before ANY
    /// NotSent refund. Stack array <=32; no global mutex or heap clone.
    pub fn complete_scoped_batch(&mut self,
        slots:&[(GlobalReservationId,ReceiptRouteScope)],
        outcome:ValidatedRepairBatchOutcome,now:MonoNs
    )->Result<BatchCompletionCounts,GlobalRepairError> {
        if slots.len()>32 || slots.len()!=outcome.total {
            return Err(GlobalRepairError::InvalidBatch);
        }
        let mut ids=[GlobalReservationId(0);32];
        for (i,(id,scope)) in slots.iter().enumerate() {
            if ids[..i].contains(id) {return Err(GlobalRepairError::DuplicateBatchId);}
            let p=self.pending.get(id).ok_or(GlobalRepairError::StaleGrant)?;
            let acc=self.accounts.get(&p.direction).ok_or(GlobalRepairError::StaleGrant)?;
            if acc.receipt_route!=Some(*scope)
                || scope.outbound_lane()!=p.lane
                || DirectionId::new(BudgetDirection {
                    tunnel:scope.outbound_lane().tunnel,
                    direction:scope.outbound_direction()
                })!=p.direction
                || !scope.contains_data_pn(p.pn) {
                return Err(GlobalRepairError::WrongReceiptScope);
            }
            ids[i]=*id;
        }
        self.complete_batch(&ids[..slots.len()],outcome,now)
    }

    /// A completion is consumed exactly once, never coerced into proof of peer
    /// delivery. NotSent refunds the original epoch and, only if still live
    /// inside the same epoch, the original grant. An old grant never creates
    /// credit at the next 1s boundary.
    pub fn complete(&mut self, id: GlobalReservationId,
        result: RepairSendResult, now: MonoNs) -> Result<(), GlobalRepairError>
    {
        self.advance(now)?;
        let p = *self.pending.get(&id).ok_or(GlobalRepairError::StaleGrant)?;
        let acc = self.accounts.get_mut(&p.direction)
            .ok_or(GlobalRepairError::StaleGrant)?;
        acc.local.on_send_result(p.local_id, result, now)?;
        self.pending.remove(&id);
        self.pending_bytes -= p.bytes;
        if result == RepairSendResult::NotSent {
            if p.epoch == self.current.index {
                self.current.charged -= p.bytes;
                if let Some(g) = acc.grant.as_mut() {
                    if g.id == p.grant_id && g.epoch == p.epoch {
                        g.remaining += p.bytes;
                        self.current.held += p.bytes;
                    }
                }
            } else if let Some(old) = self.previous.as_mut() {
                if old.index == p.epoch { old.charged -= p.bytes; }
            }
        }
        Ok(())
    }

    /// Hard bound for client departure: remove both directions and their
    /// outstanding grant metadata. Unknown kernel completions remain charged
    /// and are treated conservatively as uncertain; late callbacks are stale.
    pub fn retire_tunnel(&mut self, tunnel: TunnelKey, now: MonoNs)
        -> Result<usize, GlobalRepairError>
    {
        self.advance(now)?;
        let keys: Vec<_> = self.accounts.keys().copied()
            .filter(|id| id.tunnel() == tunnel).collect();
        for key in &keys {
            let acc = self.accounts.remove(key).expect("selected account");
            if let Some(g) = acc.grant { self.current.held -= g.remaining; }
        }
        let retired: Vec<_> = self.pending.iter().filter_map(|(id, p)| {
            keys.contains(&p.direction).then_some(*id)
        }).collect();
        for id in retired {
            let p = self.pending.remove(&id).expect("retired pending");
            self.pending_bytes -= p.bytes;
            self.overdue_bytes = self.overdue_bytes.saturating_add(p.bytes);
            if p.epoch == self.current.index {
                self.overdue_in_current = self.overdue_in_current.saturating_add(p.bytes);
            }
            self.overdue_count = self.overdue_count.saturating_add(1);
        }
        Ok(keys.len())
    }

    pub fn on_timer(&mut self, now: MonoNs) -> Result<(), GlobalRepairError> {
        self.advance(now)
    }
    pub fn local_snapshot(&self, direction: BudgetDirection)
        -> Option<crate::budget::BudgetSnapshot>
    {
        self.accounts.get(&DirectionId::new(direction)).map(|a| a.local.snapshot())
    }
    pub fn snapshot(&self) -> GlobalRepairSnapshot {
        GlobalRepairSnapshot {
            epoch: self.current.index, hard_cap: self.config.max_bytes_per_epoch,
            held_unused_grants: self.current.held,
            charged_repairs: self.current.charged,
            previous_epoch_charged: self.previous.map_or(0, |e| e.charged),
            overdue_uncertain_bytes: self.overdue_bytes,
            overdue_uncertain_count: self.overdue_count,
            registered_directions: self.accounts.len(),
            active_grants: self.accounts.values().filter(|a| a.grant.is_some()).count(),
            pending: self.pending.len(), pending_bytes: self.pending_bytes,
        }
    }
}


// === R2-M2-GLOBAL-BATCH-COMPLETION-003 ===
/// Trusted M0 platform adapter is responsible for verifying the driver's
/// statement; ProvenNotAttempted requires POSITIVE evidence a suffix was NOT
/// submitted. Ambiguous syscall remainder must use Unproven and remain charged.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum BatchSuffixEvidence {
    Unproven,
    ProvenNotAttempted,
}

/// Validated SHAPE of the outcome for independently reserved repair slots.
/// Prefix [0, accepted_prefix) had driver submission success; optional single
/// ambiguous slot MUST be at accepted_prefix. Suffix is either positively
/// known not submitted or conservatively retained. Driver Accepted is NOT
/// authenticated receipt or peer delivery.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ValidatedRepairBatchOutcome {
    total: usize,
    accepted_prefix: usize,
    uncertain_at: Option<usize>,
    suffix_evidence: BatchSuffixEvidence,
}
impl ValidatedRepairBatchOutcome {
    pub fn checked(
        total: usize,
        accepted_prefix: usize,
        uncertain_at: Option<usize>,
        suffix_evidence: BatchSuffixEvidence,
    ) -> Result<Self, GlobalRepairError> {
        if total > 32 || accepted_prefix > total
            || uncertain_at.is_some_and(|at| at != accepted_prefix || at >= total)
        {
            return Err(GlobalRepairError::InvalidBatch);
        }
        Ok(Self { total, accepted_prefix, uncertain_at, suffix_evidence })
    }
    pub fn all_accepted(total: usize) -> Result<Self, GlobalRepairError> {
        Self::checked(total, total, None, BatchSuffixEvidence::Unproven)
    }
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct BatchCompletionCounts {
    pub accepted: usize,
    pub uncertain: usize,
    pub definitely_not_sent: usize,
    /// No reliable non-send proof; still pending and charged, timeout bounded.
    pub held_unproven: usize,
}
impl GlobalRepairAllocator {
    /// Apply 0..=32 unique independently reserved repair IDs in original
    /// driver frame order, after FULL validation, without any allocation,
    /// global mutex, PN mutation, or fresh queue handling.
    /// M0 must derive ProvenNotAttempted from a verified platform observation,
    /// never infer it solely from a short/ambiguous syscall return.
    pub fn complete_batch(
        &mut self,
        ordered: &[GlobalReservationId],
        outcome: ValidatedRepairBatchOutcome,
        now: MonoNs,
    ) -> Result<BatchCompletionCounts, GlobalRepairError> {
        if ordered.len() > 32 || ordered.len() != outcome.total {
            return Err(GlobalRepairError::InvalidBatch);
        }
        for (i, id) in ordered.iter().enumerate() {
            if ordered[..i].contains(id) {
                return Err(GlobalRepairError::DuplicateBatchId);
            }
            if !self.pending.contains_key(id) {
                return Err(GlobalRepairError::StaleGrant);
            }
        }
        self.advance(now)?;
        // No acceptance after an original IO timeout/retire: late completions
        // are stale and the associated unknown send remains conservatively
        // charged against the process cap.
        if ordered.iter().any(|id| !self.pending.contains_key(id)) {
            return Err(GlobalRepairError::StaleGrant);
        }
        let mut counts=BatchCompletionCounts {
            accepted:0, uncertain:0, definitely_not_sent:0, held_unproven:0
        };
        for (i, id) in ordered.iter().enumerate() {
            if i < outcome.accepted_prefix {
                self.complete(*id,RepairSendResult::Accepted,now)?;
                counts.accepted+=1;
            } else if outcome.uncertain_at == Some(i) {
                self.complete(*id,RepairSendResult::Uncertain,now)?;
                counts.uncertain+=1;
            } else if outcome.suffix_evidence == BatchSuffixEvidence::ProvenNotAttempted {
                self.complete(*id,RepairSendResult::NotSent,now)?;
                counts.definitely_not_sent+=1;
            } else {
                counts.held_unproven+=1;
            }
        }
        Ok(counts)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;
    use wbd_types::{BufferKey, LaneKey, RecordPn, SeqOffset};
    use wbd_types::buffer_contract::{BufferOrigin, FrozenMetadata};
    use crate::receipt::{ReceiptConfig, ReceiptState};

    #[derive(Clone)]
    struct FakeFrozen {
        data: Arc<[u8]>, metadata: FrozenMetadata, origin: BufferOrigin,
    }
    impl FrozenRecordHandle for FakeFrozen {
        fn bytes(&self) -> &[u8] { &self.data }
        fn origin(&self) -> BufferOrigin { self.origin }
        fn metadata(&self) -> FrozenMetadata { self.metadata }
    }
    fn tunnel(slot: u32) -> TunnelKey { TunnelKey { slot, generation: 2 } }
    fn dir(slot: u32, direction: WireDirection) -> BudgetDirection {
        BudgetDirection { tunnel: tunnel(slot), direction }
    }
    fn cfg() -> RepairBudgetConfig {
        RepairBudgetConfig {
            outer_mtu: 1400, max_repair_bytes_per_epoch: 100_000,
            max_pending_reservations: 16, max_pending_bytes: 16_800,
            io_timeout_ns: 20_000_000,
        }
    }
    fn global(cap: u64, max_directions: usize) -> GlobalRepairAllocator {
        GlobalRepairAllocator::new(GlobalRepairConfig {
            max_bytes_per_epoch: cap, max_directions,
            max_grant_bytes: cap, max_grant_lifetime_ns: 500_000_000,
            max_pending: 16, max_pending_bytes: 16_800,
        }, MonoNs(0)).unwrap()
    }
    fn add(b: &mut GlobalRepairAllocator, d: BudgetDirection, now: u64) {
        b.register(d,cfg(),MonoNs(now)).unwrap();
    }
    fn candidate(d: BudgetDirection, pn: u64, at: u64) -> RepairCandidate<FakeFrozen> {
        let lane=LaneKey {tunnel:d.tunnel,slot:1,generation:1};
        let original=FakeFrozen {
            data:Arc::from([11,12,13,14].as_slice()),
            metadata:FrozenMetadata {
                lane,pn:RecordPn(pn),seq:SeqOffset(pn),carrier_snapshot:88
            },
            origin:BufferOrigin {owner_arena:d.tunnel.slot,
                key:BufferKey{slot:pn as u32,generation:5}},
        };
        let mut receipt=ReceiptState::new(lane,ReceiptConfig {
            max_shadow_entries:2,pto_ns:1,reorder_window_ns:1
        }).unwrap();
        receipt.on_sent(original,MonoNs(at-1),
            MonoNs(at.saturating_add(200_000_000))).unwrap();
        receipt.on_timer(MonoNs(at)).candidates.remove(0)
    }

    #[test]
    fn r2_global_sparse_no_f_per_client_multiplier_and_two_directions() {
        let a=dir(1,WireDirection::ClientToServer);
        let b=dir(2,WireDirection::ClientToServer);
        let back=dir(1,WireDirection::ServerToClient);
        let mut broker=global(3200,3);
        for d in [a,b,back] { add(&mut broker,d,0); }
        let g1=broker.grant(a,1400,100_000_000,MonoNs(1)).unwrap();
        let g2=broker.grant(b,1400,100_000_000,MonoNs(1)).unwrap();
        assert_eq!(broker.grant(back,1400,100_000_000,MonoNs(1)),
            Err(GlobalRepairError::GlobalCap));
        let c=candidate(a,1,1);
        let r=broker.reserve(g1,&c,1400,MonoNs(1)).unwrap();
        broker.complete(r,RepairSendResult::Accepted,MonoNs(1)).unwrap();
        assert_eq!(broker.snapshot().charged_repairs,1400);
        // No prior F, but a sparse direction can repair within the GLOBAL cap.
        let x=candidate(b,2,1);
        let rb=broker.reserve(g2,&x,1400,MonoNs(1)).unwrap();
        broker.complete(rb,RepairSendResult::Uncertain,MonoNs(1)).unwrap();
        assert_eq!(broker.snapshot().charged_repairs,2800);
        assert_eq!(broker.snapshot().held_unused_grants,0);
        assert_eq!(broker.local_snapshot(a).unwrap().fresh_confirmed_bytes,0);
        assert_eq!(broker.local_snapshot(back).unwrap().fresh_confirmed_bytes,0);
        assert_eq!(broker.grant(back,500,100_000_000,MonoNs(2)),
            Err(GlobalRepairError::GlobalCap));
    }
    #[test]
    fn r2_global_grant_expiry_revoke_never_refunds_submitted_bytes() {
        let a=dir(1,WireDirection::ClientToServer);
        let b=dir(2,WireDirection::ServerToClient);
        let mut broker=global(3000,2);
        add(&mut broker,a,0);add(&mut broker,b,0);
        let ga=broker.grant(a,2000,10,MonoNs(1)).unwrap();
        let c=candidate(a,1,1);
        let id=broker.reserve(ga,&c,1400,MonoNs(1)).unwrap();
        broker.on_timer(MonoNs(11)).unwrap(); // revoke 600 unspent
        assert_eq!(broker.snapshot().charged_repairs,1400);
        assert_eq!(broker.snapshot().held_unused_grants,0);
        assert_eq!(broker.reserve(ga,&c,1400,MonoNs(11)),
            Err(GlobalRepairError::StaleGrant));
        let gb=broker.grant(b,1500,10,MonoNs(12)).unwrap();
        assert_eq!(broker.snapshot().charged_repairs,1400);
        assert_eq!(broker.snapshot().held_unused_grants,1500);
        broker.complete(id,RepairSendResult::Uncertain,MonoNs(13)).unwrap();
        broker.revoke(gb,MonoNs(13)).unwrap();
        assert_eq!(broker.snapshot().held_unused_grants,0);
        assert_eq!(broker.snapshot().charged_repairs,1400);
        assert_eq!(broker.revoke(gb,MonoNs(13)),Err(GlobalRepairError::StaleGrant));
    }
    #[test]
    fn r2_global_notsent_refund_same_epoch_and_duplicate_completion() {
        let d=dir(1,WireDirection::ClientToServer);
        let mut b=global(1400,1);add(&mut b,d,0);
        let lease=b.grant(d,1400,100_000,MonoNs(1)).unwrap();
        let c=candidate(d,1,1);
        let id=b.reserve(lease,&c,1400,MonoNs(1)).unwrap();
        assert_eq!(b.snapshot().charged_repairs,1400);
        b.complete(id,RepairSendResult::NotSent,MonoNs(2)).unwrap();
        assert_eq!(b.snapshot().held_unused_grants,1400);
        assert_eq!(b.snapshot().charged_repairs,0);
        assert_eq!(b.complete(id,RepairSendResult::Accepted,MonoNs(2)),
            Err(GlobalRepairError::StaleGrant));
        let other=candidate(d,2,3);
        let id2=b.reserve(lease,&other,1400,MonoNs(3)).unwrap();
        b.complete(id2,RepairSendResult::Accepted,MonoNs(4)).unwrap();
        assert_eq!(b.snapshot().charged_repairs,1400);
    }
    #[test]
    fn r2_global_old_epoch_notsent_does_not_fund_new_grant() {
        let d=dir(1,WireDirection::ClientToServer);
        let mut b=global(1400,1);add(&mut b,d,999_999_980);
        let lease=b.grant(d,1400,1000,MonoNs(999_999_980)).unwrap();
        let c=candidate(d,3,999_999_981);
        let id=b.reserve(lease,&c,1400,MonoNs(999_999_981)).unwrap();
        b.on_timer(MonoNs(1_000_000_000)).unwrap();
        assert_eq!(b.snapshot().epoch,1);
        assert_eq!(b.snapshot().charged_repairs,0);
        assert_eq!(b.snapshot().previous_epoch_charged,1400);
        b.complete(id,RepairSendResult::NotSent,MonoNs(1_000_000_001)).unwrap();
        assert_eq!(b.snapshot().previous_epoch_charged,0);
        assert_eq!(b.snapshot().held_unused_grants,0);
        assert_eq!(b.snapshot().charged_repairs,0);
        let lease2=b.grant(d,1400,100_000,MonoNs(1_000_000_002)).unwrap();
        assert_ne!(lease2.id,lease.id);
    }
    #[test]
    fn r2_global_aggregate_cap_two_epochs_and_grant_boundary_fail_closed() {
        let a=dir(1,WireDirection::ClientToServer);
        let b=dir(2,WireDirection::ServerToClient);
        let mut x=global(1400,2);add(&mut x,a,0);add(&mut x,b,0);
        let early=x.grant(a,1400,100_000,MonoNs(999_999_990)).unwrap();
        assert_eq!(early.expires_at,MonoNs(1_000_000_000));
        assert_eq!(x.grant(b,1400,100_000,MonoNs(999_999_991)),
            Err(GlobalRepairError::GlobalCap));
        x.on_timer(MonoNs(1_000_000_000)).unwrap();
        let second=x.grant(b,1400,100_000,MonoNs(1_000_000_000)).unwrap();
        assert_ne!(early.id,second.id);
        assert_eq!(x.snapshot().held_unused_grants,1400);
        assert_eq!(x.reserve(early,&candidate(a,2,1_000_000_000),1400,MonoNs(1_000_000_000)),
            Err(GlobalRepairError::StaleGrant));
    }
    #[test]
    fn r2_global_uncertain_timeout_client_departure_bounded_and_no_fresh_hol() {
        let a=dir(1,WireDirection::ClientToServer);
        let b=dir(1,WireDirection::ServerToClient);
        let c=dir(2,WireDirection::ClientToServer);
        let mut x=global(4200,2);
        add(&mut x,a,0);add(&mut x,b,0);
        assert_eq!(x.register(c,cfg(),MonoNs(0)),Err(GlobalRepairError::DirectionCapacity));
        let ga=x.grant(a,1400,100_000_000,MonoNs(1)).unwrap();
        let gb=x.grant(b,1400,100_000_000,MonoNs(1)).unwrap();
        let id=x.reserve(ga,&candidate(a,1,1),1400,MonoNs(1)).unwrap();
        x.on_fresh_accepted(b,20_000,MonoNs(2)).unwrap();
        assert_eq!(x.local_snapshot(b).unwrap().fresh_confirmed_bytes,20_000);
        assert_eq!(x.retire_tunnel(tunnel(1),MonoNs(3)).unwrap(),2);
        assert_eq!(x.snapshot().registered_directions,0);
        assert_eq!(x.snapshot().pending,0);
        assert_eq!(x.snapshot().held_unused_grants,0);
        assert_eq!(x.snapshot().charged_repairs,1400);
        assert_eq!(x.snapshot().overdue_uncertain_bytes,1400);
        assert_eq!(x.complete(id,RepairSendResult::NotSent,MonoNs(4)),
            Err(GlobalRepairError::StaleGrant));
        assert_eq!(x.revoke(gb,MonoNs(4)),Err(GlobalRepairError::StaleGrant));
        add(&mut x,c,4);
        assert_eq!(x.grant(c,4200,100_000,MonoNs(5)),Err(GlobalRepairError::GlobalCap));
        // Departed pending send is already charged in current epoch, not twice.
        assert!(x.grant(c,2800,100_000,MonoNs(5)).is_ok());
    }
    #[test]
    fn r2_global_pending_timeout_retains_debt_and_no_stale_client_reuse() {
        let a=dir(1,WireDirection::ClientToServer);
        let mut x=global(2800,1);add(&mut x,a,0);
        let grant=x.grant(a,2800,100_000_000,MonoNs(1)).unwrap();
        let id=x.reserve(grant,&candidate(a,1,1),1400,MonoNs(1)).unwrap();
        x.on_timer(MonoNs(20_000_001)).unwrap();
        assert_eq!(x.snapshot().overdue_uncertain_bytes,1400);
        assert_eq!(x.snapshot().pending,0);
        assert_eq!(x.complete(id,RepairSendResult::NotSent,MonoNs(20_000_002)),
            Err(GlobalRepairError::StaleGrant));
        assert_eq!(x.grant(a,1000,100_000,MonoNs(20_000_002)),
            Err(GlobalRepairError::GrantAlreadyActive));
        assert_eq!(x.revoke(grant,MonoNs(20_000_003)),Ok(()));
        let b=dir(1,WireDirection::ServerToClient);
        assert_eq!(x.register(b,cfg(),MonoNs(20_000_003)),
            Err(GlobalRepairError::DirectionCapacity));
        assert_eq!(x.on_timer(MonoNs(20_000_002)),
            Err(GlobalRepairError::ClockReversed));
    }

    // Batch fixture: large enough to hold 32 independently reserved items
    // without masking the 8-MTU pacer or 1s epoch accounting.
    fn wide_batch() -> GlobalRepairAllocator {
        GlobalRepairAllocator::new(GlobalRepairConfig {
            max_bytes_per_epoch:70_000, max_directions:3,
            max_grant_bytes:70_000, max_grant_lifetime_ns:500_000_000,
            max_pending:64, max_pending_bytes:100_000,
        }, MonoNs(0)).unwrap()
    }
    fn wide_cfg() -> RepairBudgetConfig {
        RepairBudgetConfig {
            outer_mtu:1400, max_repair_bytes_per_epoch:100_000,
            max_pending_reservations:64, max_pending_bytes:100_000,
            io_timeout_ns:900_000_000,
        }
    }
    fn wide_candidates() -> (
        GlobalRepairAllocator, Vec<GlobalReservationId>,
        [BudgetDirection;3], [GrantLease;3]
    ) {
        let mut b=wide_batch();
        let dirs=[
            dir(1,WireDirection::ClientToServer),
            dir(1,WireDirection::ServerToClient),
            dir(2,WireDirection::ClientToServer),
        ];
        for d in dirs {
            b.register(d,wide_cfg(),MonoNs(0)).unwrap();
        }
        for d in dirs {
            b.on_fresh_accepted(d,1_000_000,MonoNs(1)).unwrap();
        }
        let leases=[
            b.grant(dirs[0],15_400,500_000_000,MonoNs(1)).unwrap(),
            b.grant(dirs[1],15_400,500_000_000,MonoNs(1)).unwrap(),
            b.grant(dirs[2],14_000,500_000_000,MonoNs(1)).unwrap(),
        ];
        let mut ids=Vec::new();
        for i in 0..32 {
            let n=i%3;
            let at=1+i as u64 * 15_000_000;
            let c=candidate(dirs[n],i as u64 + 1,at);
            ids.push(b.reserve(leases[n],&c,1400,MonoNs(at)).unwrap());
        }
        (b,ids,dirs,leases)
    }

    #[test]
    fn r2_batch_zero_one_all_accepted_and_no_peer_receipt() {
        let mut b=global(2800,1);
        let d=dir(1,WireDirection::ClientToServer);
        add(&mut b,d,0);
        let empty=ValidatedRepairBatchOutcome::all_accepted(0).unwrap();
        assert_eq!(b.complete_batch(&[],empty,MonoNs(0)).unwrap(),
            BatchCompletionCounts {
                accepted:0,uncertain:0,definitely_not_sent:0,held_unproven:0,
            });
        let lease=b.grant(d,1400,100_000,MonoNs(1)).unwrap();
        let frozen=candidate(d,7,1);
        let pn=frozen.pn();
        let wire=frozen.frozen().bytes().to_vec();
        let id=b.reserve(lease,&frozen,1400,MonoNs(1)).unwrap();
        let one=ValidatedRepairBatchOutcome::all_accepted(1).unwrap();
        assert_eq!(b.complete_batch(&[id],one,MonoNs(2)).unwrap().accepted,1);
        assert_eq!(b.snapshot().charged_repairs,1400);
        // Driver acceptance is not receipt: the same frozen cipher/PN survives.
        assert_eq!(frozen.pn(),pn);
        assert_eq!(frozen.frozen().bytes(),wire.as_slice());
        assert_eq!(b.complete_batch(&[id],one,MonoNs(3)),
            Err(GlobalRepairError::StaleGrant));
    }

    #[test]
    fn r2_batch_32_mixed_client_directions_prefix_uncertain_proven_suffix() {
        let (mut b,ids,dirs,_leases)=wide_candidates();
        assert_eq!(ids.len(),32);
        let evidence=ValidatedRepairBatchOutcome::checked(
            32,13,Some(13),BatchSuffixEvidence::ProvenNotAttempted
        ).unwrap();
        let r=b.complete_batch(&ids,evidence,MonoNs(465_000_002)).unwrap();
        assert_eq!(r,BatchCompletionCounts {
            accepted:13,uncertain:1,definitely_not_sent:18,held_unproven:0
        });
        assert_eq!(b.snapshot().pending,0);
        assert_eq!(b.snapshot().charged_repairs,14*1400);
        assert_eq!(b.snapshot().held_unused_grants,25_200); // replaced below
        assert_eq!(b.complete_batch(&ids,evidence,MonoNs(465_000_003)),
            Err(GlobalRepairError::StaleGrant));
        // A full process repair quota does not HOL-gate new data submission.
        b.on_fresh_accepted(dirs[2],12345,MonoNs(465_000_003)).unwrap();
        assert_eq!(b.local_snapshot(dirs[2]).unwrap().fresh_confirmed_bytes,1_012_345);
    }

    #[test]
    fn r2_batch_0_1_32_33_shape_and_duplicates_fail_closed() {
        assert_eq!(ValidatedRepairBatchOutcome::checked(
            33,0,None,BatchSuffixEvidence::Unproven
        ),Err(GlobalRepairError::InvalidBatch));
        assert_eq!(ValidatedRepairBatchOutcome::checked(
            1,0,Some(1),BatchSuffixEvidence::ProvenNotAttempted
        ),Err(GlobalRepairError::InvalidBatch));
        assert_eq!(ValidatedRepairBatchOutcome::checked(
            2,1,Some(0),BatchSuffixEvidence::Unproven
        ),Err(GlobalRepairError::InvalidBatch));
        let (mut b,ids,_,_)=wide_candidates();
        let before=b.snapshot();
        let all=ValidatedRepairBatchOutcome::all_accepted(32).unwrap();
        assert_eq!(b.complete_batch(&ids[..31],all,MonoNs(465_000_002)),
            Err(GlobalRepairError::InvalidBatch));
        let mut duplicated=ids.clone();
        duplicated[31]=duplicated[0];
        assert_eq!(b.complete_batch(&duplicated,all,MonoNs(465_000_002)),
            Err(GlobalRepairError::DuplicateBatchId));
        duplicated.push(ids[0]);
        assert_eq!(b.complete_batch(&duplicated,all,MonoNs(465_000_002)),
            Err(GlobalRepairError::InvalidBatch));
        assert_eq!(b.snapshot(),before);
        let done=b.complete_batch(&ids,all,MonoNs(465_000_002)).unwrap();
        assert_eq!(done.accepted,32);
        assert_eq!(b.snapshot().charged_repairs,44_800);
    }

    #[test]
    fn r2_batch_unproven_suffix_never_falsely_notsent_refunds() {
        let mut b=global(4200,1);
        let d=dir(1,WireDirection::ClientToServer);
        add(&mut b,d,0);
        let lease=b.grant(d,4200,100_000_000,MonoNs(1)).unwrap();
        let mut ids=Vec::new();
        for pn in 1..=3 {
            ids.push(b.reserve(lease,&candidate(d,pn,1),1400,MonoNs(1)).unwrap());
        }
        let evidence=ValidatedRepairBatchOutcome::checked(
            3,1,Some(1),BatchSuffixEvidence::Unproven
        ).unwrap();
        let mapped=b.complete_batch(&ids,evidence,MonoNs(2)).unwrap();
        assert_eq!(mapped,BatchCompletionCounts {
            accepted:1,uncertain:1,definitely_not_sent:0,held_unproven:1
        });
        assert_eq!(b.snapshot().charged_repairs,4200);
        assert_eq!(b.snapshot().pending,1);
        assert_eq!(b.snapshot().held_unused_grants,0);
        b.on_timer(MonoNs(20_000_001)).unwrap();
        assert_eq!(b.snapshot().pending,0);
        assert_eq!(b.snapshot().overdue_uncertain_bytes,1400);
        assert_eq!(b.complete_batch(&[ids[2]],
            ValidatedRepairBatchOutcome::all_accepted(1).unwrap(),
            MonoNs(20_000_002)),Err(GlobalRepairError::StaleGrant));
    }

    #[test]
    fn r2_batch_epoch_cutover_old_notsent_refund_and_grant_expiry() {
        let mut b=global(4200,2);
        let a=dir(1,WireDirection::ClientToServer);
        let c=dir(2,WireDirection::ServerToClient);
        b.register(a,wide_cfg(),MonoNs(999_999_980)).unwrap();
        b.register(c,wide_cfg(),MonoNs(999_999_980)).unwrap();
        let la=b.grant(a,1400,50_000,MonoNs(999_999_982)).unwrap();
        let lc=b.grant(c,1400,50_000,MonoNs(999_999_983)).unwrap();
        let ia=b.reserve(la,&candidate(a,1,999_999_984),1400,MonoNs(999_999_984)).unwrap();
        let ic=b.reserve(lc,&candidate(c,2,999_999_985),1400,MonoNs(999_999_985)).unwrap();
        let proof=ValidatedRepairBatchOutcome::checked(
            2,1,None,BatchSuffixEvidence::ProvenNotAttempted
        ).unwrap();
        let counts=b.complete_batch(&[ia,ic],proof,MonoNs(1_000_000_001)).unwrap();
        assert_eq!(counts.accepted,1);
        assert_eq!(counts.definitely_not_sent,1);
        assert_eq!(b.snapshot().epoch,1);
        assert_eq!(b.snapshot().previous_epoch_charged,1400);
        assert_eq!(b.snapshot().charged_repairs,0);
        assert_eq!(b.snapshot().held_unused_grants,0);
        assert_eq!(b.revoke(lc,MonoNs(1_000_000_002)),
            Err(GlobalRepairError::StaleGrant));
        b.on_fresh_accepted(c,234,MonoNs(1_000_000_003)).unwrap();
        assert_eq!(b.local_snapshot(c).unwrap().fresh_confirmed_bytes,234);
    }

    #[test]
    fn r2_batch_retired_client_fails_closed_and_no_cross_tunnel_refund() {
        let mut b=global(4200,2);
        let a=dir(1,WireDirection::ClientToServer);
        let c=dir(2,WireDirection::ServerToClient);
        add(&mut b,a,0);add(&mut b,c,0);
        let la=b.grant(a,1400,100_000,MonoNs(1)).unwrap();
        let lc=b.grant(c,1400,100_000,MonoNs(1)).unwrap();
        let ia=b.reserve(la,&candidate(a,1,1),1400,MonoNs(1)).unwrap();
        let ic=b.reserve(lc,&candidate(c,2,1),1400,MonoNs(1)).unwrap();
        b.retire_tunnel(a.tunnel,MonoNs(2)).unwrap();
        let before=b.snapshot();
        let result=ValidatedRepairBatchOutcome::checked(
            2,0,None,BatchSuffixEvidence::ProvenNotAttempted
        ).unwrap();
        assert_eq!(b.complete_batch(&[ia,ic],result,MonoNs(3)),
            Err(GlobalRepairError::StaleGrant));
        assert_eq!(b.snapshot(),before);
        assert_eq!(b.snapshot().overdue_uncertain_bytes,1400);
        // A known-not-attempted completion for surviving client is allowed.
        let single=ValidatedRepairBatchOutcome::checked(
            1,0,None,BatchSuffixEvidence::ProvenNotAttempted
        ).unwrap();
        b.complete_batch(&[ic],single,MonoNs(4)).unwrap();
        assert_eq!(b.snapshot().charged_repairs,1400);
        assert_eq!(b.snapshot().held_unused_grants,1400);
    }


    fn race_shadow(d: BudgetDirection, pn: u64, at: u64)
        -> (ReceiptState<FakeFrozen>, RepairCandidate<FakeFrozen>)
    {
        let lane=LaneKey {tunnel:d.tunnel,slot:1,generation:1};
        let f=FakeFrozen {
            data:Arc::from([19u8,20,21,22].as_slice()),
            metadata:FrozenMetadata {lane,pn:RecordPn(pn),
                seq:SeqOffset(pn),carrier_snapshot:88},
            origin:BufferOrigin {owner_arena:d.tunnel.slot,
                key:BufferKey {slot:pn as u32,generation:5}},
        };
        let mut state=ReceiptState::new(lane,ReceiptConfig {
            max_shadow_entries:4,pto_ns:1,reorder_window_ns:1
        }).unwrap();
        state.on_sent(f,MonoNs(at-1),
            MonoNs(at.saturating_add(300_000_000))).unwrap();
        let candidate=state.on_timer(MonoNs(at)).candidates.remove(0);
        (state,candidate)
    }
    fn race_receipt(d: BudgetDirection, pn: u64, seq: u32)
        -> AuthenticatedReceipt
    {
        let base=(pn/256)*256;
        let mut bits=[0u8;32];
        let off=pn-base;
        bits[(off/8) as usize] |= 1 << (off%8);
        AuthenticatedReceipt::after_authenticated_open(
            LaneKey {tunnel:d.tunnel,slot:1,generation:1},RecordPn(pn),
            seq,vec![crate::receipt::ReceiptPage{
                base_pn:RecordPn(base),bitmap:bits
            }]
        ).unwrap()
    }

    #[test]
    fn r2_race_late_ack_before_reserve_rejects_stale_without_refund() {
        let a=dir(1,WireDirection::ClientToServer);
        let b=dir(2,WireDirection::ServerToClient);
        let mut x=global(2800,2);
        add(&mut x,a,0);add(&mut x,b,0);
        let ga=x.grant(a,1400,100_000,MonoNs(1)).unwrap();
        let (mut shadow,c)=race_shadow(a,7,1);
        let peer=race_receipt(a,7,1);
        let releases=x.observe_authenticated_receipt(a,&mut shadow,&peer,MonoNs(2)).unwrap();
        assert_eq!(releases.len(),1);
        assert_eq!(releases[0].reason,crate::receipt::ReleaseReason::ReceivedByPeer);
        assert!(!shadow.preflight(&c,MonoNs(2)));
        let before=x.snapshot();
        assert_eq!(x.reserve_if_still_missing(ga,&shadow,&c,1400,MonoNs(2)),
            Err(GlobalRepairError::StaleCandidate));
        assert_eq!(x.snapshot(),before);
        assert_eq!(x.snapshot().charged_repairs,0);
        assert_eq!(x.snapshot().held_unused_grants,1400);
        x.on_fresh_accepted(b,20_000,MonoNs(3)).unwrap();
        assert_eq!(x.local_snapshot(b).unwrap().fresh_confirmed_bytes,20_000);
    }

    #[test]
    fn r2_race_ack_during_batch_is_not_kernel_or_peer_delivery() {
        let a=dir(1,WireDirection::ClientToServer);
        let b=dir(2,WireDirection::ServerToClient);
        let mut x=global(2800,2);
        add(&mut x,a,0);add(&mut x,b,0);
        let ga=x.grant(a,1400,100_000,MonoNs(1)).unwrap();
        let gb=x.grant(b,1400,100_000,MonoNs(1)).unwrap();
        let (mut sa,ca)=race_shadow(a,10,1);
        let (mut sb,cb)=race_shadow(b,20,1);
        let ia=x.reserve_if_still_missing(ga,&sa,&ca,1400,MonoNs(1)).unwrap();
        let ib=x.reserve_if_still_missing(gb,&sb,&cb,1400,MonoNs(1)).unwrap();
        // Real positive authenticated ACK wins shadow before callback;
        // pending kernel send still might have been submitted.
        assert_eq!(x.observe_authenticated_receipt(a,&mut sa,&race_receipt(a,10,1),
            MonoNs(2)).unwrap().len(),1);
        assert_eq!(x.snapshot().charged_repairs,2800);
        let mixed=ValidatedRepairBatchOutcome::checked(
            2,1,Some(1),BatchSuffixEvidence::Unproven).unwrap();
        assert_eq!(x.complete_batch(&[ia,ib],mixed,MonoNs(3)).unwrap(),
            BatchCompletionCounts {accepted:1,uncertain:1,
                definitely_not_sent:0,held_unproven:0});
        assert_eq!(x.snapshot().charged_repairs,2800);
        assert_eq!(sb.outstanding(),1); // kernel Accepted never acts as an ACK
        assert_eq!(x.complete_batch(&[ia,ib],mixed,MonoNs(4)),
            Err(GlobalRepairError::StaleGrant));
        assert_eq!(x.observe_authenticated_receipt(b,&mut sb,&race_receipt(b,20,1),
            MonoNs(5)).unwrap().len(),1);
        assert_eq!(x.snapshot().charged_repairs,2800);
    }

    #[test]
    fn r2_race_departed_tunnel_generation_cannot_resurrect_or_refund() {
        let old=dir(1,WireDirection::ClientToServer);
        let mut x=global(4200,2);
        add(&mut x,old,0);
        let lease=x.grant(old,1400,100_000,MonoNs(1)).unwrap();
        let (mut old_shadow,old_c)=race_shadow(old,1,1);
        let id=x.reserve_if_still_missing(lease,&old_shadow,&old_c,
            1400,MonoNs(1)).unwrap();
        assert_eq!(x.retire_tunnel(old.tunnel,MonoNs(2)).unwrap(),1);
        let new=BudgetDirection {tunnel:TunnelKey {slot:1,generation:3},
            direction:WireDirection::ClientToServer};
        x.register(new,cfg(),MonoNs(3)).unwrap();
        let before=x.snapshot();
        assert!(matches!(x.observe_authenticated_receipt(new,&mut old_shadow,
            &race_receipt(old,1,1),MonoNs(3)),
            Err(GlobalRepairError::WrongReceiptLane)));
        assert_eq!(x.complete_batch(&[id],
            ValidatedRepairBatchOutcome::checked(1,0,None,
                BatchSuffixEvidence::ProvenNotAttempted).unwrap(),MonoNs(3)),
            Err(GlobalRepairError::StaleGrant));
        assert_eq!(x.snapshot(),before);
        assert_eq!(x.snapshot().overdue_uncertain_bytes,1400);
        assert_eq!(x.snapshot().charged_repairs,1400);
        let gnew=x.grant(new,2800,100_000,MonoNs(4)).unwrap();
        assert_eq!(gnew.bytes(),2800);
        assert_eq!(x.snapshot().charged_repairs+x.snapshot().held_unused_grants,4200);
    }

    #[test]
    fn r2_race_old_epoch_mixed_callback_never_funds_new_grant() {
        let a=dir(1,WireDirection::ClientToServer);
        let b=dir(1,WireDirection::ServerToClient);
        let c=dir(2,WireDirection::ClientToServer);
        let mut x=global(4200,3);
        for d in [a,b,c] {x.register(d,wide_cfg(),MonoNs(999_999_980)).unwrap();}
        let leases=[
            x.grant(a,1400,10_000,MonoNs(999_999_981)).unwrap(),
            x.grant(b,1400,10_000,MonoNs(999_999_981)).unwrap(),
            x.grant(c,1400,10_000,MonoNs(999_999_981)).unwrap(),
        ];
        let mut ids=Vec::new();
        for (i,(d,l)) in [a,b,c].into_iter().zip(leases).enumerate() {
            let (s,ca)=race_shadow(d,i as u64+1,999_999_982);
            ids.push(x.reserve_if_still_missing(l,&s,&ca,1400,
                MonoNs(999_999_982)).unwrap());
        }
        let outcome=ValidatedRepairBatchOutcome::checked(
            3,1,Some(1),BatchSuffixEvidence::ProvenNotAttempted).unwrap();
        assert_eq!(x.complete_batch(&ids,outcome,MonoNs(1_000_000_001)).unwrap(),
            BatchCompletionCounts {accepted:1,uncertain:1,
                definitely_not_sent:1,held_unproven:0});
        assert_eq!(x.snapshot().previous_epoch_charged,2800);
        assert_eq!(x.snapshot().charged_repairs,0);
        assert_eq!(x.snapshot().held_unused_grants,0);
        assert_eq!(x.complete_batch(&ids,outcome,MonoNs(1_000_000_002)),
            Err(GlobalRepairError::StaleGrant));
        x.on_fresh_accepted(a,100,MonoNs(1_000_000_003)).unwrap();
        assert_eq!(x.local_snapshot(a).unwrap().fresh_confirmed_bytes,100);
        let next=x.grant(c,4200,100_000,MonoNs(1_000_000_004)).unwrap();
        assert_eq!(next.bytes(),4200);
        assert_eq!(x.snapshot().charged_repairs,0);
        assert_eq!(x.snapshot().held_unused_grants,4200);
    }

    #[test]
    fn r2_race_32_33_bounded_callback_after_timeout_is_all_stale() {
        let (mut x,ids,_,_)=wide_candidates();
        let one=ValidatedRepairBatchOutcome::all_accepted(1).unwrap();
        let prefix=ValidatedRepairBatchOutcome::checked(
            32,16,Some(16),BatchSuffixEvidence::Unproven).unwrap();
        let mut repeated=ids.clone();
        repeated[31]=repeated[0];
        let before=x.snapshot();
        assert_eq!(x.complete_batch(&repeated,prefix,MonoNs(465_000_001)),
            Err(GlobalRepairError::DuplicateBatchId));
        assert_eq!(x.snapshot(),before);
        assert_eq!(ValidatedRepairBatchOutcome::all_accepted(33),
            Err(GlobalRepairError::InvalidBatch));
        assert_eq!(x.complete_batch(&ids[..1],one,MonoNs(901_000_000)),
            Err(GlobalRepairError::StaleGrant));
        // First reservations have actually timed out; a subsequent whole
        // batch cannot partly refund the later IDs when one is stale.
        let snap=x.snapshot();
        assert_eq!(x.complete_batch(&ids,prefix,MonoNs(901_000_000)),
            Err(GlobalRepairError::StaleGrant));
        assert_eq!(x.snapshot(),snap);
        assert!(x.snapshot().overdue_uncertain_bytes>=1400);
    }


    fn route(d:BudgetDirection,epoch:u8,first:u64,last:u64)->ReceiptRouteScope {
        let out=LaneKey{tunnel:d.tunnel,slot:1,generation:1};
        let reverse=LaneKey{tunnel:d.tunnel,slot:2,generation:7};
        ReceiptRouteScope::checked(out,reverse,d.direction,
            [epoch;16],(RecordPn(first),RecordPn(last)),
            (RecordPn(1),RecordPn(1000))).unwrap()
    }
    fn opened(d:BudgetDirection,epoch:u8,pn:u64)
        -> crate::receipt::ReceiptOpenFacts {
        crate::receipt::ReceiptOpenFacts {
            verified_reverse_lane:LaneKey{tunnel:d.tunnel,slot:2,generation:7},
            verified_reverse_direction:match d.direction {
                WireDirection::ClientToServer=>WireDirection::ServerToClient,
                WireDirection::ServerToClient=>WireDirection::ClientToServer
            },
            verified_tunnel_epoch:[epoch;16],
            control_record_pn:RecordPn(pn),
        }
    }
    fn positive(pn:u64)->Vec<crate::receipt::ReceiptPage> {
        let base=pn/256*256;
        let mut bitmap=[0u8;32];
        bitmap[((pn-base)/8) as usize]|=1 << ((pn-base)%8);
        vec![crate::receipt::ReceiptPage{base_pn:RecordPn(base),bitmap}]
    }
    fn scoped_receipt(
        pinned:ReceiptRouteScope,facts:crate::receipt::ReceiptOpenFacts,
        pn:u64,seq:u32
    )->Result<ScopedAuthenticatedReceipt,DataError> {
        ScopedAuthenticatedReceipt::checked_after_open(
            pinned,facts,RecordPn(pn),seq,positive(pn))
    }

    #[test]
    fn r2_scope_forward_stale_epoch_rotation_and_pn_fail_before_receipt() {
        let a=dir(1,WireDirection::ClientToServer);
        let b=dir(2,WireDirection::ServerToClient);
        let scope=route(a,7,10,30);
        let facts=opened(a,7,10);
        assert!(scoped_receipt(scope,facts,12,1).is_ok());
        let mut forward=facts;
        forward.verified_reverse_direction=WireDirection::ClientToServer;
        assert!(matches!(scoped_receipt(scope,forward,12,1),Err(DataError::Stale)));
        let mut other=facts;
        other.verified_reverse_lane=opened(b,7,10).verified_reverse_lane;
        assert!(matches!(scoped_receipt(scope,other,12,1),Err(DataError::Stale)));
        other=facts;other.verified_reverse_lane.generation+=1;
        assert!(matches!(scoped_receipt(scope,other,12,1),Err(DataError::Stale)));
        other=facts;other.verified_tunnel_epoch=[8;16];
        assert!(matches!(scoped_receipt(scope,other,12,1),Err(DataError::Stale)));
        other=facts;other.control_record_pn=RecordPn(1001);
        assert!(matches!(scoped_receipt(scope,other,12,1),Err(DataError::Stale)));
        assert!(matches!(scoped_receipt(scope,facts,9,1),Err(DataError::Stale)));
        assert!(matches!(scoped_receipt(scope,facts,31,1),Err(DataError::Stale)));
        assert!(matches!(ReceiptRouteScope::checked(
            scope.outbound_lane(),scope.outbound_lane(),a.direction,[0;16],
            (RecordPn(1),RecordPn(2)),(RecordPn(1),RecordPn(2))),
            Err(DataError::Malformed)));
        // Largest=20 is valid but the bit for 9 is outside pinned [10,30].
        assert!(matches!(ScopedAuthenticatedReceipt::checked_after_open(
            scope,facts,RecordPn(20),1,positive(9)),Err(DataError::Stale)));
    }

    #[test]
    fn r2_scope_ack_before_grant_and_old_report_never_forged() {
        let a=dir(1,WireDirection::ClientToServer);
        let b=dir(2,WireDirection::ServerToClient);
        let mut x=global(2800,2);
        add(&mut x,a,0);add(&mut x,b,0);
        let ra=route(a,7,1,40);
        let rb=route(b,9,1,40);
        x.bind_receipt_route(a,ra,MonoNs(0)).unwrap();
        x.bind_receipt_route(b,rb,MonoNs(0)).unwrap();
        let (mut shadow,c)=race_shadow(a,12,1);
        let scoped=scoped_receipt(ra,opened(a,7,12),12,9).unwrap();
        assert_eq!(x.observe_scoped_receipt(a,&mut shadow,&scoped,MonoNs(2))
            .unwrap().len(),1);
        assert_eq!(x.observe_scoped_receipt(a,&mut shadow,&scoped,MonoNs(3))
            .unwrap().len(),0);
        assert_eq!(x.snapshot().charged_repairs,0);
        assert_eq!(shadow.outstanding(),0);
        let lease=x.grant(a,1400,100_000,MonoNs(4)).unwrap();
        let before=x.snapshot();
        assert_eq!(x.reserve_if_still_missing(lease,&shadow,&c,1400,MonoNs(4)),
            Err(GlobalRepairError::StaleCandidate));
        assert_eq!(x.snapshot(),before);
        let bad=scoped_receipt(rb,opened(b,9,12),12,10).unwrap();
        assert!(matches!(x.observe_scoped_receipt(a,&mut shadow,&bad,MonoNs(4)),
            Err(GlobalRepairError::WrongReceiptScope)));
        x.on_fresh_accepted(b,200,MonoNs(5)).unwrap();
        assert_eq!(x.local_snapshot(b).unwrap().fresh_confirmed_bytes,200);
    }

    #[test]
    fn r2_scope_four_clients_directions_mixed_batch_rejects_cross_scope() {
        let a=dir(1,WireDirection::ClientToServer);
        let b=dir(1,WireDirection::ServerToClient);
        let c=dir(2,WireDirection::ClientToServer);
        let d=dir(2,WireDirection::ServerToClient);
        let dirs=[a,b,c,d];
        let mut x=global(5600,4);
        for dir in dirs {add(&mut x,dir,0);}
        let routes=dirs.map(|dir|route(dir,7,1,80));
        for (dir,sc) in dirs.into_iter().zip(routes) {
            x.bind_receipt_route(dir,sc,MonoNs(0)).unwrap();
        }
        let grants=dirs.map(|dir|x.grant(dir,1400,100_000,MonoNs(1)).unwrap());
        let mut ids=Vec::new();
        for (i,((dir,sc),lease)) in dirs.into_iter().zip(routes).zip(grants).enumerate() {
            let (shadow,candidate)=race_shadow(dir,10+i as u64,1);
            let id=x.reserve_if_still_missing(lease,&shadow,&candidate,1400,MonoNs(1)).unwrap();
            ids.push((id,sc));
        }
        let wrong=vec![ids[0],(ids[1].0,routes[2]),ids[2],ids[3]];
        let outcome=ValidatedRepairBatchOutcome::checked(
            4,1,Some(1),BatchSuffixEvidence::ProvenNotAttempted).unwrap();
        let before=x.snapshot();
        assert_eq!(x.complete_scoped_batch(&wrong,outcome,MonoNs(2)),
            Err(GlobalRepairError::WrongReceiptScope));
        assert_eq!(x.snapshot(),before);
        let counts=x.complete_scoped_batch(&ids,outcome,MonoNs(2)).unwrap();
        assert_eq!(counts,BatchCompletionCounts{accepted:1,uncertain:1,
            definitely_not_sent:2,held_unproven:0});
        assert_eq!(x.snapshot().charged_repairs,2800);
        assert_eq!(x.snapshot().held_unused_grants,2800);
        assert_eq!(x.complete_scoped_batch(&ids,outcome,MonoNs(3)),
            Err(GlobalRepairError::StaleGrant));
        x.on_fresh_accepted(d,500,MonoNs(3)).unwrap();
        assert_eq!(x.local_snapshot(d).unwrap().fresh_confirmed_bytes,500);
    }

    #[test]
    fn r2_scope_epoch_rollover_departure_old_notsent_and_uncertain_debit() {
        let a=dir(1,WireDirection::ClientToServer);
        let b=dir(2,WireDirection::ServerToClient);
        let mut x=global(4200,2);
        x.register(a,wide_cfg(),MonoNs(999_999_980)).unwrap();
        x.register(b,wide_cfg(),MonoNs(999_999_980)).unwrap();
        let ra=route(a,7,1,60);let rb=route(b,7,1,60);
        x.bind_receipt_route(a,ra,MonoNs(999_999_980)).unwrap();
        x.bind_receipt_route(b,rb,MonoNs(999_999_980)).unwrap();
        let ga=x.grant(a,1400,1000,MonoNs(999_999_981)).unwrap();
        let gb=x.grant(b,1400,1000,MonoNs(999_999_981)).unwrap();
        let (sa,ca)=race_shadow(a,10,999_999_982);
        let (sb,cb)=race_shadow(b,20,999_999_982);
        let ia=x.reserve_if_still_missing(ga,&sa,&ca,1400,MonoNs(999_999_982)).unwrap();
        let ib=x.reserve_if_still_missing(gb,&sb,&cb,1400,MonoNs(999_999_982)).unwrap();
        let mixed=ValidatedRepairBatchOutcome::checked(
            2,0,Some(0),BatchSuffixEvidence::ProvenNotAttempted).unwrap();
        assert_eq!(x.complete_scoped_batch(&[(ia,ra),(ib,rb)],mixed,
            MonoNs(1_000_000_001)).unwrap(),
            BatchCompletionCounts{accepted:0,uncertain:1,
                definitely_not_sent:1,held_unproven:0});
        assert_eq!(x.snapshot().previous_epoch_charged,1400);
        assert_eq!(x.snapshot().charged_repairs,0);
        assert_eq!(x.snapshot().held_unused_grants,0);
        assert_eq!(x.bind_receipt_route(a,route(a,8,1,60),MonoNs(1_000_000_002)),
            Err(GlobalRepairError::WrongReceiptScope));
        x.retire_tunnel(a.tunnel,MonoNs(1_000_000_003)).unwrap();
        let anew=BudgetDirection {
            tunnel:TunnelKey{slot:1,generation:3},direction:WireDirection::ClientToServer};
        x.register(anew,wide_cfg(),MonoNs(1_000_000_004)).unwrap();
        let ranew=route(anew,8,1,60);
        x.bind_receipt_route(anew,ranew,MonoNs(1_000_000_004)).unwrap();
        let g=x.grant(anew,4200,100_000,MonoNs(1_000_000_005)).unwrap();
        assert_eq!(g.bytes(),4200);
        assert_eq!(x.complete_scoped_batch(&[(ia,ra)],
            ValidatedRepairBatchOutcome::checked(
                1,0,None,BatchSuffixEvidence::ProvenNotAttempted).unwrap(),
            MonoNs(1_000_000_006)),Err(GlobalRepairError::StaleGrant));
        assert_eq!(x.snapshot().held_unused_grants,4200);
        assert_eq!(x.snapshot().charged_repairs,0);
    }

    #[test]
    fn r2_scope_32_33_bounded_registration_and_old_callback_fail_closed() {
        let (mut x,ids,dirs,leases)=wide_candidates();
        // Untagged old grants cannot silently acquire a session scope.
        let a=route(dirs[0],7,1,80);
        assert_eq!(x.bind_receipt_route(dirs[0],a,MonoNs(465_000_001)),
            Err(GlobalRepairError::WrongReceiptScope));
        let mut batch:Vec<(GlobalReservationId,ReceiptRouteScope)>=ids.iter()
            .copied().map(|id|(id,a)).collect();
        let partial=ValidatedRepairBatchOutcome::checked(
            32,16,Some(16),BatchSuffixEvidence::Unproven).unwrap();
        let before=x.snapshot();
        assert_eq!(x.complete_scoped_batch(&batch,partial,MonoNs(465_000_001)),
            Err(GlobalRepairError::WrongReceiptScope));
        assert_eq!(x.snapshot(),before);
        batch.push((ids[0],a));
        assert_eq!(x.complete_scoped_batch(&batch,partial,MonoNs(465_000_001)),
            Err(GlobalRepairError::InvalidBatch));
        assert_eq!(ValidatedRepairBatchOutcome::all_accepted(33),
            Err(GlobalRepairError::InvalidBatch));
        // Old unscoped contract still receives no peer-delivery credit.
        assert_eq!(x.complete_batch(&ids,
            ValidatedRepairBatchOutcome::all_accepted(32).unwrap(),
            MonoNs(465_000_002)).unwrap().accepted,32);
        assert_eq!(x.snapshot().charged_repairs,44_800);
        let _=leases;
    }


    /// Source-local fixture: exactly two independent logical TunnelKeys, one
    /// client->server and one server->client. 32 immutable repair candidates
    /// use the same process-wide 44_800B cap; fake clock injection only.
    fn r2_owner_fixture() -> (GlobalRepairAllocator,
        Vec<(GlobalReservationId,ReceiptRouteScope)>,[BudgetDirection;2]) {
        let dirs=[dir(1,WireDirection::ClientToServer),
                  dir(2,WireDirection::ServerToClient)];
        let mut x=GlobalRepairAllocator::new(GlobalRepairConfig{
            max_bytes_per_epoch:44_800,max_directions:2,max_grant_bytes:22_400,
            max_grant_lifetime_ns:500_000_000,
            max_pending:32,max_pending_bytes:44_800,
        },MonoNs(0)).unwrap();
        let scopes=dirs.map(|d|route(d,7,1,64));
        for d in dirs {x.register(d,wide_cfg(),MonoNs(0)).unwrap();}
        for (d,r) in dirs.into_iter().zip(scopes) {
            x.bind_receipt_route(d,r,MonoNs(0)).unwrap();
        }
        for d in dirs {x.on_fresh_accepted(d,1_000_000,MonoNs(1)).unwrap();}
        let leases=dirs.map(|d|x.grant(d,22_400,500_000_000,MonoNs(1)).unwrap());
        let mut slots=Vec::with_capacity(32);
        for i in 0..32 {
            let which=i%2;
            let now=MonoNs(1+(i as u64)*15_000_000);
            let (shadow,c)=race_shadow(dirs[which],i as u64+1,now.0);
            let id=x.reserve_scoped_if_still_missing(
                leases[which],scopes[which],&shadow,&c,1400,now).unwrap();
            slots.push((id,scopes[which]));
        }
        assert_eq!(slots.len(),32);
        assert_eq!(slots.capacity(),32);
        assert_eq!(x.snapshot().pending,32);
        assert_eq!(x.snapshot().pending_bytes,44_800);
        assert_eq!(x.snapshot().charged_repairs,44_800);
        assert_eq!(x.snapshot().held_unused_grants,0);
        (x,slots,dirs)
    }

    #[test]
    fn r2_owner_zero_one_typed_scope_and_repeat_completion() {
        let a=dir(1,WireDirection::ClientToServer);
        let scope=route(a,7,1,64);
        let mut x=global(1400,1);
        add(&mut x,a,0);
        assert_eq!(x.complete_scoped_batch(&[],
            ValidatedRepairBatchOutcome::all_accepted(0).unwrap(),MonoNs(0))
            .unwrap().accepted,0);
        let g=x.grant(a,1400,100_000,MonoNs(1)).unwrap();
        let (shadow,c)=race_shadow(a,9,1);
        let before=x.snapshot();
        assert_eq!(x.reserve_scoped_if_still_missing(g,scope,&shadow,&c,
            1400,MonoNs(1)),Err(GlobalRepairError::WrongReceiptScope));
        assert_eq!(x.snapshot(),before);
        // Cannot retrofit a proof to an already granted owner.
        assert_eq!(x.bind_receipt_route(a,scope,MonoNs(1)),
            Err(GlobalRepairError::WrongReceiptScope));
        x.revoke(g,MonoNs(2)).unwrap();
        x.bind_receipt_route(a,scope,MonoNs(2)).unwrap();
        let g2=x.grant(a,1400,100_000,MonoNs(2)).unwrap();
        let (shadow2,c2)=race_shadow(a,9,2);
        let id=x.reserve_scoped_if_still_missing(g2,scope,&shadow2,&c2,
            1400,MonoNs(2)).unwrap();
        let all=ValidatedRepairBatchOutcome::all_accepted(1).unwrap();
        assert_eq!(x.complete_scoped_batch(&[(id,scope)],all,MonoNs(3))
            .unwrap().accepted,1);
        assert_eq!(x.snapshot().charged_repairs,1400);
        assert_eq!(x.complete_scoped_batch(&[(id,scope)],all,MonoNs(4)),
            Err(GlobalRepairError::StaleGrant));
    }

    #[test]
    fn r2_owner_two_scopes_32_mixed_stale_and_33_no_false_refund() {
        let (mut x,slots,dirs)=r2_owner_fixture();
        let outcome=ValidatedRepairBatchOutcome::checked(
            32,12,Some(12),BatchSuffixEvidence::ProvenNotAttempted).unwrap();
        let before=x.snapshot();
        let mut wrong=slots.clone();
        wrong[17].1=route(dirs[1],8,1,64);
        assert_eq!(x.complete_scoped_batch(&wrong,outcome,MonoNs(465_000_002)),
            Err(GlobalRepairError::WrongReceiptScope));
        assert_eq!(x.snapshot(),before);
        let mut oversized=slots.clone();
        oversized.push(slots[0]);
        assert_eq!(x.complete_scoped_batch(&oversized,outcome,MonoNs(465_000_002)),
            Err(GlobalRepairError::InvalidBatch));
        assert_eq!(ValidatedRepairBatchOutcome::all_accepted(33),
            Err(GlobalRepairError::InvalidBatch));
        let done=x.complete_scoped_batch(&slots,outcome,MonoNs(465_000_002)).unwrap();
        assert_eq!(done,BatchCompletionCounts {
            accepted:12,uncertain:1,definitely_not_sent:19,held_unproven:0});
        assert_eq!(x.snapshot().charged_repairs,13*1400);
        assert_eq!(x.snapshot().held_unused_grants,19*1400);
        assert_eq!(x.snapshot().pending,0);
        x.on_fresh_accepted(dirs[1],10_000,MonoNs(465_000_003)).unwrap();
        assert_eq!(x.local_snapshot(dirs[1]).unwrap().fresh_confirmed_bytes,1_010_000);
        assert_eq!(x.complete_scoped_batch(&slots,outcome,MonoNs(465_000_004)),
            Err(GlobalRepairError::StaleGrant));
    }

    #[test]
    fn r2_owner_ack_before_grant_wrong_reverse_epoch_is_not_delivery() {
        let a=dir(1,WireDirection::ClientToServer);
        let b=dir(2,WireDirection::ServerToClient);
        let mut x=global(2800,2);add(&mut x,a,0);add(&mut x,b,0);
        let sa=route(a,7,1,64);let sb=route(b,8,1,64);
        x.bind_receipt_route(a,sa,MonoNs(0)).unwrap();
        x.bind_receipt_route(b,sb,MonoNs(0)).unwrap();
        let (mut shadow,c)=race_shadow(a,11,1);
        let before=x.snapshot();
        // A plausible user-supplied route/epoch is not proof of post-AEAD
        // admission; a mismatched pinned route is denied before ACK mutation.
        let false_scoped=scoped_receipt(sb,opened(b,8,11),11,1).unwrap();
        assert!(matches!(x.observe_scoped_receipt(a,&mut shadow,&false_scoped,
            MonoNs(1)),Err(GlobalRepairError::WrongReceiptScope)));
        assert_eq!(shadow.outstanding(),1);
        assert_eq!(x.snapshot(),before);
        let truth=scoped_receipt(sa,opened(a,7,11),11,1).unwrap();
        assert_eq!(x.observe_scoped_receipt(a,&mut shadow,&truth,MonoNs(2))
            .unwrap().len(),1);
        let g=x.grant(a,1400,100_000,MonoNs(3)).unwrap();
        assert_eq!(x.reserve_scoped_if_still_missing(g,sa,&shadow,&c,
            1400,MonoNs(3)),Err(GlobalRepairError::StaleCandidate));
        assert_eq!(x.snapshot().charged_repairs,0);
        x.on_fresh_accepted(b,300,MonoNs(4)).unwrap();
        assert_eq!(x.local_snapshot(b).unwrap().fresh_confirmed_bytes,300);
    }

    #[test]
    fn r2_owner_expired_grants_stale_epoch_unknown_suffix_keeps_debt() {
        let (mut x,slots,dirs)=r2_owner_fixture();
        // The first candidates' IO timeout has elapsed; no late callback can
        // retroactively provide definite NotSent credit, even if the client
        // claims to have observed a valid send-prefix layout.
        let proven=ValidatedRepairBatchOutcome::checked(
            32,0,None,BatchSuffixEvidence::ProvenNotAttempted).unwrap();
        assert_eq!(x.complete_scoped_batch(&slots,proven,MonoNs(901_000_000)),
            Err(GlobalRepairError::StaleGrant));
        let past=x.snapshot();
        assert!(past.overdue_uncertain_bytes>=1400);
        assert_eq!(past.held_unused_grants,0);
        assert_eq!(past.charged_repairs,44_800);
        assert!(x.grant(dirs[0],1400,100_000,MonoNs(901_000_001))
            .is_err()); // no new quota in same epoch
        x.on_timer(MonoNs(1_000_000_001)).unwrap();
        assert_eq!(x.snapshot().epoch,1);
        assert!(x.snapshot().overdue_uncertain_bytes>=1400);
        assert_eq!(x.complete_scoped_batch(&slots[..1],
            ValidatedRepairBatchOutcome::all_accepted(1).unwrap(),
            MonoNs(1_000_000_002)),Err(GlobalRepairError::StaleGrant));
    }

    #[test]
    fn r2_owner_epoch_cutover_uncertain_and_notsent_preserve_original_debt() {
        let a=dir(1,WireDirection::ClientToServer);
        let b=dir(2,WireDirection::ServerToClient);
        let mut x=global(4200,2);
        for d in [a,b] {x.register(d,wide_cfg(),MonoNs(999_999_980)).unwrap();}
        let sa=route(a,7,1,64);let sb=route(b,9,1,64);
        x.bind_receipt_route(a,sa,MonoNs(999_999_980)).unwrap();
        x.bind_receipt_route(b,sb,MonoNs(999_999_980)).unwrap();
        let ga=x.grant(a,1400,1000,MonoNs(999_999_981)).unwrap();
        let gb=x.grant(b,1400,1000,MonoNs(999_999_981)).unwrap();
        let (sha,ca)=race_shadow(a,10,999_999_982);
        let (shb,cb)=race_shadow(b,20,999_999_982);
        let ia=x.reserve_scoped_if_still_missing(ga,sa,&sha,&ca,
            1400,MonoNs(999_999_982)).unwrap();
        let ib=x.reserve_scoped_if_still_missing(gb,sb,&shb,&cb,
            1400,MonoNs(999_999_982)).unwrap();
        let result=ValidatedRepairBatchOutcome::checked(
            2,0,Some(0),BatchSuffixEvidence::ProvenNotAttempted).unwrap();
        assert_eq!(x.complete_scoped_batch(&[(ia,sa),(ib,sb)],result,
            MonoNs(1_000_000_001)).unwrap(),
            BatchCompletionCounts{accepted:0,uncertain:1,
                definitely_not_sent:1,held_unproven:0});
        assert_eq!(x.snapshot().previous_epoch_charged,1400);
        assert_eq!(x.snapshot().charged_repairs,0);
        assert_eq!(x.snapshot().held_unused_grants,0);
        let next=x.grant(b,4200,100_000,MonoNs(1_000_000_002)).unwrap();
        assert_eq!(next.bytes(),4200);
        assert_eq!(x.complete_scoped_batch(&[(ib,sb)],
            ValidatedRepairBatchOutcome::checked(1,0,None,
                BatchSuffixEvidence::ProvenNotAttempted).unwrap(),
            MonoNs(1_000_000_003)),Err(GlobalRepairError::StaleGrant));
        assert_eq!(x.snapshot().held_unused_grants,4200);
    }

    /// No unsafe global allocator instrumentation is allowed in the pure
    /// recovery crate. This is actual process CPU *tick* and RSS/VmData
    /// observation via Linux procfs (NOT heap allocation counts or product
    /// p99). An omitted procfs value is reported as unavailable.
    fn r2_p0_proc_cpu_ticks()->Option<u64> {
        let stat=std::fs::read_to_string("/proc/self/stat").ok()?;
        let tail=stat.rsplit_once(") ")?.1;
        let fields:Vec<_>=tail.split_whitespace().collect();
        let user: u64=fields.get(11)?.parse().ok()?;
        let sys: u64=fields.get(12)?.parse().ok()?;
        user.checked_add(sys)
    }
    fn r2_p0_proc_kib(key:&str)->Option<u64> {
        let status=std::fs::read_to_string("/proc/self/status").ok()?;
        status.lines().find_map(|line|{
            let (k,v)=line.split_once(':')?;
            if k!=key {return None;}
            v.split_whitespace().next()?.parse::<u64>().ok()
        })
    }
    /// Synthetic owner fixture + bounded batch settlement, no wire traffic.
    /// The same 32-slot fixture is built for legacy and strict scoped arms.
    fn r2_owner_p0_leg(strict:bool,iterations:usize)->(u128,Option<u64>,Option<u64>,Option<u64>,u64) {
        let cpu_before=r2_p0_proc_cpu_ticks();
        let rss_before=r2_p0_proc_kib("VmRSS");
        let vm_before=r2_p0_proc_kib("VmData");
        let start=std::time::Instant::now();
        let mut accepted=0u64;
        for _ in 0..iterations {
            let (mut x,slots,_)=r2_owner_fixture();
            let outcome=ValidatedRepairBatchOutcome::all_accepted(32).unwrap();
            let r=if strict {
                x.complete_scoped_batch(&slots,outcome,MonoNs(465_000_002)).unwrap()
            } else {
                let ids:[GlobalReservationId;32]=std::array::from_fn(|i|slots[i].0);
                x.complete_batch(&ids,outcome,MonoNs(465_000_002)).unwrap()
            };
            accepted+=r.accepted as u64;
            assert_eq!(x.snapshot().pending,0);
            assert_eq!(x.snapshot().charged_repairs,44_800);
            std::hint::black_box(x.snapshot().charged_repairs);
        }
        let nanos=start.elapsed().as_nanos();
        let cpu_delta=cpu_before.zip(r2_p0_proc_cpu_ticks())
            .map(|(a,b)|b.saturating_sub(a));
        let rss_delta=rss_before.zip(r2_p0_proc_kib("VmRSS"))
            .map(|(a,b)|b.saturating_sub(a));
        let vm_delta=vm_before.zip(r2_p0_proc_kib("VmData"))
            .map(|(a,b)|b.saturating_sub(a));
        (nanos,cpu_delta,rss_delta,vm_delta,accepted)
    }
    #[test]
    fn r2_owner_component_p0_source_locked_repeated_ab_ba_cpu_rss() {
        const LOOPS:usize=128;
        for (pair,order) in ["AB","BA","AB"].iter().enumerate() {
            for strict in if *order=="AB" {[false,true]} else {[true,false]} {
                let (wall,proc_cpu_ticks,rss_grow_kib,vm_grow_kib,accepted)=
                    r2_owner_p0_leg(strict,LOOPS);
                assert_eq!(accepted,LOOPS as u64 * 32);
                assert!(wall>0);
                // The two orderings share the exact same test binary; this
                // records—not thresholds—host-dependent component cost.
                eprintln!(
                    "R2_OWNER_COMPONENT_P0 pair={} order={} arm={} iterations={} slots_per_cycle=32 accepted={} wall_ns={} process_cpu_ticks={:?} rss_growth_kib={:?} vm_data_growth_kib={:?} dynamic_allocation_count=NOT_INSTRUMENTED bounded_pending_slots=32 bounded_pending_bytes=44800 actual_wire_bytes=0 driver_calls=0 authenticated_go_v4=NOT_RUN",
                    pair+1,order,if strict {"scoped"} else {"legacy"},
                    LOOPS,accepted,wall,proc_cpu_ticks,rss_grow_kib,vm_grow_kib,
                );
            }
        }
    }


    #[test]
    fn r2_burst_grants_32_33_timeout_reclaims_unused_no_fresh_hol() {
        let mut x=GlobalRepairAllocator::new(GlobalRepairConfig {
            max_bytes_per_epoch:44_800,max_directions:33,
            max_grant_bytes:1400,max_grant_lifetime_ns:100_000,
            max_pending:32,max_pending_bytes:44_800,
        },MonoNs(0)).unwrap();
        let mut directions=Vec::new();
        for i in 0..33 {
            let d=BudgetDirection {
                tunnel:TunnelKey{slot:i,generation:3},
                direction:WireDirection::ClientToServer,
            };
            x.register(d,wide_cfg(),MonoNs(0)).unwrap();
            directions.push(d);
        }
        let mut leases=Vec::new();
        for i in 0..32 {
            leases.push(x.grant(directions[i],1400,100_000,MonoNs(1)).unwrap());
        }
        assert_eq!(x.snapshot().held_unused_grants,44_800);
        assert_eq!(x.grant(directions[32],1400,100_000,MonoNs(1)),
            Err(GlobalRepairError::GlobalCap));
        // Confirmed FIRST sends cannot be held behind a full repair quota.
        x.on_fresh_accepted(directions[32],10_000,MonoNs(2)).unwrap();
        assert_eq!(x.local_snapshot(directions[32]).unwrap().fresh_confirmed_bytes,10_000);
        x.on_timer(MonoNs(100_001)).unwrap();
        let snap=x.snapshot();
        assert_eq!(snap.held_unused_grants,0);
        assert_eq!(snap.charged_repairs,0);
        assert_eq!(snap.pending,0);
        assert_eq!(x.revoke(leases[0],MonoNs(100_002)),
            Err(GlobalRepairError::StaleGrant));
        assert_eq!(x.grant(directions[32],1400,100_000,MonoNs(100_003))
            .unwrap().bytes(),1400);
        assert_eq!(x.snapshot().held_unused_grants,1400);
    }

}
