//! Test-only Linux x86_64 GNU AF_PACKET SOCK_RAW isolated-loopback lifecycle.
//!
//! Never linked into release: opt-in is an explicit boolean, AND real effective
//! CAP_NET_RAW is required. Socket receive starts protocol-zero (inert).
//! A narrow classic BPF self-frame filter is installed BEFORE binding the
//! receiver to the verified lo ifindex / IPv4 protocol. The source never binds
//! any physical interface, enables promiscuity, captures ambient payload,
//! starts production Go V4, or accepts unverified ciphertext as business.
//!
//! No new external dependency, root ABI, CI setting, or cross-owner mutation.
//! All AF_PACKET FDs are owned RAII values, nonblocking and CLOEXEC. A single
//! bounded recvmmsg call uses <=32 caller-owned packet buffers and a BorrowFence
//! guard; STOP never frees a live borrowed buffer.
//!
//! Source: Linux packet(7), socket(2), filter(7); this is a test fixture only.
#![allow(dead_code)]
use crate::linux_packet_preflight::{effective_cap_net_raw, interface_index, validate_config, PacketConfig, PacketSnapshot, PreflightError};
use crate::linux_raw_rx_contract::{validate_sockaddr, RawReceiveMetadata, RawRxError, SockAddrLl};
use crate::r1::{BorrowFence, StopResult};
use std::ffi::{c_int,c_uint,c_void};
use std::io;
use std::os::fd::{AsRawFd, FromRawFd, OwnedFd};
use std::ptr;
use std::time::Instant;

const AF_PACKET:c_int=17;
const SOCK_RAW:c_int=3;
const SOCK_NONBLOCK:c_int=0x800;
const SOCK_CLOEXEC:c_int=0x80000;
const ETH_P_IP:u16=0x0800;
const SOL_SOCKET:c_int=1;
const SO_ATTACH_FILTER:c_int=26;
const EPERM:i32=1;
const EAGAIN:i32=11;
const EINTR:i32=4;
const MSG_DONTWAIT:c_int=0x40;
const MSG_TRUNC:c_int=0x20;
const MAX:usize=32;
const L2:usize=14;
const IPV4:usize=48;
const WIRE:usize=L2+IPV4;
const SRC_PORT:u16=49321;
const DST_PORT:u16=49322;
const IP:[u8;4]=[127,0,0,1];
const SNAP_MTU:u32=1500;

#[repr(C)]
#[derive(Clone,Copy)]
struct Filter{code:u16,jt:u8,jf:u8,k:u32}
#[repr(C)]
struct FilterProgram{len:u16,filter:*mut Filter}
#[repr(C)]
#[derive(Clone,Copy)]
struct Iov{base:*mut c_void,len:usize}
impl Iov{const fn zero()->Self{Self{base:ptr::null_mut(),len:0}}}
#[repr(C)]
#[derive(Clone,Copy)]
struct Msg{
    name:*mut c_void,name_len:u32,
    iov:*mut Iov,iov_len:usize,
    control:*mut c_void,control_len:usize,flags:c_int,
}
impl Msg{const fn zero()->Self{
    Self{name:ptr::null_mut(),name_len:0,iov:ptr::null_mut(),iov_len:0,
        control:ptr::null_mut(),control_len:0,flags:0}
}}
#[repr(C)]
#[derive(Clone,Copy)]
struct Mmsg{hdr:Msg,len:c_uint}
impl Mmsg{const fn zero()->Self{Self{hdr:Msg::zero(),len:0}}}
unsafe extern "C"{
    fn socket(domain:c_int,kind:c_int,protocol:c_int)->c_int;
    fn bind(fd:c_int,addr:*const c_void,addr_len:u32)->c_int;
    fn setsockopt(fd:c_int,level:c_int,opt:c_int,val:*const c_void,len:u32)->c_int;
    fn sendto(fd:c_int,data:*const c_void,len:usize,flags:c_int,
              dst:*const c_void,dstlen:u32)->isize;
    fn recvmmsg(fd:c_int,vec:*mut Mmsg,n:c_uint,flags:c_int,timeout:*mut c_void)->c_int;
}
fn errno()->i32{io::Error::last_os_error().raw_os_error().unwrap_or(5)}
fn sock()->Result<OwnedFd,LoopError>{
    // Protocol=0 prevents receiving frames before filter+loopback bind.
    // SAFETY: constants target Linux x86_64 GNU only; successful fd gets
    // one OwnedFd immediately, auto-closed on any later error path.
    let fd=unsafe{socket(AF_PACKET,SOCK_RAW|SOCK_NONBLOCK|SOCK_CLOEXEC,0)};
    if fd<0{return Err(match errno(){
        EPERM=>LoopError::Denied(EPERM),e=>LoopError::Syscall(e),
    });}
    Ok(unsafe{OwnedFd::from_raw_fd(fd)})
}
#[derive(Debug,Clone,Copy,Eq,PartialEq)]
enum LoopError{NotOptedIn,Denied(i32),Syscall(i32),UnexpectedIndex,Stopping,StaleGeneration,BadSlot}
#[derive(Debug,Clone,Copy,Eq,PartialEq)]
enum RxEntry{Unused,Rejected(RawRxError),ExactUnauthenticated,Truncated}
#[derive(Debug,Clone,Copy,Eq,PartialEq)]
enum BatchStatus{Empty,WouldBlock,Interrupted,Ready,Stopped}
#[derive(Debug,Clone,Copy,Eq,PartialEq)]
struct Batch{count:usize,attempted:usize,status:BatchStatus,entries:[RxEntry;MAX]}
impl Batch{fn new(n:usize,status:BatchStatus)->Self{
    Self{count:0,attempted:n,status,entries:[RxEntry::Unused;MAX]}
}}

