//! R1-M1-BOUNDED-EARLY-RX-BOUNDARY-010.
//! Owner-local early RX staging before an externally signaled Detach.
//! Boundary is a caller fact, NOT parsed Go cold bytes, authentication,
//! a packet-number origin, or permission to enable production traffic.
#![forbid(unsafe_code)]
use std::{collections::VecDeque,ops::Range};
use wbd_types::{LaneKey,MonoNs};
use wbd_types::buffer_contract::{checked_wire_range,UniqueSealable};
use crate::memory::UniqueBuffer;
use super::{OfferError,RxOwner,RxPacket,TxOwner,generation::{ScopedOwner,ScopeToken,ScopeError,ScopedOfferError,LoanBatch,RetiredScope}};

#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct EarlyLimits {pub slots:usize,pub bytes:usize}
impl EarlyLimits {
    pub fn valid(self)->bool {self.slots>0&&self.slots<=32&&self.bytes>0}
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub enum EarlyError {
    Scope(ScopeError),NotPrepared,BoundaryConflict,BeforeBoundary,Overlap,
    InvalidWindow,OffsetOverflow,Full,ByteBudget,Queue(OfferError),
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub enum EarlyAccepted {Staged,Ready}
struct Staged {buffer:UniqueBuffer,wire:Range<usize>,now:MonoNs}
/// Owner-local fence. `ready` only counts the ScopedOwner's already
/// dispatched LoanBatch leases; it does NOT include raw external Arc clones.
pub struct EarlyRetirement {pub ready:RetiredScope,pub early_canceled:usize}
impl EarlyRetirement {
    pub fn canceled(&self)->usize {self.ready.canceled+self.early_canceled}
}
/// All queues are bounded and preallocated on control path.
/// No mutable buffer ever crosses scopes. No session admission is claimed.
pub struct EarlyRxOwner {
    owner:ScopedOwner,
    stage:VecDeque<Staged>,
    limits:EarlyLimits,
    used_bytes:usize,
    boundary:Option<u64>,
    detached:bool,
    early_canceled:usize,
    stopped:bool,
}
impl EarlyRxOwner {
    pub fn new(owner:ScopedOwner,limits:EarlyLimits)->Option<Self>{
        if !limits.valid(){return None;}
        // Reserve enough preexisting inner RX capacity for atomic Detach.
        // While staged, only this wrapper owns the underlying RxOwner.
        let (available_slots,available_bytes)=owner.rx_capacity_remaining();
        if limits.slots>available_slots||limits.bytes>available_bytes{
            return None;
        }
        Some(Self{
            owner,stage:VecDeque::with_capacity(limits.slots),limits,
            used_bytes:0,boundary:None,detached:false,
            early_canceled:0,stopped:false,
        })
    }
    pub fn token(&self)->ScopeToken {self.owner.token()}
    pub fn staged(&self)->(usize,usize) {(self.stage.len(),self.used_bytes)}
    pub fn detached(&self)->bool {self.detached}
    pub fn prepare(&mut self,token:&ScopeToken,external_exact_rx_boundary:u64)
        ->Result<(),EarlyError> {
        self.owner.check(token).map_err(EarlyError::Scope)?;
        match self.boundary {
            Some(previous) if previous!=external_exact_rx_boundary =>
                Err(EarlyError::BoundaryConflict),
            Some(_) => Ok(()),
            None => {self.boundary=Some(external_exact_rx_boundary);Ok(())}
        }
    }
    /// Segment is [absolute_offset, absolute_offset+wire.len()).
    /// End <= boundary: caller retains pre-bootstrap bytes.
    /// Start < boundary < end: reject ALL overlapping bytes, never split.
    /// Start >= boundary: staged before Detach, or offered to current RX
    /// after Detach. No wire parser can manufacture this boundary.
    pub fn offer(&mut self,token:&ScopeToken,mut buffer:UniqueBuffer,
        wire:Range<usize>,absolute_offset:u64,now:MonoNs)
        ->Result<EarlyAccepted,(EarlyError,UniqueBuffer)> {
        if let Err(e)=self.owner.check(token) {
            return Err((EarlyError::Scope(e),buffer));
        }
        let Some(boundary)=self.boundary else{
            return Err((EarlyError::NotPrepared,buffer));
        };
        let wire=match checked_wire_range(buffer.writable().len(),wire) {
            Ok(range)=>range,
            Err(_)=>return Err((EarlyError::InvalidWindow,buffer)),
        };
        let size=wire.len();
        let Some(end)=absolute_offset.checked_add(size as u64) else{
            return Err((EarlyError::OffsetOverflow,buffer));
        };
        if end<=boundary {return Err((EarlyError::BeforeBoundary,buffer));}
        if absolute_offset<boundary {
            return Err((EarlyError::Overlap,buffer));
        }
        if self.detached {
            return self.owner.offer_rx(token,buffer,wire,now)
                .map(|()|EarlyAccepted::Ready)
                .map_err(|(e,buf)|match e {
                    ScopedOfferError::Scope(x)=>(EarlyError::Scope(x),buf),
                    ScopedOfferError::Queue(x)=>(EarlyError::Queue(x),buf),
                });
        }
        if self.stage.len()>=self.limits.slots {
            return Err((EarlyError::Full,buffer));
        }
        if size>self.limits.bytes.saturating_sub(self.used_bytes){
            return Err((EarlyError::ByteBudget,buffer));
        }
        self.stage.push_back(Staged{buffer,wire,now});
        self.used_bytes+=size;
        Ok(EarlyAccepted::Staged)
    }
    /// Control-path Detach: move each owned, unique early item into the
    /// current RxOwner. A full inner RX keeps the unoffered tail staged.
    /// No early batch becomes dispatchable until the entire flush commits.
    /// Retrying after Queue(Full) never repeats already accepted items.
    pub fn detach(&mut self,token:&ScopeToken)->Result<(),EarlyError>{
        self.owner.check(token).map_err(EarlyError::Scope)?;
        if self.boundary.is_none(){return Err(EarlyError::NotPrepared);}
        if self.detached {return Ok(());}
        // No partial Detach: either ALL pre-boundary-staged early packets
        // can enter existing RX owner or NONE move. The wrapper is its
        // exclusive owner and no other producer can interleave here.
        let (slots,bytes)=self.owner.rx_capacity_remaining();
        if self.stage.len()>slots {return Err(EarlyError::Queue(OfferError::Full));}
        if self.used_bytes>bytes {return Err(EarlyError::Queue(OfferError::ByteBudget));}
        while let Some(Staged{buffer,wire,now})=self.stage.pop_front() {
            let bytes=wire.len();
            match self.owner.offer_rx(token,buffer,wire.clone(),now) {
                Ok(())=>self.used_bytes-=bytes,
                Err((error,buffer))=>{
                    self.stage.push_front(Staged{buffer,wire,now});
                    return Err(match error {
                        ScopedOfferError::Scope(x)=>EarlyError::Scope(x),
                        ScopedOfferError::Queue(x)=>EarlyError::Queue(x),
                    });
                }
            }
        }
        self.detached=true;
        Ok(())
    }
    pub fn drain_rx(&mut self,token:&ScopeToken,now:MonoNs,storage:Vec<RxPacket>)
        ->Result<LoanBatch<RxPacket>,(EarlyError,Vec<RxPacket>)> {
        if let Err(e)=self.owner.check(token){
            return Err((EarlyError::Scope(e),storage));
        }
        if !self.detached {return Err((EarlyError::NotPrepared,storage));}
        self.owner.drain_rx(token,now,storage)
            .map_err(|(e,storage)|(EarlyError::Scope(e),storage))
    }
    /// Stop is idempotent. Drop only staged items and owned queued RX.
    /// Dispatched batches remain borrowed by their original generation.
    pub fn stop(&mut self,token:&ScopeToken)->Result<EarlyRetirement,EarlyError>{
        self.owner.check_token_identity(token).map_err(EarlyError::Scope)?;
        if !self.stopped {
            self.early_canceled=self.stage.len();
            self.stage.clear();
            self.used_bytes=0;
            self.stopped=true;
        }
        Ok(EarlyRetirement{
            ready:self.owner.stop(token).map_err(EarlyError::Scope)?,
            early_canceled:self.early_canceled,
        })
    }
    /// Rotate discards old undetached tail only AFTER successful rotation.
    /// Next external boundary must be separately prepared; old callbacks
    /// and borrowed RX handles cannot flow into the new owner.
    pub fn rotate(&mut self,token:&ScopeToken,next_lane:LaneKey,
        next_tx:TxOwner,next_rx:RxOwner)
        ->Result<EarlyRetirement,(ScopeError,TxOwner,RxOwner)>{
        let retired=self.owner.rotate(token,next_lane,next_tx,next_rx)?;
        let canceled=self.stage.len();
        self.stage.clear();
        self.used_bytes=0;
        self.boundary=None;
        self.detached=false;
        self.early_canceled=0;
        self.stopped=false;
        Ok(EarlyRetirement{ready:retired,early_canceled:canceled})
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::memory::{Arena,FrozenRecord};
    use super::super::{QueueLimits,TxDispatch};
    use wbd_types::{TunnelKey,RecordPn,SeqOffset};
    use wbd_types::buffer_contract::{BufferContractError,UniqueSealable,FrozenMetadata,FrozenRecordHandle};
    fn lane(gen:u32)->LaneKey{
        LaneKey{tunnel:TunnelKey{slot:302,generation:gen},slot:3,generation:gen}
    }
    fn limits(slots:usize,bytes:usize)->QueueLimits{
        QueueLimits{slots,bytes,max_age_ns:1_000_000}
    }
    fn pair()->(TxOwner,RxOwner) {
        (TxOwner::new(limits(64,96),limits(64,96)).unwrap(),
         RxOwner::new(limits(64,96)).unwrap())
    }
    fn early(slots:usize,bytes:usize)->EarlyRxOwner {
        let(tx,rx)=pair();
        let inner=ScopedOwner::new(991,1,lane(1),tx,rx).unwrap();
        EarlyRxOwner::new(inner,EarlyLimits{slots,bytes}).unwrap()
    }
    fn arena(count:usize)->Arena{
        Arena::new(181,count,256,1,300_000).unwrap()
    }
    fn buffer(a:&mut Arena,b:u8)->UniqueBuffer{
        let mut x=a.allocate().unwrap();
        x.writable()[0]=b;x
    }
    fn frozen(a:&mut Arena,b:u8)->FrozenRecord{
        let mut x=a.allocate().unwrap();
        x.writable()[0]=b;
        x.freeze(0..1,FrozenMetadata{
            lane:lane(1),pn:RecordPn(b as u64),
            seq:SeqOffset(b as u64),carrier_snapshot:1
        }).unwrap()
    }
    fn ready<T>(x:Result<LoanBatch<T>,(EarlyError,Vec<T>)>)->LoanBatch<T>{
        x.unwrap_or_else(|_|panic!("detached current owner must dispatch"))
    }
    #[test]
    fn r1_early_rx_prepare_caller_only_before_exact_after_overlap_overflow() {
        let mut a=arena(12);let mut s=early(8,32);let t=s.token();
        let missing=s.offer(&t,buffer(&mut a,1),0..4,100,MonoNs(0));
        assert!(matches!(missing,Err((EarlyError::NotPrepared,_))));
        drop(missing);
        s.prepare(&t,100).unwrap();
        assert_eq!(s.prepare(&t,100),Ok(()));
        assert_eq!(s.prepare(&t,101),Err(EarlyError::BoundaryConflict));
        let before=s.offer(&t,buffer(&mut a,2),0..4,96,MonoNs(0));
        assert!(matches!(before,Err((EarlyError::BeforeBoundary,_))));
        drop(before);
        let one_before=s.offer(&t,buffer(&mut a,3),0..1,99,MonoNs(0));
        assert!(matches!(one_before,Err((EarlyError::BeforeBoundary,_))));
        drop(one_before);
        let crossing=s.offer(&t,buffer(&mut a,4),0..4,99,MonoNs(0));
        assert!(matches!(crossing,Err((EarlyError::Overlap,_))));
        drop(crossing);
        let crossing_again=s.offer(&t,buffer(&mut a,5),0..4,97,MonoNs(0));
        assert!(matches!(crossing_again,Err((EarlyError::Overlap,_))));
        drop(crossing_again);
        let overflow=s.offer(&t,buffer(&mut a,6),0..4,u64::MAX-1,MonoNs(0));
        assert!(matches!(overflow,Err((EarlyError::OffsetOverflow,_))));
        drop(overflow);
        let invalid=s.offer(&t,buffer(&mut a,7),0..0,100,MonoNs(0));
        assert!(matches!(invalid,Err((EarlyError::InvalidWindow,_))));
        drop(invalid);
        assert!(matches!(s.offer(&t,buffer(&mut a,8),0..1,100,MonoNs(0)),
            Ok(EarlyAccepted::Staged)));
        assert_eq!(s.staged(),(1,1));
        assert_eq!(a.report().loaned,1);
        s.detach(&t).unwrap();
        let batch=ready(s.drain_rx(&t,MonoNs(0),Vec::with_capacity(1)));
        assert_eq!(batch.len(),1);
        drop(batch);
        assert_eq!(a.report().loaned,0);
    }
    #[test]
    fn r1_early_rx_zero_then_one_after_detach_immediate_no_hol() {
        let mut a=arena(4);let mut s=early(32,32);let t=s.token();
        s.prepare(&t,300).unwrap();
        let rejected=s.drain_rx(&t,MonoNs(0),Vec::with_capacity(1));
        assert_eq!(rejected.err().unwrap().0,EarlyError::NotPrepared);
        assert_eq!(s.staged(),(0,0));
        s.detach(&t).unwrap();
        assert_eq!(s.detach(&t),Ok(()));
        let empty=ready(s.drain_rx(&t,MonoNs(0),Vec::with_capacity(1)));
        assert_eq!(empty.len(),0);
        let storage=empty.recycle();
        assert!(matches!(s.offer(&t,buffer(&mut a,13),0..1,300,MonoNs(1)),
            Ok(EarlyAccepted::Ready)));
        let first=ready(s.drain_rx(&t,MonoNs(1),storage));
        assert_eq!(first.len(),1);
        assert_eq!(first.as_slice()[0].wire,0..1);
        drop(first);
        assert_eq!(a.report().loaned,0);
    }
    #[test]
    fn r1_early_rx_32_cap_33rd_full_still_owned_not_free_until_drop() {
        let mut a=arena(40);let mut s=early(32,32);let t=s.token();
        s.prepare(&t,10).unwrap();
        for i in 0..32u8 {
            assert!(matches!(s.offer(&t,buffer(&mut a,i),0..1,10+i as u64,MonoNs(0)),
                Ok(EarlyAccepted::Staged)));
        }
        let overflow=buffer(&mut a,33);
        let rejected=s.offer(&t,overflow,0..1,42,MonoNs(0));
        assert!(matches!(rejected,Err((EarlyError::Full,_))));
        assert_eq!(a.report().loaned,33);
        drop(rejected);
        assert_eq!(a.report().loaned,32);
        assert_eq!(s.staged(),(32,32));
        assert_eq!(s.drain_rx(&t,MonoNs(0),Vec::with_capacity(32))
            .err().unwrap().0,EarlyError::NotPrepared);
        s.detach(&t).unwrap();
        assert_eq!(s.staged(),(0,0));
        let batch=ready(s.drain_rx(&t,MonoNs(0),Vec::with_capacity(32)));
        assert_eq!(batch.len(),32);
        assert_eq!(batch.as_slice()[0].wire,0..1);
        let retired=s.stop(&t).unwrap();
        assert_eq!(retired.canceled(),0);
        assert_eq!(retired.ready.borrowed().rx_batches,1);
        assert_eq!(a.report().loaned,32);
        drop(batch);
        assert!(retired.ready.batch_handles_released());
        assert_eq!(a.report().loaned,0);
    }
    #[test]
    fn r1_early_rx_byte_cap_and_owner_prealloc_mismatch_fail_closed() {
        let mut a=arena(4);let mut s=early(3,3);let t=s.token();
        s.prepare(&t,1).unwrap();
        assert!(matches!(s.offer(&t,buffer(&mut a,1),0..2,1,MonoNs(0)),
            Ok(EarlyAccepted::Staged)));
        let r=s.offer(&t,buffer(&mut a,2),0..2,3,MonoNs(0));
        assert!(matches!(r,Err((EarlyError::ByteBudget,_))));
        drop(r);
        assert_eq!(s.staged(),(1,2));
        let stopped=s.stop(&t).unwrap();
        assert_eq!(stopped.canceled(),1);
        assert_eq!(a.report().loaned,0);
        assert!(EarlyRxOwner::new({
            let(tx,rx)=pair();
            ScopedOwner::new(10,1,lane(1),tx,rx).unwrap()
        },EarlyLimits{slots:33,bytes:96}).is_none());
        let tiny=ScopedOwner::new(11,1,lane(1),
            TxOwner::new(limits(1,1),limits(1,1)).unwrap(),
            RxOwner::new(limits(1,1)).unwrap()).unwrap();
        assert!(EarlyRxOwner::new(tiny,EarlyLimits{slots:2,bytes:2}).is_none());
    }
    #[test]
    fn r1_early_rx_stop_pre_detach_twice_held_frozen_late_return() {
        let mut a=arena(10);let mut s=early(4,4);let t=s.token();
        s.prepare(&t,50).unwrap();
        s.offer(&t,buffer(&mut a,2),0..1,50,MonoNs(0)).unwrap();
        s.offer(&t,buffer(&mut a,3),0..1,51,MonoNs(0)).unwrap();
        let frozen=frozen(&mut a,42);
        let cloned_driver_lease=frozen.clone();
        assert_eq!(frozen.bytes().as_ptr(),cloned_driver_lease.bytes().as_ptr());
        drop(frozen);
        let first=s.stop(&t).unwrap();
        let second=s.stop(&t).unwrap();
        assert_eq!((first.canceled(),second.canceled()),(2,2));
        assert!(first.ready.batch_handles_released());
        assert_eq!(s.detached(),false);
        assert_eq!(s.detach(&t),Err(EarlyError::Scope(ScopeError::Stopped)));
        let after=s.offer(&t,buffer(&mut a,4),0..1,52,MonoNs(0));
        assert!(matches!(after,Err((EarlyError::Scope(ScopeError::Stopped),_))));
        drop(after);
        assert_eq!(a.stop().loaned,1);
        let join=std::thread::spawn(move||{
            assert_eq!(cloned_driver_lease.bytes(),&[42]);
            drop(cloned_driver_lease);
        });
        join.join().unwrap();
        assert!(a.quiesced());
        assert_eq!(a.report().loaned,0);
    }
    #[test]
    fn r1_early_rx_old_32_held_rotate_fresh_new_scope_not_hol() {
        let mut a=arena(96);let mut s=early(32,32);let old=s.token();
        s.prepare(&old,100).unwrap();
        for i in 0..32u8 {
            s.offer(&old,buffer(&mut a,i),0..1,100+i as u64,MonoNs(0)).unwrap();
        }
        s.detach(&old).unwrap();
        let borrowed=ready(s.drain_rx(&old,MonoNs(0),Vec::with_capacity(32)));
        assert_eq!(borrowed.len(),32);
        let(tx,rx)=pair();
        let retired=s.rotate(&old,lane(2),tx,rx)
            .unwrap_or_else(|_|panic!("owner must rotate"));
        assert_eq!(retired.early_canceled,0);
        assert_eq!(retired.ready.borrowed().rx_batches,1);
        let new=s.token();
        let bad=s.offer(&old,buffer(&mut a,71),0..1,200,MonoNs(1));
        assert!(matches!(bad,Err((EarlyError::Scope(ScopeError::Stale),_))));
        drop(bad);
        assert_eq!(s.drain_rx(&new,MonoNs(1),Vec::with_capacity(1))
            .err().unwrap().0,EarlyError::NotPrepared);
        s.prepare(&new,200).unwrap();
        assert!(matches!(s.offer(&new,buffer(&mut a,88),0..1,200,MonoNs(1)),
            Ok(EarlyAccepted::Staged)));
        s.detach(&new).unwrap();
        let first=ready(s.drain_rx(&new,MonoNs(1),Vec::with_capacity(1)));
        assert_eq!(first.len(),1);
        assert_eq!(first.as_slice()[0].wire,0..1);
        assert_eq!(s.drain_rx(&old,MonoNs(1),Vec::with_capacity(1))
            .err().unwrap().0,EarlyError::Scope(ScopeError::Stale));
        let current=s.stop(&new).unwrap();
        assert_eq!(a.report().loaned,33);
        drop(first);
        assert_eq!(a.report().loaned,32);
        let join=std::thread::spawn(move||drop(borrowed));
        join.join().unwrap();
        assert!(retired.ready.batch_handles_released());
        assert!(current.ready.batch_handles_released());
        assert_eq!(a.report().loaned,0);
    }
    #[test]
    fn r1_early_rx_stop_after_detach_does_not_free_loan_and_aba_stale() {
        let mut a=arena(12);let mut s=early(4,4);let tk=s.token();
        s.prepare(&tk,8).unwrap();
        s.offer(&tk,buffer(&mut a,1),0..1,8,MonoNs(0)).unwrap();
        s.detach(&tk).unwrap();
        let old=ready(s.drain_rx(&tk,MonoNs(0),Vec::with_capacity(1)));
        let report=s.stop(&tk).unwrap();
        assert_eq!(s.stop(&tk).unwrap().canceled(),0);
        assert_eq!(report.ready.borrowed().rx_batches,1);
        assert_eq!(a.report().loaned,1);
        drop(s);
        let mut restarted=early(4,4);
        let new=restarted.token();
        assert_eq!((tk.serial(),tk.owner_id()),(new.serial(),new.owner_id()));
        assert_eq!(restarted.drain_rx(&tk,MonoNs(1),Vec::with_capacity(1))
            .err().unwrap().0,EarlyError::Scope(ScopeError::Stale));
        restarted.prepare(&new,8).unwrap();
        restarted.offer(&new,buffer(&mut a,2),0..1,8,MonoNs(1)).unwrap();
        restarted.detach(&new).unwrap();
        let fresh=ready(restarted.drain_rx(&new,MonoNs(1),Vec::with_capacity(1)));
        assert_eq!(fresh.len(),1);
        assert_eq!(a.report().loaned,2);
        drop(old);
        assert!(report.ready.batch_handles_released());
        assert_eq!(a.report().loaned,1);
        drop(fresh);
        assert_eq!(a.report().loaned,0);
    }
    #[test]
    fn r1_early_rx_rotation_discards_undelivered_tail_no_old_new_mix() {
        let mut a=arena(16);let mut s=early(4,4);let old=s.token();
        s.prepare(&old,100).unwrap();
        for i in 0..4u8 {
            s.offer(&old,buffer(&mut a,i),0..1,100+i as u64,MonoNs(0)).unwrap();
        }
        let(tx,rx)=pair();
        let retired=s.rotate(&old,lane(2),tx,rx)
            .unwrap_or_else(|_|panic!("valid rotate"));
        assert_eq!(retired.canceled(),4);
        assert_eq!(a.report().loaned,0);
        let now=s.token();
        assert_eq!(s.staged(),(0,0));
        let stale=s.offer(&old,buffer(&mut a,7),0..1,100,MonoNs(1));
        assert!(matches!(stale,Err((EarlyError::Scope(ScopeError::Stale),_))));
        drop(stale);
        assert_eq!(s.prepare(&now,200),Ok(()));
        s.offer(&now,buffer(&mut a,9),0..1,200,MonoNs(1)).unwrap();
        s.detach(&now).unwrap();
        let batch=ready(s.drain_rx(&now,MonoNs(1),Vec::with_capacity(1)));
        assert_eq!(batch.len(),1);
        drop(batch);
        assert_eq!(a.report().loaned,0);
    }
}
