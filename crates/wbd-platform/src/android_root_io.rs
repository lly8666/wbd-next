//! Android/Bionic cold ownership boundary for the shared WBD Rust product.
//! These are syscall/descriptor primitives, NOT a second crypto, packet pump,
//! VPN service or privilege-escalation path. The authenticated Go owner still
//! must supply and retain the actual generation/lease/physical network.
#![cfg(target_os = "android")]

use std::ffi::{c_int, c_uint, c_void, CString};
use std::io;
use std::os::fd::{AsRawFd, FromRawFd, OwnedFd, RawFd};
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Instant;
use crate::r1::{BorrowFence,BorrowError,StopResult};

const IFNAMSIZ: usize = 16;
const IFREQ_BYTES: usize = 40; // Android 64-bit struct ifreq; asserted in NDK C compile.
const IFF_TUN: i16 = 1;
const IFF_NO_PI: i16 = 0x1000;
const TUNGETIFF: usize = 0x8004_54d2; // _IOR('T',210,int), Linux64
const F_GETFL: c_int = 3;
const F_SETFL: c_int = 4;
const O_NONBLOCK: c_int = 0x800;
const SOL_SOCKET: c_int = 1;
const SO_BINDTODEVICE: c_int = 25;
const AF_INET: c_int = 2;
const SOCK_RAW: c_int = 3;
const SOCK_NONBLOCK: c_int = 0x800;
const SOCK_CLOEXEC: c_int = 0x80000;
const IPPROTO_TCP: c_int = 6;

// Only Android ARM64 arm64-v8a is supported. Android x86/x86_64 and
// 32-bit targets are excluded; the mature Linux x86 code remains unchanged.
const _: [(); IFREQ_BYTES] = [(); std::mem::size_of::<[u8; 40]>()];

unsafe extern "C" {
    fn ioctl(fd: c_int, request: usize, ...) -> c_int;
    fn fcntl(fd: c_int, request: c_int, ...) -> c_int;
    fn if_nametoindex(name: *const std::ffi::c_char) -> c_uint;
    fn setsockopt(fd: c_int, level: c_int, option: c_int, value: *const c_void, len: u32) -> c_int;
    fn socket(domain: c_int, kind: c_int, protocol: c_int) -> c_int;
    fn read(fd: c_int, data: *mut c_void, len: usize) -> isize;
    fn write(fd: c_int, data: *const c_void, len: usize) -> isize;
}

#[link(name = "android")]
unsafe extern "C" {
    // Android NDK android/multinetwork.h; explicit physical Network handle
    // from ConnectivityManager, never a process-global binding.
    fn android_setsocknetwork(network: u64, fd: c_int) -> c_int;
}

fn name_bytes(name: &str) -> io::Result<CString> {
    if name.is_empty() || name.len() >= IFNAMSIZ ||
        !name.bytes().all(|c| c.is_ascii_alphanumeric() || c == b'_' || c == b'-') {
        return Err(io::Error::new(io::ErrorKind::InvalidInput, "invalid interface name"));
    }
    CString::new(name).map_err(|_| io::Error::new(io::ErrorKind::InvalidInput, "NUL in name"))
}

