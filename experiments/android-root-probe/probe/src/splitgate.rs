//! Actual kernel per-UID split/global lookup using 2 short-lived owned TUNs.
//! Strictly unshare+verify EMPTY netns first: NEVER touch Android netd routes.
//! Main FIB models a physical underlay; table236 split with CN throw prefixes
//! and table237 all-tunnel. Real OEM offload, tether and WBD remain NOT_RUN.
use super::{ip,IFF_NO_PI,IFF_TUN,TUNSETIFF};
use serde_json::{json,Value};
use std::fs::{self,File,OpenOptions};
use std::io::{self,ErrorKind};
use std::os::fd::AsRawFd;
use std::os::unix::fs::OpenOptionsExt;
use std::path::Path;
use std::process::Command;
fn ns()->io::Result<String>{
 Ok(fs::read_link("/proc/self/ns/net")?.to_string_lossy().to_string())
}
fn tun(name:&str)->io::Result<File>{
 if ip(&["link","show","dev",name]).is_ok(){
  return Err(io::Error::new(ErrorKind::AlreadyExists,"owned TUN collision"))
 }
 let path=["/dev/tun","/dev/net/tun"].iter().copied().find(|p|Path::new(p).exists())
   .ok_or_else(||io::Error::new(ErrorKind::NotFound,"/dev/tun absent"))?;
 let f=OpenOptions::new().read(true).write(true)
    .custom_flags(libc::O_NONBLOCK|libc::O_CLOEXEC).open(path)?;
 let mut ifr=[0u8;40];
 ifr[..name.len()].copy_from_slice(name.as_bytes());
 ifr[16..18].copy_from_slice(&(IFF_TUN|IFF_NO_PI).to_ne_bytes());
 if unsafe{libc::ioctl(f.as_raw_fd(),TUNSETIFF as _,ifr.as_mut_ptr())}<0{
    return Err(io::Error::last_os_error())
 }
 Ok(f)
}
fn lookup(ipaddr:&str,uid:&str)->io::Result<String>{
 let out=Command::new("ip").args(["-4","route","get",ipaddr,"uid",uid]).output()?;
 if !out.status.success(){
    return Err(io::Error::other(format!("ip -4 route get {ipaddr} uid {uid}: {}",
        String::from_utf8_lossy(&out.stderr))))
 }
 Ok(String::from_utf8_lossy(&out.stdout).into_owned())
}
fn fixture()->io::Result<Value>{
 let tag=format!("{:05x}",std::process::id()%0xfffff);
 let physical=format!("wbph{tag}");
 let tunnel=format!("wbtn{tag}");
 let fp=tun(&physical)?;let ft=tun(&tunnel)?;
 let outcome=(||->io::Result<Value>{
  for (dev,addr) in [(&physical,"198.51.100.1/30"),(&tunnel,"198.18.253.1/30")] {
   ip(&["link","set","dev",dev,"mtu","1400"])?;
   ip(&["-4","addr","add",addr,"dev",dev])?;
   ip(&["link","set","dev",dev,"up"])?;
  }
  // ROOT-only direct helper's physical FIB. The two Android App UIDs are
  // redirected before main; a shared-IP CDN exception does NOT bypass them.
  ip(&["-4","route","add","default","dev",&physical])?;
  ip(&["-4","route","add","default","dev",&tunnel,"table","236"])?;
  ip(&["-4","route","add","default","dev",&tunnel,"table","237"])?;
  // "throw" is a real kernel FIB action: let a better prior policy rule
  // end this table and continue into Android's physical routing owner.
  // Here the last-stage physical route is the namespace's main table.
  for prefix in ["203.0.113.0/24","10.0.0.0/8","172.16.0.0/12",
     "192.168.0.0/16","169.254.0.0/16","198.51.100.240/28"]{
   ip(&["-4","route","add","throw",prefix,"table","236"])?;
  }
  ip(&["-4","rule","add","pref","12000","uidrange","10501-10501","lookup","236"])?;
  ip(&["-4","rule","add","pref","12001","uidrange","10502-10502","lookup","237"])?;
  let cases=[
   ("split_cn_ip_direct","203.0.113.8","10501",&physical),
   ("split_foreign_ip_tunnel","8.8.8.8","10501",&tunnel),
   ("split_lan_direct","10.1.2.3","10501",&physical),
   ("split_explicit_direct","198.51.100.242","10501",&physical),
   ("global_cn_ip_tunnel","203.0.113.8","10502",&tunnel),
   ("global_foreign_ip_tunnel","8.8.8.8","10502",&tunnel),
   ("global_cn_dns_ip_still_tunnel_for_ordinary_app","223.5.5.5","10502",&tunnel),
   ("bootstrap_control_socket_physical_uid0","192.0.2.222","0",&physical),
   ("direct_dns_socket_physical_uid0","223.5.5.5","0",&physical),
   ("server_ip_not_whitelisted_for_global_app","192.0.2.222","10502",&tunnel)
  ];
  let mut results=Vec::new();
  for (label,dst,uid,want) in cases{
   let got=lookup(dst,uid)?;
   let pass=got.contains(&format!(" dev {want} "))||got.contains(&format!(" dev {want}\n"));
   results.push(json!({"case":label,"uid":uid,"dst":dst,"expected_dev":want,
       "kernel_route_get":got.trim(),"pass":pass}));
  }
  if results.iter().any(|x|x["pass"]!=true) {
   return Err(io::Error::other(format!("UID kernel FIB decision mismatch: {results:?}")))
  }
  Ok(json!({"status":"SUPPORTED_IN_SCOPE","checks":results,
    "check_count":results.len(),"kernel_uidrange_real":true,
    "physical_fib_simulated":true,"split_table":236,"global_table":237,
    "main_netns_untouched":true,
    "real_android_netd":"NOT_RUN",
    "physical_wifi_usb":"NOT_RUN","production_wbd":"NOT_RUN"}))
 })();
 drop(fp);drop(ft);
 if ip(&["link","show","dev",&physical]).is_ok()||ip(&["link","show","dev",&tunnel]).is_ok(){
  return Err(io::Error::other("owned synthetic TUN remained after fd close"))
 }
 outcome
}
pub fn run()->Value{
 if unsafe{libc::geteuid()}!=0{return json!({"status":"PERMISSION_DENIED",
   "reason":"Root required","global_changes":false})}
 let before=match ns(){Ok(s)=>s,Err(e)=>return json!({"status":"ENV_BLOCKED",
    "errno":e.raw_os_error(),"reason":e.to_string(),"global_changes":false})};
 if unsafe{libc::unshare(libc::CLONE_NEWNET)}!=0{
  let e=io::Error::last_os_error();
  return json!({"status":"ENV_BLOCKED","reason":format!("unshare: {e}"),
   "errno":e.raw_os_error(),"global_changes":false})
 }
 let after=match ns(){Ok(s)=>s,Err(e)=>return json!({"status":"FAIL",
    "reason":e.to_string(),"global_changes":false})};
 if before==after{return json!({"status":"FAIL","reason":"not a separate netns",
     "global_changes":false})}
 let empty=match fs::read_to_string("/proc/net/route"){
  Ok(s)=>s.lines().skip(1).all(|s|s.trim().is_empty()),
  Err(_)=>false
 };
 if !empty{return json!({"status":"ENV_BLOCKED",
   "reason":"private netns main FIB not verifiably empty","global_changes":false})}
 match fixture(){
  Ok(e)=>json!({"status":"SUPPORTED_IN_SCOPE","before_netns":before,
    "after_netns":after,"global_changes":false,"evidence":e}),
  Err(e)=>json!({"status":"FAIL","before_netns":before,"after_netns":after,
    "reason":e.to_string(),"errno":e.raw_os_error(),"global_changes":false,
    "scope":"isolated kernel per-UID route only"})
 }
}
