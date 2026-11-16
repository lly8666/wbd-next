//! Real kernel IPv4 UDP/53 egress+response selection in a verified EMPTY
//! CLONE_NEWNET. "Physical" and "tunnel" are TWO synthetic ephemeral TUNs.
//! The client uses the same QNAME->purpose decision as android_split::Policy.
//! This is NOT Android DNS capture, external 223.5.5.5/1.1.1.1, real WBD
//! TLS, or physical network forwarding; never mutate host netd.
use super::{ip,udp_packet,wait_read,IFF_TUN,IFF_NO_PI,TUNSETIFF};
use serde_json::{json,Value};
use std::fs::{self,File,OpenOptions};
use std::io::{self,ErrorKind};
use std::net::{Ipv4Addr,SocketAddrV4,UdpSocket};
use std::os::fd::AsRawFd;
use std::os::unix::fs::OpenOptionsExt;
use std::path::Path;
use std::time::{Duration,Instant};

const DIRECT_LOCAL:[u8;4]=[198,51,100,1];
const DIRECT_DNS:[u8;4]=[198,51,100,2];
const TUNNEL_LOCAL:[u8;4]=[198,18,253,1];
const TUNNEL_DNS:[u8;4]=[198,18,253,2];
const ANSWER:[u8;4]=[8,8,8,8];
#[derive(Clone,Debug)]
pub(crate) struct Case{
 pub label:&'static str,
 pub qname:&'static str,
 pub direct:bool,
 pub data_outcome:&'static str,
}
fn netns()->io::Result<String>{
 Ok(fs::read_link("/proc/self/ns/net")?.to_string_lossy().into_owned())
}
fn tun(name:&str)->io::Result<File>{
 let path=["/dev/tun","/dev/net/tun"].iter().copied().find(|p|Path::new(p).exists())
    .ok_or_else(||io::Error::new(ErrorKind::NotFound,"TUN device absent"))?;
 if ip(&["link","show","dev",name]).is_ok(){
  return Err(io::Error::new(ErrorKind::AlreadyExists,"owned TUN collision"))
 }
 let fd=OpenOptions::new().read(true).write(true)
   .custom_flags(libc::O_NONBLOCK|libc::O_CLOEXEC).open(path)?;
 let mut ifr=[0u8;40];
 ifr[..name.len()].copy_from_slice(name.as_bytes());
 ifr[16..18].copy_from_slice(&(IFF_TUN|IFF_NO_PI).to_ne_bytes());
 if unsafe{libc::ioctl(fd.as_raw_fd(),TUNSETIFF as _,ifr.as_mut_ptr())}<0{
   return Err(io::Error::last_os_error())
 }
 Ok(fd)
}
fn question(qname:&str,id:u16)->io::Result<Vec<u8>>{
 if qname.is_empty()||qname.len()>240||!qname.is_ascii(){
    return Err(io::Error::other("unsafe DNS name"))
 }
 let mut b=vec![0u8;12];
 b[0..2].copy_from_slice(&id.to_be_bytes());
 b[2..4].copy_from_slice(&0x0100u16.to_be_bytes()); // RD
 b[4..6].copy_from_slice(&1u16.to_be_bytes()); // one QD
 for s in qname.split('.'){
    if s.is_empty()||s.len()>63||!s.bytes().all(|x|
       x.is_ascii_alphanumeric()||x==b'-'){
      return Err(io::Error::other("invalid ASCII DNS label"))
    }
    b.push(s.len() as u8);b.extend_from_slice(s.as_bytes());
 }
 b.push(0);
 b.extend_from_slice(&1u16.to_be_bytes()); // A
 b.extend_from_slice(&1u16.to_be_bytes()); // IN
 Ok(b)
}
fn answer(q:&[u8])->io::Result<Vec<u8>>{
 if q.len()<17 || q[4..6]!=1u16.to_be_bytes(){
    return Err(io::Error::other("unexpected DNS question format"))
 }
 let mut b=q.to_vec();
 b[2..4].copy_from_slice(&0x8180u16.to_be_bytes()); // QR RD RA, NOERROR
 b[6..8].copy_from_slice(&1u16.to_be_bytes());
 b.extend_from_slice(&[0xc0,0x0c]); // compressed QNAME pointer
 b.extend_from_slice(&1u16.to_be_bytes()); // A
 b.extend_from_slice(&1u16.to_be_bytes()); // IN
 b.extend_from_slice(&60u32.to_be_bytes());
 b.extend_from_slice(&4u16.to_be_bytes());
 b.extend_from_slice(&ANSWER);
 Ok(b)
}
fn attempt_case(test:&Case,direct:&File,tunnel:&File,id:u16)->io::Result<Value>{
 let (fd,local,peer,label) = if test.direct {
    (direct,DIRECT_LOCAL,DIRECT_DNS,"direct_synthetic")
 }else{
    (tunnel,TUNNEL_LOCAL,TUNNEL_DNS,"tunnel_synthetic")
 };
 let socket=UdpSocket::bind(SocketAddrV4::new(Ipv4Addr::from(local),0))?;
 socket.set_read_timeout(Some(Duration::from_millis(2000)))?;
 let sport=socket.local_addr()?.port();
 let q=question(test.qname,id)?;
 let n=socket.send_to(&q,SocketAddrV4::new(Ipv4Addr::from(peer),53))?;
 if n!=q.len(){return Err(io::Error::new(ErrorKind::WriteZero,"short DNS question"))}
 let deadline=Instant::now()+Duration::from_millis(2000);
 let mut buf=[0u8;4096];
 let mut got=None;
 let mut ignored=0;
 while Instant::now()<deadline{
    let left=deadline.saturating_duration_since(Instant::now()).as_millis() as i32;
    if left<=0{break}
    let read=wait_read(fd.as_raw_fd(),&mut buf,left.min(300));
    match read{
      Ok(n) if n>=28+q.len() && buf[0]>>4==4&&buf[9]==17 &&
          buf[12..16]==local&&buf[16..20]==peer &&
          u16::from_be_bytes([buf[20],buf[21]])==sport &&
          u16::from_be_bytes([buf[22],buf[23]])==53 &&
          &buf[28..n]==&q=>{
             got=Some(n);break;
          },
      Ok(_)=>ignored+=1,
      Err(e) if e.kind()==ErrorKind::TimedOut=>continue,
      Err(e)=>return Err(e)
    }
 }
 let egress_bytes=got.ok_or_else(||io::Error::new(ErrorKind::TimedOut,
    format!("kernel did not emit matching {label} QNAME={} DNS UDP",test.qname)))?;
 let resp=answer(&q)?;
 let packet=udp_packet(peer,local,53,sport,&resp);
 let written=unsafe{libc::write(fd.as_raw_fd(),packet.as_ptr().cast(),packet.len())};
 if written<0{return Err(io::Error::last_os_error())}
 if written as usize!=packet.len(){return Err(io::Error::new(ErrorKind::WriteZero,"short DNS TUN ingress"))}
 let mut response=[0u8;4096];
 let (got,src)=socket.recv_from(&mut response)?;
 if src.ip()!=Ipv4Addr::from(peer) || src.port()!=53 || got!=resp.len()||
     response[..got]!=resp || response[..2]!=id.to_be_bytes() ||
     response[6..8]!=1u16.to_be_bytes()||!response.ends_with(&ANSWER) {
   return Err(io::Error::other("DNS UDP response wrong transaction/answer/route"))
 }
 Ok(json!({"case":test.label,"qname":test.qname,"purpose_egress":label,
   "actual_kernel_tun_egress_bytes":egress_bytes,
   "actual_kernel_tun_ingress_bytes":written,
   "response_received_bytes":got,"answer_A":Ipv4Addr::from(ANSWER).to_string(),
   "data_after_real_A":test.data_outcome,
   "dns_transaction_verified":true,"ignored_background_packets":ignored}))
}
fn fixture(cases:&[Case])->io::Result<Value>{
 let id=format!("{:05x}",std::process::id()%0xfffff);
 let d=format!("wbdp{id}");let t=format!("wbdt{id}");
 let direct=tun(&d)?;let tunnel=tun(&t)?;
 let worked=(||->io::Result<Value>{
  for (name,addr) in [(&d,"198.51.100.1/30"),(&t,"198.18.253.1/30")]{
    ip(&["link","set","dev",name,"mtu","1400"])?;
    ip(&["-4","addr","add",addr,"dev",name])?;
    ip(&["link","set","dev",name,"up"])?;
  }
  let mut results=Vec::with_capacity(cases.len());
  for (i,case) in cases.iter().enumerate(){
    results.push(attempt_case(case,&direct,&tunnel,0xb600+(i as u16))?);
  }
  Ok(json!({"status":"SUPPORTED_IN_SCOPE","checks":results,
   "check_count":results.len(),"actual_kernel_dns_udp":true,
   "dns_response_A_foreign":Ipv4Addr::from(ANSWER).to_string(),
   "real_upstream_direct_DNS":"NOT_RUN","real_upstream_tunnel_DNS":"NOT_RUN",
   "android_system_dns_interception":"NOT_RUN","real_wbd_tunnel":"NOT_RUN"}))
 })();
 drop(direct);drop(tunnel);
 if ip(&["link","show","dev",&d]).is_ok() || ip(&["link","show","dev",&t]).is_ok(){
   return Err(io::Error::other("private DNS TUN leaked after owned fd closure"))
 }
 worked
}
pub(crate) fn run(cases:&[Case])->Value{
 if unsafe{libc::geteuid()}!=0{
   return json!({"status":"PERMISSION_DENIED","reason":"requires genuine UID0",
     "global_changes":false})
 }
 let before=match netns(){Ok(s)=>s,Err(e)=>return json!({"status":"ENV_BLOCKED",
   "reason":e.to_string(),"errno":e.raw_os_error(),"global_changes":false})};
 if unsafe{libc::unshare(libc::CLONE_NEWNET)}!=0{
   let e=io::Error::last_os_error();
   return json!({"status":"ENV_BLOCKED","reason":format!("CLONE_NEWNET failed: {e}"),
     "errno":e.raw_os_error(),"global_changes":false})
 }
 let after=match netns(){Ok(s)=>s,Err(e)=>return json!({"status":"FAIL",
   "reason":e.to_string(),"global_changes":false})};
 if before==after{
   return json!({"status":"FAIL","reason":"network namespace not isolated","global_changes":false})
 }
 let empty=matches!(fs::read_to_string("/proc/net/route"),
    Ok(ref s) if s.lines().skip(1).all(|x|x.trim().is_empty()));
 if !empty {
   return json!({"status":"ENV_BLOCKED","reason":"fresh netns main IPv4 FIB is not empty",
       "global_changes":false})
 }
 match fixture(cases){
  Ok(v)=>json!({"status":"SUPPORTED_IN_SCOPE","before_netns":before,
     "after_netns":after,"global_changes":false,"evidence":v}),
  Err(e)=>json!({"status":"FAIL","reason":e.to_string(),
     "errno":e.raw_os_error(),"before_netns":before,"after_netns":after,
     "global_changes":false})
 }
}
#[cfg(test)]
mod tests{
 use super::*;
 #[test]fn dns_query_transaction(){
  let q=question("www.baidu.com",0xb600).unwrap();
  let a=answer(&q).unwrap();
  assert_eq!(&q[..2],&a[..2]);
  assert_eq!(&a[a.len()-4..],&ANSWER);
 }
}
