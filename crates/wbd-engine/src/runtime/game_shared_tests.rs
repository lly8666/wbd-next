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
fn r1_game_r4_g01_one_common_job_four_lane_copies_no_source_clone(){
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
fn r1_game_r4_g01_normal_two_lane_overlap_no_game_envelope_or_duplicate(){
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
fn r1_game_r4_g02_24_arrival_orders_first_valid_delivery_once(){
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
fn r1_game_r4_g02_cross_lane_complementary_four_shards_24_orders(){
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
fn r1_game_r4_g02_recovered_then_systematic_delivers_once_and_window_stale(){
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
fn r1_game_r4_g03_slow_lane_full_does_not_block_other_lanes(){
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
fn r1_game_r4_g03_0_1_32_33_immediate_batch_and_pressure_bounded(){
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
fn r1_game_r4_g03_normal_rotation_mss_a_old_big_b_new_small(){
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
fn r1_game_r4_g04_stop_rotation_old_epoch_and_wrong_scope_fail_closed(){
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
fn r1_game_r4_g04_block_budget_duplicates_and_stop_reclaim(){
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
fn r1_game_r4_g04_parity_first_send_independent_from_repair_and_arena(){
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


#[test]
fn r1_game_r4_g03_one_lane_queue_full_three_other_lanes_immediate(){
    let mut a=arena(32);
    let mut tx=GameTx::new(snap(FlowDirection::Tx,1,&[1,2,3,4],256),
        limits(1,32)).unwrap();
    let first=tx.offer(input(&mut a,3),0..1,Mode::Game,1,None,MonoNs(0)).unwrap();
    assert_eq!(first,Some(LogicalPacketId(0)));
    // Owner has already served B,C,D while A is still backpressured.
    let mut first_fast=Vec::new();
    assert_eq!(tx.drain_ready(MonoNs(0),3,|v|{
        first_fast.push(v.lane.slot);
        DispatchOutcome::Accepted
    }),3);
    assert_eq!(first_fast,[2,3,4]);
    assert_eq!(tx.lane_queued(lane(1,1,256).key),Some((1,1)));
    // Second logical input has three available routes despite A being full.
    let second=tx.offer(input(&mut a,4),0..1,Mode::Game,1,None,MonoNs(0)).unwrap();
    assert_eq!(second,Some(LogicalPacketId(1)));
    assert_eq!(tx.counters().lane_copy_drop,1);
    assert_eq!(tx.in_use(),(2,2));
    let mut seen=Vec::new();
    while tx.drain_ready(MonoNs(0),1,|v|{
        seen.push((v.lane.slot,v.logical_id,v.common_payload[0]));
        DispatchOutcome::Accepted
    })!=0{}
    assert_eq!(seen.len(),4);
    assert_eq!(seen.iter().filter(|v|v.1==second).count(),3);
    assert_eq!(seen.iter().filter(|v|v.1==first).count(),1);
    assert_eq!(tx.counters().lane_dispatch,7);
    assert_eq!(tx.in_use(),(0,0));
    assert_eq!(a.report().loaned,0);
}
#[test]
fn r1_game_r4_g04_completed_shards_external_loan_survives_stop(){
    let mut a=arena(12);
    let mut rx=GameRx::new(snap(FlowDirection::Rx,1,&[1,2],256),
        RxLimits{delivered_window:8,open_blocks:2,open_bytes:8}).unwrap();
    let at=scope(FlowDirection::Rx,1);
    assert!(matches!(rx.offer_piece(at,lane(1,1,256).key,BlockIdExt(2),
        LogicalPacketId(3),0,2,input(&mut a,4),0..1),
        Ok(PieceProgress::Pending)));
    let finished=rx.offer_piece(at,lane(1,2,256).key,BlockIdExt(2),
        LogicalPacketId(3),1,2,input(&mut a,5),0..1).unwrap();
    let block=match finished {
        PieceProgress::Complete(b)=>b,
        PieceProgress::Pending=>panic!("quorum was reached")
    };
    assert_eq!(rx.open_state(),(0,0));
    assert_eq!(a.report().loaned,2);
    assert_eq!(rx.stop(),0);
    assert_eq!(a.report().loaned,2); // external M3 completion owns originals
    let join=std::thread::spawn(move||drop(block));
    join.join().unwrap();
    assert_eq!(a.report().loaned,0);
    let rejected=rx.offer_piece(at,lane(1,1,256).key,BlockIdExt(3),
        LogicalPacketId(4),0,1,input(&mut a,6),0..1);
    assert!(matches!(rejected,Err((GameError::Stopped,_))));
    drop(rejected);
    assert_eq!(a.report().loaned,0);
}

#[test]
fn r1_game_r5_dedup_ring_matches_old_reference_wrap_huge_gap_and_u64_max(){
    // Independent bounded old-013 oracle, deliberately only inside tests.
    struct Reference{base:u64,bits:Vec<bool>}
    impl Reference{
        fn accept(&mut self,id:u64)->Result<(),GameError>{
            if id<self.base{return Err(GameError::Stale);}
            let width=self.bits.len() as u64;
            let delta=id-self.base;
            if delta>=width {
                let shift=(delta-width+1).min(width) as usize;
                if shift>=self.bits.len(){self.bits.fill(false);}
                else {self.bits.rotate_left(shift);
                    let end=self.bits.len();self.bits[end-shift..].fill(false);}
                self.base=id-width+1;
            }
            let idx=(id-self.base) as usize;
            if self.bits[idx]{return Err(GameError::Duplicate);}
            self.bits[idx]=true;Ok(())
        }
    }
    let mut arena=arena(8);
    for width in [1,2,7,64,65,256,65536]{
        let mut rx=GameRx::new(snap(FlowDirection::Rx,1,&[1,2,3,4],256),
            RxLimits{delivered_window:width,open_blocks:2,open_bytes:16}).unwrap();
        let mut old=Reference{base:0,bits:vec![false;width]};
        let mut ids=vec![0,0,1,1,2,3,3,5,9,8,9,200,201,199,1000,1001,
            1002,1002,1003,1004,1004,90000,90001,7,100_001];
        for i in 0..300u64{
            ids.push(100_002+i);
            if i%13==0{ids.push(100_002+i);}
            if i%17==0{ids.push(i);}
        }
        ids.extend([u64::MAX-1,u64::MAX,u64::MAX,0,u64::MAX-2]);
        for (iteration,id) in ids.into_iter().enumerate(){
            let chosen=lane(1,(iteration%4+1) as u32,256).key;
            let expected=old.accept(id);
            let actual=rx.first_delivery(scope(FlowDirection::Rx,1),chosen,
                LogicalPacketId(id),input(&mut arena,(iteration%251) as u8));
            let mapped=actual.as_ref().map(|_|()).map_err(|(e,_)|*e);
            assert_eq!(mapped,expected,"width={width} id={id} at={iteration}");
            drop(actual);
            assert_eq!(rx.base,old.base);
        }
        assert_eq!(rx.stop(),0);
        assert_eq!(arena.report().loaned,0);
    }
}
#[test]
fn r1_game_r5_sequential_full_window_advancement_is_constant_word_work(){
    let mut arena=arena(8);
    let width=65536;
    let mut rx=GameRx::new(snap(FlowDirection::Rx,1,&[1],256),
        RxLimits{delivered_window:width,open_blocks:1,open_bytes:4}).unwrap();
    let before=rx.dedup_clear_word_ops;
    for id in 0..10000u64 {
        drop(rx.first_delivery(scope(FlowDirection::Rx,1),lane(1,1,256).key,
            LogicalPacketId(id),input(&mut arena,1)).unwrap());
    }
    // Fill a whole 65536 logical positions with no clearing.
    assert_eq!(rx.dedup_clear_word_ops,before);
    drop(rx.first_delivery(scope(FlowDirection::Rx,1),lane(1,1,256).key,
        LogicalPacketId(width as u64),input(&mut arena,1)).unwrap());
    assert_eq!(rx.dedup_clear_word_ops-before,1);
    for id in width as u64+1..width as u64+4097{
        drop(rx.first_delivery(scope(FlowDirection::Rx,1),lane(1,1,256).key,
            LogicalPacketId(id),input(&mut arena,1)).unwrap());
    }
    // Each sequential step clears one word; never shifts 65536 bools.
    assert!(rx.dedup_clear_word_ops-before<=4097);
    let mark=rx.dedup_clear_word_ops;
    drop(rx.first_delivery(scope(FlowDirection::Rx,1),lane(1,1,256).key,
        LogicalPacketId(9_000_000),input(&mut arena,1)).unwrap());
    assert_eq!(rx.dedup_clear_word_ops-mark,width as u64/64);
    assert_eq!(arena.report().loaned,0);
}
#[test]
fn r1_game_r5_open_index_swap_remove_pressure_and_external_loan(){
    let mut arena=arena(300);
    let mut rx=GameRx::new(snap(FlowDirection::Rx,1,&[1,2,3,4],256),
        RxLimits{delivered_window:65,open_blocks:128,open_bytes:256}).unwrap();
    let at=scope(FlowDirection::Rx,1);
    for block in 0..128u64{
        let result=rx.offer_piece(at,lane(1,1,256).key,BlockIdExt(block*5),
            LogicalPacketId(block),0,2,input(&mut arena,1),0..1);
        assert!(matches!(result,Ok(PieceProgress::Pending)));
    }
    assert_eq!(rx.open_state(),(128,128));
    assert_eq!(rx.open_index.len(),128);
    let denied=rx.offer_piece(at,lane(1,2,256).key,BlockIdExt(999),
        LogicalPacketId(999),0,1,input(&mut arena,2),0..1);
    assert!(matches!(denied,Err((GameError::Capacity,_))));
    drop(denied);
    let mut loan=None;
    // Complete in a scrambled permutation; swap_remove moves old last many times.
    for v in 0..128usize{
        let index=(v*73)%128;
        let block=BlockIdExt(index as u64*5);
        let r=rx.offer_piece(at,lane(1,2,256).key,block,
            LogicalPacketId(index as u64),1,2,input(&mut arena,2),0..1).unwrap();
        let PieceProgress::Complete(done)=r else {panic!("should complete");};
        assert_eq!(done.block,block);
        assert_eq!(done.packet,LogicalPacketId(index as u64));
        if v==1{loan=Some(done);}else{drop(done);}
        assert_eq!(rx.open.len(),rx.open_index.len());
        assert!(rx.open.iter().enumerate().all(|(i,b)|
            rx.open_index.get(&b.block)==Some(&i)));
    }
    assert_eq!(rx.open_state(),(0,0));
    assert_eq!(rx.stop(),0);
    assert!(rx.open_index.is_empty());
    assert_eq!(arena.report().loaned,2);
    drop(loan);
    assert_eq!(arena.report().loaned,0);
}


/// Component-only, paced Game fan-out/load probe. NOT a UDP/TLS/FEC/network
/// benchmark and never a per-lane physical throughput or product qualification.
/// M1 exercises only existing public GameTx/Arena/GameRx with real 256/1200B
/// payload writes, per-lane owned copies, complete byte verification, and a
/// deterministic 25 Mbps/lane offered payload schedule (1ms batches).
/// Raw numbers are DEBUG-profile worker-native CI observations, not release CPU.
fn game_r5_read_u64(path:&str,key:&str)->Option<u64>{
    let data=std::fs::read_to_string(path).ok()?;
    data.lines().find_map(|line|{
        let mut parts=line.split_whitespace();
        (parts.next()?==key).then(||parts.next()?.parse().ok()).flatten()
    })
}
fn game_r5_sched_cpu_ns()->Option<u64>{
    std::fs::read_to_string("/proc/self/schedstat").ok()?
        .split_whitespace().next()?.parse().ok()
}
fn game_r5_proc_status_kib(key:&str)->Option<u64>{
    game_r5_read_u64("/proc/self/status",key)
}
fn game_r5_p99_ns(v:&mut [u64])->u64{
    v.sort_unstable();
    let rank=(v.len()*99).div_ceil(100);
    v[rank.saturating_sub(1)]
}
fn game_r5_lane25m_case(nlanes:usize,payload:usize){
    use std::time::{Duration,Instant};
    const RATE_BPS_PER_LANE:u64=25_000_000;
    const DURATION_MS:u64=2_000;
    assert!(nlanes==1||nlanes==4);
    assert!(payload==256||payload==1200);
    let per_tick_bits=RATE_BPS_PER_LANE/1000;
    let bits_per_packet=(payload*8) as u64;
    let lane_ids:Vec<u32>=(1..=nlanes as u32).collect();
    let tx_scope=scope(FlowDirection::Tx,1);
    let rx_scope=scope(FlowDirection::Rx,1);
    let mut tx=GameTx::new(snap(FlowDirection::Tx,1,&lane_ids,payload),
        GameLimits{
            jobs:64,logical_bytes:64*payload,
            lane_slots:64,lane_bytes:64*payload,
            max_age_ns:1_000_000_000,
        }).expect("bounded GameTx");
    let mut rx=GameRx::new(snap(FlowDirection::Rx,1,&lane_ids,payload),
        RxLimits{delivered_window:65536,open_blocks:64,open_bytes:payload*64})
        .expect("bounded GameRx");
    let class=if payload<=256{256}else{1536};
    let mut tx_arena=Arena::new(701,64,class,64,500_000).expect("bounded Tx arena");
    let mut rx_arena=Arena::new(702,64,class,64,500_000).expect("bounded Rx arena");
    let mut lane_bytes=[0u64;4];
    let mut packets=0u64;
    let mut first=0u64;
    let mut duplicate=0u64;
    let mut byte_sum=0u64;
    let mut delays=Vec::with_capacity((DURATION_MS*per_tick_bits/bits_per_packet) as usize);
    let mut tardy_ticks=0u64;
    let mut max_lateness_us=0u64;
    let cpu_before=game_r5_sched_cpu_ns();
    let rss_before=game_r5_proc_status_kib("VmRSS:");
    let hwm_before=game_r5_proc_status_kib("VmHWM:");
    let cgroup_mem_before=game_r5_read_u64("/sys/fs/cgroup/memory.stat","anon");
    let cgroup_throttle_before=game_r5_read_u64("/sys/fs/cgroup/cpu.stat","nr_throttled");
    let cgroup_throttled_us_before=game_r5_read_u64("/sys/fs/cgroup/cpu.stat","throttled_usec");
    let start=Instant::now();
    for tick in 0..DURATION_MS {
        let release=start+Duration::from_millis(tick);
        let now=Instant::now();
        if now<release{std::thread::sleep(release-now);}
        let late=Instant::now().saturating_duration_since(release);
        if late>=Duration::from_millis(1){tardy_ticks+=1;}
        max_lateness_us=max_lateness_us.max(late.as_micros() as u64);
        // Exactly 25 Mbps offered per lane in 1ms batches; Game mode fans out
        // one logical payload to all lanes. 4 lanes = 100 Mbps copied payload.
        let target=((tick+1)*per_tick_bits)/bits_per_packet;
        while packets<target {
            let begin=Instant::now();
            let mut source=tx_arena.allocate().expect("available Tx slab");
            let bytes=&mut source.writable()[..payload];
            let mut expected_sum=0u64;
            for (i,b) in bytes.iter_mut().enumerate(){
                *b=(packets.wrapping_mul(17).wrapping_add((i as u64)*3)%251) as u8;
                expected_sum+=*b as u64;
            }
            let id=tx.offer(source,0..payload,Mode::Game,payload,None,
                MonoNs(tick*1_000_000)).expect("Game offer")
                .expect("Game must assign packet ID");
            assert_eq!(id,LogicalPacketId(packets));
            let emitted=tx.drain_ready(MonoNs(tick*1_000_000),32,|view|{
                assert_eq!(view.mode,Mode::Game);
                assert_eq!(view.logical_id,Some(id));
                assert_eq!(view.scope,tx_scope);
                assert_eq!(view.common_payload.len(),payload);
                let slot=(view.lane.slot-1) as usize;
                assert!(slot<nlanes);
                let mut copy=rx_arena.allocate().expect("bounded per-lane Rx copy");
                copy.writable()[..payload].copy_from_slice(view.common_payload);
                let sum:u64=copy.writable()[..payload].iter().map(|&b|b as u64).sum();
                assert_eq!(sum,expected_sum,"payload bytes altered");
                byte_sum=byte_sum.wrapping_add(sum);
                lane_bytes[slot]+=payload as u64;
                match rx.first_delivery(rx_scope,view.lane,id,copy){
                    Ok(first_buffer)=>{first+=1;drop(first_buffer);}
                    Err((GameError::Duplicate,duplicate_buffer))=>{
                        duplicate+=1;drop(duplicate_buffer);
                    }
                    Err((error,buffer))=>{
                        drop(buffer);
                        panic!("Game RX unexpected error: {error:?}");
                    }
                }
                DispatchOutcome::Accepted
            });
            assert_eq!(emitted,nlanes,"each qualified Game lane must dispatch");
            assert_eq!(tx.in_use(),(0,0));
            packets+=1;
            delays.push(begin.elapsed().as_nanos() as u64);
        }
    }
    let deadline=start+Duration::from_millis(DURATION_MS);
    let now=Instant::now();
    if now<deadline{std::thread::sleep(deadline-now);}
    let wall_ns=start.elapsed().as_nanos() as u64;
    let cpu_after=game_r5_sched_cpu_ns();
    let rss_after=game_r5_proc_status_kib("VmRSS:");
    let hwm_after=game_r5_proc_status_kib("VmHWM:");
    let cgroup_mem_after=game_r5_read_u64("/sys/fs/cgroup/memory.stat","anon");
    let cgroup_throttle_after=game_r5_read_u64("/sys/fs/cgroup/cpu.stat","nr_throttled");
    let cgroup_throttled_us_after=game_r5_read_u64("/sys/fs/cgroup/cpu.stat","throttled_usec");
    let expected_packets=DURATION_MS*per_tick_bits/bits_per_packet;
    assert_eq!(packets,expected_packets,"offered rate schedule");
    assert_eq!(first,packets,"only first logical Game payload delivered");
    assert_eq!(duplicate,packets*(nlanes as u64-1),"cross-lane duplicate copies");
    let tx_counts=tx.counters();
    assert_eq!(tx_counts.logical_jobs,packets);
    assert_eq!(tx_counts.lane_dispatch,packets*nlanes as u64);
    assert_eq!(tx_counts.lane_copy_drop,0);
    assert_eq!(tx_counts.common_bytes,packets*payload as u64);
    assert!(lane_bytes[..nlanes].iter().all(|&v|v==packets*payload as u64));
    assert_eq!(tx.in_use(),(0,0));
    assert_eq!(rx.open_state(),(0,0));
    assert_eq!(tx.stop(),0);
    assert_eq!(rx.stop(),0);
    assert_eq!(tx_arena.report().loaned,0);
    assert_eq!(rx_arena.report().loaned,0);
    let p99_ns=game_r5_p99_ns(&mut delays);
    let p50_ns=delays[delays.len()/2];
    let good_bytes=packets*payload as u64;
    let emitted_bytes=good_bytes*nlanes as u64;
    let measured_mbps=(emitted_bytes as f64)*8_000.0/(wall_ns as f64);
    let cpu_ns=cpu_after.and_then(|after|cpu_before.and_then(|before|after.checked_sub(before)));
    let cpu_percent=cpu_ns.map(|n|n as f64*100.0/wall_ns as f64);
    let max_slot_bytes=lane_bytes[..nlanes].iter().copied().max().unwrap_or(0);
    // Printed by worker-native with --nocapture. Inspect this line; cargo
    // PASS only asserts correctness, not that the host achieved rate/capacity.
    println!("M1_GAME_LANE25_PROFILE profile=debug mode=Game lanes={nlanes} payload_bytes={payload} target_per_lane_mbps=25 target_aggregate_mbps={} wall_ns={wall_ns} offered_packets={packets} unique_rx={first} duplicate_rx={duplicate} copies={} actual_aggregate_mbps={measured_mbps:.5} per_lane_mbps={:.5} p50_processing_ns={p50_ns} p99_processing_ns={p99_ns} cpu_ns={} cpu_percent={} cpu_ns_per_logical={} tx_bytes={good_bytes} lane_payload_bytes={max_slot_bytes} total_copied_bytes={emitted_bytes} copied_byte_checksum={byte_sum} lane_copy_drop={} tardy_ticks={tardy_ticks} max_tick_lateness_us={max_lateness_us} rss_before_kib={} rss_after_kib={} hwm_before_kib={} hwm_after_kib={} cgroup_anon_before={} cgroup_anon_after={} nr_throttled_delta={} throttled_us_delta={} host_capacity_25m_met={} network=NOT_RUN tls=NOT_RUN fec=NOT_RUN release=NOT_RUN",
        nlanes*25,
        packets*nlanes as u64,
        measured_mbps/nlanes as f64,
        cpu_ns.map_or_else(||"NOT_RUN".into(),|v|v.to_string()),
        cpu_percent.map_or_else(||"NOT_RUN".into(),|v|format!("{v:.4}")),
        cpu_ns.map_or_else(||"NOT_RUN".into(),|v|format!("{:.4}",v as f64/packets as f64)),
        tx_counts.lane_copy_drop,
        rss_before.map_or_else(||"NOT_RUN".into(),|v|v.to_string()),
        rss_after.map_or_else(||"NOT_RUN".into(),|v|v.to_string()),
        hwm_before.map_or_else(||"NOT_RUN".into(),|v|v.to_string()),
        hwm_after.map_or_else(||"NOT_RUN".into(),|v|v.to_string()),
        cgroup_mem_before.map_or_else(||"NOT_RUN".into(),|v|v.to_string()),
        cgroup_mem_after.map_or_else(||"NOT_RUN".into(),|v|v.to_string()),
        cgroup_throttle_after.and_then(|v|cgroup_throttle_before.and_then(|w|v.checked_sub(w)))
            .map_or_else(||"NOT_RUN".into(),|v|v.to_string()),
        cgroup_throttled_us_after.and_then(|v|cgroup_throttled_us_before.and_then(|w|v.checked_sub(w)))
            .map_or_else(||"NOT_RUN".into(),|v|v.to_string()),
        measured_mbps>=nlanes as f64*25.0*0.95);
}
#[test]
fn r1_game_r5_25mbps_per_lane_one_and_four_256_and_1200_byte_profile(){
    // Sequential profiles share process and debug build; no clean-room
    // independent RSS claim. This observes bounded owner overhead at target,
    // not one NIC, not 25 Mbps of unique bytes for four replicated lanes.
    for payload in [256usize,1200]{
        for nlanes in [1usize,4]{
            game_r5_lane25m_case(nlanes,payload);
        }
    }
}