/// A single already-created TUN descriptor is MOVED into Rust after
/// authenticated cold-control. Never calls TUNSETIFF, changes netd, or
/// guesses a tunnel address. Only IFF_TUN|IFF_NO_PI is accepted.
pub struct AndroidOwnedTun {
    fd: OwnedFd,
    name: String,
    generation: u32,
    active: AtomicBool,
    borrow: BorrowFence,
}
impl AndroidOwnedTun {
    pub fn adopt(fd: OwnedFd, expected_name: &str, generation: u32)
        -> Result<Self, (io::Error, OwnedFd)> {
        if generation == 0 || name_bytes(expected_name).is_err() {
            return Err((io::Error::new(io::ErrorKind::InvalidInput, "name/generation"), fd));
        }
        let mut ifreq = [0u8; IFREQ_BYTES];
        // SAFETY: owns a live FD and passes a bounded, 40-byte aligned-sized
        // Bionic/Linux64 ifreq backing store. NDK static asserts gate layout.
        if unsafe { ioctl(fd.as_raw_fd(), TUNGETIFF, ifreq.as_mut_ptr()) } != 0 {
            return Err((io::Error::last_os_error(), fd));
        }
        let namelen = ifreq[..IFNAMSIZ].iter().position(|b| *b == 0).unwrap_or(IFNAMSIZ);
        let flags = i16::from_ne_bytes([ifreq[16], ifreq[17]]);
        if namelen != expected_name.len() || &ifreq[..namelen] != expected_name.as_bytes()
            || flags & (IFF_TUN | IFF_NO_PI) != (IFF_TUN | IFF_NO_PI)
            || flags & 2 != 0 {
            return Err((io::Error::new(io::ErrorKind::InvalidData, "wrong TUN or PI"), fd));
        }
        let old = unsafe { fcntl(fd.as_raw_fd(), F_GETFL) };
        if old < 0 {
            return Err((io::Error::last_os_error(), fd));
        }
        if old & O_NONBLOCK == 0
            && unsafe { fcntl(fd.as_raw_fd(), F_SETFL, old | O_NONBLOCK) } < 0 {
            return Err((io::Error::last_os_error(), fd));
        }
        Ok(Self { fd, name: expected_name.to_owned(), generation, active: AtomicBool::new(true), borrow: BorrowFence::default() })
    }

    pub fn name(&self) -> &str { &self.name }
    pub fn generation(&self) -> u32 { self.generation }
    pub fn readiness_fd(&self) -> RawFd { self.fd.as_raw_fd() }
    pub fn begin_stop(&self) {
        self.active.store(false, Ordering::Release);
        self.borrow.begin_stop();
    }
    pub fn stop_until(&self, deadline: Instant) -> StopResult {
        self.begin_stop();
        self.borrow.wait_drained_until(deadline)
    }

    pub fn read_ip(&self, packet: &mut [u8]) -> io::Result<usize> {
        if !self.active.load(Ordering::Acquire) { return Err(io::ErrorKind::BrokenPipe.into()); }
        if packet.is_empty() { return Err(io::ErrorKind::InvalidInput.into()); }
        let _loan = self.borrow.try_enter_ready()
            .map_err(|_|io::Error::from(io::ErrorKind::BrokenPipe))?;
        let count = unsafe { read(self.fd.as_raw_fd(), packet.as_mut_ptr().cast(), packet.len()) };
        if count < 0 { Err(io::Error::last_os_error()) } else { Ok(count as usize) }
    }
    /// Only the authenticated data owner can call this after remote AEAD +
    /// valid leased-address checks; kernel copy is NOT a delivery receipt.
    pub fn write_authenticated_ip(&self, packet: &[u8]) -> io::Result<usize> {
        if !self.active.load(Ordering::Acquire) { return Err(io::ErrorKind::BrokenPipe.into()); }
        if packet.is_empty() { return Err(io::ErrorKind::InvalidInput.into()); }
        let _loan = self.borrow.try_enter_ready()
            .map_err(|_|io::Error::from(io::ErrorKind::BrokenPipe))?;
        let count = unsafe { write(self.fd.as_raw_fd(), packet.as_ptr().cast(), packet.len()) };
        if count < 0 { Err(io::Error::last_os_error()) } else { Ok(count as usize) }
    }
}

/// The cold Go/network controller supplies the real physical Network handle
/// AND expected interface. A 0 handle fails closed. No global process mark,
/// no exception for all root UID traffic, no fallback to default Android net.
pub fn bind_underlay_socket(fd: RawFd, network_handle: u64, interface: &str)
    -> io::Result<u32> {
    let ifname = name_bytes(interface)?;
    if fd < 0 || network_handle == 0 {
        return Err(io::Error::new(io::ErrorKind::InvalidInput, "missing fd/network handle"));
    }
    let index = unsafe { if_nametoindex(ifname.as_ptr()) };
    if index == 0 { return Err(io::Error::last_os_error()); }
    let rc = unsafe { android_setsocknetwork(network_handle, fd) };
    if rc != 0 { return Err(io::Error::from_raw_os_error(rc.abs())); }
    let rc = unsafe {
        setsockopt(fd, SOL_SOCKET, SO_BINDTODEVICE,
            ifname.as_bytes_with_nul().as_ptr().cast(),
            ifname.as_bytes_with_nul().len() as u32)
    };
    if rc < 0 { return Err(io::Error::last_os_error()); }
    Ok(index)
}

