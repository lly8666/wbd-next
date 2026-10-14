//! Authenticated-input FEC BlockID32 wrapping/retirement tests.
use crate::fec_block_id::{
    AuthenticatedContext,COMPACT_MS,FecBlockIdOwner,HALF_SPACE,HEAVY_MS,
    IdConfig,IdError,TrackedPhase,
};
use crate::fec_rx::{Config as RxConfig,Direction,FecRxOwner,RxError};
use crate::fec_tx::FecTxOwner;
use crate::link_fec_wire::{inspect_fec_frame,FEC_HEADER};
fn ctx(generation:u32)->AuthenticatedContext {
    AuthenticatedContext{epoch:7,direction:Direction::ClientToServer,trusted_generation:generation}
}
fn config(anchor:u64,retired_floor:u64)->IdConfig {
    IdConfig{epoch:7,direction:Direction::ClientToServer,anchor,retired_floor,
        max_forward:1024,max_reorder:1024,max_heavy:4,max_compact:4}
}
fn owner(anchor:u64,floor:u64)->FecBlockIdOwner{
    FecBlockIdOwner::new(config(anchor,floor)).unwrap()
}
#[test]
fn r1_blockid_pinned_go_56b_source_and_final_parity_wire_oracle(){
    let old=include_str!("../../../r0/fixtures/legacy-link-fec-wire-v1.txt");
    let source=old.lines().find(|l|l.starts_with("fec-source|")).unwrap()
        .split('|').nth(1).unwrap();
    let frame=(0..source.len()).step_by(2)
        .map(|i|u8::from_str_radix(&source[i..i+2],16).unwrap())
        .collect::<Vec<_>>();
    let head=inspect_fec_frame(&frame,59).unwrap().header;
    assert_eq!(head.block_id,0x01020304);
    assert_eq!((frame.len(),FEC_HEADER),(59,56));
    let mut ext=owner(0x01020303,0x01020302);
    let obs=ext.observe_wire_after_auth(&frame,59,ctx(0),10).unwrap();
    assert_eq!(obs.id_ext,u64::from(head.block_id));
    assert!(obs.first_seen);
    assert_eq!(ext.observe_wire_after_auth(&frame,59,ctx(0),11).unwrap().first_seen,false);
    assert_eq!(ext.stats().distinct_accepted,1);
}
#[test]
fn r1_blockid_zero_reserved_and_zero_length_duplicate_never_advances(){
    let mut s=owner(0,0);
    let initial=s.stats();
    assert_eq!(s.observe_id_after_auth(0,ctx(0),7),Err(IdError::ReservedZero));
    assert_eq!(s.stats(),initial);
    assert_eq!(s.observe_id_after_auth(1,ctx(0),10).unwrap().id_ext,1);
    for now in [10,100,200,500]{
        let p=s.observe_id_after_auth(1,ctx(0),now).unwrap();
        assert!(!p.first_seen); assert_eq!(p.phase,TrackedPhase::Heavy);
    }
    assert_eq!((s.stats().highest,s.stats().distinct_accepted,s.stats().duplicates),(1,1,4));
    s.expire(3_010);
    assert_eq!(s.stats().compact,1);
    assert_eq!(s.observe_id_after_auth(1,ctx(0),3_011).unwrap().phase,TrackedPhase::Compact);
    assert_eq!(s.stats().highest,1);
}
#[test]
fn r1_blockid_wrap_ffffffff_to_one_skips_reserved_zero_and_uses_new_generation(){
    let mut s=owner(0xffff_fffe,0xffff_fffd);
    assert_eq!(s.observe_id_after_auth(0xffff_ffff,ctx(0),1).unwrap().id_ext,0xffff_ffff);
    assert_eq!(s.preview(0,ctx(1)),Err(IdError::ReservedZero));
    assert_eq!(s.preview(1,ctx(0)),Err(IdError::WrongGeneration));
    assert_eq!(s.observe_id_after_auth(1,ctx(1),2).unwrap().id_ext,0x1_0000_0001);
    assert_eq!(s.observe_id_after_auth(2,ctx(1),3).unwrap().id_ext,0x1_0000_0002);
    assert_eq!((s.stats().highest,s.stats().heavy),(0x1_0000_0002,3));
    assert_eq!(s.preview(0xffff_ffff,ctx(0)),Ok(0xffff_ffff));
    s.advance_retired_floor(0xffff_ffff);
    assert_eq!(s.preview(0xffff_ffff,ctx(0)),Err(IdError::Retired));
    assert_eq!(s.preview(1,ctx(0)),Err(IdError::WrongGeneration));
}
#[test]
fn r1_blockid_halfspace_and_far_jumps_are_fail_closed_not_guessed(){
    let mut s=owner(1,0);
    let before=s.stats();
    assert_eq!(s.preview((1u64+HALF_SPACE) as u32,ctx(0)),Err(IdError::HalfSpaceAmbiguous));
    assert_eq!(s.preview(1+1025,ctx(0)),Err(IdError::OutOfWindow));
    // Reverse jump that might also be a future generation: no guessing.
    assert_eq!(s.preview(1u32.wrapping_sub(1025),ctx(0)),Err(IdError::HalfSpaceAmbiguous));
    assert_eq!(s.preview(u32::MAX,ctx(0)),Err(IdError::Retired));
    assert_eq!(s.stats(),before);
    let accepted=s.observe_id_after_auth(100,ctx(0),10).unwrap();
    assert_eq!(accepted.id_ext,100);
    assert_eq!(s.observe_id_after_auth(99,ctx(0),11).unwrap().id_ext,99);
}
#[test]
fn r1_blockid_wrong_epoch_direction_generation_have_no_side_effects(){
    let mut s=owner(0,0);
    let mut bad=ctx(0);bad.epoch=99;
    assert_eq!(s.observe_id_after_auth(1,bad,100),Err(IdError::WrongEpoch));
    bad=ctx(0);bad.direction=Direction::ServerToClient;
    assert_eq!(s.observe_id_after_auth(1,bad,200),Err(IdError::WrongDirection));
    assert_eq!(s.observe_id_after_auth(1,ctx(1),300),Err(IdError::WrongGeneration));
    assert_eq!(s.stats().heavy,0);
    assert_eq!(s.stats().highest,0);
    let p=s.observe_id_after_auth(1,ctx(0),1).unwrap();
    assert!(p.first_seen);
    s.expire(3_000);
    assert_eq!(s.stats().heavy,1); // malformed previous frames did not move monotone clock
}
#[test]
fn r1_blockid_heavy_3s_compact_10s_absolute_no_extension(){
    let mut s=owner(0,0);
    s.observe_id_after_auth(1,ctx(0),100).unwrap();
    s.observe_id_after_auth(1,ctx(0),HEAVY_MS+90).unwrap();
    s.expire(HEAVY_MS+99);
    assert_eq!(s.stats().heavy,1);
    s.expire(HEAVY_MS+100);
    assert_eq!((s.stats().heavy,s.stats().compact),(0,1));
    s.observe_id_after_auth(1,ctx(0),HEAVY_MS+200).unwrap();
    s.expire(HEAVY_MS+COMPACT_MS+99);
    assert_eq!(s.stats().compact,1);
    s.expire(HEAVY_MS+COMPACT_MS+100);
    assert_eq!(s.stats().compact,0);
    assert_eq!(s.stats().retired_floor,1);
    assert_eq!(s.observe_id_after_auth(1,ctx(0),99_999),Err(IdError::Retired));
}
#[test]
fn r1_blockid_late_timer_callback_expires_heavy_and_compact_together(){
    let mut s=owner(0,0);
    s.observe_id_after_auth(1,ctx(0),100).unwrap();
    s.expire(100+HEAVY_MS+COMPACT_MS+5);
    assert_eq!((s.stats().heavy,s.stats().compact,s.stats().retired_floor),(0,0,1));
    assert_eq!(s.observe_id_after_auth(1,ctx(0),20_000),Err(IdError::Retired));
}
#[test]
fn r1_blockid_pressure_oldest_compaction_floor_no_resurrection(){
    let mut c=config(0,0);c.max_heavy=1;c.max_compact=1;
    let mut s=FecBlockIdOwner::new(c).unwrap();
    s.observe_id_after_auth(10,ctx(0),1).unwrap();
    s.observe_id_after_auth(20,ctx(0),2).unwrap();
    assert_eq!((s.stats().heavy,s.stats().compact),(1,1));
    assert_eq!(s.observe_id_after_auth(5,ctx(0),3),Err(IdError::Retired));
    assert_eq!(s.stats().retired_floor,10);
    assert_eq!(s.observe_id_after_auth(10,ctx(0),4),Err(IdError::Retired));
    let p=s.observe_id_after_auth(20,ctx(0),5).unwrap();
    assert!(!p.first_seen);
    assert_eq!(s.stats().distinct_accepted,2);
}
#[test]
fn r1_blockid_old_parity_wrong_generation_and_retired_floor_not_reopened(){
    let mut s=owner(0xffff_fffe,0xffff_fffd);
    s.observe_id_after_auth(0xffff_ffff,ctx(0),0).unwrap();
    s.observe_id_after_auth(1,ctx(1),1).unwrap();
    let old=ctx(0);
    assert_eq!(s.preview(1,old),Err(IdError::WrongGeneration));
    assert_eq!(s.observe_id_after_auth(1,old,2),Err(IdError::WrongGeneration));
    s.advance_retired_floor(0xffff_ffff);
    assert_eq!(s.observe_id_after_auth(0xffff_ffff,old,10),Err(IdError::Retired));
    assert_eq!(s.stats().distinct_accepted,2);
    assert_eq!(s.stats().highest,0x1_0000_0001);
}
#[test]
fn r1_blockid_real_fec_rx_first_delivery_no_duplicate_after_compact(){
    let mut tx=FecTxOwner::new(1,10000).unwrap();
    let first=tx.submit(b"ONE",0,4,128,false).unwrap().systematic.pop().unwrap();
    let second=tx.submit(b"TWO",1,4,128,false).unwrap().systematic.pop().unwrap();
    let parity=tx.flush_all(32).unwrap().parity;
    let mut scope=owner(0,0);
    let mut rx=FecRxOwner::new(RxConfig{epoch:7,
        direction:Direction::ClientToServer,max_wire:128,
        max_heavy_bytes:1000,max_heavy_blocks:4,max_compact_blocks:4,first_id_ext:1
    }).unwrap();
    let one=scope.observe_wire_after_auth(&first,128,ctx(0),10).unwrap();
    assert_eq!(rx.push_after_auth(&first,one.rx_scope(ctx(0)),10).unwrap().systematic,
        vec![(0,b"ONE".to_vec())]);
    assert!(!scope.observe_wire_after_auth(&first,128,ctx(0),11).unwrap().first_seen);
    assert!(rx.push_after_auth(&first,one.rx_scope(ctx(0)),11).unwrap().systematic.is_empty());
    let two=scope.observe_wire_after_auth(&second,128,ctx(0),12).unwrap();
    assert!(rx.push_after_auth(&second,two.rx_scope(ctx(0)),12).unwrap().systematic.len()==1);
    for p in &parity{
        let o=scope.observe_wire_after_auth(p,128,ctx(0),13).unwrap();
        assert!(rx.push_after_auth(p,o.rx_scope(ctx(0)),13).unwrap().recovered.is_empty());
    }
    scope.mark_compact(1,13);
    scope.expire(13+COMPACT_MS);
    rx.expire(13+HEAVY_MS+COMPACT_MS);
    assert_eq!(scope.observe_wire_after_auth(&first,128,ctx(0),30_000),Err(IdError::Retired));
    assert_eq!(rx.push_after_auth(&first,one.rx_scope(ctx(0)),30_000),Err(RxError::Retired));
    assert_eq!(rx.stats().systematic,2);
}
#[test]
fn r1_blockid_invalid_old_go_wire_does_not_advance_scope_or_budget(){
    let mut s=owner(0,0);
    assert!(matches!(s.observe_wire_after_auth(&[0;10],100,ctx(0),100),Err(IdError::Wire(_))));
    assert_eq!(s.stats().highest,0);
    assert_eq!(s.stats().heavy,0);
}
#[test]
fn r1_blockid_config_bounds_and_u64_exhaustion(){
    let mut c=config(0,0);c.max_forward=0;
    assert!(matches!(FecBlockIdOwner::new(c),Err(IdError::InvalidConfig)));
    c=config(0,0);c.max_forward=65_536;
    assert!(matches!(FecBlockIdOwner::new(c),Err(IdError::InvalidConfig)));
    c=config(0,0);c.max_heavy=65;
    assert!(matches!(FecBlockIdOwner::new(c),Err(IdError::InvalidConfig)));
    let mut s=owner(u64::MAX-1,u64::MAX-2);
    // The final u32::MAX is valid at the last u64 value, no reuse after it.
    assert_eq!(s.observe_id_after_auth(u32::MAX,ctx(u32::MAX),1).unwrap().id_ext,u64::MAX);
    assert_eq!(s.preview(1,ctx(u32::MAX)),Err(IdError::Exhausted));
}
