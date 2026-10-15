//! R1 ready-only driver boundary. No lock, Arc clone, heap allocation or wait
//! on the synchronous submit path. The caller retains frozen handles and
//! commits the returned outcome; syscall acceptance is NOT a peer receipt.
//! Linux AF_PACKET/sendmmsg, Windows Npcap/Wintun and RX need distinct adapters
//! and native qualifications. `ConnectedUdpTx` is only a native datagram smoke
//! adapter for the first Normal/FEC-off wire round trip, not an AF_PACKET claim.

use crate::{TxBatchOutcome, TxDisposition, TxError};
use std::io::{self, ErrorKind};
use std::net::UdpSocket;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Condvar, Mutex};
use std::time::Instant;
use wbd_types::buffer_contract::{driver_read, DriverRead, FrozenRecordHandle};

pub const MAX_READY_TX: usize = 32;

/// A validated constant-size outcome. `disposition_at` and `iter` allocate
/// nothing; any suffix after an uncertain frame was never attempted.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct BatchResult {
    outcome: TxBatchOutcome,
    count: usize,
}
impl BatchResult {
    pub fn new(outcome: TxBatchOutcome, count: usize) -> Result<Self, TxError> {
        if outcome.accepted_prefix > count { return Err(TxError::InvalidOutcome); }
        let valid = match (outcome.uncertain_index, outcome.error) {
            (None, None) => outcome.accepted_prefix == count,
            (None, Some(TxError::WouldBlock | TxError::IoFailed | TxError::Stopping)) =>
                outcome.accepted_prefix < count,
            (Some(i), Some(TxError::IoUncertain)) =>
                i == outcome.accepted_prefix && i < count,
            _ => false,
        };
        if !valid { return Err(TxError::InvalidOutcome); }
        Ok(Self { outcome, count })
    }
    pub fn disposition_at(&self, index: usize) -> Option<TxDisposition> {
        if index >= self.count { return None; }
        Some(if index < self.outcome.accepted_prefix {
            TxDisposition::Accepted
        } else if self.outcome.uncertain_index == Some(index) {
            TxDisposition::Uncertain
        } else { TxDisposition::NotAttempted })
    }
    pub fn iter(&self) -> impl ExactSizeIterator<Item = TxDisposition> + '_ {
        (0..self.count).map(|i| self.disposition_at(i).expect("bounded index"))
    }
    pub fn accepted_prefix(&self) -> usize { self.outcome.accepted_prefix }
    pub fn uncertain_index(&self) -> Option<usize> { self.outcome.uncertain_index }
    pub fn error(&self) -> Option<TxError> { self.outcome.error }
    pub fn len(&self) -> usize { self.count }
    pub fn is_empty(&self) -> bool { self.count == 0 }
}

#[derive(Default, Debug)]
pub struct ReadyTxLedger {
    pub accepted: u64,
    pub uncertain: u64,
    pub not_attempted: u64,
}
impl ReadyTxLedger {
    /// Check all counters before changing any; no Vec or per-frame scan.
    pub fn record(&mut self, outcome: TxBatchOutcome, count: usize)
        -> Result<BatchResult, TxError> {
        let v = BatchResult::new(outcome, count)?;
        let a = v.accepted_prefix() as u64;
        let u = u64::from(v.uncertain_index().is_some());
        let n = (count - v.accepted_prefix() - u as usize) as u64;
        let na = self.accepted.checked_add(a).ok_or(TxError::CounterOverflow)?;
        let nu = self.uncertain.checked_add(u).ok_or(TxError::CounterOverflow)?;
        let nn = self.not_attempted.checked_add(n).ok_or(TxError::CounterOverflow)?;
        (self.accepted, self.uncertain, self.not_attempted) = (na, nu, nn);
        Ok(v)
    }
}

/// A ready-only datagram syscall. A positive result is the number of bytes
/// copied, never an ACK. Return promptly on EAGAIN/EINTR; never sleep/poll
/// inside the owner loop. Backends MUST keep the borrowed slice read-only.
pub trait ReadyPacketSink {
    fn try_send(&mut self, wire: &[u8]) -> io::Result<usize>;
}

