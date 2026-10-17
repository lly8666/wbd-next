//! PACK-009: deterministic controlled-driver cross-component tests.
//! These inputs represent an M0/M3-authenticated session, NOT raw network
//! bytes; no fake fixture here may authorize production feedback admission.
use std::sync::Arc;
use crate::{
    AuthenticatedReceipt, FeedbackReceive, FeedbackSendResult, ReceiptConfig,
    ReceiptOpenFacts, ReceiptRouteScope, ReceiptState, RepairBudget, RepairBudgetConfig,
    RepairSendResult, RxFeedbackConfig, RxFeedbackState, ReleaseReason, BudgetDirection,
    WireDirection,
};
use wbd_types::{BufferKey,LaneKey,MonoNs,RecordPn,SeqOffset,TunnelKey,DataError};
use wbd_types::buffer_contract::{
    BufferOrigin,FrozenMetadata,FrozenRecordHandle,driver_read,
};
#[derive(Clone)]
struct ControlledFrozen { ciphertext:Arc<[u8]>,origin:BufferOrigin,metadata:FrozenMetadata }
impl FrozenRecordHandle for ControlledFrozen {
    fn origin(&self)->BufferOrigin {self.origin}
    fn metadata(&self)->FrozenMetadata {self.metadata}
    fn bytes(&self)->&[u8] {&self.ciphertext}
}
fn lane()->LaneKey {LaneKey{tunnel:TunnelKey{slot:7,generation:11},slot:3,generation:2}}
fn make_frozen(pn:u64)->ControlledFrozen {
    ControlledFrozen {
        ciphertext:Arc::from([0x73,0x12,0x40,0x99,0x0e,0x06].as_slice()),
        origin:BufferOrigin{owner_arena:9,key:BufferKey{slot:pn as u32,generation:88}},
        metadata:FrozenMetadata{lane:lane(),pn:RecordPn(pn),seq:SeqOffset(0xffff_ffff-2),carrier_snapshot:4},
    }
}
fn sender(max:usize)->ReceiptState<ControlledFrozen> {
    ReceiptState::new(lane(),ReceiptConfig {
        max_shadow_entries:max,pto_ns:30_000_000,reorder_window_ns:2_000_000
    }).unwrap()
}
fn receiver()->RxFeedbackState {
    RxFeedbackState::new(RxFeedbackConfig {
        max_retained_pages:4,max_pages_per_report:8,
        retention_ns:150_000_000,srtt_ns:40_000_000
    }).unwrap()
}
fn budget()->RepairBudget {
    RepairBudget::new(BudgetDirection{tunnel:lane().tunnel,
        direction:WireDirection::ClientToServer},
        RepairBudgetConfig{outer_mtu:1400,max_repair_bytes_per_epoch:100_000,
        max_pending_reservations:4,max_pending_bytes:5600,io_timeout_ns:10_000_000},
        MonoNs(0)).unwrap()
}
#[test]
fn r2_pack_009_two_lost_receipts_pto_same_frozen_handle_late_positive() {
    let original=make_frozen(42);
    let same=original.ciphertext.clone();
    let mut tx=sender(2);
    tx.on_sent(original,MonoNs(0),MonoNs(120_000_000)).unwrap();
    let mut rx=receiver();
    assert_eq!(rx.on_authenticated_data(RecordPn(42),MonoNs(0)),FeedbackReceive::First);
    let a=rx.on_due(MonoNs(10_000_000)).unwrap();
    assert_eq!(a.pages().len(),1);
    rx.on_send_result(&a,FeedbackSendResult::Accepted,MonoNs(10_000_000)).unwrap();
    let b=rx.on_due(MonoNs(20_000_000)).unwrap();
    rx.on_send_result(&b,FeedbackSendResult::Uncertain,MonoNs(20_000_000)).unwrap();
    // Both sealed controls were lost on the reverse path: no TX receipt yet.
    assert_eq!(tx.outstanding(),1);
    assert!(tx.on_timer(MonoNs(29_999_999)).candidates.is_empty());
    let c=tx.on_timer(MonoNs(30_000_000)).candidates.remove(0);
    assert!(tx.preflight(&c,MonoNs(30_000_000)));
    assert!(Arc::ptr_eq(&same,&c.frozen().ciphertext));
    let borrowed=driver_read(c.frozen());
    assert_eq!(borrowed.metadata.seq,SeqOffset(0xffff_ffff-2));
    assert_eq!(borrowed.metadata.pn,RecordPn(42));
    assert_eq!(borrowed.wire,&same[..]);
    let mut quota=budget();
    quota.on_fresh_accepted(1400,MonoNs(0)).unwrap();
    let reservation=quota.reserve(&c,128,MonoNs(30_000_000)).unwrap();
    quota.on_send_result(reservation,RepairSendResult::Uncertain,MonoNs(30_000_000)).unwrap();
    tx.on_send_result(&c,RepairSendResult::Uncertain,MonoNs(30_000_000)).unwrap();
    assert_eq!(quota.snapshot().charged_repair_bytes,128);
    assert_eq!(quota.on_send_result(reservation,RepairSendResult::NotSent,MonoNs(30_000_001)).err(),
        Some(crate::BudgetError::StaleReservation));
    assert!(tx.on_timer(MonoNs(30_000_001)).candidates.is_empty());
    // A real duplicate DATA on RX triggers one bounded feedback reassertion,
    // rather than control ACK-of-ACK traffic or a same-evidence extra repair.
    assert_eq!(rx.on_authenticated_data(RecordPn(42),MonoNs(30_000_000)),FeedbackReceive::Duplicate);
    let c_receipt=rx.on_due(MonoNs(32_000_000)).unwrap();
    let verified_open=AuthenticatedReceipt::after_authenticated_open(
        lane(),c_receipt.largest_data_pn(),c_receipt.report_seq(),
        c_receipt.pages().to_vec()).unwrap();
    let releases=tx.on_receipt(&verified_open,MonoNs(32_000_000)).unwrap();
    assert_eq!(releases.len(),1);
    assert_eq!(releases[0].reason,ReleaseReason::ReceivedByPeer);
    assert!(Arc::ptr_eq(&releases[0].frozen.ciphertext,&same));
    assert!(!tx.preflight(&c,MonoNs(32_000_000)));
    assert!(tx.on_timer(MonoNs(60_000_000)).candidates.is_empty());
    // Fresh sends never wait for repair quota or an ACK.
    quota.on_fresh_accepted(1400,MonoNs(60_000_000)).unwrap();
    assert_eq!(quota.snapshot().fresh_confirmed_bytes,2800);
}
#[test]
fn r2_pack_009_reported_scope_only_no_cumulative_hole_or_cross_lane_release() {
    let mut tx=sender(3);
    tx.on_sent(make_frozen(1),MonoNs(0),MonoNs(120_000_000)).unwrap();
    tx.on_sent(make_frozen(600),MonoNs(0),MonoNs(120_000_000)).unwrap();
    let mut rx=receiver();
    assert_eq!(rx.on_authenticated_data(RecordPn(600),MonoNs(0)),FeedbackReceive::First);
    let d=rx.on_due(MonoNs(10_000_000)).unwrap();
    assert_eq!(d.pages().len(),1);
    assert_eq!(d.pages()[0].base_pn,RecordPn(512));
    let reverse=LaneKey{slot:4,..lane()};
    let scope=ReceiptRouteScope::checked(
        lane(),reverse,WireDirection::ClientToServer,[3;16],
        (RecordPn(0),RecordPn(1000)),(RecordPn(1001),RecordPn(1100))).unwrap();
    let opened=ReceiptOpenFacts{
        verified_reverse_lane:reverse,
        verified_reverse_direction:WireDirection::ServerToClient,
        verified_tunnel_epoch:[3;16],control_record_pn:RecordPn(1001),
    };
    let wrong=ReceiptOpenFacts{verified_tunnel_epoch:[4;16],..opened};
    assert!(matches!(crate::ScopedAuthenticatedReceipt::checked_after_open(
        scope,wrong,d.largest_data_pn(),d.report_seq(),d.pages().to_vec()),Err(DataError::Stale)));
    let verified=crate::ScopedAuthenticatedReceipt::checked_after_open(
        scope,opened,d.largest_data_pn(),d.report_seq(),d.pages().to_vec()).unwrap();
    let released=tx.on_receipt(verified.receipt(),MonoNs(10_000_000)).unwrap();
    assert_eq!(released.len(),1);
    assert_eq!(released[0].pn,RecordPn(600));
    // PN 1 is in a *different, unreported* page; no cumulative prefix.
    assert_eq!(tx.outstanding(),1);
    assert!(tx.on_timer(MonoNs(29_999_999)).candidates.is_empty());
    // It may receive one PTO tail candidate; never held behind missing PN.
    assert_eq!(tx.on_timer(MonoNs(30_000_000)).candidates.len(),1);
}


