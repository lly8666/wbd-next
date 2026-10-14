//! R1-M1-WAKE-STOP-002: one-consumer, bounded std-only wake adapter.
 //! This is *not* rtrb/SPSC/eventfd or a production dataplane.
 //! The producer publishes to a fixed sync_channel before using armed.swap.
 //! The owner drains existing inputs before arming, then checks again before
 //! parking. unpark tokens cover publish-before-park without a lost wake.
 #![forbid(unsafe_code)]
 
 use std::sync::{
     atomic::{AtomicBool, AtomicUsize, Ordering::SeqCst},
     mpsc::{self, Receiver, SyncSender, TryRecvError, TrySendError},
     Arc, OnceLock,
 };
 use std::thread::{self, Thread};
 use std::time::Duration;
 use wbd_types::MonoNs;
 use crate::memory::Arena;
 
 pub struct WakeGate {
     armed: AtomicBool,
     stopping: AtomicBool,
     inflight: AtomicUsize,
     target: OnceLock<Thread>,
 }
 impl WakeGate {
     fn new() -> Self {
         Self { armed: AtomicBool::new(false),
             stopping: AtomicBool::new(false),
             inflight: AtomicUsize::new(0), target: OnceLock::new() }
     }
     /// Only the owner thread may bind/park. Early publications are not
     /// missed because the first queue inspection occurs after binding.
     fn bind_current(&self) -> bool {
         let this = thread::current();
         self.target.get_or_init(|| this.clone()).id() == this.id()
     }
     pub fn notify(&self) {
         if self.armed.swap(false, SeqCst) {
             if let Some(t) = self.target.get() { t.unpark(); }
         }
     }
     pub fn request_stop(&self) {
         if !self.stopping.swap(true, SeqCst) { self.notify(); }
     }
     pub fn is_stopping(&self) -> bool { self.stopping.load(SeqCst) }
     fn disarm(&self) { self.armed.store(false, SeqCst); }
 }
 
 #[derive(Debug)]
 pub enum PushError<T> { Full(T), Stopping(T), Disconnected(T) }
 #[derive(Clone, Copy, Debug, Eq, PartialEq)]
 pub enum Class { Fresh, Repair }
 pub struct OwnerProducer<T> {
     tx: SyncSender<T>,
     gate: Arc<WakeGate>,
 }
 impl<T> OwnerProducer<T> {
     pub fn try_push(&self, item: T) -> Result<(), PushError<T>> {
         // A producer already inside try_push at the stop linearization
         // point remains visible to the drain via the inflight counter.
         self.gate.inflight.fetch_add(1, SeqCst);
         if self.gate.is_stopping() {
             self.gate.inflight.fetch_sub(1, SeqCst);
             return Err(PushError::Stopping(item));
         }
         let result = match self.tx.try_send(item) {
             Ok(()) => { self.gate.notify(); Ok(()) }
             Err(TrySendError::Full(item)) => Err(PushError::Full(item)),
             Err(TrySendError::Disconnected(item)) => Err(PushError::Disconnected(item)),
         };
         self.gate.inflight.fetch_sub(1, SeqCst);
         if self.gate.is_stopping() { self.gate.notify(); }
         result
     }
     pub fn stop(&self) { self.gate.request_stop(); }
     pub fn gate(&self) -> Arc<WakeGate> { Arc::clone(&self.gate) }
 }
 
 #[derive(Debug)]
 pub enum WakeEvent<T> { Ready(Class, T), Returned, Deadline, Stopped }
 #[derive(Clone, Copy, Debug, Eq, PartialEq)]
 pub enum StopProgress {
     Quiesced,
     Pending { loans: usize, inflight: usize },
 }
 pub struct OwnerConsumer<T> {
     ready: Receiver<T>,
     repair: Option<Receiver<T>>,
     gate: Arc<WakeGate>,
 }
 impl<T> OwnerConsumer<T> {
     pub fn bind_current(&self) -> bool { self.gate.bind_current() }
     pub fn gate(&self) -> Arc<WakeGate> { Arc::clone(&self.gate) }
     fn inspect<C: Fn() -> MonoNs, R: FnMut() -> bool>(
         &mut self, now: &C, deadline: Option<MonoNs>, returns: &mut R
     ) -> Option<WakeEvent<T>> {
         // Stop wins at the observable event boundary: after stop no new
         // Ready value escapes this loop. Caller must cancel retained values.
         if self.gate.is_stopping() { return Some(WakeEvent::Stopped); }
         let fresh_closed = match self.ready.try_recv() {
             Ok(v) => {
                 if self.gate.is_stopping() { drop(v); return Some(WakeEvent::Stopped); }
                 return Some(WakeEvent::Ready(Class::Fresh, v));
             }
             Err(TryRecvError::Disconnected) => true,
             Err(TryRecvError::Empty) => false,
         };
         let repair_closed = match self.repair.as_ref() {
             Some(rx) => match rx.try_recv() {
                 Ok(v) => {
                     if self.gate.is_stopping() { drop(v); return Some(WakeEvent::Stopped); }
                     return Some(WakeEvent::Ready(Class::Repair, v));
                 }
                 Err(TryRecvError::Disconnected) => true,
                 Err(TryRecvError::Empty) => false,
             },
             None => true,
         };
         if fresh_closed && repair_closed {
             self.gate.request_stop();
             return Some(WakeEvent::Stopped);
         }
         if returns() { return Some(WakeEvent::Returned); }
         if deadline.is_some_and(|d| now().0 >= d.0) {
             return Some(WakeEvent::Deadline);
         }
         None
     }
     fn wait_inner<C, R, B, A, P>(
         &mut self, now: C, deadline: Option<MonoNs>, mut returns: R,
         mut before_arm: B, mut after_arm: A, mut before_park: P
     ) -> WakeEvent<T>
     where C: Fn() -> MonoNs, R: FnMut() -> bool,
           B: FnMut(), A: FnMut(), P: FnMut() {
         assert!(self.gate.bind_current(), "owner consumer cannot migrate threads");
         loop {
             // Ready is checked first, never wait for a batch to fill.
             if let Some(v) = self.inspect(&now, deadline, &mut returns) { return v; }
             before_arm();
             self.gate.armed.store(true, SeqCst);
             after_arm();
             // Critical second inspection of BOTH data classes, returns,
             // stop and fake monotonic deadline after arming.
             if let Some(v) = self.inspect(&now, deadline, &mut returns) {
                 self.gate.disarm();
                 return v;
             }
             before_park();
             match deadline {
                 None => thread::park(),
                 Some(d) => {
                     let remaining = d.0.saturating_sub(now().0);
                     if remaining > 0 { thread::park_timeout(Duration::from_nanos(remaining)); }
                 }
             }
             self.gate.disarm();
             // Spurious wake is fine: inspect everything again.
         }
     }
     pub fn wait<C, R>(&mut self, now: C, deadline: Option<MonoNs>, returns: R)
         -> WakeEvent<T>
     where C: Fn() -> MonoNs, R: FnMut() -> bool {
         self.wait_inner(now, deadline, returns, ||{}, ||{}, ||{})
     }
     /// Explicit nonblocking stop: drop queued handles, then query arena.
     /// Never report quiesced while an in-flight producer or loan remains.
     /// This avoids claiming that kernel/driver borrows have been released.
     pub fn stop_step(&mut self, arena: &mut Arena) -> StopProgress {
         assert!(self.gate.bind_current(), "owner consumer cannot migrate threads");
         self.gate.request_stop();
         while let Ok(item) = self.ready.try_recv() { drop(item); }
         if let Some(repair) = self.repair.as_ref() {
             while let Ok(item) = repair.try_recv() { drop(item); }
         }
         let status = arena.stop();
         let inflight = self.gate.inflight.load(SeqCst);
         if status.loaned == 0 && inflight == 0 { StopProgress::Quiesced }
         else { StopProgress::Pending {loans:status.loaned, inflight} }
     }
     /// At most one bounded park. The caller re-invokes this when still
     /// pending, rather than spinning or waiting forever for a driver loan.
     /// A published return wakes this path even with an already stopped owner.
     pub fn wait_return_once<C: Fn() -> MonoNs>(
         &mut self, arena: &mut Arena, now: C, hard_deadline: MonoNs
     ) -> StopProgress {
         let state = self.stop_step(arena);
         if state == StopProgress::Quiesced { return state; }
         self.gate.armed.store(true, SeqCst);
         let again = self.stop_step(arena);
         if again == StopProgress::Quiesced {
             self.gate.disarm();
             return again;
         }
         let remaining = hard_deadline.0.saturating_sub(now().0);
         if remaining > 0 { thread::park_timeout(Duration::from_nanos(remaining)); }
         self.gate.disarm();
         self.stop_step(arena)
     }
 }
 /// A single class (for RX/feedback/returns); only the returned producer
 /// owns the publishing endpoint. The consumer is bound to one OS thread.
 pub fn single<T>(capacity: usize) -> Option<(OwnerProducer<T>, OwnerConsumer<T>)> {
     if !(1..=8192).contains(&capacity) { return None; }
     let gate = Arc::new(WakeGate::new());
     let (tx, ready) = mpsc::sync_channel(capacity);
     Some((OwnerProducer { tx, gate: Arc::clone(&gate) },
         OwnerConsumer { ready, repair: None, gate }))
 }
 /// Separate bounded fresh and repair slots. Full repair queue cannot deny
 /// a fresh item a slot, and a wake always inspects fresh first.
 pub fn tx_pair<T>(
     fresh_capacity: usize, repair_capacity: usize
 ) -> Option<((OwnerProducer<T>, OwnerProducer<T>), OwnerConsumer<T>)> {
     if !(1..=8192).contains(&fresh_capacity)
         || !(1..=8192).contains(&repair_capacity) { return None; }
     let gate = Arc::new(WakeGate::new());
     let (fresh_tx, ready) = mpsc::sync_channel(fresh_capacity);
     let (repair_tx, repair) = mpsc::sync_channel(repair_capacity);
     Some(((OwnerProducer { tx:fresh_tx, gate:Arc::clone(&gate) },
            OwnerProducer { tx:repair_tx, gate:Arc::clone(&gate) }),
         OwnerConsumer { ready, repair:Some(repair), gate }))
 }
 
 #[cfg(test)]
 mod tests {
     use super::*;
     use std::sync::{Barrier, mpsc, atomic::{AtomicU64, Ordering}};
     use wbd_types::{LaneKey, RecordPn, SeqOffset, TunnelKey};
     use wbd_types::buffer_contract::{FrozenMetadata, FrozenRecordHandle, UniqueSealable};
 
     fn meta() -> FrozenMetadata {
         FrozenMetadata {lane:LaneKey{
             tunnel:TunnelKey{slot:1,generation:1},slot:1,generation:1},
             pn:RecordPn(7),seq:SeqOffset(9),carrier_snapshot:3}
     }
     fn arena(n: usize) -> Arena { Arena::new(71,n,256,1,100_000).unwrap() }
     #[test]
     fn r1_wake_idle_single_packet_push_before_arm_r01() {
         let (sender, mut owner) = single::<u8>(1).unwrap();
         sender.try_push(42).unwrap(); // publication precedes thread binding
         let join=thread::spawn(move || {
             match owner.wait(||MonoNs(0),None,||false) {
                 WakeEvent::Ready(Class::Fresh,42) => (),
                 _ => panic!("first packet not ready"),
             }
         });
         join.join().unwrap();
     }
     #[test]
     fn r1_wake_publish_during_armed_recheck_r01() {
         let (sender,mut owner)=single::<u8>(1).unwrap();
         let go=Arc::new(Barrier::new(2));
         let done=Arc::new(Barrier::new(2));
         let go2=Arc::clone(&go);
         let done2=Arc::clone(&done);
         let producer=thread::spawn(move || {
             go2.wait();
             sender.try_push(5).unwrap(); // after armed, before second check
             done2.wait();
         });
         let outcome=owner.wait_inner(||MonoNs(0),None,||false,||{},||{
             go.wait();done.wait();
         },||{});
         assert!(matches!(outcome,WakeEvent::Ready(Class::Fresh,5)));
         producer.join().unwrap();
     }
     #[test]
     fn r1_wake_token_publish_at_park_boundary_r01() {
         let (sender,mut owner)=single::<u8>(1).unwrap();
         let go=Arc::new(Barrier::new(2));
         let go2=Arc::clone(&go);
         let producer=thread::spawn(move || {
             go2.wait();
             sender.try_push(11).unwrap(); // before/during/after park permitted
         });
         let mut once=true;
         let event=owner.wait_inner(||MonoNs(0),None,||false,||{},||{},||{
             if once {once=false;go.wait();}
         });
         assert!(matches!(event,WakeEvent::Ready(Class::Fresh,11)));
         producer.join().unwrap();
     }
     #[test]
     fn r1_wake_full_repair_does_not_block_fresh_r02() {
         let ((fresh,repair),mut owner)=tx_pair::<u8>(1,1).unwrap();
         repair.try_push(8).unwrap();
         assert!(matches!(repair.try_push(9),Err(PushError::Full(9))));
         fresh.try_push(3).unwrap();
         assert!(matches!(owner.wait(||MonoNs(0),None,||false),
             WakeEvent::Ready(Class::Fresh,3)));
         assert!(matches!(owner.wait(||MonoNs(0),None,||false),
             WakeEvent::Ready(Class::Repair,8)));
     }
     #[test]
     fn r1_wake_stop_before_delivery_and_reject_late_offer_r02() {
         let (sender,mut owner)=single::<u8>(1).unwrap();
         sender.try_push(1).unwrap();
         sender.stop();
         assert!(matches!(sender.try_push(2),Err(PushError::Stopping(2))));
         assert!(matches!(owner.wait(||MonoNs(0),None,||false),
             WakeEvent::Stopped));
         let mut a=arena(1);
         assert_eq!(owner.stop_step(&mut a),StopProgress::Quiesced);
     }
     #[test]
     fn r1_wake_stop_with_full_return_backlog_and_last_frozen_loan_m01() {
         let (sender,mut owner)=single::<wbd_types::BufferKey>(1).unwrap();
         let mut a=arena(3);
         assert!(a.register_wake(owner.gate()));
         let owned=(0..3).map(|_|a.allocate().unwrap()
             .freeze(0..1,meta()).unwrap()).collect::<Vec<_>>();
         let one=owned[0].clone();
         let two=owned[1].clone();
         let three=owned[2].clone();
         let key=one.origin().key;
         let start=Arc::new(Barrier::new(2));
         let start2=Arc::clone(&start);
         let producer=thread::spawn(move || {
             start2.wait();
             // An arriving message is not allowed to dispatch after stop.
             let _=sender.try_push(key);
             drop(one); drop(two); drop(three);
         });
         owner.gate().request_stop();
         start.wait();
         assert!(matches!(owner.wait(||MonoNs(0),None,||false),WakeEvent::Stopped));
         assert!(matches!(owner.stop_step(&mut a),
             StopProgress::Pending {loans:3,..}));
         drop(owned); // release final refs; return queue capacity one
         producer.join().unwrap();
         assert_eq!(owner.stop_step(&mut a),StopProgress::Quiesced);
         assert_eq!(a.report().free,3);
         assert!(a.quiesced());
     }
     #[test]
     fn r1_wake_return_after_park_wakes_stopped_owner_m01() {
         let (sender,mut owner)=single::<u8>(1).unwrap();
         let mut a=arena(1);
         a.register_wake(owner.gate());
         let frozen=a.allocate().unwrap().freeze(0..1,meta()).unwrap();
         let gate=sender.gate();
         let (go_tx,go_rx)=mpsc::sync_channel::<()>(0);
         let (done_tx,done_rx)=mpsc::sync_channel::<()>(0);
         let release=thread::spawn(move || {
             go_rx.recv().unwrap();
             drop(frozen);
             done_tx.send(()).unwrap();
         });
         sender.stop();
         assert!(matches!(owner.stop_step(&mut a),
             StopProgress::Pending {loans:1,..}));
         // The release may happen before the owner parks; a retained
         // unpark token AND the second return check must both be safe.
         go_tx.send(()).unwrap();
         let outcome=owner.wait_return_once(&mut a,||MonoNs(0),MonoNs(50_000_000));
         done_rx.recv().unwrap();
         release.join().unwrap();
         let result=if outcome==StopProgress::Quiesced {outcome}
             else {owner.stop_step(&mut a)};
         assert_eq!(result,StopProgress::Quiesced);
         assert!(gate.is_stopping());
     }
     #[test]
     fn r1_wake_fake_monotonic_deadline_recheck_r02() {
         let (_sender,mut owner)=single::<u8>(1).unwrap();
         let ns=Arc::new(AtomicU64::new(0));
         let ns2=Arc::clone(&ns);
         let gate=owner.gate();
         let go=Arc::new(Barrier::new(2));
         let go2=Arc::clone(&go);
         let clock=move||MonoNs(ns2.load(Ordering::SeqCst));
         let advance=thread::spawn(move||{
             go2.wait();
             ns.store(1_000_000,Ordering::SeqCst);
             gate.notify();
         });
         let mut once=true;
         let event=owner.wait_inner(clock,Some(MonoNs(1_000_000)),||false,
             ||{},||{
                 if once {once=false;go.wait();}
             },||{});
         assert!(matches!(event,WakeEvent::Deadline));
         advance.join().unwrap();
     }
 }
