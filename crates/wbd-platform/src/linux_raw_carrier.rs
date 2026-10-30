//! Linux x86_64 GNU IPv4/TCP raw TX for an already authenticated V4 owner.
//! Sends original immutable M1 FrozenRecord via normal ipv4_tcp::build.
//! No TLS keys/cold auth/Go readiness in this driver. Owned Linux raw fd
//! needs CAP_NET_RAW and exact interface bound by kernel SO_BINDTODEVICE.
//! STOP fences synchronously borrowed record until kernel copy completes.
//! Kernel acceptance is NOT remote peer ACK or application delivery.
#![cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
use std::ffi::{c_int,c_void,CString};
use std::io;
use std::net::Ipv4Addr;
use std::os::fd::{FromRawFd,AsRawFd,OwnedFd};
use std::sync::{Mutex,atomic::{AtomicBool,Ordering}};
use std::time::{Instant,Duration};
use crate::r1::{BorrowFence,BorrowError,StopResult};
use crate::{TxBatchOutcome,TxError};
use crate::linux_batch::{self,KernelSendReport,KernelSendSignal};
use crate::linux_rx_batch::{self,RxEntry,RxStatus};
use crate::linux_packet_preflight::{interface_index,observe_interface_mtu};
use crate::linux_mtu_scope::{ScopedRouteBudget,BudgetError};
use crate::ipv4_tcp::{self,Ipv4Tuple,Presentation,PacketPersona};
use crate::rx_ipv4_tcp::{parse_data_packet,parse_ack_packet,TrustedRx,RxError};
use wbd_types::buffer_contract::FrozenRecordHandle;

const AF_INET:c_int=2;
const SOCK_RAW:c_int=3;
const SOCK_NONBLOCK:c_int=0x800;
const SOCK_CLOEXEC:c_int=0x80000;
const IPPROTO_RAW:c_int=255;
const IPPROTO_TCP:c_int=6;
const POLLIN:i16=1;
#[repr(C)]
struct PollFd{fd:c_int,events:i16,revents:i16}
const IPPROTO_IP:c_int=0;
const IP_HDRINCL:c_int=3;
const SOL_SOCKET:c_int=1;
const SO_BINDTODEVICE:c_int=25;
const SO_ATTACH_FILTER:c_int=26;
const SO_RCVBUF:c_int=8;
// Linux doubles a SO_RCVBUF request for bookkeeping; 4 MiB requested
// yields up to 8 MiB effective per owned raw RX socket, capped by rmem_max.
// A 4 MiB request is ~20x the observed 212,992-byte guest default. This is
// NOT a global sysctl change, and it never changes qdisc fq600 or FEC pools.
const RAW_RX_RCVBUF_REQUEST_BYTES:c_int=4*1024*1024;
const RAW_RX_RCVBUF_EFFECTIVE_CEILING_BYTES:c_int=8*1024*1024;
// Linux classic BPF instruction ABI. Kernel copies this short program at setsockopt.
#[repr(C)]
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
struct SockFilter{code:u16,jt:u8,jf:u8,k:u32}
#[repr(C)]
struct SockFprog{len:u16,filter:*const SockFilter}
const MSG_DONTWAIT:c_int=0x40;
#[repr(C)]
struct SockAddrIn {
    family:u16, port:u16, ip_be:u32, zero:[u8;8],
}
unsafe extern "C" {
    fn socket(domain:c_int,typ:c_int,proto:c_int)->c_int;
    fn setsockopt(fd:c_int,level:c_int,opt:c_int,value:*const c_void,len:u32)->c_int;
    fn getsockopt(fd:c_int,level:c_int,opt:c_int,value:*mut c_void,len:*mut u32)->c_int;
    fn poll(fds:*mut PollFd,nfds:usize,timeout:c_int)->c_int;
    fn recvfrom(fd:c_int,bytes:*mut c_void,len:usize,flags:c_int,
        src:*mut c_void,addr_len:*mut u32)->isize;
    fn sendto(fd:c_int,bytes:*const c_void,len:usize,flags:c_int,
        dst:*const c_void,dst_len:u32)->isize;
}
fn errno()->i32{io::Error::last_os_error().raw_os_error().unwrap_or(5)}
/// Bound just this owned Linux raw receive queue. Never SO_RCVBUFFORCE,
/// never adjust the host/guest sysctl, never call once per packet.
/// Return actual Linux effective doubled/clamped allocation, not request.
fn tune_raw_rx_buffer(fd:c_int)->Result<c_int,RawTxError>{
    let wanted=RAW_RX_RCVBUF_REQUEST_BYTES;
    // SAFETY: kernel synchronously copies a bounded 32-bit value.
    let rc=unsafe{setsockopt(fd,SOL_SOCKET,SO_RCVBUF,
        (&wanted as *const c_int).cast(),std::mem::size_of::<c_int>() as u32)};
    if rc!=0{return Err(RawTxError::Kernel(errno()))}
    let mut effective:c_int=0;
    let mut size=std::mem::size_of::<c_int>() as u32;
    // SAFETY: kernel writes one aligned c_int and its actual size.
    let rc=unsafe{getsockopt(fd,SOL_SOCKET,SO_RCVBUF,
        (&mut effective as *mut c_int).cast(),&mut size)};
    if rc!=0{return Err(RawTxError::Kernel(errno()))}
    if size!=std::mem::size_of::<c_int>() as u32 ||
        effective<=0 || effective>RAW_RX_RCVBUF_EFFECTIVE_CEILING_BYTES {
        return Err(RawTxError::InvalidInterface)
    }
    Ok(effective)
}
/// A tuple has to be checked before indexing a Rust slice or consulting
/// kernel link/route state. Malformed or unauthenticated tuples are not an
/// interface/MTU event and must never cause a panic or packet transmission.
fn checked_destination(tuple:Ipv4Tuple<'_>)->Result<Ipv4Addr,RawTxError>{
    if tuple.src_ip.len()!=4||tuple.dst_ip.len()!=4||
       tuple.src_port==0||tuple.dst_port==0 {
        return Err(RawTxError::InvalidPacket)
    }
    Ok(Ipv4Addr::new(tuple.dst_ip[0],tuple.dst_ip[1],
        tuple.dst_ip[2],tuple.dst_ip[3]))
}

