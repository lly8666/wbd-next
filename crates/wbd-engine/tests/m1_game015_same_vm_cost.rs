//! PLAN-008 M1 Game receive fixed old/new component cost fixture.
//! Only run with --ignored --exact --test-threads=1 from an M0-owned single-
//! measurement-job Action. M0 must compile this SAME fixture against both
//! immutable old/new GameRx SOURCES, verify binary SHA256, run AB/BA in one
//! runner and report host CPU, cgroup, resource and sources. This file alone
//! does NOT supply valid performance evidence or product qualification.
use std::time::Instant;
use wbd_engine::{memory::Arena,runtime::game_shared::{
    ActiveLaneSnapshot,FlowDirection,GameError,GameRx,GameScope,
    PieceProgress,QualifiedLane,RxLimits,
}};
use wbd_types::{BlockIdExt,LaneKey,LogicalPacketId,TunnelKey};
use wbd_types::buffer_contract::UniqueSealable;

#[test]
#[ignore = "M0-owned isolated paired same-VM ACTION required; ordinary worker-native is functional only"]
fn m1_game015_same_vm_game_receive_fixed_scenario(){
    const WINDOW:usize=65536;
    const INPUTS:u64=262144;
    const BLOCK_BATCH:u64=32;
    const BLOCK_PERIOD:u64=8192;
    let tunnel=TunnelKey{slot:41,generation:1};
    let scope=GameScope{tunnel,epoch:[7;16],direction:FlowDirection::Rx};
    let lanes=(1..=4).map(|slot|QualifiedLane{
        key:LaneKey{tunnel,slot,generation:1},mss:256
    }).collect();
    let snapshot=ActiveLaneSnapshot::new(scope,lanes).expect("authenticated fixture");
    let mut rx=GameRx::new(snapshot,RxLimits{
        delivered_window:WINDOW,open_blocks:64,open_bytes:128
    }).expect("valid scoped limits");
    let mut arena=Arena::new(501,128,256,1,300000).expect("bounded buffer arena");
    let mut first=0u64;
    let mut duplicate=0u64;
    let mut complete=0u64;
    let start=Instant::now();
    for seq in 0..INPUTS{
        let id=if seq>0 && seq%17==0 {seq-1} else {seq};
        let lane=LaneKey{tunnel,slot:seq as u32%4+1,generation:1};
        let mut buffer=arena.allocate().expect("returned previous loan");
        buffer.writable()[0]=(seq%251) as u8;
        match rx.first_delivery(scope,lane,LogicalPacketId(id),buffer){
            Ok(original)=>{
                assert_eq!(original.writable()[0],(seq%251) as u8);
                first+=1;
                std::hint::black_box(&original);
                drop(original);
            }
            Err((GameError::Duplicate,original))=>{
                duplicate+=1;
                drop(original);
            }
            Err((e,buffer))=>{
                drop(buffer);
                panic!("unexpected game delivery rejection: {e:?} id={id}");
            }
        }
        if seq>0 && seq%BLOCK_PERIOD==0{
            // One open set, then complete in a permutation; stresses old
            // linear scan versus indexed swap_remove without new wire/codec.
            let block_base=(seq/BLOCK_PERIOD)*BLOCK_BATCH;
            for k in 0..BLOCK_BATCH{
                let block=BlockIdExt(block_base+k);
                let buffer=arena.allocate().expect("64 bounded open slots");
                let progress=rx.offer_piece(scope,LaneKey{tunnel,slot:1,generation:1},
                    block,LogicalPacketId(seq),0,2,buffer,0..1)
                    .expect("first shard");
                assert!(matches!(progress,PieceProgress::Pending));
            }
            for k in (0..BLOCK_BATCH).rev(){
                let block=BlockIdExt(block_base+k);
                let buffer=arena.allocate().expect("bounded open slots");
                let progress=rx.offer_piece(scope,LaneKey{tunnel,slot:2,generation:1},
                    block,LogicalPacketId(seq),1,2,buffer,0..1)
                    .expect("second shard");
                let PieceProgress::Complete(block)=progress else {
                    panic!("complete 2/2 shard");
                };
                complete+=1;
                drop(block);
            }
        }
    }
    let elapsed_ns=start.elapsed().as_nanos();
    assert_eq!(first+duplicate,INPUTS);
    assert_eq!(duplicate,(INPUTS-1)/17);
    assert_eq!(rx.open_state(),(0,0));
    assert_eq!(rx.stop(),0);
    assert_eq!(arena.report().loaned,0);
    // Machine-parseable for paired Action, but wall clock by itself is NOT
    // comparable across runners/jobs or uncontrolled CI contention.
    println!("M1_GAME015_COST_RESULT window={} inputs={} first={} duplicate={} complete={} elapsed_ns={} checksum={}",
        WINDOW,INPUTS,first,duplicate,complete,elapsed_ns,
        first.wrapping_mul(31).wrapping_add(duplicate*17).wrapping_add(complete));
}
