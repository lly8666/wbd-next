//! R1-M1-OWNER-LOAN-STOP-INTEGRATION-009: owner-only counterexamples.
 //! A FrozenRecord Arc clone stands in for an already handed-off driver
 //! borrow, NOT for a real OS driver lease or authenticated admission.
 #![forbid(unsafe_code)]
 use super::generation::{ScopedOwner,ScopeToken,ScopeError,ScopedOfferError,LoanBatch,Borrowed};
 use super::{TxOwner,RxOwner,TxDispatch,RxPacket,QueueLimits,TxKind};
 use crate::memory::{Arena,FrozenRecord,UniqueBuffer};
 use wbd_types::{MonoNs,LaneKey,TunnelKey,RecordPn,SeqOffset};
 use wbd_types::buffer_contract::{FrozenMetadata,FrozenRecordHandle,UniqueSealable,BufferContractError};
 fn lane(gen:u32)->LaneKey {
     LaneKey{tunnel:TunnelKey{slot:503,generation:gen},slot:4,generation:gen}
 }
 fn limits()->QueueLimits{QueueLimits{slots:64,bytes:64,max_age_ns:1_000_000}}
 fn pair()->(TxOwner,RxOwner){
     (TxOwner::new(limits(),limits()).unwrap(),RxOwner::new(limits()).unwrap())
 }
 fn owner()->ScopedOwner{
     let(tx,rx)=pair();
     ScopedOwner::new(73,1,lane(1),tx,rx).unwrap()
 }
 fn arena(n:usize)->Arena{Arena::new(141,n,256,1,200_000).unwrap()}
 fn frozen(a:&mut Arena,b:u8,gen:u32)->FrozenRecord{
     let mut x=a.allocate().unwrap();x.writable()[0]=b;
     x.freeze(0..1,FrozenMetadata{
         lane:lane(gen),pn:RecordPn(b as u64),seq:SeqOffset(b as u64),
         carrier_snapshot:4
     }).unwrap()
 }
 fn incoming(a:&mut Arena,b:u8)->UniqueBuffer{
     let mut x=a.allocate().unwrap();x.writable()[0]=b;x
 }
 fn ready<T>(v:Result<LoanBatch<T>,(ScopeError,Vec<T>)>)->LoanBatch<T>{
     v.unwrap_or_else(|_|panic!("current ready owner must accept"))
 }
 fn rotate(s:&mut ScopedOwner,t:&ScopeToken)->super::generation::RetiredScope{
     let(tx,rx)=pair();
     s.rotate(t,lane(2),tx,rx).unwrap_or_else(|_|panic!("rotate"))
 }

 #[test]
 fn r1_owner_loan_stop_idempotent_cancels_only_undispatched_33_tail() {
     let mut a=arena(96);let mut s=owner();let tk=s.token();
     for i in 0..33u8 {
         s.offer_fresh(&tk,frozen(&mut a,i,1),MonoNs(0)).unwrap();
         s.offer_rx(&tk,incoming(&mut a,i),0..1,MonoNs(0)).unwrap();
     }
     let borrowed_tx=ready(s.drain_tx(&tk,MonoNs(0),Vec::with_capacity(32)));
     let borrowed_rx=ready(s.drain_rx(&tk,MonoNs(0),Vec::with_capacity(32)));
     assert_eq!((borrowed_tx.len(),borrowed_rx.len()),(32,32));
     let first=s.stop(&tk).unwrap();
     assert_eq!(first.canceled,2);
     assert_eq!(first.borrowed(),Borrowed{tx_batches:1,rx_batches:1});
     let repeat=s.stop(&tk).unwrap();
     assert_eq!(repeat.canceled,2);
     assert_eq!(repeat.borrowed(),first.borrowed());
     assert!(matches!(s.offer_fresh(&tk,frozen(&mut a,40,1),MonoNs(1)),
         Err((ScopedOfferError::Scope(ScopeError::Stopped),_))));
     assert_eq!(s.checked_tx_ready(&tk,&borrowed_tx).err(),Some(ScopeError::Stopped));
     assert_eq!(s.checked_rx_ready(&tk,&borrowed_rx).err(),Some(ScopeError::Stopped));
     assert_eq!(a.report().loaned,64); // 2 queued tails dropped, 64 borrowed remain
     let report=a.stop();
     assert_eq!(report.loaned,64);
     assert!(matches!(a.allocate(),Err(BufferContractError::OwnerStopping)));
     let join=std::thread::spawn(move||{drop(borrowed_rx);drop(borrowed_tx);});
     join.join().unwrap();
     assert!(repeat.batch_handles_released());
     assert!(first.batch_handles_released());
     assert!(a.quiesced());
     assert_eq!(a.report().free,96);
 }
 #[test]
 fn r1_owner_loan_stop_held_frozen_arc_last_clone_after_batch_fence() {
     let mut a=arena(8);let mut s=owner();let t=s.token();
     let f=frozen(&mut a,79,1);
     let orig=f.bytes().as_ptr();
     let driver_hold=f.clone();
     assert_eq!(orig,driver_hold.bytes().as_ptr()); // same payload, no memcpy
     s.offer_fresh(&t,f,MonoNs(0)).unwrap();
     let tx=ready(s.drain_tx(&t,MonoNs(0),Vec::with_capacity(1)));
     assert_eq!(tx.as_slice()[0].record.bytes().as_ptr(),orig);
     let fence=s.stop(&t).unwrap();
     assert_eq!(fence.canceled,0);
     assert_eq!(fence.borrowed().tx_batches,1);
     assert_eq!(a.stop().loaned,1);
     let held=std::thread::spawn(move||{
         assert_eq!(driver_hold.bytes(),&[79]);
         drop(driver_hold);
     });
     drop(tx);
     assert!(fence.batch_handles_released()); // only batch leases, not ALL slab clones
     held.join().unwrap();
     assert!(a.quiesced()); // true only once final frozen clone has returned
     assert_eq!(a.report().loaned,0);
     assert_eq!(s.stop(&t).unwrap().canceled,0);
 }
 #[test]
 fn r1_owner_loan_stop_old_generation_33_plus_new_first_fresh() {
     let mut a=arena(96);let mut s=owner();let old=s.token();
     for i in 0..33u8 {
         s.offer_fresh(&old,frozen(&mut a,i,1),MonoNs(0)).unwrap();
         s.offer_rx(&old,incoming(&mut a,i),0..1,MonoNs(0)).unwrap();
     }
     let tx32=ready(s.drain_tx(&old,MonoNs(0),Vec::with_capacity(32)));
     let rx32=ready(s.drain_rx(&old,MonoNs(0),Vec::with_capacity(32)));
     let tx1=ready(s.drain_tx(&old,MonoNs(0),Vec::with_capacity(32)));
     let rx1=ready(s.drain_rx(&old,MonoNs(0),Vec::with_capacity(32)));
     assert_eq!((tx32.len(),rx32.len(),tx1.len(),rx1.len()),(32,32,1,1));
     let cloned_driver=tx32.as_slice()[0].record.clone();
     let frozen_ptr=tx32.as_slice()[0].record.bytes().as_ptr();
     assert_eq!(cloned_driver.bytes().as_ptr(),frozen_ptr);
     let retired=rotate(&mut s,&old);
     assert_eq!(retired.borrowed(),Borrowed{tx_batches:2,rx_batches:2});
     let current=s.token();
     let stale=s.offer_repair(&old,cloned_driver.clone(),MonoNs(1));
     assert!(matches!(stale,Err((ScopedOfferError::Scope(ScopeError::Stale),_))));
     drop(stale);
     let cross=s.offer_repair(&current,cloned_driver.clone(),MonoNs(1));
     assert!(matches!(cross,Err((ScopedOfferError::Scope(ScopeError::LaneMismatch),_))));
     drop(cross);
     s.offer_repair(&current,frozen(&mut a,83,2),MonoNs(1)).unwrap();
     s.offer_fresh(&current,frozen(&mut a,84,2),MonoNs(1)).unwrap();
     let new_ready=ready(s.drain_tx(&current,MonoNs(1),Vec::with_capacity(2)));
     let order=s.checked_tx_ready(&current,&new_ready).unwrap();
     assert_eq!(order[0].kind,TxKind::Fresh);
     assert_eq!(order[0].record.bytes(),&[84]);
     assert_eq!(order[1].kind,TxKind::Repair);
     assert_eq!(s.checked_tx_ready(&current,&tx32).err(),Some(ScopeError::Stale));
     assert_eq!(s.checked_rx_ready(&current,&rx1).err(),Some(ScopeError::Stale));
     let r=s.stop(&current).unwrap();
     assert_eq!(s.stop(&current).unwrap().canceled,r.canceled);
     assert_eq!(r.borrowed(),Borrowed{tx_batches:1,rx_batches:0});
     let old_join=std::thread::spawn(move||{
         drop(rx1);drop(tx1);drop(rx32);drop(tx32);
     });
     old_join.join().unwrap();
     assert!(retired.batch_handles_released());
     assert_eq!(a.report().loaned,3); // external frozen driver-hold + two live current
     assert_eq!(cloned_driver.bytes().as_ptr(),frozen_ptr);
     drop(cloned_driver);drop(new_ready);
     assert!(r.batch_handles_released());
     assert_eq!(a.report().loaned,0);
 }
 #[test]
 fn r1_owner_loan_stop_bounded_full_return_backlog_two_generations() {
     // 32 TX+32 RX old, then 16 TX+16 RX current: all 96 slabs loaned.
     // ReturnPath has just 1 channel slot; other returns use bounded backlog.
     let mut a=arena(96);let mut s=owner();let old=s.token();
     for i in 0..32u8 {
         s.offer_fresh(&old,frozen(&mut a,i,1),MonoNs(0)).unwrap();
         s.offer_rx(&old,incoming(&mut a,i),0..1,MonoNs(0)).unwrap();
     }
     let old_tx=ready(s.drain_tx(&old,MonoNs(0),Vec::with_capacity(32)));
     let old_rx=ready(s.drain_rx(&old,MonoNs(0),Vec::with_capacity(32)));
     let retired=rotate(&mut s,&old);let current=s.token();
     for i in 0..16u8 {
         s.offer_fresh(&current,frozen(&mut a,i,2),MonoNs(1)).unwrap();
         s.offer_rx(&current,incoming(&mut a,i),0..1,MonoNs(1)).unwrap();
     }
     let now_tx=ready(s.drain_tx(&current,MonoNs(1),Vec::with_capacity(32)));
     let now_rx=ready(s.drain_rx(&current,MonoNs(1),Vec::with_capacity(32)));
     assert_eq!((now_tx.len(),now_rx.len()),(16,16));
     assert_eq!(a.report().loaned,96);
     assert!(matches!(a.allocate(),Err(BufferContractError::NoCapacity)));
     let fence=s.stop(&current).unwrap();
     assert_eq!(a.stop().loaned,96);
     let older=std::thread::spawn(move||{drop(old_tx);drop(old_rx);});
     let newer=std::thread::spawn(move||{drop(now_tx);drop(now_rx);});
     older.join().unwrap();newer.join().unwrap();
     assert!(retired.batch_handles_released());
     assert!(fence.batch_handles_released());
     assert!(a.quiesced());
     assert_eq!(a.report().free,96);
     assert_eq!(a.report().retired,0);
 }
 #[test]
 fn r1_owner_loan_stop_restart_aba_stale_token_cannot_reenter() {
     let mut a=arena(8);
     let mut first=owner();let old=first.token();
     first.offer_fresh(&old,frozen(&mut a,2,1),MonoNs(0)).unwrap();
     let held=ready(first.drain_tx(&old,MonoNs(0),Vec::with_capacity(1)));
     let retired=first.stop(&old).unwrap();
     assert_eq!(first.stop(&old).unwrap().canceled,0);
     drop(first);
     let mut restarted=owner();
     let tk=restarted.token();
     assert_eq!((tk.serial(),tk.owner_id()),(old.serial(),old.owner_id()));
     assert_eq!(restarted.checked_tx_ready(&tk,&held).err(),Some(ScopeError::Stale));
     let rejected=restarted.offer_fresh(&old,frozen(&mut a,3,1),MonoNs(0));
     assert!(matches!(rejected,Err((ScopedOfferError::Scope(ScopeError::Stale),_))));
     drop(rejected);
     restarted.offer_fresh(&tk,frozen(&mut a,4,1),MonoNs(0)).unwrap();
     let next=ready(restarted.drain_tx(&tk,MonoNs(0),Vec::with_capacity(1)));
     assert_eq!(restarted.checked_tx_ready(&tk,&next).unwrap()[0].record.bytes(),&[4]);
     drop(held);drop(next);
     assert!(retired.batch_handles_released());
     assert_eq!(a.report().loaned,0);
 }
