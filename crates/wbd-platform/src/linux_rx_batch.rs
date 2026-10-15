//! Linux x86_64 GNU bounded recvmmsg RX syscall fixture.
//!
//! This is **unprivileged UDP socket I/O**, not AF_PACKET/raw TCP, TUN,
//! Windows Npcap, or a live production carrier reader. Buffers and socket are
//! caller-owned for the *synchronous* syscall; no allocation, new thread,
//! spin, delay, heap, per-frame clone, lock or `Arc` occurs on receive.
//!
//! ABI: glibc sys/socket.h mmsghdr/msghdr, sys/uio.h iovec. This separately
//! cfg-gated unsafe island copies the audited existing sendmmsg structs;
//! native 64-bit offsets/sizes are checked by platform unit tests.
//! A complete UDP payload may be passed to the *separate* strict IPv4/TCP
//! parser; the resulting ciphertext remains cryptographically UNAUTHENTICATED.
use crate::r1::{BorrowError, BorrowFence, MAX_READY_TX};
use crate::rx_ipv4_tcp::{parse_data_packet, RxError, TrustedRx, UnauthenticatedData};
use std::ffi::{c_int, c_uint, c_void};
use std::io;
use std::net::UdpSocket;
use std::os::fd::{AsRawFd, RawFd};
use std::ptr;

pub const MAX_READY_RX: usize = MAX_READY_TX;
const MSG_DONTWAIT: c_int = 0x40;
const MSG_TRUNC: c_int = 0x20;
const MSG_CTRUNC: c_int = 0x08;
const EAGAIN: i32 = 11;
const EINTR: i32 = 4;

#[repr(C)]
#[derive(Clone, Copy)]
struct CIovec { iov_base: *mut c_void, iov_len: usize }
impl CIovec {
    const fn empty() -> Self { Self {iov_base: ptr::null_mut(), iov_len: 0} }
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
        Self {msg_name:ptr::null_mut(),msg_namelen:0,msg_iov:ptr::null_mut(),
            msg_iovlen:0,msg_control:ptr::null_mut(),msg_controllen:0,msg_flags:0}
    }
}
#[repr(C)]
#[derive(Clone, Copy)]
struct CMmsghdr { msg_hdr: CMsghdr, msg_len: c_uint }
impl CMmsghdr {
    const fn empty() -> Self {Self {msg_hdr:CMsghdr::empty(),msg_len:0}}
}
// NULL timeout is used; recvmmsg obeys per-call MSG_DONTWAIT even if the
// borrowed fd is blocking. No declaration of libc timespec is required.
unsafe extern "C" {
    fn recvmmsg(sockfd:c_int,msgvec:*mut CMmsghdr,vlen:c_uint,
                flags:c_int,timeout:*mut c_void)->c_int;
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RxEntry {
    /// Nothing copied into this caller buffer by this invocation.
    Unused,
    /// Entire datagram copied; bytes still UNAUTHENTICATED.
    Complete { len: usize },
    /// Datagram consumed, but no valid full record may be exposed.
    /// wire_len is the reported original length with Linux MSG_TRUNC.
    Truncated { wire_len: usize, capacity: usize },
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RxStatus {
    Empty, Ready, AtCap, WouldBlock, Interrupted,
    IoUncertain, InvalidBuffers, Stopping,
}
/// Result is 32 fixed-size entries, not a dynamic vector. The caller keeps
/// its buffers until the borrowed parser view is no longer used.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RxBatchOutcome {
    pub requested: usize,
    pub attempted: usize,
    pub received: usize,
    pub status: RxStatus,
    pub entries: [RxEntry; MAX_READY_RX],
}
impl RxBatchOutcome {
    fn with_status(requested:usize,attempted:usize,status:RxStatus)->Self{
        Self{requested,attempted,received:0,status,entries:[RxEntry::Unused;MAX_READY_RX]}
    }
    /// Access only slots actually submitted; never read a 33rd slot in a
    /// 32-message syscall or a stale slot from a previous caller batch.
    pub fn entry(&self,index:usize)->Option<RxEntry>{
        if index < self.attempted {Some(self.entries[index])} else {None}
    }
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ParseGateError {
    NotReceived, Truncated, InvalidSlot, InvalidPacket(RxError),
}
/// The ONLY bridge to the strict carrier parser. Truncated datagrams and
/// unreceived slots cannot be promoted into bytes with valid packet metadata.
pub fn parse_complete<'a>(
    slot: RxEntry, buffer: &'a [u8], trusted: TrustedRx<'_>,
)->Result<UnauthenticatedData<'a>,ParseGateError>{
    let n=match slot{
        RxEntry::Unused=>return Err(ParseGateError::NotReceived),
        RxEntry::Truncated{..}=>return Err(ParseGateError::Truncated),
        RxEntry::Complete{len} if len<=buffer.len()=>len,
        _=>return Err(ParseGateError::InvalidSlot),
    };
    parse_data_packet(&buffer[..n],trusted).map_err(ParseGateError::InvalidPacket)
}

