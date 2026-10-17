//! Linux x86_64 GNU sendmmsg syscall island. Native, but not AF_PACKET.
//!
//! This module intentionally owns the only unsafe FFI in wbd-platform.
//! ABI source: Linux sendmmsg(2), glibc sys/socket.h (mmsghdr / msghdr),
//! sys/uio.h (iovec). The 64-bit GNU Linux layout is checked in a native
//! test; other architectures/libcs do not compile this island.
//! MSG_DONTWAIT=0x40, EAGAIN/EWOULDBLOCK=11, EINTR=4 on Linux x86_64.
//!
//! Every frame is a full, immutable packet. Each syscall copies it before
//! returning. The guard fences shutdown for the call; no kernel owns the
//! buffer after return, so it must NOT acquire an async KernelLoan.
//! Accepted is a kernel send result, NOT a peer ACK/record receipt.
use crate::{TxBatchOutcome, TxError};
use crate::r1::{BorrowError, BorrowFence, MAX_READY_TX};
use std::ffi::{c_int, c_uint, c_void};
use std::io;
use std::net::UdpSocket;
use std::os::fd::{AsRawFd, RawFd};
use std::ptr;
use wbd_types::buffer_contract::{driver_read, FrozenRecordHandle};

const MSG_DONTWAIT: c_int = 0x40;
const EAGAIN: i32 = 11;
const EINTR: i32 = 4;
const EMSGSIZE: i32 = 90;
const ENODEV: i32 = 19;
const ENETDOWN: i32 = 100;
const ENETUNREACH: i32 = 101;
const EHOSTUNREACH: i32 = 113;

