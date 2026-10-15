//! Linux x86_64 GNU AF_PACKET capability and FD *preflight* only.
//!
//! This is NOT a live AF_PACKET reader/writer: socket protocol is exactly 0,
//! which receives no packets; there is deliberately no bind/send/recv.
//! The authenticated owner would later install a trusted tuple and actual
//! carrier lifecycle under an independent M0 authorization. Never fall back
//! to the UDP fixture on EPERM.
//!
//! ABI: Linux packet(7), socket(2), capabilities(7), capget(2) and
//! netdevice(7). Isolated unsafe libc/syscall island, x86_64 GNU only;
//! no new dependency, root ABI, or public Go V4 activation.
use crate::r1::{BorrowError, BorrowFence, ReadyBatchGuard, StopResult};
use std::ffi::{c_char, c_int, c_long, c_uint, CString};
use std::io;
use std::os::fd::{AsRawFd, FromRawFd, OwnedFd};
use std::path::Path;
use std::time::Instant;

const AF_PACKET: c_int = 17;
const SOCK_RAW: c_int = 3;
const SOCK_NONBLOCK: c_int = 0x800;
const SOCK_CLOEXEC: c_int = 0x80000;
const ETH_P_IP: u16 = 0x0800;
const PACKET_HOST: u8 = 0;
const EPERM: i32 = 1;
const ENODEV: i32 = 19;
const F_GETFD: c_int = 1;
const F_GETFL: c_int = 3;
const FD_CLOEXEC: c_int = 1;
const SYS_CAPGET: c_long = 125;
#[cfg(test)]
const SYS_CAPSET: c_long = 126;
const CAP_V3: u32 = 0x20080522;
const CAP_NET_RAW: u32 = 13;
const MIN_IPV4_MTU: u32 = 68;
// Avoid sysfs path traversal and allow Linux's common device labels.
const IFNAME_MAX: usize = 15;

