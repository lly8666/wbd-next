//! Root tethering NAT feasibility using a private EMPTY network namespace.
//! Actual hotspot/USB/Android eBPF offload are NOT touched or certified.
//! Two synthetic Wi-Fi clients and one synthetic USB client each inject real
//! IPv4 UDP packets into distinct TUN downstreams, then verify forward SNAT
//! on a third TUN and independent kernel conntrack reverse translation.
use super::{ip,udp_packet,wait_read,IFF_NO_PI,IFF_TUN,TUNSETIFF};
use serde_json::{json,Value};
use std::fs::{self,File,OpenOptions};
use std::io::{self,ErrorKind,Write};
use std::os::fd::AsRawFd;
use std::os::unix::fs::OpenOptionsExt;
use std::path::Path;
use std::process::Command;
use std::time::{Duration,Instant};
const UP:[u8;4]=[198,18,253,1];
const PEER:[u8;4]=[198,18,254,2];
fn namespace()->io::Result<String>{
 Ok(fs::read_link("/proc/self/ns/net")?.to_string_lossy().into_owned())
}
fn tool(args:&[&str])->io::Result<String>{
 let o=Command::new("iptables").args(args).output()?;
 if !o.status.success(){return Err(io::Error::other(format!("iptables {args:?}: {}",String::from_utf8_lossy(&o.stderr))))}
 Ok(String::from_utf8_lossy(&o.stdout).into_owned())
}
fn tun(name:&str)->io::Result<File>{
 let p=["/dev/tun","/dev/net/tun"].iter().find(|x|Path::new(x).exists())
    .ok_or_else(||io::Error::new(ErrorKind::NotFound,"TUN absent"))?;
 if ip(&["link","show","dev",name]).is_ok(){
     return Err(io::Error::new(ErrorKind::AlreadyExists,"private device name collision"));
 }
 let f=OpenOptions::new().read(true).write(true)
    .custom_flags(libc::O_NONBLOCK|libc::O_CLOEXEC).open(p)?;
 let mut ifr=[0u8;40];ifr[..name.len()].copy_from_slice(name.as_bytes());
 ifr[16..18].copy_from_slice(&(IFF_TUN|IFF_NO_PI).to_ne_bytes());
 if unsafe{libc::ioctl(f.as_raw_fd(),TUNSETIFF as _,ifr.as_mut_ptr())}<0{
    return Err(io::Error::last_os_error())
 }
 Ok(f)
}
fn setup(dev:&str,addr:&str)->io::Result<()>{
 ip(&["link","set","dev",dev,"mtu","1400"])?;
 ip(&["-4","addr","add",addr,"dev",dev])?;
 ip(&["link","set","dev",dev,"up"])?;
 Ok(())
}
fn ipv4_matches(pkt:&[u8],src:[u8;4],dst:[u8;4],dport:u16,payload:&[u8])->bool{
 pkt.len()>=28 && pkt[0]==0x45 && pkt[9]==17 &&
 pkt[12..16]==src && pkt[16..20]==dst &&
 u16::from_be_bytes([pkt[22],pkt[23]])==dport &&
 &pkt[28..]==payload
}
fn get_matching(fd:&File,src:[u8;4],dst:[u8;4],port:u16,payload:&[u8])->io::Result<(usize,u16,usize)>{
 let deadline=Instant::now()+Duration::from_millis(2400);
 let mut packet=[0u8;2048];let mut missed=0;
 while Instant::now()<deadline{
     let left=deadline.saturating_duration_since(Instant::now()).as_millis() as i32;
     let n=match wait_read(fd.as_raw_fd(),&mut packet,left.clamp(1,400)){
       Ok(n)=>n,Err(e) if e.kind()==ErrorKind::TimedOut=>continue,Err(e)=>return Err(e)};
     if ipv4_matches(&packet[..n],src,dst,port,payload){
         return Ok((n,u16::from_be_bytes([packet[20],packet[21]]),missed));
     }
     missed+=1;
 }
 Err(io::Error::new(ErrorKind::TimedOut,format!("no intended forwarded packet; ignored={missed}")))
}
fn write_pkt(fd:&File,pkt:&[u8])->io::Result<()>{
 let n=unsafe{libc::write(fd.as_raw_fd(),pkt.as_ptr().cast(),pkt.len())};
 if n<0{return Err(io::Error::last_os_error())}
 if n as usize != pkt.len(){return Err(io::Error::new(ErrorKind::WriteZero,"short TUN write"))}
 Ok(())
}
fn fixture()->io::Result<Value>{
 let tag=format!("{:04x}",std::process::id()%0xffff);
 let wifi=format!("wbwf{tag}");
 let usb=format!("wbus{tag}");
 let up=format!("wbup{tag}");
 let fw=tun(&wifi)?;
 let fu=tun(&usb)?;
 let fo=tun(&up)?;
 setup(&wifi,"10.128.11.1/24")?;
 setup(&usb,"10.128.12.1/24")?;
 setup(&up,"198.18.253.1/30")?;
 ip(&["-4","route","add","198.18.254.2/32","dev",&up])?;
 fs::write("/proc/sys/net/ipv4/ip_forward","1\n")?;
 let forward=fs::read_to_string("/proc/sys/net/ipv4/ip_forward")?;
 if forward.trim()!="1"{return Err(io::Error::other("per-netns forwarding readback not 1"))}
 // This iptables command is executed only AFTER CLONE_NEWNET + empty-FIB.
 // Failure is reported, never substituted by global netfilter modifications.
 for (down,source) in [(&wifi,"10.128.11.0/24"),(&usb,"10.128.12.0/24")]{
   tool(&["-I","FORWARD","1","-i",down,"-o",&up,"-j","ACCEPT"])?;
   tool(&["-I","FORWARD","1","-i",&up,"-o",down,
        "-m","conntrack","--ctstate","ESTABLISHED,RELATED","-j","ACCEPT"])?;
   tool(&["-t","nat","-A","POSTROUTING","-s",source,
         "-d","198.18.254.2/32","-o",&up,
         "-j","SNAT","--to-source","198.18.253.1"])?;
 }
 let rules=tool(&["-t","nat","-S","POSTROUTING"])?;
 if !rules.contains(&wifi.replace("wbwf","10.128.11.0/24")) &&
    !(rules.contains("10.128.11.0/24")&&rules.contains("10.128.12.0/24")){
   return Err(io::Error::other("SNAT rules not visible in private namespace"))
 }
 let samples=[
   ("wifi", [10,128,11,10],43001,&fw),
   ("wifi", [10,128,11,11],43002,&fw),
   ("usb", [10,128,12,10],43003,&fu)
 ];
 let mut records=Vec::new();
 for (kind,client,source_port,down) in samples{
   let request=format!("wbd-{kind}-{source_port}");
   let req=udp_packet(client,PEER,source_port,49492,request.as_bytes());
   write_pkt(down,&req)?;
   let (outlen,translated_port,missed)=get_matching(&fo,UP,PEER,49492,request.as_bytes())?;
   let reply=format!("wbd-return-{kind}-{source_port}");
   let resp=udp_packet(PEER,UP,49492,translated_port,reply.as_bytes());
   write_pkt(&fo,&resp)?;
   let (inlen,_,missed_back)=get_matching(down,PEER,client,source_port,reply.as_bytes())?;
   records.push(json!({"link":kind,"client_ipv4":format!("{}.{}.{}.{}",client[0],client[1],client[2],client[3]),
    "client_port":source_port,"translated_src":"198.18.253.1","translated_port":translated_port,
    "forwarded_udp_bytes":outlen,"reverse_udp_bytes":inlen,
    "ignored_forward":missed,"ignored_reverse":missed_back,
    "snat_pass":true,"conntrack_reverse_pass":true}));
 }
 drop(fw);drop(fu);drop(fo);
 let all_gone=[&wifi,&usb,&up].iter().all(|n|ip(&["link","show","dev",n]).is_err());
 if !all_gone{return Err(io::Error::other("private TUN lingered after fds closed"))}
 Ok(json!({"status":"SUPPORTED_IN_SCOPE","forwarding_readback":forward.trim(),
   "synthetic_clients":records,"client_count":3,"downstream_types":["wifi-synthetic","usb-synthetic"],
   "owned_tun_gone":true,"native_netns_only":true,
   "real_wifi_hotspot":"NOT_RUN","real_usb_tether":"NOT_RUN",
   "offload_bypass":"NOT_RUN","physical_nat":"NOT_RUN"}))
}
pub fn run()->Value{
 if unsafe{libc::geteuid()}!=0{
   return json!({"status":"PERMISSION_DENIED","reason":"root required"});
 }
 let original=match namespace(){
   Ok(x)=>x,Err(e)=>return json!({"status":"ENV_BLOCKED","reason":e.to_string()})
 };
 if unsafe{libc::unshare(libc::CLONE_NEWNET)}!=0 {
   return json!({"status":"ENV_BLOCKED","reason":format!("unshare(CLONE_NEWNET): {}",io::Error::last_os_error()),
       "global_changes":false,"real_tether":"NOT_RUN"})
 }
 let current=match namespace(){
   Ok(x)=>x,Err(e)=>return json!({"status":"FAIL","reason":e.to_string(),"global_changes":false})
 };
 if original==current {
   return json!({"status":"FAIL","reason":"namespace unchanged","global_changes":false});
 }
 let route=fs::read_to_string("/proc/net/route");
 if !matches!(route,Ok(ref s) if s.lines().skip(1).all(str::is_empty)){
   return json!({"status":"ENV_BLOCKED","reason":"new namespace not empty",
       "global_changes":false})
 }
 // Network namespace lifetime is this process. No persistent bridge to a real tether.
 let result=fixture();
 match result{
    Ok(data)=>json!({"status":"SUPPORTED_IN_SCOPE","before":original,"after":current,
        "global_changes":false,"evidence":data,
        "scope":"one private network namespace, 3 synthetic downstream clients SNAT/conntrack, no Android tether"}),
    Err(e)=>json!({"status":"UNAVAILABLE","before":original,"after":current,
        "global_changes":false,"reason":e.to_string(),
        "real_hotspot_usb":"NOT_RUN","scope":"kernel NAT/iptables/private netns fixture blocked or unsupported"})
 }
}
