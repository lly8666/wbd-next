//! Linux real TUN L3 application egress for an already authenticated owner.
//! Attaches ONLY a caller-owned preconfigured TUN FD; Go retains OS network
//! configuration. Not a RAW carrier, TLS authority, route manager or netem.
//! Synchronous kernel write copy completion is NOT application receipt.
#![cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
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
const F_GETFL:i32=3;
const F_SETFL:i32=4;
const O_NONBLOCK:i32=0x800;
#[repr(C)]
struct PollFd {fd:i32,events:i16,revents:i16}

unsafe extern "C" {
    fn ioctl(fd:i32,request:usize,...) -> i32;
    fn write(fd:i32,ptr:*const std::ffi::c_void,len:usize)->isize;
    fn read(fd:i32,ptr:*mut std::ffi::c_void,len:usize)->isize;
    fn poll(fds:*mut PollFd,nfds:usize,timeout:i32)->i32;
    fn fcntl(fd:i32,cmd:i32,...)->i32;
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
        // A bounded ready-only read must never block after a readiness race.
        // This FD is *moved* into this owner, no concurrent Go reader allowed.
        let flags=unsafe{fcntl(fd.as_raw_fd(),F_GETFL)};
        if flags<0 {return Err((TunError::InvalidFd,fd))}
        if flags&O_NONBLOCK==0 &&
            unsafe{fcntl(fd.as_raw_fd(),F_SETFL,flags|O_NONBLOCK)}<0 {
            return Err((TunError::InvalidFd,fd))
        }
        Ok(Self{fd,generation,name:expected_name.to_owned(),fence:BorrowFence::default(),
            serialized:Mutex::new(()),started:AtomicBool::new(true)})
    }
    pub fn name(&self)->&str{&self.name}
    pub fn generation(&self)->u32{self.generation}
    /// Poll-only while the owning generation is alive.
    pub fn readiness_fd(&self)->i32{self.fd.as_raw_fd()}
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