/// Open only a nonblocking raw IPv4/TCP socket, then require an exact
/// interface + Android Network binding. There is no unbound fallback.
pub fn open_bound_raw_tcp(network_handle: u64, interface: &str)
    -> io::Result<(OwnedFd, u32)> {
    let fd = unsafe { socket(AF_INET, SOCK_RAW | SOCK_NONBLOCK | SOCK_CLOEXEC, IPPROTO_TCP) };
    if fd < 0 { return Err(io::Error::last_os_error()); }
    // SAFETY: socket returned a unique valid descriptor; Rust owns Close.
    let owned = unsafe { OwnedFd::from_raw_fd(fd) };
    let index = bind_underlay_socket(owned.as_raw_fd(), network_handle, interface)?;
    Ok((owned, index))
}


// A2 Android-only kernel I/O seam for the ORIGINAL Rust authenticated M4
// worker. The structs own only Bionic FDs; no credentials, TLS, FEC, packet
// scheduler or route mutation lives here. Integration with M4 is NOT_RUN.
const IPPROTO_RAW: c_int = 255;
const IPPROTO_IP: c_int = 0;
const IP_HDRINCL: c_int = 3;
const SO_ATTACH_FILTER: c_int = 26;
const SIOCGIFMTU: usize = 0x8921;
const MSG_DONTWAIT: c_int = 0x40;
const MSG_TRUNC: c_int = 0x20;
const MIN_IPV4_MTU: u32 = 68;
const MAX_IPV4_MTU: u32 = 65535;

#[repr(C)]
struct AndroidSockAddrIn {
    family: u16,
    port: u16,
    ip_be: u32,
    zero: [u8; 8],
}
#[repr(C)]
#[derive(Clone, Copy)]
struct AndroidSockFilter {
    code: u16,
    jt: u8,
    jf: u8,
    k: u32,
}
#[repr(C)]
struct AndroidSockFprog {
    len: u16,
    filter: *const AndroidSockFilter,
}
unsafe extern "C" {
    fn sendto(fd: c_int, data: *const c_void, len: usize, flags: c_int,
        address: *const c_void, address_len: u32) -> isize;
    fn recvfrom(fd: c_int, data: *mut c_void, len: usize, flags: c_int,
        address: *mut c_void, address_len: *mut u32) -> isize;
}

/// Read back the physical interface MTU using the *same* bound socket.
/// Go's cold Network callback must rotate/re-authorize a changed ifindex/MTU;
/// this is not a second netlink listener or a per-packet ioctl.
pub fn check_bound_interface_mtu(
    fd: RawFd, interface: &str, expected_ifindex: u32, expected_mtu: u32,
) -> io::Result<()> {
    let name = name_bytes(interface)?;
    if fd < 0 || expected_ifindex == 0 ||
        !(MIN_IPV4_MTU..=MAX_IPV4_MTU).contains(&expected_mtu) {
        return Err(io::Error::new(io::ErrorKind::InvalidInput, "invalid network scope"));
    }
    let observed_index = unsafe { if_nametoindex(name.as_ptr()) };
    if observed_index == 0 || observed_index != expected_ifindex {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "physical ifindex changed"));
    }
    let mut req = [0u8; IFREQ_BYTES];
    req[..name.as_bytes().len()].copy_from_slice(name.as_bytes());
    if unsafe { ioctl(fd, SIOCGIFMTU, req.as_mut_ptr()) } != 0 {
        return Err(io::Error::last_os_error());
    }
    let observed_mtu = i32::from_ne_bytes(req[16..20].try_into().unwrap());
    if observed_mtu <= 0 || observed_mtu as u32 != expected_mtu {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "physical MTU changed"));
    }
    Ok(())
}

