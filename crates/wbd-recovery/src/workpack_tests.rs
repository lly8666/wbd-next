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
fn r2_pack_009_lost_receipts_single_uncertain_repair_retires_payload() {
    let original=make_frozen(42);
    let same=original.ciphertext.clone();
    let mut tx=sender(2);
    tx.on_sent(original,MonoNs(0),MonoNs(120_000_000)).unwrap();
    let mut rx=receiver();
    assert_eq!(rx.on_authenticated_data(RecordPn(42),MonoNs(0)),FeedbackReceive::First);
    let a=rx.on_due(MonoNs(10_000_000)).unwrap();
    rx.on_send_result(&a,FeedbackSendResult::Accepted,MonoNs(10_000_000)).unwrap();
    let b=rx.on_due(MonoNs(20_000_000)).unwrap();
    rx.on_send_result(&b,FeedbackSendResult::Uncertain,MonoNs(20_000_000)).unwrap();
    let c=tx.on_timer(MonoNs(30_000_000)).candidates.remove(0);
    assert!(tx.preflight(&c,MonoNs(30_000_000)));
    assert!(Arc::ptr_eq(&same,&c.frozen().ciphertext));
    assert_eq!(driver_read(c.frozen()).metadata.pn,RecordPn(42));
    let mut quota=budget();
    quota.on_fresh_accepted(1400,MonoNs(0)).unwrap();
    let reservation=quota.reserve(&c,128,MonoNs(30_000_000)).unwrap();
    quota.on_send_result(reservation,RepairSendResult::Uncertain,MonoNs(30_000_000)).unwrap();
    tx.on_send_result(&c,RepairSendResult::Uncertain,MonoNs(30_000_000)).unwrap();
    assert_eq!(tx.outstanding(),0);
    assert!(tx.on_timer(MonoNs(60_000_000)).candidates.is_empty());

    // A genuine late positive receipt is still valid receiver evidence but
    // cannot resurrect or re-release the already retired sender payload.
    assert_eq!(rx.on_authenticated_data(RecordPn(42),MonoNs(30_000_000)),
        FeedbackReceive::Duplicate);
    let late=rx.on_due(MonoNs(32_000_000)).unwrap();
    let verified=AuthenticatedReceipt::after_authenticated_open(
        lane(),late.largest_data_pn(),late.report_seq(),late.pages().to_vec()).unwrap();
    assert!(tx.on_receipt(&verified,MonoNs(32_000_000)).unwrap().is_empty());
    assert_eq!(tx.on_send_result(&c,RepairSendResult::Accepted,MonoNs(32_000_001)),
        Err(DataError::Stale));
    drop(c);
    assert_eq!(Arc::strong_count(&same),1);
    quota.on_fresh_accepted(1400,MonoNs(60_000_000)).unwrap();
    assert_eq!(quota.snapshot().fresh_confirmed_bytes,2800);
}
#[test]
fn r2_pack_009_reported_scope_only_no_cumulative_hole_or_cross_lane_release() {#[test]
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

/// Deterministic fake clock: the one outer repair uses the exact original
/// ciphertext/PN, then terminal completion prevents any second network repair.
#[test]
fn r2_pack_009_one_actual_repair_old_report_never_rearms_or_reseals() {
    use crate::ReceiptPage;
    let orig=make_frozen(70);
    let wire=orig.ciphertext.clone();
    let mut tx=sender(1);
    tx.on_sent(orig,MonoNs(0),MonoNs(220_000_000)).unwrap();
    let first=tx.on_timer(MonoNs(30_000_000)).candidates.remove(0);
    assert!(Arc::ptr_eq(&wire,&first.frozen().ciphertext));
    assert_eq!(first.frozen().metadata().pn,RecordPn(70));
    assert_eq!(first.frozen().metadata().seq,SeqOffset(0xffff_ffff-2));
    tx.on_send_result(&first,RepairSendResult::Uncertain,MonoNs(30_000_000)).unwrap();
    assert_eq!(tx.outstanding(),0);
    assert_eq!(tx.on_send_result(&first,RepairSendResult::Accepted,
        MonoNs(30_000_001)),Err(DataError::Stale));
    let stale_negative=AuthenticatedReceipt::after_authenticated_open(
        lane(),RecordPn(70),1,vec![ReceiptPage{base_pn:RecordPn(0),bitmap:[0;32]}]).unwrap();
    assert!(tx.on_receipt(&stale_negative,MonoNs(31_000_000)).unwrap().is_empty());
    for at in [60_000_000,90_000_000,220_000_000] {
        let p=tx.on_timer(MonoNs(at));
        assert!(p.candidates.is_empty());
        assert!(p.releases.is_empty());
    }
    assert!(!tx.preflight(&first,MonoNs(31_000_000)));
    drop(first);
    assert_eq!(Arc::strong_count(&wire),1);
}


// PACK-010: strictly typed bridge into the existing pure R2 state.

// PACK-010: strictly typed bridge into the existing pure R2 state. These
// controlled fixtures are NOT live Go authentication or actual kernel claims.
fn ingress_010_broker(max_directions:usize,cap:u64)->crate::GlobalRepairAllocator {
    crate::GlobalRepairAllocator::new(crate::GlobalRepairConfig {
        max_bytes_per_epoch:cap,max_directions,max_grant_bytes:cap,
        max_grant_lifetime_ns:100_000_000,max_pending:32,
        max_pending_bytes:4096,
    },MonoNs(0)).unwrap()
}
fn ingress_010_owner(
    broker:&mut crate::GlobalRepairAllocator,
    tx_lane:LaneKey,direction:WireDirection,pn:u64
)->(ReceiptState<ControlledFrozen>,ReceiptRouteScope,crate::GrantLease,
   crate::RepairCandidate<ControlledFrozen>) {
    let d=BudgetDirection{tunnel:tx_lane.tunnel,direction};
    broker.register(d,RepairBudgetConfig {
        outer_mtu:1400,max_repair_bytes_per_epoch:100_000,
        max_pending_reservations:8,max_pending_bytes:4096,
        io_timeout_ns:10_000_000,
    },MonoNs(30_000_000)).unwrap();
    let reverse=LaneKey{slot:tx_lane.slot+1,..tx_lane};
    let scope=ReceiptRouteScope::checked(
        tx_lane,reverse,direction,[3;16],
        (RecordPn(0),RecordPn(999)),(RecordPn(1000),RecordPn(1099))
    ).unwrap();
    broker.bind_receipt_route(d,scope,MonoNs(30_000_000)).unwrap();
    let mut sh=ReceiptState::new(tx_lane,ReceiptConfig{
        max_shadow_entries:2,pto_ns:30_000_000,
        reorder_window_ns:2_000_000,
    }).unwrap();
    let mut f=make_frozen(pn);
    f.metadata.lane=tx_lane;
    sh.on_sent(f,MonoNs(0),MonoNs(120_000_000)).unwrap();
    let c=sh.on_timer(MonoNs(30_000_000)).candidates.remove(0);
    let g=broker.grant(d,128,80_000_000,MonoNs(30_000_000)).unwrap();
    (sh,scope,g,c)
}
fn ingress_010_open(tx_lane:LaneKey)->ReceiptOpenFacts {
    ReceiptOpenFacts{
        verified_reverse_lane:LaneKey{slot:tx_lane.slot+1,..tx_lane},
        verified_reverse_direction:WireDirection::ServerToClient,
        verified_tunnel_epoch:[3;16],control_record_pn:RecordPn(1000),
    }
}
#[test]
fn r2_pack_010_authenticated_scope_and_late_positive_never_refunds_unknown() {
    use crate::{
        admit_opened_receipt,reserve_frozen_submission,complete_driver_prefix,
        DriverPrefixObservation,BatchSuffixEvidence,GlobalRepairError,ReleaseReason,
    };
    let mut broker=ingress_010_broker(1,128);
    let direction=BudgetDirection{tunnel:lane().tunnel,
        direction:WireDirection::ClientToServer};
    let (mut shadow,scope,lease,c)=ingress_010_owner(
        &mut broker,lane(),WireDirection::ClientToServer,42);
    let original_wire=c.frozen().ciphertext.clone();
    let borrowed=reserve_frozen_submission(
        &mut broker,lease,scope,&shadow,&c,128,MonoNs(30_000_000)).unwrap();
    assert!(Arc::ptr_eq(&original_wire,&c.frozen().ciphertext));
    assert_eq!(borrowed.driver.wire,&original_wire[..]);
    assert_eq!(borrowed.driver.metadata.pn,RecordPn(42));
    assert_eq!(borrowed.driver.metadata.seq,SeqOffset(0xffff_ffff-2));
    let id=borrowed.reservation_id;
    let prefix=DriverPrefixObservation::checked(1,0,Some(0),
        BatchSuffixEvidence::Unproven).unwrap();
    let settled=complete_driver_prefix(
        &mut broker,&[(id,scope)],prefix,MonoNs(30_000_000)).unwrap();
    assert_eq!(settled.counts.uncertain,1);
    shadow.on_send_result(&c,settled.shadow_result(0).unwrap(),
        MonoNs(30_000_000)).unwrap();
    assert_eq!(broker.snapshot().charged_repairs,128);
    let mut bitmap=[0u8;32];
    bitmap[5]|=1<<2; // PN 42 is a positive report; not an exterior ACK
    let page=crate::ReceiptPage{base_pn:RecordPn(0),bitmap};
    let good=ingress_010_open(lane());
    let cases=[
        ReceiptOpenFacts{verified_tunnel_epoch:[9;16],..good},
        ReceiptOpenFacts{control_record_pn:RecordPn(1100),..good},
        ReceiptOpenFacts{verified_reverse_lane:lane(),..good},
        ReceiptOpenFacts{verified_reverse_direction:WireDirection::ClientToServer,..good},
    ];
    for wrong in cases {
        let prior=broker.snapshot();
        assert!(admit_opened_receipt(
            &mut broker,direction,&mut shadow,scope,wrong,
            RecordPn(42),3,vec![page.clone()],MonoNs(31_000_000)).is_err());
        assert_eq!(broker.snapshot(),prior);
        assert_eq!(shadow.outstanding(),0);
    }
    let bad=crate::ReceiptPage{base_pn:RecordPn(256),bitmap:[1;32]};
    assert!(admit_opened_receipt(
        &mut broker,direction,&mut shadow,scope,good,
        RecordPn(42),3,vec![bad],MonoNs(31_000_000)).is_err());
    let received=admit_opened_receipt(
        &mut broker,direction,&mut shadow,scope,good,
        RecordPn(42),3,vec![page],MonoNs(31_000_000)).unwrap();
    assert!(received.is_empty());
    assert_eq!(shadow.outstanding(),0);
    assert_eq!(broker.snapshot().charged_repairs,128);
    assert_eq!(broker.complete(id,RepairSendResult::NotSent,
        MonoNs(31_000_001)),Err(GlobalRepairError::StaleGrant));
    assert!(!shadow.preflight(&c,MonoNs(31_000_001)));
}
#[test]
fn r2_pack_010_kernel_prefix_one_uncertain_unknown_suffix_and_fresh_independent() {
    use crate::{
        reserve_frozen_submission,complete_driver_prefix,DriverPrefixObservation,
        BatchSuffixEvidence,BatchCompletionCounts,GlobalRepairError,
    };
    let lanes=[
        lane(),
        LaneKey{tunnel:TunnelKey{slot:7,generation:12},..lane()},
        LaneKey{tunnel:TunnelKey{slot:8,generation:1},..lane()},
    ];
    let mut broker=ingress_010_broker(3,384);
    let mut owners=Vec::new();
    let mut slots=Vec::new();
    for (i,tx_lane) in lanes.into_iter().enumerate() {
        let (shadow,scope,lease,c)=ingress_010_owner(
            &mut broker,tx_lane,WireDirection::ClientToServer,42+i as u64);
        let borrowed=reserve_frozen_submission(
            &mut broker,lease,scope,&shadow,&c,128,MonoNs(30_000_000)).unwrap();
        assert_eq!(borrowed.driver.metadata.lane,tx_lane);
        assert_eq!(borrowed.driver.wire,c.frozen().bytes());
        slots.push((borrowed.reservation_id,scope));
        owners.push((shadow,c));
    }
    assert_eq!(broker.snapshot().charged_repairs,384);
    let obs=DriverPrefixObservation::checked(3,1,Some(1),
        BatchSuffixEvidence::Unproven).unwrap();
    let mut wrong=slots.clone();
    wrong[2].1=slots[0].1;
    let before=broker.snapshot();
    assert_eq!(complete_driver_prefix(&mut broker,&wrong,obs,
        MonoNs(30_000_001)).err(),Some(GlobalRepairError::WrongReceiptScope));
    assert_eq!(broker.snapshot(),before); // full validation before any refund
    let settlement=complete_driver_prefix(&mut broker,&slots,obs,
        MonoNs(30_000_001)).unwrap();
    assert_eq!(settlement.counts,BatchCompletionCounts{
        accepted:1,uncertain:1,definitely_not_sent:0,held_unproven:1
    });
    assert_eq!(settlement.len(),3);
    assert_eq!(settlement.shadow_result(0),Some(RepairSendResult::Accepted));
    assert_eq!(settlement.shadow_result(1),Some(RepairSendResult::Uncertain));
    assert_eq!(settlement.shadow_result(2),Some(RepairSendResult::Uncertain));
    assert_eq!(settlement.shadow_result(3),None);
    for (i,(sh,c)) in owners.iter_mut().enumerate() {
        sh.on_send_result(c,settlement.shadow_result(i).unwrap(),
            MonoNs(30_000_001)).unwrap();
        assert!(sh.on_timer(MonoNs(30_000_002)).candidates.is_empty());
    }
    assert_eq!(broker.snapshot().charged_repairs,384);
    assert_eq!(broker.snapshot().pending,1);
    let new_direction=BudgetDirection{tunnel:lanes[1].tunnel,
        direction:WireDirection::ClientToServer};
    broker.on_fresh_accepted(new_direction,1400,MonoNs(30_000_002)).unwrap();
    assert_eq!(broker.local_snapshot(new_direction).unwrap().fresh_confirmed_bytes,1400);
    broker.on_timer(MonoNs(40_000_002)).unwrap();
    assert_eq!(broker.snapshot().overdue_uncertain_bytes,128);
    assert_eq!(broker.snapshot().charged_repairs,384);
    assert_eq!(broker.complete(slots[2].0,RepairSendResult::NotSent,
        MonoNs(40_000_003)),Err(GlobalRepairError::StaleGrant));
    broker.on_timer(MonoNs(1_000_000_001)).unwrap();
    assert_eq!(broker.snapshot().overdue_uncertain_bytes,128);
    assert_eq!(broker.grant(new_direction,257,10_000,
        MonoNs(1_000_000_002)),Err(GlobalRepairError::GlobalCap));
}
#[test]
fn r2_pack_010_zero_one_32_33_shape_and_proven_notsent_is_terminal() {
    use crate::{
        DriverPrefixObservation,BatchSuffixEvidence,complete_driver_prefix,
        reserve_frozen_submission,GlobalRepairError,
    };
    let mut broker=ingress_010_broker(1,256);
    let empty=DriverPrefixObservation::checked(0,0,None,
        BatchSuffixEvidence::Unproven).unwrap();
    assert!(complete_driver_prefix(&mut broker,&[],empty,MonoNs(0))
        .unwrap().is_empty());
    assert!(DriverPrefixObservation::checked(32,32,None,
        BatchSuffixEvidence::Unproven).is_ok());
    assert_eq!(DriverPrefixObservation::checked(33,0,None,
        BatchSuffixEvidence::Unproven),Err(GlobalRepairError::InvalidBatch));
    let (mut shadow,scope,lease,c)=ingress_010_owner(
        &mut broker,lane(),WireDirection::ClientToServer,60);
    let id=reserve_frozen_submission(
        &mut broker,lease,scope,&shadow,&c,128,MonoNs(30_000_000))
        .unwrap().reservation_id;
    let known=DriverPrefixObservation::checked(1,0,None,
        BatchSuffixEvidence::ProvenNotAttempted).unwrap();
    let res=complete_driver_prefix(&mut broker,&[(id,scope)],known,
        MonoNs(30_000_000)).unwrap();
    assert_eq!(res.counts.definitely_not_sent,1);
    assert_eq!(res.shadow_result(0),Some(RepairSendResult::NotSent));
    shadow.on_send_result(&c,RepairSendResult::NotSent,MonoNs(30_000_000)).unwrap();
    assert_eq!(broker.snapshot().charged_repairs,0);
    assert_eq!(shadow.outstanding(),0);
    assert!(shadow.on_timer(MonoNs(60_000_000)).candidates.is_empty());
    assert_eq!(broker.complete(id,RepairSendResult::NotSent,
        MonoNs(60_000_000)),Err(GlobalRepairError::StaleGrant));
}