/// Generic reference-only path over M1's FrozenRecordHandle; no frame clones,
/// Arc traffic, mutexes, dynamic dispatch or heap vectors per batch.
/// Each call attempts at most 32 already-ready frames. A short datagram is
/// ambiguous, never split into a second send. The caller must keep the same
/// sealed PN/seq/ciphertext for a retry/repair decision.
pub fn submit_ready<H: FrozenRecordHandle, S: ReadyPacketSink>(
    sink: &mut S, frozen: &[H],
) -> TxBatchOutcome {
    let limit = frozen.len().min(MAX_READY_TX);
    for (i, frame) in frozen.iter().take(limit).enumerate() {
        let wire: DriverRead<'_> = driver_read(frame);
        // Empty frames are invalid at the driver boundary, not a successful
        // zero-length datagram. They have not been submitted.
        if wire.wire.is_empty() {
            return TxBatchOutcome {
                accepted_prefix: i, uncertain_index: None, error: Some(TxError::IoFailed),
            };
        }
        match sink.try_send(wire.wire) {
            Ok(n) if n == wire.wire.len() => {},
            Ok(_) => return TxBatchOutcome {
                accepted_prefix: i, uncertain_index: Some(i), error: Some(TxError::IoUncertain),
            },
            Err(e) if e.kind() == ErrorKind::WouldBlock => return TxBatchOutcome {
                accepted_prefix: i, uncertain_index: None, error: Some(TxError::WouldBlock),
            },
            // EINTR or all other unclassified errors are conservative:
            // an in-flight/driver-specific send may have happened.
            Err(_) => return TxBatchOutcome {
                accepted_prefix: i, uncertain_index: Some(i), error: Some(TxError::IoUncertain),
            },
        }
    }
    if limit < frozen.len() {
        TxBatchOutcome {
            accepted_prefix: limit, uncertain_index: None, error: Some(TxError::WouldBlock),
        }
    } else { TxBatchOutcome::copied_all(limit) }
}

/// Native connected UDP proof adapter (Linux/Windows OS datagram syscall);
/// intentionally NOT AF_PACKET or Npcap, and never claims to have sent a
/// TCP-like outer packet. Explicitly nonblocking; no kernel buffer loan.
pub struct ConnectedUdpTx(UdpSocket);
impl ConnectedUdpTx {
    pub fn new(socket: UdpSocket) -> io::Result<Self> {
        socket.set_nonblocking(true)?;
        socket.peer_addr()?; // fail closed if no connected destination
        Ok(Self(socket))
    }
}
impl ReadyPacketSink for ConnectedUdpTx {
    fn try_send(&mut self, wire: &[u8]) -> io::Result<usize> { self.0.send(wire) }
}

// Atomic stop bit and count are a single CAS state: after begin_stop wins,
// no new borrow may slip through, even if another thread was acquiring.
const STOP: usize = 1usize << (usize::BITS - 1);
const COUNT_MASK: usize = STOP - 1;
#[derive(Default)]
pub struct BorrowFence {
    state: AtomicUsize,
    // Only the shutdown waiter or the LAST completion touches this mutex.
    // There is no mutex on acquire nor on non-final completion.
    wait_lock: Mutex<()>,
    released: Condvar,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum BorrowError { Stopping, TooManyLoans }
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum StopResult { Drained, Pending { outstanding: usize } }

/// RAII guard for a copied synchronous syscall: one borrowed fence count per
/// entire batch, but no Arc clone, mutex, heap buffer, or per-record lifetime
/// bookkeeping. The caller's &[FrozenHandle] keeps memory alive for sendmmsg.
pub struct ReadyBatchGuard<'a> { fence: &'a BorrowFence }
impl Drop for ReadyBatchGuard<'_> {
    fn drop(&mut self) { self.fence.release_one(); }
}

