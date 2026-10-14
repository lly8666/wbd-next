//! R0 shared Rust-only value types. NOT a C ABI nor a wire layout.
//! Authoritative protocol contract: docs/architecture/modules/00-CONTRACTS.md.
#![forbid(unsafe_code)]

/// M0 Rust-only cross-worker buffer ownership hand-off contract; M1 owns concrete arena.
pub mod buffer_contract;

#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd, Hash)]
pub struct MonoNs(pub u64);

impl MonoNs {
    pub fn checked_after(self, delta_ns: u64) -> Option<Self> {
        self.0.checked_add(delta_ns).map(Self)
    }
    pub fn elapsed_since(self, before: Self) -> u64 {
        self.0.saturating_sub(before.0)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd, Hash)]
pub struct ConfigRevision(pub u64);

impl ConfigRevision {
    pub fn is_newer_than(self, installed: Self) -> bool {
        self.0 > installed.0
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub struct TunnelKey {
    pub slot: u32,
    pub generation: u32,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub struct LaneKey {
    pub tunnel: TunnelKey,
    pub slot: u32,
    pub generation: u32,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub struct BufferKey {
    pub slot: u32,
    pub generation: u32,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd, Hash)]
pub struct RecordPn(pub u64);
#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd, Hash)]
pub struct SeqOffset(pub u64);
#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd, Hash)]
pub struct LogicalPacketId(pub u64);
#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd, Hash)]
pub struct BlockIdExt(pub u64);

/// Explicitly retire a slot at generation exhaustion; never alias a previous key.
pub fn next_generation(generation: u32) -> Option<u32> {
    generation.checked_add(1)
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LimitedResource {
    ArenaBytes,
    ReturnQueue,
    ShadowBytes,
    TimerNodes,
    ReassemblyBytes,
    PendingWork,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DataError {
    Malformed,
    Unsupported,
    Stale,
    Duplicate,
    Late,
    NoCapacity(LimitedResource),
    WouldBlock,
    IoUncertain,
    FatalLane,
    FatalEngine,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn r0_clock_checked_and_saturating() {
        assert_eq!(MonoNs(10).checked_after(20), Some(MonoNs(30)));
        assert_eq!(MonoNs(u64::MAX).checked_after(1), None);
        assert_eq!(MonoNs(20).elapsed_since(MonoNs(30)), 0);
        assert_eq!(MonoNs(30).elapsed_since(MonoNs(20)), 10);
    }

    #[test]
    fn r0_revision_rejects_replay() {
        assert!(!ConfigRevision(3).is_newer_than(ConfigRevision(3)));
        assert!(!ConfigRevision(2).is_newer_than(ConfigRevision(3)));
        assert!(ConfigRevision(4).is_newer_than(ConfigRevision(3)));
    }

    #[test]
    fn r0_generations_do_not_wrap() {
        assert_eq!(next_generation(0), Some(1));
        assert_eq!(next_generation(u32::MAX - 1), Some(u32::MAX));
        assert_eq!(next_generation(u32::MAX), None);
        assert_ne!(
            LaneKey { tunnel: TunnelKey { slot: 1, generation: 1 }, slot: 2, generation: 1 },
            LaneKey { tunnel: TunnelKey { slot: 1, generation: 2 }, slot: 2, generation: 1 }
        );
    }

    #[test]
    fn r0_identity_types_are_distinct() {
        let pn = RecordPn(u64::MAX);
        let seq = SeqOffset(u64::MAX);
        let logical = LogicalPacketId(u64::MAX);
        let block = BlockIdExt(u64::MAX);
        assert_eq!(pn.0, seq.0);
        assert_eq!(logical.0, block.0);
        assert_ne!(BufferKey { slot: 4, generation: 1 }, BufferKey { slot: 4, generation: 2 });
    }

    #[test]
    fn r0_capacity_errors_name_resources() {
        assert_eq!(
            DataError::NoCapacity(LimitedResource::ShadowBytes),
            DataError::NoCapacity(LimitedResource::ShadowBytes)
        );
        assert_ne!(DataError::NoCapacity(LimitedResource::ShadowBytes), DataError::WouldBlock);
    }
}
