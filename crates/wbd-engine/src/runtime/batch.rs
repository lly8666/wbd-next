//! M1 R1-M1-READY-BATCH-004: owner-local ready-only bounded handle drain.
 //! No allocator call, socket, driver send or ciphertext clone in this path.
 #![forbid(unsafe_code)]
 use wbd_types::MonoNs;
 use super::{TxDispatch, TxOwner};

 /// Maximum number of already-ready immutable records a TX owner hands to
 /// one caller per scheduling turn. NOT an age/latency batching threshold.
 pub const READY_BATCH_MAX: usize = 32;

 impl TxOwner {
     /// Append up to min(32, caller's already allocated unused slots) to
     /// `output`, returning the number newly appended. Existing elements are
     /// untouched. A Vec with no spare capacity is *not* resized.
     ///
     /// Each dispatch moves the original frozen handle; no Arc clone or
     /// payload-byte copy. The caller must hold dispatched handles until the
     /// platform has stopped borrowing them; stop() only drains queued ones.
     /// Every selected record is READY at `now`; future parity remains queued.
     /// Fresh/repair/parity order and byte quotas remain exclusively owned by
     /// next_ready(), including its 10-fresh bounded secondary fairness.
     pub fn drain_ready_batch(&mut self, now: MonoNs, output: &mut Vec<TxDispatch>) -> usize {
         let available = output.capacity().saturating_sub(output.len());
         let limit = READY_BATCH_MAX.min(available);
         let mut appended = 0;
         while appended < limit {
             match self.next_ready(now) {
                 Some(ready) => {
                     output.push(ready);
                     appended += 1;
                 }
                 None => break,
             }
         }
         appended
     }
 }

 #[cfg(test)]
 mod tests {
     use super::*;
     use super::super::{OfferError, QueueLimits, TxKind};
     use crate::memory::Arena;
     use wbd_types::{LaneKey, RecordPn, SeqOffset, TunnelKey};
     use wbd_types::buffer_contract::{FrozenMetadata, FrozenRecordHandle, UniqueSealable};

     fn metadata() -> FrozenMetadata {
         FrozenMetadata {
             lane: LaneKey { tunnel: TunnelKey {slot: 14, generation: 4},
                 slot: 2, generation: 1 },
             pn: RecordPn(91), seq: SeqOffset(123), carrier_snapshot: 27,
         }
     }
     fn arena() -> Arena {
         Arena::new(43, 96, 256, 1, 100_000).unwrap()
     }
     fn frozen(arena: &mut Arena, value: u8) -> crate::memory::FrozenRecord {
         let mut buffer = arena.allocate().unwrap();
         buffer.writable()[0] = value;
         buffer.freeze(0..1, metadata()).unwrap()
     }
     fn limit(slots: usize) -> QueueLimits {
         QueueLimits {slots, bytes: slots, max_age_ns: 100_000_000}
     }
     fn tx() -> TxOwner {
         TxOwner::with_parity(limit(64), limit(8), limit(8)).unwrap()
     }

     #[test]
     fn r1_batch_empty_zero_capacity_never_allocates_or_blocks() {
         let mut tx = tx();
         let mut output: Vec<TxDispatch> = Vec::new();
         assert_eq!(output.capacity(), 0);
         assert_eq!(tx.drain_ready_batch(MonoNs(0), &mut output), 0);
         assert!(output.is_empty());
         assert_eq!(output.capacity(), 0);
         let mut supplied = Vec::with_capacity(32);
         let pointer = supplied.as_ptr();
         assert_eq!(tx.drain_ready_batch(MonoNs(100), &mut supplied), 0);
         assert_eq!(supplied.capacity(), 32);
         assert_eq!(pointer, supplied.as_ptr());
     }

     #[test]
     fn r1_batch_one_fresh_is_immediate_and_moves_exact_frozen_allocation() {
         let mut arena = arena();
         let mut tx = tx();
         let record = frozen(&mut arena, 29);
         let source_pointer = record.bytes().as_ptr();
         tx.offer_fresh(record, MonoNs(0)).unwrap();
         let mut output = Vec::with_capacity(32);
         let pointer = output.as_ptr();
         assert_eq!(tx.drain_ready_batch(MonoNs(0), &mut output), 1);
         assert_eq!(output.len(), 1);
         assert_eq!(output[0].kind, TxKind::Fresh);
         assert_eq!(output[0].record.bytes(), &[29]);
         assert_eq!(source_pointer, output[0].record.bytes().as_ptr());
         assert_eq!(pointer, output.as_ptr());
         assert_eq!(tx.drain_ready_batch(MonoNs(0), &mut output), 0);
         drop(output);
         assert_eq!(arena.report().loaned, 0);
     }

     #[test]
     fn r1_batch_thirty_two_exact_cap_from_preallocated_output() {
         let mut arena = arena();
         let mut tx = tx();
         for i in 0..32u8 {
             tx.offer_fresh(frozen(&mut arena, i), MonoNs(0)).unwrap();
         }
         let mut output = Vec::with_capacity(32);
         let pointer = output.as_ptr();
         assert_eq!(tx.drain_ready_batch(MonoNs(0), &mut output), 32);
         assert_eq!(output.len(), 32);
         assert_eq!(pointer, output.as_ptr());
         assert_eq!(tx.queued(), (0,0));
         for (i, dispatched) in output.iter().enumerate() {
             assert_eq!(dispatched.kind, TxKind::Fresh);
             assert_eq!(dispatched.record.bytes(), &[i as u8]);
         }
         assert_eq!(tx.drain_ready_batch(MonoNs(0), &mut output), 0);
         drop(output);
         assert_eq!(arena.report().loaned, 0);
     }

     #[test]
     fn r1_batch_thirty_three_requires_second_call_and_never_drops_tail() {
         let mut arena = arena();
         let mut tx = tx();
         for i in 0..33u8 {
             tx.offer_fresh(frozen(&mut arena, i), MonoNs(0)).unwrap();
         }
         let mut output = Vec::with_capacity(64);
         let pointer = output.as_ptr();
         assert_eq!(tx.drain_ready_batch(MonoNs(0), &mut output), 32);
         assert_eq!(output.len(), 32);
         assert_eq!(tx.queued(), (1,0));
         assert_eq!(tx.drain_ready_batch(MonoNs(0), &mut output), 1);
         assert_eq!(output.len(), 33);
         assert_eq!(pointer, output.as_ptr());
         assert_eq!(output[32].record.bytes(), &[32]);
         drop(output);
         assert_eq!(arena.report().loaned, 0);
     }

     #[test]
     fn r1_batch_full_independent_repair_parity_cannot_hol_fresh() {
         let mut arena = arena();
         let mut tx = TxOwner::with_parity(limit(1),limit(1),limit(1)).unwrap();
         tx.offer_repair(frozen(&mut arena, 91),MonoNs(0)).unwrap();
         tx.offer_parity(frozen(&mut arena, 92),MonoNs(0),MonoNs(32_000_000)).unwrap();
         assert!(matches!(tx.offer_repair(frozen(&mut arena, 93),MonoNs(0)),
             Err((OfferError::Full,_))));
         assert!(matches!(tx.offer_parity(frozen(&mut arena, 94),MonoNs(0),MonoNs(30_000_000)),
             Err((OfferError::Full,_))));
         tx.offer_fresh(frozen(&mut arena, 5),MonoNs(0)).unwrap();
         let mut output = Vec::with_capacity(32);
         assert_eq!(tx.drain_ready_batch(MonoNs(0), &mut output), 2);
         assert_eq!(output[0].kind, TxKind::Fresh);
         assert_eq!(output[1].kind, TxKind::Repair);
         assert_eq!(tx.parity_deadline(MonoNs(0)), Some(MonoNs(32_000_000)));
         assert_eq!(tx.drain_ready_batch(MonoNs(31_999_999), &mut output), 0);
         assert_eq!(tx.drain_ready_batch(MonoNs(32_000_000), &mut output), 1);
         assert_eq!(output[2].kind, TxKind::Parity);
         drop(output);
         assert_eq!(arena.report().loaned, 0);
     }

     #[test]
     fn r1_batch_first_systematic_precedes_already_due_parity() {
         let mut arena = arena();
         let mut tx = tx();
         tx.offer_parity(frozen(&mut arena, 7),MonoNs(0),MonoNs(0)).unwrap();
         tx.offer_fresh(frozen(&mut arena, 8),MonoNs(0)).unwrap();
         let mut output = Vec::with_capacity(2);
         assert_eq!(tx.drain_ready_batch(MonoNs(0), &mut output), 2);
         assert_eq!((output[0].kind, output[1].kind),
             (TxKind::Fresh, TxKind::Parity));
         drop(output);
         assert_eq!(arena.report().loaned, 0);
     }

     #[test]
     fn r1_batch_secondary_fairness_continues_over_multiple_batches() {
         let mut arena = arena();
         let mut tx = tx();
         for i in 0..64u8 {
             tx.offer_fresh(frozen(&mut arena, i),MonoNs(0)).unwrap();
         }
         for i in 0..3u8 {
             tx.offer_repair(frozen(&mut arena, 90+i), MonoNs(0)).unwrap();
             tx.offer_parity(frozen(&mut arena, 100+i), MonoNs(0), MonoNs(0)).unwrap();
         }
         let mut output = Vec::with_capacity(32);
         assert_eq!(tx.drain_ready_batch(MonoNs(0), &mut output), 32);
         assert_eq!(output[0].kind, TxKind::Fresh);
         assert_eq!(output[10].kind, TxKind::Repair);
         assert_eq!(output[21].kind, TxKind::Parity);
         assert_eq!(output.capacity(), 32);
         // Caller releases the dispatched handles before the next turn.
         output.clear();
         assert_eq!(tx.drain_ready_batch(MonoNs(0), &mut output), 32);
         let secondary = output.iter().filter(|p| p.kind != TxKind::Fresh)
             .map(|p| p.kind).collect::<Vec<_>>();
         assert!(secondary.contains(&TxKind::Repair));
         assert!(secondary.contains(&TxKind::Parity));
         assert_eq!(output.len(), 32);
         assert_eq!(tx.queued().0 + tx.queued().1 + tx.parity_state().0, 6);
         drop(output);
         assert_eq!(tx.stop(), 6);
         assert_eq!(arena.report().loaned, 0);
     }

     #[test]
     fn r1_batch_prefilled_output_obeys_spare_slots_without_realloc() {
         let mut arena = arena();
         let mut tx = tx();
         let mut output = Vec::with_capacity(2);
         output.push(TxDispatch {kind: TxKind::Fresh,
             record: frozen(&mut arena, 99) });
         tx.offer_fresh(frozen(&mut arena, 1),MonoNs(0)).unwrap();
         tx.offer_fresh(frozen(&mut arena, 2),MonoNs(0)).unwrap();
         let pointer = output.as_ptr();
         assert_eq!(tx.drain_ready_batch(MonoNs(0), &mut output), 1);
         assert_eq!(output.len(), 2);
         assert_eq!(output[0].record.bytes(), &[99]);
         assert_eq!(output[1].record.bytes(), &[1]);
         assert_eq!(pointer, output.as_ptr());
         assert_eq!(tx.queued().0, 1);
         assert_eq!(tx.drain_ready_batch(MonoNs(0), &mut output), 0);
         drop(output);
         assert_eq!(tx.stop(), 1);
         assert_eq!(arena.report().loaned, 0);
     }

     #[test]
     fn r1_batch_stop_keeps_dispatched_last_loan_until_external_release() {
         let mut arena = arena();
         let mut tx = tx();
         let source = frozen(&mut arena, 50);
         let held = source.clone();
         let old_origin = held.origin();
         tx.offer_fresh(source,MonoNs(0)).unwrap();
         tx.offer_repair(frozen(&mut arena, 51),MonoNs(0)).unwrap();
         tx.offer_parity(frozen(&mut arena, 52),MonoNs(0),MonoNs(32_000_000)).unwrap();
         let mut output = Vec::with_capacity(1);
         assert_eq!(tx.drain_ready_batch(MonoNs(0), &mut output), 1);
         assert_eq!(output[0].kind, TxKind::Fresh);
         assert_eq!(tx.stop(), 2);
         assert_eq!(tx.drain_ready_batch(MonoNs(33_000_000), &mut output), 0);
         assert!(matches!(tx.offer_fresh(frozen(&mut arena, 1),MonoNs(0)),
             Err((OfferError::Stopping,_))));
         assert_eq!(arena.stop().loaned, 1);
         drop(output);
         assert_eq!(arena.report().loaned, 1);
         let join = std::thread::spawn(move || {
             assert_eq!(held.origin(), old_origin);
             drop(held);
         });
         join.join().unwrap();
         assert!(arena.quiesced());
         assert_eq!(arena.report().loaned, 0);
     }

     #[test]
     fn r1_batch_stopped_queue_and_full_return_backlog_zero_loan() {
         let mut arena = arena();
         let mut tx = tx();
         for i in 0..8 {
             tx.offer_fresh(frozen(&mut arena, i),MonoNs(0)).unwrap();
         }
         let mut output = Vec::with_capacity(4);
         assert_eq!(tx.drain_ready_batch(MonoNs(0),&mut output), 4);
         assert_eq!(tx.stop(), 4); // return channel capacity one
         assert_eq!(arena.stop().loaned, 4);
         drop(output);
         assert!(arena.quiesced());
     }
 }
