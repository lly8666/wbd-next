//! R1-M1-STOP-LOAN-GENERATION-006: owner-local, scope-tagged ready batches.
 //! Scope tags fence callbacks, NOT sender authentication or ABI keys.
 //! All mutable TX/RX queues stay on one owner; no hot-path heap allocation.
 #![forbid(unsafe_code)]
 use std::{ops::Range, sync::{Arc,atomic::{AtomicUsize,Ordering::SeqCst}}};
 use wbd_types::{LaneKey,MonoNs};
 use wbd_types::buffer_contract::FrozenRecordHandle;
 use crate::memory::{FrozenRecord,UniqueBuffer};
 use super::{OfferError,RxOwner,RxPacket,TxDispatch,TxOwner};

 #[derive(Debug)]
 struct Tag { owner_id:u64, serial:u32, lane:LaneKey }
 /// Arc identity disallows a stale callback from a restarted owner even
 /// if its human-readable (owner_id, serial, lane) values were reused.
 #[derive(Clone,Debug)]
 pub struct ScopeToken(Arc<Tag>);
 impl ScopeToken {
     pub fn serial(&self)->u32 {self.0.serial}
     pub fn lane(&self)->LaneKey {self.0.lane}
     pub fn owner_id(&self)->u64 {self.0.owner_id}
 }
 #[derive(Debug,Clone,Copy,Eq,PartialEq)]
 pub enum ScopeError { Stale, Stopped, Exhausted, LaneMismatch, NonEmptyOutput }
 #[derive(Debug,Clone,Copy,Eq,PartialEq)]
 pub enum ScopedOfferError { Scope(ScopeError), Queue(OfferError) }
 #[derive(Debug,Clone,Copy,Eq,PartialEq)]
 pub struct Borrowed {pub tx_batches:usize,pub rx_batches:usize}
 impl Borrowed {
     pub fn quiescent(self)->bool {self.tx_batches==0&&self.rx_batches==0}
 }
 struct Ledger {tx:AtomicUsize,rx:AtomicUsize}
 impl Ledger {
     fn new()->Self {Self{tx:AtomicUsize::new(0),rx:AtomicUsize::new(0)}}
     fn snapshot(&self)->Borrowed {
         Borrowed{tx_batches:self.tx.load(SeqCst),rx_batches:self.rx.load(SeqCst)}
     }
 }
 /// An exact ownership fence for all *scoped batch handles*; standalone TX
 /// FrozenRecord clones outside these batches remain accounted by Arena's
 /// slot-generation/loan count, not by this counter. Do not call all-loans
 /// quiesced until BOTH this and the arena loan report are empty.
 pub struct RetiredScope {pub owner_id:u64,pub serial:u32,pub canceled:usize,ledger:Arc<Ledger>}
 impl RetiredScope {
     pub fn borrowed(&self)->Borrowed {self.ledger.snapshot()}
     pub fn batch_handles_released(&self)->bool {self.borrowed().quiescent()}
 }
 enum Kind {Tx,Rx}
 /// The batch owns all its handles until drop/recycle. It cannot be
 /// silently handed off as a bare Vec while a retirement fence is active.
 /// TX ciphertext remains immutable; RX remains pre-auth owned ingress.
 pub struct LoanBatch<T> {
     contents:Vec<T>,
     ledger:Option<Arc<Ledger>>,
     kind:Kind,
 }
 impl<T> LoanBatch<T> {
     pub fn as_slice(&self)->&[T] {&self.contents}
     pub fn len(&self)->usize {self.contents.len()}
     pub fn is_empty(&self)->bool {self.contents.is_empty()}
     /// Clear handles and return the original caller-preallocated Vec.
     /// No allocation; ledger only decrements AFTER payloads are dropped.
     pub fn recycle(mut self)->Vec<T> {
         self.contents.clear();
         std::mem::take(&mut self.contents)
     }
 }
 impl<T> Drop for LoanBatch<T> {
     fn drop(&mut self) {
         self.contents.clear();
         if let Some(ledger)=self.ledger.take() {
             match self.kind {
                 Kind::Tx => {ledger.tx.fetch_sub(1,SeqCst);}
                 Kind::Rx => {ledger.rx.fetch_sub(1,SeqCst);}
             }
         }
     }
 }
 /// Generation-scoped, single-owner facade around existing native proofs.
 /// Old scope batches remain valid immutable/unique borrows; they are not
 /// drained/re-enqueued by rotation. New scope never waits for old drops.
 pub struct ScopedOwner {
     tag:ScopeToken,
     tx:TxOwner,
     rx:RxOwner,
     ledger:Arc<Ledger>,
     stopped:bool,
 }
 impl ScopedOwner {
     pub fn new(owner_id:u64,serial:u32,lane:LaneKey,tx:TxOwner,rx:RxOwner)->Option<Self>{
         if owner_id==0||serial==0||lane.generation==0||lane.tunnel.generation==0 {
             return None;
         }
         Some(Self{
             tag:ScopeToken(Arc::new(Tag{owner_id,serial,lane})),
             tx,rx,ledger:Arc::new(Ledger::new()),stopped:false,
         })
     }
     pub fn token(&self)->ScopeToken {self.tag.clone()}
     fn check(&self,token:&ScopeToken)->Result<(),ScopeError> {
         if !Arc::ptr_eq(&self.tag.0,&token.0) {return Err(ScopeError::Stale);}
         if self.stopped {return Err(ScopeError::Stopped);}
         Ok(())
     }
     fn tx_meta(&self,record:&FrozenRecord)->Result<(),ScopeError> {
         if record.metadata().lane!=self.tag.0.lane {
             Err(ScopeError::LaneMismatch)
         } else {Ok(())}
     }
     pub fn offer_fresh(&mut self, token:&ScopeToken, record:FrozenRecord, now:MonoNs)
         ->Result<(),(ScopedOfferError,FrozenRecord)> {
         if let Err(e)=self.check(token) {return Err((ScopedOfferError::Scope(e),record));}
         if let Err(e)=self.tx_meta(&record) {return Err((ScopedOfferError::Scope(e),record));}
         self.tx.offer_fresh(record,now).map_err(|(e,v)|(ScopedOfferError::Queue(e),v))
     }
     pub fn offer_repair(&mut self,token:&ScopeToken,record:FrozenRecord,now:MonoNs)
         ->Result<(),(ScopedOfferError,FrozenRecord)> {
         if let Err(e)=self.check(token) {return Err((ScopedOfferError::Scope(e),record));}
         if let Err(e)=self.tx_meta(&record) {return Err((ScopedOfferError::Scope(e),record));}
         self.tx.offer_repair(record,now).map_err(|(e,v)|(ScopedOfferError::Queue(e),v))
     }
     pub fn offer_rx(&mut self,token:&ScopeToken,buffer:UniqueBuffer,wire:Range<usize>,now:MonoNs)
         ->Result<(),(ScopedOfferError,UniqueBuffer)> {
         if let Err(e)=self.check(token) {return Err((ScopedOfferError::Scope(e),buffer));}
         self.rx.offer_lane(buffer,wire,self.tag.0.lane,now)
             .map_err(|(e,v)|(ScopedOfferError::Queue(e),v))
     }
     pub fn drain_tx(&mut self,token:&ScopeToken,now:MonoNs,mut storage:Vec<TxDispatch>)
         ->Result<LoanBatch<TxDispatch>,(ScopeError,Vec<TxDispatch>)> {
         if let Err(e)=self.check(token) {return Err((e,storage));}
         if !storage.is_empty() {return Err((ScopeError::NonEmptyOutput,storage));}
         self.tx.drain_ready_batch(now,&mut storage);
         let ledger=if storage.is_empty(){None}else{
             self.ledger.tx.fetch_add(1,SeqCst);Some(Arc::clone(&self.ledger))
         };
         Ok(LoanBatch{contents:storage,ledger,kind:Kind::Tx})
     }
     pub fn drain_rx(&mut self,token:&ScopeToken,now:MonoNs,mut storage:Vec<RxPacket>)
         ->Result<LoanBatch<RxPacket>,(ScopeError,Vec<RxPacket>)> {
         if let Err(e)=self.check(token) {return Err((e,storage));}
         if !storage.is_empty() {return Err((ScopeError::NonEmptyOutput,storage));}
         self.rx.drain_ready_batch(now,&mut storage);
         let ledger=if storage.is_empty(){None}else{
             self.ledger.rx.fetch_add(1,SeqCst);Some(Arc::clone(&self.ledger))
         };
         Ok(LoanBatch{contents:storage,ledger,kind:Kind::Rx})
     }
     fn retire(&mut self)->RetiredScope {
         let canceled=self.tx.stop()+self.rx.stop();
         self.stopped=true;
         RetiredScope{owner_id:self.tag.0.owner_id,serial:self.tag.0.serial,
             canceled,ledger:Arc::clone(&self.ledger)}
     }
     pub fn stop(&mut self,token:&ScopeToken)->Result<RetiredScope,ScopeError>{
         self.check(token)?;
         Ok(self.retire())
     }
     /// Strictly next owner serial. Preallocate replacement owner queues on
     /// the control path, never during hot drains. Retired records and their
     /// immutable bytes are not moved into the successor.
     pub fn rotate(&mut self,token:&ScopeToken,next_lane:LaneKey,
         next_tx:TxOwner,next_rx:RxOwner)
         ->Result<RetiredScope,(ScopeError,TxOwner,RxOwner)> {
         if let Err(e)=self.check(token){return Err((e,next_tx,next_rx));}
         let Some(serial)=self.tag.0.serial.checked_add(1) else {
             return Err((ScopeError::Exhausted,next_tx,next_rx))
         };
         if next_lane.generation==0||next_lane.tunnel.generation==0||
           (next_lane==self.tag.0.lane) {
             return Err((ScopeError::LaneMismatch,next_tx,next_rx));
         }
         let old=self.retire();
         self.tag=ScopeToken(Arc::new(Tag{owner_id:old.owner_id,serial,lane:next_lane}));
         self.tx=next_tx;
         self.rx=next_rx;
         self.ledger=Arc::new(Ledger::new());
         self.stopped=false;
         Ok(old)
     }
 }