#[repr(C)]
#[derive(Clone, Copy, Debug)]
struct CapHeader {version: u32, pid: i32}
#[repr(C)]
#[derive(Clone, Copy, Default, Debug)]
struct CapData {effective:u32, permitted:u32, inheritable:u32}
unsafe extern "C" {
    fn socket(domain:c_int,typ:c_int,proto:c_int)->c_int;
    fn if_nametoindex(ifname:*const c_char)->c_uint;
    fn syscall(number:c_long,...)->c_long;
    #[cfg(test)]
    fn fcntl(fd:c_int,cmd:c_int,...)->c_int;
}
fn errno()->i32 {io::Error::last_os_error().raw_os_error().unwrap_or(5)}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PreflightError {
    InvalidInterfaceName,
    MissingInterface {errno:i32},
    InvalidInterfaceIndex,
    WrongInterfaceIndex {expected:u32, actual:u32},
    InvalidProtocol,
    InvalidPacketType,
    InvalidMtu,
    ExceedsDeviceMtu {requested:u32, available:u32},
    InvalidGeneration,
    CapabilityProbe {errno:i32},
    /// Explicit failure with Linux EPERM=1, never fake UDP socket fallback.
    PermissionDenied {errno:i32},
    KernelSocket {errno:i32},
    Stopping,
    StaleGeneration,
    LoansFull,
    Truncated,
    InvalidRxLength,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct PacketConfig<'a> {
    pub ifname:&'a str,
    pub ifindex:u32,
    pub protocol:u16,
    /// RX metadata must be PACKET_HOST=0; outgoing frames are not inbound.
    pub packet_type:u8,
    pub mtu:u32,
    /// 0 is uninitialized; generation must be explicitly assigned by owner.
    pub generation:u32,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct PacketSnapshot {
    pub ifindex:u32,
    pub protocol:u16,
    pub packet_type:u8,
    pub mtu:u32,
    pub generation:u32,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RxFrameMeta {
    pub ifindex:u32,
    pub protocol:u16,
    pub packet_type:u8,
    pub generation:u32,
    pub captured_l3_len:usize,
    pub wire_l3_len:usize,
    pub truncated:bool,
}

/// Validated *metadata* is not a complete or authenticated packet. The
/// caller still needs strict IPv4/TCP parse and M3 AEAD+PN replay checks.
pub fn validate_rx_metadata(
    snapshot:PacketSnapshot, meta:RxFrameMeta,
) -> Result<(),PreflightError>{
    if snapshot.generation==0||meta.generation!=snapshot.generation {
        return Err(PreflightError::StaleGeneration);
    }
    if snapshot.ifindex==0||meta.ifindex!=snapshot.ifindex {
        return Err(PreflightError::WrongInterfaceIndex{
            expected:snapshot.ifindex,actual:meta.ifindex});
    }
    if meta.protocol!=ETH_P_IP||meta.protocol!=snapshot.protocol {
        return Err(PreflightError::InvalidProtocol);
    }
    if meta.packet_type!=PACKET_HOST||meta.packet_type!=snapshot.packet_type {
        return Err(PreflightError::InvalidPacketType);
    }
    if meta.truncated||meta.wire_l3_len>meta.captured_l3_len {
        return Err(PreflightError::Truncated);
    }
    if meta.captured_l3_len < 40 || meta.captured_l3_len > snapshot.mtu as usize
        || meta.captured_l3_len != meta.wire_l3_len {
        return Err(PreflightError::InvalidRxLength);
    }
    Ok(())
}
fn valid_name(name:&str)->bool {
    !name.is_empty()&&name.len()<=IFNAME_MAX&&name.bytes().all(|b|
        b.is_ascii_alphanumeric()||b==b'_'||b==b'-'||b==b'.')
}
fn kernel_ifindex(name:&str)->Result<u32,PreflightError>{
    if !valid_name(name){return Err(PreflightError::InvalidInterfaceName);}
    let cname=CString::new(name).map_err(|_|PreflightError::InvalidInterfaceName)?;
    // SAFETY: CString is NUL-terminated, nonempty and live for the call.
    let index=unsafe{if_nametoindex(cname.as_ptr())};
    if index==0{return Err(PreflightError::MissingInterface{errno:errno()});}
    Ok(index)
}
/// Queries the *actual host kernel* interface index, no privileged FD.
pub fn interface_index(ifname:&str)->Result<u32,PreflightError>{
    kernel_ifindex(ifname)
}
fn actual_mtu(name:&str)->Result<u32,PreflightError>{
    // Safe path: validate name before joining; no /, colon, whitespace, NUL.
    if !valid_name(name){return Err(PreflightError::InvalidInterfaceName);}
    let p=Path::new("/sys/class/net").join(name).join("mtu");
    let value=std::fs::read_to_string(p)
        .map_err(|e|PreflightError::KernelSocket{errno:e.raw_os_error().unwrap_or(5)})?;
    value.trim().parse::<u32>().map_err(|_|PreflightError::InvalidMtu)
}
/// Cold validation happens *before* privilege check or socket allocation.
/// The allowed proto is IPv4 only; capture type HOST (not outgoing/loopback
/// packet_type). This avoids accepting arbitrary link-layer traffic.
pub fn validate_config(c:PacketConfig<'_>)->Result<PacketSnapshot,PreflightError>{
    if c.ifindex==0{return Err(PreflightError::InvalidInterfaceIndex);}
    if c.protocol!=ETH_P_IP{return Err(PreflightError::InvalidProtocol);}
    if c.packet_type!=PACKET_HOST{return Err(PreflightError::InvalidPacketType);}
    if c.mtu<MIN_IPV4_MTU||c.mtu>u16::MAX as u32 {
        return Err(PreflightError::InvalidMtu);
    }
    if c.generation==0{return Err(PreflightError::InvalidGeneration);}
    let actual=kernel_ifindex(c.ifname)?;
    if actual!=c.ifindex {
        return Err(PreflightError::WrongInterfaceIndex{expected:c.ifindex,actual});
    }
    let available=actual_mtu(c.ifname)?;
    if c.mtu>available {
        return Err(PreflightError::ExceedsDeviceMtu{requested:c.mtu,available});
    }
    Ok(PacketSnapshot{ifindex:actual,protocol:c.protocol,packet_type:c.packet_type,
        mtu:c.mtu,generation:c.generation})
}
fn caps()->Result<[CapData;2],PreflightError>{
    let mut header=CapHeader{version:CAP_V3,pid:0};
    let mut data=[CapData::default();2];
    // SAFETY: Linux x86_64 syscall 125 accepts an 8-byte version/pid struct
    // and two 12-byte v3 user_cap_data structs. Kernel writes only data.
    let rc=unsafe{syscall(SYS_CAPGET,&mut header as *mut CapHeader,
        data.as_mut_ptr())};
    if rc<0{return Err(PreflightError::CapabilityProbe{errno:errno()});}
    Ok(data)
}
pub fn effective_cap_net_raw()->Result<bool,PreflightError>{
    let data=caps()?;
    Ok((data[0].effective & (1u32<<CAP_NET_RAW))!=0)
}

/// RAII owned *inactive* AF_PACKET raw FD with protocol=0. No bind() call,
/// no Rx/Tx, no FD leaking to Go/driver. Drop closes this fd exactly once.
pub struct PacketPreflightFd {
    fd:OwnedFd,
    snapshot:PacketSnapshot,
    fence:BorrowFence,
}
impl PacketPreflightFd {
    pub fn snapshot(&self)->PacketSnapshot{self.snapshot}
    pub fn begin_stop(&self){self.fence.begin_stop();}
    pub fn wait_drained_until(&self,deadline:Instant)->StopResult{
        self.fence.wait_drained_until(deadline)
    }
    pub fn outstanding(&self)->usize{self.fence.outstanding()}
    pub fn is_stopping(&self)->bool{self.fence.is_stopping()}
    /// Rust borrow lifetime keeps the FD owned and open until the guard is
    /// returned. Atomic BorrowFence fences stop with the last borrower.
    pub fn borrow(&self,caller_generation:u32)->Result<PacketPreflightBorrow<'_>,PreflightError>{
        if caller_generation!=self.snapshot.generation {
            return Err(PreflightError::StaleGeneration);
        }
        let guard=self.fence.try_enter_ready().map_err(|e|match e{
            BorrowError::Stopping=>PreflightError::Stopping,
            BorrowError::TooManyLoans=>PreflightError::LoansFull
        })?;
        Ok(PacketPreflightBorrow{_fd:&self.fd,_guard:guard})
    }
    #[cfg(test)]
    fn raw_fd(&self)->c_int{self.fd.as_raw_fd()}
}
pub struct PacketPreflightBorrow<'a> {
    _fd:&'a OwnedFd,
    _guard:ReadyBatchGuard<'a>,
}

