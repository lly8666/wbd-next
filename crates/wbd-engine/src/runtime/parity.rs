//! M1 R1 strictly bounded owner-local FEC parity READY handles.
 //! The FEC encoder determines eligibility; this module never encodes.
 //! Only handle metadata is moved/sorted, never ciphertext bytes.
 #![forbid(unsafe_code)]
 use std::collections::VecDeque;
 use wbd_types::MonoNs;
 use wbd_types::buffer_contract::FrozenRecordHandle;
 use crate::memory::FrozenRecord;
 use super::{OfferError, QueueLimits};

 struct Pending {
     record: FrozenRecord,
     ready_at: MonoNs,
     expiry: MonoNs,
     wire_bytes: usize,
 }
 /// Ready times are kept sorted; stable insertion order for equal times.
 /// This bounded O(slots) insertion is owner-local and confined to optional
 /// parity, NOT the Normal/off hot path or a new dynamic thread/queue.
 pub struct ParityReady {
     pending: VecDeque<Pending>,
     limit: QueueLimits,
     charged_bytes: usize,
     expired: usize,
 }
 impl ParityReady {
     pub fn new(limit: QueueLimits) -> Option<Self> {
         if !limit.valid() { return None; }
         Some(Self {
             pending: VecDeque::with_capacity(limit.slots),
             limit, charged_bytes: 0, expired: 0,
         })
     }
     pub fn offer(
         &mut self, record: FrozenRecord, now: MonoNs, eligible_at: MonoNs,
     ) -> Result<(), (OfferError, FrozenRecord)> {
         let bytes = record.bytes().len();
         // Only sweep the bounded parity queue on admission pressure;
         // no O(slots) scan for every ready FEC record.
         if self.pending.len() >= self.limit.slots
             || bytes > self.limit.bytes.saturating_sub(self.charged_bytes) {
             self.expire(now);
         }
         let expiry = MonoNs(now.0.saturating_add(self.limit.max_age_ns));
         // FEC parity cannot be retained beyond its queue's age budget;
         // callers choose an earlier eligible deadline or must drop.
         if eligible_at.0 < now.0 || eligible_at.0 > expiry.0 {
             return Err((OfferError::InvalidWindow, record));
         }
         if self.pending.len() >= self.limit.slots {
             return Err((OfferError::Full, record));
         }
         if bytes > self.limit.bytes.saturating_sub(self.charged_bytes) {
             return Err((OfferError::ByteBudget, record));
         }
         let index = self.pending.iter()
             .position(|item| item.ready_at.0 > eligible_at.0)
             .unwrap_or(self.pending.len());
         self.pending.insert(index, Pending {
             record, ready_at: eligible_at, expiry, wire_bytes: bytes,
         });
         self.charged_bytes += bytes;
         Ok(())
     }
     /// Independently expire ANY overdue entry, even if a later-ready
     /// head precedes it, without ever preserving an expired ciphertext.
     pub fn expire(&mut self, now: MonoNs) -> usize {
         let before = self.pending.len();
         self.pending.retain(|item| now.0 <= item.expiry.0);
         let removed = before - self.pending.len();
         if removed > 0 {
             self.charged_bytes = self.pending.iter().map(|x| x.wire_bytes).sum();
             self.expired += removed;
         }
         removed
     }
     pub fn is_ready(&mut self, now: MonoNs) -> bool {
         // Since ready_at <= expiry and entries are ordered by ready_at,
         // no later item can expire without the head ALREADY being due.
         // Thus the first-ready hot path is O(1); stale due heads are
         // reclaimed as needed. Full scans occur only on admission pressure.
         while self.pending.front().is_some_and(|p| now.0 > p.expiry.0) {
             let old = self.pending.pop_front().unwrap();
             self.charged_bytes -= old.wire_bytes;
             self.expired += 1;
         }
         self.pending.front().is_some_and(|p| now.0 >= p.ready_at.0)
     }
     pub fn take_ready(&mut self, now: MonoNs) -> Option<FrozenRecord> {
         if !self.is_ready(now) { return None; }
         let item = self.pending.pop_front().unwrap();
         self.charged_bytes -= item.wire_bytes;
         Some(item.record)
     }
     /// Because eligible_at <= expiry was checked on admission, the
     /// earliest *ready* head is also earlier than every item expiry.
     /// Peek only (O(1)); no full parity scan per systematic packet.
     pub fn next_deadline(&mut self, now: MonoNs) -> Option<MonoNs> {
         self.is_ready(now);
         self.pending.front().map(|item| item.ready_at)
     }
     pub fn len(&self) -> usize { self.pending.len() }
     pub fn charged_bytes(&self) -> usize { self.charged_bytes }
     pub fn expired_count(&self) -> usize { self.expired }
     pub fn clear(&mut self) -> usize {
         let n = self.pending.len();
         self.pending.clear();
         self.charged_bytes = 0;
         n
     }
 }