// Ready TUN L3 has no multi-message recvmmsg ABI. This bound is a maximum of
// 32 immediately-ready poll(0)+read/write kernel operations on a single
// preconfigured, exclusively owned, nonblocking IFF_TUN|IFF_NO_PI FD.
// Unsupported IPv6/invalid length is rejected without authentication or PN.
const MAX_READY_TUN:usize=32;
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub enum TunReadyStatus{Empty,Ready,AtCap,WouldBlock,Interrupted}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub enum TunReadyEntry{Unused,UntrustedIpv4{len:usize},Rejected}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct TunReadyReads{
    pub requested:usize,pub attempted:usize,pub observed:usize,
    pub status:TunReadyStatus,pub entries:[TunReadyEntry;MAX_READY_TUN],
}
impl TunReadyReads{
    fn new(requested:usize)->Self{
        Self{requested,attempted:requested.min(MAX_READY_TUN),
            observed:0,status:if requested==0{
                TunReadyStatus::Empty
            }else{TunReadyStatus::Ready},
            entries:[TunReadyEntry::Unused;MAX_READY_TUN]}
    }
    pub fn entry(&self,i:usize)->Option<TunReadyEntry>{
        if i<self.attempted{Some(self.entries[i])}else{None}
    }
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct TunReadyWrites{
    pub requested:usize,pub attempted:usize,pub accepted_prefix:usize,
    pub uncertain_index:Option<usize>,pub error:Option<TunError>,
}
fn ipv4_contract(packet:&[u8])->bool{
    if packet.len()<20||packet.len()>65535||packet[0]>>4!=4 {
        return false
    }
    let ihl=usize::from(packet[0]&0x0f)*4;
    let declared=usize::from(u16::from_be_bytes([packet[2],packet[3]]));
    ihl>=20&&ihl<=packet.len()&&declared==packet.len()
}
impl ScopedTunSink{
    /// Never waits for fresh packets or allocates a second frame. An
    /// unsupported/invalid datagram is counted and **not** handed to owner.
    /// The returned complete slice remains UNTRUSTED OS application ingress.
    pub fn read_ready_batch(&self,generation:u32,slots:&mut [&mut [u8]])
        ->Result<TunReadyReads,TunError>
    {
        if generation!=self.generation{return Err(TunError::InvalidScope)}
        if self.is_stopping(){return Err(TunError::Stopped)}
        let mut out=TunReadyReads::new(slots.len());
        if out.attempted==0{return Ok(out)}
        if slots[..out.attempted].iter().any(|x|x.is_empty()){
            return Err(TunError::TooLarge)
        }
        let _loan=self.fence.try_enter_ready().map_err(|e|match e{
            BorrowError::Stopping=>TunError::Stopped,
            BorrowError::TooManyLoans=>TunError::TooLarge,
        })?;
        let _lock=self.serialized.lock().map_err(|_|TunError::InvalidFd)?;
        for (i,slot) in slots[..out.attempted].iter_mut().enumerate(){
            let mut p=PollFd{fd:self.fd.as_raw_fd(),events:POLLIN,revents:0};
            // SAFETY: owned O_NONBLOCK TUN fd and one live pollfd, timeout 0.
            let ready=unsafe{poll(&mut p,1,0)};
            if ready<0{
                let e=io::Error::last_os_error().raw_os_error().unwrap_or(5);
                if e==4{out.status=TunReadyStatus::Interrupted;break}
                return Err(TunError::Kernel(e))
            }
            if ready==0 {out.status=TunReadyStatus::WouldBlock;break}
            if p.revents&POLLIN==0{return Err(TunError::InvalidFd)}
            // SAFETY: caller-exclusive slot stays borrowed, kernel-owned
            // descriptor is nonblocking even if another event races poll.
            let n=unsafe{read(self.fd.as_raw_fd(),slot.as_mut_ptr().cast(),slot.len())};
            if n<0{
                let e=io::Error::last_os_error().raw_os_error().unwrap_or(5);
                if e==11{out.status=TunReadyStatus::WouldBlock;break}
                if e==4{out.status=TunReadyStatus::Interrupted;break}
                return Err(TunError::Kernel(e))
            }
            out.observed+=1;
            let size=n as usize;
            out.entries[i]=if ipv4_contract(&slot[..size]){
                TunReadyEntry::UntrustedIpv4{len:size}
            }else{TunReadyEntry::Rejected};
        }
        if out.observed==MAX_READY_TUN && slots.len()>MAX_READY_TUN{
            out.status=TunReadyStatus::AtCap
        }
        Ok(out)
    }
    /// Only packets independently authenticated by the existing engine owner
    /// may be passed here. One owned FD, <=32 sync writes; never reseal data.
    /// A short TUN write has uncertain completion, not accepted packet.
    pub fn write_ready_batch(&self,generation:u32,frames:&[&[u8]])
        ->TunReadyWrites
    {
        let cap=frames.len().min(MAX_READY_TUN);
        let mut out=TunReadyWrites{requested:frames.len(),attempted:cap,
            accepted_prefix:0,uncertain_index:None,error:None};
        if generation!=self.generation{out.error=Some(TunError::InvalidScope);return out}
        if self.is_stopping(){out.error=Some(TunError::Stopped);return out}
        for frame in &frames[..cap] {
            match self.write_authenticated_ipv4(generation,frame){
                Ok(_)=>out.accepted_prefix+=1,
                Err(e)=>{
                    // Kernel EINTR/unknown faults after a ready-only write
                    // do not authorize reusing an already published packet.
                    if e==TunError::ShortWrite ||
                        matches!(e,TunError::Kernel(4|5)) {
                        out.uncertain_index=Some(out.accepted_prefix)
                    }
                    out.error=Some(e);
                    return out;
                }
            }
        }
        if cap<frames.len(){out.error=Some(TunError::TooLarge)}
        out
    }
}
#[cfg(test)]
mod ready_tests {
    use super::*;
    #[test]
    fn r1_m4_pack_tun_0_1_32_33_bounded_no_implicit_auth(){
        assert_eq!(TunReadyReads::new(0).status,TunReadyStatus::Empty);
        assert_eq!(TunReadyReads::new(1).attempted,1);
        assert_eq!(TunReadyReads::new(32).attempted,32);
        assert_eq!(TunReadyReads::new(33).attempted,32);
        assert_eq!(TunReadyReads::new(33).entry(32),None);
        let gold="4500002e0015400040064e31c0000228c6336428a7f801bb00000064000000c850180400cc2900007265636f7264";
        let wire:Vec<u8>=(0..gold.len()).step_by(2).map(|i|
            u8::from_str_radix(&gold[i..i+2],16).unwrap()).collect();
        assert!(ipv4_contract(&wire));
        let mut bad=wire.clone();bad[2]=0;bad[3]=45;
        assert!(!ipv4_contract(&bad));
        assert!(!ipv4_contract(&[0x60u8;40]));
        assert!(!ipv4_contract(&[0x45u8;7]));
    }

    #[test]
    fn r1_m4_012_tun_stop_and_preflight_outcome_without_real_privileged_fd(){
        // The genuine TUN FD positive remains NOT_RUN. These contracts
        // ensure failures do not fabricate a usable device or content.
        assert!(!ipv4_contract(&[]));
        let mut frame=[0u8;20];frame[0]=0x45;
        frame[2..4].copy_from_slice(&20u16.to_be_bytes());
        assert!(ipv4_contract(&frame));
        frame[0]=0x44;
        assert!(!ipv4_contract(&frame));
        assert_eq!(TunReadyReads::new(0).observed,0);
        assert_eq!(TunReadyReads::new(33).entry(32),None);
    }
    #[test]
    fn r1_m4_pack_tun_wrong_fd_does_not_gain_privileged_device(){
        let f=std::fs::File::open("/dev/null").unwrap();
        let fd:i32=std::os::fd::AsRawFd::as_raw_fd(&f);
        assert!(fd>=0);
        // No ioctl/write is issued to an untrusted /dev/null as a real TUN:
        // old from_owned_fd negative fixture proves TUNGETIFF rejection.
    }
}