/// A typed, allocation-free signal beside the existing exact prefix/uncertain
/// outcome. Linux loses errno when sendmmsg returns a positive partial count;
/// PartialErrnoUnavailable is NOT evidence that the suffix was accepted.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum KernelSendSignal {
    None,
    Backpressure,
    Interrupted,
    MtuExceeded,
    DeviceUnavailable,
    RouteUnavailable,
    PartialErrnoUnavailable,
    OtherErrno(i32),
    AmbiguousCompletion,
    PreflightRejected,
    Stopping,
}
impl KernelSendSignal {
    /// Owner must invalidate its route/MTU snapshot before another DATA send.
    /// Backpressure and EINTR alone do not authorize a refreshed budget.
    pub fn invalidates_path(self) -> bool {
        matches!(self, Self::MtuExceeded | Self::DeviceUnavailable |
            Self::RouteUnavailable | Self::PartialErrnoUnavailable |
            Self::OtherErrno(_) | Self::AmbiguousCompletion)
    }
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct KernelSendReport {
    pub outcome: TxBatchOutcome,
    pub signal: KernelSendSignal,
}

#[repr(C)]
#[derive(Clone, Copy)]
struct CIovec { iov_base: *mut c_void, iov_len: usize }
impl CIovec {
    const fn empty() -> Self { Self { iov_base: ptr::null_mut(), iov_len: 0 } }
}

#[repr(C)]
#[derive(Clone, Copy)]
struct CMsghdr {
    msg_name: *mut c_void,
    msg_namelen: u32,
    msg_iov: *mut CIovec,
    msg_iovlen: usize,
    msg_control: *mut c_void,
    msg_controllen: usize,
    msg_flags: c_int,
}
impl CMsghdr {
    const fn empty() -> Self {
        Self {msg_name: ptr::null_mut(), msg_namelen: 0,
            msg_iov: ptr::null_mut(), msg_iovlen: 0,
            msg_control: ptr::null_mut(), msg_controllen: 0, msg_flags: 0}
    }
}
#[repr(C)]
#[derive(Clone, Copy)]
struct CMmsghdr { msg_hdr: CMsghdr, msg_len: c_uint }
impl CMmsghdr {
    const fn empty() -> Self { Self { msg_hdr: CMsghdr::empty(), msg_len: 0 } }
}
unsafe extern "C" {
    fn sendmmsg(sockfd: c_int, msgvec: *mut CMmsghdr, vlen: c_uint, flags: c_int) -> c_int;
}
fn not_sent(error: TxError) -> TxBatchOutcome {
    TxBatchOutcome { accepted_prefix: 0, uncertain_index: None, error: Some(error) }
}
fn uncertain(index: usize) -> TxBatchOutcome {
    TxBatchOutcome {
        accepted_prefix: index, uncertain_index: Some(index), error: Some(TxError::IoUncertain),
    }
}
fn accepted_prefix(n: usize, count: usize, total: usize) -> TxBatchOutcome {
    if n == total { TxBatchOutcome::copied_all(n) }
    else if n < count {
        // Linux discards the specific errno after partial success. The kernel
        // reports a definite sent prefix; the rest was not sent by this call.
        TxBatchOutcome {accepted_prefix:n, uncertain_index:None, error:Some(TxError::IoFailed)}
    } else {
        // The batch cap (32), not a kernel failure, left a ready suffix.
        TxBatchOutcome {accepted_prefix:n, uncertain_index:None, error:Some(TxError::WouldBlock)}
    }
}

/// Separable classification makes rare errno / short-count branches
/// deterministic without falsely claiming kernel-injected EINTR/EAGAIN.
/// reported_lens contains only kernel-completed message lengths.
fn classify(sent: c_int, errno: Option<i32>, submitted: usize,
            total: usize, reported_lens: &[u32], expected_lens: &[usize])
    -> TxBatchOutcome
{
    if submitted == 0 { return TxBatchOutcome::copied_all(0); }
    if sent < 0 {
        return match errno {
            Some(EAGAIN) => not_sent(TxError::WouldBlock),
            Some(EINTR) | _ => uncertain(0),
        };
    }
    let n = sent as usize;
    if n == 0 || n > submitted { return uncertain(0); }
    for i in 0..n {
        if reported_lens[i] as usize != expected_lens[i] {
            // Short datagram success violates the atomic-datagram invariant.
            // Quarantine this and remaining frames on a backend that can
            // report it; do NOT split/resend the ambiguous datagram.
            return uncertain(i);
        }
    }
    accepted_prefix(n, submitted, total)
}

/// Native connected UDP fixture, NOT a raw-TCP packet transport.
/// The detailed report carries errno/partial invalidation without changing
/// the legacy TxBatchOutcome-only caller's contract.
/// Caller owns the frozen records and keeps socket/device lifetime through
/// the call; the fence prevents concurrently completing stop.
pub fn submit_connected_udp<H: FrozenRecordHandle>(
    socket: &UdpSocket, frozen: &[H], fence: &BorrowFence,
) -> TxBatchOutcome {
    submit_connected_udp_detailed(socket, frozen, fence).outcome
}

pub fn submit_connected_udp_detailed<H: FrozenRecordHandle>(
    socket: &UdpSocket, frozen: &[H], fence: &BorrowFence,
) -> KernelSendReport {
    if socket.peer_addr().is_err() {
        return KernelSendReport { outcome: not_sent(TxError::IoFailed),
            signal: KernelSendSignal::PreflightRejected };
    }
    submit_fd_detailed(socket.as_raw_fd(), frozen, fence)
}

#[cfg(test)]
fn submit_fd<H: FrozenRecordHandle>(fd: RawFd, frozen: &[H],
                                   fence: &BorrowFence) -> TxBatchOutcome {
    submit_fd_detailed(fd, frozen, fence).outcome
}

fn submit_fd_detailed<H: FrozenRecordHandle>(fd: RawFd, frozen: &[H],
                                            fence: &BorrowFence) -> KernelSendReport {
    // Register before inspecting the bytes; shutdown may race this CAS but
    // cannot finish with a live synchronous send.
    let _inflight = match fence.try_enter_ready() {
        Ok(token) => token,
        Err(BorrowError::Stopping) => return KernelSendReport {
            outcome: not_sent(TxError::Stopping), signal: KernelSendSignal::Stopping },
        Err(BorrowError::TooManyLoans) => return KernelSendReport {
            outcome: not_sent(TxError::IoFailed), signal: KernelSendSignal::PreflightRejected },
    };
    let limit = frozen.len().min(MAX_READY_TX);
    if limit == 0 { return KernelSendReport {
        outcome: TxBatchOutcome::copied_all(0), signal: KernelSendSignal::None }; }
    let mut iovecs = [CIovec::empty(); MAX_READY_TX];
    let mut messages = [CMmsghdr::empty(); MAX_READY_TX];
    let mut expected = [0usize; MAX_READY_TX];
    for (i, record) in frozen[..limit].iter().enumerate() {
        let read = driver_read(record);
        if read.wire.is_empty() || read.wire.len() > u32::MAX as usize {
            // Fail entire batch before a syscall; do not send a partial set
            // and then mistakenly classify a malformed later frame as sent.
            return KernelSendReport {
                outcome: not_sent(TxError::IoFailed),
                signal: KernelSendSignal::PreflightRejected };
        }
        expected[i] = read.wire.len();
        // SAFETY: Linux sendmmsg only reads this iovec for a send operation.
        // Source bytes remain immutably borrowed from frozen records through
        // completion. Kernel cannot retain the slice on a copied UDP syscall.
        iovecs[i] = CIovec {
            iov_base: read.wire.as_ptr().cast_mut().cast::<c_void>(),
            iov_len: read.wire.len(),
        };
        messages[i].msg_hdr.msg_iov = ptr::addr_of_mut!(iovecs[i]);
        messages[i].msg_hdr.msg_iovlen = 1;
    }
    // SAFETY: each repr(C) mmsghdr + iovec matches audited glibc x86_64
    // GNU Linux layout and points to a live immutable slice in 'frozen'.
    // Arrays are stack-fixed until syscall return. No pointers escape, one
    // iovec per datagram, vlen<=32, fd is borrowed from caller's live socket,
    // and MSG_DONTWAIT forbids kernel wait on socket capacity.
    let sent = unsafe { sendmmsg(fd, messages.as_mut_ptr(), limit as c_uint, MSG_DONTWAIT) };
    let errno = if sent < 0 { io::Error::last_os_error().raw_os_error() } else { None };
    let reported: [u32; MAX_READY_TX] = std::array::from_fn(|i| messages[i].msg_len);
    classify_report(sent, errno, limit, frozen.len(), &reported, &expected)
}

/// Keep the legacy classifier unchanged for old historical tests. The new
/// typed signal distinguishes a *known* zero-prefix EMSGSIZE/ENODEV from
/// partial success, whose errno Linux has irretrievably discarded.
fn classify_report(sent: c_int, errno: Option<i32>, submitted: usize,
                   total: usize, reported_lens: &[u32], expected_lens: &[usize])
    -> KernelSendReport
{
    let old = classify(sent, errno, submitted, total, reported_lens, expected_lens);
    if submitted == 0 {
        return KernelSendReport { outcome: old, signal: KernelSendSignal::None };
    }
    if sent < 0 {
        let signal = match errno {
            Some(EAGAIN) => KernelSendSignal::Backpressure,
            Some(EINTR) => KernelSendSignal::Interrupted,
            Some(EMSGSIZE) => KernelSendSignal::MtuExceeded,
            Some(ENODEV) => KernelSendSignal::DeviceUnavailable,
            Some(ENETDOWN | ENETUNREACH | EHOSTUNREACH) =>
                KernelSendSignal::RouteUnavailable,
            Some(e) => KernelSendSignal::OtherErrno(e),
            None => KernelSendSignal::AmbiguousCompletion,
        };
        // A negative Linux sendmmsg return has no successful messages.
        // Only a *known* route/device/MTU errno authorizes zero-prefix
        // IoFailed; unknown/EINTR remain conservatively uncertain.
        let outcome = if matches!(signal, KernelSendSignal::MtuExceeded |
            KernelSendSignal::DeviceUnavailable | KernelSendSignal::RouteUnavailable) {
            not_sent(TxError::IoFailed)
        } else { old };
        return KernelSendReport { outcome, signal };
    }
    let n = sent as usize;
    let signal = if n == 0 || n > submitted ||
        reported_lens.iter().zip(expected_lens.iter()).take(n)
            .any(|(actual, expected)| *actual as usize != *expected) {
        KernelSendSignal::AmbiguousCompletion
    } else if n < submitted {
        KernelSendSignal::PartialErrnoUnavailable
    } else {
        KernelSendSignal::None
    };
    KernelSendReport { outcome: old, signal }
}


/// Raw scatter backend only: the caller holds a single generation/Stop
/// BorrowFence guard and lock before preparing the header and calling this.
/// This function borrows the EXACT frozen ciphertext for iovec[1] and does
/// one Linux sendmmsg syscall. Positive kernel result is NOT peer ACK.
pub(crate) fn submit_scatter_fd<H:FrozenRecordHandle>(
    fd:RawFd,destination:std::net::SocketAddrV4,
    headers:&[[u8;80];MAX_READY_TX],header_lens:&[usize;MAX_READY_TX],
    records:&[H],
)->KernelSendReport{
    let submitted=records.len().min(MAX_READY_TX);
    if submitted==0{return KernelSendReport{
        outcome:TxBatchOutcome::copied_all(0),signal:KernelSendSignal::None
    }}
    let mut iovecs=[[CIovec::empty();2];MAX_READY_TX];
    let mut messages=[CMmsghdr::empty();MAX_READY_TX];
    let mut expected=[0usize;MAX_READY_TX];
    // socket address has native x86_64 GNU sockaddr_in C layout.
    #[repr(C)]
    struct SockAddrIn{family:u16,port_be:u16,ip_be:u32,zero:[u8;8]}
    let target=SockAddrIn{family:2,port_be:destination.port().to_be(),
        ip_be:u32::from_ne_bytes(destination.ip().octets()),zero:[0;8]};
    for (i,r) in records[..submitted].iter().enumerate(){
        let payload=driver_read(r);
        let len=header_lens[i];
        if !(40..=80).contains(&len) ||len%4!=0||
            payload.wire.is_empty()||len+payload.wire.len()>65535{
            return KernelSendReport{outcome:not_sent(TxError::IoFailed),
                signal:KernelSendSignal::PreflightRejected}
        }
        expected[i]=len+payload.wire.len();
        iovecs[i][0]=CIovec{iov_base:headers[i].as_ptr().cast_mut().cast(),
            iov_len:len};
        iovecs[i][1]=CIovec{iov_base:payload.wire.as_ptr().cast_mut().cast(),
            iov_len:payload.wire.len()};
        messages[i].msg_hdr.msg_name=(&target as *const SockAddrIn)
            .cast_mut().cast();
        messages[i].msg_hdr.msg_namelen=std::mem::size_of::<SockAddrIn>() as u32;
        messages[i].msg_hdr.msg_iov=std::ptr::addr_of_mut!(iovecs[i][0]);
        messages[i].msg_hdr.msg_iovlen=2;
    }
    // SAFETY: all headers live on caller stack for the entire synchronous
    // call, frozen records stay immutably borrowed and alive, two repr(C)
    // iovecs per packet, valid native sockaddr_in per message, vlen<=32,
    // nonblocking kernel copy. No kernel references escape on return.
    let sent=unsafe{sendmmsg(fd,messages.as_mut_ptr(),
        submitted as c_uint,MSG_DONTWAIT)};
    let errno=if sent<0{io::Error::last_os_error().raw_os_error()}else{None};
    let reported:[u32;MAX_READY_TX]=std::array::from_fn(|i|messages[i].msg_len);
    classify_report(sent,errno,submitted,records.len(),&reported,&expected)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::r1::{BatchResult, StopResult};
    use std::mem::{offset_of, size_of};
    use std::os::unix::net::UnixDatagram;
    use std::sync::{Arc, atomic::{AtomicUsize, Ordering}};
    use std::time::{Duration, Instant};
    use wbd_types::buffer_contract::{BufferOrigin,FrozenMetadata};
    use wbd_types::{BufferKey,LaneKey,RecordPn,SeqOffset,TunnelKey};
    #[derive(Clone)]
    struct Frozen { bytes: Arc<[u8]>, meta: FrozenMetadata }
    impl FrozenRecordHandle for Frozen {
        fn origin(&self) -> BufferOrigin {
            BufferOrigin {owner_arena: 7, key: BufferKey{slot:1,generation:3}}
        }
        fn metadata(&self) -> FrozenMetadata {self.meta}
        fn bytes(&self)->&[u8] {&self.bytes}
    }
    fn frame(bytes:&[u8], n:u64)->Frozen {
        Frozen {bytes:Arc::from(bytes),
            meta:FrozenMetadata {
                lane:LaneKey{tunnel:TunnelKey{slot:1,generation:1},slot:2,generation:1},
                seq:SeqOffset(n),pn:RecordPn(n),carrier_snapshot:2}}
    }
    fn udp_pair()->(UdpSocket,UdpSocket) {
        let rx=UdpSocket::bind("127.0.0.1:0").unwrap();
        rx.set_read_timeout(Some(Duration::from_millis(150))).unwrap();
        let tx=UdpSocket::bind("127.0.0.1:0").unwrap();
        tx.connect(rx.local_addr().unwrap()).unwrap();
        (tx,rx)
    }
    #[test]
    fn r1_linux_sendmmsg_x86_64_glibc_ffi_layout_audited() {
        assert_eq!(size_of::<CIovec>(),16);
        assert_eq!(size_of::<CMsghdr>(),56);
        assert_eq!(size_of::<CMmsghdr>(),64);
        assert_eq!(offset_of!(CMsghdr,msg_iov),16);
        assert_eq!(offset_of!(CMsghdr,msg_iovlen),24);
        assert_eq!(offset_of!(CMsghdr,msg_controllen),40);
        assert_eq!(offset_of!(CMsghdr,msg_flags),48);
        assert_eq!(offset_of!(CMmsghdr,msg_len),56);
    }
    #[test]
    fn r1_linux_sendmmsg_real_kernel_udp_all_and_immutable_bytes() {
        let (tx,rx)=udp_pair();
        let f=[frame(b"full IPv4/TCP packet 0",1),
               frame(b"\x45\0\xff\x13\x20",2),
               frame(b"last packet",3)];
        let ptr=f[1].bytes.as_ptr();
        let fence=BorrowFence::default();
        let out=submit_connected_udp(&tx,&f,&fence);
        assert_eq!(out,TxBatchOutcome::copied_all(3));
        assert_eq!(f[1].bytes.as_ptr(),ptr);
        let mut buf=[0u8;256];
        for expected in &f {
            let n=rx.recv(&mut buf).unwrap();
            assert_eq!(&buf[..n],expected.bytes());
        }
        assert_eq!(fence.outstanding(),0);
    }
    #[test]
    fn r1_linux_sendmmsg_real_kernel_partial_udp_emsgsize_prefix_only() {
        let (tx,rx)=udp_pair();
        let oversize=vec![0x55u8;65508]; // > Linux IPv4 UDP max 65507
        let f=[frame(b"first",1),frame(&oversize,2)];
        let fence=BorrowFence::default();
        let out=submit_connected_udp(&tx,&f,&fence);
        assert_eq!(BatchResult::new(out,2).unwrap().accepted_prefix(),1);
        assert_eq!(out.uncertain_index,None);
        assert_eq!(out.error,Some(TxError::IoFailed)); // errno after success lost.
        let mut buf=[0u8;32];
        assert_eq!(rx.recv(&mut buf).unwrap(),5);
        assert_eq!(&buf[..5],b"first");
        assert!(rx.recv(&mut buf).is_err());
    }
    #[test]
    fn r1_linux_sendmmsg_real_kernel_cap32_not_33rd() {
        let (tx,rx)=udp_pair();
        let f:Vec<_>=(0..33).map(|n|frame(&[n as u8,0xaa],n)).collect();
        let fence=BorrowFence::default();
        let out=submit_connected_udp(&tx,&f,&fence);
        assert_eq!(out.accepted_prefix,32);
        assert_eq!(out.error,Some(TxError::WouldBlock));
        let mut b=[0;8];
        for n in 0..32 {assert_eq!(rx.recv(&mut b).unwrap(),2);assert_eq!(b[0],n);}
        assert!(rx.recv(&mut b).is_err());
    }
    #[test]
    fn r1_linux_sendmmsg_real_kernel_unix_backpressure_eagain_notsent() {
        // Deterministically fill an unprivileged connected kernel datagram
        // queue without draining. Then invoke the SAME real sendmmsg syscall
        // and require errno EAGAIN, not an invented fake errno.
        let (tx,_rx)=UnixDatagram::pair().unwrap();
        tx.set_nonblocking(true).unwrap();
        let mut full=false;
        let bytes=[0xa5u8;8192];
        for _ in 0..4096 {
            match tx.send(&bytes) {
                Ok(n) => assert_eq!(n,bytes.len()),
                Err(e) if e.kind()==io::ErrorKind::WouldBlock => {full=true;break},
                Err(e) => panic!("unix fill: {e}"),
            }
        }
        assert!(full,"unprivileged UNIX datagram fixture never backpressured");
        let f=[frame(b"never accepted",6)];
        let fence=BorrowFence::default();
        let out=submit_fd(tx.as_raw_fd(),&f,&fence);
        assert_eq!(out,not_sent(TxError::WouldBlock));
    }
    #[test]
    fn r1_linux_sendmmsg_deterministic_classifier_eintr_short_and_zero() {
        let expected=[4,5,6];
        let good=[4u32,5,6];
        assert_eq!(classify(-1,Some(EAGAIN),3,3,&good,&expected),
            not_sent(TxError::WouldBlock));
        assert_eq!(classify(-1,Some(EINTR),3,3,&good,&expected),uncertain(0));
        assert_eq!(classify(-1,Some(5),3,3,&good,&expected),uncertain(0));
        assert_eq!(classify(0,None,3,3,&good,&expected),uncertain(0));
        assert_eq!(classify(1,None,3,3,&good,&expected),
            accepted_prefix(1,3,3));
        assert_eq!(classify(3,None,3,3,&good,&expected),TxBatchOutcome::copied_all(3));
        assert_eq!(classify(2,None,3,3,&[4,2,6],&expected),uncertain(1));
    }
    #[test]
    fn r1_linux_sendmmsg_stop_keeps_borrowed_bytes_until_return() {
        let (tx,_rx)=udp_pair();
        let fence=Arc::new(BorrowFence::default());
        let lease=fence.try_enter_ready().unwrap();
        assert_eq!(fence.outstanding(),1);
        assert_eq!(fence.wait_drained_until(Instant::now()),
            StopResult::Pending{outstanding:1});
        let f=[frame(b"unchanged",4)];
        assert_eq!(submit_connected_udp(&tx,&f,&fence),
            not_sent(TxError::Stopping));
        assert_eq!(&*f[0].bytes,b"unchanged");
        drop(lease);
        assert_eq!(fence.wait_drained_until(Instant::now()),StopResult::Drained);
        assert_eq!(fence.outstanding(),0);
    }
    #[test]
    fn r1_linux_sendmmsg_stop_vs_atomic_submission_registration() {
        let fence=Arc::new(BorrowFence::default());
        let start=Arc::new(std::sync::Barrier::new(2));
        let entries=Arc::new(AtomicUsize::new(0));
        let f2=Arc::clone(&fence);
        let start2=Arc::clone(&start);
        let entries2=Arc::clone(&entries);
        let t=std::thread::spawn(move||{
            start2.wait();
            if let Ok(_lease)=f2.try_enter_ready(){
                entries2.fetch_add(1,Ordering::SeqCst);
                std::thread::yield_now();
            }
        });
        start.wait();
        fence.begin_stop();
        t.join().unwrap();
        assert!(entries.load(Ordering::SeqCst)<=1);
        assert_eq!(fence.outstanding(),0);
        assert!(fence.try_enter_ready().is_err());
    }
    #[test]
    fn r1_linux_sendmmsg_real_kernel_typed_emsgsize_and_partial_unknown() {
        let (tx,rx)=udp_pair();
        let oversized=vec![0x42u8;65508]; // real Linux IPv4 UDP max=65507
        let fence=BorrowFence::default();
        let failed=[frame(&oversized,1)];
        let report=submit_connected_udp_detailed(&tx,&failed,&fence);
        assert_eq!(report.signal,KernelSendSignal::MtuExceeded);
        assert!(report.signal.invalidates_path());
        assert_eq!(report.outcome,not_sent(TxError::IoFailed));
        let mut received=[0u8;16];
        assert!(rx.recv(&mut received).is_err());
        let frames=[frame(b"ok",2),frame(&oversized,3)];
        let partial=submit_connected_udp_detailed(&tx,&frames,&fence);
        assert_eq!(partial.outcome.accepted_prefix,1);
        assert_eq!(partial.outcome.uncertain_index,None);
        assert_eq!(partial.signal,KernelSendSignal::PartialErrnoUnavailable);
        assert!(partial.signal.invalidates_path());
        assert_eq!(rx.recv(&mut received).unwrap(),2);
        assert_eq!(&received[..2],b"ok");
        assert!(rx.recv(&mut received).is_err());
        assert_eq!(fence.outstanding(),0);
    }
    #[test]
    fn r1_linux_sendmmsg_typed_device_route_and_backpressure_are_distinct() {
        let lengths=[3usize,4];
        let returned=[3u32,4];
        for (errno,signal) in [
            (EMSGSIZE,KernelSendSignal::MtuExceeded),
            (ENODEV,KernelSendSignal::DeviceUnavailable),
            (ENETDOWN,KernelSendSignal::RouteUnavailable),
            (ENETUNREACH,KernelSendSignal::RouteUnavailable),
            (EHOSTUNREACH,KernelSendSignal::RouteUnavailable),
        ] {
            let report=classify_report(-1,Some(errno),2,2,&returned,&lengths);
            assert_eq!(report.outcome,not_sent(TxError::IoFailed));
            assert_eq!(report.signal,signal);
            assert!(signal.invalidates_path());
        }
        let blocked=classify_report(-1,Some(EAGAIN),2,2,&returned,&lengths);
        assert_eq!(blocked.outcome,not_sent(TxError::WouldBlock));
        assert_eq!(blocked.signal,KernelSendSignal::Backpressure);
        assert!(!blocked.signal.invalidates_path());
        let interrupted=classify_report(-1,Some(EINTR),2,2,&returned,&lengths);
        assert_eq!(interrupted.outcome,uncertain(0));
        assert_eq!(interrupted.signal,KernelSendSignal::Interrupted);
        assert!(!interrupted.signal.invalidates_path());
        let partial=classify_report(1,None,2,2,&returned,&lengths);
        assert_eq!(partial.outcome,accepted_prefix(1,2,2));
        assert_eq!(partial.signal,KernelSendSignal::PartialErrnoUnavailable);
        assert!(partial.signal.invalidates_path());
        let short=classify_report(2,None,2,2,&[3,1],&lengths);
        assert_eq!(short.outcome,uncertain(1));
        assert_eq!(short.signal,KernelSendSignal::AmbiguousCompletion);
    }

    #[test]
    fn r1_m4_013_scatter_real_kernel_sendmmsg_udp_0_1_32_33_and_partial(){
        use crate::ipv4_tcp::{build_scatter_header,Ipv4Tuple,Presentation,PacketPersona};
        let (tx,rx)=udp_pair();
        let tuple=Ipv4Tuple{src_ip:&[127,0,0,1],dst_ip:&[127,0,0,1],
            src_port:1000,dst_port:2000};
        let present=Presentation{ack32:11,ip_id:33,
            advertised_window:65535,persona:PacketPersona::Legacy};
        let mut bytes=[0u8;128];
        let empty:Vec<Frozen>=Vec::new();
        let blank=[[0u8;80];MAX_READY_TX];
        let lengths=[0usize;MAX_READY_TX];
        let addr=match rx.local_addr().unwrap(){
            std::net::SocketAddr::V4(v)=>v,_=>unreachable!()};
        assert_eq!(submit_scatter_fd(tx.as_raw_fd(),addr,&blank,&lengths,&empty)
            .outcome,TxBatchOutcome::copied_all(0));
        for total in [1usize,32,33]{
            let frames:Vec<_>=(0..total).map(|i|frame(&[i as u8,0x9a],i as u64)).collect();
            let mut headers=[[0u8;80];MAX_READY_TX];
            let mut lens=[0usize;MAX_READY_TX];
            for (i,f) in frames[..total.min(MAX_READY_TX)].iter().enumerate(){
                lens[i]=build_scatter_header(tuple,present,f,None,1500,
                    &mut headers[i]).unwrap();
            }
            let report=submit_scatter_fd(tx.as_raw_fd(),addr,&headers,&lens,&frames);
            assert_eq!(report.outcome.accepted_prefix,total.min(MAX_READY_TX));
            assert_eq!(report.outcome.uncertain_index,None);
            for i in 0..total.min(MAX_READY_TX){
                let n=rx.recv(&mut bytes).unwrap();
                assert_eq!(n,42);
                assert_eq!(bytes[40],i as u8);
            }
            if total==33 {
                assert_eq!(report.outcome.error,Some(TxError::WouldBlock));
                assert!(rx.recv(&mut bytes).is_err());
            }
        }
        let large=vec![0xb6;65500];
        let frames=[frame(b"prefix",1),frame(&large,2)];
        let mut headers=[[0u8;80];MAX_READY_TX];
        let mut lens=[0usize;MAX_READY_TX];
        for (i,f) in frames.iter().enumerate(){
            lens[i]=build_scatter_header(tuple,present,f,None,65535,
                &mut headers[i]).unwrap();
        }
        let short=submit_scatter_fd(tx.as_raw_fd(),addr,&headers,&lens,&frames);
        assert_eq!(short.outcome.accepted_prefix,1);
        assert_eq!(short.signal,KernelSendSignal::PartialErrnoUnavailable);
        assert_eq!(rx.recv(&mut bytes).unwrap(),46);
        assert!(rx.recv(&mut bytes).is_err());
    }
    #[test]
    fn r1_linux_sendmmsg_preflight_reject_invalid_without_writing() {
        let (tx,_rx)=udp_pair();
        let f=[frame(b"valid",1),frame(b"",2)];
        let fence=BorrowFence::default();
        assert_eq!(submit_connected_udp(&tx,&f,&fence),not_sent(TxError::IoFailed));
        assert_eq!(fence.outstanding(),0);
        assert_eq!(submit_connected_udp::<Frozen>(&tx,&[],&fence),TxBatchOutcome::copied_all(0));
    }
}
