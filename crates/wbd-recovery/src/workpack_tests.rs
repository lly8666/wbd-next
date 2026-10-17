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