fn exact_raw_tcp_filter(
    source: [u8; 4], destination: [u8; 4],
    source_port: u16, destination_port: u16,
) -> io::Result<[AndroidSockFilter; 13]> {
    if source_port == 0 || destination_port == 0 ||
        source[0] == 0 || destination[0] == 0 {
        return Err(io::Error::new(io::ErrorKind::InvalidInput, "invalid owned TCP tuple"));
    }
    // Exactly the mature Linux M4 13-insn classic BPF shape: protocol,
    // source/destination IP and TCP ports at variable IPv4 IHL. Bionic
    // sock_filter/sock_fprog are verified against the NDK at build time.
    let load = |code, k| AndroidSockFilter { code, jt: 0, jf: 0, k };
    let eq = |k, jf| AndroidSockFilter { code: 0x15, jt: 0, jf, k };
    Ok([
        load(0x30, 9), eq(6, 10),
        load(0x20, 12), eq(u32::from_be_bytes(source), 8),
        load(0x20, 16), eq(u32::from_be_bytes(destination), 6),
        load(0xb1, 0),
        load(0x48, 0), eq(u32::from(source_port), 3),
        load(0x48, 2), eq(u32::from(destination_port), 1),
        load(0x06, u32::MAX), load(0x06, 0),
    ])
}

/// Kernel-only raw RX descriptor, with NO unfiltered fallback. A packet
/// remains unauthenticated until the existing Rust M3 opener validates it.
pub struct AndroidBoundRawRx {
    fd: OwnedFd,
    generation: u32,
    mtu: u32,
    stopping: AtomicBool,
    borrow: BorrowFence,
}
impl AndroidBoundRawRx {
    pub fn open_exact(
        network_handle: u64, interface: &str, expected_ifindex: u32,
        expected_mtu: u32, generation: u32,
        source: [u8; 4], destination: [u8; 4],
        source_port: u16, destination_port: u16,
    ) -> io::Result<Self> {
        if generation == 0 {
            return Err(io::Error::new(io::ErrorKind::InvalidInput, "missing generation"));
        }
        let instructions = exact_raw_tcp_filter(source, destination, source_port, destination_port)?;
        let (fd, index) = open_bound_raw_tcp(network_handle, interface)?;
        if index != expected_ifindex {
            return Err(io::Error::new(io::ErrorKind::InvalidData, "raw RX wrong ifindex"));
        }
        check_bound_interface_mtu(fd.as_raw_fd(), interface, index, expected_mtu)?;
        let program = AndroidSockFprog { len: instructions.len() as u16,
            filter: instructions.as_ptr() };
        let rc = unsafe { setsockopt(fd.as_raw_fd(), SOL_SOCKET, SO_ATTACH_FILTER,
            (&program as *const AndroidSockFprog).cast(),
            std::mem::size_of::<AndroidSockFprog>() as u32) };
        if rc != 0 { return Err(io::Error::last_os_error()); }
        Ok(Self { fd, generation, mtu: expected_mtu,
            stopping: AtomicBool::new(false), borrow: BorrowFence::default() })
    }
    pub fn generation(&self) -> u32 { self.generation }
    pub fn is_stopping(&self) -> bool { self.stopping.load(Ordering::Acquire) }
    pub fn readiness_fd(&self) -> RawFd { self.fd.as_raw_fd() }
    pub fn begin_stop(&self) {
        self.stopping.store(true, Ordering::Release);
        self.borrow.begin_stop();
    }
    pub fn stop_until(&self, deadline: Instant) -> StopResult {
        self.begin_stop();
        self.borrow.wait_drained_until(deadline)
    }
    /// Nonblocking *one* kernel read into the original M1-owned slab. The
    /// caller must use shared rx_ipv4_tcp parsing and original M3 AEAD/PN.
    pub fn read_untrusted(&self, generation: u32, buffer: &mut [u8]) -> io::Result<usize> {
        if self.stopping.load(Ordering::Acquire) || generation != self.generation {
            return Err(io::ErrorKind::BrokenPipe.into());
        }
        if buffer.len() < 40 {
            return Err(io::Error::new(io::ErrorKind::InvalidInput, "small M1 slab"));
        }
        let _loan = self.borrow.try_enter_ready().map_err(|error|match error {
            BorrowError::Stopping => io::Error::from(io::ErrorKind::BrokenPipe),
            BorrowError::TooManyLoans => io::Error::from(io::ErrorKind::OutOfMemory),
        })?;
        let cap = buffer.len().min(self.mtu as usize);
        let n = unsafe { recvfrom(self.fd.as_raw_fd(), buffer.as_mut_ptr().cast(), cap,
            MSG_DONTWAIT | MSG_TRUNC, std::ptr::null_mut(), std::ptr::null_mut()) };
        if n < 0 { return Err(io::Error::last_os_error()); }
        if n as usize > cap {
            return Err(io::Error::new(io::ErrorKind::InvalidData, "truncated raw RX"));
        }
        Ok(n as usize)
    }
    /// Shared original rx_ipv4_tcp strict parser over the ORIGINAL M1 slab.
    /// The result is untrusted ciphertext until the same M3 AEAD/unique PN
    /// accepts it; the IPv4/TCP headers are compacted IN PLACE, no allocation.
    pub fn read_original_record(
        &self,generation:u32,slab:&mut [u8],
        tuple:crate::ipv4_tcp::Ipv4Tuple<'_>,
        persona:crate::ipv4_tcp::PacketPersona,
    )->io::Result<(usize,u32)>{
        let total=self.read_untrusted(generation,slab)?;
        let parsed=crate::rx_ipv4_tcp::parse_data_packet(
            &slab[..total],crate::rx_ipv4_tcp::TrustedRx{
                tuple,persona,mtu:self.mtu as usize,
                authenticated_options:None,
            }
        ).map_err(|_|io::Error::new(io::ErrorKind::InvalidData,
            "invalid original M4 IPv4/TCP candidate"))?;
        let seq=parsed.seq32;
        let wire=parsed.ciphertext.len();
        // No unrelated packets or malformed flags/checksums reach M1.
        slab.copy_within(total-wire..total,0);
        Ok((wire,seq))
    }
}