#[cfg(test)]
mod tests {
    use super::*;
    use super::super::{TxKind, TxOwner, TxWait};
    use super::super::wake;
    use crate::memory::Arena;
    use std::sync::{Arc, mpsc, atomic::{AtomicU64, Ordering}};
    use std::time::Duration;
    use wbd_types::{LaneKey, RecordPn, SeqOffset, TunnelKey};
    use wbd_types::buffer_contract::{FrozenMetadata, UniqueSealable};
    fn meta() -> FrozenMetadata {
        FrozenMetadata {
            lane: LaneKey { tunnel:TunnelKey{slot:7,generation:1},
                slot:1,generation:1 },
            pn:RecordPn(3),seq:SeqOffset(17),carrier_snapshot:7
        }
    }
    fn a() -> Arena { Arena::new(77, 96, 256, 1, 100_000).unwrap() }
    fn rec(arena:&mut Arena, value:u8) -> FrozenRecord {
        let mut unique=arena.allocate().unwrap();
        unique.writable()[0]=value;
        unique.freeze(0..1,meta()).unwrap()
    }
    fn limit(n:usize, bytes:usize) -> QueueLimits {
        QueueLimits{slots:n,bytes,max_age_ns:100_000_000}
    }
    fn tx() -> TxOwner {
        TxOwner::with_parity(limit(64,64),limit(16,16),limit(16,16)).unwrap()
    }
    #[test]
    fn r1_parity_first_fresh_before_32ms_fec_due_and_no_early_wake() {
        let mut arena=a();
        let mut owner=tx();
        let deadline=MonoNs(32_000_000);
        owner.offer_parity(rec(&mut arena, 9), MonoNs(0), deadline).unwrap();
        owner.offer_fresh(rec(&mut arena, 1), MonoNs(0)).unwrap();
        assert_eq!(owner.next_ready(MonoNs(0)).unwrap().kind, TxKind::Fresh);
        assert!(owner.next_ready(MonoNs(31_999_999)).is_none());
        assert_eq!(owner.parity_deadline(MonoNs(31_999_999)),Some(deadline));
        let got=owner.next_ready(deadline).unwrap();
        assert_eq!(got.kind,TxKind::Parity);
        assert_eq!(got.record.bytes(),&[9]);
        drop(got);
        assert_eq!(owner.parity_state().0,0);
    }
    #[test]
    fn r1_parity_only_absolute_fake_deadline_wakes_parked_owner() {
        let mut arena=a();
        let mut owner=tx();
        owner.offer_parity(rec(&mut arena,4),MonoNs(0),MonoNs(32_000_000)).unwrap();
        let (_unused,consumer)=wake::single::<u8>(1).unwrap();
        let gate=consumer.gate();
        let clock=Arc::new(AtomicU64::new(0));
        let worker_clock=Arc::clone(&clock);
        let worker_gate=Arc::clone(&gate);
        let (done_tx, done_rx)=mpsc::sync_channel(1);
        let worker=std::thread::spawn(move|| {
            let outcome=owner.wait_ready(&worker_gate,
                ||MonoNs(worker_clock.load(Ordering::SeqCst)),||false);
            let result=match outcome {
                Some(TxWait::Dispatch(d)) => (d.kind,d.record.bytes()[0]),
                _=>panic!("expected due parity"),
            };
            done_tx.send(result).unwrap();
        });
        clock.store(31_000_000,Ordering::SeqCst);
        gate.notify();
        // A spurious/early wake cannot publish the 32ms parity handle.
        assert!(matches!(done_rx.try_recv(),Err(mpsc::TryRecvError::Empty)));
        clock.store(32_000_000,Ordering::SeqCst);
        gate.notify();
        assert_eq!(done_rx.recv_timeout(Duration::from_secs(2)).unwrap(),
            (TxKind::Parity,4));
        worker.join().unwrap();
        assert_eq!(arena.report().loaned,0);
    }
    #[test]
    fn r1_parity_out_of_order_deadlines_do_not_hol_or_expire_wrong() {
        let mut arena=a();
        let mut owner=tx();
        owner.offer_parity(rec(&mut arena,10),MonoNs(0),MonoNs(80_000_000)).unwrap();
        owner.offer_parity(rec(&mut arena,11),MonoNs(0),MonoNs(20_000_000)).unwrap();
        assert_eq!(owner.parity_deadline(MonoNs(0)),Some(MonoNs(20_000_000)));
        assert!(owner.next_ready(MonoNs(19_999_999)).is_none());
        let first=owner.next_ready(MonoNs(20_000_000)).unwrap();
        assert_eq!(first.record.bytes(),&[11]);
        assert_eq!(first.kind,TxKind::Parity);
        assert!(owner.next_ready(MonoNs(79_999_999)).is_none());
        assert_eq!(owner.next_ready(MonoNs(80_000_000)).unwrap().record.bytes(),&[10]);
    }
    #[test]
    fn r1_parity_capacity_slots_bytes_and_independent_fresh_repair() {
        let mut arena=a();
        let mut owner=TxOwner::with_parity(limit(1,1),limit(1,1),limit(1,1)).unwrap();
        owner.offer_parity(rec(&mut arena,1),MonoNs(0),MonoNs(32_000_000)).unwrap();
        assert!(matches!(
            owner.offer_parity(rec(&mut arena,2),MonoNs(0),MonoNs(32_000_000)),
            Err((OfferError::Full,_))));
        owner.offer_repair(rec(&mut arena,3),MonoNs(0)).unwrap();
        owner.offer_fresh(rec(&mut arena,4),MonoNs(0)).unwrap();
        assert_eq!(owner.parity_state(),(1,1,0));
        assert_eq!(owner.next_ready(MonoNs(0)).unwrap().kind,TxKind::Fresh);
        assert_eq!(owner.next_ready(MonoNs(0)).unwrap().kind,TxKind::Repair);
        assert!(owner.next_ready(MonoNs(0)).is_none());
        assert_eq!(owner.next_ready(MonoNs(32_000_000)).unwrap().kind,TxKind::Parity);
    }
    #[test]
    fn r1_parity_bounded_repair_parity_fairness_under_continuous_fresh() {
        let mut arena=a();
        let mut owner=tx();
        owner.offer_repair(rec(&mut arena,1),MonoNs(0)).unwrap();
        owner.offer_parity(rec(&mut arena,2),MonoNs(0),MonoNs(0)).unwrap();
        for i in 0..36u8 {
            owner.offer_fresh(rec(&mut arena,i),MonoNs(0)).unwrap();
        }
        for _ in 0..10 { assert_eq!(owner.next_ready(MonoNs(0)).unwrap().kind,TxKind::Fresh); }
        assert_eq!(owner.next_ready(MonoNs(0)).unwrap().kind,TxKind::Repair);
        for _ in 0..10 { assert_eq!(owner.next_ready(MonoNs(0)).unwrap().kind,TxKind::Fresh); }
        assert_eq!(owner.next_ready(MonoNs(0)).unwrap().kind,TxKind::Parity);
        assert_eq!(owner.queued().0,16);
    }
    #[test]
    fn r1_parity_age_boundary_drops_expired_owned_record_and_zero_charge() {
        let mut arena=a();
        let mut owner=TxOwner::with_parity(limit(1,1),limit(1,1),
            QueueLimits{slots:1,bytes:1,max_age_ns:40}).unwrap();
        assert!(matches!(owner.offer_parity(rec(&mut arena,1),MonoNs(0),MonoNs(41)),
            Err((OfferError::InvalidWindow,_))));
        owner.offer_parity(rec(&mut arena,2),MonoNs(0),MonoNs(39)).unwrap();
        assert_eq!(owner.parity_deadline(MonoNs(10)),Some(MonoNs(39)));
        assert!(owner.next_ready(MonoNs(38)).is_none());
        // Deadline at 39 is eligible; ordinary stop or expiry still owns drop.
        assert_eq!(owner.next_ready(MonoNs(39)).unwrap().kind,TxKind::Parity);
        owner.offer_parity(rec(&mut arena,3),MonoNs(0),MonoNs(40)).unwrap();
        assert_eq!(owner.parity_deadline(MonoNs(41)),None);
        assert_eq!(owner.parity_state(),(0,0,1));
        assert_eq!(arena.report().loaned,0);
    }
    #[test]
    fn r1_parity_stop_full_three_classes_and_frozen_return_race() {
        let mut arena=a();
        let mut owner=TxOwner::with_parity(limit(1,1),limit(1,1),limit(1,1)).unwrap();
        let held=rec(&mut arena,7);
        let loan=held.clone();
        owner.offer_fresh(held,MonoNs(0)).unwrap();
        owner.offer_repair(rec(&mut arena,8),MonoNs(0)).unwrap();
        owner.offer_parity(rec(&mut arena,9),MonoNs(0),MonoNs(32_000_000)).unwrap();
        assert!(matches!(owner.offer_fresh(rec(&mut arena,1),MonoNs(0)),
            Err((OfferError::Full,_))));
        assert!(matches!(owner.offer_repair(rec(&mut arena,2),MonoNs(0)),
            Err((OfferError::Full,_))));
        assert!(matches!(owner.offer_parity(rec(&mut arena,3),MonoNs(0),MonoNs(1)),
            Err((OfferError::Full,_))));
        assert_eq!(owner.stop(),3);
        assert!(matches!(owner.offer_parity(rec(&mut arena,4),MonoNs(0),MonoNs(1)),
            Err((OfferError::Stopping,_))));
        assert!(owner.next_ready(MonoNs(33_000_000)).is_none());
        assert_eq!(owner.parity_state().0,0);
        assert_eq!(arena.stop().loaned,1);
        let exit=std::thread::spawn(move || drop(loan));
        exit.join().unwrap();
        assert!(arena.quiesced());
        assert_eq!(arena.report().loaned,0);
    }
    #[test]
    fn r1_parity_wake_stop_cancels_delayed_parity_before_delivery() {
        let mut arena=a();
        let mut owner=tx();
        owner.offer_parity(rec(&mut arena,7),MonoNs(0),MonoNs(32_000_000)).unwrap();
        let (producer,consumer)=wake::single::<u8>(1).unwrap();
        let gate=consumer.gate();
        producer.stop();
        assert!(owner.wait_ready(&gate,||MonoNs(32_000_000),||false).is_none());
        assert_eq!(owner.parity_state().0,0);
        assert_eq!(arena.report().loaned,0);
    }
    #[test]
    fn r1_parity_expiry_behind_nonexpired_ready_head_never_leaks_or_hol() {
        let mut arena=a();
        let mut queue=ParityReady::new(
            QueueLimits { slots:2,bytes:2,max_age_ns:50 }
        ).unwrap();
        // Older ready deadline but younger age is intentionally at head.
        queue.offer(rec(&mut arena,1),MonoNs(40),MonoNs(45)).unwrap();
        queue.offer(rec(&mut arena,2),MonoNs(0),MonoNs(50)).unwrap();
        assert_eq!(queue.next_deadline(MonoNs(51)),Some(MonoNs(45)));
        assert_eq!(queue.take_ready(MonoNs(51)).unwrap().bytes(),&[1]);
        // Later-in-ready-order entry is expired and cannot be delivered.
        assert!(queue.take_ready(MonoNs(51)).is_none());
        assert_eq!(queue.expired_count(),1);
        assert_eq!(queue.charged_bytes(),0);
        assert_eq!(arena.report().loaned,0);
    }
    #[test]
    fn r1_parity_rejects_slot_budget_and_retains_no_extra_payload_copy() {
        let mut arena=a();
        assert!(ParityReady::new(QueueLimits{slots:0,bytes:1,max_age_ns:1}).is_none());
        let mut queue=ParityReady::new(QueueLimits{slots:2,bytes:1,max_age_ns:100}).unwrap();
        let f=rec(&mut arena,12);
        let ptr=f.bytes().as_ptr();
        queue.offer(f,MonoNs(0),MonoNs(1)).unwrap();
        assert!(matches!(queue.offer(rec(&mut arena,13),MonoNs(0),MonoNs(1)),
            Err((OfferError::ByteBudget,_))));
        let frozen=queue.take_ready(MonoNs(1)).unwrap();
        assert!(std::ptr::eq(frozen.bytes().as_ptr(),ptr));
        drop(frozen);
        assert_eq!(queue.charged_bytes(),0);
        assert_eq!(arena.report().loaned,0);
    }
}
