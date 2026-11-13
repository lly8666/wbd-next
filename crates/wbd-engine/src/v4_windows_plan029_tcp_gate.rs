//! PLAN029 H1706 one-shot independent-Linux TCP *diagnostic*.
#![cfg(all(target_os="windows",feature="m0_v4_probe"))]
use std::ffi::c_void;
use std::net::{Ipv4Addr,SocketAddr,SocketAddrV4,TcpListener,TcpStream};
use std::io::ErrorKind;
use std::thread;
use std::time::{Duration,Instant};
use wbd_platform::windows_native_io::{
    split_borrowed_wintun,WintunFns,ReadResult,
};
use wbd_platform::windows_direct_tcp::{
    PhysicalTcpSocket,ConnectProgress,TcpDirectRelay,
};
use crate::v4_client_direct_tcp_nat::DirectTcpNat;

#[repr(C)]
#[derive(Clone,Copy)]
pub struct WbdP029OwnedDirectTcpTrialV1{
    pub version:u32,pub size:u32,
    pub session:usize,pub read_event:usize,
    pub receive:usize,pub release:usize,
    pub allocate:usize,pub send:usize,
    pub client:[u8;4],pub presented:[u8;4],
    pub synthetic:[u8;4],pub remote:[u8;4],
    pub physical_source:[u8;4],pub ifindex:u32,
    pub listener_port:u16,pub remote_port:u16,
    pub inner_mtu:u32,pub deadline_ms:u32,
    pub current_luid:u64,pub current_wintun_index:u32,
    pub generation:[u8;16],
}
fn run(c:&WbdP029OwnedDirectTcpTrialV1)->i32{
    if c.version!=1||c.size as usize!=std::mem::size_of::<WbdP029OwnedDirectTcpTrialV1>()||
      c.session==0||c.read_event==0||c.receive==0||c.release==0||
      c.allocate==0||c.send==0||c.ifindex==0||c.current_luid==0||
      c.current_wintun_index==0||c.generation==[0;16]||
      !(576..=1500).contains(&c.inner_mtu)||
      !(500..=20000).contains(&c.deadline_ms)||
      c.listener_port==0||c.remote_port==0{return 1}
    let client=Ipv4Addr::from(c.client);
    let synthetic=Ipv4Addr::from(c.synthetic);
    let presented=Ipv4Addr::from(c.presented);
    let guest=Ipv4Addr::from(c.remote);
    let physical_source=Ipv4Addr::from(c.physical_source);
    if client==synthetic||client==presented||guest==presented||
       guest.is_loopback()||physical_source==guest{return 2}
    let funs=unsafe{WintunFns{
      receive:std::mem::transmute::<usize,unsafe extern "system" fn(*mut c_void,*mut u32)->*const u8>(c.receive),
      release:std::mem::transmute::<usize,unsafe extern "system" fn(*mut c_void,*const u8)>(c.release),
      allocate:std::mem::transmute::<usize,unsafe extern "system" fn(*mut c_void,u32)->*mut u8>(c.allocate),
      send:std::mem::transmute::<usize,unsafe extern "system" fn(*mut c_void,*mut u8)>(c.send),
    }};
    let (mut rx,mut tx)=match unsafe{split_borrowed_wintun(c.session,c.read_event,funs)}{
      Ok(p)=>p,Err(e)=>{eprintln!("PLAN029_H1706_FIRST_ERROR borrow_wintun {e:?}");return 3}
    };
    let listener=match TcpListener::bind(SocketAddrV4::new(client,c.listener_port)){
      Ok(s)=>s,Err(e)=>{
        eprintln!("PLAN029_H1706_FIRST_ERROR real_kernel_listener_bind {e}");
        return 4
      }
    };
    if listener.set_nonblocking(true).is_err(){return 5}
    eprintln!("PLAN029_H1706_REAL_WINDOWS_KERNEL_LISTENER_READY local={}:{}",client,c.listener_port);
    let mut nat=match DirectTcpNat::new(u32::from_be_bytes(c.client),
      u32::from_be_bytes(c.synthetic),c.listener_port,64){
      Ok(n)=>n,Err(e)=>{eprintln!("PLAN029_H1706_FIRST_ERROR NAT config {e:?}");return 6}
    };
    let mut scratch=[0u8;2048];
    let mut rewritten=[0u8;2048];
    let deadline=Instant::now()+Duration::from_millis(c.deadline_ms as u64);
    let mut app_packets=0usize;
    let mut reverse_packets=0usize;
    let mut accepted:Option<TcpStream>=None;
    let mut physical:Option<PhysicalTcpSocket>=None;
    let mut relay:Option<TcpDirectRelay>=None;
    let mut nat_port=0u16;
    // The native two-leg socket relay reaching EOF is NOT sufficient to
    // finish a Wintun TCP flow: the Windows kernel still has to emit its
    // outbound FIN, and the sole Rust RX owner must translate and submit
    // that FIN to the original application. H1708 delivered the complete
    // payload but exited before this final kernel packet was observed.
    let mut client_fin_seen=false;
    let mut reverse_fin_submitted=false;
    let mut relay_done=false;
    loop {
      if Instant::now()>=deadline{break}
      for _ in 0..8{
        match rx.read(&mut scratch){
          Ok(ReadResult::Frame(n))=>{
            let p=&scratch[..n];
            if n<40||p[9]!=6{continue}
            let ihl=usize::from(p[0]&15)*4;
            if ihl<20||ihl+20>n{continue}
            let flags=p[ihl+13];
            let from=u32::from_be_bytes(p[12..16].try_into().unwrap());
            let to=u32::from_be_bytes(p[16..20].try_into().unwrap());
            let source_port=u16::from_be_bytes([p[20],p[21]]);
            if from==u32::from_be_bytes(c.client)&&
               to==u32::from_be_bytes(c.presented){
              match nat.to_listener(p,u32::from_be_bytes(c.remote),0,&mut rewritten){
                Ok((bytes,entry))=>{
                  if flags&0x01!=0{client_fin_seen=true;}
                  nat_port=entry.proxy_port;
                  if let Err(e)=tx.deliver_native_direct_response(&rewritten[..bytes]){
                    eprintln!("PLAN029_H1706_FIRST_ERROR native_wintun_nat_to_listener {e:?}");
                    return 7
                  }
                  app_packets+=1;
                  if app_packets==1{
                    eprintln!("PLAN029_H1706_APP_SYN_TO_RUST_NAT_LISTENER_PASS nat_port={} src={} dst={} guest_real={}",
                      nat_port,synthetic,client,guest);
                  }
                }
                Err(e)=>{eprintln!("PLAN029_H1706_FIRST_ERROR NAT_to_listener {e:?}");return 8}
              }
            }else if from==u32::from_be_bytes(c.client)&&
              to==u32::from_be_bytes(c.synthetic)&&source_port==c.listener_port{
              match nat.to_app(p,&mut rewritten){
                Ok((bytes,_))=>{
                  if let Err(e)=tx.deliver_native_direct_response(&rewritten[..bytes]){
                    eprintln!("PLAN029_H1706_FIRST_ERROR native_wintun_nat_reverse {e:?}");
                    return 9
                  }
                  reverse_packets+=1;
                  if flags&0x01!=0{
                    reverse_fin_submitted=true;
                    eprintln!("PLAN029_H1709_KERNEL_TCP_FIN_WINTUN_REVERSE_SUBMITTED nat_port={nat_port} packet={reverse_packets}");
                  }
                  if reverse_packets==1{
                    eprintln!("PLAN029_H1706_KERNEL_SYNACK_REVERSE_TO_ORIGINAL_APP_PASS nat_port={nat_port}");
                  }
                }
                Err(e)=>{eprintln!("PLAN029_H1706_FIRST_ERROR NAT_to_app {e:?}");return 10}
              }
            }
          }
          Ok(ReadResult::NoPacket|ReadResult::Skipped|ReadResult::EndOfStream)=>break,
          Err(e)=>{eprintln!("PLAN029_H1706_FIRST_ERROR wintun_read {e:?}");return 11}
        }
      }
      if accepted.is_none()&&physical.is_none()&&relay.is_none(){
        match listener.accept(){
          Ok((stream,peer))=>{
            let addr=match peer{SocketAddr::V4(a)=>a,_=>return 12};
            let Some(e)=nat.accepted(u32::from(*addr.ip()),addr.port())else{
              eprintln!("PLAN029_H1706_FIRST_ERROR native_TCP_accept_not_owned_nat_peer {addr}");
              return 13
            };
            if e.real_dst!=u32::from_be_bytes(c.remote){
              eprintln!("PLAN029_H1706_FIRST_ERROR guest_target_mismatch");
              return 14
            }
            eprintln!("PLAN029_H1706_REAL_KERNEL_SYN_ACCEPT_PASS peer={} port={}",addr.ip(),addr.port());
            accepted=Some(stream);
            match PhysicalTcpSocket::start(physical_source,c.ifindex,
              SocketAddrV4::new(guest,c.remote_port)){
              Ok(sock)=>physical=Some(sock),
              Err(e)=>{eprintln!("PLAN029_H1706_FIRST_ERROR physical_tcp_socket_create {e:?}");return 15}
            }
          }
          Err(e) if e.kind()==ErrorKind::WouldBlock=>{}
          Err(e)=>{eprintln!("PLAN029_H1706_FIRST_ERROR kernel_accept {e}");return 16}
        }
      }
      if relay.is_none(){
        if let Some(socket)=physical.as_mut(){
          match socket.poll_connected(){
            Ok(ConnectProgress::Pending)=>{}
            Ok(ConnectProgress::Connected)=>{
              let socket=physical.take().unwrap();
              let outer=match socket.into_connected_stream(){
                Ok(stream)=>stream,Err(e)=>{eprintln!("PLAN029_H1706_FIRST_ERROR socket_take {e:?}");return 17}
              };
              let inner=accepted.take().unwrap();
              match TcpDirectRelay::new(inner,outer){
                Ok(pair)=>relay=Some(pair),
                Err(e)=>{eprintln!("PLAN029_H1706_FIRST_ERROR start_two_leg_relay {e:?}");return 18}
              }
              eprintln!("PLAN029_H1706_PHYSICAL_BOUND_TCP_INDEPENDENT_GUEST_CONNECTED source={} ifindex={} guest={}:{}",physical_source,c.ifindex,guest,c.remote_port);
            }
            Err(e)=>{eprintln!("PLAN029_H1706_FIRST_ERROR nonblocking_connect {e:?}");return 19}
          }
        }
      }
      if let Some(pair)=relay.as_mut(){
        if !relay_done {
          match pair.service_once(){
            Ok(tick) if tick.finished=>{
              relay_done=true;
              eprintln!("PLAN029_H1709_TWO_NATIVE_TCP_LEGS_EOF_DRAIN_PENDING app_packets={} reverse_packets={} guest={}",app_packets,reverse_packets,guest);
            }
            Ok(_)=>{}
            Err(e)=>{eprintln!("PLAN029_H1706_FIRST_ERROR relay_service {e:?}");return 21}
          }
        }
      }
      if relay_done&&client_fin_seen&&reverse_fin_submitted&&
          app_packets>=2&&reverse_packets>=2{
          eprintln!("PLAN029_H1709_NATIVE_FIN_SUBMITTED_AFTER_TWO_LEG_EOF_PASS app_packets={} reverse_packets={} guest={}",app_packets,reverse_packets,guest);
          return 0
      }
      // This is a single isolated test gate, NOT the production steady
      // loop. Production schedules readiness with bounded WSAPoll/IOCP;
      // no borrowed RX packet or Wintun Allocate slot crosses this sleep.
      thread::sleep(Duration::from_millis(3))
    }
    eprintln!("PLAN029_H1709_FIRST_ERROR deadline app_packets={} reverse={} native_accept={} physical_connected={} client_fin={} reverse_fin={} relay_eof={}",
        app_packets,reverse_packets,accepted.is_some()||relay.is_some(),
        relay.is_some(),client_fin_seen,reverse_fin_submitted,relay_done);
    22
}
/// # Safety
/// Borrowed original Windows Wintun session/funcs and generation are pinned
/// by a Go N4OriginalKernelPacketLease until this entire call returns.
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_plan029_owned_tcp_trial_v1(
    cfg:*const WbdP029OwnedDirectTcpTrialV1,
)->i32{
    if cfg.is_null(){return 1}
    let cfg=unsafe{*cfg};
    std::panic::catch_unwind(||run(&cfg)).unwrap_or(99)
}