/// Controlled same-slot/new-generation sessions share a PROCESS budget, not
/// two independent sparse floors. An unproven partial-syscall suffix remains
/// charged even if its shadow subsequently receives an authenticated positive
/// receipt; neither that receipt nor a late completion can refund it.
#[test]
fn r2_pack_009_generation_uncertain_held_and_fresh_still_progress() {
    use crate::{
        GlobalRepairAllocator, GlobalRepairConfig, GlobalRepairError,
        ValidatedRepairBatchOutcome, BatchSuffixEvidence, BatchCompletionCounts,
        ReceiptPage,
    };
    let old_lane=lane();
    let new_lane=LaneKey{
        tunnel:TunnelKey{slot:old_lane.tunnel.slot,
            generation:old_lane.tunnel.generation+1},
        ..old_lane
    };
    let old_direction=BudgetDirection{
        tunnel:old_lane.tunnel,direction:WireDirection::ClientToServer};
    let new_direction=BudgetDirection{
        tunnel:new_lane.tunnel,direction:WireDirection::ClientToServer};
    let local=RepairBudgetConfig{
        outer_mtu:1400,max_repair_bytes_per_epoch:100_000,
        max_pending_reservations:4,max_pending_bytes:5600,
        io_timeout_ns:10_000_000,
    };
    let mut global=GlobalRepairAllocator::new(GlobalRepairConfig{
        max_bytes_per_epoch:256,max_directions:2,max_grant_bytes:256,
        max_grant_lifetime_ns:200_000_000,
        max_pending:2,max_pending_bytes:256,
    },MonoNs(0)).unwrap();
    for d in [old_direction,new_direction] {
        global.register(d,local,MonoNs(0)).unwrap();
        global.on_fresh_accepted(d,1400,MonoNs(0)).unwrap();
    }
    let mut old_shadow=sender(1);
    old_shadow.on_sent(make_frozen(42),MonoNs(0),MonoNs(120_000_000))
        .unwrap();
    let mut changed=make_frozen(42);
    changed.metadata.lane=new_lane;
    changed.origin.key.generation+=1;
    let mut new_shadow=ReceiptState::new(new_lane,ReceiptConfig{
        max_shadow_entries:1,pto_ns:30_000_000,reorder_window_ns:2_000_000
    }).unwrap();
    new_shadow.on_sent(changed,MonoNs(0),MonoNs(120_000_000))
        .unwrap();
    let a=old_shadow.on_timer(MonoNs(30_000_000)).candidates.remove(0);
    let b=new_shadow.on_timer(MonoNs(30_000_000)).candidates.remove(0);
    let ga=global.grant(old_direction,128,80_000_000,MonoNs(30_000_000))
        .unwrap();
    let gb=global.grant(new_direction,128,80_000_000,MonoNs(30_000_000))
        .unwrap();
    let ia=global.reserve_if_still_missing(ga,&old_shadow,&a,128,
        MonoNs(30_000_000)).unwrap();
    let ib=global.reserve_if_still_missing(gb,&new_shadow,&b,128,
        MonoNs(30_000_000)).unwrap();
    assert_eq!(global.snapshot().charged_repairs,256);
    assert_eq!(global.snapshot().pending,2);
    assert_eq!(global.complete_batch(&[ia,ib],
        ValidatedRepairBatchOutcome::checked(2,0,Some(0),
            BatchSuffixEvidence::Unproven).unwrap(),
        MonoNs(30_000_001)).unwrap(),BatchCompletionCounts{
            accepted:0,uncertain:1,definitely_not_sent:0,held_unproven:1
        });
    old_shadow.on_send_result(&a,RepairSendResult::Uncertain,
        MonoNs(30_000_001)).unwrap();

    // An authenticated positive observation releases the new shadow, but
    // cannot prove that its outstanding driver submission was NotSent.
    let mut bitmap=[0u8;32];
    bitmap[42/8] |= 1 << (42%8);
    let positive=AuthenticatedReceipt::after_authenticated_open(
        new_lane,RecordPn(42),1,vec![
            ReceiptPage{base_pn:RecordPn(0),bitmap}
        ]).unwrap();
    let released=new_shadow.on_receipt(&positive,MonoNs(31_000_000))
        .unwrap();
    assert_eq!(released.len(),1);
    assert!(!new_shadow.preflight(&b,MonoNs(31_000_000)));
    assert_eq!(global.snapshot().charged_repairs,256);
    global.on_timer(MonoNs(40_000_001)).unwrap();
    assert_eq!(global.snapshot().overdue_uncertain_bytes,128);
    assert_eq!(global.snapshot().pending,0);
    assert_eq!(global.complete(ib,RepairSendResult::NotSent,
        MonoNs(40_000_002)),Err(GlobalRepairError::StaleGrant));
    assert_eq!(global.retire_tunnel(old_lane.tunnel,
        MonoNs(40_000_003)).unwrap(),1);
    // Repair cap is exhausted; an unrelated new generation's F is never
    // waiting on old shadow, old quota, or missing control feedback.
    global.on_fresh_accepted(new_direction,1400,MonoNs(40_000_004))
        .unwrap();
    assert_eq!(global.local_snapshot(new_direction).unwrap()
        .fresh_confirmed_bytes,2800);
    assert_eq!(global.snapshot().charged_repairs,256);
    assert_eq!(global.snapshot().overdue_uncertain_bytes,128);
    global.on_timer(MonoNs(1_000_000_001)).unwrap();
    assert_eq!(global.grant(new_direction,129,100_000,
        MonoNs(1_000_000_002)),Err(GlobalRepairError::GlobalCap));
    assert!(global.grant(new_direction,128,100_000,
        MonoNs(1_000_000_003)).is_ok());
}

