//! R2 scoped pure receipt/recovery state (not connected to a live engine).
//! No socket, encryption, PN allocator, engine or platform dependency.
#![forbid(unsafe_code)]
pub use wbd_types::{LaneKey, MonoNs, RecordPn};
pub mod receipt;
pub mod rx_feedback;
pub mod budget;
pub mod global_sparse;
pub mod ingress;
pub mod maturity;
pub mod outer_ack;
pub mod quality_window;
pub use quality_window::{assess as assess_low_rate_quality,WireReport as LowRateQualityWire,QualityError,WindowKey,ClosedWindow,MatureReport,LossBounds};
pub use outer_ack::{OuterAckError, OuterAckIndex, OuterAckUpdate, SackRange32};
pub use maturity::{MatureFirstSend,MaturityConfig,MaturityError,FirstSendKind,FirstSendOutcome,MatureWindow,MaturityPoll,MaturityStop,ObservationCounters};
pub use ingress::{
    admit_opened_receipt, reserve_frozen_submission, complete_driver_prefix,
    DriverPrefixObservation, FrozenRepairSubmission, IngressBatchSettlement,
};
pub use global_sparse::{
    BatchCompletionCounts, BatchSuffixEvidence, ValidatedRepairBatchOutcome,
    GlobalRepairAllocator, GlobalRepairConfig, GlobalRepairError, GlobalRepairSnapshot,
    GlobalReservationId, GrantId, GrantLease,
};
pub use budget::{
    BudgetDirection, BudgetError, BudgetSnapshot, RepairBudget, RepairBudgetConfig,
    ReservationId, WireDirection,
};
pub use rx_feedback::{FeedbackDraft,FeedbackError,FeedbackReceive,FeedbackSendResult,RxFeedbackConfig,RxFeedbackState};
pub use receipt::{
    ReceiptOpenFacts, ReceiptRouteScope, ScopedAuthenticatedReceipt,
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

#[cfg(test)]
mod workpack_tests;
