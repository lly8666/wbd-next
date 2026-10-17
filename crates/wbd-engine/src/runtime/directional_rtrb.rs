//! M1-012: exact-rtrb 0.3.2 safe single-producer/single-consumer transport.
 //! Enabled ONLY when M0's shared Cargo pin and m1_rtrb compile selection
 //! are present. No chunk API, no unsafe, no cloned producer, no mutex on
 //! producer/consumer and no allocation on push/pop.
 #![forbid(unsafe_code)]
 use std::{
     cell::RefCell, ops::Range,
     sync::{Arc,atomic::{AtomicBool,AtomicUsize,Ordering::SeqCst}},
 };
 use wbd_types::{LaneKey,MonoNs};
 use wbd_types::buffer_contract::FrozenRecordHandle;
 use crate::memory::{FrozenRecord,UniqueBuffer};
 use rtrb::{RingBuffer,Producer,Consumer,PushError,PopError};
 use super::{TxKind,wake::{self,WakeGate,WakeEvent,Class}};

 #[derive(Clone,Copy,Debug,Eq,PartialEq)]
 pub enum Direction {Tx,Rx}
 struct Epoch {
     owner_id:u64,serial:u32,lane:LaneKey,
     stopping:AtomicBool,consumer_alive:AtomicBool,
     publishing:AtomicUsize,
 }
 #[derive(Clone)]
 pub struct DirectionToken(Arc<Epoch>);
 impl DirectionToken {
     pub fn owner_id(&self)->u64{self.0.owner_id}
     pub fn serial(&self)->u32{self.0.serial}
     pub fn lane(&self)->LaneKey{self.0.lane}
 }
 #[derive(Clone,Copy,Debug,Eq,PartialEq)]
 pub enum DirectionError {Stale,Stopped,WrongLane,Full,Disconnected}
 #[derive(Debug)]
 pub struct TxIngress {
     pub kind:TxKind,pub record:FrozenRecord,
     pub offered_at:MonoNs,pub eligible_at:MonoNs,
 }
 #[derive(Debug)]
 pub struct RxIngress {
     pub buffer:UniqueBuffer,pub wire:Range<usize>,
     pub lane_hint:Option<LaneKey>,pub offered_at:MonoNs,
 }
 /// Only ONE producer endpoint. RefCell preserves the frozen &self API
 /// without synchronization: !Sync prevents concurrent sender sharing.
 pub struct DirectionProducer<T> {
     writer:RefCell<Producer<T>>,
     epoch:Arc<Epoch>,direction:Direction,gate:Arc<WakeGate>,
 }
 /// Only ONE consumer endpoint. Different TX and RX consumers can run on
 /// independent OS threads. No Mutex<Entry> is shared between directions.
 pub struct DirectionConsumer<T> {
     reader:Consumer<T>,epoch:Arc<Epoch>,
     direction:Direction,gate:Arc<WakeGate>,canceled:usize,
 }
 impl<T> DirectionProducer<T> {
     pub fn token(&self)->DirectionToken{DirectionToken(Arc::clone(&self.epoch))}
     pub fn direction(&self)->Direction{self.direction}
     fn check(&self,token:&DirectionToken)->Result<(),DirectionError>{
         if !Arc::ptr_eq(&self.epoch,&token.0){return Err(DirectionError::Stale);}
         if self.epoch.stopping.load(SeqCst){return Err(DirectionError::Stopped);}
         if !self.epoch.consumer_alive.load(SeqCst){return Err(DirectionError::Disconnected);}
         Ok(())
     }
     pub fn try_publish(&self,token:&DirectionToken,item:T)
         ->Result<(),(DirectionError,T)>{
         // Linearize STOP vs producer admission: STOP may still follow
         // successful publication but the owner then drains or retains it.
         self.epoch.publishing.fetch_add(1,SeqCst);
         if let Err(e)=self.check(token){
             self.epoch.publishing.fetch_sub(1,SeqCst);
             return Err((e,item));
         }
         let answer=self.writer.borrow_mut().push(item).map_err(|err|match err{
             PushError::Full(item)=>(DirectionError::Full,item),
         });
         if answer.is_ok(){self.gate.notify();}
         self.epoch.publishing.fetch_sub(1,SeqCst);
         if self.epoch.stopping.load(SeqCst){self.gate.notify();}
         answer
     }
     pub fn stop(&self){
         self.epoch.stopping.store(true,SeqCst);
         self.gate.request_stop();
     }
 }
 impl<T> DirectionConsumer<T> {
     pub fn token(&self)->DirectionToken{DirectionToken(Arc::clone(&self.epoch))}
     pub fn direction(&self)->Direction{self.direction}
     pub fn check_current(&self,token:&DirectionToken)->Result<(),DirectionError>{
         if !Arc::ptr_eq(&self.epoch,&token.0){return Err(DirectionError::Stale);}
         if self.epoch.stopping.load(SeqCst){return Err(DirectionError::Stopped);}
         Ok(())
     }
     pub fn drain_ready(&mut self,storage:&mut Vec<T>)->usize {
         if !self.gate.bind_current(){return 0;}
         if self.epoch.stopping.load(SeqCst){return 0;}
         let slots=32usize.min(storage.capacity().saturating_sub(storage.len()));
         let mut delivered=0;
         while delivered<slots{
             let Ok(item)=self.reader.pop() else{break};
             if self.epoch.stopping.load(SeqCst){drop(item);break;}
             storage.push(item);delivered+=1;
         }
         delivered
     }
     /// The exact same SeqCst arm/second-check/Stop protocol used by old
     /// WakeGate, with rtrb pop as the ready probe. Std thread park is NOT
     /// qualified Linux eventfd/Windows notification. External deadlines
     /// and return signals are hints; no driver syscall occurs in this API.
     pub fn wait_input<C,R>(&mut self,now:C,deadline:Option<MonoNs>,mut returns:R)
         ->WakeEvent<T>
     where C:Fn()->MonoNs,R:FnMut()->bool{
         if !self.gate.bind_current(){return WakeEvent::Stopped;}
         let epoch=Arc::clone(&self.epoch);
         let gate=Arc::clone(&self.gate);
         gate.wait_scheduled(now,|at|{
             if epoch.stopping.load(SeqCst){return (None,None);}
             match self.reader.pop(){
                 Ok(item)=>{
                     if epoch.stopping.load(SeqCst) {
                         drop(item);return (None,None);
                     }
                     return (Some(WakeEvent::Ready(Class::Fresh,item)),None);
                 }
                 Err(PopError::Empty)=>{}
             }
             if returns() {return (Some(WakeEvent::Returned),None);}
             if deadline.is_some_and(|d|at.0>=d.0){
                 return (Some(WakeEvent::Deadline),None);
             }
             (None,deadline)
         }).unwrap_or(WakeEvent::Stopped)
     }
     pub fn stop(&mut self)->(usize,usize){
         self.epoch.stopping.store(true,SeqCst);
         self.gate.request_stop();
         while let Ok(item)=self.reader.pop(){
             drop(item);self.canceled=self.canceled.saturating_add(1);
         }
         let mut inflight=self.epoch.publishing.load(SeqCst);
         if inflight==0{
             // This is the second drain after observing no publishers.
             while let Ok(item)=self.reader.pop(){
                 drop(item);self.canceled=self.canceled.saturating_add(1);
             }
             inflight=self.epoch.publishing.load(SeqCst);
         }
         (self.canceled,inflight)
     }
 }
 impl<T> Drop for DirectionConsumer<T>{
     fn drop(&mut self){
         self.epoch.stopping.store(true,SeqCst);
         self.epoch.consumer_alive.store(false,SeqCst);
         self.gate.request_stop();
         while let Ok(item)=self.reader.pop(){drop(item);}
     }
 }
 fn pair<T>(direction:Direction,owner_id:u64,serial:u32,lane:LaneKey,
     capacity:usize)->Option<(DirectionProducer<T>,DirectionConsumer<T>)>{
     if owner_id==0||serial==0||lane.generation==0||
         lane.tunnel.generation==0||!(1..=8192).contains(&capacity){return None;}
     let (writer,reader)=RingBuffer::<T>::new(capacity);
     let epoch=Arc::new(Epoch{
         owner_id,serial,lane,
         stopping:AtomicBool::new(false),consumer_alive:AtomicBool::new(true),
         publishing:AtomicUsize::new(0),
     });
     let gate=Arc::new(WakeGate::new());
     Some((
         DirectionProducer{writer:RefCell::new(writer),
             epoch:Arc::clone(&epoch),direction,gate:Arc::clone(&gate)},
         DirectionConsumer{reader,epoch,direction,gate,canceled:0},
     ))
 }
 pub fn split_tx(owner_id:u64,serial:u32,lane:LaneKey,capacity:usize)
     ->Option<(DirectionProducer<TxIngress>,DirectionConsumer<TxIngress>)>{
     pair(Direction::Tx,owner_id,serial,lane,capacity)
 }
 pub fn split_rx(owner_id:u64,serial:u32,lane:LaneKey,capacity:usize)
     ->Option<(DirectionProducer<RxIngress>,DirectionConsumer<RxIngress>)>{
     pair(Direction::Rx,owner_id,serial,lane,capacity)
 }
 impl DirectionProducer<TxIngress>{
     pub fn publish_tx(&self,token:&DirectionToken,item:TxIngress)
         ->Result<(),(DirectionError,TxIngress)>{
         if item.record.metadata().lane!=self.epoch.lane {
             return Err((DirectionError::WrongLane,item));
         }
         self.try_publish(token,item)
     }
 }
 #[cfg(test)]
 mod tests {
     use super::*;
     use crate::memory::Arena;
     use wbd_types::{TunnelKey,RecordPn,SeqOffset};
     use wbd_types::buffer_contract::{UniqueSealable,FrozenMetadata};
     fn lane(gen:u32)->LaneKey{
         LaneKey{tunnel:TunnelKey{slot:900,generation:gen},slot:1,generation:gen}
     }
     fn arena()->Arena{Arena::new(224,128,256,1,100000).unwrap()}
     fn frozen(a:&mut Arena,b:u8,gen:u32)->FrozenRecord{
         let mut u=a.allocate().unwrap();u.writable()[0]=b;
         u.freeze(0..1,FrozenMetadata{lane:lane(gen),
             pn:RecordPn(b as u64),seq:SeqOffset(b as u64),
             carrier_snapshot:1}).unwrap()
     }
     fn tx(a:&mut Arena,b:u8,gen:u32)->TxIngress {
         TxIngress{kind:TxKind::Fresh,record:frozen(a,b,gen),
             offered_at:MonoNs(0),eligible_at:MonoNs(0)}
     }
     fn rx(a:&mut Arena,b:u8)->RxIngress {
         let mut u=a.allocate().unwrap();u.writable()[0]=b;
         RxIngress{buffer:u,wire:0..1,lane_hint:None,offered_at:MonoNs(0)}
     }
     #[test]
     fn r1_rtrb_direction_r01_zero_one_32_33_no_batch_fill(){
         let mut a=arena();
         let(p,mut c)=split_tx(2,1,lane(1),64).unwrap();
         let t=p.token();let mut out=Vec::with_capacity(64);
         assert_eq!(c.drain_ready(&mut out),0);
         p.publish_tx(&t,tx(&mut a,1,1)).unwrap();
         assert_eq!(c.drain_ready(&mut out),1);
         assert_eq!(out[0].record.bytes(),&[1]);
         out.clear();
         for i in 0..33u8 {p.publish_tx(&t,tx(&mut a,i,1)).unwrap();}
         assert_eq!(c.drain_ready(&mut out),32);
         assert_eq!(c.drain_ready(&mut out),1);
         assert_eq!(out.len(),33);
         assert_eq!(out[32].record.bytes(),&[32]);
         drop(out);assert_eq!(a.report().loaned,0);
     }
     #[test]
     fn r1_rtrb_direction_r01_full_returns_original_unique_and_no_loss(){
         let mut a=arena();let(p,mut c)=split_rx(2,1,lane(1),1).unwrap();
         let t=p.token();
         p.try_publish(&t,rx(&mut a,1)).unwrap();
         let second=rx(&mut a,2);
         let origin=second.buffer.origin();
         let returned=p.try_publish(&t,second);
         assert!(matches!(returned,Err((DirectionError::Full,_))));
         let recovered=returned.err().unwrap().1;
         assert_eq!(recovered.buffer.origin(),origin);
         assert_eq!(a.report().loaned,2);
         drop(recovered);
         let mut out=Vec::with_capacity(1);
         assert_eq!(c.drain_ready(&mut out),1);
         assert_eq!(out[0].buffer.writable()[0],1);
         drop(out);assert_eq!(a.report().loaned,0);
     }
     #[test]
     fn r1_rtrb_direction_b04_stop_late_lease_epoch_aba(){
         let mut a=arena();
         let(p,mut c)=split_tx(7,1,lane(1),2).unwrap();
         let t=p.token();
         p.publish_tx(&t,tx(&mut a,1,1)).unwrap();
         p.publish_tx(&t,tx(&mut a,2,1)).unwrap();
         let mut held=Vec::with_capacity(1);
         assert_eq!(c.drain_ready(&mut held),1);
         assert_eq!(c.stop(),(1,0));
         assert_eq!(c.stop(),(1,0));
         assert_eq!(a.report().loaned,1);
         let(future,mut next)=split_tx(7,1,lane(1),2).unwrap();
         let current=future.token();
         let rejected=future.publish_tx(&t,tx(&mut a,3,1));
         assert_eq!(rejected.err().unwrap().0,DirectionError::Stale);
         future.publish_tx(&current,tx(&mut a,4,1)).unwrap();
         let mut out=Vec::with_capacity(1);
         assert_eq!(next.drain_ready(&mut out),1);
         assert_eq!(out[0].record.bytes(),&[4]);
         let late=std::thread::spawn(move||drop(held));
         late.join().unwrap();
         assert_eq!(a.report().loaned,1);
         drop(out);assert_eq!(a.report().loaned,0);
     }
     #[test]
     fn r1_rtrb_direction_r02_sparse_cross_thread_and_dual_rx_tx(){
         let mut a=arena();
         let(txp,mut txc)=split_tx(8,1,lane(1),2).unwrap();
         let(rxp,mut rxc)=split_rx(8,1,lane(1),2).unwrap();
         let tt=txp.token();let rt=rxp.token();
         let ti=tx(&mut a,10,1);let ri=rx(&mut a,11);
         let thread_tx=std::thread::spawn(move||{
             match txc.wait_input(||MonoNs(0),None,||false){
                 WakeEvent::Ready(_,value)=>assert_eq!(value.record.bytes(),&[10]),
                 _=>panic!("TX did not wake"),
             }
         });
         let thread_rx=std::thread::spawn(move||{
             match rxc.wait_input(||MonoNs(0),None,||false){
                 WakeEvent::Ready(_,mut value)=>assert_eq!(value.buffer.writable()[0],11),
                 _=>panic!("RX did not wake"),
             }
         });
         txp.publish_tx(&tt,ti).unwrap();
         rxp.try_publish(&rt,ri).unwrap();
         thread_tx.join().unwrap();thread_rx.join().unwrap();
         assert_eq!(a.report().loaned,0);
     }
     #[test]
     fn r1_rtrb_direction_g01_old_held_rx_new_first_and_stale_reject(){
         let mut a=arena();
         let(p,mut c)=split_rx(7,1,lane(1),32).unwrap();
         let t=p.token();
         for i in 0..32u8{p.try_publish(&t,rx(&mut a,i)).unwrap();}
         let mut old=Vec::with_capacity(32);
         assert_eq!(c.drain_ready(&mut old),32);
         assert_eq!(c.stop(),(0,0));
         let(q,mut d)=split_rx(7,2,lane(2),32).unwrap();
         let nt=q.token();
         let rejected=q.try_publish(&t,rx(&mut a,90));
         assert_eq!(rejected.err().unwrap().0,DirectionError::Stale);
         q.try_publish(&nt,rx(&mut a,91)).unwrap();
         let mut out=Vec::with_capacity(1);
         assert_eq!(d.drain_ready(&mut out),1);
         assert_eq!(a.report().loaned,33);
         drop(old);drop(out);
         assert_eq!(a.report().loaned,0);
     }
     #[test]
     fn r1_rtrb_direction_r02_concurrent_publish_stop_returns_all_original_loans(){
         use std::sync::{Arc,Barrier};
         let mut a=arena();
         let (producer,mut consumer)=split_rx(17,1,lane(1),16).unwrap();
         let token=producer.token();
         let pending=(0..33u8).map(|v|rx(&mut a,v)).collect::<Vec<_>>();
         let gate=Arc::new(Barrier::new(2));
         let worker_gate=Arc::clone(&gate);
         let worker=std::thread::spawn(move||{
             worker_gate.wait();
             let mut accepted=0;
             let mut returned=0;
             for item in pending {
                 match producer.try_publish(&token,item){
                     Ok(())=>accepted+=1,
                     Err((reason,item))=>{
                         assert!(matches!(reason,
                             DirectionError::Stopped|DirectionError::Full));
                         drop(item);returned+=1;
                     }
                 }
             }
             (accepted,returned)
         });
         gate.wait();
         let (_,inflight)=consumer.stop();
         assert!(inflight<=1,"single producer inflight bounded");
         let (accepted,returned)=worker.join().unwrap();
         assert_eq!(accepted+returned,33);
         let (canceled,inflight)=consumer.stop();
         assert_eq!(inflight,0);
         assert_eq!(canceled,accepted);
         assert_eq!(a.report().loaned,0);
     }

 }