/// Scoped native RAW TX. Only the original M4 may supply a fully formed
/// IPv4/TCP packet from shared ipv4_tcp::build over an immutable M3 record.
/// No direct-app TCP relay, Go data pump, or alternative TCP/IP stack.
pub struct AndroidBoundRawTx {
    fd: OwnedFd,
    generation: u32,
    mtu: u32,
    source: [u8; 4],
    destination: [u8; 4],
    source_port:u16,
    destination_port:u16,
    stopping: AtomicBool,
    borrow: BorrowFence,
}
impl AndroidBoundRawTx {
    pub fn open(
        network_handle: u64, interface: &str, expected_ifindex: u32,
        expected_mtu: u32, generation: u32,
        source: [u8; 4], destination: [u8; 4],
        source_port:u16,destination_port:u16,
    ) -> io::Result<Self> {
        if generation == 0 || source[0] == 0 ||
            destination[0] == 0 || destination[0] >= 224 ||
            source_port==0 || destination_port==0 {
            return Err(io::Error::new(io::ErrorKind::InvalidInput, "invalid owned outer tuple"));
        }
        let raw = unsafe { socket(AF_INET, SOCK_RAW | SOCK_NONBLOCK | SOCK_CLOEXEC, IPPROTO_RAW) };
        if raw < 0 { return Err(io::Error::last_os_error()); }
        let fd = unsafe { OwnedFd::from_raw_fd(raw) };
        let index = bind_underlay_socket(fd.as_raw_fd(), network_handle, interface)?;
        if index != expected_ifindex {
            return Err(io::Error::new(io::ErrorKind::InvalidData, "raw TX wrong ifindex"));
        }
        check_bound_interface_mtu(fd.as_raw_fd(), interface, index, expected_mtu)?;
        let hdrincl: c_int = 1;
        if unsafe { setsockopt(fd.as_raw_fd(), IPPROTO_IP, IP_HDRINCL,
            (&hdrincl as *const c_int).cast(), std::mem::size_of::<c_int>() as u32) } != 0 {
            return Err(io::Error::last_os_error());
        }
        Ok(Self { fd, generation, mtu: expected_mtu, source, destination,
            source_port,destination_port,
            stopping: AtomicBool::new(false), borrow: BorrowFence::default() })
    }
    pub fn generation(&self) -> u32 { self.generation }
    pub fn is_stopping(&self) -> bool { self.stopping.load(Ordering::Acquire) }
    pub fn readiness_fd(&self) -> RawFd { self.fd.as_raw_fd() }
    pub fn begin_stop(&self) {
        self.stopping.store(true, Ordering::Release);
        self.borrow.begin_stop();
    }
    pub fn stop_until(&self, deadline: Instant) -> StopResult {
        self.begin_stop();
        self.borrow.wait_drained_until(deadline)
    }
    /// Build the exact original Ipv4/TCP presentation around the already
    /// encrypted immutable FrozenRecord and its original PN/seq metadata.
    /// Caller preallocates a reusable scratch buffer; no Go, TLS, heap or
    /// independent worker is introduced on this record path.
    pub fn send_original_frozen<H:wbd_types::buffer_contract::FrozenRecordHandle>(
        &self,generation:u32,record:&H,
        tuple:crate::ipv4_tcp::Ipv4Tuple<'_>,
        presentation:crate::ipv4_tcp::Presentation,
        route_budget:u32,scratch:&mut [u8],
    )->io::Result<usize>{
        if generation!=self.generation||self.is_stopping() ||
            route_budget<MIN_IPV4_MTU||route_budget>self.mtu {
            return Err(io::Error::from(io::ErrorKind::BrokenPipe))
        }
        let built=crate::ipv4_tcp::build(
            tuple,presentation,record,None,route_budget as usize,scratch
        ).map_err(|_|io::Error::new(io::ErrorKind::InvalidData,
            "original M3 frozen record exceeds physical MTU"))?;
        self.send_built_outer(generation,built,route_budget)
    }

