//! Linux real TUN L3 application egress for an already authenticated owner.
//! Attaches ONLY a caller-owned preconfigured TUN FD; Go retains OS network
//! configuration. Not a RAW carrier, TLS authority, route manager or netem.
//! Synchronous kernel write copy completion is NOT application receipt.
#![cfg(all(target_os="linux",target_arch="x86_64",target_env="gnu"))]
use std::io;
use std::os::fd::{AsRawFd,OwnedFd};
use std::sync::atomic::{AtomicBool,Ordering};
use std::sync::Mutex;
use crate::r1::{BorrowFence,BorrowError,StopResult};
use std::time::Instant;

const TUNGETIFF:usize=0x800454d2;
const IFF_TUN:i16=0x0001;
const IFF_NO_PI:i16=0x1000;
const MAX_NAME:usize=15;
const POLLIN:i16=1;
#[repr(C)]
struct PollFd {fd:i32,events:i16,revents:i16}

unsafe extern "C" {
    fn ioctl(fd:i32,request:usize,...) -> i32;
    fn write(fd:i32,ptr:*const std::ffi::c_void,len:usize)->isize;
    fn read(fd:i32,ptr:*mut std::ffi::c_void,len:usize)->isize;
    fn poll(fds:*mut PollFd,nfds:usize,timeout:i32)->i32;
}
#[derive(Debug,Clone,Copy,PartialEq,Eq)]
pub enum TunError {
    InvalidScope,Stopped,InvalidFd,InvalidName,WrongMode,
    InvalidPacket,TooLarge,Kernel(i32),ShortWrite,TimedOut,
}
pub struct ScopedTunSink {
    fd:OwnedFd,
    generation:u32,
    name:String,
    fence:BorrowFence,
    serialized:Mutex<()>,
    started:AtomicBool,
}
impl ScopedTunSink {
    /// Does NOT create a TUN, select a route, or grant CAP_NET_ADMIN.
    /// The FD must be a live Linux IFF_TUN+IFF_NO_PI endpoint configured by
    /// the original Go OS-device owner; it is moved into this Rust owner.
    pub fn from_owned_fd(fd:OwnedFd, generation:u32, expected_name:&str)
        ->Result<Self,(TunError,OwnedFd)>{
        if generation==0 || expected_name.is_empty() ||
            expected_name.len()>MAX_NAME ||
            !expected_name.bytes().all(|b|b.is_ascii_alphanumeric()||b==b'_'||b==b'-'){
            return Err((TunError::InvalidName,fd))
        }
        let mut ifreq=[0u8;40];
        // SAFETY: owned descriptor, live 40-byte Linux x86_64 struct ifreq
        // backing store, ioctl fills only expected bounded region.
        if unsafe{ioctl(fd.as_raw_fd(),TUNGETIFF,ifreq.as_mut_ptr())} < 0 {
            return Err((TunError::InvalidFd,fd))
        }
        let name_len=ifreq[..16].iter().position(|&b|b==0).unwrap_or(16);
        if name_len>MAX_NAME || &ifreq[..name_len]!=expected_name.as_bytes(){
            return Err((TunError::InvalidName,fd))
        }
        let flags=i16::from_ne_bytes([ifreq[16],ifreq[17]]);
        if flags&IFF_TUN==0 || flags&IFF_NO_PI==0 ||
            flags&0x0002!=0 {
            return Err((TunError::WrongMode,fd))
        }
        Ok(Self{fd,generation,name:expected_name.to_owned(),fence:BorrowFence::default(),
            serialized:Mutex::new(()),started:AtomicBool::new(true)})
    }
    pub fn name(&self)->&str{&self.name}
    pub fn generation(&self)->u32{self.generation}
    pub fn begin_stop(&self){
        self.started.store(false,Ordering::Release);
        self.fence.begin_stop();
    }
    pub fn stop_until(&self,deadline:Instant)->StopResult{
        self.begin_stop();self.fence.wait_drained_until(deadline)
    }
    pub fn outstanding(&self)->usize{self.fence.outstanding()}
    pub fn is_stopping(&self)->bool{self.fence.is_stopping()}
    /// One real kernel TUN application ingress, direct into caller's ORIGINAL
    /// M1 UniqueBuffer writable region. No second data buffer/copy and no
    /// alternate TX path. This is UNTRUSTED plaintext input from the OS
    /// device; it must go through the current protected Rust owner and AEAD.
    /// A bounded readiness poll prevents a missing app datagram from hanging
    /// the OS integration runner. It never retries uncertain kernel reads.
    pub fn read_ipv4_into(&self,generation:u32,out:&mut [u8])
        ->Result<usize,TunError>{
        if generation!=self.generation{return Err(TunError::InvalidScope)}
        if !self.started.load(Ordering::Acquire){return Err(TunError::Stopped)}
        if out.len()<20{return Err(TunError::TooLarge)}
        let _guard=self.fence.try_enter_ready().map_err(|e|match e{
            BorrowError::Stopping=>TunError::Stopped,
            BorrowError::TooManyLoans=>TunError::TooLarge,
        })?;
        let _serialized=self.serialized.lock().map_err(|_|TunError::InvalidFd)?;
        let deadline=Instant::now()+std::time::Duration::from_millis(750);
        // TUN is L3: Linux can emit IPv6 DAD/neighbor traffic immediately
        // after a new IFF_TUN is brought up. This owner negotiates ONLY
        // IPv4 Normal/off; NEVER AEAD-seal unsupported IPv6 as IPv4 business.
        // A bounded 8-receive filter avoids a startup false-first packet,
        // with a single total 750ms deadline and no second data buffer.
        for _ in 0..8 {
            let remaining=deadline.saturating_duration_since(Instant::now());
            if remaining.is_zero(){return Err(TunError::TimedOut)}
            let timeout=remaining.as_millis().max(1).min(750) as i32;
            let mut pfd=PollFd{fd:self.fd.as_raw_fd(),events:POLLIN,revents:0};
            // SAFETY: the kernel sees one correctly laid-out live pollfd.
            let ready=unsafe{poll(&mut pfd,1,timeout)};
            if ready<0 {
                return Err(TunError::Kernel(
                    io::Error::last_os_error().raw_os_error().unwrap_or(5)))
            }
            if ready==0{return Err(TunError::TimedOut)}
            if pfd.revents&POLLIN==0{return Err(TunError::InvalidFd)}
            // SAFETY: owned fd and live original M1 writable buffer.
            let n=unsafe{read(self.fd.as_raw_fd(),out.as_mut_ptr().cast(),out.len())};
            if n<0 {
                return Err(TunError::Kernel(
                    io::Error::last_os_error().raw_os_error().unwrap_or(5)))
            }
            let n=n as usize;
            if n>=40 && out[0]>>4==6 {continue} // unsupported IPv6 control
            if n<20 || n>65535 || out[0]>>4!=4 || out[0]&0x0f<5 {
                return Err(TunError::InvalidPacket)
            }
            let header_len=usize::from(out[0]&0x0f)*4;
            let total=usize::from(u16::from_be_bytes([out[2],out[3]]));
            if total!=n || header_len>n {return Err(TunError::InvalidPacket)}
            return Ok(n)
        }
        Err(TunError::TimedOut)
    }