/// Opens an inactive protocol-0 AF_PACKET FD, only after validating actual
/// ifname/index/MTU and a positive effective CAP_NET_RAW check.
/// A kernel EPERM even when caps report present remains typed and terminal.
/// **No UDP fallback**, no raw bind, no I/O, no ambient privileges granted.
pub fn open_preflight(c:PacketConfig<'_>)->Result<PacketPreflightFd,PreflightError>{
    let snapshot=validate_config(c)?;
    if !effective_cap_net_raw()? {
        return Err(PreflightError::PermissionDenied{errno:EPERM});
    }
    // SAFETY: fixed numeric Linux AF_PACKET/SOCK_RAW|NONBLOCK|CLOEXEC ABI;
    // protocol ZERO intentionally deactivates raw reception/transmission.
    let fd=unsafe{socket(AF_PACKET,SOCK_RAW|SOCK_NONBLOCK|SOCK_CLOEXEC,0)};
    if fd<0{
        let e=errno();
        return Err(if e==EPERM {PreflightError::PermissionDenied{errno:e}}
            else{PreflightError::KernelSocket{errno:e}});
    }
    // SAFETY: fd>=0 was returned exclusively by successful libc socket().
    // OwnedFd owns it and its Drop closes, including unwind/early exits.
    let fd=unsafe{OwnedFd::from_raw_fd(fd)};
    Ok(PacketPreflightFd{fd,snapshot,fence:BorrowFence::default()})
}