#[cfg(test)]
mod tests {
    use super::*;
    use crate::memory::Arena;
    use super::super::QueueLimits;
    use wbd_types::{TunnelKey,RecordPn,SeqOffset};
    use wbd_types::buffer_contract::{UniqueSealable,FrozenMetadata};
    fn lane(gen:u32)->LaneKey {
        LaneKey{tunnel:TunnelKey{slot:17,generation:gen},
            slot:2,generation:gen}
    }
    fn arena()->Arena {Arena::new(80,128,256,1,100_000).unwrap()}
    fn bounds()->QueueLimits {
        QueueLimits{slots:64,bytes:256,max_age_ns:10}
    }
    fn scope(gen:u32)->ScopedOwner {
        ScopedOwner::new(7,gen,lane(gen),
            TxOwner::new(bounds(),bounds()).unwrap(),
            RxOwner::new(bounds()).unwrap()).unwrap()
    }
    fn packet(a:&mut Arena,b:u8,gen:u32)->FrozenRecord {
        let mut p=a.allocate().unwrap();
        p.writable()[0]=b;
        p.freeze(0..1,FrozenMetadata{lane:lane(gen),pn:RecordPn(b as u64),
            seq:SeqOffset(b as u64),carrier_snapshot:1}).unwrap()
    }
    fn input(a:&mut Arena,b:u8)->UniqueBuffer{
        let mut p=a.allocate().unwrap();p.writable()[0]=b;p
    }
    fn new_pair()->(TxOwner,RxOwner) {
        (TxOwner::new(bounds(),bounds()).unwrap(),RxOwner::new(bounds()).unwrap())
    }
    #[test]
    fn r1_scope_empty_capacity_zero_is_a_nonallocating_ready_probe() {
        let mut s=scope(1);let t=s.token();
        let tx:Vec<TxDispatch>=Vec::new();let rx:Vec<RxPacket>=Vec::new();
        let out=s.drain_tx(&t,MonoNs(0),tx).unwrap_or_else(|_|panic!("unexpected batch rejection"));
        assert_eq!(out.len(),0);
        let tx=out.recycle();assert_eq!(tx.capacity(),0);
        let out=s.drain_rx(&t,MonoNs(0),rx).unwrap_or_else(|_|panic!("unexpected batch rejection"));
        assert_eq!(out.len(),0);
        assert_eq!(out.recycle().capacity(),0);
        assert!(s.stop(&t).unwrap().batch_handles_released());
    }
    #[test]
    fn r1_scope_one_mixed_tx_rx_exact_loan_stop_fence_and_last_return() {
        let mut a=arena();let mut s=scope(1);let t=s.token();
        s.offer_fresh(&t,packet(&mut a,11,1),MonoNs(0)).unwrap();
        s.offer_rx(&t,input(&mut a,33),0..1,MonoNs(0)).unwrap();
        let tx=s.drain_tx(&t,MonoNs(0),Vec::with_capacity(2)).unwrap_or_else(|_|panic!("unexpected batch rejection"));
        let rx=s.drain_rx(&t,MonoNs(0),Vec::with_capacity(2)).unwrap_or_else(|_|panic!("unexpected batch rejection"));
        assert_eq!(tx.len(),1);assert_eq!(rx.len(),1);
        let retired=s.stop(&t).unwrap();
        assert_eq!(retired.canceled,0);
        assert_eq!(retired.borrowed(),Borrowed{tx_batches:1,rx_batches:1});
        assert_eq!(a.report().loaned,2);
        drop(tx);
        assert_eq!(retired.borrowed(),Borrowed{tx_batches:0,rx_batches:1});
        assert_eq!(a.report().loaned,1);
        drop(rx);
        assert!(retired.batch_handles_released());
        assert_eq!(a.report().loaned,0);
    }
    #[test]
    fn r1_scope_exact_32_tx_and_rx_use_caller_preallocated_storage() {
        let mut a=arena();let mut s=scope(1);let t=s.token();
        for i in 0..32u8 {
            s.offer_fresh(&t,packet(&mut a,i,1),MonoNs(0)).unwrap();
            s.offer_rx(&t,input(&mut a,i),0..1,MonoNs(0)).unwrap();
        }
        let storage_tx=Vec::with_capacity(32);
        let storage_rx=Vec::with_capacity(32);
        let txptr=storage_tx.as_ptr();let rxptr=storage_rx.as_ptr();
        let tx=s.drain_tx(&t,MonoNs(0),storage_tx).unwrap_or_else(|_|panic!("unexpected batch rejection"));
        let rx=s.drain_rx(&t,MonoNs(0),storage_rx).unwrap_or_else(|_|panic!("unexpected batch rejection"));
        assert_eq!((tx.len(),rx.len()),(32,32));
        assert_eq!(tx.as_slice().as_ptr(),txptr);
        assert_eq!(rx.as_slice().as_ptr(),rxptr);
        assert_eq!(tx.as_slice()[0].record.bytes(),&[0]);
        assert_eq!(tx.as_slice()[31].record.bytes(),&[31]);
        assert_eq!(a.report().loaned,64);
        let retired=s.stop(&t).unwrap();
        assert_eq!(retired.borrowed(),Borrowed{tx_batches:1,rx_batches:1});
        drop(tx);drop(rx);
        assert!(retired.batch_handles_released());
        assert_eq!(a.report().loaned,0);
    }
    #[test]
    fn r1_scope_33_split_32_plus_one_both_directions_no_tail_loss() {
        let mut a=arena();let mut s=scope(1);let t=s.token();
        for i in 0..33u8 {
            s.offer_fresh(&t,packet(&mut a,i,1),MonoNs(0)).unwrap();
            s.offer_rx(&t,input(&mut a,i),0..1,MonoNs(0)).unwrap();
        }
        let tx1=s.drain_tx(&t,MonoNs(0),Vec::with_capacity(32)).unwrap_or_else(|_|panic!("unexpected batch rejection"));
        let rx1=s.drain_rx(&t,MonoNs(0),Vec::with_capacity(32)).unwrap_or_else(|_|panic!("unexpected batch rejection"));
        let tx2=s.drain_tx(&t,MonoNs(0),Vec::with_capacity(32)).unwrap_or_else(|_|panic!("unexpected batch rejection"));
        let rx2=s.drain_rx(&t,MonoNs(0),Vec::with_capacity(32)).unwrap_or_else(|_|panic!("unexpected batch rejection"));
        assert_eq!((tx1.len(),rx1.len(),tx2.len(),rx2.len()),(32,32,1,1));
        assert_eq!(tx2.as_slice()[0].record.bytes(),&[32]);
        assert_eq!(tx2.as_slice()[0].record.metadata().lane,lane(1));
        let retired=s.stop(&t).unwrap();
        assert_eq!(retired.borrowed(),Borrowed{tx_batches:2,rx_batches:2});
        drop(tx1);drop(tx2);drop(rx1);drop(rx2);
        assert!(retired.batch_handles_released());
        assert_eq!(a.report().loaned,0);
    }
    #[test]
    fn r1_scope_two_lane_generations_stale_callback_cannot_resubmit_ciphertext() {
        let mut a=arena();let mut s=scope(1);let old=s.token();
        let old_frozen=packet(&mut a,8,1);
        let clone=old_frozen.clone();
        s.offer_fresh(&old,old_frozen,MonoNs(0)).unwrap();
        let (nt,nr)=new_pair();
        let retired=s.rotate(&old,lane(2),nt,nr).unwrap_or_else(|_|panic!("unexpected rotation"));
        assert_eq!(retired.canceled,1);
        let fresh=s.token();
        assert_eq!((fresh.serial(),fresh.lane()),(2,lane(2)));
        let stale=s.offer_fresh(&old,clone.clone(),MonoNs(0));
        assert!(matches!(stale,Err((ScopedOfferError::Scope(ScopeError::Stale),_))));
        drop(stale);
        let wrong=s.offer_repair(&fresh,clone,MonoNs(0));
        assert!(matches!(wrong,Err((ScopedOfferError::Scope(ScopeError::LaneMismatch),_))));
        drop(wrong);
        s.offer_fresh(&fresh,packet(&mut a,9,2),MonoNs(0)).unwrap();
        let batch=s.drain_tx(&fresh,MonoNs(0),Vec::with_capacity(1)).unwrap_or_else(|_|panic!("unexpected batch rejection"));
        assert_eq!(batch.as_slice()[0].record.bytes(),&[9]);
        assert_eq!(retired.borrowed(),Borrowed{tx_batches:0,rx_batches:0});
        drop(batch);
        assert_eq!(a.report().loaned,0);
    }
    #[test]
    fn r1_scope_aba_restarted_owner_same_ids_rejects_old_token() {
        let mut a=arena();let x=scope(1);let stale=x.token();drop(x);
        let mut y=scope(1);let new=y.token();
        assert_eq!(stale.serial(),new.serial());
        assert_eq!(stale.owner_id(),new.owner_id());
        let result=y.offer_fresh(&stale,packet(&mut a,3,1),MonoNs(0));
        assert!(matches!(result,Err((ScopedOfferError::Scope(ScopeError::Stale),_))));
        drop(result);
        assert_eq!(y.drain_tx(&stale,MonoNs(0),Vec::with_capacity(4)).err().unwrap().0,
            ScopeError::Stale);
        assert_eq!(a.report().loaned,0);
    }
    #[test]
    fn r1_scope_rotate_does_not_wait_old_loan_first_new_fresh_immediate() {
        let mut a=arena();let mut s=scope(1);let old=s.token();
        s.offer_fresh(&old,packet(&mut a,6,1),MonoNs(0)).unwrap();
        s.offer_rx(&old,input(&mut a,7),0..1,MonoNs(0)).unwrap();
        let old_tx=s.drain_tx(&old,MonoNs(0),Vec::with_capacity(1)).unwrap_or_else(|_|panic!("unexpected batch rejection"));
        let old_rx=s.drain_rx(&old,MonoNs(0),Vec::with_capacity(1)).unwrap_or_else(|_|panic!("unexpected batch rejection"));
        let (tx,rx)=new_pair();
        let retired=s.rotate(&old,lane(2),tx,rx).unwrap_or_else(|_|panic!("rotation failure"));
        assert_eq!(retired.borrowed(),Borrowed{tx_batches:1,rx_batches:1});
        let next=s.token();
        s.offer_fresh(&next,packet(&mut a,8,2),MonoNs(1)).unwrap();
        let new_first=s.drain_tx(&next,MonoNs(1),Vec::with_capacity(1)).unwrap_or_else(|_|panic!("unexpected batch rejection"));
        assert_eq!(new_first.as_slice()[0].record.bytes(),&[8]);
        assert_eq!(a.report().loaned,3);
        drop(old_tx);drop(old_rx);
        assert!(retired.batch_handles_released());
        assert_eq!(a.report().loaned,1);
        drop(new_first);
        assert_eq!(a.report().loaned,0);
    }
    #[test]
    fn r1_scope_stop_during_ready_releases_only_queued_not_dispatched() {
        let mut a=arena();let mut s=scope(1);let t=s.token();
        for i in 0..5 {
            s.offer_fresh(&t,packet(&mut a,i,1),MonoNs(0)).unwrap();
            s.offer_rx(&t,input(&mut a,i),0..1,MonoNs(0)).unwrap();
        }
        let tx=s.drain_tx(&t,MonoNs(0),Vec::with_capacity(1)).unwrap_or_else(|_|panic!("unexpected batch rejection"));
        let rx=s.drain_rx(&t,MonoNs(0),Vec::with_capacity(1)).unwrap_or_else(|_|panic!("unexpected batch rejection"));
        let retired=s.stop(&t).unwrap();
        assert_eq!(retired.canceled,8);
        assert_eq!(a.report().loaned,2);
        assert_eq!(retired.borrowed(),Borrowed{tx_batches:1,rx_batches:1});
        assert_eq!(s.stop(&t).err(),Some(ScopeError::Stopped));
        assert_eq!(s.drain_tx(&t,MonoNs(0),Vec::with_capacity(2)).err().unwrap().0,
            ScopeError::Stopped);
        drop(rx);drop(tx);
        assert!(retired.batch_handles_released());
        assert_eq!(a.report().loaned,0);
    }
    #[test]
    fn r1_scope_fake_clock_expiry_drops_old_without_leaking_or_early_fresh() {
        let mut a=arena();let mut s=scope(1);let t=s.token();
        s.offer_fresh(&t,packet(&mut a,1,1),MonoNs(0)).unwrap();
        s.offer_rx(&t,input(&mut a,2),0..1,MonoNs(0)).unwrap();
        let no=s.drain_tx(&t,MonoNs(11),Vec::with_capacity(1)).unwrap_or_else(|_|panic!("unexpected batch rejection"));
        let nr=s.drain_rx(&t,MonoNs(11),Vec::with_capacity(1)).unwrap_or_else(|_|panic!("unexpected batch rejection"));
        assert_eq!((no.len(),nr.len()),(0,0));
        assert_eq!(a.report().loaned,0);
        assert!(s.stop(&t).unwrap().batch_handles_released());
    }
    #[test]
    fn r1_scope_stop_last_frozen_clone_return_backlog_and_rx_mix() {
        let mut a=arena();let mut s=scope(1);let t=s.token();
        let f=packet(&mut a,1,1);let clone=f.clone();
        s.offer_fresh(&t,f,MonoNs(0)).unwrap();
        s.offer_rx(&t,input(&mut a,2),0..1,MonoNs(0)).unwrap();
        let tx=s.drain_tx(&t,MonoNs(0),Vec::with_capacity(1)).unwrap_or_else(|_|panic!("unexpected batch rejection"));
        let rx=s.drain_rx(&t,MonoNs(0),Vec::with_capacity(1)).unwrap_or_else(|_|panic!("unexpected batch rejection"));
        let fence=s.stop(&t).unwrap();
        drop(tx);drop(rx);
        assert!(fence.batch_handles_released());
        // Batch fence is clear, but last clone still holds arena loan.
        assert_eq!(a.report().loaned,1);
        let join=std::thread::spawn(move||drop(clone));
        join.join().unwrap();
        assert_eq!(a.report().loaned,0);
    }
    #[test]
    fn r1_scope_generation_exhausted_or_reused_lane_fails_without_retire() {
        let mut a=arena();let mut s=scope(u32::MAX);let old=s.token();
        let (tx,rx)=new_pair();
        let err=s.rotate(&old,lane(1),tx,rx);
        assert!(matches!(err,Err((ScopeError::Exhausted,_,_))));
        s.offer_fresh(&old,packet(&mut a,3,u32::MAX),MonoNs(0)).unwrap();
        let b=s.drain_tx(&old,MonoNs(0),Vec::with_capacity(1)).unwrap_or_else(|_|panic!("unexpected batch rejection"));
        assert_eq!(b.len(),1);
        drop(b);s.stop(&old).unwrap();
        assert_eq!(a.report().loaned,0);
        let mut o=scope(1);let tk=o.token();
        let (tx,rx)=new_pair();
        assert!(matches!(o.rotate(&tk,lane(1),tx,rx),
            Err((ScopeError::LaneMismatch,_,_))));
    }
    #[test]
    fn r1_scope_nonempty_caller_batch_and_zero_spare_capacity_reject_without_loss() {
        let mut a=arena();let mut s=scope(1);let t=s.token();
        s.offer_fresh(&t,packet(&mut a,7,1),MonoNs(0)).unwrap();
        let empty=s.drain_tx(&t,MonoNs(0),Vec::new()).unwrap_or_else(|_|panic!("unexpected batch rejection"));
        assert_eq!(empty.len(),0);
        let prev=packet(&mut a,8,1);
        let mut filled=Vec::with_capacity(1);
        filled.push(TxDispatch{kind:super::super::TxKind::Fresh,record:prev});
        let rejected=s.drain_tx(&t,MonoNs(0),filled);
        assert_eq!(rejected.err().unwrap().0,ScopeError::NonEmptyOutput);
        let valid=s.drain_tx(&t,MonoNs(0),Vec::with_capacity(1)).unwrap_or_else(|_|panic!("unexpected batch rejection"));
        assert_eq!(valid.as_slice()[0].record.bytes(),&[7]);
        drop(valid);
        s.stop(&t).unwrap();
        assert_eq!(a.report().loaned,0);
    }
}