    /// Kernel copy != remote delivery. Short/uncertain sends are returned
    /// as errors; never reseal a PN or silently try an unbound route.
    /// route_budget is the shared native M4's last approved PMTU snapshot,
    /// not a per-packet Go callback or an independently refreshed timer.
    pub fn send_built_outer(
        &self, generation: u32, packet: &[u8], route_budget: u32,
    ) -> io::Result<usize> {
        if self.stopping.load(Ordering::Acquire) || generation != self.generation {
            return Err(io::ErrorKind::BrokenPipe.into());
        }
        if packet.len() < 40 || route_budget < MIN_IPV4_MTU ||
            route_budget > self.mtu || packet.len() > route_budget as usize ||
            packet.len() > MAX_IPV4_MTU as usize || packet[0] != 0x45 ||
            packet[9] != IPPROTO_TCP as u8 ||
            usize::from(u16::from_be_bytes([packet[2], packet[3]])) != packet.len() ||
            packet[12..16] != self.source || packet[16..20] != self.destination ||
            u16::from_be_bytes([packet[20],packet[21]])!=self.source_port ||
            u16::from_be_bytes([packet[22],packet[23]])!=self.destination_port ||
            packet[6]!=0x40 || packet[7]!=0 {
            return Err(io::Error::new(io::ErrorKind::InvalidData, "invalid original M4 outer"));
        }
        let _loan = self.borrow.try_enter_ready().map_err(|error|match error {
            BorrowError::Stopping => io::Error::from(io::ErrorKind::BrokenPipe),
            BorrowError::TooManyLoans => io::Error::from(io::ErrorKind::OutOfMemory),
        })?;
        let address = AndroidSockAddrIn {
            family: AF_INET as u16, port: 0,
            ip_be: u32::from_ne_bytes(self.destination), zero: [0; 8],
        };
        let sent = unsafe { sendto(self.fd.as_raw_fd(), packet.as_ptr().cast(),
            packet.len(), MSG_DONTWAIT,
            (&address as *const AndroidSockAddrIn).cast(),
            std::mem::size_of::<AndroidSockAddrIn>() as u32) };
        if sent < 0 { return Err(io::Error::last_os_error()); }
        if sent as usize != packet.len() {
            return Err(io::Error::new(io::ErrorKind::WriteZero, "uncertain raw short send"));
        }
        Ok(sent as usize)
    }
}
