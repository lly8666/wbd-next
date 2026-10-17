//! PACK-010: owner-local typed integration edge into the *existing* R2 state.
//! These helpers DO NOT AEAD-open records, certify a platform send or schedule
//! the engine. Only M0 may supply independently verified reverse-lane facts
//! and trusted driver prefix/proven-not-attempted observations.
use wbd_types::buffer_contract::{driver_read, DriverRead, FrozenRecordHandle};
use wbd_types::{MonoNs, RecordPn};
use crate::{
    BatchCompletionCounts, BatchSuffixEvidence, BudgetDirection, GlobalRepairAllocator,
    GlobalRepairError, GlobalReservationId, GrantLease, ReceiptOpenFacts, ReceiptPage,
    ReceiptRouteScope, ReceiptState, Release, RepairCandidate, RepairSendResult,
    ScopedAuthenticatedReceipt, ValidatedRepairBatchOutcome,
};

/// M0 calls this only after successful AEAD/open, control PN replay filtering,
/// and authoritative tunnel/lane/epoch lookup; fields alone are not a proof.
/// Invalid scope/bitmap is rejected BEFORE touching shadow or quota. Kernel
/// Accepted and ordinary TCP ACK never call this endpoint.
pub fn admit_opened_receipt<H: FrozenRecordHandle>(
    broker: &mut GlobalRepairAllocator,
    direction: BudgetDirection,
    shadow: &mut ReceiptState<H>,
    independently_pinned: ReceiptRouteScope,
    opened: ReceiptOpenFacts,
    largest_data_pn: RecordPn,
    report_seq: u32,
    pages: Vec<ReceiptPage>,
    now: MonoNs,
) -> Result<Vec<Release<H>>, GlobalRepairError> {
    let scoped=ScopedAuthenticatedReceipt::checked_after_open(
        independently_pinned,opened,largest_data_pn,report_seq,pages)
        .map_err(GlobalRepairError::Receipt)?;
    broker.observe_scoped_receipt(direction,shadow,&scoped,now)
}

/// A borrow of the original immutable record for a real driver submission.
/// The grant debit and stale candidate/generation check both happen before
/// publishing these bytes. Caller must check ReceiptState::preflight again
/// immediately before actual syscall, because it can race an authenticated ACK.
pub struct FrozenRepairSubmission<'a> {
    pub reservation_id: GlobalReservationId,
    pub driver: DriverRead<'a>,
}
pub fn reserve_frozen_submission<'a,H: FrozenRecordHandle>(
    broker: &mut GlobalRepairAllocator,
    lease: GrantLease,
    pinned: ReceiptRouteScope,
    shadow: &ReceiptState<H>,
    candidate: &'a RepairCandidate<H>,
    outer_wire_bytes: u64,
    now: MonoNs,
) -> Result<FrozenRepairSubmission<'a>,GlobalRepairError> {
    let reservation_id=broker.reserve_scoped_if_still_missing(
        lease,pinned,shadow,candidate,outer_wire_bytes,now)?;
    Ok(FrozenRepairSubmission{reservation_id,driver:driver_read(candidate.frozen())})
}

/// A trusted PLATFORM observation in original frame order, 0..=32 slots.
/// The platform must not invent ProvenNotAttempted from EAGAIN, short writes,
/// cancellation without proof, or missing completion. In those cases use
/// Unproven: held pending quota times out as conservative uncertain debt.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct DriverPrefixObservation {
    total:usize, accepted_prefix:usize, uncertain_at:Option<usize>,
    suffix:BatchSuffixEvidence,
}
impl DriverPrefixObservation {
    pub fn checked(total:usize,accepted_prefix:usize,
        uncertain_at:Option<usize>,suffix:BatchSuffixEvidence)
        ->Result<Self,GlobalRepairError> {
        ValidatedRepairBatchOutcome::checked(total,accepted_prefix,uncertain_at,suffix)?;
        Ok(Self{total,accepted_prefix,uncertain_at,suffix})
    }
}

/// The result includes one shadow-local status per original slot. M0 MUST
/// apply these statuses once to matching ReceiptState::on_send_result after
/// settling quota, skipping DataError::Stale when a valid late receipt already
/// retired that shadow. No slot can be transformed into peer delivery.
/// HeldUnproven is shadow-Uncertain immediately (an attempt may have occurred)
/// while the global reservation stays pending/charged until IO timeout.
/// Late definite NotSent cannot retroactively roll back that shadow attempt.
pub struct IngressBatchSettlement {
    pub counts:BatchCompletionCounts,
    len:usize,
    shadow_results:[RepairSendResult;32],
}
impl IngressBatchSettlement {
    pub fn len(&self)->usize{self.len}
    pub fn is_empty(&self)->bool{self.len==0}
    pub fn shadow_result(&self,index:usize)->Option<RepairSendResult>{
        (index<self.len).then_some(self.shadow_results[index])
    }
}

/// Does not allocate, seal, copy ciphertext, regenerate PN or touch fresh.
/// Delegates all full-batch scope/identity/duplicate prevalidation and epoch
/// refund rules to the existing process-wide quota owner. On invalid scope
/// no send is falsely refunded and no shadow result is returned.
pub fn complete_driver_prefix(
    broker:&mut GlobalRepairAllocator,
    ordered:&[(GlobalReservationId,ReceiptRouteScope)],
    observation:DriverPrefixObservation,
    now:MonoNs,
)->Result<IngressBatchSettlement,GlobalRepairError>{
    if ordered.len()!=observation.total{return Err(GlobalRepairError::InvalidBatch);}
    let validated=ValidatedRepairBatchOutcome::checked(
        observation.total,observation.accepted_prefix,
        observation.uncertain_at,observation.suffix)?;
    let counts=broker.complete_scoped_batch(ordered,validated,now)?;
    let mut statuses=[RepairSendResult::Uncertain;32];
    for (i,status) in statuses.iter_mut().enumerate().take(observation.total) {
        *status=if i<observation.accepted_prefix {
            RepairSendResult::Accepted
        }else if observation.uncertain_at==Some(i) ||
            observation.suffix==BatchSuffixEvidence::Unproven {
            RepairSendResult::Uncertain
        }else {
            RepairSendResult::NotSent
        };
    }
    Ok(IngressBatchSettlement{counts,len:observation.total,shadow_results:statuses})
}