/// An OS completion token *owns* a frozen allocation, not a borrowed raw
/// pointer. Move this token to the backend's completion/cancel bookkeeping.
/// Dropping is ONLY permitted after driver completion or confirmed cancel;
/// timeout does not drop or revoke a token. No extra clone on construction.
pub struct KernelLoan<H: FrozenRecordHandle> {
    record: H,
    fence: Arc<BorrowFence>,
}
impl<H: FrozenRecordHandle> KernelLoan<H> {
    pub fn read(&self) -> DriverRead<'_> { driver_read(&self.record) }
}
impl<H: FrozenRecordHandle> Drop for KernelLoan<H> {
    fn drop(&mut self) {
        self.fence.release_one();
    }
}
impl BorrowFence {
    fn release_one(&self) {
        let old = self.state.fetch_sub(1, Ordering::AcqRel);
        debug_assert!(old & COUNT_MASK != 0);
        // A hot-path last release is lock-free unless a shutdown is waiting.
        if old & STOP != 0 && old & COUNT_MASK == 1 {
            let _guard = self.wait_lock.lock().unwrap_or_else(|e| e.into_inner());
            self.released.notify_all();
        }
    }

    /// Enter a bounded ready-only copied-syscall batch. begin_stop is atomic
    /// with the CAS registration; shutdown cannot drain while a send is live.
    pub fn try_enter_ready(&self) -> Result<ReadyBatchGuard<'_>, BorrowError> {
        let mut cur = self.state.load(Ordering::Acquire);
        loop {
            if cur & STOP != 0 { return Err(BorrowError::Stopping); }
            if cur & COUNT_MASK == COUNT_MASK { return Err(BorrowError::TooManyLoans); }
            match self.state.compare_exchange_weak(
                cur, cur + 1, Ordering::AcqRel, Ordering::Acquire,
            ) {
                Ok(_) => return Ok(ReadyBatchGuard { fence: self }),
                Err(updated) => cur = updated,
            }
        }
    }

    /// Takes ownership, NOT a clone, and returns it on failed acquisition.
    /// The common synchronous send should never acquire a loan at all.
    pub fn try_loan<H: FrozenRecordHandle>(self: &Arc<Self>, record: H)
        -> Result<KernelLoan<H>, (BorrowError, H)> {
        let mut cur = self.state.load(Ordering::Acquire);
        loop {
            if cur & STOP != 0 { return Err((BorrowError::Stopping, record)); }
            if cur & COUNT_MASK == COUNT_MASK {
                return Err((BorrowError::TooManyLoans, record));
            }
            match self.state.compare_exchange_weak(
                cur, cur + 1, Ordering::AcqRel, Ordering::Acquire,
            ) {
                Ok(_) => return Ok(KernelLoan { record, fence: Arc::clone(self) }),
                Err(updated) => cur = updated,
            }
        }
    }
    pub fn begin_stop(&self) { self.state.fetch_or(STOP, Ordering::AcqRel); }
    pub fn outstanding(&self) -> usize {
        self.state.load(Ordering::Acquire) & COUNT_MASK
    }
    pub fn is_stopping(&self) -> bool {
        self.state.load(Ordering::Acquire) & STOP != 0
    }
    /// Monotonic, bounded wait. `Pending` forbids device EndSession/free,
    /// unmap, or buffer release. Retain backend and tokens for late completion
    /// and call again; `Drained` alone permits driver-owned cleanup.
    pub fn wait_drained_until(&self, deadline: Instant) -> StopResult {
        self.begin_stop();
        let mut guard = self.wait_lock.lock().unwrap_or_else(|e| e.into_inner());
        loop {
            let n = self.outstanding();
            if n == 0 { return StopResult::Drained; }
            let now = Instant::now();
            if now >= deadline { return StopResult::Pending { outstanding: n }; }
            let remaining = deadline.saturating_duration_since(now);
            let (g, _) = self.released.wait_timeout(guard, remaining)
                .unwrap_or_else(|e| e.into_inner());
            guard = g;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::mpsc;
    use std::thread;
    use std::time::Duration;
    use wbd_types::buffer_contract::{BufferOrigin, FrozenMetadata};
    use wbd_types::{BufferKey, LaneKey, RecordPn, SeqOffset, TunnelKey};

    #[derive(Clone)]
    struct FakeFrozen { wire: Arc<[u8]>, metadata: FrozenMetadata }
    impl FrozenRecordHandle for FakeFrozen {
        fn origin(&self) -> BufferOrigin {
            BufferOrigin { owner_arena: 9, key: BufferKey {slot: 3, generation: 1} }
        }
        fn metadata(&self) -> FrozenMetadata { self.metadata }
        fn bytes(&self) -> &[u8] { &self.wire }
    }
    fn frame(b: &[u8], pn: u64) -> FakeFrozen {
        FakeFrozen {
            wire: Arc::from(b),
            metadata: FrozenMetadata {
                lane: LaneKey {tunnel: TunnelKey {slot: 1,generation: 1},slot: 2,generation: 1},
                seq: SeqOffset(pn * 12), pn: RecordPn(pn), carrier_snapshot: 7,
            },
        }
    }
    struct FakeSink { replies: Vec<io::Result<usize>>, calls: usize }
    impl ReadyPacketSink for FakeSink {
        fn try_send(&mut self, wire: &[u8]) -> io::Result<usize> {
            assert!(!wire.is_empty());
            let i = self.calls;
            self.calls += 1;
            std::mem::replace(&mut self.replies[i], Ok(0))
        }
    }
    #[test]
    fn r1_driver_prefix_uncertain_and_untouched_are_constant_size() {
        let frames = [frame(b"one", 7),frame(b"two", 8),frame(b"three", 9),frame(b"four",10)];
        let mut sink = FakeSink {replies: vec![Ok(3), Ok(3), Ok(2)],calls: 0};
        let mut ledger = ReadyTxLedger::default();
        let result = ledger.record(submit_ready(&mut sink, &frames), frames.len()).unwrap();
        assert_eq!(sink.calls, 3);
        assert_eq!(result.accepted_prefix(), 2);
        assert_eq!(result.uncertain_index(), Some(2));
        assert_eq!(result.iter().collect::<Vec<_>>(), vec![
            TxDisposition::Accepted,TxDisposition::Accepted,
            TxDisposition::Uncertain,TxDisposition::NotAttempted,
        ]);
        assert_eq!((ledger.accepted,ledger.uncertain,ledger.not_attempted),(2,1,1));
        assert_eq!(frames[2].metadata.pn, RecordPn(9)); // No reseal.
    }
    #[test]
    fn r1_driver_wouldblock_and_interrupt_do_not_reclassify_suffix() {
        let frames = [frame(b"A",1),frame(b"B",2),frame(b"C",3)];
        let mut sink = FakeSink {replies: vec![Ok(1), Err(io::Error::from(ErrorKind::WouldBlock))],calls:0};
        let got = BatchResult::new(submit_ready(&mut sink,&frames),3).unwrap();
        assert_eq!(got.iter().collect::<Vec<_>>(),vec![
            TxDisposition::Accepted,TxDisposition::NotAttempted,TxDisposition::NotAttempted]);
        assert_eq!(sink.calls,2);
        let mut interrupted = FakeSink {replies: vec![Err(io::Error::from(ErrorKind::Interrupted))],calls:0};
        let got = BatchResult::new(submit_ready(&mut interrupted,&frames),3).unwrap();
        assert_eq!(got.iter().collect::<Vec<_>>(),vec![
            TxDisposition::Uncertain,TxDisposition::NotAttempted,TxDisposition::NotAttempted]);
        assert_eq!(interrupted.calls,1);
    }
    #[test]
    fn r1_driver_bounded_batch_and_invalid_accounting_fail_closed() {
        let frames: Vec<_> = (0..33).map(|i|frame(b"A",i)).collect();
        let mut sink = FakeSink {replies: (0..32).map(|_|Ok(1)).collect(),calls:0};
        let got = BatchResult::new(submit_ready(&mut sink,&frames),33).unwrap();
        assert_eq!(sink.calls,MAX_READY_TX);
        assert_eq!(got.disposition_at(32),Some(TxDisposition::NotAttempted));
        let mut ledger=ReadyTxLedger{accepted:u64::MAX,uncertain:0,not_attempted:0};
        assert_eq!(ledger.record(TxBatchOutcome::copied_all(1),1),Err(TxError::CounterOverflow));
        assert_eq!(ledger.accepted,u64::MAX);
        for invalid in [
            TxBatchOutcome::copied_all(34),
            TxBatchOutcome {accepted_prefix:0,uncertain_index:Some(1),error:Some(TxError::IoUncertain)},
            TxBatchOutcome {accepted_prefix:0,uncertain_index:None,error:None},
        ] {
            assert_eq!(BatchResult::new(invalid,33),Err(TxError::InvalidOutcome));
        }
    }
    #[test]
    fn r1_borrow_stop_timeout_preserves_live_frozen_memory_until_completion() {
        let fence = Arc::new(BorrowFence::default());
        let f=frame(b"ciphertext",23);
        let original=Arc::as_ptr(&f.wire);
        let loan=fence.try_loan(f).ok().unwrap();
        assert_eq!(Arc::as_ptr(&loan.record.wire),original);
        assert_eq!(loan.read().wire,b"ciphertext");
        assert_eq!(fence.wait_drained_until(Instant::now()),StopResult::Pending{outstanding:1});
        assert_eq!(fence.outstanding(),1);
        let candidate=frame(b"new",24);
        let rejected=fence.try_loan(candidate);
        assert!(matches!(rejected, Err((BorrowError::Stopping, _))));
        let (tx,rx)=mpsc::channel();
        let clone=Arc::clone(&fence);
        let waiter=thread::spawn(move || tx.send(clone.wait_drained_until(Instant::now()+Duration::from_secs(2))).unwrap());
        assert_eq!(loan.read().wire,b"ciphertext");
        drop(loan); // verified kernel completion/cancel, NOT timer expiry
        assert_eq!(rx.recv_timeout(Duration::from_secs(2)).unwrap(),StopResult::Drained);
        waiter.join().unwrap();
        assert_eq!(fence.wait_drained_until(Instant::now()),StopResult::Drained);
    }
    #[test]
    fn r1_borrow_stop_and_acquire_race_is_fenced() {
        let fence = Arc::new(BorrowFence::default());
        let existing=fence.try_loan(frame(b"held",1)).ok().unwrap();
        let f2=Arc::clone(&fence);
        let t=thread::spawn(move|| {
            for i in 0..500 { match f2.try_loan(frame(b"new",i)) {
                Ok(loan) => drop(loan), Err((BorrowError::Stopping,_)) => return true,
                Err(_) => return false,
            }}
            f2.is_stopping()
        });
        fence.begin_stop();
        assert!(t.join().unwrap());
        assert_eq!(fence.wait_drained_until(Instant::now()),StopResult::Pending{outstanding:1});
        drop(existing);
        assert_eq!(fence.wait_drained_until(Instant::now()),StopResult::Drained);
    }
    #[cfg(target_os="linux")]
    #[test]
    fn r1_linux_native_udp_single_wire_roundtrip_not_af_packet() {
        let receiver=UdpSocket::bind("127.0.0.1:0").unwrap();
        receiver.set_read_timeout(Some(Duration::from_secs(2))).unwrap();
        let sender=UdpSocket::bind("127.0.0.1:0").unwrap();
        sender.connect(receiver.local_addr().unwrap()).unwrap();
        let mut native=ConnectedUdpTx::new(sender).unwrap();
        let frames=[frame(b"normal-off-frozen-record",91)];
        let result=BatchResult::new(submit_ready(&mut native,&frames),1).unwrap();
        assert_eq!(result.disposition_at(0),Some(TxDisposition::Accepted));
        let mut received=[0u8;64];
        let n=receiver.recv(&mut received).unwrap();
        assert_eq!(&received[..n],frames[0].bytes());
    }
}