/// Deterministic fake clock: an old gap report may not cause two immediate
/// repairs; NotSent is NOT an attempt, Uncertain and Accepted each count one.
/// All candidates retain the exact same immutable ciphertext and PN.
#[test]
fn r2_pack_009_two_actual_repairs_old_report_and_generation_never_reseal() {
    use crate::ReceiptPage;
    let orig=make_frozen(70);
    let wire=orig.ciphertext.clone();
    let mut tx=sender(1);
    tx.on_sent(orig,MonoNs(0),MonoNs(220_000_000)).unwrap();
    let first=tx.on_timer(MonoNs(30_000_000)).candidates.remove(0);
    assert!(Arc::ptr_eq(&wire,&first.frozen().ciphertext));
    tx.on_send_result(&first,RepairSendResult::Uncertain,
        MonoNs(30_000_000)).unwrap();
    assert_eq!(tx.on_send_result(&first,RepairSendResult::Accepted,
        MonoNs(30_000_001)),Err(DataError::Stale));
    let empty=ReceiptPage{base_pn:RecordPn(0),bitmap:[0;32]};
    let stale_negative=AuthenticatedReceipt::after_authenticated_open(
        lane(),RecordPn(70),1,vec![empty]).unwrap();
    tx.on_receipt(&stale_negative,MonoNs(31_000_000)).unwrap();
    assert!(tx.on_timer(MonoNs(31_000_000)).candidates.is_empty());
    assert!(tx.on_timer(MonoNs(59_999_999)).candidates.is_empty());
    let not_sent=tx.on_timer(MonoNs(60_000_000)).candidates.remove(0);
    assert!(Arc::ptr_eq(&wire,&not_sent.frozen().ciphertext));
    tx.on_send_result(&not_sent,RepairSendResult::NotSent,
        MonoNs(60_000_000)).unwrap();
    assert_eq!(tx.on_send_result(&not_sent,RepairSendResult::Accepted,
        MonoNs(60_000_001)),Err(DataError::Stale));
    assert!(tx.on_timer(MonoNs(89_999_999)).candidates.is_empty());
    let second=tx.on_timer(MonoNs(90_000_000)).candidates.remove(0);
    assert_ne!(second.retry_epoch(),not_sent.retry_epoch());
    assert!(Arc::ptr_eq(&wire,&second.frozen().ciphertext));
    assert_eq!(second.frozen().metadata().pn,RecordPn(70));
    assert_eq!(second.frozen().metadata().seq,
        SeqOffset(0xffff_ffff-2));
    assert_eq!(driver_read(second.frozen()).wire,&wire[..]);
    tx.on_send_result(&second,RepairSendResult::Accepted,
        MonoNs(90_000_000)).unwrap();
    let stale_again=AuthenticatedReceipt::after_authenticated_open(
        lane(),RecordPn(70),2,vec![ReceiptPage{
            base_pn:RecordPn(0),bitmap:[0;32]}]).unwrap();
    tx.on_receipt(&stale_again,MonoNs(95_000_000)).unwrap();
    assert!(tx.on_timer(MonoNs(120_000_000)).candidates.is_empty());
    assert!(!tx.preflight(&first,MonoNs(120_000_000)));
    assert!(!tx.preflight(&second,MonoNs(120_000_000)));
    let expired=tx.on_timer(MonoNs(220_000_000));
    assert_eq!(expired.releases.len(),1);
    assert_eq!(expired.releases[0].reason,ReleaseReason::HardExpired);
    assert_eq!(tx.outstanding(),0);
}