#[derive(Debug,Clone,Copy,Eq,PartialEq)]
pub enum RawTxError {
    InvalidScope,Stopped,InvalidInterface,Kernel(i32),InvalidPacket,
    BoundedMtu,PacketExceedsBudget,NoCapacity,RouteStale,RouteUnavailable,ShortSend,UnsupportedOptions,
}
pub struct ScopedRawIpv4Tx {
    fd:OwnedFd,
    ifindex:u32,
    ifname:String,
    generation:u32,
    mtu:usize,
    budget:ScopedRouteBudget,
    stopped:AtomicBool,
    borrow:BorrowFence,
    serialize:Mutex<()>,
}
impl ScopedRawIpv4Tx {
    /// Open only after authenticated Go V4 Detach/Commit in the SAME
    /// network namespace. Interface name+ifindex/actual MTU must match.
    /// No unprivileged UDP fallback on ENOPERM/CAP_NET_RAW failure.
    pub fn open(ifname:&str,expected_ifindex:u32,generation:u32)
        ->Result<Self,RawTxError>{
        if generation==0 || ifname.is_empty() || ifname.len()>15 ||
            !ifname.bytes().all(|b|b.is_ascii_alphanumeric()||b==b'_'||b==b'-'){
            return Err(RawTxError::InvalidInterface)
        }
        let actual=interface_index(ifname).map_err(|_|RawTxError::InvalidInterface)?;
        if actual==0 || actual!=expected_ifindex {
            return Err(RawTxError::InvalidInterface)
        }
        let observed=observe_interface_mtu(ifname,actual)
            .map_err(|_|RawTxError::InvalidInterface)?;
        // SAFETY: Linux raw fd ownership is transferred into OwnedFd once.
        let descriptor=unsafe{socket(AF_INET,SOCK_RAW|SOCK_NONBLOCK|SOCK_CLOEXEC,
            IPPROTO_RAW)};
        if descriptor<0{return Err(RawTxError::Kernel(errno()))}
        let fd=unsafe{OwnedFd::from_raw_fd(descriptor)};
        let name=CString::new(ifname).map_err(|_|RawTxError::InvalidInterface)?;
        // SAFETY: kernel copies live NUL-terminated validated name.
        let rc=unsafe{setsockopt(fd.as_raw_fd(),SOL_SOCKET,SO_BINDTODEVICE,
            name.as_ptr().cast(),name.as_bytes_with_nul().len() as u32)};
        if rc!=0{return Err(RawTxError::Kernel(errno()))}
        let on:c_int=1;
        // SAFETY: live aligned c_int and fd, explicit userspace IPv4 header.
        let rc=unsafe{setsockopt(fd.as_raw_fd(),IPPROTO_IP,IP_HDRINCL,
            (&on as *const c_int).cast(),std::mem::size_of::<c_int>() as u32)};
        if rc!=0{return Err(RawTxError::Kernel(errno()))}
        let budget=ScopedRouteBudget::open(ifname,actual,generation,observed.kernel_mtu)
            .map_err(|_|RawTxError::InvalidInterface)?;
        Ok(Self{
            fd,ifindex:actual,ifname:ifname.to_owned(),generation,
            mtu:observed.kernel_mtu as usize,budget,stopped:AtomicBool::new(false),
            borrow:BorrowFence::default(),serialize:Mutex::new(())
        })
    }
    pub fn generation(&self)->u32{self.generation}
    pub fn is_stopping(&self)->bool{self.stopped.load(Ordering::Acquire)}
    pub fn begin_stop(&self){
        self.stopped.store(true,Ordering::Release);
        self.borrow.begin_stop();
    }
    pub fn stop_until(&self,deadline:Instant)->StopResult{
        self.begin_stop();
        self.borrow.wait_drained_until(deadline)
    }
    pub fn outstanding(&self)->usize{self.borrow.outstanding()}
    /// A SYN/route tuple MUST be supplied by the credential-checked Go
    /// owner; raw packet shape and TCP presentation are not identity.
    /// Original PN/record and bytewise TCP sequence are immutable.
    pub fn send_one<H:FrozenRecordHandle>(&self,
        generation:u32,record:&H,tuple:Ipv4Tuple<'_>,presentation:Presentation,
    )->Result<usize,RawTxError>{
        if generation!=self.generation{return Err(RawTxError::InvalidScope)}
        if self.is_stopping(){return Err(RawTxError::Stopped)}
        let _guard=self.borrow.try_enter_ready().map_err(|e|match e {
            BorrowError::Stopping=>RawTxError::Stopped,
            BorrowError::TooManyLoans=>RawTxError::NoCapacity,
        })?;
        let _lock=self.serialize.lock().map_err(|_|RawTxError::InvalidInterface)?;
        let dest_ip=checked_destination(tuple)?;
        let bounded=self.budget.send_budget(dest_ip)
            .map_err(|e|match e {
                BudgetError::Unavailable=>RawTxError::RouteUnavailable,
                BudgetError::ChangedOrInvalid|BudgetError::Deferred=>RawTxError::RouteStale,
            })?;
        let mut scratch=[0u8;2048];
        let packet=ipv4_tcp::build(tuple,presentation,record,None,
            bounded.min(scratch.len()),&mut scratch)
            .map_err(|e|match e {
                ipv4_tcp::PacketError::MtuExceeded{..}=>RawTxError::PacketExceedsBudget,
                _=>RawTxError::InvalidPacket,
            })?;
        if packet.len()<41 || packet[9]!=6 ||
            packet[12..16]!=tuple.src_ip[..] ||
            packet[16..20]!=tuple.dst_ip[..]{
            return Err(RawTxError::InvalidPacket)
        }
        let dest=[tuple.dst_ip[0],tuple.dst_ip[1],tuple.dst_ip[2],tuple.dst_ip[3]];
        let addr=SockAddrIn{
            family:AF_INET as u16,port:0,
            ip_be:u32::from_ne_bytes(dest),zero:[0;8],
        };
        // SAFETY: immutable caller record lives through synchronous kernel
        // copy; local packet and sockaddr live until sendto completes.
        let n=unsafe{sendto(self.fd.as_raw_fd(),packet.as_ptr().cast(),packet.len(),
            MSG_DONTWAIT,(&addr as *const SockAddrIn).cast(),
            std::mem::size_of::<SockAddrIn>() as u32)};
        if n<0 {
            let e=errno();
            if matches!(e,90|19|100|101|113){self.budget.invalidate()}
            return Err(RawTxError::Kernel(e))
        }
        if n as usize!=packet.len(){self.budget.invalidate();return Err(RawTxError::ShortSend)}
        Ok(n as usize)
    }
}

