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
use std::time::Instant;
use crate::r1::{BorrowFence,BorrowError,StopResult};
use crate::linux_packet_preflight::{interface_index,observe_interface_mtu};
use crate::ipv4_tcp::{self,Ipv4Tuple,Presentation};
use wbd_types::buffer_contract::FrozenRecordHandle;

const AF_INET:c_int=2;
const SOCK_RAW:c_int=3;
const SOCK_NONBLOCK:c_int=0x800;
const SOCK_CLOEXEC:c_int=0x80000;
const IPPROTO_RAW:c_int=255;
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
    fn sendto(fd:c_int,bytes:*const c_void,len:usize,flags:c_int,
        dst:*const c_void,dst_len:u32)->isize;
}
fn errno()->i32{io::Error::last_os_error().raw_os_error().unwrap_or(5)}
#[derive(Debug,Clone,Copy,Eq,PartialEq)]
pub enum RawTxError {
    InvalidScope,Stopped,InvalidInterface,Kernel(i32),InvalidPacket,
    BoundedMtu,ShortSend,UnsupportedOptions,
}
pub struct ScopedRawIpv4Tx {
    fd:OwnedFd,
    ifindex:u32,
    ifname:String,
    generation:u32,
    mtu:usize,
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
        Ok(Self{
            fd,ifindex:actual,ifname:ifname.to_owned(),generation,
            mtu:observed.kernel_mtu as usize,stopped:AtomicBool::new(false),
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
            BorrowError::TooManyLoans=>RawTxError::BoundedMtu,
        })?;
        let _lock=self.serialize.lock().map_err(|_|RawTxError::InvalidInterface)?;
        let fresh=observe_interface_mtu(
            // Validated and fixed interface is retained below to prevent
            // link MTU/ifindex changes from widening a scoped packet.
            &self.ifname,self.ifindex
        ).map_err(|_|RawTxError::InvalidInterface)?;
        if fresh.kernel_mtu as usize != self.mtu {
            return Err(RawTxError::BoundedMtu)
        }
        let mut scratch=[0u8;2048];
        let packet=ipv4_tcp::build(tuple,presentation,record,None,
            self.mtu.min(scratch.len()),&mut scratch)
            .map_err(|_|RawTxError::InvalidPacket)?;
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
        if n<0{return Err(RawTxError::Kernel(errno()))}
        if n as usize!=packet.len(){return Err(RawTxError::ShortSend)}
        Ok(n as usize)
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
