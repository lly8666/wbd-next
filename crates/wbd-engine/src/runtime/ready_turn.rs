//! R1-M1-OWNER-MEMORY-READY-WORKPACK-011 owner-only ready turn.
//! The caller retains original TX frozen and RX unique leases until driver
//! completion, and owns the two Vecs. This is NOT a real fd worker loop,
//! clock source, system-call dispatcher, or authenticated data path.
#![forbid(unsafe_code)]
use wbd_types::MonoNs;
use super::{TxOwner,RxOwner,TxDispatch,RxPacket};
pub const TURN_BUDGET_NS:u64=100_000;
pub const PER_CLASS_MAX:usize=32;
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub enum Side{Tx,Rx}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct TurnResult {
    pub tx:usize,pub rx:usize,pub yielded_for_budget:bool,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct TurnStats{pub turns:u64,pub tx_items:u64,pub rx_items:u64,pub budget_yields:u64}
/// Single-threaded owner turn, no per-packet Arc, Vec or dynamic clock read.
/// A turn starts on the opposite side from the previous one even when one
/// class was full. Clock is sampled at start and after one complete class;
/// the 100us budget is a cooperative yield, not a hard preemption guarantee.
pub struct ReadyTurn {first:Side,stats:TurnStats}
impl ReadyTurn {
    pub fn new()->Self{
        Self{first:Side::Rx,stats:TurnStats{
            turns:0,tx_items:0,rx_items:0,budget_yields:0
        }}
    }
    pub fn next_first(&self)->Side{self.first}
    /// Low-frequency snapshot: caller chooses cadence (e.g. every 1024
    /// turns); no instrumentation or Atomics per packet.
    pub fn snapshot(&self)->TurnStats{self.stats}
    pub fn run<C:FnMut()->MonoNs>(&mut self,tx:&mut TxOwner,rx:&mut RxOwner,
        at:MonoNs,mut now:C,tx_out:&mut Vec<TxDispatch>,
        rx_out:&mut Vec<RxPacket>)->TurnResult{
        let begin=now();
        let first=self.first;
        self.first=match first{Side::Rx=>Side::Tx,Side::Tx=>Side::Rx};
        let mut result=TurnResult{tx:0,rx:0,yielded_for_budget:false};
        for step in 0..2{
            if step==1&&now().elapsed_since(begin)>=TURN_BUDGET_NS {
                result.yielded_for_budget=true;break;
            }
            let side=if step==0{first}else{self.first};
            match side{
                Side::Tx=>result.tx=tx.drain_ready_batch(at,tx_out),
                Side::Rx=>result.rx=rx.drain_ready_batch(at,rx_out),
            }
        }
        self.stats.turns=self.stats.turns.saturating_add(1);
        self.stats.tx_items=self.stats.tx_items.saturating_add(result.tx as u64);
        self.stats.rx_items=self.stats.rx_items.saturating_add(result.rx as u64);
        if result.yielded_for_budget{
            self.stats.budget_yields=self.stats.budget_yields.saturating_add(1);
        }
        result
    }
}
impl Default for ReadyTurn{fn default()->Self{Self::new()}}
#[cfg(test)]
mod tests {
    use super::*;
    use crate::memory::{Arena,FrozenRecord,UniqueBuffer};
    use super::super::QueueLimits;
    use wbd_types::{LaneKey,TunnelKey,RecordPn,SeqOffset};
    use wbd_types::buffer_contract::{UniqueSealable,FrozenMetadata,FrozenRecordHandle};
    fn bounds()->QueueLimits{QueueLimits{slots:64,bytes:64,max_age_ns:1000000}}
    fn owners()->(TxOwner,RxOwner){
        (TxOwner::new(bounds(),bounds()).unwrap(),RxOwner::new(bounds()).unwrap())
    }
    fn a()->Arena{Arena::new(222,144,256,1,100000).unwrap()}
    fn frozen(a:&mut Arena,v:u8)->FrozenRecord{
        let mut b=a.allocate().unwrap();b.writable()[0]=v;
        b.freeze(0..1,FrozenMetadata{
            lane:LaneKey{tunnel:TunnelKey{slot:8,generation:1},slot:1,generation:1},
            pn:RecordPn(v as u64),seq:SeqOffset(v as u64),
            carrier_snapshot:1
        }).unwrap()
    }
    fn input(a:&mut Arena,v:u8)->UniqueBuffer{
        let mut b=a.allocate().unwrap();b.writable()[0]=v;b
    }
    #[test]
    fn r1_workpack_ready_r01_b01_zero_one_32_33_immediate_prealloc() {
        let mut a=a();let(mut tx,mut rx)=owners();let mut turn=ReadyTurn::new();
        let mut tv=Vec::with_capacity(32);
        let mut rv=Vec::with_capacity(32);
        let tp=tv.as_ptr();let rp=rv.as_ptr();
        let empty=turn.run(&mut tx,&mut rx,MonoNs(0),||MonoNs(0),&mut tv,&mut rv);
        assert_eq!((empty.tx,empty.rx),(0,0));
        tx.offer_fresh(frozen(&mut a,1),MonoNs(0)).unwrap();
        rx.offer(input(&mut a,1),0..1,MonoNs(0)).unwrap();
        let one=turn.run(&mut tx,&mut rx,MonoNs(0),||MonoNs(0),&mut tv,&mut rv);
        assert_eq!((one.tx,one.rx),(1,1));
        assert_eq!(tv.as_ptr(),tp);assert_eq!(rv.as_ptr(),rp);
        tv.clear();rv.clear();
        for i in 0..33u8 {
            tx.offer_fresh(frozen(&mut a,i),MonoNs(0)).unwrap();
            rx.offer(input(&mut a,i),0..1,MonoNs(0)).unwrap();
        }
        let thirty_two=turn.run(&mut tx,&mut rx,MonoNs(0),||MonoNs(0),&mut tv,&mut rv);
        assert_eq!((thirty_two.tx,thirty_two.rx),(32,32));
        assert_eq!(tx.queued().0,1);assert_eq!(rx.queued(),1);
        tv.clear();rv.clear();
        let tail=turn.run(&mut tx,&mut rx,MonoNs(0),||MonoNs(0),&mut tv,&mut rv);
        assert_eq!((tail.tx,tail.rx),(1,1));
        assert_eq!(tv[0].record.bytes(),&[32]);
        assert_eq!(rv[0].wire,0..1);
        drop(tv);drop(rv);
        assert_eq!(a.report().loaned,0);
    }
    #[test]
    fn r1_workpack_ready_r02_budget_yield_alternates_no_rx_hol() {
        let mut a=a();let(mut tx,mut rx)=owners();let mut turn=ReadyTurn::new();
        for i in 0..32u8 {
            rx.offer(input(&mut a,i),0..1,MonoNs(0)).unwrap();
            tx.offer_fresh(frozen(&mut a,i),MonoNs(0)).unwrap();
        }
        let(mut tv,mut rv)=(Vec::with_capacity(32),Vec::with_capacity(32));
        let mut checks=0;
        let first=turn.run(&mut tx,&mut rx,MonoNs(0),||{
            checks+=1;MonoNs(if checks==1{0}else{100_001})
        },&mut tv,&mut rv);
        assert_eq!((first.rx,first.tx,first.yielded_for_budget),(32,0,true));
        assert_eq!(turn.next_first(),Side::Tx);
        tv.clear();rv.clear();
        let second=turn.run(&mut tx,&mut rx,MonoNs(0),||MonoNs(0),&mut tv,&mut rv);
        assert_eq!((second.tx,second.rx),(32,0));
        assert_eq!(turn.snapshot().budget_yields,1);
        assert_eq!(turn.snapshot().turns,2);
        assert_eq!((turn.snapshot().tx_items,turn.snapshot().rx_items),(32,32));
        drop(tv);drop(rv);
        assert_eq!(a.report().loaned,0);
    }
    #[test]
    fn r1_workpack_ready_g01_blocked_lane_skipped_without_loss_of_other_lane() {
        use wbd_types::LaneKey;
        let mut a=a();let(mut tx,mut rx)=owners();
        let slow=LaneKey{tunnel:TunnelKey{slot:4,generation:1},slot:1,generation:1};
        let fast=LaneKey{tunnel:TunnelKey{slot:4,generation:1},slot:2,generation:1};
        rx.offer_lane(input(&mut a,1),0..1,slow,MonoNs(0)).unwrap();
        rx.offer_lane(input(&mut a,2),0..1,fast,MonoNs(0)).unwrap();
        let mut out=Vec::with_capacity(32);
        assert_eq!(rx.drain_ready_batch_where(MonoNs(0),&mut out,
            |lane|lane!=Some(slow)),1);
        assert_eq!(rx.queued(),1);
        assert_eq!(out[0].wire,0..1);
        out.clear();
        assert_eq!(rx.drain_ready_batch_where(MonoNs(0),&mut out,
            |lane|lane==Some(slow)),1);
        drop(out);drop(tx);assert_eq!(a.report().loaned,0);
    }
}
