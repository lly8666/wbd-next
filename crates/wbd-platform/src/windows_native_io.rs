//! PLAN026: real Windows Wintun/Npcap I/O primitives used by a future
//! authenticated native owner. This is the ONLY unsafe Win32/NPF island.
//!
//! The Go cold layer creates/validates the Wintun session and opens the
//! exact-BPF Npcap handles. After Go's reader is quiesced, the Rust owner
//! receives a scoped loan of the raw handles and stable DLL function addresses.
//! Go MUST keep both DLLs and all handles alive until the Rust workers join.
//! These wrappers never create a second Wintun session, release a Go handle,
//! authenticate ciphertext, infer peer ACK, or call back to Go per packet.
//! The transfer of the actual handles is deliberately NOT activated by this
//! library module alone: that requires the real protected TLS+OS owner.
use std::ffi::c_void;
use std::ptr::{self, NonNull};
use crate::{TxBatchOutcome, TxError};

const NO_MORE_ITEMS: u32 = 259;
const HANDLE_EOF: u32 = 38;
const BUFFER_OVERFLOW: u32 = 111;
const WAIT_OBJECT_0: u32 = 0;
const WAIT_TIMEOUT: u32 = 258;
const WAIT_FAILED: u32 = u32::MAX;
pub const MAX_NPF_FRAME: usize = 65_535 + 64;
pub const MAX_WAIT_HANDLES: usize = 64;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum NativeIoError {
    InvalidHandle,
    BufferTooSmall,
    InvalidFrame,
    UnsupportedEvent,
    TooManyWaitHandles,
    Driver(u32),
    CaptureFailed,
    CaptureEnded,
    Stopping,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ReadResult {
    Frame(usize),
    NoPacket,
    Skipped,
    EndOfStream,
}
/// Returned only after the Npcap borrowed bytes have been processed inside
/// the caller's synchronous callback. T cannot borrow the temporary capture.
#[derive(Debug, PartialEq, Eq)]
pub enum Captured<T> {
    Frame(T),
    NoPacket,
    Skipped,
    EndOfStream,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum WaitResult {
    Ready(usize),
    Timeout,
}

#[link(name = "kernel32")]
extern "system" {
    fn GetLastError() -> u32;
    fn CreateEventW(attributes: *const c_void, manual_reset: i32, initial_state: i32,
                    name: *const u16) -> *mut c_void;
    fn SetEvent(handle: *mut c_void) -> i32;
    fn ResetEvent(handle: *mut c_void) -> i32;
    fn CloseHandle(handle: *mut c_void) -> i32;
    fn WaitForMultipleObjects(count: u32, handles: *const usize,
                              wait_all: i32, timeout_millis: u32) -> u32;
}

fn last_error() -> NativeIoError {
    NativeIoError::Driver(unsafe { GetLastError() })
}

/// A single owner-update/stop event. Its Win32 handle belongs only to Rust,
/// unlike the Wintun read event, which must NEVER be CloseHandle'd here.
pub struct WakeEvent { handle: NonNull<c_void> }
unsafe impl Send for WakeEvent {}
unsafe impl Sync for WakeEvent {}
impl WakeEvent {
    pub fn new() -> Result<Self, NativeIoError> { Self::create(true) }
    pub fn new_auto() -> Result<Self, NativeIoError> { Self::create(false) }
    fn create(manual: bool) -> Result<Self, NativeIoError> {
        let p = unsafe { CreateEventW(ptr::null(), if manual {1} else {0}, 0, ptr::null()) };
        let handle = NonNull::new(p).ok_or_else(last_error)?;
        Ok(Self { handle })
    }
    pub fn reset(&self) -> Result<(), NativeIoError> {
        if unsafe { ResetEvent(self.handle.as_ptr()) } == 0 {
            return Err(last_error());
        }
        Ok(())
    }
    pub fn handle(&self) -> usize { self.handle.as_ptr() as usize }
    pub fn wake(&self) -> Result<(), NativeIoError> {
        if unsafe { SetEvent(self.handle.as_ptr()) } == 0 {
            return Err(last_error());
        }
        Ok(())
    }
}
impl Drop for WakeEvent {
    fn drop(&mut self) {
        unsafe { CloseHandle(self.handle.as_ptr()); }
    }
}

/// Wait on only real driver/update/deadline events; timeout_ms is computed by
/// the Rust owner from the next pending deadline (u32::MAX means indefinite).
/// The list contains raw Win32 HANDLE values, not Go pointers.
pub fn wait_ready(handles: &[usize], timeout_ms: u32) -> Result<WaitResult, NativeIoError> {
    if handles.is_empty() || handles.iter().any(|&h| h == 0) {
        return Err(NativeIoError::InvalidHandle);
    }
    if handles.len() > MAX_WAIT_HANDLES {
        return Err(NativeIoError::TooManyWaitHandles);
    }
    let status = unsafe {
        WaitForMultipleObjects(handles.len() as u32, handles.as_ptr(), 0, timeout_ms)
    };
    if status == WAIT_TIMEOUT { return Ok(WaitResult::Timeout); }
    if status == WAIT_FAILED { return Err(last_error()); }
    if status < WAIT_OBJECT_0 + handles.len() as u32 {
        return Ok(WaitResult::Ready((status - WAIT_OBJECT_0) as usize));
    }
    Err(NativeIoError::Driver(status))
}

/// Exact Windows pcap_pkthdr shape: timeval is two 32-bit LONGs under Win32
/// (including Windows x64). Npcap owns this pointer until the next read.
#[repr(C)]
pub struct PcapHeader {
    pub sec: i32,
    pub usec: i32,
    pub caplen: u32,
    pub len: u32,
}

/// Same-process Npcap function table, filled only by the original Go
/// NpcapEndpoint's already-loaded wpcap.dll (whose lifetime covers the loan).
/// Function pointers use the libpcap C ABI, *not* stdcall on x86.
#[repr(C)]
#[derive(Clone, Copy)]
pub struct NpcapFns {
    pub next_ex: unsafe extern "C" fn(
        *mut c_void, *mut *const PcapHeader, *mut *const u8) -> i32,
    pub send_packet: unsafe extern "C" fn(*mut c_void, *const u8, i32) -> i32,
    pub get_event: unsafe extern "C" fn(*mut c_void) -> *mut c_void,
    // Optional Npcap sendqueue v1; only the TX worker uses these on a
    // dedicated handle. The entire ready batch is serialized into ONE
    // reusable 16KiB driver queue rather than one syscall per frame.
    pub queue_alloc: Option<unsafe extern "C" fn(u32) -> *mut NpcapSendQueue>,
    pub queue_transmit: Option<unsafe extern "C" fn(
        *mut c_void, *mut NpcapSendQueue, i32) -> u32>,
    pub queue_destroy: Option<unsafe extern "C" fn(*mut NpcapSendQueue)>,
}

/// Native Npcap pcap_send_queue. The buffer belongs to wpcap.dll and must
/// be destroyed before the original Go loan unloads that DLL.
#[repr(C)]
pub struct NpcapSendQueue {
    pub max_len: u32,
    pub len: u32,
    pub buffer: *mut u8,
}
const NPF_QUEUE_BYTES: usize = 16 * 1024;
const NPF_QUEUE_PACKETS: usize = 8;

/// Single RX-worker use only; raw pcap_t and DLL remain owned by the Go
/// scoped handoff. The Go reader MUST have stopped before construction.
/// The struct is Send but deliberately not Sync.
pub struct NpcapRx {
    handle: NonNull<c_void>,
    fns: NpcapFns,
}
unsafe impl Send for NpcapRx {}
impl NpcapRx {
    /// # Safety
    /// handle is a live pcap_t from the correct DLL and has no concurrent
    /// pcap_next_ex reader. Go cannot pcap_close/release DLL before Rust Stop.
    pub unsafe fn from_borrowed(handle: usize, fns: NpcapFns) -> Result<Self, NativeIoError> {
        let handle = NonNull::new(handle as *mut c_void)
            .ok_or(NativeIoError::InvalidHandle)?;
        Ok(Self { handle, fns })
    }
    pub fn event(&self) -> Result<usize, NativeIoError> {
        let h = unsafe { (self.fns.get_event)(self.handle.as_ptr()) } as usize;
        if h == 0 { Err(NativeIoError::UnsupportedEvent) } else { Ok(h) }
    }
    /// Process Npcap's borrowed capture bytes synchronously, BEFORE any
    /// subsequent pcap_next_ex/dispatch/loop on the same handle. This avoids
    /// one full Ethernet-frame memcpy per RX packet. Its callback cannot
    /// return a slice borrowing this temporary data: T has no capture lifetime.
    /// The original Go cold owner keeps the live pcap_t/DLL handle pinned.
    pub fn with_frame<T, F>(&mut self, f:F)->Result<Captured<T>,NativeIoError>
    where F:FnOnce(&[u8])->T {
        let mut header: *const PcapHeader = ptr::null();
        let mut frame: *const u8 = ptr::null();
        let rc=unsafe{
            (self.fns.next_ex)(self.handle.as_ptr(),&mut header,&mut frame)
        };
        match rc{
            0=>Ok(Captured::NoPacket),
            -2=>Ok(Captured::EndOfStream),
            -1=>Err(NativeIoError::CaptureFailed),
            1=>{
                if header.is_null()||frame.is_null(){return Ok(Captured::Skipped)}
                let meta=unsafe{&*header};
                let n=meta.caplen as usize;
                if n==0||n>MAX_NPF_FRAME||meta.caplen>meta.len{
                    return Ok(Captured::Skipped)
                }
                // SAFETY: Npcap owns caplen valid bytes until the next pcap
                // read. f is called synchronously, before that next read.
                let borrowed=unsafe{std::slice::from_raw_parts(frame,n)};
                Ok(Captured::Frame(f(borrowed)))
            },
            _=>Err(NativeIoError::CaptureFailed)
        }
    }
    /// Compatibility path for callers requiring an owned scratch copy.
    /// Native Rust RX uses with_frame() instead, avoiding this packet copy.
    pub fn read(&mut self, out: &mut [u8]) -> Result<ReadResult, NativeIoError> {
        let mut header: *const PcapHeader = ptr::null();
        let mut frame: *const u8 = ptr::null();
        let rc = unsafe {
            (self.fns.next_ex)(self.handle.as_ptr(), &mut header, &mut frame)
        };
        match rc {
            0 => Ok(ReadResult::NoPacket),
            -2 => Ok(ReadResult::EndOfStream),
            -1 => Err(NativeIoError::CaptureFailed),
            1 => {
                if header.is_null() || frame.is_null() { return Ok(ReadResult::Skipped); }
                let meta = unsafe { &*header };
                let len = meta.caplen as usize;
                if len == 0 || len > MAX_NPF_FRAME || meta.caplen > meta.len {
                    return Ok(ReadResult::Skipped);
                }
                if len > out.len() { return Err(NativeIoError::BufferTooSmall); }
                unsafe { ptr::copy_nonoverlapping(frame, out.as_mut_ptr(), len) };
                Ok(ReadResult::Frame(len))
            }
            _ => Err(NativeIoError::CaptureFailed),
        }
    }
}

/// Npcap sender: a DIFFERENT pcap_t from the capture handle. A single Rust
/// TX worker serializes all lane writes, so no mutex is needed per packet.
/// No pcap_t is closed by Drop: it is part of the Go cold-layer driver lease.
pub struct NpcapTx {
    handle: NonNull<c_void>,
    fns: NpcapFns,
    queue: Option<NonNull<NpcapSendQueue>>,
}
unsafe impl Send for NpcapTx {}
impl NpcapTx {
    /// # Safety
    /// handle must be a SEPARATE live Npcap TX pcap_t. No concurrent pcap
    /// user or premature Go DLL unload. The queue belongs solely to Rust.
    pub unsafe fn from_borrowed(handle: usize, fns: NpcapFns) -> Result<Self, NativeIoError> {
        let handle = NonNull::new(handle as *mut c_void)
            .ok_or(NativeIoError::InvalidHandle)?;
        let queue = fns.queue_alloc
            .filter(|_| fns.queue_transmit.is_some() && fns.queue_destroy.is_some())
            .and_then(|allocate| NonNull::new(unsafe { allocate(NPF_QUEUE_BYTES as u32) }));
        Ok(Self { handle, fns, queue })
    }
    /// Drive all READY Ethernet frames without waiting to fill a queue.
    /// At most 8/16KiB are submitted to one NPF sendqueue call; a short
    /// return is mapped to EXACT accepted packet-end offsets. A fragment of
    /// one packet is Uncertain; never re-encrypt/retry its potentially copied
    /// bytes or infer any peer ACK from this syscall.
    pub fn send_batch(&mut self, frames: &[&[u8]]) -> TxBatchOutcome {
        let mut accepted = 0usize;
        while accepted < frames.len() {
            let mut sent_by_queue = false;
            if let (Some(ptr), Some(transmit)) =
                (self.queue, self.fns.queue_transmit)
            {
                let queue_ptr = ptr.as_ptr();
                let queue = unsafe { &mut *queue_ptr };
                if !queue.buffer.is_null() &&
                    queue.max_len as usize >= NPF_QUEUE_BYTES &&
                    frames.len() - accepted >= 2
                {
                    let scratch = unsafe {
                        std::slice::from_raw_parts_mut(queue.buffer, NPF_QUEUE_BYTES)
                    };
                    let mut ends = [0usize; NPF_QUEUE_PACKETS];
                    let mut bytes = 0usize;
                    let mut n = 0usize;
                    for frame in &frames[accepted..] {
                        if n >= NPF_QUEUE_PACKETS ||
                           frame.is_empty() || frame.len() > MAX_NPF_FRAME ||
                           frame.len() + 16 > scratch.len() - bytes {
                            break;
                        }
                        // Native Windows pcap_pkthdr: timeval 8B,
                        // caplen/len 4B each. No padding/alignment guessed.
                        scratch[bytes..bytes+8].fill(0);
                        scratch[bytes+8..bytes+12].copy_from_slice(
                            &(frame.len() as u32).to_ne_bytes());
                        scratch[bytes+12..bytes+16].copy_from_slice(
                            &(frame.len() as u32).to_ne_bytes());
                        bytes += 16;
                        scratch[bytes..bytes+frame.len()].copy_from_slice(frame);
                        bytes += frame.len();
                        ends[n] = bytes;
                        n += 1;
                    }
                    if n >= 2 {
                        queue.len = bytes as u32;
                        let copied = unsafe {
                            transmit(self.handle.as_ptr(), queue_ptr, 0)
                        } as usize;
                        queue.len = 0;
                        if copied != bytes {
                            // A driver result beyond the submitted buffer is
                            // invalid: do not credit a fabricated prefix.
                            if copied > bytes {
                                return TxBatchOutcome {
                                    accepted_prefix: accepted,
                                    uncertain_index: Some(accepted),
                                    error: Some(TxError::IoUncertain),
                                };
                            }
                            let mut confirmed = 0;
                            while confirmed < n && ends[confirmed] <= copied {
                                confirmed += 1;
                            }
                            let total = accepted + confirmed;
                            if confirmed > 0 && ends[confirmed - 1] == copied {
                                return TxBatchOutcome {
                                    accepted_prefix: total,
                                    uncertain_index: None,
                                    error: Some(TxError::IoFailed),
                                };
                            }
                            return TxBatchOutcome {
                                accepted_prefix: total,
                                uncertain_index: Some(total),
                                error: Some(TxError::IoUncertain),
                            };
                        }
                        accepted += n;
                        sent_by_queue = true;
                    }
                }
            }
            if sent_by_queue { continue; }
            // One small or oversized-for-queue ready frame: direct syscall.
            let frame = frames[accepted];
            if frame.is_empty() || frame.len() > MAX_NPF_FRAME {
                return TxBatchOutcome {
                    accepted_prefix: accepted, uncertain_index: None,
                    error: Some(TxError::IoFailed),
                };
            }
            let rc = unsafe {
                (self.fns.send_packet)(
                    self.handle.as_ptr(), frame.as_ptr(), frame.len() as i32)
            };
            if rc != 0 {
                return TxBatchOutcome {
                    accepted_prefix: accepted, uncertain_index: Some(accepted),
                    error: Some(TxError::IoUncertain),
                };
            }
            accepted += 1;
        }
        TxBatchOutcome::copied_all(accepted)
    }
}
impl Drop for NpcapTx {
    fn drop(&mut self) {
        if let (Some(queue), Some(destroy)) = (self.queue.take(), self.fns.queue_destroy) {
            unsafe { destroy(queue.as_ptr()); }
        }
    }
}

#[repr(C)]
#[derive(Clone, Copy)]
pub struct WintunFns {
    pub receive: unsafe extern "system" fn(*mut c_void, *mut u32) -> *const u8,
    pub release: unsafe extern "system" fn(*mut c_void, *const u8),
    pub allocate: unsafe extern "system" fn(*mut c_void, u32) -> *mut u8,
    pub send: unsafe extern "system" fn(*mut c_void, *mut u8),
}

/// Two independent mutable worker halves of ONE Go-created Wintun session.
/// Session, adapter and read event are never closed by Rust.
pub struct WintunRx {
    session: NonNull<c_void>,
    read_event: usize,
    fns: WintunFns,
}
pub struct WintunTx {
    session: NonNull<c_void>,
    fns: WintunFns,
}
unsafe impl Send for WintunRx {}
unsafe impl Send for WintunTx {}

/// # Safety
/// The Go network owner must have verified this exact Wintun session, its
/// OS generation and exclusive borrow. It must keep session and DLL alive
/// until both Rust halves have stopped; no second receive worker is allowed.
pub unsafe fn split_borrowed_wintun(
    session: usize, read_event: usize, fns: WintunFns,
) -> Result<(WintunRx, WintunTx), NativeIoError> {
    let s = NonNull::new(session as *mut c_void).ok_or(NativeIoError::InvalidHandle)?;
    if read_event == 0 { return Err(NativeIoError::InvalidHandle); }
    Ok((
        WintunRx { session: s, read_event, fns },
        WintunTx { session: s, fns },
    ))
}
impl WintunRx {
    pub fn event(&self) -> usize { self.read_event }
    /// Each Wintun receive loan is copied once into an owned reusable buffer
    /// and always released BEFORE returning to the worker scheduler.
    /// IPv6/non-IPv4 control frames are skipped, not fed to Rust M1.
    pub fn read(&mut self, dst: &mut [u8]) -> Result<ReadResult, NativeIoError> {
        let mut size = 0u32;
        let raw = unsafe { (self.fns.receive)(self.session.as_ptr(), &mut size) };
        if raw.is_null() {
            return match unsafe { GetLastError() } {
                NO_MORE_ITEMS => Ok(ReadResult::NoPacket),
                HANDLE_EOF => Ok(ReadResult::EndOfStream),
                code => Err(NativeIoError::Driver(code)),
            };
        }
        // Release even if a frame is malformed or exceeds the caller slab.
        let n = size as usize;
        let result = if n < 20 || n > 65_535 {
            Ok(ReadResult::Skipped)
        } else {
            let data = unsafe { std::slice::from_raw_parts(raw, n) };
            if data[0] >> 4 != 4 {
                Ok(ReadResult::Skipped)
            } else if n > dst.len() {
                Err(NativeIoError::BufferTooSmall)
            } else if ipv4_packet_size(data) != Some(n) {
                Ok(ReadResult::Skipped)
            } else {
                unsafe { ptr::copy_nonoverlapping(raw, dst.as_mut_ptr(), n) };
                Ok(ReadResult::Frame(n))
            }
        };
        unsafe { (self.fns.release)(self.session.as_ptr(), raw) };
        result
    }
}
impl WintunTx {
    /// The Rust M3 owner must authenticate and replay-check first. Wintun
    /// AllocateSendPacket always needs a matching SendPacket upon success.
    pub fn deliver_authenticated(&mut self, packet: &[u8]) -> Result<(), NativeIoError> {
        if ipv4_packet_size(packet) != Some(packet.len()) {
            return Err(NativeIoError::InvalidFrame);
        }
        let raw = unsafe { (self.fns.allocate)(self.session.as_ptr(), packet.len() as u32) };
        if raw.is_null() {
            let code = unsafe { GetLastError() };
            return if code == BUFFER_OVERFLOW {
                Err(NativeIoError::BufferTooSmall)
            } else { Err(NativeIoError::Driver(code)) };
        }
        unsafe {
            ptr::copy_nonoverlapping(packet.as_ptr(), raw, packet.len());
            (self.fns.send)(self.session.as_ptr(), raw);
        }
        Ok(())
    }
}
fn ipv4_packet_size(packet: &[u8]) -> Option<usize> {
    if packet.len() < 20 || packet.len() > 65_535 ||
       packet[0] >> 4 != 4 || (packet[0] & 15) < 5 {
        return None;
    }
    let ihl = usize::from(packet[0] & 15) * 4;
    if ihl > packet.len() { return None; }
    let total = u16::from_be_bytes([packet[2], packet[3]]) as usize;
    if total < ihl || total != packet.len() { return None; }
    Some(total)
}

/// Ethernet parser only removes the NPF link header. The trusted original
/// session must still run rx_ipv4_tcp::parse_data_packet and then AEAD/PN.
pub fn ethernet_ipv4(frame: &[u8]) -> Option<&[u8]> {
    if frame.len() < 14 { return None; }
    let mut kind = u16::from_be_bytes([frame[12], frame[13]]);
    let mut at = 14;
    for _ in 0..2 {
        if kind != 0x8100 && kind != 0x88a8 { break; }
        if frame.len() < at + 4 { return None; }
        kind = u16::from_be_bytes([frame[at + 2], frame[at + 3]]);
        at += 4;
    }
    if kind != 0x0800 || frame.len() < at + 20 { return None; }
    let packet = &frame[at..];
    // Ethernet can pad short IPv4 packets up to its minimum frame size.
    // Wintun packets themselves require exact lengths, but NPF frames do
    // not. Trim only the declared IPv4 length before the trusted TCP parser.
    if packet[0] >> 4 != 4 || (packet[0] & 15) < 5 { return None; }
    let ihl = usize::from(packet[0] & 15) * 4;
    let size = usize::from(u16::from_be_bytes([packet[2],packet[3]]));
    if size < ihl || size > packet.len() { return None; }
    Some(&packet[..size])
}
/// Outbound Ethernet frame assembly into a reused Rust slab. No heap work.
pub fn ethernet_outbound<'a>(
    ipv4: &[u8], source_mac: &[u8; 6], next_hop_mac: &[u8; 6], dst: &'a mut [u8],
) -> Result<&'a [u8], NativeIoError> {
    if ipv4_packet_size(ipv4) != Some(ipv4.len()) || dst.len() < ipv4.len() + 14 {
        return Err(NativeIoError::InvalidFrame);
    }
    dst[..6].copy_from_slice(next_hop_mac);
    dst[6..12].copy_from_slice(source_mac);
    dst[12..14].copy_from_slice(&0x0800u16.to_be_bytes());
    dst[14..ipv4.len()+14].copy_from_slice(ipv4);
    Ok(&dst[..ipv4.len()+14])
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};
    static RELEASES: AtomicUsize = AtomicUsize::new(0);
    static SENT: AtomicUsize = AtomicUsize::new(0);
    static IPV4: [u8; 20] = [
        0x45,0,0,20,0,0,0,0,64,17,0,0,1,1,1,1,2,2,2,2,
    ];
    unsafe extern "system" fn recv(_: *mut c_void, size: *mut u32) -> *const u8 {
        unsafe { *size = IPV4.len() as u32 };
        IPV4.as_ptr()
    }
    unsafe extern "system" fn release(_: *mut c_void, _: *const u8) {
        RELEASES.fetch_add(1, Ordering::SeqCst);
    }
    unsafe extern "system" fn allocate(_: *mut c_void, _: u32) -> *mut u8 {
        static mut BUFFER: [u8; 2048] = [0;2048];
        std::ptr::addr_of_mut!(BUFFER).cast::<u8>()
    }
    unsafe extern "system" fn send(_: *mut c_void, _: *mut u8) {
        SENT.fetch_add(1, Ordering::SeqCst);
    }
    #[test]
    fn receive_loan_is_released_and_ethernet_bytes_are_borrowed() {
        RELEASES.store(0, Ordering::SeqCst);
        let fns = WintunFns {receive:recv,release,allocate,send};
        let (mut rx, _) = unsafe { split_borrowed_wintun(1,2,fns).unwrap() };
        let mut buf = [0u8;128];
        assert_eq!(rx.read(&mut buf), Ok(ReadResult::Frame(20)));
        assert_eq!(&buf[..20], &IPV4);
        assert_eq!(RELEASES.load(Ordering::SeqCst), 1);
        let mut frame = [0u8;128];
        let enc = ethernet_outbound(&IPV4,&[4;6],&[8;6],&mut frame).unwrap();
        assert_eq!(ethernet_ipv4(enc),Some(IPV4.as_slice()));
        frame[12..14].copy_from_slice(&0x8100u16.to_be_bytes());
        frame[14..18].copy_from_slice(&[0,1,0x08,0]);
        frame[18..38].copy_from_slice(&IPV4);
        assert_eq!(ethernet_ipv4(&frame[..38]),Some(IPV4.as_slice()));
        // Genuine NPF receives may include Ethernet minimum-length padding.
        frame[12..14].copy_from_slice(&0x0800u16.to_be_bytes());
        frame[14..34].copy_from_slice(&IPV4);
        frame[34..60].fill(0);
        assert_eq!(ethernet_ipv4(&frame[..60]),Some(IPV4.as_slice()));
    }
    #[test]
    fn outbound_requires_complete_ipv4_and_real_wintun_send() {
        SENT.store(0, Ordering::SeqCst);
        let fns = WintunFns {receive:recv,release,allocate,send};
        let (_,mut tx) = unsafe { split_borrowed_wintun(1,2,fns).unwrap() };
        assert_eq!(tx.deliver_authenticated(&IPV4),Ok(()));
        assert_eq!(SENT.load(Ordering::SeqCst),1);
        assert_eq!(tx.deliver_authenticated(&IPV4[..10]),Err(NativeIoError::InvalidFrame));
        assert_eq!(SENT.load(Ordering::SeqCst),1);
    }
    unsafe extern "C" fn next_ex(_: *mut c_void,
        hdr:*mut *const PcapHeader, bytes:*mut *const u8) -> i32 {
        static HDR:PcapHeader = PcapHeader { sec:0,usec:0,caplen:20,len:20 };
        unsafe { *hdr = &HDR; *bytes = IPV4.as_ptr() };
        1
    }
    unsafe extern "C" fn send_packet(_: *mut c_void, _: *const u8, _: i32)->i32 {0}
    unsafe extern "C" fn get_event(_: *mut c_void)->*mut c_void { 3 as *mut c_void }
    static SEND_CALLS: AtomicUsize = AtomicUsize::new(0);
    unsafe extern "C" fn send_partial(_: *mut c_void, _: *const u8, _: i32)->i32 {
        if SEND_CALLS.fetch_add(1, Ordering::SeqCst)==1 {-1}else{0}
    }
    #[test]
    fn partial_npf_send_is_uncertain_and_suffix_not_attempted() {
        SEND_CALLS.store(0, Ordering::SeqCst);
        let fns=NpcapFns {next_ex,send_packet:send_partial,get_event,queue_alloc:None,queue_transmit:None,queue_destroy:None};
        let mut tx=unsafe{NpcapTx::from_borrowed(2,fns).unwrap()};
        let result=tx.send_batch(&[&IPV4[..],&IPV4[..],&IPV4[..]]);
        assert_eq!(result.classify(3).unwrap(),vec![
            crate::TxDisposition::Accepted,
            crate::TxDisposition::Uncertain,
            crate::TxDisposition::NotAttempted,
        ]);
        assert_eq!(SEND_CALLS.load(Ordering::SeqCst),2);
    }
    static QUEUE_COPIES: AtomicUsize = AtomicUsize::new(0);
    static QUEUE_BYTES: AtomicUsize = AtomicUsize::new(0);
    static QUEUE_FREES: AtomicUsize = AtomicUsize::new(0);
    unsafe extern "C" fn queue_alloc(_: u32) -> *mut NpcapSendQueue {
        let backing = Box::into_raw(Box::new([0u8; NPF_QUEUE_BYTES]));
        Box::into_raw(Box::new(NpcapSendQueue {
            max_len: NPF_QUEUE_BYTES as u32,
            len: 0, buffer: backing.cast::<u8>(),
        }))
    }
    unsafe extern "C" fn queue_transmit(
        _: *mut c_void, queue: *mut NpcapSendQueue, _: i32,
    ) -> u32 {
        let len = unsafe { (*queue).len } as usize;
        QUEUE_BYTES.store(len, Ordering::SeqCst);
        QUEUE_COPIES.fetch_add(1, Ordering::SeqCst);
        (16 + IPV4.len() + 3) as u32
    }
    unsafe extern "C" fn queue_destroy(queue: *mut NpcapSendQueue) {
        let q = unsafe { Box::from_raw(queue) };
        unsafe { drop(Box::from_raw(q.buffer.cast::<[u8; NPF_QUEUE_BYTES]>())); }
        QUEUE_FREES.fetch_add(1, Ordering::SeqCst);
    }
    #[test]
    fn native_sendqueue_partial_bytes_map_to_one_uncertain_packet() {
        QUEUE_COPIES.store(0, Ordering::SeqCst);
        QUEUE_FREES.store(0, Ordering::SeqCst);
        let fns = NpcapFns {
            next_ex,send_packet,get_event,
            queue_alloc:Some(queue_alloc),
            queue_transmit:Some(queue_transmit),
            queue_destroy:Some(queue_destroy),
        };
        let mut tx=unsafe { NpcapTx::from_borrowed(2,fns).unwrap() };
        let batch=tx.send_batch(&[&IPV4[..],&IPV4[..],&IPV4[..]]);
        assert_eq!(batch.classify(3).unwrap(),vec![
            crate::TxDisposition::Accepted,
            crate::TxDisposition::Uncertain,
            crate::TxDisposition::NotAttempted,
        ]);
        assert_eq!(QUEUE_COPIES.load(Ordering::SeqCst),1);
        assert_eq!(QUEUE_BYTES.load(Ordering::SeqCst),3*(16+IPV4.len()));
        drop(tx);
        assert_eq!(QUEUE_FREES.load(Ordering::SeqCst),1);
    }
    #[test]
    fn borrowed_capture_callback_reads_in_place_without_copy_or_lifetime_escape(){
        let fns=NpcapFns {next_ex,send_packet,get_event,queue_alloc:None,
            queue_transmit:None,queue_destroy:None};
        let mut rx=unsafe{NpcapRx::from_borrowed(1,fns).unwrap()};
        let mut invoked=0usize;
        let result=rx.with_frame(|bytes|{
            invoked+=1;
            assert_eq!(bytes.as_ptr(),IPV4.as_ptr());
            assert_eq!(bytes,&IPV4);
            // Owned scalar result only, not a borrowed slice.
            bytes.len()
        });
        assert_eq!(result,Ok(Captured::Frame(20)));
        assert_eq!(invoked,1);
    }
    unsafe extern "C" fn invalid_capture(_: *mut c_void,
        hdr:*mut *const PcapHeader,bytes:*mut *const u8)->i32 {
        static BAD:PcapHeader=PcapHeader{sec:0,usec:0,caplen:30,len:20};
        unsafe{*hdr=&BAD;*bytes=IPV4.as_ptr()};
        1
    }
    #[test]
    fn borrowed_capture_rejects_inconsistent_caplen_before_callback(){
        let fns=NpcapFns {next_ex:invalid_capture,send_packet,get_event,
            queue_alloc:None,queue_transmit:None,queue_destroy:None};
        let mut rx=unsafe{NpcapRx::from_borrowed(1,fns).unwrap()};
        let mut called=false;
        assert_eq!(rx.with_frame(|_|{called=true}),Ok(Captured::Skipped));
        assert!(!called);
    }
    #[test]
    fn captured_frame_copied_into_owner_scratch_and_send_prefix() {
        let fns = NpcapFns {next_ex,send_packet,get_event,queue_alloc:None,queue_transmit:None,queue_destroy:None};
        let mut rx = unsafe {NpcapRx::from_borrowed(1,fns).unwrap()};
        let mut dst = [0u8; 100];
        assert_eq!(rx.event(),Ok(3));
        assert_eq!(rx.read(&mut dst),Ok(ReadResult::Frame(20)));
        assert_eq!(&dst[..20], &IPV4);
        let mut tx = unsafe {NpcapTx::from_borrowed(2,fns).unwrap()};
        assert_eq!(tx.send_batch(&[&IPV4[..],&IPV4[..]]).classify(2).unwrap(),
            vec![crate::TxDisposition::Accepted,crate::TxDisposition::Accepted]);
        assert_eq!(tx.send_batch(&[&IPV4[..],&[]]).classify(2).unwrap(),
            vec![crate::TxDisposition::Accepted,crate::TxDisposition::NotAttempted]);
    }
}