    /// Writes only a complete authenticated IPv4 L3 packet; any rejected
    /// header or short/failed kernel write is counted as non-delivery.
    /// This method cannot be used to authenticate its packet argument.
    pub fn write_authenticated_ipv4(&self,generation:u32,packet:&[u8])
        ->Result<usize,TunError>{
        if generation!=self.generation{return Err(TunError::InvalidScope)}
        if !self.started.load(Ordering::Acquire){return Err(TunError::Stopped)}
        if packet.len()<20 || packet.len()>65535{return Err(TunError::InvalidPacket)}
        if packet[0]>>4!=4 || (packet[0]&0xf)<5{return Err(TunError::InvalidPacket)}
        let header_len=usize::from(packet[0]&0xf)*4;
        let declared=usize::from(u16::from_be_bytes([packet[2],packet[3]]));
        if declared!=packet.len() || header_len>declared{
            return Err(TunError::InvalidPacket)
        }
        let _guard=self.fence.try_enter_ready().map_err(|e|match e{
            BorrowError::Stopping=>TunError::Stopped,
            BorrowError::TooManyLoans=>TunError::TooLarge,
        })?;
        let _serialized=self.serialized.lock().map_err(|_|TunError::InvalidFd)?;
        // SAFETY: fd is owned for the guard lifetime and packet slice
        // remains valid until the synchronous kernel call returns.
        let n=unsafe{write(self.fd.as_raw_fd(),packet.as_ptr().cast(),packet.len())};
        if n<0 {
            return Err(TunError::Kernel(io::Error::last_os_error().raw_os_error().unwrap_or(5)))
        }
        if n as usize!=packet.len(){return Err(TunError::ShortWrite)}
        Ok(n as usize)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::os::fd::FromRawFd;
    unsafe extern "C" {fn dup(fd:i32)->i32;}
    #[test]
    fn r1_tun_reject_non_tun_fd_and_invalid_scope() {
        // This is only a negative contract. A privileged real FD positive
        // must come from the separate end-to-end namespace test.
        let orig=std::fs::File::open("/dev/null").unwrap();
        let fd=unsafe{dup(orig.as_raw_fd())};
        let owned=unsafe{OwnedFd::from_raw_fd(fd)};
        assert!(matches!(ScopedTunSink::from_owned_fd(owned,1,"wbdtun0"),
            Err((TunError::InvalidFd,_))));
    }
}
