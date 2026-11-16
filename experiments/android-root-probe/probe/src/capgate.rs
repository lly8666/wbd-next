//! Isolated reduced-capability native gate. Never exec after capset.
//! Direct owned TUNSETIFF and raw IPv4/TCP loopback only; no system route edits.
use super::{classify, exercise_raw, failure, IFF_NO_PI, IFF_TUN, TUNSETIFF};
use serde_json::{json, Value};
use std::fs::{self, OpenOptions};
use std::io;
use std::os::fd::AsRawFd;
use std::os::unix::fs::OpenOptionsExt;
use std::path::Path;

const CAP_VERSION_3: u32 = 0x2008_0522;
const CAP_NET_ADMIN: u64 = 1 << 12;
const CAP_NET_RAW: u64 = 1 << 13;
#[repr(C)]
struct CapHeader { version: u32, pid: i32 }
#[repr(C)]
struct CapData { effective: u32, permitted: u32, inheritable: u32 }

fn status_caps() -> Value {
    let text = fs::read_to_string("/proc/self/status").unwrap_or_default();
    let mut values = serde_json::Map::new();
    for line in text.lines() {
        if let Some((key, val)) = line.split_once(':') {
            if ["CapEff","CapPrm","CapInh","CapBnd","CapAmb","Seccomp"].contains(&key) {
                values.insert(key.into(), json!(val.trim()));
            }
        }
    }
    Value::Object(values)
}
fn gate_tun() -> Value {
    let path = ["/dev/tun", "/dev/net/tun"].iter().copied().find(|x| Path::new(x).exists());
    let Some(path) = path else {
        return json!({"status":"UNAVAILABLE","action":"TUN device absent","cleanup":"nothing created"});
    };
    let name = format!("wbdg{:05x}", std::process::id() % 0xfffff);
    if Path::new(&format!("/sys/class/net/{name}")).exists() {
        return json!({"status":"FAIL","action":"owned TUN name collision","cleanup":"not attempted"});
    }
    let file = match OpenOptions::new().read(true).write(true)
        .custom_flags(libc::O_NONBLOCK | libc::O_CLOEXEC).open(path) {
        Ok(f) => f, Err(e) => return failure("open TUN device", &e),
    };
    let mut ifr = [0u8; 40];
    ifr[..name.len()].copy_from_slice(name.as_bytes());
    ifr[16..18].copy_from_slice(&(IFF_TUN | IFF_NO_PI).to_ne_bytes());
    let rc = unsafe { libc::ioctl(file.as_raw_fd(), TUNSETIFF as _, ifr.as_mut_ptr()) };
    let err = if rc < 0 { Some(io::Error::last_os_error()) } else { None };
    let existed = Path::new(&format!("/sys/class/net/{name}")).exists();
    drop(file);
    let cleaned = !Path::new(&format!("/sys/class/net/{name}")).exists();
    match err {
        Some(e) => json!({"status":if cleaned {classify(&e)} else {"FAIL"},
            "action":"TUNSETIFF with restricted CapEff/CapPrm","errno":e.raw_os_error(),
            "evidence":e.to_string(),"created":existed,"cleanup":if cleaned {"no owned interface"} else {"LEAK"}}),
        None => json!({"status":if existed && cleaned {"SUPPORTED_IN_SCOPE"} else {"FAIL"},
            "action":"TUNSETIFF with restricted CapEff/CapPrm",
            "created":existed,"cleanup":if cleaned {"interface gone after close"} else {"LEAK"},
            "scope":"create+close only; does not validate MTU, UDP or policy routing at reduced caps"})
    }
}
pub(super) fn run(profile: &str, operation: &str) -> Value {
    let mask = match profile {
        "none" => 0u64, "netadmin" => CAP_NET_ADMIN,
        "netraw" => CAP_NET_RAW, "both" => CAP_NET_ADMIN | CAP_NET_RAW,
        _ => return json!({"status":"FAIL","reason":"invalid profile"}),
    };
    if operation != "tun" && operation != "raw" {
        return json!({"status":"FAIL","reason":"operation must be tun|raw"});
    }
    let before = status_caps();
    let uid = unsafe { libc::getuid() };
    let euid = unsafe { libc::geteuid() };
    let selinux = fs::read_to_string("/proc/self/attr/current").unwrap_or_default().trim().to_owned();
    let nnp_rc = unsafe { libc::prctl(libc::PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) };
    if nnp_rc != 0 {
        return json!({"status":"FAIL","operation":operation,"profile":profile,
            "action":"PR_SET_NO_NEW_PRIVS","errno":io::Error::last_os_error().raw_os_error()});
    }
    let mut hdr = CapHeader { version: CAP_VERSION_3, pid: 0 };
    let bits = mask as u32;
    let mut data = [
        CapData { effective: bits, permitted: bits, inheritable: 0 },
        CapData { effective: 0, permitted: 0, inheritable: 0 },
    ];
    let rc = unsafe { libc::syscall(libc::SYS_capset, &mut hdr as *mut CapHeader, data.as_mut_ptr()) };
    if rc != 0 {
        return json!({"status":"FAIL","operation":operation,"profile":profile,
            "action":"capset(V3)","errno":io::Error::last_os_error().raw_os_error(),
            "caps_before":before,"uid":uid,"euid":euid,"selinux":selinux});
    }
    let after = status_caps();
    let expected = format!("{mask:016x}");
    let verified = after["CapEff"].as_str() == Some(expected.as_str())
        && after["CapPrm"].as_str() == Some(expected.as_str())
        && after["CapInh"].as_str() == Some("0000000000000000");
    let nnp = unsafe { libc::prctl(libc::PR_GET_NO_NEW_PRIVS, 0, 0, 0, 0) };
    if !verified || nnp != 1 {
        return json!({"status":"FAIL","operation":operation,"profile":profile,
            "action":"verify caps+NNP","expected":expected,
            "caps_before":before,"caps_after":after,"no_new_privs":nnp,"uid":uid,"euid":euid});
    }
    let check = if operation == "tun" { gate_tun() } else { exercise_raw() };
    json!({"schema":"android-root-capgate/v1","status":"CAPSET_VERIFIED",
        "execution_path":"adb-root caller; NOT app su","operation":operation,"profile":profile,
        "requested_caps":expected,"uid":uid,"euid":euid,"selinux":selinux,"no_new_privs":nnp,
        "caps_before":before,"caps_after":after,"check":check,
        "limitations":["CapBnd and UID0 unchanged; this proves only isolated CapEff/CapPrm/CapInh gate under AOSP su SELinux domain",
           "No exec after capset; TUN only create+cleanup, raw only loopback",
           "No app-su, fwmark, netfilter/NAT, real physical network or hotspot/USB tested"]})
}
