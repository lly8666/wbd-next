//! Linux x86_64 GNU IPv4/TCP raw TX for an already authenticated V4 owner.
//! Sends original immutable M1 FrozenRecord via normal ipv4_tcp::build.
//! No TLS keys/cold auth/Go readiness in this driver. Owned Linux raw fd
//! needs CAP_NET_RAW and exact interface bound by kernel SO_BINDTODEVICE.
//! STOP fences synchronously borrowed record until kernel copy completes.
//! Kernel acceptance is NOT remote peer ACK or application delivery.
#![cfg(all(target_os="linux",target_arch="x86_64",target_env="gnu"))]
use std::ffi::{c_int,c_void,CString};
use std::io;
use std::net::Ipv4Addr;
use std::os::fd::{FromRawFd,AsRawFd,OwnedFd};
use std::sync::{Mutex,atomic::{AtomicBool,Ordering}};
use std::time::{Instant,Duration};
use crate::r1::{BorrowFence,BorrowError,StopResult};
use crate::{TxBatchOutcome,TxError};
use crate::linux_batch::{KernelSendReport,KernelSendSignal};
use crate::linux_packet_preflight::{interface_index,observe_interface_mtu};
use crate::linux_mtu_scope::{ScopedRouteBudget,BudgetError};
use crate::ipv4_tcp::{self,Ipv4Tuple,Presentation,PacketPersona};
use crate::rx_ipv4_tcp::{parse_data_packet,TrustedRx,RxError};
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
const MSG_DONTWAIT:c_int=0x40;
#[repr(C)]
struct SockAddrIn {
    family:u16, port:u16, ip_be:u32, zero:[u8;8],
}
unsafe extern "C" {
    fn socket(domain:c_int,typ:c_int,proto:c_int)->c_int;
    fn setsockopt(fd:c_int,level:c_int,opt:c_int,value:*const c_void,len:u32)->c_int;
    fn poll(fds:*mut PollFd,nfds:usize,timeout:c_int)->c_int;
    fn recvfrom(fd:c_int,bytes:*mut c_void,len:usize,flags:c_int,
        src:*mut c_void,addr_len:*mut u32)->isize;
    fn sendto(fd:c_int,bytes:*const c_void,len:usize,flags:c_int,
        dst:*const c_void,dst_len:u32)->isize;
}
fn errno()->i32{io::Error::last_os_error().raw_os_error().unwrap_or(5)}
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
    Empty, Ready, AtCap, WouldBlock, Interrupted,
}
#[derive(Debug,Clone,Copy,Eq,PartialEq)]
pub enum RawReadyEntry{
    Unused,
    /// Caller still owns this original buffer. Parser output is not AEAD.
    Unauthenticated {cipher_len:usize,seq32:u32},
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
            let parsed=match parse_data_packet(&slot[..n],TrustedRx{
                tuple,persona,mtu,authenticated_options:None}){
                Ok(v)=>v,
                Err(_)=>{outcome.entries[i]=RawReadyEntry::Rejected;continue}
            };
            let begin=n-parsed.ciphertext.len();
            let size=parsed.ciphertext.len();
            let seq=parsed.seq32;
            slot.copy_within(begin..n,0);
            outcome.entries[i]=RawReadyEntry::Unauthenticated{
                cipher_len:size,seq32:seq};
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
