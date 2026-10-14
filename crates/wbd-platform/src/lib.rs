//! R0 platform/send ownership contract, not a native socket driver.
//! The fake driver and fake clock live only in tests. This crate cannot
//! depend on wbd-engine; only the engine will compose real clocks/drivers.
//! No FFI types or wire layouts are defined here.
#![forbid(unsafe_code)]

/// R1 verified, bounded ready-only adapter; production native AF_PACKET/Windows not enabled.
pub mod r1;

use std::sync::{Arc, Condvar, Mutex};
use wbd_types::{LaneKey, MonoNs, RecordPn, SeqOffset};

pub trait MonoClock {
    fn now(&self) -> MonoNs;
}

pub fn deadline_after(clock: &impl MonoClock, delta: u64) -> Option<MonoNs> {
    clock.now().checked_after(delta)
}

pub fn deadline_reached(clock: &impl MonoClock, due: MonoNs) -> bool {
    clock.now().0 >= due.0
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum TxError {
    SealRejected,
    PnExhausted,
    WouldBlock,
    IoUncertain,
    IoFailed,
    InvalidOutcome,
    CounterOverflow,
    Stopping,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum TxDisposition {
    /// The driver confirms the system call accepted/copy-completed the frame,
    /// NOT that the peer received or acknowledged the packet.
    Accepted,
    /// A partial/uncertain syscall: NO confirmed acceptance or ACK inference.
    Uncertain,
    /// The driver did not attempt this frame. Its reserved PN remains burned.
    NotAttempted,
}

/// A kernel driver may either have copied data before returning, or hold an
/// explicit loan that keeps the backing allocation alive through shutdown.
/// Begin-stop fences out new loans. Stop waits for existing loans to drop.
#[derive(Default)]
pub struct BorrowFence {
    state: Mutex<LoanState>,
    released: Condvar,
}
#[derive(Default)]
struct LoanState {
    stopping: bool,
    outstanding: usize,
}
pub struct KernelLoan {
    fence: Arc<BorrowFence>,
    bytes: Arc<[u8]>,
}
impl KernelLoan {
    pub fn bytes(&self) -> &[u8] { &self.bytes }
}
impl Drop for KernelLoan {
    fn drop(&mut self) {
        let mut state = self.fence.state.lock().unwrap_or_else(|e| e.into_inner());
        // Only trusted in-process loan creation can increment outstanding.
        debug_assert!(state.outstanding > 0);
        state.outstanding -= 1;
        if state.outstanding == 0 {
            self.fence.released.notify_all();
        }
    }
}
impl BorrowFence {
    fn acquire(self: &Arc<Self>, bytes: Arc<[u8]>) -> Result<KernelLoan, TxError> {
        let mut state = self.state.lock().unwrap_or_else(|e| e.into_inner());
        if state.stopping { return Err(TxError::Stopping); }
        state.outstanding = state.outstanding.checked_add(1).ok_or(TxError::CounterOverflow)?;
        Ok(KernelLoan { fence: Arc::clone(self), bytes })
    }
    /// Mark shutdown synchronously; no new driver loans can race through.
    pub fn begin_stop(&self) {
        let mut state = self.state.lock().unwrap_or_else(|e| e.into_inner());
        state.stopping = true;
    }
    /// For an owned shutdown after begin_stop, wait until the driver has
    /// completed or cancelled every outstanding kernel loan.
    pub fn wait_drained(&self) {
        let mut state = self.state.lock().unwrap_or_else(|e| e.into_inner());
        while state.outstanding > 0 {
            state = self.released.wait(state).unwrap_or_else(|e| e.into_inner());
        }
    }
    pub fn outstanding(&self) -> usize {
        self.state.lock().unwrap_or_else(|e| e.into_inner()).outstanding
    }
}

pub struct FrozenFrame {
    pub lane: LaneKey,
    pub seq: SeqOffset,
    pub pn: RecordPn,
    pub carrier_snapshot: u64,
    bytes: Arc<[u8]>,
    fence: Arc<BorrowFence>,
}
impl FrozenFrame {
    pub fn bytes(&self) -> &[u8] { &self.bytes }
    pub fn borrow_for_driver(&self) -> Result<KernelLoan, TxError> {
        self.fence.acquire(Arc::clone(&self.bytes))
    }
}

/// Monotonic PN reservations never roll back, even if sealing or driver send
/// fails. The record codec supplies the bytes once; no later repair re-seals.
#[derive(Default)]
pub struct PnAllocator {
    next: Option<u64>,
}
impl PnAllocator {
    pub fn new(start: u64) -> Self { Self { next: Some(start) } }
    pub fn reserve(&mut self) -> Result<RecordPn, TxError> {
        let current = self.next.ok_or(TxError::PnExhausted)?;
        self.next = current.checked_add(1);
        Ok(RecordPn(current))
    }
    pub fn freeze<F>(
        &mut self,
        lane: LaneKey,
        seq: SeqOffset,
        carrier_snapshot: u64,
        fence: Arc<BorrowFence>,
        seal_once: F,
    ) -> Result<FrozenFrame, TxError>
    where F: FnOnce(RecordPn) -> Result<Vec<u8>, TxError> {
        let pn = self.reserve()?; // Must be consumed BEFORE sealing.
        let bytes: Arc<[u8]> = seal_once(pn)?.into();
        Ok(FrozenFrame { lane, seq, pn, carrier_snapshot, bytes, fence })
    }
}

/// accepted_prefix counts frames confirmed copied by the driver.
/// uncertain_index (when present) MUST equal accepted_prefix and remains
/// ambiguous. All subsequent frames are unattempted. No guessing of success.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct TxBatchOutcome {
    pub accepted_prefix: usize,
    pub uncertain_index: Option<usize>,
    pub error: Option<TxError>,
}
impl TxBatchOutcome {
    pub fn copied_all(n: usize) -> Self {
        Self { accepted_prefix: n, uncertain_index: None, error: None }
    }
    pub fn classify(self, count: usize) -> Result<Vec<TxDisposition>, TxError> {
        if self.accepted_prefix > count {
            return Err(TxError::InvalidOutcome);
        }
        match (self.uncertain_index, self.error) {
            (None, None) if self.accepted_prefix == count => {}
            (None, Some(TxError::WouldBlock | TxError::IoFailed))
                if self.accepted_prefix < count => {}
            (Some(i), Some(TxError::IoUncertain))
                if i == self.accepted_prefix && i < count => {}
            _ => return Err(TxError::InvalidOutcome),
        }
        Ok((0..count).map(|i| {
            if i < self.accepted_prefix { TxDisposition::Accepted }
            else if Some(i) == self.uncertain_index { TxDisposition::Uncertain }
            else { TxDisposition::NotAttempted }
        }).collect())
    }
}

pub trait TxDriver {
    fn submit(&mut self, batch: &[FrozenFrame]) -> TxBatchOutcome;
}

#[derive(Default)]
pub struct TxLedger {
    pub syscall_accepted: u64,
    pub uncertain: u64,
    pub not_attempted: u64,
}
impl TxLedger {
    pub fn submit<D: TxDriver>(
        &mut self, driver: &mut D, frames: &[FrozenFrame],
    ) -> Result<Vec<TxDisposition>, TxError> {
        let classifications = driver.submit(frames).classify(frames.len())?;
        let accepted = classifications.iter().filter(|x| **x == TxDisposition::Accepted).count() as u64;
        let uncertain = classifications.iter().filter(|x| **x == TxDisposition::Uncertain).count() as u64;
        let not_attempted = classifications.iter().filter(|x| **x == TxDisposition::NotAttempted).count() as u64;
        let next_a = self.syscall_accepted.checked_add(accepted).ok_or(TxError::CounterOverflow)?;
        let next_u = self.uncertain.checked_add(uncertain).ok_or(TxError::CounterOverflow)?;
        let next_n = self.not_attempted.checked_add(not_attempted).ok_or(TxError::CounterOverflow)?;
        self.syscall_accepted = next_a;
        self.uncertain = next_u;
        self.not_attempted = next_n;
        Ok(classifications)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{cell::Cell, sync::mpsc, thread, time::Duration};
    use wbd_types::TunnelKey;

    fn lane() -> LaneKey {
        LaneKey { tunnel: TunnelKey { slot: 1, generation: 2 }, slot: 3, generation: 4 }
    }
    struct FakeClock(Cell<u64>);
    impl MonoClock for FakeClock { fn now(&self) -> MonoNs { MonoNs(self.0.get()) } }
    struct FakeDriver {
        reply: TxBatchOutcome,
        loans: Vec<KernelLoan>,
        borrow_index: Option<usize>,
    }
    impl TxDriver for FakeDriver {
        fn submit(&mut self, batch: &[FrozenFrame]) -> TxBatchOutcome {
            if let Some(i) = self.borrow_index {
                self.loans.push(batch[i].borrow_for_driver().expect("driver borrow"));
            }
            self.reply
        }
    }
    fn batch(n: usize, fence: &Arc<BorrowFence>, pn: &mut PnAllocator) -> Vec<FrozenFrame> {
        (0..n).map(|i| pn.freeze(
            lane(), SeqOffset(i as u64), 7, Arc::clone(fence),
            |num| Ok(vec![num.0 as u8, i as u8]),
        ).unwrap()).collect()
    }

    #[test]
    fn r0_i01_prefix_partial_uncertain_does_not_count_as_ack() {
        let fence = Arc::new(BorrowFence::default());
        let mut pn = PnAllocator::new(7);
        let frames = batch(4, &fence, &mut pn);
        let mut fake = FakeDriver {
            reply: TxBatchOutcome {
                accepted_prefix: 2, uncertain_index: Some(2),
                error: Some(TxError::IoUncertain),
            }, loans: vec![], borrow_index: None,
        };
        let mut ledger = TxLedger::default();
        assert_eq!(ledger.submit(&mut fake, &frames).unwrap(),
            vec![TxDisposition::Accepted, TxDisposition::Accepted,
                 TxDisposition::Uncertain, TxDisposition::NotAttempted]);
        assert_eq!((ledger.syscall_accepted, ledger.uncertain, ledger.not_attempted), (2,1,1));
        assert_eq!(frames.iter().map(|f| f.pn.0).collect::<Vec<_>>(), vec![7,8,9,10]);
        // Arrival/ACK not established by syscall prefix; no ACK counter exists.
        assert_eq!(pn.reserve().unwrap(), RecordPn(11));
    }

    #[test]
    fn r0_i01_zero_prefix_failure_does_not_block_fresh() {
        let fence=Arc::new(BorrowFence::default());
        let mut pn=PnAllocator::new(90);
        let bad=batch(2,&fence,&mut pn);
        let mut fake=FakeDriver {reply: TxBatchOutcome {
            accepted_prefix:0,uncertain_index:None,error:Some(TxError::WouldBlock),
        },loans:vec![],borrow_index:None};
        let mut ledger=TxLedger::default();
        assert_eq!(ledger.submit(&mut fake,&bad).unwrap(),
            vec![TxDisposition::NotAttempted,TxDisposition::NotAttempted]);
        let fresh=batch(1,&fence,&mut pn);
        assert_eq!(fresh[0].pn,RecordPn(92));
        fake.reply=TxBatchOutcome::copied_all(1);
        assert_eq!(ledger.submit(&mut fake,&fresh).unwrap(),vec![TxDisposition::Accepted]);
        assert_eq!((ledger.syscall_accepted,ledger.not_attempted),(1,2));
    }

    #[test]
    fn r0_c01_failed_seal_burns_pn_and_u64_never_wraps() {
        let fence=Arc::new(BorrowFence::default());
        let mut pn=PnAllocator::new(u64::MAX-1);
        assert!(matches!(pn.freeze(lane(),SeqOffset(0),1,Arc::clone(&fence),
            |_pn|Err(TxError::SealRejected)),Err(TxError::SealRejected)));
        let immutable=pn.freeze(lane(),SeqOffset(1),1,Arc::clone(&fence),
            |n|Ok(vec![n.0 as u8,23])).unwrap();
        assert_eq!(immutable.pn,RecordPn(u64::MAX));
        assert_eq!(immutable.bytes(),&[255,23]);
        assert_eq!(pn.reserve(),Err(TxError::PnExhausted));
        assert_eq!(immutable.bytes(),&[255,23]); // frozen immutable; no re-seal.
    }

    #[test]
    fn r0_i01_invalid_driver_accounting_is_fail_closed() {
        let fence=Arc::new(BorrowFence::default());
        let mut pn=PnAllocator::new(0);
        let frames=batch(2,&fence,&mut pn);
        let bad=[
            TxBatchOutcome::copied_all(3),
            TxBatchOutcome {accepted_prefix:1,uncertain_index:None,error:None},
            TxBatchOutcome {accepted_prefix:1,uncertain_index:Some(0),error:Some(TxError::IoUncertain)},
            TxBatchOutcome {accepted_prefix:2,uncertain_index:Some(2),error:Some(TxError::IoUncertain)},
            TxBatchOutcome {accepted_prefix:0,uncertain_index:Some(0),error:Some(TxError::WouldBlock)},
        ];
        let mut ledger=TxLedger::default();
        for reply in bad {
            let mut fake=FakeDriver {reply,loans:vec![],borrow_index:None};
            assert!(matches!(ledger.submit(&mut fake,&frames),Err(TxError::InvalidOutcome)));
        }
        assert_eq!((ledger.syscall_accepted,ledger.uncertain,ledger.not_attempted),(0,0,0));
    }

    #[test]
    fn r0_b01_stop_waits_for_driver_borrow_and_rejects_new_loans() {
        let fence=Arc::new(BorrowFence::default());
        let mut pn=PnAllocator::new(1);
        let mut frames=batch(1,&fence,&mut pn);
        let frame=frames.pop().unwrap();
        let loan=frame.borrow_for_driver().unwrap();
        assert_eq!(loan.bytes(),&[1,0]);
        drop(frame); // backing bytes must survive owner destruction
        assert_eq!(loan.bytes(),&[1,0]);
        assert_eq!(fence.outstanding(),1);
        fence.begin_stop();
        let (done_tx,done_rx)=mpsc::channel();
        let copied=Arc::clone(&fence);
        let handle=thread::spawn(move||{copied.wait_drained();done_tx.send(()).unwrap();});
        assert!(matches!(done_rx.try_recv(),Err(mpsc::TryRecvError::Empty)));
        assert_eq!(fence.outstanding(),1);
        drop(loan);
        assert!(done_rx.recv_timeout(Duration::from_secs(3)).is_ok());
        handle.join().unwrap();
        assert_eq!(fence.outstanding(),0);
        assert!(matches!(pn.freeze(lane(),SeqOffset(3),1,Arc::clone(&fence),
            |_n|Ok(vec![5])).unwrap().borrow_for_driver(),Err(TxError::Stopping)));
    }

    #[test]
    fn r0_b01_fake_driver_returns_while_holding_a_live_loan() {
        let fence=Arc::new(BorrowFence::default());
        let mut pn=PnAllocator::new(10);
        let frames=batch(3,&fence,&mut pn);
        let mut fake=FakeDriver {
            reply:TxBatchOutcome {
                accepted_prefix:1,uncertain_index:Some(1),error:Some(TxError::IoUncertain),
            },
            loans:vec![],borrow_index:Some(1),
        };
        let mut ledger=TxLedger::default();
        let statuses=ledger.submit(&mut fake,&frames).unwrap();
        assert_eq!(statuses[1],TxDisposition::Uncertain);
        assert_eq!(fake.loans[0].bytes(),frames[1].bytes());
        assert_eq!(fence.outstanding(),1);
        fence.begin_stop();
        assert!(matches!(frames[0].borrow_for_driver(),Err(TxError::Stopping)));
        drop(frames);
        assert_eq!(fake.loans[0].bytes(),&[11,1]);
        fake.loans.clear(); // driver completes/cancels uncertain submission
        fence.wait_drained();
        assert_eq!(fence.outstanding(),0);
    }

    #[test]
    fn r0_r01_injected_fake_clock_saturates_and_never_uses_wall_time() {
        let clock=FakeClock(Cell::new(100));
        let due=deadline_after(&clock,20).unwrap();
        assert!(!deadline_reached(&clock,due));
        clock.0.set(119);
        assert!(!deadline_reached(&clock,due));
        clock.0.set(120);
        assert!(deadline_reached(&clock,due));
        clock.0.set(u64::MAX);
        assert_eq!(deadline_after(&clock,1),None);
        assert!(deadline_reached(&clock,due));
    }
}