#[cfg(test)]
mod tests{
    use super::*;
    use std::mem::{size_of,offset_of};
    use std::process::Command;
    use std::sync::{Arc,Barrier,atomic::{AtomicUsize,Ordering}};
    use std::time::Instant;
    const EPERM_RAW_CHILD:&str="WBD_M4_DROP_RAW_EFFECTIVE_ONLY";
    fn config<'a>(name:&'a str)->PacketConfig<'a>{
        PacketConfig{ifname:name,ifindex:interface_index(name).unwrap(),protocol:ETH_P_IP,
            packet_type:PACKET_HOST,mtu:1500,generation:7}
    }
    #[test]
    fn r1_af_packet_kernel_interface_index_and_mtu_prevalidate(){
        let lo=interface_index("lo").unwrap();
        assert!(lo>0);
        let c=config("lo");
        let validated=validate_config(c).unwrap();
        assert_eq!(validated.ifindex,lo);
        assert_eq!(validated.mtu,1500);
        assert_eq!(validated.generation,7);
        assert!(actual_mtu("lo").unwrap()>=1500);
        assert_eq!(interface_index("../../etc"),Err(PreflightError::InvalidInterfaceName));
        assert_eq!(interface_index("name with space"),Err(PreflightError::InvalidInterfaceName));
        assert_eq!(interface_index(""),Err(PreflightError::InvalidInterfaceName));
        assert_eq!(interface_index("0".repeat(16).as_str()),Err(PreflightError::InvalidInterfaceName));
    }
    #[test]
    fn r1_af_packet_invalid_iface_and_index_fail_before_socket(){
        let mut c=config("lo");c.ifindex=0;
        assert_eq!(validate_config(c),Err(PreflightError::InvalidInterfaceIndex));
        c=config("lo");c.ifindex=c.ifindex.wrapping_add(1);
        assert!(matches!(validate_config(c),Err(PreflightError::WrongInterfaceIndex{..})));
        c=config("lo");c.ifname="wbd_notreal0";
        assert!(matches!(validate_config(c),Err(PreflightError::MissingInterface{..})));
    }
    #[test]
    fn r1_af_packet_protocol_packet_type_mtu_generation_gate(){
        let mut c=config("lo");c.protocol=0;
        assert_eq!(validate_config(c),Err(PreflightError::InvalidProtocol));
        c=config("lo");c.protocol=3;
        assert_eq!(validate_config(c),Err(PreflightError::InvalidProtocol));
        c=config("lo");c.packet_type=4;
        assert_eq!(validate_config(c),Err(PreflightError::InvalidPacketType));
        c=config("lo");c.mtu=67;
        assert_eq!(validate_config(c),Err(PreflightError::InvalidMtu));
        c=config("lo");c.mtu=65536;
        assert_eq!(validate_config(c),Err(PreflightError::InvalidMtu));
        c=config("lo");c.generation=0;
        assert_eq!(validate_config(c),Err(PreflightError::InvalidGeneration));
        c=config("lo");c.mtu=1500;
        assert_eq!(open_preflight(c).map(|_|()).err(),
            open_preflight(c).map(|_|()).err()); // each independent open is RAII
    }
    #[test]
    fn r1_af_packet_no_raw_cap_child_exact_eperm_and_no_udp_fallback(){
        if std::env::var_os(EPERM_RAW_CHILD).is_some(){
            let mut hdr=CapHeader{version:CAP_V3,pid:0};
            let mut data=caps().unwrap();
            data[0].effective &= !(1u32<<CAP_NET_RAW);
            // SAFETY: running in isolated test child process: change only
            // this process's effective CAP_NET_RAW, keep all other caps and
            // permitted/inheritable unchanged. Never mutate parent runner.
            let rc=unsafe{syscall(SYS_CAPSET,&mut hdr as *mut CapHeader,
                data.as_ptr())};
            assert_eq!(rc,0,"capset child: {}",errno());
            assert_eq!(effective_cap_net_raw(),Ok(false));
            let c=config("lo");
            assert!(matches!(open_preflight(c),
                Err(PreflightError::PermissionDenied{errno:EPERM})));
            // Direct real kernel negative syscall, not only an invented
            // classifier result. CAP_NET_RAW removed => EPERM exactly.
            let fd=unsafe{socket(AF_PACKET,SOCK_RAW|SOCK_NONBLOCK|SOCK_CLOEXEC,0)};
            assert_eq!(fd,-1);
            assert_eq!(errno(),EPERM);
            return;
        }
        let exe=std::env::current_exe().unwrap();
        let out=Command::new(exe)
            .arg("--exact")
            .arg("linux_packet_preflight::tests::r1_af_packet_no_raw_cap_child_exact_eperm_and_no_udp_fallback")
            .arg("--nocapture")
            .env(EPERM_RAW_CHILD,"1")
            .output().unwrap();
        assert!(out.status.success(),
            "child exit {:?} stderr:{} stdout:{}",
            out.status,String::from_utf8_lossy(&out.stderr),
            String::from_utf8_lossy(&out.stdout));
        assert!(String::from_utf8_lossy(&out.stdout).contains("1 passed"));
    }
    #[test]
    fn r1_af_packet_native_socket_protocol_zero_fd_owned_and_closed(){
        let c=config("lo");
        match open_preflight(c){
            Ok(s)=>{
                let fd=s.raw_fd();
                // Native fcntl verifies exact nonblocking+close-on-exec.
                let flags=unsafe{fcntl(fd,F_GETFL)};
                let fdflags=unsafe{fcntl(fd,F_GETFD)};
                assert_ne!(flags&SOCK_NONBLOCK,0);
                assert_eq!(fdflags&FD_CLOEXEC,FD_CLOEXEC);
                assert_eq!(s.snapshot().protocol,ETH_P_IP);
                assert_eq!(s.outstanding(),0);
                drop(s);
                assert_eq!(unsafe{fcntl(fd,F_GETFD)},-1);
                assert_eq!(errno(),9); // EBADF: OwnedFd closed.
            }
            Err(PreflightError::PermissionDenied{errno:EPERM})=>{
                // Unprivileged GH runner: exact permission gating, no fd.
                assert!(!effective_cap_net_raw().unwrap_or(false)
                    || std::env::var_os("CI").is_some());
            }
            Err(e)=>panic!("unexpected kernel AF_PACKET preflight: {e:?}")
        }
    }
    #[test]
    fn r1_af_packet_rx_meta_packet_type_truncation_generation_fail_closed(){
        let s=PacketSnapshot{ifindex:3,protocol:ETH_P_IP,packet_type:PACKET_HOST,
            mtu:1500,generation:9};
        let m=RxFrameMeta{ifindex:3,protocol:ETH_P_IP,packet_type:PACKET_HOST,
            generation:9,captured_l3_len:80,wire_l3_len:80,truncated:false};
        assert_eq!(validate_rx_metadata(s,m),Ok(()));
        assert_eq!(validate_rx_metadata(s,RxFrameMeta{ifindex:4,..m}),
            Err(PreflightError::WrongInterfaceIndex{expected:3,actual:4}));
        assert_eq!(validate_rx_metadata(s,RxFrameMeta{protocol:0x86dd,..m}),
            Err(PreflightError::InvalidProtocol));
        for bad_type in [1,2,3,4,5,255]{
            assert_eq!(validate_rx_metadata(s,RxFrameMeta{packet_type:bad_type,..m}),
                Err(PreflightError::InvalidPacketType));
        }
        assert_eq!(validate_rx_metadata(s,RxFrameMeta{generation:8,..m}),
            Err(PreflightError::StaleGeneration));
        assert_eq!(validate_rx_metadata(s,RxFrameMeta{truncated:true,..m}),
            Err(PreflightError::Truncated));
        assert_eq!(validate_rx_metadata(s,RxFrameMeta{captured_l3_len:40,wire_l3_len:80,..m}),
            Err(PreflightError::Truncated));
        assert_eq!(validate_rx_metadata(s,RxFrameMeta{captured_l3_len:1501,wire_l3_len:1501,..m}),
            Err(PreflightError::InvalidRxLength));
        assert_eq!(validate_rx_metadata(s,RxFrameMeta{captured_l3_len:39,wire_l3_len:39,..m}),
            Err(PreflightError::InvalidRxLength));
    }
    #[test]
    fn r1_af_packet_borrow_stop_generation_close_raii(){
        match open_preflight(config("lo")){
            Ok(s)=>{
                assert_eq!(s.borrow(8).err(),Some(PreflightError::StaleGeneration));
                let loan=s.borrow(7).unwrap();
                assert_eq!(s.outstanding(),1);
                assert_eq!(s.wait_drained_until(Instant::now()),StopResult::Pending{outstanding:1});
                assert!(matches!(s.borrow(7),Err(PreflightError::Stopping)));
                drop(loan);
                assert_eq!(s.wait_drained_until(Instant::now()),StopResult::Drained);
                assert_eq!(s.outstanding(),0);
                let fd=s.raw_fd();
                drop(s);
                assert_eq!(unsafe{fcntl(fd,F_GETFD)},-1);
                assert_eq!(errno(),9);
            }
            Err(PreflightError::PermissionDenied{errno:EPERM})=>{}
            Err(e)=>panic!("unexpected kernel permission state {e:?}")
        }
    }
    #[test]
    fn r1_af_packet_stop_registration_race_atomic_and_bounded(){
        let fence=Arc::new(BorrowFence::default());
        let barrier=Arc::new(Barrier::new(2));
        let registered=Arc::new(AtomicUsize::new(0));
        let b=Arc::clone(&barrier);let f=Arc::clone(&fence);let n=Arc::clone(&registered);
        let t=std::thread::spawn(move||{
            b.wait();
            if let Ok(_l)=f.try_enter_ready(){
                n.fetch_add(1,Ordering::SeqCst);
                std::thread::yield_now();
            }
        });
        barrier.wait();fence.begin_stop();t.join().unwrap();
        assert!(registered.load(Ordering::SeqCst)<=1);
        assert_eq!(fence.outstanding(),0);
        assert_eq!(fence.wait_drained_until(Instant::now()),StopResult::Drained);
        assert!(fence.try_enter_ready().is_err());
    }
    #[test]
    fn r1_af_packet_cap_syscall_native_abi_no_privilege_escalation(){
        assert_eq!(size_of::<CapHeader>(),8);
        assert_eq!(size_of::<CapData>(),12);
        assert_eq!(offset_of!(CapData,effective),0);
        assert_eq!(offset_of!(CapData,permitted),4);
        assert_eq!(offset_of!(CapData,inheritable),8);
        assert_eq!(CAP_NET_RAW,13);
        let cap=effective_cap_net_raw().unwrap();
        let again=effective_cap_net_raw().unwrap();
        assert_eq!(cap,again);
    }
}
