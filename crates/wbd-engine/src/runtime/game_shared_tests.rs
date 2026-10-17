//! Scoped R4-M1-PACK-013 counterexamples; all fake admitted/decoded facts
//! supplied by M0-shaped caller. No TLS, AEAD, FEC decoder or driver.
use super::*;
use crate::{memory::Arena,runtime::{TxOwner,TxKind,QueueLimits}};
use wbd_types::{BufferKey};
use wbd_types::buffer_contract::{FrozenMetadata,UniqueSealable,FrozenRecordHandle};
fn scope(direction:FlowDirection,gen:u32)->GameScope{
    GameScope{tunnel:TunnelKey{slot:41,generation:gen},epoch:[7;16],direction}
}
fn lane(gen:u32,slot:u32,mss:usize)->QualifiedLane{
    QualifiedLane{key:LaneKey{tunnel:TunnelKey{slot:41,generation:gen},
        slot,generation:gen},mss}
}
fn snap(dir:FlowDirection,gen:u32,ids:&[u32],mss:usize)->ActiveLaneSnapshot{
    ActiveLaneSnapshot::new(scope(dir,gen),
        ids.iter().copied().map(|i|lane(gen,i,mss)).collect()).unwrap()
}
fn limits(slots:usize,bytes:usize)->GameLimits{
    GameLimits{jobs:128,logical_bytes:bytes,lane_slots:slots,
        lane_bytes:bytes,max_age_ns:1_000_000}
}
fn arena(count:usize)->Arena{Arena::new(301,count,256,1,300_000).unwrap()}
fn input(a:&mut Arena,tag:u8)->UniqueBuffer{
    let mut u=a.allocate().unwrap();u.writable()[0]=tag;u
}
fn dispatch_all(tx:&mut GameTx)->Vec<(u32,Option<LogicalPacketId>,u8)>{
    let mut out=Vec::new();
    loop{
        let n=tx.drain_ready(MonoNs(0),32,|v|{
            out.push((v.lane.slot,v.logical_id,v.common_payload[0]));
            DispatchOutcome::Accepted
        });
        if n==0{break;}
    }
    out
}
fn permutations(items:&mut [usize;4],at:usize,out:&mut Vec<[usize;4]>){
    if at==items.len(){out.push(*items);return;}
    for i in at..items.len(){
        items.swap(i,at);
        permutations(items,at+1,out);
        items.swap(i,at);
    }
}
#[test]
fn r4_game_g01_one_common_job_four_lane_copies_no_source_clone(){
    let mut a=arena(32);let mut tx=GameTx::new(snap(FlowDirection::Tx,1,&[4,1,3,2],256),
        limits(32,1024)).unwrap();
    let original=input(&mut a,51);
    let source=original.origin();
    let id=tx.offer(original,0..1,Mode::Game,2,Some(BlockIdExt(9)),MonoNs(0)).unwrap();
    assert_eq!(id,Some(LogicalPacketId(0)));
    assert_eq!(tx.in_use(),(1,1));
    assert_eq!(a.report().loaned,1);
    let mut ptrs=Vec::new();let mut lanes=Vec::new();
    for _ in 0..4{
        assert_eq!(tx.drain_ready(MonoNs(0),1,|v|{
            assert_eq!(v.logical_id,id);
            assert_eq!(v.block,Some(BlockIdExt(9)));
            lanes.push(v.lane.slot);ptrs.push(v.common_payload.as_ptr() as usize);
            DispatchOutcome::Accepted
        }),1);
    }
    assert_eq!(lanes.len(),4);
    lanes.sort_unstable();assert_eq!(lanes,[1,2,3,4]);
    assert!(ptrs.iter().all(|&x|x==ptrs[0]));
    assert_eq!(tx.counters().common_bytes,1);
    assert_eq!(tx.counters().lane_dispatch,4);
    assert_eq!(tx.in_use(),(0,0));
    assert_eq!(a.report().loaned,0);
    let _=source;
}
#[test]
fn r4_game_g01_normal_two_lane_overlap_no_game_envelope_or_duplicate(){
    let mut a=arena(24);let mut tx=GameTx::new(snap(FlowDirection::Tx,1,&[1,2],128),
        limits(8,128)).unwrap();
    for i in 0..8u8 {
        assert!(matches!(tx.offer(input(&mut a,i),0..1,Mode::Normal,1,None,MonoNs(0)),
            Ok(None)));
    }
    let v=dispatch_all(&mut tx);
    assert_eq!(v.len(),8);
    assert!(v.iter().all(|v|v.1.is_none()));
    assert_eq!(v.iter().filter(|x|x.0==1).count(),4);
    assert_eq!(v.iter().filter(|x|x.0==2).count(),4);
    assert_eq!(tx.next_packet(),Some(LogicalPacketId(0)));
    assert_eq!(tx.counters().lane_dispatch,8);
    assert_eq!(a.report().loaned,0);
}
#[test]
fn r4_game_g02_24_arrival_orders_first_valid_delivery_once(){
    let mut a=arena(128);
    let mut perms=Vec::new();permutations(&mut [0,1,2,3],0,&mut perms);
    assert_eq!(perms.len(),24);
    for (iteration,order) in perms.iter().enumerate(){
        let mut rx=GameRx::new(snap(FlowDirection::Rx,1,&[1,2,3,4],256),
            RxLimits{delivered_window:64,open_blocks:4,open_bytes:64}).unwrap();
        let mut accepted=0;
        for &i in order {
            let payload=input(&mut a,iteration as u8);
            let v=rx.first_delivery(scope(FlowDirection::Rx,1),lane(1,(i+1) as u32,256).key,
                LogicalPacketId(9),payload);
            if accepted==0 {
                let original=v.unwrap();
                let mut original=original;
                assert_eq!(original.writable()[0],iteration as u8);
                drop(original);accepted+=1;
            }else{
                assert!(matches!(v,Err((GameError::Duplicate,_))));
                drop(v);
            }
        }
        assert_eq!(accepted,1);
    }
    assert_eq!(a.report().loaned,0);
}
#[test]
fn r4_game_g02_cross_lane_complementary_four_shards_24_orders(){
    let mut a=arena(128);let mut orders=Vec::new();
    permutations(&mut [0,1,2,3],0,&mut orders);
    for order in orders {
        let mut rx=GameRx::new(snap(FlowDirection::Rx,1,&[1,2,3,4],256),
            RxLimits{delivered_window:64,open_blocks:2,open_bytes:8}).unwrap();
        for (step,&i) in order.iter().enumerate(){
            let result=rx.offer_piece(scope(FlowDirection::Rx,1),
                lane(1,(i+1) as u32,256).key,BlockIdExt(19),
                LogicalPacketId(9),i as u8,4,input(&mut a,i as u8),0..1).unwrap();
            if step<3{assert!(matches!(result,PieceProgress::Pending));}
            else if let PieceProgress::Complete(block)=result{
                assert_eq!(block.block,BlockIdExt(19));
                assert_eq!(block.packet,LogicalPacketId(9));
                assert_eq!(block.pieces.iter().filter(|p|p.is_some()).count(),4);
                for (index,p) in block.pieces.iter().enumerate(){
                    assert_eq!(p.as_ref().unwrap().wire,0..1);
                    assert_eq!(p.as_ref().unwrap().lane.slot,(index+1) as u32);
                }
                drop(block);
            }else{panic!("fourth shard must hand off to decoder");}
        }
        assert_eq!(rx.open_state(),(0,0));
        assert_eq!(a.report().loaned,0);
    }
}
#[test]
fn r4_game_g02_recovered_then_systematic_delivers_once_and_window_stale(){
    let mut a=arena(24);
    let mut rx=GameRx::new(snap(FlowDirection::Rx,1,&[1,2],256),
        RxLimits{delivered_window:8,open_blocks:2,open_bytes:4}).unwrap();
    // M3 recovered candidate can arrive before source; the same logical ID
    // is delivered once even across different authenticated lanes.
    drop(rx.first_delivery(scope(FlowDirection::Rx,1),lane(1,2,256).key,
        LogicalPacketId(4),input(&mut a,4)).unwrap());
    let duplicate=rx.first_delivery(scope(FlowDirection::Rx,1),lane(1,1,256).key,
        LogicalPacketId(4),input(&mut a,4));
    assert!(matches!(duplicate,Err((GameError::Duplicate,_))));drop(duplicate);
    drop(rx.first_delivery(scope(FlowDirection::Rx,1),lane(1,1,256).key,
        LogicalPacketId(20),input(&mut a,20)).unwrap());
    let late=rx.first_delivery(scope(FlowDirection::Rx,1),lane(1,2,256).key,
        LogicalPacketId(4),input(&mut a,4));
    assert!(matches!(late,Err((GameError::Stale,_))));drop(late);
    assert_eq!(a.report().loaned,0);
}
#[test]
fn r4_game_g03_slow_lane_full_does_not_block_other_lanes(){
    let mut a=arena(60);let mut tx=GameTx::new(snap(FlowDirection::Tx,1,&[1,2,3,4],256),
        limits(2,120)).unwrap();
    for i in 0..2u8{
        tx.offer(input(&mut a,i),0..1,Mode::Game,1,None,MonoNs(0)).unwrap();
    }
    // A slow lane's callbacks reject its copies, but ready service of all
    // others must proceed without ever waiting for this lane's driver.
    let mut sent=Vec::new();let mut pressure=0;
    while tx.drain_ready(MonoNs(0),1,|v|{
        if v.lane.slot==1 {
            pressure+=1;DispatchOutcome::PressureDrop
        }else{
            sent.push((v.lane.slot,v.common_payload[0]));
            DispatchOutcome::Accepted
        }
    })!=0{}
    assert_eq!(pressure,2);
    assert_eq!(sent.len(),6);
    assert!(sent.iter().any(|v|v.0==4));
    assert_eq!(tx.counters().lane_copy_drop,2);
    assert_eq!(tx.in_use(),(0,0));
    assert_eq!(a.report().loaned,0);
}
#[test]
fn r4_game_g03_0_1_32_33_immediate_batch_and_pressure_bounded(){
    let mut a=arena(100);let mut tx=GameTx::new(snap(FlowDirection::Tx,1,&[1],256),
        limits(64,128)).unwrap();
    assert_eq!(tx.drain_ready(MonoNs(0),32,|_|DispatchOutcome::Accepted),0);
    for i in 0..33u8{
        tx.offer(input(&mut a,i),0..1,Mode::Normal,1,None,MonoNs(0)).unwrap();
    }
    assert_eq!(tx.drain_ready(MonoNs(0),32,|_|DispatchOutcome::Accepted),32);
    assert_eq!(tx.drain_ready(MonoNs(0),32,|_|DispatchOutcome::Accepted),1);
    assert_eq!(tx.in_use(),(0,0));
    let mut narrow=GameTx::new(snap(FlowDirection::Tx,1,&[1,2,3,4],256),
        limits(1,8)).unwrap();
    narrow.offer(input(&mut a,1),0..1,Mode::Game,1,None,MonoNs(0)).unwrap();
    let refusal=narrow.offer(input(&mut a,2),0..1,Mode::Game,1,None,MonoNs(0));
    assert!(matches!(refusal,Err((GameError::NoLane,_))));drop(refusal);
    assert_eq!(narrow.counters().lane_copy_drop,4);
    assert_eq!(narrow.in_use(),(1,1));
    assert_eq!(narrow.stop(),4);
    assert_eq!(narrow.stop(),4);
    assert_eq!(a.report().loaned,0);
}
#[test]
fn r4_game_g03_normal_rotation_mss_a_old_big_b_new_small(){
    let mut a=arena(20);
    let mut tx=GameTx::new(snap(FlowDirection::Tx,1,&[1],200),
        limits(8,128)).unwrap();
    tx.offer(input(&mut a,1),0..8,Mode::Normal,120,None,MonoNs(0)).unwrap();
    tx.rotate(ActiveLaneSnapshot::new(scope(FlowDirection::Tx,1),
        vec![lane(1,1,200),lane(1,2,60)]).unwrap()).unwrap();
    tx.offer(input(&mut a,2),0..1,Mode::Normal,40,None,MonoNs(0)).unwrap();
    // The old queued bigger frame MUST NOT be rebound to B.
    let mut seen=Vec::new();
    while tx.drain_ready(MonoNs(0),1,|v|{
        seen.push((v.lane.slot,v.common_payload[0]));
        DispatchOutcome::Accepted
    })!=0{}
    assert_eq!(seen.len(),2);
    assert!(seen.contains(&(1,1)));
    assert!(seen.contains(&(2,2)));
    assert_eq!(a.report().loaned,0);
}
#[test]
fn r4_game_g04_stop_rotation_old_epoch_and_wrong_scope_fail_closed(){
    let mut a=arena(20);
    let mut tx=GameTx::new(snap(FlowDirection::Tx,1,&[1,2],200),
        limits(8,128)).unwrap();
    let scope_old=scope(FlowDirection::Tx,1);
    tx.offer(input(&mut a,1),0..1,Mode::Game,1,Some(BlockIdExt(10)),MonoNs(0)).unwrap();
    let invalid=tx.rotate(snap(FlowDirection::Tx,2,&[1],100));
    assert_eq!(invalid,Err(GameError::Scope));
    assert_eq!(tx.in_use(),(1,1));
    let already=tx.drain_ready(MonoNs(0),1,|_|DispatchOutcome::Accepted);
    assert_eq!(already,1);
    assert_eq!(tx.stop(),1);
    assert_eq!(tx.stop(),1);
    assert_eq!(a.report().loaned,0);
    let new=GameTx::new(snap(FlowDirection::Tx,2,&[1],100),
        limits(8,128)).unwrap();
    assert_ne!(scope_old,new.scope());
    let mut rx=GameRx::new(snap(FlowDirection::Rx,2,&[1],100),
        RxLimits{delivered_window:8,open_blocks:2,open_bytes:8}).unwrap();
    let wrong=rx.first_delivery(scope(FlowDirection::Rx,1),lane(2,1,100).key,
        LogicalPacketId(1),input(&mut a,2));
    assert!(matches!(wrong,Err((GameError::Scope,_))));drop(wrong);
    assert_eq!(a.report().loaned,0);
}
#[test]
fn r4_game_g04_block_budget_duplicates_and_stop_reclaim(){
    let mut a=arena(20);
    let mut rx=GameRx::new(snap(FlowDirection::Rx,1,&[1,2],100),
        RxLimits{delivered_window:4,open_blocks:1,open_bytes:2}).unwrap();
    assert!(matches!(rx.offer_piece(scope(FlowDirection::Rx,1),lane(1,1,100).key,
        BlockIdExt(1),LogicalPacketId(1),0,2,
        input(&mut a,1),0..1),Ok(PieceProgress::Pending)));
    let duplicate=rx.offer_piece(scope(FlowDirection::Rx,1),lane(1,2,100).key,
        BlockIdExt(1),LogicalPacketId(1),0,2,input(&mut a,2),0..1);
    assert!(matches!(duplicate,Err((GameError::Duplicate,_))));drop(duplicate);
    let full=rx.offer_piece(scope(FlowDirection::Rx,1),lane(1,1,100).key,
        BlockIdExt(2),LogicalPacketId(2),0,2,input(&mut a,2),0..1);
    assert!(matches!(full,Err((GameError::Capacity,_))));drop(full);
    assert_eq!(rx.open_state(),(1,1));
    assert_eq!(rx.stop(),1);
    assert_eq!(rx.stop(),0);
    assert_eq!(a.report().loaned,0);
}
#[test]
fn r4_game_g04_parity_first_send_independent_from_repair_and_arena(){
    let mut a=arena(16);
    let lim=QueueLimits{slots:16,bytes:16,max_age_ns:1_000_000};
    let mut tx=TxOwner::with_parity_share(lim,lim,lim,4,4).unwrap();
    for i in 0..4u8 {
        let mut u=input(&mut a,i);
        let metadata=FrozenMetadata{lane:lane(1,1,256).key,
            pn:wbd_types::RecordPn(i as u64),
            seq:wbd_types::SeqOffset(i as u64),carrier_snapshot:1};
        u.writable()[0]=i;
        tx.offer_fresh(u.freeze(0..1,metadata).unwrap(),MonoNs(0)).unwrap();
    }
    let mut p=input(&mut a,5);
    p.writable()[0]=5;
    let metadata=FrozenMetadata{lane:lane(1,1,256).key,
        pn:wbd_types::RecordPn(5),seq:wbd_types::SeqOffset(5),
        carrier_snapshot:1};
    tx.offer_parity(p.freeze(0..1,metadata).unwrap(),MonoNs(0),MonoNs(0)).unwrap();
    let first=tx.next_ready(MonoNs(0)).unwrap();
    assert_eq!(first.kind,TxKind::Fresh);drop(first);
    let second=tx.next_ready(MonoNs(0)).unwrap();
    assert_eq!(second.kind,TxKind::Parity);drop(second);
    assert_eq!(tx.queued().1,0);
    tx.stop();
    assert_eq!(a.report().loaned,0);
}