/// Pure branch classifier for exceptional errno/length metadata. Cases that
/// are difficult to force in a privileged-free CI fixture (EINTR and
/// inconsistent kernel msg_len) are tested here *without* asserting kernel
/// injection. No uncertain/truncated packet is submitted to the parser.
fn classify(count:c_int,errno:Option<i32>,requested:usize,attempted:usize,
            msg_lens:&[u32;MAX_READY_RX],msg_flags:&[c_int;MAX_READY_RX],
            caps:&[usize;MAX_READY_RX])->RxBatchOutcome{
    if attempted==0{return RxBatchOutcome::with_status(requested,0,RxStatus::Empty);}
    if count<0{return RxBatchOutcome::with_status(requested,attempted,
        match errno{Some(EAGAIN)=>RxStatus::WouldBlock,
            Some(EINTR)=>RxStatus::Interrupted,_=>RxStatus::IoUncertain});}
    let n=count as usize;
    if n==0||n>attempted {
        return RxBatchOutcome::with_status(requested,attempted,RxStatus::IoUncertain);
    }
    let mut out=RxBatchOutcome::with_status(requested,attempted,
        if n==MAX_READY_RX && requested>MAX_READY_RX{RxStatus::AtCap}else{RxStatus::Ready});
    out.received=n;
    for i in 0..n{
        let reported=msg_lens[i] as usize;
        out.entries[i]=if reported>caps[i] || msg_flags[i]&(MSG_TRUNC|MSG_CTRUNC)!=0 {
            RxEntry::Truncated{wire_len:reported,capacity:caps[i]}
        }else{
            RxEntry::Complete{len:reported}
        };
    }
    out
}

/// Receive at most 32 already-available UDP datagrams via one kernel
/// recvmmsg(MSG_DONTWAIT|MSG_TRUNC) call, directly into caller-owned mutable
/// slices. The kernel writes only during this synchronous call. A single
/// atomic BorrowFence guard prevents stop from reporting drained while the
/// slices are borrowed; no asynchronous completion lease is invented.
///
/// An unconnected UDP socket may receive from any sender. The separate
/// strict parser MUST validate a trusted in-band carrier tuple before
/// M0/M3 authenticate any record; this fixture does NOT install a BPF filter.
pub fn receive_ready_udp(
    socket:&UdpSocket,buffers:&mut [&mut [u8]],fence:&BorrowFence
)->RxBatchOutcome{
    receive_fd(socket.as_raw_fd(),buffers,fence)
}
fn receive_fd(fd:RawFd,buffers:&mut [&mut [u8]],fence:&BorrowFence)
    ->RxBatchOutcome
{
    let requested=buffers.len();
    let limit=requested.min(MAX_READY_RX);
    // Atomic CAS registration prevents stop/return of caller buffers while a
    // native syscall can still write to them. No mutex on normal entry.
    let _inflight=match fence.try_enter_ready(){
        Ok(g)=>g,
        Err(BorrowError::Stopping)=>{
            return RxBatchOutcome::with_status(requested,limit,RxStatus::Stopping)
        }
        Err(BorrowError::TooManyLoans)=>{
            return RxBatchOutcome::with_status(requested,limit,RxStatus::IoUncertain)
        }
    };
    if limit==0 {return RxBatchOutcome::with_status(0,0,RxStatus::Empty);}
    if buffers[..limit].iter().any(|slot|slot.is_empty()){
        return RxBatchOutcome::with_status(requested,limit,RxStatus::InvalidBuffers);
    }
    let mut iovecs=[CIovec::empty();MAX_READY_RX];
    let mut messages=[CMmsghdr::empty();MAX_READY_RX];
    let mut caps=[0usize;MAX_READY_RX];
    for (i,slot) in buffers[..limit].iter_mut().enumerate(){
        caps[i]=slot.len();
        iovecs[i]=CIovec{iov_base:slot.as_mut_ptr().cast::<c_void>(),iov_len:slot.len()};
        messages[i].msg_hdr.msg_iov=ptr::addr_of_mut!(iovecs[i]);
        messages[i].msg_hdr.msg_iovlen=1;
    }
    // SAFETY: repr(C) iovec/msghdr/mmsghdr layout fixed to native
    // x86_64-unknown-linux-gnu, and proven by actual size/offset tests.
    // Arrays remain live on this stack throughout call; each iov_base points
    // exclusively to a caller-borrowed mutable buffer, with the borrow held
    // until return. UDP kernel copies bytes synchronously. timeout=NULL,
    // MSG_DONTWAIT forbids waiting for datagrams, vlen<=32, and no pointers
    // escape the syscall. No other user thread may use these &mut slices.
    let count=unsafe{recvmmsg(fd,messages.as_mut_ptr(),limit as c_uint,
        MSG_DONTWAIT|MSG_TRUNC,ptr::null_mut())};
    let errno=if count<0{io::Error::last_os_error().raw_os_error()}else{None};
    let msg_lens=std::array::from_fn(|i|messages[i].msg_len);
    let msg_flags=std::array::from_fn(|i|messages[i].msg_hdr.msg_flags);
    classify(count,errno,requested,limit,&msg_lens,&msg_flags,&caps)
}