/// Only for a deliberate test frame with a process-specific cookie.
/// Classic BPF loads the raw Ethernet header at offsets 0..14, then the
/// fixed 20B IPv4+20B TCP headers and a 4B cookie at L2+40. Non-test packets
/// are rejected IN THE KERNEL before delivery to the test process.
/// No broad lo sniffing; no promiscuous or PHYSICAL interface capture.
fn cookie_filter(cookie:u32)->[Filter;25]{
    const LDH:u16=0x28;const LDB:u16=0x30;const LDW:u16=0x20;
    const JEQ:u16=0x15;const RET:u16=0x06;
    const fn ld(code:u16,offset:u32)->Filter{Filter{code,jt:0,jf:0,k:offset}}
    const fn eq(k:u32)->Filter{Filter{code:JEQ,jt:1,jf:0,k}}
    const fn no()->Filter{Filter{code:RET,jt:0,jf:0,k:0}}
    [
        ld(LDH,12),eq(ETH_P_IP as u32),no(),
        ld(LDB,14),eq(0x45),no(),
        ld(LDB,23),eq(6),no(),
        ld(LDW,26),eq(0x7f000001),no(),
        ld(LDW,30),eq(0x7f000001),no(),
        ld(LDH,34),eq(SRC_PORT as u32),no(),
        ld(LDH,36),eq(DST_PORT as u32),no(),
        ld(LDW,54),eq(cookie),no(),
        Filter{code:RET,jt:0,jf:0,k:u32::MAX}
    ]
}
fn lo_addr(ifindex:u32)->SockAddrLl{
    SockAddrLl{family:AF_PACKET as u16,protocol_be:ETH_P_IP.to_be(),
        ifindex:ifindex as i32,hatype:0,packet_type:0,
        hardware_addr_len:0,hardware_addr:[0;8]}
}
struct Loopback {
    rx:OwnedFd,
    tx:OwnedFd,
    snapshot:PacketSnapshot,
    fence:BorrowFence,
}
impl Loopback{
    fn open(explicit_opt_in:bool,cookie:u32)->Result<Self,LoopError>{
        if !explicit_opt_in{return Err(LoopError::NotOptedIn);}
        // Reject every interface except the constant "lo" before opening
        // any AF_PACKET FD, including the transmit side.
        let idx=interface_index("lo").map_err(|_|LoopError::UnexpectedIndex)?;
        if idx==0||idx>i32::MAX as u32{return Err(LoopError::UnexpectedIndex);}
        let snap=validate_config(PacketConfig{
            ifname:"lo",ifindex:idx,protocol:ETH_P_IP,packet_type:0,
            mtu:SNAP_MTU,generation:8
        }).map_err(|_|LoopError::UnexpectedIndex)?;
        if !effective_cap_net_raw().map_err(|_|LoopError::Syscall(5))?{
            return Err(LoopError::Denied(EPERM));
        }
        let rx=sock()?;
        let tx=sock()?;
        let mut filters=cookie_filter(cookie);
        let program=FilterProgram{len:filters.len() as u16,filter:filters.as_mut_ptr()};
        // SAFETY: kernel copies the immutable classic BPF program from
        // live stack memory; no pointers escape. Install *before* activation.
        let rc=unsafe{setsockopt(rx.as_raw_fd(),SOL_SOCKET,SO_ATTACH_FILTER,
            (&program as *const FilterProgram).cast::<c_void>(),
            std::mem::size_of::<FilterProgram>() as u32)};
        if rc<0{return Err(LoopError::Syscall(errno()));}
        let addr=lo_addr(idx);
        // SAFETY: complete sockaddr_ll 20B with only validated lo ifindex;
        // ETH_P_IP activates RX ONLY after the selective BPF is installed.
        let rc=unsafe{bind(rx.as_raw_fd(),
            (&addr as *const SockAddrLl).cast::<c_void>(),
            std::mem::size_of::<SockAddrLl>() as u32)};
        if rc<0{return Err(LoopError::Syscall(errno()));}
        Ok(Self{rx,tx,snapshot:snap,fence:BorrowFence::default()})
    }
    fn begin_stop(&self){self.fence.begin_stop();}
    fn drained(&self)->StopResult{self.fence.wait_drained_until(Instant::now())}
    fn send_one(&self,frame:&[u8],generation:u32)->Result<(),LoopError>{
        if generation!=self.snapshot.generation{return Err(LoopError::StaleGeneration);}
        if frame.len()!=WIRE||frame[12..14]!=ETH_P_IP.to_be_bytes()||
           frame[26..30]!=IP||frame[30..34]!=IP{
            return Err(LoopError::BadSlot);
        }
        let _borrow=self.fence.try_enter_ready().map_err(|_|LoopError::Stopping)?;
        let addr=lo_addr(self.snapshot.ifindex);
        // SAFETY: frame is borrowed immutably until synchronous nonblocking
        // sendto completes; destination is strictly the already verified lo.
        let n=unsafe{sendto(self.tx.as_raw_fd(),frame.as_ptr().cast::<c_void>(),
            frame.len(),MSG_DONTWAIT,
            (&addr as *const SockAddrLl).cast::<c_void>(),
            std::mem::size_of::<SockAddrLl>() as u32)};
        if n<0{return Err(LoopError::Syscall(errno()));}
        if n as usize!=frame.len(){return Err(LoopError::Syscall(5));}
        Ok(())
    }
    fn recv_exact(&self,generation:u32,slots:&mut [&mut [u8]],expected:&[u8])
        ->Result<Batch,LoopError>
    {
        let cap=slots.len().min(MAX);
        if cap==0{return Ok(Batch::new(0,BatchStatus::Empty));}
        if slots[..cap].iter().any(|s|s.is_empty()){return Err(LoopError::BadSlot);}
        if generation!=self.snapshot.generation{return Err(LoopError::StaleGeneration);}
        let _borrow=self.fence.try_enter_ready().map_err(|_|LoopError::Stopping)?;
        let mut addr=[SockAddrLl::zero();MAX];
        let mut iov=[Iov::zero();MAX];
        let mut vec=[Mmsg::zero();MAX];
        for (i,b) in slots[..cap].iter_mut().enumerate(){
            iov[i]=Iov{base:b.as_mut_ptr().cast::<c_void>(),len:b.len()};
            vec[i].hdr.name=ptr::addr_of_mut!(addr[i]).cast::<c_void>();
            vec[i].hdr.name_len=std::mem::size_of::<SockAddrLl>() as u32;
            vec[i].hdr.iov=ptr::addr_of_mut!(iov[i]);
            vec[i].hdr.iov_len=1;
        }
        // SAFETY: bounded <=32 mutually exclusive caller &mut byte slices,
        // stack-lived headers and addresses; synchronous MSG_DONTWAIT only,
        // RAII guard prevents stop from draining until all kernel copies end.
        let n=unsafe{recvmmsg(self.rx.as_raw_fd(),vec.as_mut_ptr(),
            cap as u32,MSG_DONTWAIT|MSG_TRUNC,ptr::null_mut())};
        if n<0{
            return match errno(){
                EAGAIN=>Ok(Batch::new(cap,BatchStatus::WouldBlock)),
                EINTR=>Ok(Batch::new(cap,BatchStatus::Interrupted)),
                e=>Err(LoopError::Syscall(e)),
            };
        }
        let n=n as usize;
        if n==0||n>cap{return Err(LoopError::Syscall(5));}
        let mut out=Batch::new(cap,BatchStatus::Ready);
        out.count=n;
        for i in 0..n{
            let original=vec[i].len as usize;
            let captured=original.min(slots[i].len());
            // SOCK_RAW has 14B link-layer header; never guess VLAN.
            if original<L2 || captured<L2 {
                out.entries[i]=RxEntry::Truncated;
                continue;
            }
            let meta=RawReceiveMetadata{
                sockaddr:addr[i],sockaddr_len:vec[i].hdr.name_len as usize,
                captured_len:captured-L2,original_len:original-L2,
                msg_flags:vec[i].hdr.flags,generation,
            };
            out.entries[i]=match validate_sockaddr(self.snapshot,meta){
                Err(RawRxError::Truncated)=>RxEntry::Truncated,
                Err(e)=>RxEntry::Rejected(e),
                Ok(()) if captured==expected.len() && &slots[i][..captured]==expected
                    => RxEntry::ExactUnauthenticated,
                Ok(())=>RxEntry::Rejected(RawRxError::LengthOrMtu)
            };
        }
        Ok(out)
    }
}
/// Independent checksum construction for one exact full L2/IPv4/TCP test
/// packet; only local lo 127.0.0.1->127.0.0.1 with process cookie, not real
/// credentials/record ciphertext. Kernel may synthesize RST; BPF drops it.
fn checksum(bytes:&[u8])->u16{
    let mut sum=0u32;
    let mut chunks=bytes.chunks_exact(2);
    for p in &mut chunks{sum+=u16::from_be_bytes([p[0],p[1]]) as u32;}
    if let [odd]=chunks.remainder(){sum+=(*odd as u32)<<8;}
    while sum>0xffff{sum=(sum&0xffff)+(sum>>16);}
    !(sum as u16)
}
fn frame(cookie:u32)->[u8;WIRE]{
    let mut b=[0u8;WIRE];
    b[12..14].copy_from_slice(&ETH_P_IP.to_be_bytes());
    let (ip,tcp)=b[L2..].split_at_mut(20);
    ip[0]=0x45;ip[2..4].copy_from_slice(&(IPV4 as u16).to_be_bytes());
    ip[4..6].copy_from_slice(&0x704u16.to_be_bytes());
    ip[6..8].copy_from_slice(&0x4000u16.to_be_bytes());
    ip[8]=64;ip[9]=6;ip[12..16].copy_from_slice(&IP);
    ip[16..20].copy_from_slice(&IP);
    ip[10..12].copy_from_slice(&checksum(ip).to_be_bytes());
    tcp[0..2].copy_from_slice(&SRC_PORT.to_be_bytes());
    tcp[2..4].copy_from_slice(&DST_PORT.to_be_bytes());
    tcp[4..8].copy_from_slice(&0x10203040u32.to_be_bytes());
    tcp[8..12].copy_from_slice(&1u32.to_be_bytes());
    tcp[12]=0x50;tcp[13]=0x18;tcp[14..16].copy_from_slice(&1024u16.to_be_bytes());
    tcp[20..24].copy_from_slice(&cookie.to_be_bytes());
    tcp[24..28].copy_from_slice(b"M4R8");
    let mut pseudo=[0u8;40];
    pseudo[..4].copy_from_slice(&IP);pseudo[4..8].copy_from_slice(&IP);
    pseudo[9]=6;pseudo[10..12].copy_from_slice(&(tcp.len() as u16).to_be_bytes());
    pseudo[12..].copy_from_slice(tcp);
    tcp[16..18].copy_from_slice(&checksum(&pseudo).to_be_bytes());
    b
}
fn test_cookie()->u32{0x4d340000 | (std::process::id()&0xffff)}

