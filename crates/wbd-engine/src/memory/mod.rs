//! M1 R1 local, bounded, owned slab arena. This is NOT an OS/driver pool.
 //! Buffer identity is (arena id, full slot generation); no raw cross-owner pointers.
 //! The only payload copy is the caller's input into a writable owned slab.
 //! Freeze moves its Box into an Arc once; clones never copy ciphertext.
 #![forbid(unsafe_code)]
 
 use std::collections::VecDeque;
 use std::ops::Range;
 use std::sync::{mpsc::{self, Receiver, SyncSender, TryRecvError, TrySendError}, Arc, Mutex, OnceLock};
 use crate::runtime::wake::WakeGate;
 use wbd_types::{next_generation, BufferKey};
 use wbd_types::buffer_contract::{
     checked_wire_range, BufferContractError, BufferOrigin, FrozenMetadata,
     FrozenRecordHandle, UniqueSealable,
 };
 
 pub const ARENA_READY: bool = false; // Independent R1 proof only; not integrated.
 pub const SLAB_CLASSES: [usize; 5] = [256, 512, 768, 1536, 2048];
 pub fn class_for(needed: usize) -> Option<usize> {
     SLAB_CLASSES.iter().copied().find(|&size| size >= needed && needed > 0)
 }
 
 struct Returned {
     origin: BufferOrigin,
     slab: Box<[u8]>,
 }
 
 // Final-drop may race stop and a full return queue. At most one return can
 // exist per loan; backlog capacity is the total number of arena slots.
 // A contended Mutex exists only on the saturated return slow path, NEVER
 // while borrowing or sealing packet bytes. No producer silently loses a return.
 struct ReturnPath {
     tx: SyncSender<Returned>,
     backlog: Mutex<VecDeque<Returned>>,
     max_backlog: usize,
     wake: OnceLock<Arc<WakeGate>>,
 }
 impl ReturnPath {
     fn post(&self, item: Returned) {
         match self.tx.try_send(item) {
             Ok(()) => {}
             Err(TrySendError::Full(item)) => {
                 let mut q = self.backlog.lock().unwrap_or_else(|e| e.into_inner());
                 assert!(q.len() < self.max_backlog, "return invariant broken");
                 q.push_back(item);
             }
             // The owning arena is already gone. The returned Box is then
             // safely freed; no driver borrow is represented by this type.
             Err(TrySendError::Disconnected(_item)) => {}
         }
         // Return is published before its notification, even when the
         // channel was full and it entered the bounded fallback backlog.
         if let Some(gate) = self.wake.get() { gate.notify(); }
     }
 }
 
 pub struct UniqueBuffer {
     origin: BufferOrigin,
     slab: Option<Box<[u8]>>,
     return_path: Arc<ReturnPath>,
 }
 impl std::fmt::Debug for UniqueBuffer {
     fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
         f.debug_struct("UniqueBuffer").field("origin", &self.origin).finish()
     }
 }
 impl Drop for UniqueBuffer {
     fn drop(&mut self) {
         if let Some(slab) = self.slab.take() {
             self.return_path.post(Returned { origin: self.origin, slab });
         }
     }
 }
 impl UniqueSealable for UniqueBuffer {
     type Frozen = FrozenRecord;
     fn origin(&self) -> BufferOrigin { self.origin }
     fn writable(&mut self) -> &mut [u8] {
         self.slab.as_deref_mut().expect("unique slab not moved")
     }
     fn freeze(mut self, wire: Range<usize>, metadata: FrozenMetadata)
         -> Result<FrozenRecord, BufferContractError>
     {
         let checked = checked_wire_range(self.slab.as_ref().unwrap().len(), wire)?;
         let slab = self.slab.take().unwrap();
         Ok(FrozenRecord(Arc::new(FrozenPayload {
             origin: self.origin, wire: checked, metadata,
             slab: Some(slab), return_path: Arc::clone(&self.return_path),
         })))
     }
 }
 
 struct FrozenPayload {
     origin: BufferOrigin,
     metadata: FrozenMetadata,
     wire: Range<usize>,
     slab: Option<Box<[u8]>>,
     return_path: Arc<ReturnPath>,
 }
 impl Drop for FrozenPayload {
     fn drop(&mut self) {
         if let Some(slab) = self.slab.take() {
             self.return_path.post(Returned { origin: self.origin, slab });
         }
     }
 }
 #[derive(Clone)]
 pub struct FrozenRecord(Arc<FrozenPayload>);
 impl std::fmt::Debug for FrozenRecord {
     fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
         f.debug_struct("FrozenRecord").field("origin", &self.0.origin)
             .field("metadata", &self.0.metadata).finish()
     }
 }
 impl FrozenRecordHandle for FrozenRecord {
     fn origin(&self) -> BufferOrigin { self.0.origin }
     fn metadata(&self) -> FrozenMetadata { self.0.metadata }
     fn bytes(&self) -> &[u8] {
         &self.0.slab.as_ref().expect("frozen slab alive")[self.0.wire.clone()]
     }
 }
 
 struct Slot {
     generation: u32,
     available: Option<Box<[u8]>>,
     loaned: bool,
 }
 #[derive(Clone, Copy, Debug, Eq, PartialEq)]
 pub struct ArenaReport {
     pub loaned: usize,
     pub free: usize,
     pub retired: usize,
     pub charged_bytes: usize,
     pub stopping: bool,
 }
 
 /// All mutable slots and free indices belong to ONE arena owner thread.
 /// External holders own their allocations via Arc and can only return them.
 /// charged_bytes includes payload and a conservative slot/return bookkeeping
 /// allowance; it does not measure driver memory or Rust allocator overhead.
 pub struct Arena {
     id: u32,
     slots: Vec<Slot>,
     free: Vec<usize>,
     incoming: Receiver<Returned>,
     returns: Arc<ReturnPath>,
     loaned: usize,
     retired: usize,
     charged_bytes: usize,
     stopping: bool,
 }
 impl Arena {
     pub fn new(
         id: u32, count: usize, class_capacity: usize,
         return_queue_slots: usize, byte_budget: usize,
     ) -> Result<Self, BufferContractError> {
         if id == 0 || count == 0 || count > 8192
             || !SLAB_CLASSES.contains(&class_capacity)
             || return_queue_slots == 0 || return_queue_slots > count
         {
             return Err(BufferContractError::NoCapacity);
         }
         // Account for slots, free indices and a worst-case returned item
         // in each queue/backlog location, even though only count loans exist.
         let per_slot = class_capacity
             .checked_add(std::mem::size_of::<Slot>())
             .and_then(|n| n.checked_add(std::mem::size_of::<usize>()))
             .and_then(|n| n.checked_add(2 * std::mem::size_of::<Returned>()))
             .ok_or(BufferContractError::NoCapacity)?;
         let charged = count.checked_mul(per_slot)
             .ok_or(BufferContractError::NoCapacity)?;
         if charged > byte_budget { return Err(BufferContractError::NoCapacity); }
         let (tx, incoming) = mpsc::sync_channel(return_queue_slots);
         let mut slots = Vec::with_capacity(count);
         for _ in 0..count {
             slots.push(Slot { generation: 1,
                 available: Some(vec![0u8; class_capacity].into_boxed_slice()),
                 loaned: false });
         }
         let free = (0..count).rev().collect();
         Ok(Self {
             id, slots, free, incoming,
             returns: Arc::new(ReturnPath {
                 tx, backlog: Mutex::new(VecDeque::with_capacity(count)),
                 max_backlog: count,
                 wake: OnceLock::new(),
             }),
             loaned: 0, retired: 0, charged_bytes: charged, stopping: false,
         })
     }
     /// Attach exactly one owner consumer gate. Register before its first park;
     /// a prior returned item remains visible to the double-check anyway.
     pub fn register_wake(&mut self, gate: Arc<WakeGate>) -> bool {
         self.returns.wake.set(gate).is_ok()
     }
     pub fn allocate(&mut self) -> Result<UniqueBuffer, BufferContractError> {
         if self.stopping { return Err(BufferContractError::OwnerStopping); }
         self.drain_returns();
         let idx = self.free.pop().ok_or(BufferContractError::NoCapacity)?;
         let slot = &mut self.slots[idx];
         debug_assert!(!slot.loaned);
         slot.loaned = true;
         self.loaned += 1;
         Ok(UniqueBuffer {
             origin: BufferOrigin {
                 owner_arena: self.id,
                 key: BufferKey { slot: idx as u32, generation: slot.generation },
             },
             slab: slot.available.take(),
             return_path: Arc::clone(&self.returns),
         })
     }
     fn install(&mut self, item: Returned) {
         let i = item.origin.key.slot as usize;
         assert_eq!(item.origin.owner_arena, self.id);
         let slot = self.slots.get_mut(i).expect("valid return slot");
         assert!(slot.loaned && slot.generation == item.origin.key.generation,
             "stale, duplicated or foreign return");
         slot.loaned = false;
         self.loaned -= 1;
         if let Some(next) = next_generation(slot.generation) {
             slot.generation = next;
             slot.available = Some(item.slab);
             self.free.push(i);
         } else {
             self.retired += 1;
             // Generation exhausted: permanently retire, never alias old key.
         }
     }
     /// Owner-only, nonblocking: drains both bounded queue and fallback.
     /// Drop may publish concurrently; caller must recheck after observing stop.
     pub fn drain_returns(&mut self) -> usize {
         let mut returned = 0;
         loop {
             match self.incoming.try_recv() {
                 Ok(item) => { self.install(item); returned += 1; }
                 Err(TryRecvError::Empty | TryRecvError::Disconnected) => break,
             }
         }
         // Pop one by one; do not hold backlog lock while touching owner slots.
         loop {
             let next = self.returns.backlog.lock()
                 .unwrap_or_else(|e| e.into_inner()).pop_front();
             match next {
                 Some(item) => { self.install(item); returned += 1; }
                 None => break,
             }
         }
         returned
     }
     pub fn stop(&mut self) -> ArenaReport {
         self.stopping = true;
         self.report()
     }
     pub fn report(&mut self) -> ArenaReport {
         self.drain_returns();
         ArenaReport {
             loaned: self.loaned, free: self.free.len(),
             retired: self.retired, charged_bytes: self.charged_bytes,
             stopping: self.stopping,
         }
     }
     pub fn quiesced(&mut self) -> bool {
         self.drain_returns();
         self.stopping && self.loaned == 0
     }
 }
 
 #[cfg(test)]
 mod tests {
     use super::*;
     use wbd_types::{LaneKey, RecordPn, SeqOffset, TunnelKey};
     use wbd_types::buffer_contract::{driver_read, FrozenRecordHandle, UniqueSealable};
     fn metadata() -> FrozenMetadata {
         FrozenMetadata {
             lane: LaneKey { tunnel: TunnelKey { slot: 2, generation: 1 },
                 slot: 3, generation: 4 },
             pn: RecordPn(11), seq: SeqOffset(200), carrier_snapshot: 9,
         }
     }
     fn arena(count: usize, return_size: usize) -> Arena {
         Arena::new(7, count, 256, return_size, 1_000_000).unwrap()
     }
     #[test]
     fn r1_buffer_contract_freeze_shares_allocation_and_metadata() {
         let mut a = arena(2, 1);
         let mut writable = a.allocate().unwrap();
         let origin = writable.origin();
         writable.writable()[10..14].copy_from_slice(&[2, 3, 5, 7]);
         let f = writable.freeze(10..14, metadata()).unwrap();
         let repair = f.clone();
         assert_eq!(driver_read(&repair).wire, &[2, 3, 5, 7]);
         assert_eq!(repair.origin(), origin);
         assert_eq!(repair.metadata(), metadata());
         assert!(std::ptr::eq(f.bytes().as_ptr(), repair.bytes().as_ptr()));
         drop(f);
         assert_eq!(a.report().loaned, 1); // repair still owns same Box
         drop(repair);
         assert_eq!(a.drain_returns(), 1);
         assert_eq!(a.report().loaned, 0);
         assert_ne!(a.allocate().unwrap().origin().key, origin.key);
     }
     #[test]
     fn r1_arena_capacity_budget_classes_and_invalid_window() {
         assert_eq!(class_for(257), Some(512));
         assert_eq!(class_for(2049), None);
         assert!(Arena::new(1, 2, 256, 1, 10).is_err());
         let mut a = arena(1, 1);
         let b = a.allocate().unwrap();
         assert!(matches!(a.allocate(), Err(BufferContractError::NoCapacity)));
         assert!(matches!(b.freeze(5..300, metadata()),
             Err(BufferContractError::InvalidWindow)));
         assert_eq!(a.drain_returns(), 1); // failed freeze returns the Box
         assert_eq!(a.report().loaned, 0);
     }
     #[test]
     fn r1_return_queue_full_backlog_never_loses_slot() {
         let mut a = arena(4, 1);
         let buffers: Vec<_> = (0..4).map(|_| a.allocate().unwrap()).collect();
         assert!(matches!(a.allocate(), Err(BufferContractError::NoCapacity)));
         drop(buffers); // one channel entry and three fallback returns
         assert_eq!(a.drain_returns(), 4);
         assert_eq!(a.report().free, 4);
         assert_eq!(a.report().loaned, 0);
         for _ in 0..4 { let _ = a.allocate().unwrap(); }
         assert_eq!(a.report().loaned, 0);
     }
     #[test]
     fn r1_stop_last_clone_return_race_is_not_quiesced_early() {
         let mut a = arena(2, 1);
         let f = a.allocate().unwrap().freeze(0..1, metadata()).unwrap();
         let other = f.clone();
         let join = std::thread::spawn(move || drop(other));
         let report = a.stop();
         assert!(report.loaned >= 1);
         assert!(matches!(a.allocate(), Err(BufferContractError::OwnerStopping)));
         drop(f);
         join.join().unwrap();
         assert!(a.quiesced());
         assert_eq!(a.report().loaned, 0);
     }
     #[test]
     fn r1_return_backlog_concurrent_final_drops_fully_drains() {
         let mut a = arena(8, 1);
         let frozen: Vec<_> = (0..8)
             .map(|_| a.allocate().unwrap().freeze(0..1, metadata()).unwrap()).collect();
         let joins: Vec<_> = frozen.into_iter()
             .map(|f| std::thread::spawn(move || drop(f))).collect();
         a.stop();
         for join in joins { join.join().unwrap(); }
         assert!(a.quiesced());
         assert_eq!(a.report().free, 8);
     }
 }
 