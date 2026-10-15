//! Linux AF_PACKET RX *metadata/ownership contract*, not a live reader.
//!
//! The only real raw-socket receive in this module is a test-only, protocol-0
//! (inactive), never-bound loopback preflight FD. In production this module
//! ONLY validates untrusted sockaddr_ll metadata and a complete packet slice.
//! No physical interface capture, no promiscuity, no BPF installation, no
//! UDP fallback and no Go V4 activation. Future live RX needs M0 authority.
//!
//! Linux packet(7) sockaddr_ll wire ABI is audited on x86_64 GNU. The
//! sockaddr data is untrusted until every field has passed the trusted
//! preflight snapshot, length, generation and packet type tests. Passing
//! these checks is NOT AEAD authentication, PN replay, or business delivery.
use crate::linux_packet_preflight::{PacketSnapshot, PreflightError, RxFrameMeta, validate_rx_metadata};
use crate::rx_ipv4_tcp::{parse_data_packet, RxError, TrustedRx, UnauthenticatedData};
use std::ffi::c_int;

const AF_PACKET: u16 = 17;
const ETH_P_IP: u16 = 0x0800;
const PACKET_HOST: u8 = 0;
const SOCKADDR_LL_SIZE: usize = 20;

/// Fixed-capacity, kernel-written sockaddr_ll; do not deserialize an arbitrary
/// Rust struct directly from network bytes. This is the Linux host ABI only.
#[repr(C)]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SockAddrLl {
    pub family:u16,
    /// Network byte order, as in Linux sockaddr_ll.sll_protocol.
    pub protocol_be:u16,
    pub ifindex:i32,
    pub hatype:u16,
    pub packet_type:u8,
    pub hardware_addr_len:u8,
    pub hardware_addr:[u8;8],
}
impl SockAddrLl {
    pub const fn zero()->Self {
        Self{family:0,protocol_be:0,ifindex:0,hatype:0,packet_type:0,
            hardware_addr_len:0,hardware_addr:[0;8]}
    }
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RawReceiveMetadata {
    pub sockaddr:SockAddrLl,
    pub sockaddr_len:usize,
    pub captured_len:usize,
    pub original_len:usize,
    pub msg_flags:c_int,
    pub generation:u32,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RawRxError {
    MissingSockaddr,
    WrongFamily,
    InvalidHardwareAddress,
    WrongInterface,
    WrongProtocol,
    WrongPacketType,
    Truncated,
    LengthOrMtu,
    StaleGeneration,
    InvalidCarrier(RxError),
}
/// Pure sockaddr and truncation classifier. `MSG_TRUNC` can be set on
/// recvmmsg/recvmsg and the kernel may also return original length > capacity.
/// BOTH reject, even if the copied prefix looks like a complete IPv4 packet.
///
/// For packet-socket SOCK_RAW the reported length can include L2 bytes.
/// This contract deliberately requires the caller to provide the separated
/// complete L3 payload length; it never guesses an Ethernet/VLAN offset.
/// Actual L2 decoding and live socket configuration are NOT implemented.
pub fn validate_sockaddr(
    snapshot:PacketSnapshot,received:RawReceiveMetadata,
)->Result<(),RawRxError>{
    if received.generation!=snapshot.generation||snapshot.generation==0 {
        return Err(RawRxError::StaleGeneration);
    }
    if received.sockaddr_len!=SOCKADDR_LL_SIZE {
        return Err(RawRxError::MissingSockaddr);
    }
    let a=received.sockaddr;
    if a.family!=AF_PACKET{return Err(RawRxError::WrongFamily);}
    if a.hardware_addr_len>8{return Err(RawRxError::InvalidHardwareAddress);}
    if a.ifindex<=0||a.ifindex as u32!=snapshot.ifindex{
        return Err(RawRxError::WrongInterface);
    }
    if u16::from_be(a.protocol_be)!=ETH_P_IP||snapshot.protocol!=ETH_P_IP{
        return Err(RawRxError::WrongProtocol);
    }
    if a.packet_type!=PACKET_HOST||snapshot.packet_type!=PACKET_HOST{
        return Err(RawRxError::WrongPacketType);
    }
    if received.msg_flags & 0x28 != 0 || received.original_len>received.captured_len {
        // MSG_TRUNC(0x20) / MSG_CTRUNC(0x08).
        return Err(RawRxError::Truncated);
    }
    if received.captured_len!=received.original_len ||
       received.captured_len<40 ||
       received.captured_len>snapshot.mtu as usize {
        return Err(RawRxError::LengthOrMtu);
    }
    validate_rx_metadata(snapshot,RxFrameMeta{
        ifindex:a.ifindex as u32,protocol:ETH_P_IP,packet_type:a.packet_type,
        generation:received.generation,
        captured_l3_len:received.captured_len,
        wire_l3_len:received.original_len,
        truncated:false,
    }).map_err(|e|match e{
        PreflightError::StaleGeneration=>RawRxError::StaleGeneration,
        PreflightError::Truncated=>RawRxError::Truncated,
        _=>RawRxError::LengthOrMtu,
    })
}

/// Parse exactly the verified full L3 region; the borrow is *untrusted*
/// ciphertext and is not an authenticated record. No async lifetime is held.
pub fn parse_received<'a>(
    snapshot:PacketSnapshot,received:RawReceiveMetadata,wire:&'a [u8],
    cold:TrustedRx<'_>
)->Result<UnauthenticatedData<'a>,RawRxError>{
    validate_sockaddr(snapshot,received)?;
    if wire.len()!=received.captured_len {
        return Err(RawRxError::LengthOrMtu);
    }
    parse_data_packet(wire,cold).map_err(RawRxError::InvalidCarrier)
}

