//! PLAN029 H1704 single-shot signed Windows Wintun → Rust → independent
//! Linux UDP guest → Rust Wintun reverse qualification. This ABI is
//! compiled ONLY with an explicit non-product m0_v4_probe feature.
//! Actual product wiring must later install the same Direct branch inside
//! the ONE authenticated native TX ingress; this diagnostic is not Ready.
#![cfg(all(target_os="windows",feature="m0_v4_probe"))]

use std::ffi::c_void;
use std::io::ErrorKind;
use std::net::{Ipv4Addr,SocketAddrV4};
use std::time::{Duration,Instant};
use std::thread;
use wbd_platform::windows_native_io::{
    split_borrowed_wintun,wait_ready,ReadResult,WaitResult,WintunFns,
};
use wbd_platform::windows_direct_udp::{
    PhysicalUdpSocket,parse_owned_ipv4_udp,encode_reverse_ipv4_udp,
};

const PROBE_BYTES:&[u8]=b"p029-linux-guest-udp-wire";
const MAX_L3:usize=2048;
#[repr(C)]
#[derive(Clone,Copy)]
pub struct WbdP029OwnedDirectUdpTrialV1{
    pub version:u32,
    pub size:u32,
    pub session:usize,
    pub read_event:usize,
    pub receive:usize,
    pub release:usize,
    pub allocate:usize,
    pub send:usize,
    pub client:[u8;4],
    pub presented:[u8;4],
    pub remote:[u8;4],
    pub physical_source:[u8;4],
    pub ifindex:u32,
    pub client_port:u16,
    pub target_port:u16,
    pub inner_mtu:u32,
    pub deadline_ms:u32,
    pub current_luid:u64,
    pub current_wintun_index:u32,
    pub generation:[u8;16],
}
fn exec(c:&WbdP029OwnedDirectUdpTrialV1)->i32{
    if c.version!=1||c.size as usize!=std::mem::size_of::<WbdP029OwnedDirectUdpTrialV1>()||
       c.session==0||c.read_event==0||c.receive==0||c.release==0||
       c.allocate==0||c.send==0||c.ifindex==0||c.client_port==0||
       c.target_port==0||c.current_luid==0||c.current_wintun_index==0||
       c.generation==[0u8;16]||!(500..=12000).contains(&c.deadline_ms)||
       !(576..=1500).contains(&c.inner_mtu){
        return 1
    }
    let client=Ipv4Addr::from(c.client);
    let presented=Ipv4Addr::from(c.presented);
    let remote=Ipv4Addr::from(c.remote);
    let physical_source=Ipv4Addr::from(c.physical_source);
    if client==presented || presented==remote ||
       physical_source==client||physical_source==remote ||
       remote.is_loopback()||remote.is_unspecified()||
       presented.is_loopback()||client.is_loopback(){
        return 2
    }
    // These are the exact WINAPI function addresses pinned by the original
    // Go current-generation N4RustWintunLoan. No second session, DLL load,
    // Wintun reader or Go per-packet method is introduced.
    let funcs=unsafe{ WintunFns{
        receive:std::mem::transmute::<usize,unsafe extern "system" fn(*mut c_void,*mut u32)->*const u8>(c.receive),
        release:std::mem::transmute::<usize,unsafe extern "system" fn(*mut c_void,*const u8)>(c.release),
        allocate:std::mem::transmute::<usize,unsafe extern "system" fn(*mut c_void,u32)->*mut u8>(c.allocate),
        send:std::mem::transmute::<usize,unsafe extern "system" fn(*mut c_void,*mut u8)>(c.send),
    }};
    let (mut rx,mut tx)=match unsafe{split_borrowed_wintun(c.session,c.read_event,funcs)}{
        Ok(pair)=>pair,Err(e)=>{eprintln!("PLAN029_H1704_FIRST_ERROR stage=borrow_wintun error={e:?}");return 3}
    };
    let deadline=Instant::now()+Duration::from_millis(c.deadline_ms as u64);
    let mut incoming=[0u8;MAX_L3];
    let mut accepted=false;
    let mut tuple=None;
    while Instant::now()<deadline{
        match rx.read(&mut incoming){
            Ok(ReadResult::Frame(n))=>{
                match parse_owned_ipv4_udp(&incoming[..n],client,presented){
                    Ok(pkt) if pkt.tuple.client_port==c.client_port &&
                        pkt.tuple.target_port==c.target_port && pkt.data==PROBE_BYTES=>{
                        tuple=Some(pkt.tuple);
                        accepted=true;break;
                    }
                    // Ignore OS-driven unrelated non-probe packets on the
                    // only Wintun reader; never send them outside via Direct.
                    Ok(_)|Err(_)=>{}
                }
            }
            Ok(ReadResult::Skipped|ReadResult::NoPacket|ReadResult::EndOfStream)=>{
                match wait_ready(&[rx.event()],20){
                    Ok(WaitResult::Timeout|WaitResult::Ready(_))=>{}
                    Err(e)=>{eprintln!("PLAN029_H1704_FIRST_ERROR stage=wait_wintun error={e:?}");return 4}
                }
            }
            Err(e)=>{eprintln!("PLAN029_H1704_FIRST_ERROR stage=read_wintun error={e:?}");return 5}
        }
    }
    if !accepted{
        eprintln!("PLAN029_H1704_FIRST_ERROR stage=wintun_application_outbound_no_matching_udp");
        return 6
    }
    eprintln!("PLAN029_H1704_WINTUN_TO_RUST_INGRESS_PASS source={} presented={} client_port={} current_generation_luid={}",
        client,presented,c.client_port,c.current_luid);
    let socket=match PhysicalUdpSocket::open(physical_source,c.ifindex,
        SocketAddrV4::new(remote,c.target_port)){
        Ok(s)=>s,
        Err(e)=>{eprintln!("PLAN029_H1704_FIRST_ERROR stage=physical_socket_bind error={e:?}");return 7}
    };
    let local=match socket.local_addr(){
        Ok(v)=>v,Err(e)=>{eprintln!("PLAN029_H1704_FIRST_ERROR stage=physical_socket_local error={e:?}");return 8}
    };
    let mut sent=false;
    while Instant::now()<deadline{
        match socket.send_ready(PROBE_BYTES){
            Ok(n) if n==PROBE_BYTES.len()=>{sent=true;break}
            Err(e) if e.kind()==ErrorKind::WouldBlock=>{
                thread::sleep(Duration::from_millis(5))
            }
            e=>{eprintln!("PLAN029_H1704_FIRST_ERROR stage=physical_send result={e:?}");return 9}
        }
    }
    if !sent{
        eprintln!("PLAN029_H1704_FIRST_ERROR stage=physical_send_timeout");
        return 10
    }
    eprintln!("PLAN029_H1704_RUST_PHYSICAL_UDP_SENT source={} port={} ifindex={} remote={} remote_port={}",
        physical_source,local.port(),c.ifindex,remote,c.target_port);
    let mut response=[0u8;MAX_L3];
    let mut n=0usize;
    while Instant::now()<deadline{
        match socket.receive_ready(&mut response){
            Ok(len)=>{n=len;break}
            Err(e) if e.kind()==ErrorKind::WouldBlock=>{
                thread::sleep(Duration::from_millis(5))
            }
            Err(e)=>{eprintln!("PLAN029_H1704_FIRST_ERROR stage=physical_receive error={e}");return 11}
        }
    }
    if n==0{
        eprintln!("PLAN029_H1704_FIRST_ERROR stage=independent_linux_guest_no_reverse");
        return 12
    }
    let mut expected=Vec::with_capacity(PROBE_BYTES.len()+6);
    expected.extend_from_slice(PROBE_BYTES);
    expected.extend_from_slice(b"-reply");
    if &response[..n]!=expected{
        eprintln!("PLAN029_H1704_FIRST_ERROR stage=independent_guest_payload_mismatch bytes={n}");
        return 13
    }
    eprintln!("PLAN029_H1704_INDEPENDENT_LINUX_GUEST_REVERSE_PASS bytes={} source={}",n,remote);
    let mut out=[0u8;MAX_L3];
    let Some(tuple)=tuple else{return 14};
    let used=match encode_reverse_ipv4_udp(tuple,&response[..n],57,c.inner_mtu as usize,&mut out){
        Ok(n)=>n,Err(e)=>{eprintln!("PLAN029_H1704_FIRST_ERROR stage=reverse_packet_build error={e:?}");return 15}
    };
    // Data is complete in OUT before Windows WintunAllocateSendPacket.
    // Direct replies are not AEAD-protected tunnel DATA. The Go side owns
    // generation and release fences; this Rust half owns only this session.
    match tx.deliver_native_direct_response(&out[..used]){
        Ok(())=>{
            eprintln!("PLAN029_H1704_RUST_WINTUN_REVERSE_SUBMITTED_PASS source={} client={} bytes={} stop=caller_join_then_release",
                presented,client,used);
            0
        }
        Err(e)=>{
            eprintln!("PLAN029_H1704_FIRST_ERROR stage=wintun_reverse_send error={e:?}");
            16
        }
    }
}

/// # Safety
/// cfg points to one fully initialized pinned Windows Go lease-owned struct
/// that lives until this synchronous call returns; all four WINAPI function
/// pointers and its Wintun session are valid until Rust joins.
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_plan029_owned_udp_trial_v1(
    cfg:*const WbdP029OwnedDirectUdpTrialV1,
)->i32{
    if cfg.is_null(){return 1}
    let cfg=unsafe{*cfg};
    std::panic::catch_unwind(||exec(&cfg)).unwrap_or(99)
}
