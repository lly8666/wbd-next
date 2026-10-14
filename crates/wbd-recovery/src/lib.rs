//! R2 scoped pure receipt/recovery state (not connected to a live engine).
//! No socket, encryption, PN allocator, engine or platform dependency.
#![forbid(unsafe_code)]
pub use wbd_types::{LaneKey, MonoNs, RecordPn};
pub mod receipt;
pub use receipt::{
    AuthenticatedReceipt, PollResult, ReceiptConfig, ReceiptPage, ReceiptState,
    Release, ReleaseReason, RepairCandidate, RepairSendResult,
};

/// True only after M0 wires and qualifies product recovery. Pure R2 tests
/// alone cannot advertise a working data plane.
pub const RECOVERY_ENGINE_READY: bool = false;

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn bootstrap_is_not_product_qualification() {
        assert!(!RECOVERY_ENGINE_READY);
        assert_eq!(MonoNs(9).checked_after(1), Some(MonoNs(10)));
        assert_eq!(RecordPn(u64::MAX).0, u64::MAX);
    }
}