#[cfg(test)]
mod tests{
    use super::*;
    use crate::linux_packet_preflight::{open_preflight, effective_cap_net_raw, interface_index, PacketConfig,PacketPreflightFd};
    use crate::ipv4_tcp::{Ipv4Tuple,PacketPersona};
    use std::ffi::{c_int,c_uint,c_void};
    use std::io;
    use std::mem::{size_of,offset_of};
    use std::ptr;
    use std::sync::{Arc,Barrier,atomic::{AtomicUsize,Ordering}};
    use std::time::Instant;
    use crate::r1::{BorrowFence,StopResult};
    use std::os::fd::AsRawFd;

    const MSG_DONTWAIT:c_int=0x40;
    const MSG_TRUNC:c_int=0x20;
    const MSG_CTRUNC:c_int=0x08;
    const EAGAIN:i32=11;
    const EINTR:i32=4;
    const EPERM:i32=1;
    const MAX:usize=32;
    #[repr(C)]
    #[derive(Clone,Copy)]
    struct CIovec {base:*mut c_void,len:usize}
    impl CIovec{const fn zero()->Self{Self{base:ptr::null_mut(),len:0}}}
    #[repr(C)]
    #[derive(Clone,Copy)]
    struct CMsghdr {
        name:*mut c_void,name_len:u32,
        iov:*mut CIovec,iov_len:usize,
        control:*mut c_void,control_len:usize,flags:c_int,
    }
    impl CMsghdr {
        const fn zero()->Self{
            Self{name:ptr::null_mut(),name_len:0,iov:ptr::null_mut(),iov_len:0,
                control:ptr::null_mut(),control_len:0,flags:0}
        }
    }
    #[repr(C)]
    #[derive(Clone,Copy)]
    struct CMmsghdr{hdr:CMsghdr,len:c_uint}
    impl CMmsghdr{const fn zero()->Self{Self{hdr:CMsghdr::zero(),len:0}}}
    unsafe extern "C" {
        fn recvmmsg(fd:c_int,v:*mut CMmsghdr,n:c_uint,flags:c_int,timeout:*mut c_void)->c_int;
    }
    #[derive(Clone,Copy,Debug,Eq,PartialEq)]
    enum InertStatus {
        Empty, WouldBlock, Interrupted, UnexpectedPacket, Stopping,
        BadBuffer, Other(i32),
    }
    // Test only: NEVER activate the protocol-zero socket. On successful
    // recv (>0) QUARANTINE contents; do not parse/read/copy/print payload.
    fn receive_inactive<const N:usize>(
        socket:&PacketPreflightFd,
        caller_gen:u32,
        slots:&mut [&mut [u8];N],
    )->InertStatus{
        if N==0{return InertStatus::Empty;}
        if slots[..N.min(MAX)].iter().any(|s|s.is_empty()){return InertStatus::BadBuffer;}
        let loan=match socket.borrow(caller_gen){
            Ok(b)=>b,
            Err(PreflightError::Stopping)=>return InertStatus::Stopping,
            Err(_)=>return InertStatus::Other(EPERM),
        };
        let mut iov=[CIovec::zero();MAX];
        let mut sockaddr=[SockAddrLl::zero();MAX];
        let mut hdr=[CMmsghdr::zero();MAX];
        for (i,s) in slots.iter_mut().take(MAX).enumerate(){
            iov[i]=CIovec{base:s.as_mut_ptr().cast::<c_void>(),len:s.len()};
            hdr[i].hdr.name=ptr::addr_of_mut!(sockaddr[i]).cast::<c_void>();
            hdr[i].hdr.name_len=SOCKADDR_LL_SIZE as u32;
            hdr[i].hdr.iov=ptr::addr_of_mut!(iov[i]);
            hdr[i].hdr.iov_len=1;
        }
        // SAFETY: <=32 stack-stable kernel writable buffers, owned sock FD
        // kept live by `loan`, protocol zero remains INERT, MSG_DONTWAIT
        // gives no wait, null timeout. No pointer outlives this call.
        let n=unsafe{recvmmsg(loan.test_only_inert_raw_fd(),hdr.as_mut_ptr(),
            N.min(MAX) as u32,MSG_DONTWAIT|MSG_TRUNC,ptr::null_mut())};
        if n<0{
            let errno=io::Error::last_os_error().raw_os_error().unwrap_or(5);
            match errno {
                EAGAIN=>InertStatus::WouldBlock,
                EINTR=>InertStatus::Interrupted,
                e=>InertStatus::Other(e),
            }
        }else if n==0 {InertStatus::UnexpectedPacket}
        else{
            // Intentionally never expose captured bytes from any unexpected
            // positive count, even if an OS violates protocol-zero behavior.
            InertStatus::UnexpectedPacket
        }
    }
    fn cfg()->PacketConfig<'static>{
        PacketConfig{ifname:"lo",ifindex:interface_index("lo").unwrap(),
            protocol:ETH_P_IP,packet_type:PACKET_HOST,mtu:1500,generation:42}
    }
    fn sample()->(PacketSnapshot,RawReceiveMetadata){
        let snap=PacketSnapshot{ifindex:3,protocol:ETH_P_IP,
            packet_type:PACKET_HOST,mtu:1500,generation:42};
        let mut addr=SockAddrLl::zero();
        addr.family=AF_PACKET;addr.protocol_be=ETH_P_IP.to_be();
        addr.ifindex=3;addr.packet_type=PACKET_HOST;addr.hardware_addr_len=6;
        let meta=RawReceiveMetadata{sockaddr:addr,sockaddr_len:20,
            captured_len:46,original_len:46,msg_flags:0,generation:42};
        (snap,meta)
    }
    fn golden()->Vec<u8>{
        let s="4500002e0015400040064e31c0000228c6336428a7f801bb00000064000000c850180400cc2900007265636f7264";
        (0..s.len()).step_by(2).map(|i|u8::from_str_radix(&s[i..i+2],16).unwrap()).collect()
    }
    fn cold()->TrustedRx<'static>{
        TrustedRx{tuple:Ipv4Tuple{src_ip:&[192,0,2,40],dst_ip:&[198,51,100,40],
            src_port:43000,dst_port:443},
            persona:PacketPersona::Legacy,mtu:1500,
            authenticated_options:None}
    }
    #[test]
    fn r1_raw_rx_sockaddr_ll_and_mmsghdr_abi_native(){
        assert_eq!(size_of::<SockAddrLl>(),20);
        assert_eq!(offset_of!(SockAddrLl,ifindex),4);
        assert_eq!(offset_of!(SockAddrLl,packet_type),10);
        assert_eq!(offset_of!(SockAddrLl,hardware_addr),12);
        assert_eq!(size_of::<CIovec>(),16);
        assert_eq!(size_of::<CMsghdr>(),56);
        assert_eq!(size_of::<CMmsghdr>(),64);
        assert_eq!(offset_of!(CMmsghdr,len),56);
        assert_eq!((MSG_DONTWAIT,MSG_TRUNC,MSG_CTRUNC),(64,32,8));
    }
    #[test]
    fn r1_raw_rx_sockaddr_good_and_strict_ciphertext_no_auth(){
        let (s,m)=sample();
        assert_eq!(validate_sockaddr(s,m),Ok(()));
        let wire=golden();
        let v=parse_received(s,m,&wire,cold()).unwrap();
        assert_eq!(v.ciphertext,b"record");
        assert_eq!(v.seq32,100);
        // No method to deliver, decrypt or confirm the packet.
    }
    #[test]
    fn r1_raw_rx_wrong_iface_proto_type_generation_fail_closed(){
        let (s,m)=sample();
        assert_eq!(validate_sockaddr(s,RawReceiveMetadata{
            sockaddr:SockAddrLl{ifindex:4,..m.sockaddr},..m
        }),Err(RawRxError::WrongInterface));
        assert_eq!(validate_sockaddr(s,RawReceiveMetadata{
            sockaddr:SockAddrLl{ifindex:0,..m.sockaddr},..m
        }),Err(RawRxError::WrongInterface));
        assert_eq!(validate_sockaddr(s,RawReceiveMetadata{
            sockaddr:SockAddrLl{family:2,..m.sockaddr},..m
        }),Err(RawRxError::WrongFamily));
        assert_eq!(validate_sockaddr(s,RawReceiveMetadata{
            sockaddr:SockAddrLl{protocol_be:0x86dd_u16.to_be(),..m.sockaddr},..m
        }),Err(RawRxError::WrongProtocol));
        for p in [1,2,3,4,5,255] {
            assert_eq!(validate_sockaddr(s,RawReceiveMetadata{
                sockaddr:SockAddrLl{packet_type:p,..m.sockaddr},..m
            }),Err(RawRxError::WrongPacketType));
        }
        assert_eq!(validate_sockaddr(s,RawReceiveMetadata{generation:41,..m}),
            Err(RawRxError::StaleGeneration));
        assert_eq!(validate_sockaddr(s,RawReceiveMetadata{
            sockaddr:SockAddrLl{hardware_addr_len:9,..m.sockaddr},..m
        }),Err(RawRxError::InvalidHardwareAddress));
    }
    #[test]
    fn r1_raw_rx_truncation_l3_mtu_and_null_sockaddr_no_parse(){
        let (s,m)=sample();
        assert_eq!(validate_sockaddr(s,RawReceiveMetadata{sockaddr_len:0,..m}),
            Err(RawRxError::MissingSockaddr));
        assert_eq!(validate_sockaddr(s,RawReceiveMetadata{msg_flags:MSG_TRUNC,..m}),
            Err(RawRxError::Truncated));
        assert_eq!(validate_sockaddr(s,RawReceiveMetadata{msg_flags:MSG_CTRUNC,..m}),
            Err(RawRxError::Truncated));
        assert_eq!(validate_sockaddr(s,RawReceiveMetadata{
            captured_len:46,original_len:60,..m
        }),Err(RawRxError::Truncated));
        assert_eq!(validate_sockaddr(s,RawReceiveMetadata{
            captured_len:45,original_len:45,..m
        }),Ok(()));
        let mut small=s;small.mtu=45;
        assert_eq!(validate_sockaddr(small,m),Err(RawRxError::LengthOrMtu));
        let mut wire=golden();wire[40]^=1;
        assert_eq!(parse_received(s,m,&wire,cold()),
            Err(RawRxError::InvalidCarrier(RxError::TcpChecksum)));
        assert_eq!(parse_received(s,m,&wire[..45],cold()),
            Err(RawRxError::LengthOrMtu));
    }
    #[test]
    fn r1_raw_rx_kernel_protocol_zero_no_ambient_capture_and_capability_gate(){
        // Existing preflight opens AF_PACKET protocol=0 only, WITHOUT bind.
        // Zero protocol receives *nothing*, even on lo. Never capture traffic.
        match open_preflight(cfg()){
            Ok(s)=>{
                assert_eq!(s.snapshot().generation,42);
                let mut a=[0xa5u8;64];
                let mut b=[a.as_mut_slice()];
                let out=receive_inactive(&s,42,&mut b);
                assert_eq!(out,InertStatus::WouldBlock);
                assert_eq!(&a,[0xa5;64]); // no packet bytes were written
                assert_eq!(s.outstanding(),0);
            }
            Err(PreflightError::PermissionDenied{errno:EPERM})=>{
                // Raw kernel RX is NOT_RUN due to missing CAP_NET_RAW.
                // The preflight still proves typed EPERM, with no UDP fallback.
                assert_eq!(open_preflight(cfg()).map(|_|()).err(),
                    Some(PreflightError::PermissionDenied{errno:EPERM}));
            }
            Err(e)=>panic!("preflight refused unexpectedly {e:?}")
        }
    }
    #[test]
    fn r1_raw_rx_kernel_bounded_32_of_33_preallocated_no_mutation(){
        // Native syscall only if cap is *genuinely* present; otherwise EPERM.
        let s=match open_preflight(cfg()){
            Ok(s)=>s,
            Err(PreflightError::PermissionDenied{errno:EPERM})=>return,
            Err(e)=>panic!("{e:?}")
        };
        let mut storage=[[0x8bu8;64];33];
        let mut refs:Vec<&mut [u8]>=storage.iter_mut().map(|x|x.as_mut_slice()).collect();
        let mut first: [&mut [u8];33]=std::array::from_fn(|_|&mut []);
        // Avoid creating aliasing &mut [] to backing bytes: copy references
        // into our stack only for this single call, never access refs meanwhile.
        for (i,x) in refs.iter_mut().enumerate(){first[i]=&mut **x;}
        assert_eq!(receive_inactive(&s,42,&mut first),InertStatus::WouldBlock);
        assert_eq!(s.outstanding(),0);
        assert!(storage.iter().flatten().all(|&b|b==0x8b));
    }
    #[test]
    fn r1_raw_rx_kernel_stop_borrow_generation_and_last_loan(){
        let s=match open_preflight(cfg()){
            Ok(s)=>s,
            Err(PreflightError::PermissionDenied{errno:EPERM})=>return,
            Err(e)=>panic!("{e:?}")
        };
        assert_eq!(s.borrow(41).err(),Some(PreflightError::StaleGeneration));
        let loan=s.borrow(42).unwrap();
        assert_eq!(s.wait_drained_until(Instant::now()),
            StopResult::Pending{outstanding:1});
        let mut a=[0xccu8;64];let mut refs=[a.as_mut_slice()];
        s.begin_stop();
        assert_eq!(receive_inactive(&s,42,&mut refs),InertStatus::Stopping);
        assert_eq!(s.outstanding(),1);
        drop(loan);
        assert_eq!(s.wait_drained_until(Instant::now()),StopResult::Drained);
        assert!(a.iter().all(|&x|x==0xcc));
    }
    #[test]
    fn r1_raw_rx_atomic_stop_registration_race_pure(){
        let fence=Arc::new(BorrowFence::default());
        let barrier=Arc::new(Barrier::new(2));
        let registered=Arc::new(AtomicUsize::new(0));
        let f=Arc::clone(&fence);let b=Arc::clone(&barrier);let n=Arc::clone(&registered);
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
    }
}