/// Real kernel IPv4/TCP receive, strict owner-scoped tuple & checked
/// TCP checksum BEFORE the original Rust M1 AEAD/PN admission. Kernel
/// writes L3 directly into caller's M1 UniqueBuffer, then payload is
/// compacted within the SAME slab (no ciphertext heap-copy or new owner).
/// This driver never authenticates, publishes LINK, or grants V4 authority.
// Raw IPPROTO_TCP sockets see every local TCP flow on their bound interface.
// Filter by a tuple obtained only from the authenticated Go connection, before
// the kernel copies unrelated lane packets to userspace. AEAD remains mandatory.
fn exact_tcp_rx_filter(tuple:Ipv4Tuple<'_>)->Result<[SockFilter;13],RawTxError>{
    checked_destination(tuple)?;
    let src=u32::from_be_bytes(tuple.src_ip.try_into().map_err(|_|RawTxError::InvalidPacket)?);
    let dst=u32::from_be_bytes(tuple.dst_ip.try_into().map_err(|_|RawTxError::InvalidPacket)?);
    // BPF interpreter converts network-order packet fields to host-order A.
    // LDX MSH computes dynamic IPv4 IHL (IP options, no assumed 20B offset).
    let load=|code,k|SockFilter{code,jt:0,jf:0,k};
    let eq=|k,jf|SockFilter{code:0x15,jt:0,jf,k}; // JMP JEQ K
    Ok([
        load(0x30,9),eq(6,10),       // IPv4 protocol TCP (also enforced by socket)
        load(0x20,12),eq(src,8),   // exact source IP
        load(0x20,16),eq(dst,6),   // exact destination IP
        load(0xb1,0),             // LDX B MSH [0] IPv4 IHL in bytes
        load(0x48,0),eq(u32::from(tuple.src_port),3), // LD H IND [X]
        load(0x48,2),eq(u32::from(tuple.dst_port),1),
        load(0x06,u32::MAX),       // accept all bytes, not packet identity
        load(0x06,0),              // reject unmatched packets in kernel
    ])
}
pub struct ScopedRawIpv4Rx {
    fd:OwnedFd,
    ifindex:u32,
    ifname:String,
    generation:u32,
    mtu:usize,
    budget:ScopedRouteBudget,
    stopped:AtomicBool,
    borrow:BorrowFence,
    serialize:Mutex<()>,
}
impl ScopedRawIpv4Rx {
    /// Kernel-level prefilter; tuple comes from already-authenticated GoFlow.
    /// Failure is fail-closed: no unfiltered fallback to extra socket reads.
    pub fn open_exact_tuple(ifname:&str,expected_ifindex:u32,generation:u32,
        tuple:Ipv4Tuple<'_>)->Result<Self,RawTxError>{
        let instructions=exact_tcp_rx_filter(tuple)?;
        let rx=Self::open(ifname,expected_ifindex,generation)?;
        let prog=SockFprog{len:instructions.len() as u16,
            filter:instructions.as_ptr()};
        // SAFETY: synchronously copied Linux sock_fprog references the live
        // immutable stack instruction array. Owned fd closes on failure.
        let rc=unsafe{setsockopt(rx.fd.as_raw_fd(),SOL_SOCKET,SO_ATTACH_FILTER,
            (&prog as *const SockFprog).cast(),std::mem::size_of::<SockFprog>() as u32)};
        if rc!=0{return Err(RawTxError::Kernel(errno()))}
        Ok(rx)
    }
    pub fn open(ifname:&str,expected_ifindex:u32,generation:u32)
        ->Result<Self,RawTxError>{
        if generation==0 || ifname.is_empty()||ifname.len()>15 ||
            !ifname.bytes().all(|b|b.is_ascii_alphanumeric()||b==b'_'||b==b'-'){
            return Err(RawTxError::InvalidInterface)
        }
        let ifindex=interface_index(ifname).map_err(|_|RawTxError::InvalidInterface)?;
        if ifindex==0 || ifindex!=expected_ifindex {
            return Err(RawTxError::InvalidInterface)
        }
        let observed=observe_interface_mtu(ifname,ifindex)
            .map_err(|_|RawTxError::InvalidInterface)?;
        // SAFETY: owned nonblocking IPPROTO_TCP socket, never promiscuous,
        // bound to exact validated interface before any kernel receive.
        let fd=unsafe{socket(AF_INET,SOCK_RAW|SOCK_NONBLOCK|SOCK_CLOEXEC,IPPROTO_TCP)};
        if fd<0{return Err(RawTxError::Kernel(errno()))}
        let fd=unsafe{OwnedFd::from_raw_fd(fd)};
        let name=CString::new(ifname).map_err(|_|RawTxError::InvalidInterface)?;
        let rc=unsafe{setsockopt(fd.as_raw_fd(),SOL_SOCKET,SO_BINDTODEVICE,
            name.as_ptr().cast(),name.as_bytes_with_nul().len() as u32)};
        if rc!=0{return Err(RawTxError::Kernel(errno()))}
        // This is a receive-side Linux raw IPPROTO_TCP queue, not the
        // already verified egress TUN fq600. Keep scoped error cleanup:
        // owned fd automatically closes on all tuning/readback failures.
        let actual_rx_bytes=tune_raw_rx_buffer(fd.as_raw_fd())?;
        eprintln!("WBD_LINUX_RAW_RX_RCVBUF requested_bytes={} effective_bytes={} kernel_capped={} scope=OWNED_RAW_RX_SOCKET",
            RAW_RX_RCVBUF_REQUEST_BYTES,actual_rx_bytes,
            actual_rx_bytes<RAW_RX_RCVBUF_EFFECTIVE_CEILING_BYTES);
        let budget=ScopedRouteBudget::open(ifname,ifindex,generation,observed.kernel_mtu)
            .map_err(|_|RawTxError::InvalidInterface)?;
        Ok(Self{fd,ifindex,ifname:ifname.to_owned(),generation,
            mtu:observed.kernel_mtu as usize,budget,stopped:AtomicBool::new(false),
            borrow:BorrowFence::default(),serialize:Mutex::new(())})
    }
    pub fn generation(&self)->u32{self.generation}
    /// Readiness-only descriptor. Original Rust owner joins its workers before dropping the driver.
    pub fn readiness_fd(&self)->i32{self.fd.as_raw_fd()}
    pub fn is_stopping(&self)->bool{self.stopped.load(Ordering::Acquire)}
    pub fn begin_stop(&self){
        self.stopped.store(true,Ordering::Release);
        self.borrow.begin_stop();
    }
    pub fn outstanding(&self)->usize{self.borrow.outstanding()}
    pub fn stop_until(&self,deadline:Instant)->StopResult{
        self.begin_stop();self.borrow.wait_drained_until(deadline)
    }
    pub fn recv_one_into(&self,generation:u32,buffer:&mut [u8],
        tuple:Ipv4Tuple<'_>,persona:PacketPersona)
        ->Result<(usize,u32),RawTxError>{
        if generation!=self.generation{return Err(RawTxError::InvalidScope)}
        if self.is_stopping(){return Err(RawTxError::Stopped)}
        if buffer.len()<64{return Err(RawTxError::InvalidPacket)}
        let _loan=self.borrow.try_enter_ready().map_err(|e|match e{
            BorrowError::Stopping=>RawTxError::Stopped,
            BorrowError::TooManyLoans=>RawTxError::BoundedMtu,
        })?;
        let _lock=self.serialize.lock().map_err(|_|RawTxError::InvalidInterface)?;
        let mtu=self.budget.receive_budget()
            .map_err(|e|match e{
                BudgetError::Unavailable=>RawTxError::RouteUnavailable,
                BudgetError::ChangedOrInvalid|BudgetError::Deferred=>RawTxError::RouteStale,
            })?;
        let deadline=Instant::now()+Duration::from_millis(750);
        // Bounded irrelevant Linux RST/ACK traffic can share this interface.
        // Only the *exact* configured tuple and full checksummed DATA is
        // exposed as untrusted ciphertext to the original engine owner.
        for _ in 0..32{
            let time=deadline.saturating_duration_since(Instant::now());
            if time.is_zero(){return Err(RawTxError::Kernel(110))}
            let mut pfd=PollFd{fd:self.fd.as_raw_fd(),events:POLLIN,revents:0};
            let rc=unsafe{poll(&mut pfd,1,time.as_millis().max(1).min(750) as c_int)};
            if rc<0{return Err(RawTxError::Kernel(errno()))}
            if rc==0{return Err(RawTxError::Kernel(110))}
            if pfd.revents&POLLIN==0{return Err(RawTxError::InvalidPacket)}
            // SAFETY: original caller M1 slab stays exclusively borrowed
            // while synchronous recvfrom copies packet bytes.
            let n=unsafe{recvfrom(self.fd.as_raw_fd(),buffer.as_mut_ptr().cast(),
                buffer.len().min(mtu),MSG_DONTWAIT,
                std::ptr::null_mut(),std::ptr::null_mut())};
            if n<0{
                let e=errno();if e==11||e==4{continue}
                return Err(RawTxError::Kernel(e))
            }
            let n=n as usize;
            if n<40 {continue}
            let parsed=match parse_data_packet(&buffer[..n],TrustedRx{
                tuple,persona,mtu:self.mtu,authenticated_options:None,
            }){
                Ok(p)=>p,
                Err(RxError::WrongTuple|RxError::WrongProtocol|
                    RxError::InvalidDataFlags|RxError::EmptyData|
                    RxError::WrongPersona|RxError::FragmentedOrUnexpectedFlags|
                    RxError::WrongVersionOrIhl) => continue,
                Err(_)=>return Err(RawTxError::InvalidPacket),
            };
            let start=n-parsed.ciphertext.len();
            let len=parsed.ciphertext.len();
            let seq=parsed.seq32;
            if len==0 {return Err(RawTxError::InvalidPacket)}
            buffer.copy_within(start..n,0);
            return Ok((len,seq))
        }
        Err(RawTxError::Kernel(110))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn game_exact_tuple_kernel_bpf_matches_authenticated_four_tuple(){
        let src=[10,2,0,4];let dst=[10,3,0,5];
        let f=exact_tcp_rx_filter(Ipv4Tuple{
            src_ip:&src,dst_ip:&dst,src_port:45001,dst_port:443
        }).unwrap();
        assert_eq!(f.len(),13);
        assert_eq!(f[0].code,0x30);assert_eq!(f[0].k,9);
        assert_eq!(f[3].k,u32::from_be_bytes(src));
        assert_eq!(f[5].k,u32::from_be_bytes(dst));
        assert_eq!(f[6].code,0xb1); // IPv4 options-safe IHL
        assert_eq!(f[8].k,45001);assert_eq!(f[10].k,443);
        for i in [1usize,3,5,8,10]{
            assert_eq!(i+1+f[i].jf as usize,12); // all rejects fail closed
        }
        assert_eq!(f[11].k,u32::MAX);assert_eq!(f[12].k,0);
        assert!(matches!(exact_tcp_rx_filter(Ipv4Tuple{
            src_ip:&src,dst_ip:&dst,src_port:0,dst_port:443
        }),Err(RawTxError::InvalidPacket)));
    }
    #[test]
    fn r1_raw_bad_interface_fails_before_socket() {
        assert!(matches!(ScopedRawIpv4Tx::open("../lo",1,1),
            Err(RawTxError::InvalidInterface)));
        assert!(matches!(ScopedRawIpv4Tx::open("lo",0,1),
            Err(RawTxError::InvalidInterface)));
        assert!(matches!(ScopedRawIpv4Tx::open("lo",1,0),
            Err(RawTxError::InvalidInterface)));
    }
}

// Ready-only scoped raw driver: at most 32 kernel send attempts/receive slots,
// with no Vec, heap frame copies or new authenticated Rust/Go authority.
const MAX_READY_RAW:usize=32;
#[derive(Debug,Clone,Copy,Eq,PartialEq)]
pub enum RawReadyStatus {
    Empty, Ready, AtCap, WouldBlock, Interrupted, IoUncertain,
}
#[derive(Debug,Clone,Copy,Eq,PartialEq)]
pub enum RawReadyEntry{
    Unused,
    /// Caller still owns this original buffer. Parser output is not AEAD.
    Unauthenticated {cipher_len:usize,seq32:u32,ack32:u32},
    /// TCP-only, tuple/TTL/checksum/MTU checked; never AEAD-authenticated.
    /// Only eligible as an optional scoped outer cache-retirement hint.
    PureAck {ack32:u32},
    Rejected,
    Truncated {wire_len:usize,capacity:usize},
}
#[derive(Debug,Clone,Copy,Eq,PartialEq)]
pub struct RawReadyBatch{
    pub requested:usize,
    pub attempted:usize,
    pub observed:usize,
    pub status:RawReadyStatus,
    pub entries:[RawReadyEntry;MAX_READY_RAW],
}
impl RawReadyBatch{
    fn new(requested:usize)->Self{
        Self{requested,attempted:requested.min(MAX_READY_RAW),observed:0,
            status:if requested==0{RawReadyStatus::Empty}else{RawReadyStatus::Ready},
            entries:[RawReadyEntry::Unused;MAX_READY_RAW]}
    }
    pub fn entry(&self,i:usize)->Option<RawReadyEntry>{
        if i<self.attempted{Some(self.entries[i])}else{None}
    }
}
fn raw_batch_failure(n:usize,err:RawTxError)->KernelSendReport{
    let (uncertain,error,signal)=match err{
        RawTxError::Stopped=>(None,TxError::Stopping,KernelSendSignal::Stopping),
        RawTxError::BoundedMtu=>(None,TxError::IoFailed,KernelSendSignal::MtuExceeded),
        RawTxError::PacketExceedsBudget|RawTxError::NoCapacity=>
            (None,TxError::IoFailed,KernelSendSignal::PreflightRejected),
        RawTxError::InvalidInterface=>(None,TxError::IoFailed,KernelSendSignal::DeviceUnavailable),
        RawTxError::RouteUnavailable|RawTxError::RouteStale=>
            (None,TxError::IoFailed,KernelSendSignal::RouteUnavailable),
        RawTxError::ShortSend=>(Some(n),TxError::IoUncertain,KernelSendSignal::AmbiguousCompletion),
        RawTxError::Kernel(4)=>(Some(n),TxError::IoUncertain,KernelSendSignal::Interrupted),
        RawTxError::Kernel(11)=>(None,TxError::WouldBlock,KernelSendSignal::Backpressure),
        RawTxError::Kernel(90)=>(None,TxError::IoFailed,KernelSendSignal::MtuExceeded),
        RawTxError::Kernel(19)=>(None,TxError::IoFailed,KernelSendSignal::DeviceUnavailable),
        RawTxError::Kernel(100|101|113)=>(None,TxError::IoFailed,KernelSendSignal::RouteUnavailable),
        RawTxError::Kernel(e)=>(Some(n),TxError::IoUncertain,KernelSendSignal::OtherErrno(e)),
        _=>(None,TxError::IoFailed,KernelSendSignal::PreflightRejected),
    };
    KernelSendReport{outcome:TxBatchOutcome{
        accepted_prefix:n,uncertain_index:uncertain,error:Some(error)},signal}
}
impl ScopedRawIpv4Tx{
    /// A bounded ready-only *sequence* of synchronous sendto calls, **not**
    /// hardware multishot sendmmsg. Reports the precise kernel-copied prefix,
    /// one conservatively uncertain item when necessary and untouched tail.
    /// No record is re-sealed or re-numbered; caller chooses retry policy.
    pub fn send_ready_batch<H:FrozenRecordHandle>(
        &self,generation:u32,frames:&[H],tuple:Ipv4Tuple<'_>,
        presentation:Presentation,
    )->KernelSendReport{
        let limit=frames.len().min(MAX_READY_RAW);
        // Even empty callbacks cannot claim success on a retired owner.
        if generation!=self.generation {
            return raw_batch_failure(0,RawTxError::InvalidScope)
        }
        if self.is_stopping() {
            return raw_batch_failure(0,RawTxError::Stopped)
        }
        if limit==0{return KernelSendReport{
            outcome:TxBatchOutcome::copied_all(0),signal:KernelSendSignal::None}}
        for (i,record) in frames[..limit].iter().enumerate(){
            if let Err(e)=self.send_one(generation,record,tuple,presentation){
                return raw_batch_failure(i,e)
            }
        }
        if limit==frames.len(){
            KernelSendReport{outcome:TxBatchOutcome::copied_all(limit),
                signal:KernelSendSignal::None}
        }else{
            KernelSendReport{outcome:TxBatchOutcome{
                accepted_prefix:limit,uncertain_index:None,
                error:Some(TxError::WouldBlock)},signal:KernelSendSignal::None}
        }
    }
}
impl ScopedRawIpv4Rx{
    /// One strictly nonblocking drain (poll timeout 0, recv MSG_DONTWAIT |
    /// MSG_TRUNC), at most 32 caller-supplied independent mutable packet
    /// slots. Kernel copies L3 directly into original caller buffer; only
    /// valid DATA ciphertext is compacted **in place** within that slice.
    /// Unrelated packets, invalid checksums and truncation never promote a
    /// trusted record. Does not read sysfs per received packet.
    pub fn receive_ready_batch(&self,generation:u32,buffers:&mut [&mut [u8]],
        tuple:Ipv4Tuple<'_>,persona:PacketPersona
    )->Result<RawReadyBatch,RawTxError>{
        if generation!=self.generation{return Err(RawTxError::InvalidScope)}
        if self.is_stopping(){return Err(RawTxError::Stopped)}
        let mut outcome=RawReadyBatch::new(buffers.len());
        if outcome.attempted==0{return Ok(outcome)}
        if buffers[..outcome.attempted].iter().any(|b|b.len()<40){
            return Err(RawTxError::InvalidPacket)
        }
        let _guard=self.borrow.try_enter_ready().map_err(|e|match e{
            BorrowError::Stopping=>RawTxError::Stopped,
            BorrowError::TooManyLoans=>RawTxError::BoundedMtu,
        })?;
        let _lock=self.serialize.lock().map_err(|_|RawTxError::InvalidInterface)?;
        let mtu=self.budget.receive_budget().map_err(|e|match e{
            BudgetError::Unavailable=>RawTxError::RouteUnavailable,
            BudgetError::ChangedOrInvalid|BudgetError::Deferred=>RawTxError::RouteStale,
        })?;
        for i in 0..outcome.attempted{
            let mut pfd=PollFd{fd:self.fd.as_raw_fd(),events:POLLIN,revents:0};
            // SAFETY: one live pollfd, timeout zero, owned FD.
            let ready=unsafe{poll(&mut pfd,1,0)};
            if ready<0 {
                let e=errno();
                if e==4{outcome.status=RawReadyStatus::Interrupted;break}
                return Err(RawTxError::Kernel(e))
            }
            if ready==0{
                outcome.status=RawReadyStatus::WouldBlock;break
            }
            if pfd.revents&POLLIN==0{return Err(RawTxError::InvalidPacket)}
            let slot=&mut buffers[i];
            let cap=slot.len().min(mtu);
            // SAFETY: original caller mutable byte slice stays borrowed,
            // bounded copy and MSG_TRUNC original-wire length for rejection.
            let n=unsafe{recvfrom(self.fd.as_raw_fd(),slot.as_mut_ptr().cast(),
                cap,MSG_DONTWAIT|0x20,std::ptr::null_mut(),std::ptr::null_mut())};
            if n<0{
                let e=errno();
                if e==11{outcome.status=RawReadyStatus::WouldBlock;break}
                if e==4{outcome.status=RawReadyStatus::Interrupted;break}
                return Err(RawTxError::Kernel(e))
            }
            let n=n as usize;
            outcome.observed+=1;
            if n>cap{
                outcome.entries[i]=RawReadyEntry::Truncated{wire_len:n,capacity:cap};
                continue
            }
            if n<40{outcome.entries[i]=RawReadyEntry::Rejected;continue}
            let trusted=TrustedRx{
                tuple,persona,mtu,authenticated_options:None};
            let parsed=match parse_data_packet(&slot[..n],trusted){
                Ok(v)=>v,
                Err(_)=>{
                    // The protected handshake has not negotiated SACK.
                    // Reject option-bearing pure ACKs, never reinterpret as DATA.
                    outcome.entries[i]=parse_ack_packet(&slot[..n],trusted,false)
                        .map(|ack|RawReadyEntry::PureAck{ack32:ack.ack32})
                        .unwrap_or(RawReadyEntry::Rejected);
                    continue
                }
            };
            let begin=n-parsed.ciphertext.len();
            let size=parsed.ciphertext.len();
            let seq=parsed.seq32;
            let ack32=parsed.presentation_ack32; // copy before mutating same slab
            slot.copy_within(begin..n,0);
            outcome.entries[i]=RawReadyEntry::Unauthenticated{
                cipher_len:size,seq32:seq,ack32};
        }
        if outcome.observed==MAX_READY_RAW && buffers.len()>MAX_READY_RAW{
            outcome.status=RawReadyStatus::AtCap;
        }
        Ok(outcome)
    }
}

#[cfg(test)]
mod ready_batch_tests{
    use super::*;
    #[test]
    fn r1_m4_pack_raw_0_1_32_33_prefix_uncertain_suffix_and_kernel_error_gate(){
        let list=[
            (RawTxError::Kernel(11),KernelSendSignal::Backpressure,None,TxError::WouldBlock),
            (RawTxError::Kernel(4),KernelSendSignal::Interrupted,Some(2),TxError::IoUncertain),
            (RawTxError::Kernel(90),KernelSendSignal::MtuExceeded,None,TxError::IoFailed),
            (RawTxError::Kernel(19),KernelSendSignal::DeviceUnavailable,None,TxError::IoFailed),
            (RawTxError::Kernel(101),KernelSendSignal::RouteUnavailable,None,TxError::IoFailed),
            (RawTxError::PacketExceedsBudget,KernelSendSignal::PreflightRejected,None,TxError::IoFailed),
            (RawTxError::NoCapacity,KernelSendSignal::PreflightRejected,None,TxError::IoFailed),
            (RawTxError::RouteUnavailable,KernelSendSignal::RouteUnavailable,None,TxError::IoFailed),
            (RawTxError::RouteStale,KernelSendSignal::RouteUnavailable,None,TxError::IoFailed),
            (RawTxError::ShortSend,KernelSendSignal::AmbiguousCompletion,Some(2),TxError::IoUncertain),
            (RawTxError::Stopped,KernelSendSignal::Stopping,None,TxError::Stopping),
        ];
        for (err,signal,uncertain,error) in list{
            let got=raw_batch_failure(2,err);
            assert_eq!(got.outcome.accepted_prefix,2);
            assert_eq!(got.outcome.uncertain_index,uncertain);
            assert_eq!(got.outcome.error,Some(error));
            assert_eq!(got.signal,signal);
        }
        assert_eq!(RawReadyBatch::new(0).status,RawReadyStatus::Empty);
        assert_eq!(RawReadyBatch::new(1).attempted,1);
        assert_eq!(RawReadyBatch::new(32).attempted,32);
        assert_eq!(RawReadyBatch::new(33).attempted,32);
        assert_eq!(RawReadyBatch::new(33).entry(32),None);
    }
    #[test]
    fn linux_raw_rx_receive_buffer_is_bounded_and_kernel_readback_actual(){
        // Use unprivileged ephemeral UDP socket only to test the Linux
        // SOL_SOCKET buffer syscall ABI; never open a live raw interface.
        use std::net::UdpSocket;
        let s=UdpSocket::bind("127.0.0.1:0").unwrap();
        let actual=tune_raw_rx_buffer(s.as_raw_fd()).unwrap();
        assert!(actual>0);
        assert!(actual<=RAW_RX_RCVBUF_EFFECTIVE_CEILING_BYTES);
        // Both kernel reads must reflect the same effective byte count.
        let mut readback:c_int=0;
        let mut n=std::mem::size_of::<c_int>() as u32;
        let rc=unsafe{getsockopt(s.as_raw_fd(),SOL_SOCKET,SO_RCVBUF,
            (&mut readback as *mut c_int).cast(),&mut n)};
        assert_eq!(rc,0);
        assert_eq!(n,4);
        assert_eq!(readback,actual);
        assert_eq!(RAW_RX_RCVBUF_REQUEST_BYTES,4*1024*1024);
    }
    #[test]
    fn linux_raw_rx_buffer_does_not_scale_with_fec_or_flow_count(){
        assert_eq!(RAW_RX_RCVBUF_EFFECTIVE_CEILING_BYTES,2*RAW_RX_RCVBUF_REQUEST_BYTES);
        // Runtime has one bounded fixed request per OS-owned raw RX
        // socket. There is no global rmem sysctl, FEC pool or queue growth.
    }
    #[test]
    fn r1_m4_pack_raw_nonprivileged_no_interface_capture(){
        // Raw bearer requires explicit interface and CAP_NET_RAW; no
        // physical-interface/ambient test captures or Go admission occur.
        assert!(matches!(ScopedRawIpv4Rx::open("../eth0",1,1),
            Err(RawTxError::InvalidInterface)));
        assert!(matches!(ScopedRawIpv4Tx::open("lo",0,1),
            Err(RawTxError::InvalidInterface)));
    }
}

#[cfg(test)]
mod raw_tuple_tests{
    use super::*;
    #[test]
    fn r1_m4_pack_raw_malformed_ipv4_tuple_fails_before_mtu_or_fd(){
        let t=Ipv4Tuple{src_ip:&[127,0,0,1],dst_ip:&[127,0,0,1],
            src_port:1,dst_port:2};
        assert_eq!(checked_destination(t),Ok(Ipv4Addr::LOCALHOST));
        for dst in [&[127u8,0,0][..],&[127,0,0,1,1][..],&[][..]]{
            assert_eq!(checked_destination(Ipv4Tuple{dst_ip:dst,..t}),
                Err(RawTxError::InvalidPacket));
        }
        assert_eq!(checked_destination(Ipv4Tuple{src_port:0,..t}),
            Err(RawTxError::InvalidPacket));
        assert_eq!(checked_destination(Ipv4Tuple{src_ip:&[127,0,0],..t}),
            Err(RawTxError::InvalidPacket));
    }
}


/// The original owner must hand a live, explicitly scoped raw FD to this
/// driver after authenticated Go->Rust provenance installation. This uses
/// ONE actual Linux sendmmsg syscall, not 32 sendto loops. No ciphertext
/// copy: each message has header iovec + exactly the original frozen record
/// slice. STOP holds the single batch guard across all header preparations
/// and the synchronous kernel syscall. A positive return is NOT peer ACK.
impl ScopedRawIpv4Tx {
    pub fn send_kernel_multimsg<H:FrozenRecordHandle>(
        &self,generation:u32,records:&[H],tuple:Ipv4Tuple<'_>,
        presentations:&[Presentation],
    )->KernelSendReport {
        if generation!=self.generation {
            return raw_batch_failure(0,RawTxError::InvalidScope)
        }
        if self.is_stopping() {
            return raw_batch_failure(0,RawTxError::Stopped)
        }
        let limit=records.len().min(MAX_READY_RAW);
        if presentations.len()<limit {
            return raw_batch_failure(0,RawTxError::InvalidPacket)
        }
        let _loan=match self.borrow.try_enter_ready(){
            Ok(g)=>g,
            Err(BorrowError::Stopping)=>return raw_batch_failure(0,RawTxError::Stopped),
            Err(BorrowError::TooManyLoans)=>return raw_batch_failure(0,RawTxError::NoCapacity)
        };
        let _lock=match self.serialize.lock(){
            Ok(g)=>g,
            Err(_)=>return raw_batch_failure(0,RawTxError::InvalidInterface)
        };
        if limit==0{
            return KernelSendReport{outcome:TxBatchOutcome::copied_all(0),
                signal:KernelSendSignal::None}
        }
        let dest=match checked_destination(tuple){
            Ok(d)=>d,
            Err(e)=>return raw_batch_failure(0,e)
        };
        let mtu=match self.budget.send_budget(dest){
            Ok(m)=>m,
            Err(BudgetError::Unavailable)=>
                return raw_batch_failure(0,RawTxError::RouteUnavailable),
            Err(_)=>return raw_batch_failure(0,RawTxError::RouteStale)
        };
        let mut headers=[[0u8;80];MAX_READY_RAW];
        let mut sizes=[0usize;MAX_READY_RAW];
        // Validate ALL submitted frames before first possible kernel send.
        // The 33rd unsent record is not read, touched or resealed.
        for i in 0..limit{
            sizes[i]=match ipv4_tcp::build_scatter_header(
                tuple,presentations[i],&records[i],None,mtu,&mut headers[i]){
                Ok(n)=>n,
                Err(ipv4_tcp::PacketError::MtuExceeded{..})=>
                    return raw_batch_failure(0,RawTxError::PacketExceedsBudget),
                Err(_)=>return raw_batch_failure(0,RawTxError::InvalidPacket)
            };
        }
        let result=linux_batch::submit_scatter_fd(
            self.fd.as_raw_fd(),std::net::SocketAddrV4::new(dest,0),
            &headers,&sizes,records);
        if result.signal.invalidates_path(){self.budget.invalidate()}
        result
    }
}
/// Kernel native raw recvmmsg into original owner-borrowed M1 packet slots.
/// A completed raw packet is NEVER authenticated just by kernel acceptance:
/// strict trusted tuple/checksum precedes engine AEAD/PN checks. The owner
/// holds a BorrowFence across syscall AND parser, so STOP cannot free or
/// rotate borrowed memory until both operations have exited.
impl ScopedRawIpv4Rx {
    pub fn receive_kernel_multimsg(&self,generation:u32,
        buffers:&mut [&mut [u8]],tuple:Ipv4Tuple<'_>,persona:PacketPersona
    )->Result<RawReadyBatch,RawTxError>{
        if generation!=self.generation{return Err(RawTxError::InvalidScope)}
        if self.is_stopping(){return Err(RawTxError::Stopped)}
        let mut out=RawReadyBatch::new(buffers.len());
        if out.attempted==0{return Ok(out)}
        if buffers[..out.attempted].iter().any(|b|b.len()<40){
            return Err(RawTxError::InvalidPacket)
        }
        checked_destination(tuple)?;
        let _loan=self.borrow.try_enter_ready().map_err(|e|match e {
            BorrowError::Stopping=>RawTxError::Stopped,
            BorrowError::TooManyLoans=>RawTxError::NoCapacity
        })?;
        let _lock=self.serialize.lock().map_err(|_|RawTxError::InvalidInterface)?;
        let mtu=self.budget.receive_budget().map_err(|e|match e{
            BudgetError::Unavailable=>RawTxError::RouteUnavailable,
            BudgetError::ChangedOrInvalid|BudgetError::Deferred=>RawTxError::RouteStale,
        })?;
        let native=linux_rx_batch::receive_fd(
            self.fd.as_raw_fd(),buffers,&self.borrow);
        out.observed=native.received;
        out.status=match native.status{
            RxStatus::Empty=>RawReadyStatus::Empty,
            RxStatus::Ready=>RawReadyStatus::Ready,
            RxStatus::AtCap=>RawReadyStatus::AtCap,
            RxStatus::WouldBlock=>RawReadyStatus::WouldBlock,
            RxStatus::Interrupted=>RawReadyStatus::Interrupted,
            RxStatus::Stopping=>return Err(RawTxError::Stopped),
            RxStatus::InvalidBuffers=>return Err(RawTxError::InvalidPacket),
            RxStatus::IoUncertain=>RawReadyStatus::IoUncertain,
        };
        for i in 0..native.received{
            out.entries[i]=match native.entry(i){
                Some(RxEntry::Truncated{wire_len,capacity})=>
                    RawReadyEntry::Truncated{wire_len,capacity},
                Some(RxEntry::Complete{len})=>{
                    let slot=&mut buffers[i];
                    let parsed=if len<=mtu{
                        parse_data_packet(&slot[..len],TrustedRx{
                            tuple,persona,mtu,authenticated_options:None
                        })
                    }else{out.entries[i]=RawReadyEntry::Rejected;continue};
                    match parsed{
                        Ok(p)=>{
                            let begin=len-p.ciphertext.len();
                            let n=p.ciphertext.len();let seq32=p.seq32;
                            let ack32=p.presentation_ack32;
                            slot.copy_within(begin..len,0);
                            RawReadyEntry::Unauthenticated{
                                cipher_len:n,seq32,ack32}
                        },
                        Err(reason)=>{
                            // Pure carrier ACK is a scoped optional cache hint,
                            // NOT an authenticated business or quality receipt.
                            if let Ok(ack)=parse_ack_packet(&slot[..len],TrustedRx{
                                tuple,persona,mtu,authenticated_options:None
                            },false){
                                out.entries[i]=RawReadyEntry::PureAck{ack32:ack.ack32};
                                continue
                            }
                            // TEST DIAGNOSTIC ONLY: bounded numeric/header-only
                            // evidence to distinguish W168 exact tuple/persona
                            // failures. Does not admit, authenticate, decrypt,
                            // copy, or touch accepted packet ownership.
                            static ENABLED:std::sync::OnceLock<bool>=std::sync::OnceLock::new();
                            static COUNT:std::sync::atomic::AtomicUsize=
                                std::sync::atomic::AtomicUsize::new(0);
                            if *ENABLED.get_or_init(||std::env::var("WBD_WL_RX_TUPLE_DIAG")
                                .ok().as_deref()==Some("1")) &&
                                COUNT.fetch_add(1,std::sync::atomic::Ordering::Relaxed)<12 {
                                let ihl=usize::from(slot[0]&0x0f)*4;
                                let observed=if len>=ihl+4 && ihl>=20 {
                                    format!("ip={:?}->{:?} ports={}->{} flags={:#x} ihl={} len={}",
                                        &slot[12..16],&slot[16..20],
                                        u16::from_be_bytes([slot[ihl],slot[ihl+1]]),
                                        u16::from_be_bytes([slot[ihl+2],slot[ihl+3]]),
                                        slot.get(ihl+13).copied().unwrap_or(0),ihl,len)
                                }else{format!("malformed_header ihl={} len={}",ihl,len)};
                                eprintln!("WBD_WL_RX_TUPLE_REJECT reason={reason:?} expected={tuple:?} observed={observed}");
                            }
                            RawReadyEntry::Rejected
                        },
                    }
                }
                _=>RawReadyEntry::Unused,
            };
        }
        Ok(out)
    }
}
#[cfg(test)]
mod leased_multimsg_contract_tests{
    use super::*;
    #[test]
    fn r1_m4_013_privilege_is_not_inferred_from_new_raw_signatures(){
        assert!(matches!(ScopedRawIpv4Tx::open("lo",0,12),
            Err(RawTxError::InvalidInterface)));
        assert!(matches!(ScopedRawIpv4Rx::open("lo",0,12),
            Err(RawTxError::InvalidInterface)));
        // Entry indexes prove the 33rd buffer cannot be observed by the
        // 32-slot syscall contract before a separate caller drain.
        assert_eq!(RawReadyBatch::new(0).attempted,0);
        assert_eq!(RawReadyBatch::new(33).attempted,32);
        assert_eq!(RawReadyBatch::new(33).entry(32),None);
    }
}
