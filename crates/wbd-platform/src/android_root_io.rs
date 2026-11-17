//! Android/Bionic cold ownership boundary for the shared WBD Rust product.
//! These are syscall/descriptor primitives, NOT a second crypto, packet pump,
//! VPN service or privilege-escalation path. The authenticated Go owner still
//! must supply and retain the actual generation/lease/physical network.
#![cfg(target_os = "android")]

use std::ffi::{c_int, c_uint, c_void, CString};
use std::io;
use std::os::fd::{AsRawFd, FromRawFd, OwnedFd, RawFd};
use std::sync::atomic::{AtomicBool, Ordering};

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

// Only 64-bit Android (arm64-v8a / x86_64) is enabled. Revisit the
// Bionic ifreq layout and ioctl request ABI before introducing a 32-bit ABI.
const _: [(); IFREQ_BYTES] = [(); std::mem::size_of::<[u8; 40]>()];

unsafe extern "C" {
    fn ioctl(fd: c_int, request: usize, ...) -> c_int;
    fn fcntl(fd: c_int, request: c_int, ...) -> c_int;
    fn if_nametoindex(name: *const i8) -> c_uint;
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
        Ok(Self { fd, name: expected_name.to_owned(), generation, active: AtomicBool::new(true) })
    }

    pub fn name(&self) -> &str { &self.name }
    pub fn generation(&self) -> u32 { self.generation }
    pub fn readiness_fd(&self) -> RawFd { self.fd.as_raw_fd() }
    pub fn begin_stop(&self) { self.active.store(false, Ordering::Release); }

    pub fn read_ip(&self, packet: &mut [u8]) -> io::Result<usize> {
        if !self.active.load(Ordering::Acquire) { return Err(io::ErrorKind::BrokenPipe.into()); }
        if packet.is_empty() { return Err(io::ErrorKind::InvalidInput.into()); }
        let count = unsafe { read(self.fd.as_raw_fd(), packet.as_mut_ptr().cast(), packet.len()) };
        if count < 0 { Err(io::Error::last_os_error()) } else { Ok(count as usize) }
    }
    /// Only the authenticated data owner can call this after remote AEAD +
    /// valid leased-address checks; kernel copy is NOT a delivery receipt.
    pub fn write_authenticated_ip(&self, packet: &[u8]) -> io::Result<usize> {
        if !self.active.load(Ordering::Acquire) { return Err(io::ErrorKind::BrokenPipe.into()); }
        if packet.is_empty() { return Err(io::ErrorKind::InvalidInput.into()); }
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