#[cfg(test)]
mod tests{
    use super::*;
    use crate::ipv4_tcp::{Ipv4Tuple,PacketPersona};
    use crate::r1::StopResult;
    use std::mem::{size_of,offset_of};
    use std::sync::{Arc,Barrier,atomic::{AtomicUsize,Ordering}};
    use std::time::Instant;
    fn pair()->(UdpSocket,UdpSocket){
        let rx=UdpSocket::bind("127.0.0.1:0").unwrap();
        let tx=UdpSocket::bind("127.0.0.1:0").unwrap();
        tx.connect(rx.local_addr().unwrap()).unwrap();
        (tx,rx)
    }
    fn golden()->Vec<u8>{
        let hex="4500002e0015400040064e31c0000228c6336428a7f801bb00000064000000c850180400cc2900007265636f7264";
        (0..hex.len()).step_by(2)
            .map(|i|u8::from_str_radix(&hex[i..i+2],16).unwrap()).collect()
    }
    fn trusted()->TrustedRx<'static>{
        TrustedRx{tuple:Ipv4Tuple{src_ip:&[192,0,2,40],dst_ip:&[198,51,100,40],
                src_port:43000,dst_port:443},persona:PacketPersona::Legacy,
                mtu:1500,authenticated_options:None}
    }
    #[test]
    fn r1_linux_recvmmsg_native_abi_layout_and_flags(){
        assert_eq!(size_of::<CIovec>(),16);
        assert_eq!(size_of::<CMsghdr>(),56);
        assert_eq!(size_of::<CMmsghdr>(),64);
        assert_eq!(offset_of!(CMsghdr,msg_iov),16);
        assert_eq!(offset_of!(CMsghdr,msg_iovlen),24);
        assert_eq!(offset_of!(CMsghdr,msg_controllen),40);
        assert_eq!(offset_of!(CMsghdr,msg_flags),48);
        assert_eq!(offset_of!(CMmsghdr,msg_len),56);
        assert_eq!((MSG_DONTWAIT,MSG_TRUNC,MSG_CTRUNC),(64,32,8));
    }
    #[test]
    fn r1_linux_recvmmsg_actual_kernel_udp_zero_and_eagain(){
        let (_tx,rx)=pair();let fence=BorrowFence::default();
        let mut empty: [&mut [u8];0]=[];
        let out=receive_ready_udp(&rx,&mut empty,&fence);
        assert_eq!((out.attempted,out.received,out.status),(0,0,RxStatus::Empty));
        let mut b=[0x99u8;32];
        let mut slots=[b.as_mut_slice()];
        let out=receive_ready_udp(&rx,&mut slots,&fence);
        assert_eq!((out.attempted,out.received,out.status),(1,0,RxStatus::WouldBlock));
        assert_eq!(out.entry(0),Some(RxEntry::Unused));
        assert_eq!(&b,[0x99;32]);
        assert_eq!(fence.outstanding(),0);
    }
    #[test]
    fn r1_linux_recvmmsg_actual_kernel_udp_one_exact_owned_slice(){
        let (tx,rx)=pair();tx.send(b"hello").unwrap();
        let fence=BorrowFence::default();
        let mut b=[0xaau8;64];
        let mut slots=[b.as_mut_slice()];
        let out=receive_ready_udp(&rx,&mut slots,&fence);
        assert_eq!((out.received,out.status),(1,RxStatus::Ready));
        assert_eq!(out.entry(0),Some(RxEntry::Complete{len:5}));
        assert_eq!(&b[..5],b"hello");
        assert!(b[5..].iter().all(|x|*x==0xaa));
        b[0]=b'H'; // caller regains unique write ownership after syscall
        assert_eq!(fence.outstanding(),0);
    }
    #[test]
    fn r1_linux_recvmmsg_actual_kernel_udp_32_of_33_cap_and_next_ready(){
        let (tx,rx)=pair();
        for n in 0..33u8 {assert_eq!(tx.send(&[n,0xfe]).unwrap(),2);}
        let fence=BorrowFence::default();
        let mut storage=[[0xccu8;16];33];
        let mut views:Vec<&mut [u8]>=storage.iter_mut().map(|x|x.as_mut_slice()).collect();
        let out=receive_ready_udp(&rx,&mut views,&fence);
        assert_eq!((out.received,out.attempted,out.status),(32,32,RxStatus::AtCap));
        for n in 0..32usize{
            assert_eq!(out.entry(n),Some(RxEntry::Complete{len:2}));
            assert_eq!(&views[n][..2],&[n as u8,0xfe]);
        }
        assert_eq!(out.entry(32),None);
        assert!(views[32].iter().all(|x|*x==0xcc));
        let next=receive_ready_udp(&rx,&mut views[32..],&fence);
        assert_eq!(next.received,1);
        assert_eq!(next.entry(0),Some(RxEntry::Complete{len:2}));
        assert_eq!(&views[32][..2],&[32,0xfe]);
        assert_eq!(fence.outstanding(),0);
    }
    #[test]
    fn r1_linux_recvmmsg_actual_kernel_udp_partial_ready_prefix_and_no_hol(){
        let (tx,rx)=pair();tx.send(b"A").unwrap();tx.send(b"BC").unwrap();
        let fence=BorrowFence::default();
        let mut storage=[[0x55u8;32];4];
        let mut views:Vec<&mut [u8]>=storage.iter_mut().map(|x|x.as_mut_slice()).collect();
        let out=receive_ready_udp(&rx,&mut views,&fence);
        assert_eq!((out.received,out.status),(2,RxStatus::Ready));
        assert_eq!(out.entry(0),Some(RxEntry::Complete{len:1}));
        assert_eq!(out.entry(1),Some(RxEntry::Complete{len:2}));
        assert_eq!(out.entry(2),Some(RxEntry::Unused));
        assert_eq!(&views[0][..1],b"A");assert_eq!(&views[1][..2],b"BC");
        assert!(views[2].iter().all(|b|*b==0x55));
        tx.send(b"next").unwrap();
        let next=receive_ready_udp(&rx,&mut views[2..3],&fence);
        assert_eq!(next.entry(0),Some(RxEntry::Complete{len:4}));
        assert_eq!(&views[2][..4],b"next");
    }
    #[test]
    fn r1_linux_recvmmsg_actual_kernel_udp_truncation_no_parse_and_good_after(){
        let (tx,rx)=pair();
        assert_eq!(tx.send(&[0xeeu8;200]).unwrap(),200);
        let good=golden();tx.send(&good).unwrap();
        let mut little=[0xa5u8;8];let mut full=[0xccu8;128];
        let mut slots=[little.as_mut_slice(),full.as_mut_slice()];
        let fence=BorrowFence::default();
        let out=receive_ready_udp(&rx,&mut slots,&fence);
        assert_eq!(out.received,2);
        assert_eq!(out.entry(0),Some(RxEntry::Truncated{wire_len:200,capacity:8}));
        assert_eq!(parse_complete(out.entries[0],&little,trusted()),
            Err(ParseGateError::Truncated));
        assert_eq!(out.entry(1),Some(RxEntry::Complete{len:46}));
        let p=parse_complete(out.entries[1],&full,trusted()).unwrap();
        assert_eq!(p.ciphertext,b"record");
        assert_eq!(&full[..46],&good);
    }
    #[test]
    fn r1_linux_recvmmsg_actual_kernel_udp_corrupt_packet_then_valid_no_hol(){
        let (tx,rx)=pair();let good=golden();let mut bad=good.clone();
        bad[40]^=0x80;tx.send(&bad).unwrap();tx.send(&good).unwrap();
        let mut storage=[[0u8;128];2];
        let mut views:Vec<&mut [u8]>=storage.iter_mut().map(|x|x.as_mut_slice()).collect();
        let fence=BorrowFence::default();
        let out=receive_ready_udp(&rx,&mut views,&fence);
        assert_eq!(out.received,2);
        assert_eq!(parse_complete(out.entries[0],views[0],trusted()),
            Err(ParseGateError::InvalidPacket(RxError::TcpChecksum)));
        let v=parse_complete(out.entries[1],views[1],trusted()).unwrap();
        assert_eq!(v.ciphertext,b"record"); // still not authenticated!
        assert_eq!(v.seq32,100);
    }
    #[test]
    fn r1_linux_recvmmsg_deterministic_classifier_eintr_short_and_trunc_flags(){
        let mut len=[0u32;MAX_READY_RX];
        let mut flags=[0i32;MAX_READY_RX];
        let mut caps=[0usize;MAX_READY_RX];
        len[0]=11;caps[0]=8;
        assert_eq!(classify(-1,Some(EAGAIN),2,2,&len,&flags,&caps).status,RxStatus::WouldBlock);
        assert_eq!(classify(-1,Some(EINTR),2,2,&len,&flags,&caps).status,RxStatus::Interrupted);
        assert_eq!(classify(-1,Some(5),2,2,&len,&flags,&caps).status,RxStatus::IoUncertain);
        assert_eq!(classify(0,None,2,2,&len,&flags,&caps).status,RxStatus::IoUncertain);
        let out=classify(1,None,2,2,&len,&flags,&caps);
        assert_eq!(out.entries[0],RxEntry::Truncated{wire_len:11,capacity:8});
        assert_eq!(out.entry(1),Some(RxEntry::Unused));
        len[0]=5;flags[0]=MSG_TRUNC;
        let out=classify(1,None,2,2,&len,&flags,&caps);
        assert_eq!(out.entries[0],RxEntry::Truncated{wire_len:5,capacity:8});
        flags[0]=MSG_CTRUNC;
        assert!(matches!(classify(1,None,2,2,&len,&flags,&caps).entries[0],
            RxEntry::Truncated{..}));
        flags[0]=0;
        let out=classify(1,None,2,2,&len,&flags,&caps);
        assert_eq!(out.entries[0],RxEntry::Complete{len:5});
        assert_eq!(parse_complete(RxEntry::Complete{len:9},&[0u8;8],trusted()),
            Err(ParseGateError::InvalidSlot));
        assert_eq!(parse_complete(RxEntry::Unused,&[0u8;8],trusted()),
            Err(ParseGateError::NotReceived));
    }
    #[test]
    fn r1_linux_recvmmsg_preflight_empty_buffer_never_consumes_kernel_datagram(){
        let (tx,rx)=pair();tx.send(b"still-ready").unwrap();
        let fence=BorrowFence::default();
        let mut empty: [u8;0]=[];let mut ok=[0xccu8;32];
        let mut slots=[empty.as_mut_slice(),ok.as_mut_slice()];
        let fail=receive_ready_udp(&rx,&mut slots,&fence);
        assert_eq!(fail.status,RxStatus::InvalidBuffers);
        assert_eq!(fail.received,0);
        assert!(ok.iter().all(|x|*x==0xcc));
        let mut slots=[ok.as_mut_slice()];
        let success=receive_ready_udp(&rx,&mut slots,&fence);
        assert_eq!(success.entry(0),Some(RxEntry::Complete{len:11}));
        assert_eq!(&ok[..11],b"still-ready");
    }
    #[test]
    fn r1_linux_recvmmsg_stop_borrow_fence_pending_and_no_post_stop_mutation(){
        let (_tx,rx)=pair();let fence=BorrowFence::default();
        let lease=fence.try_enter_ready().unwrap();
        assert_eq!(fence.outstanding(),1);
        assert_eq!(fence.wait_drained_until(Instant::now()),
            StopResult::Pending{outstanding:1});
        let mut b=[0xaau8;16];let mut slots=[b.as_mut_slice()];
        let out=receive_ready_udp(&rx,&mut slots,&fence);
        assert_eq!(out.status,RxStatus::Stopping);
        assert_eq!(out.received,0);
        assert_eq!(&b,[0xaa;16]);
        drop(lease);
        assert_eq!(fence.wait_drained_until(Instant::now()),StopResult::Drained);
    }
    #[test]
    fn r1_linux_recvmmsg_stop_vs_registration_race_atomic(){
        let fence=Arc::new(BorrowFence::default());
        let sync=Arc::new(Barrier::new(2));
        let entered=Arc::new(AtomicUsize::new(0));
        let f=Arc::clone(&fence);let b=Arc::clone(&sync);let n=Arc::clone(&entered);
        let t=std::thread::spawn(move||{
            b.wait();
            if let Ok(_g)=f.try_enter_ready(){
                n.fetch_add(1,Ordering::SeqCst);
                std::thread::yield_now();
            }
        });
        sync.wait();fence.begin_stop();t.join().unwrap();
        assert!(entered.load(Ordering::SeqCst)<=1);
        assert_eq!(fence.outstanding(),0);
        assert!(fence.try_enter_ready().is_err());
    }
}
