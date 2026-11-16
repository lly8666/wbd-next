//! True IPv6 UDP ingress/egress through an owned TUN in a *fresh private*
//! Linux network namespace. No Android netd, main namespace, tether or NAT.
//! This is not proof of IPv6-only cellular/CLAT/real hotspot.
use super::{ip,wait_read,IFF_NO_PI,IFF_TUN,TUNSETIFF};
use serde_json::{json,Value};
use std::fs::{self,File,OpenOptions};
use std::io::{self,ErrorKind};
use std::net::{Ipv6Addr,SocketAddrV6,UdpSocket};
use std::os::fd::AsRawFd;
use std::os::unix::fs::OpenOptionsExt;
use std::path::Path;
use std::time::{Duration,Instant};

const LOCAL:[u8;16]=[0xfd,0xb6,0,0,0,0,0,0,0,0,0,0,0,0,0,1];
const PEER:[u8;16]=[0xfd,0xb6,0,0,0,0,0,0,0,0,0,0,0,0,0,2];
const PAYLOAD:&[u8]=b"wbd-ipv6-out";
const RESPONSE:&[u8]=b"wbd-ipv6-in";

fn namespace()->io::Result<String>{
 Ok(fs::read_link("/proc/self/ns/net")?.to_string_lossy().into_owned())
}
fn tun(name:&str)->io::Result<File>{
 let path=["/dev/tun","/dev/net/tun"].iter().copied().find(|p|Path::new(p).exists())
     .ok_or_else(||io::Error::new(ErrorKind::NotFound,"/dev/tun or /dev/net/tun not present"))?;
 if ip(&["link","show","dev",name]).is_ok(){
     return Err(io::Error::new(ErrorKind::AlreadyExists,"temporary IPv6 TUN collision"))
 }
 let fd=OpenOptions::new().read(true).write(true).custom_flags(libc::O_NONBLOCK|libc::O_CLOEXEC).open(path)?;
 let mut ifr=[0u8;40];
 ifr[..name.len()].copy_from_slice(name.as_bytes());
 ifr[16..18].copy_from_slice(&(IFF_TUN|IFF_NO_PI).to_ne_bytes());
 if unsafe{libc::ioctl(fd.as_raw_fd(),TUNSETIFF as _,ifr.as_mut_ptr())}<0{
     return Err(io::Error::last_os_error())
 }
 Ok(fd)
}
fn checksum(bytes:&[u8])->u16{
 let mut total:u32=0;
 for x in bytes.chunks(2){
  total+=u16::from_be_bytes([x[0],*x.get(1).unwrap_or(&0)]) as u32;
 }
 while total>>16!=0 {total=(total&0xffff)+(total>>16)}
 !(total as u16)
}
fn ipv6_udp(src:[u8;16],dst:[u8;16],sport:u16,dport:u16,payload:&[u8])->Vec<u8>{
 let len=8+payload.len();
 let mut b=vec![0u8;40+len];
 b[0]=0x60;
 b[4..6].copy_from_slice(&(len as u16).to_be_bytes());
 b[6]=17;b[7]=64;
 b[8..24].copy_from_slice(&src);
 b[24..40].copy_from_slice(&dst);
 b[40..42].copy_from_slice(&sport.to_be_bytes());
 b[42..44].copy_from_slice(&dport.to_be_bytes());
 b[44..46].copy_from_slice(&(len as u16).to_be_bytes());
 b[48..].copy_from_slice(payload);
 let mut pseudo=Vec::with_capacity(40+len);
 pseudo.extend_from_slice(&src);pseudo.extend_from_slice(&dst);
 pseudo.extend_from_slice(&(len as u32).to_be_bytes());
 pseudo.extend_from_slice(&[0,0,0,17]);
 pseudo.extend_from_slice(&b[40..]);
 let sum=checksum(&pseudo);
 b[46..48].copy_from_slice(&(if sum==0{0xffff}else{sum}).to_be_bytes());
 b
}
fn attempt()->io::Result<Value>{
 let name=format!("wbd6{:05x}",std::process::id()%0xfffff);
 let fd=tun(&name)?;
 let work=(||->io::Result<Value>{
  ip(&["link","set","dev",&name,"mtu","1400"])?;
  ip(&["-6","addr","add","fdb6::1/64","dev",&name])?;
  ip(&["link","set","dev",&name,"up"])?;
  let send=UdpSocket::bind(SocketAddrV6::new(Ipv6Addr::from(LOCAL),0,0,0))?;
  send.set_read_timeout(Some(Duration::from_millis(1500)))?;
  let src_port=send.local_addr()?.port();
  let n=send.send_to(PAYLOAD,SocketAddrV6::new(Ipv6Addr::from(PEER),49492,0,0))?;
  if n!=PAYLOAD.len(){return Err(io::Error::new(ErrorKind::WriteZero,"short IPv6 UDP send"))}
  let mut buf=[0u8;2048];
  let deadline=Instant::now()+Duration::from_millis(2000);
  let mut outlen=0usize;
  let mut ignored=0;
  while Instant::now()<deadline{
    let remain=deadline.saturating_duration_since(Instant::now()).as_millis() as i32;
    if remain<=0{break}
    match wait_read(fd.as_raw_fd(),&mut buf,remain.min(300)){
      Ok(n) if n>=48&&buf[0]>>4==6&&buf[6]==17&&
        buf[8..24]==LOCAL&&buf[24..40]==PEER&&
        u16::from_be_bytes([buf[42],buf[43]])==49492&&
        &buf[48..n]==PAYLOAD => {outlen=n;break},
      Ok(_)=>ignored+=1,
      Err(e) if e.kind()==ErrorKind::TimedOut=>continue,
      Err(e)=>return Err(e)
    }
  }
  if outlen==0{return Err(io::Error::new(ErrorKind::TimedOut,
      format!("no expected IPv6 UDP packet on owned TUN; ignored={ignored}")))}
  let reply=ipv6_udp(PEER,LOCAL,49492,src_port,RESPONSE);
  let written=unsafe{libc::write(fd.as_raw_fd(),reply.as_ptr().cast(),reply.len())};
  if written<0{return Err(io::Error::last_os_error())}
  if written as usize!=reply.len(){return Err(io::Error::new(ErrorKind::WriteZero,"short IPv6 ingress"))}
  let mut got=[0u8;128];
  let (received,from)=send.recv_from(&mut got)?;
  if &got[..received]!=RESPONSE || from.ip()!=Ipv6Addr::from(PEER) {
      return Err(io::Error::other("IPv6 reply destination, origin or payload mismatch"))
  }
  Ok(json!({"status":"SUPPORTED_IN_SCOPE","ipv6_send_bytes":n,
    "tun_ipv6_egress_bytes":outlen,"tun_ipv6_ingress_bytes":written,
    "udp6_receive_bytes":received,"reply_src":from.to_string(),
    "src_port":src_port,"owned_tun":name,"ignored_packets":ignored,
    "scope":"private netns TUN, no Android netd or cellular CLAT"}))
 })();
 drop(fd);
 let gone=ip(&["link","show","dev",&name]).is_err();
 match work{
   Ok(e) if gone=>Ok(json!({"status":"SUPPORTED_IN_SCOPE","evidence":e,
      "owned_tun_gone":true,"real_ipv6_clat":"NOT_RUN"})),
   Ok(e)=>Err(io::Error::other(format!("temporary IPv6 TUN still present: {e}"))),
   Err(e)=>Err(e)
 }
}
pub fn run()->Value{
 if unsafe{libc::geteuid()}!=0{
    return json!({"status":"PERMISSION_DENIED","reason":"root required","global_changes":false})
 }
 let before=match namespace(){Ok(v)=>v,Err(e)=>return json!({"status":"ENV_BLOCKED","reason":e.to_string(),"global_changes":false})};
 if unsafe{libc::unshare(libc::CLONE_NEWNET)}!=0{
    return json!({"status":"ENV_BLOCKED","reason":format!("CLONE_NEWNET: {}",io::Error::last_os_error()),
       "global_changes":false,"actual_cellular_ipv6":"NOT_RUN"})
 }
 let after=match namespace(){Ok(v)=>v,Err(e)=>return json!({"status":"FAIL","reason":e.to_string(),"global_changes":false})};
 if before==after{return json!({"status":"FAIL","reason":"network namespace was not isolated","global_changes":false})}
 let main_fib=fs::read_to_string("/proc/net/route");
 if !matches!(main_fib,Ok(ref s) if s.lines().skip(1).all(str::is_empty)){
    return json!({"status":"ENV_BLOCKED","reason":"private namespace not empty","global_changes":false})
 }
 match attempt(){
   Ok(v)=>json!({"schema":"android-root-ipv6gate/v1","status":"SUPPORTED_IN_SCOPE",
       "before_netns":before,"after_netns":after,"global_changes":false,"evidence":v,
       "real_cellular_ipv6_clat":"NOT_RUN"}),
   Err(e)=>json!({"schema":"android-root-ipv6gate/v1","status":"UNAVAILABLE",
       "before_netns":before,"after_netns":after,"global_changes":false,
       "reason":e.to_string(),"errno":e.raw_os_error(),"real_cellular_ipv6_clat":"NOT_RUN"})
 }
}
#[cfg(test)]
mod tests{
 use super::*;
 #[test]fn udp6_checksum_nonzero(){
   let p=ipv6_udp(PEER,LOCAL,49492,41000,b"test");
   assert_eq!(p[0],0x60);
   assert_eq!(p[6],17);
   assert_ne!(u16::from_be_bytes([p[46],p[47]]),0);
 }
}
