//! AVD-only App UID to root-owned TUN. No default route, netfilter or NAT mutation.
use super::{wait_read,udp_packet,IFF_NO_PI,IFF_TUN,TUNSETIFF};
use serde_json::{json,Value};
use std::fs::{self,File,OpenOptions};
use std::io::{self,ErrorKind,Write};
use std::os::fd::AsRawFd;
use std::os::unix::fs::OpenOptionsExt;
use std::path::Path;
use std::process::Command;
use std::time::{Duration,Instant};
const DEST:&str="198.18.254.2/32";
const TABLE:&str="235";
fn ip(args:&[&str])->io::Result<String>{
 let o=Command::new("ip").args(args).output()?;
 if !o.status.success(){return Err(io::Error::new(ErrorKind::Other,format!("ip {:?}: {:?}: {}",args,o.status,String::from_utf8_lossy(&o.stderr).trim())))}
 Ok(String::from_utf8_lossy(&o.stdout).into_owned())
}
fn prop(k:&str)->String{
 Command::new("getprop").arg(k).output().ok().map(|o|String::from_utf8_lossy(&o.stdout).trim().to_owned()).unwrap_or_default()
}
fn rule(uid:&str,verb:&str)->io::Result<()>{
 ip(&["-4","rule",verb,"pref","8200","uidrange",uid,"to",DEST,"lookup",TABLE]).map(|_|())
}
fn route(dev:&str,verb:&str)->io::Result<()>{
 if verb=="add"{ip(&["-4","route","add",DEST,"dev",dev,"src","198.18.253.1","table",TABLE])?;}
 else{ip(&["-4","route","del",DEST,"dev",dev,"table",TABLE])?;}
 Ok(())
}
struct Owned{tun:Option<File>,name:String,uid:String,has_route:bool,has_rule:bool,closed:bool}
impl Owned{
 fn cleanup(&mut self)->io::Result<()>{
  let mut err=Vec::new();
  if self.has_rule{match rule(&self.uid,"del"){Ok(())=>self.has_rule=false,Err(e)=>err.push(e.to_string())}}
  if self.has_route{match route(&self.name,"del"){Ok(())=>self.has_route=false,Err(e)=>err.push(e.to_string())}}
  self.tun.take();self.closed=true;
  if err.is_empty(){Ok(())}else{Err(io::Error::new(ErrorKind::Other,err.join("; ")))}
 }
}
impl Drop for Owned{fn drop(&mut self){if !self.closed{let _=self.cleanup();}}}
fn tun()->io::Result<(File,String)>{
 let path=["/dev/tun","/dev/net/tun"].iter().copied().find(|p|Path::new(p).exists()).ok_or_else(||io::Error::new(ErrorKind::NotFound,"TUN missing"))?;
 let name=format!("wba{:05x}",std::process::id()%0xfffff);
 if ip(&["link","show","dev",&name]).is_ok(){return Err(io::Error::new(ErrorKind::AlreadyExists,"owned TUN collision"))}
 let f=OpenOptions::new().read(true).write(true).custom_flags(libc::O_CLOEXEC|libc::O_NONBLOCK).open(path)?;
 let mut ifr=[0u8;40];ifr[..name.len()].copy_from_slice(name.as_bytes());
 ifr[16..18].copy_from_slice(&(IFF_TUN|IFF_NO_PI).to_ne_bytes());
 if unsafe{libc::ioctl(f.as_raw_fd(),TUNSETIFF as _,ifr.as_mut_ptr())}<0{return Err(io::Error::last_os_error())}
 Ok((f,name))
}
fn stop(uid:u32,status:&str,why:&str)->Value{
 json!({"schema":"android-app-uid-route/v1","mode":"appflow","status":status,"app_uid":uid,"reason":why,"global_changes":false})
}
pub fn run(uid:u32,token:&str)->Value{
 if unsafe{libc::getuid()}!=0||uid<10000||uid>199999||token.is_empty()||token.len()>64||
  !token.bytes().all(|c|c.is_ascii_alphanumeric()||c==b'_'||c==b'-'){
  return stop(uid,"FAIL","UID0 or app UID/token constraints not met")
 }
 let hw=prop("ro.hardware");let qemu=prop("ro.kernel.qemu");
 if !["goldfish","ranchu"].contains(&hw.as_str())||qemu!="1"{
  return stop(uid,"ENV_BLOCKED",&format!("AVD-only guard: hardware={hw},qemu={qemu}"))
 }
 let before_rule=match ip(&["-4","rule","show"]){Ok(x)=>x,Err(e)=>return stop(uid,"FAIL",&e.to_string())};
 let before_route=match ip(&["-4","route","show","table","all"]){Ok(x)=>x,Err(e)=>return stop(uid,"FAIL",&e.to_string())};
 if before_rule.lines().any(|s|s.trim_start().starts_with("8200:")||s.contains("lookup 235")||s.contains("lookup 0xeb")){
  return stop(uid,"ENV_BLOCKED","rule priority/table collision")
 }
 match ip(&["-4","route","show","table",TABLE]){
  Ok(s) if s.trim().is_empty()=>(),Ok(_)=>return stop(uid,"ENV_BLOCKED","table235 occupied"),
  Err(e)=>return stop(uid,"FAIL",&e.to_string())
 }
 let (f,name)=match tun(){Ok(v)=>v,Err(e)=>return stop(uid,"FAIL",&format!("TUNSETIFF: {e}"))};
 let range=format!("{uid}-{uid}");
 let mut owned=Owned{tun:Some(f),name:name.clone(),uid:range.clone(),has_route:false,has_rule:false,closed:false};
 let test=(||->io::Result<Value>{
  ip(&["link","set","dev",&name,"mtu","1400"])?;
  ip(&["-4","addr","add","198.18.253.1/30","dev",&name])?;
  ip(&["link","set","dev",&name,"up"])?;
  route(&name,"add")?;owned.has_route=true;
  rule(&range,"add")?;owned.has_rule=true;
  println!("WBD_APPFLOW_READY {token}");io::stdout().flush()?;
  let expected=format!("wbd-app-{token}");
  let deadline=Instant::now()+Duration::from_secs(12);
  let mut buf=[0u8;2048];let mut ignored=0usize;
  while Instant::now()<deadline{
   let n=match wait_read(owned.tun.as_ref().unwrap().as_raw_fd(),&mut buf,500){
    Ok(n)=>n,Err(e) if e.kind()==ErrorKind::TimedOut=>continue,Err(e)=>return Err(e)};
   if n<28||buf[0]>>4!=4||buf[9]!=17{ignored+=1;continue;}
   let ihl=(buf[0]&15) as usize*4;
   if ihl!=20||buf[16..20]!=[198,18,254,2]||n<ihl+8{ignored+=1;continue;}
   let port=u16::from_be_bytes([buf[ihl+2],buf[ihl+3]]);
   if port!=49492||&buf[ihl+8..n]!=expected.as_bytes(){ignored+=1;continue;}
   // Reply from a peer on the owned /30, not from a real network or netd.
   // The destination is the ACTUAL app sender's IP and ephemeral UDP port.
   let src_ip=[buf[12],buf[13],buf[14],buf[15]];
   let sport=u16::from_be_bytes([buf[ihl],buf[ihl+1]]);
   let reply_data=format!("wbd-reply-{token}");
   let packet=udp_packet([198,18,253,2],src_ip,49492,sport,reply_data.as_bytes());
   let wrote=unsafe{libc::write(owned.tun.as_ref().unwrap().as_raw_fd(),
       packet.as_ptr().cast(),packet.len())};
   if wrote<0{return Err(io::Error::last_os_error())}
   if wrote as usize!=packet.len(){return Err(io::Error::new(ErrorKind::WriteZero,"short UDP TUN return packet"))}
   return Ok(json!({"status":"SUPPORTED_IN_SCOPE","app_payload_on_tun":true,
     "udp_packet_bytes":n,"payload":expected,"app_uid_rule":range,
     "src_ip":format!("{}.{}.{}.{}",buf[12],buf[13],buf[14],buf[15]),
     "dst_ip":"198.18.254.2","dst_port":49492,"tun_mtu":1400,"ignored_packets":ignored,
     "tun_reply_injected_bytes":wrote,"tun_reply_source":"198.18.253.2:49492",
     "tun_reply_destination_port":sport,"tun_reply_payload":reply_data}));
  }
  Err(io::Error::new(ErrorKind::TimedOut,format!("real App UDP not captured on owned TUN; ignored={ignored}")))
 })();
 let clean=owned.cleanup();
 let rules_equal=matches!(ip(&["-4","rule","show"]),Ok(ref s) if s==&before_rule);
 let routes_equal=matches!(ip(&["-4","route","show","table","all"]),Ok(ref s) if s==&before_route);
 let tun_gone=ip(&["link","show","dev",&name]).is_err();
 let clean_ok=clean.is_ok()&&rules_equal&&routes_equal&&tun_gone;
 let evidence=test.unwrap_or_else(|e|json!({"status":"FAIL","error":e.to_string()}));
 json!({"schema":"android-app-uid-route/v1","mode":"appflow",
  "status":if evidence["status"]=="SUPPORTED_IN_SCOPE"&&clean_ok{"SUPPORTED_IN_SCOPE"}else{"FAIL"},
  "app_uid":uid,"root_uid":unsafe{libc::getuid()},
  "root_selinux":fs::read_to_string("/proc/self/attr/current").unwrap_or_default().trim(),
  "evidence":evidence,"cleanup":{"ok":clean_ok,"rules_equal":rules_equal,"routes_equal":routes_equal,"tun_gone":tun_gone,
     "error":clean.err().map(|e|e.to_string())},
  "mutation":{"uidrange":range,"destination":DEST,"table":235,"priority":8200},
  "scope":"ephemeral AVD one app UID and synthetic /32; NOT real netd/NAT/tether"})
}
