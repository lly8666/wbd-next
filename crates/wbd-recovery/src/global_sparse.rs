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
use crate::receipt::{RepairCandidate, RepairSendResult};
use wbd_types::buffer_contract::FrozenRecordHandle;
use wbd_types::{MonoNs, TunnelKey};

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
            epoch: self.current.index, bytes: wire_bytes, until,
        });
        Ok(GlobalReservationId(next))
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
}