#[test]
fn r1_packet_loopback_optin_deny_without_side_effects(){
    assert!(matches!(Loopback::open(false,test_cookie()),Err(LoopError::NotOptedIn)));
}
#[test]
fn r1_packet_loopback_raw_capability_negative_or_real(){
    let cap=effective_cap_net_raw().unwrap();
    match Loopback::open(true,test_cookie()){
        Err(LoopError::Denied(EPERM))=>{
            assert!(!cap || std::env::var_os("CI").is_some());
            eprintln!("RAW_RX_NOT_RUN CAP_NET_RAW missing or kernel EPERM");
        }
        Ok(l)=>{
            assert!(cap);
            assert_eq!(l.snapshot.ifindex,interface_index("lo").unwrap());
            assert_eq!(l.drained(),StopResult::Drained);
            l.begin_stop();
            assert_eq!(l.drained(),StopResult::Drained);
            eprintln!("RAW_LOOPBACK_PREPARED only lo; kernel CAP_NET_RAW present");
        }
        Err(e)=>panic!("unexpected scoped raw socket failure: {e:?}")
    }
}
#[test]
fn r1_packet_loopback_ipv4_tcp_full_frame_checksum_native_fixture(){
    let x=frame(test_cookie());
    assert_eq!(x.len(),62);
    assert_eq!(checksum(&x[L2..L2+20]),0);
    let tcp=&x[L2+20..];
    let mut pseudo=[0u8;40];
    pseudo[..4].copy_from_slice(&IP);pseudo[4..8].copy_from_slice(&IP);
    pseudo[9]=6;pseudo[10..12].copy_from_slice(&(tcp.len() as u16).to_be_bytes());
    pseudo[12..].copy_from_slice(tcp);
    assert_eq!(checksum(&pseudo),0);
}
#[test]
fn r1_packet_loopback_cap_gated_controlled_raw_rx_tx_truncation_stop(){
    let cookie=test_cookie();
    let l=match Loopback::open(true,cookie){
        Ok(s)=>s,
        Err(LoopError::Denied(EPERM))=>{
            eprintln!("RAW_RX_NOT_RUN lack CAP_NET_RAW: exact EPERM held by prior child test");
            return;
        }
        Err(e)=>panic!("unexpected lo preflight {e:?}")
    };
    let p=frame(cookie);
    // Native send and receive occur ONLY in the same runner's loopback netns.
    l.send_one(&p,8).unwrap();
    let mut seen=false;
    for _ in 0..64 {
        let mut storage=[[0xa5u8;128];33];
        let mut slots:[&mut [u8];33]=storage.each_mut().map(|s|s.as_mut_slice());
        let got=l.recv_exact(8,&mut slots,&p).unwrap();
        assert!(got.attempted<=32);
        assert!(storage[32].iter().all(|&x|x==0xa5));
        if got.entries[..got.count].iter().any(|e|*e==RxEntry::ExactUnauthenticated){
            seen=true;break;
        }
        assert!(matches!(got.status,BatchStatus::Ready|BatchStatus::WouldBlock|BatchStatus::Interrupted));
        std::thread::yield_now();
    }
    assert!(seen,"controlled lo self-frame not seen; never infer native raw positive");
    // A second frame is received into a deliberately insufficient buffer:
    // length/truncation must not be promoted into authenticated payload.
    l.send_one(&p,8).unwrap();
    let mut truncated=false;
    for _ in 0..64 {
        let mut small=[0xcbu8;16];
        let mut slots=[small.as_mut_slice()];
        let got=l.recv_exact(8,&mut slots,&p).unwrap();
        if got.entries[0]==RxEntry::Truncated{truncated=true;break;}
        std::thread::yield_now();
    }
    assert!(truncated,"MSG_TRUNC or kernel-reported original length must reject");
    let lease=l.fence.try_enter_ready().unwrap();
    assert_eq!(l.fence.outstanding(),1);
    assert_eq!(l.drained(),StopResult::Pending{outstanding:1});
    l.begin_stop();
    let mut one=[0u8;128];let mut slots=[one.as_mut_slice()];
    assert_eq!(l.recv_exact(8,&mut slots,&p),Err(LoopError::Stopping));
    assert_eq!(l.send_one(&p,8),Err(LoopError::Stopping));
    drop(lease);
    assert_eq!(l.drained(),StopResult::Drained);
    eprintln!("RAW_RX_LOOPBACK_PASS isolated lo self-injected checked L2/IP/TCP and truncation");
}
