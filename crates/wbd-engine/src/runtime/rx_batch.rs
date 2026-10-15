//! M1 R1 RX owner: bounded, caller-allocated ready-only ingress batches.
 //! A lane hint is pre-auth routing metadata, NEVER a verified identity.
 //! No ciphertext/plaintext copies, socket reads, or per-batch allocations.
 #![forbid(unsafe_code)]
 use wbd_types::{LaneKey, MonoNs};
 use super::{RxOwner, RxPacket};

 pub const RX_READY_BATCH_MAX: usize = 32;

 impl RxOwner {
     /// One eligible item, preferring oldest arrival for first service,
     /// then a different eligible lane before repeated service of the
     /// previously dispatched lane. Per-lane FIFO is preserved when the
     /// predicate is stable for the duration of this call.
     ///
     /// The predicate only expresses downstream capacity; it cannot
     /// authenticate the untrusted lane hint. A blocked lane never
     /// obstructs an unrelated eligible lane.
     pub fn take_ready_where<F>(&mut self, now: MonoNs, mut eligible: F)
         -> Option<RxPacket>
     where F: FnMut(Option<LaneKey>) -> bool {
         if self.stopping { return None; }

         // The owner queue is fixed-size and may remove arbitrary middle
         // indices for fair lane dispatch. Unlike head-only FIFO expiry,
         // reclaim all aged loans before selecting a live candidate.
         // No transient vector/heap allocation and no polling or sleep.
         let mut released_bytes = 0usize;
         let mut released_count = 0usize;
         let max_age = self.ready.limit.max_age_ns;
         self.ready.q.retain(|entry| {
             if now.elapsed_since(entry.now) > max_age {
                 released_bytes += entry.bytes;
                 released_count += 1;
                 false
             } else { true }
         });
         self.ready.used_bytes -= released_bytes;
         self.ready.expired += released_count;

         let mut earliest_allowed = None;
         let mut different_lane = None;
         for (index, entry) in self.ready.q.iter().enumerate() {
             let lane = entry.value.lane_hint;
             if !eligible(lane) { continue; }
             if earliest_allowed.is_none() { earliest_allowed = Some(index); }
             if self.last_lane.is_some_and(|last| last != lane) {
                 different_lane = Some(index);
                 break;
             }
         }
         let chosen = different_lane.or(earliest_allowed)?;
         let entry = self.ready.q.remove(chosen)
             .expect("chosen index belongs to bounded owner queue");
         self.ready.used_bytes -= entry.bytes;
         self.last_lane = Some(entry.value.lane_hint);
         Some(entry.value.packet)
     }

     /// Append at most 32 eligible uniquely owned RX packets into already
     /// allocated spare Vec slots. No packet memory or queue metadata clone.
     /// Empty/full caller output returns immediately and never reserves.
     pub fn drain_ready_batch(&mut self, now: MonoNs, output: &mut Vec<RxPacket>) -> usize {
         self.drain_ready_batch_where(now, output, |_| true)
     }

     /// Same ownership/cap contract but skips blocked untrusted lane hints.
     /// `lane_ready` MUST be a stable per-lane capacity predicate throughout
     /// a call. A false result is not a packet rejection or authentication.
     pub fn drain_ready_batch_where<F>(
         &mut self, now: MonoNs, output: &mut Vec<RxPacket>, mut lane_ready: F,
     ) -> usize
     where F: FnMut(Option<LaneKey>) -> bool {
         let available = output.capacity().saturating_sub(output.len());
         let limit = RX_READY_BATCH_MAX.min(available);
         let mut appended = 0;
         while appended < limit {
             match self.take_ready_where(now, &mut lane_ready) {
                 Some(packet) => { output.push(packet); appended += 1; }
                 None => break,
             }
         }
         appended
     }
 }

 #[cfg(test)]
 mod tests {
     use super::*;
     use super::super::{OfferError, QueueLimits};
     use crate::memory::Arena;
     use std::ops::Range;
     use wbd_types::{TunnelKey, buffer_contract::UniqueSealable};

     fn a() -> Arena { Arena::new(73, 96, 256, 1, 100_000).unwrap() }
     fn q(slots: usize, bytes: usize, age: u64) -> RxOwner {
         RxOwner::new(QueueLimits {slots, bytes, max_age_ns:age}).unwrap()
     }
     fn lane(slot: u32) -> LaneKey {
         LaneKey { tunnel:TunnelKey {slot:9,generation:1},
             slot,generation:1 }
     }
     fn buf(a: &mut Arena, b: u8) -> crate::memory::UniqueBuffer {
         let mut x=a.allocate().unwrap();
         x.writable()[8] = b;
         x
     }
     fn offer(a: &mut Arena, rx: &mut RxOwner, lane: LaneKey, b: u8, at:u64) {
         rx.offer_lane(buf(a,b),8..9,lane,MonoNs(at)).unwrap();
     }
     fn wire(mut p: RxPacket) -> u8 {
         p.wire_mut()[0]
     }

     #[test]
     fn r1_rx_batch_empty_and_zero_capacity_do_not_allocate() {
         let mut rx=q(64,64,100);
         let mut out: Vec<RxPacket> = Vec::new();
         assert_eq!(out.capacity(),0);
         assert_eq!(rx.drain_ready_batch(MonoNs(0),&mut out),0);
         assert_eq!(out.capacity(),0);
         let mut preallocated=Vec::with_capacity(32);
         let ptr=preallocated.as_ptr();
         assert_eq!(rx.drain_ready_batch(MonoNs(0),&mut preallocated),0);
         assert_eq!(ptr,preallocated.as_ptr());
         assert_eq!(preallocated.capacity(),32);
     }
     #[test]
     fn r1_rx_batch_one_first_arrival_preserves_unique_buffer_pointer() {
         let mut a=a();
         let mut rx=q(64,64,100);
         let mut source=buf(&mut a,11);
         let ptr=source.writable().as_ptr();
         rx.offer_lane(source,8..9,lane(1),MonoNs(0)).unwrap();
         let mut out=Vec::with_capacity(1);
         let storage=out.as_ptr();
         assert_eq!(rx.drain_ready_batch(MonoNs(0),&mut out),1);
         assert_eq!(storage,out.as_ptr());
         assert_eq!(out[0].buffer.writable().as_ptr(),ptr);
         assert_eq!(wire(out.pop().unwrap()),11);
         assert_eq!(rx.queued(),0);
         assert_eq!(a.report().loaned,0);
     }
     #[test]
     fn r1_rx_batch_exact_32_no_grow_or_extra_wakeup() {
         let mut a=a();
         let mut rx=q(64,64,100);
         for i in 0..32 {offer(&mut a,&mut rx,lane(1),i,0);}
         let mut out=Vec::with_capacity(32);
         let ptr=out.as_ptr();
         assert_eq!(rx.drain_ready_batch(MonoNs(0),&mut out),32);
         assert_eq!(ptr,out.as_ptr());
         assert_eq!(out.len(),32);
         for i in 0..32 {assert_eq!(out[i].wire_mut(),&[i as u8]);}
         assert_eq!(rx.drain_ready_batch(MonoNs(0),&mut out),0);
         drop(out);
         assert_eq!(a.report().loaned,0);
     }
     #[test]
     fn r1_rx_batch_33_split_32_and_one_without_tail_drop() {
         let mut a=a();
         let mut rx=q(64,64,100);
         for i in 0..33 {offer(&mut a,&mut rx,lane(1),i,0);}
         let mut out=Vec::with_capacity(64);
         let ptr=out.as_ptr();
         assert_eq!(rx.drain_ready_batch(MonoNs(0),&mut out),32);
         assert_eq!(rx.queued(),1);
         assert_eq!(rx.drain_ready_batch(MonoNs(0),&mut out),1);
         assert_eq!(out.len(),33);
         assert_eq!(ptr,out.as_ptr());
         assert_eq!(out[32].wire_mut(),&[32]);
         drop(out);
         assert_eq!(a.report().loaned,0);
     }
     #[test]
     fn r1_rx_batch_full_prefilled_output_never_overwrites_or_grows() {
         let mut a=a();
         let mut rx=q(4,4,100);
         let mut prior=buf(&mut a,99);
         prior.writable()[8]=99;
         let mut out=Vec::with_capacity(2);
         out.push(RxPacket {buffer:prior,wire:8..9});
         offer(&mut a,&mut rx,lane(1),1,0);
         offer(&mut a,&mut rx,lane(1),2,0);
         let ptr=out.as_ptr();
         assert_eq!(rx.drain_ready_batch(MonoNs(0),&mut out),1);
         assert_eq!(out[0].wire_mut(),&[99]);
         assert_eq!(out[1].wire_mut(),&[1]);
         assert_eq!(rx.queued(),1);
         assert_eq!(rx.drain_ready_batch(MonoNs(0),&mut out),0);
         assert_eq!(ptr,out.as_ptr());
         assert_eq!(rx.stop(),1);
         drop(out);
         assert_eq!(a.report().loaned,0);
     }
     #[test]
     fn r1_rx_batch_two_lanes_alternate_without_reordering_each_lane() {
         let mut a=a();
         let mut rx=q(16,16,100);
         for x in [1,2,3,4] {offer(&mut a,&mut rx,lane(1),x,0);}
         for x in [51,52,53] {offer(&mut a,&mut rx,lane(2),x,0);}
         let mut out=Vec::with_capacity(8);
         assert_eq!(rx.drain_ready_batch(MonoNs(0),&mut out),7);
         let actual:Vec<u8>=out.into_iter().map(wire).collect();
         assert_eq!(actual,[1,51,2,52,3,53,4]);
         assert_eq!(rx.queued(),0);
         assert_eq!(a.report().loaned,0);
     }
     #[test]
     fn r1_rx_batch_obstructed_head_lane_allows_unrelated_lane() {
         let mut a=a();
         let mut rx=q(16,16,100);
         offer(&mut a,&mut rx,lane(1),1,0);
         offer(&mut a,&mut rx,lane(1),2,0);
         offer(&mut a,&mut rx,lane(2),71,0);
         offer(&mut a,&mut rx,lane(2),72,0);
         let mut out=Vec::with_capacity(4);
         assert_eq!(rx.drain_ready_batch_where(MonoNs(0),&mut out,
             |l| l==Some(lane(2))),2);
         assert_eq!(out[0].wire_mut(),&[71]);
         assert_eq!(out[1].wire_mut(),&[72]);
         assert_eq!(rx.queued(),2);
         out.clear();
         assert_eq!(rx.drain_ready_batch_where(MonoNs(0),&mut out,
             |l| l==Some(lane(1))),2);
         assert_eq!(out[0].wire_mut(),&[1]);
         assert_eq!(out[1].wire_mut(),&[2]);
         drop(out);
         assert_eq!(a.report().loaned,0);
     }
     #[test]
     fn r1_rx_batch_bound_slots_bytes_and_invalid_range_return_owned_buffer() {
         let mut a=a();
         let mut rx=q(2,2,100);
         offer(&mut a,&mut rx,lane(1),1,0);
         offer(&mut a,&mut rx,lane(2),2,0);
         let err=rx.offer_lane(buf(&mut a,3),8..9,lane(1),MonoNs(0));
         assert!(matches!(err,Err((OfferError::Full,_))));
         drop(err);
         assert_eq!(rx.queued(),2);
         assert_eq!(rx.stop(),2);
         assert_eq!(a.report().loaned,0);
         let mut rx=q(3,1,100);
         offer(&mut a,&mut rx,lane(1),4,0);
         let err=rx.offer_lane(buf(&mut a,5),8..9,lane(2),MonoNs(0));
         assert!(matches!(err,Err((OfferError::ByteBudget,_))));
         drop(err);
         let err=rx.offer_lane(buf(&mut a,6),Range{start:8,end:300},
             lane(2),MonoNs(0));
         assert!(matches!(err,Err((OfferError::InvalidWindow,_))));
         drop(err);
         assert_eq!(rx.stop(),1);
         assert_eq!(a.report().loaned,0);
     }
     #[test]
     fn r1_rx_batch_expiry_in_middle_does_not_deliver_stale_or_block_other_lane() {
         let mut a=a();
         let mut rx=q(4,4,10);
         offer(&mut a,&mut rx,lane(1),1,15);
         offer(&mut a,&mut rx,lane(2),2,0);
         offer(&mut a,&mut rx,lane(1),3,17);
         let mut out=Vec::with_capacity(4);
         assert_eq!(rx.drain_ready_batch(MonoNs(18),&mut out),2);
         assert_eq!(out[0].wire_mut(),&[1]);
         assert_eq!(out[1].wire_mut(),&[3]);
         assert_eq!(rx.ready.expired,1);
         assert_eq!(rx.queued(),0);
         drop(out);
         assert_eq!(a.report().loaned,0);
     }
     #[test]
     fn r1_rx_batch_stop_cancels_queued_but_dispatched_loan_remains() {
         let mut a=a();
         let mut rx=q(8,8,100);
         for i in 0..6 {offer(&mut a,&mut rx,lane(1),i,0);}
         let mut out=Vec::with_capacity(2);
         assert_eq!(rx.drain_ready_batch(MonoNs(0),&mut out),2);
         assert_eq!(rx.stop(),4);
         assert_eq!(a.stop().loaned,2);
         assert_eq!(rx.drain_ready_batch(MonoNs(0),&mut out),0);
         drop(out);
         assert!(a.quiesced());
         assert_eq!(a.report().loaned,0);
     }
     #[test]
     fn r1_rx_batch_full_return_backlog_and_last_loan_from_other_thread() {
         let mut a=a();
         let mut rx=q(8,8,100);
         for i in 0..8 {offer(&mut a,&mut rx,lane(1),i,0);}
         let mut out=Vec::with_capacity(8);
         assert_eq!(rx.drain_ready_batch(MonoNs(0),&mut out),8);
         assert_eq!(rx.stop(),0);
         let held=out.pop().unwrap();
         drop(out); // 7 final drops fill return queue and bounded backlog
         assert_eq!(a.stop().loaned,1);
         let join=std::thread::spawn(move||drop(held));
         join.join().unwrap();
         assert!(a.quiesced());
         assert_eq!(a.report().free,96);
     }
     #[test]
     fn r1_rx_batch_unscoped_legacy_offer_keeps_fifo_and_never_claims_auth() {
         let mut a=a();
         let mut rx=q(4,4,100);
         rx.offer(buf(&mut a,11),8..9,MonoNs(0)).unwrap();
         rx.offer(buf(&mut a,12),8..9,MonoNs(0)).unwrap();
         let mut out=Vec::with_capacity(4);
         assert_eq!(rx.drain_ready_batch(MonoNs(0),&mut out),2);
         assert_eq!(out.into_iter().map(wire).collect::<Vec<_>>(),[11,12]);
         assert_eq!(a.report().loaned,0);
     }
 }
