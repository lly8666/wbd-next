//! Read-only phone/AVD Root capability inventory. Never change netd/tether,
//! disable SELinux/offload, leak SSID/serial, or treat this as live VPN proof.
use serde_json::{json,Value};
use std::fs;
use std::path::Path;
use std::process::Command;

fn read(path:&str,max:usize)->String{
 fs::read_to_string(path).map(|s|s.chars().take(max).collect::<String>().trim().to_owned())
    .unwrap_or_else(|e|format!("UNAVAILABLE:{}",e.kind()))
}
fn prop(name:&str)->String{
 Command::new("getprop").arg(name).output().ok()
 .filter(|v|v.status.success())
 .map(|v|String::from_utf8_lossy(&v.stdout).trim().chars().take(120).collect::<String>())
 .unwrap_or_default()
}
fn cmd_version(program:&str,arg:&str)->Value{
 match Command::new(program).arg(arg).output(){
   Ok(o)=>json!({"present":true,"exit":o.status.code(),
     "version":String::from_utf8_lossy(if o.stdout.is_empty(){&o.stderr}else{&o.stdout})
       .chars().take(160).collect::<String>().trim()}),
   Err(e)=>json!({"present":false,"error":e.to_string(),"errno":e.raw_os_error()})
 }
}
fn cap(fields:&str,name:&str)->Option<u64>{
 fields.lines().find_map(|l|l.strip_prefix(name))
  .and_then(|s|u64::from_str_radix(s.trim(),16).ok())
}
fn relevant_dumpsys()->Value{
 // Android Root dumpsys tethering is advisory; vendor services have divergent
 // grammar and offload might not touch the CPU at all. No sensitive full dump.
 match Command::new("dumpsys").arg("tethering").output(){
   Ok(v)=>{
     let s=String::from_utf8_lossy(&v.stdout);
     let mut filtered=Vec::<String>::new();
     for l in s.lines(){
       let lc=l.to_ascii_lowercase();
       if ["tethered","downstream","upstream","offload","bpf","rndis","ncm","usb","wlan"].iter().any(|k|lc.contains(k)){
          // Retain only key names/booleans, not IP, MAC, SSID, lease or serial.
          let mask=l.chars().take(160).map(|c|if c.is_ascii_digit(){'#'}else{c}).collect::<String>();
          filtered.push(mask.trim().to_owned());
       }
       if filtered.len()>=14{break}
     }
     json!({"status":"OBSERVATION_ONLY","exit":v.status.code(),
       "filtered_redacted_lines":filtered,"not_actual_downstream_packet_proof":true})
   },
   Err(e)=>json!({"status":"UNAVAILABLE","errno":e.raw_os_error(),"reason":e.to_string()})
 }
}
pub fn run()->Value{
 let uid=unsafe{libc::getuid()};
 let euid=unsafe{libc::geteuid()};
 let status=read("/proc/self/status",5000);
 let caps=cap(&status,"CapEff:");
 let bounding=cap(&status,"CapBnd:");
 let c12=1u64<<12;let c13=1u64<<13;let c21=1u64<<21;
 let mut ifnames=Vec::new();
 if let Ok(entries)=fs::read_dir("/sys/class/net"){
   for x in entries.flatten(){
     if let Some(n)=x.file_name().to_str(){
       if n.len()<=15 && n.bytes().all(|b|b.is_ascii_alphanumeric()||b==b'_'||b==b'-'||b==b'.'){
           ifnames.push(n.to_owned())
       }
     }
   }
 }
 ifnames.sort();
 let effective=caps.unwrap_or(0);
 json!({"schema":"wbd-android-physical-readonly-root/v1",
  "status":if uid==0&&euid==0{"SUPPORTED_IN_SCOPE"}else{"PERMISSION_DENIED"},
  "identity":{"uid":uid,"euid":euid,"gid":unsafe{libc::getgid()},
   "selinux_context":read("/proc/self/attr/current",180),
   "selinux_enforce":read("/sys/fs/selinux/enforce",16),
   "cap_effective_hex":caps.map(|x|format!("{x:016x}")),
   "cap_bounding_hex":bounding.map(|x|format!("{x:016x}")),
   "cap_net_admin":effective&c12!=0,
   "cap_net_raw":effective&c13!=0,
   "cap_sys_admin":effective&c21!=0},
  "platform":{"api":prop("ro.build.version.sdk"),
    "release":prop("ro.build.version.release"),
    "security_patch":prop("ro.build.version.security_patch"),
    "cpu_abi":prop("ro.product.cpu.abi"),
    "kernel_release":read("/proc/sys/kernel/osrelease",160),
    "page_size":unsafe{libc::sysconf(libc::_SC_PAGESIZE)},
    "is_emulator":prop("ro.kernel.qemu")=="1"},
  "devices":{"tun_present":Path::new("/dev/tun").exists()||Path::new("/dev/net/tun").exists(),
    "net_interfaces":ifnames,
    "bpf_tethering_dir":Path::new("/sys/fs/bpf/tethering").exists(),
    "iptables":cmd_version("iptables","--version"),
    "ip":cmd_version("ip","-Version")},
  "tether_observation":relevant_dumpsys(),
  "real_wifi_hotspot_udp_tcp":"NOT_RUN",
  "real_usb_tether_udp_tcp":"NOT_RUN",
  "physical_tether_offload_bypass":"NOT_RUN",
  "underlay_raw_binding":"NOT_RUN",
  "system_dns_private_dns_ipv6_clat":"NOT_RUN",
  "note":"read-only system inventory; UID0/caps presence is not actual network capability. Real hotspot/USB need downstream packet counters and WBD data tunnel."})
}
