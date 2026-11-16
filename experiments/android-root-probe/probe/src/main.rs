//! Bounded Android capability experiment, not a VPN/client or root installer.
//! inspect is read-only; exercise only creates a short-lived owned TUN and loopback raw socket.
mod capgate;
mod routegate;
mod appflow;
mod mainstream;
mod tethergate;
mod recovery;
mod ipv6gate;
mod devicecheck;
mod android_split;
mod cn_geosite;
mod splitgate;
use serde_json::{json, Value};
use std::collections::BTreeMap;
use std::fs::{self, OpenOptions};
use std::io::{self, ErrorKind};
use std::net::UdpSocket;
use std::os::fd::{AsRawFd, RawFd};
use std::os::unix::fs::OpenOptionsExt;
use std::path::Path;
use std::process::{Command, Stdio};
use std::thread;
use std::time::{Duration, Instant};

const TUNSETIFF: libc::c_ulong = 0x4004_54ca;
const IFF_TUN: i16 = 0x0001;
const IFF_NO_PI: i16 = 0x1000;
const LOCAL: [u8; 4] = [198, 18, 251, 1];
const PEER: [u8; 4] = [198, 18, 251, 2];

struct Fd(RawFd);
impl Drop for Fd {
    fn drop(&mut self) {
        unsafe { libc::close(self.0); }
    }
}

fn read(path: &str, limit: usize) -> Value {
    match fs::read_to_string(path) {
        Ok(s) => json!({"status":"SUPPORTED_IN_SCOPE","value": s.chars().take(limit).collect::<String>().trim()}),
        Err(e) => json!({"status":classify(&e),"errno":e.raw_os_error(),"error":e.to_string()}),
    }
}
fn classify(e: &io::Error) -> &'static str {
    match e.raw_os_error() {
        Some(libc::EACCES | libc::EPERM) => "PERMISSION_DENIED",
        Some(libc::ENOENT | libc::ENODEV | libc::ENOSYS | libc::EOPNOTSUPP) => "UNAVAILABLE",
        _ => "FAIL",
    }
}
fn failure(action: &str, e: &io::Error) -> Value {
    json!({"status":classify(e),"action":action,"errno":e.raw_os_error(),"evidence":e.to_string()})
}
fn unavailable(reason: &str) -> Value {
    json!({"status":"NOT_RUN","reason":reason})
}
fn checksum(bytes: &[u8]) -> u16 {
    let mut acc: u32 = 0;
    for chunk in bytes.chunks(2) {
        let word = if chunk.len() == 2 {
            u16::from_be_bytes([chunk[0], chunk[1]])
        } else { u16::from_be_bytes([chunk[0], 0]) };
        acc += word as u32;
    }
    while acc >> 16 != 0 { acc = (acc & 0xffff) + (acc >> 16); }
    !(acc as u16)
}
fn ip_header(buf: &mut [u8], proto: u8, src: [u8; 4], dst: [u8; 4]) {
    buf[..20].fill(0);
    buf[0] = 0x45;
    let total_len = buf.len() as u16;
    buf[2..4].copy_from_slice(&total_len.to_be_bytes());
    buf[8] = 64;
    buf[9] = proto;
    buf[12..16].copy_from_slice(&src);
    buf[16..20].copy_from_slice(&dst);
    let sum = checksum(&buf[..20]);
    buf[10..12].copy_from_slice(&sum.to_be_bytes());
}
fn pseudo_checksum(src: [u8; 4], dst: [u8; 4], proto: u8, segment: &[u8]) -> u16 {
    let mut pseudo = Vec::with_capacity(12 + segment.len());
    pseudo.extend_from_slice(&src);
    pseudo.extend_from_slice(&dst);
    pseudo.extend_from_slice(&[0, proto]);
    pseudo.extend_from_slice(&(segment.len() as u16).to_be_bytes());
    pseudo.extend_from_slice(segment);
    checksum(&pseudo)
}
fn udp_packet(src: [u8; 4], dst: [u8; 4], sport: u16, dport: u16, data: &[u8]) -> Vec<u8> {
    let mut pkt = vec![0u8; 28 + data.len()];
    ip_header(&mut pkt, 17, src, dst);
    pkt[20..22].copy_from_slice(&sport.to_be_bytes());
    pkt[22..24].copy_from_slice(&dport.to_be_bytes());
    pkt[24..26].copy_from_slice(&((8 + data.len()) as u16).to_be_bytes());
    pkt[28..].copy_from_slice(data);
    let c = pseudo_checksum(src, dst, 17, &pkt[20..]);
    pkt[26..28].copy_from_slice(&(if c == 0 { 0xffff } else { c }).to_be_bytes());
    pkt
}
fn tcp_syn_packet() -> Vec<u8> {
    let addr = [127, 0, 0, 1];
    let mut pkt = vec![0u8; 40];
    ip_header(&mut pkt, 6, addr, addr);
    pkt[20..22].copy_from_slice(&49491u16.to_be_bytes());
    pkt[22..24].copy_from_slice(&49492u16.to_be_bytes());
    pkt[24..28].copy_from_slice(&0x6a1b2c3du32.to_be_bytes());
    pkt[32] = 0x50; // TCP header length 20
    pkt[33] = 0x02; // SYN; no application data
    pkt[34..36].copy_from_slice(&1024u16.to_be_bytes());
    let c = pseudo_checksum(addr, addr, 6, &pkt[20..]);
    pkt[36..38].copy_from_slice(&c.to_be_bytes());
    pkt
}
// Commands are narrowly scoped to our ephemeral interface. No shell, no global rule flush.
fn ip(args: &[&str]) -> io::Result<()> {
    let mut child = Command::new("ip").args(args).stdin(Stdio::null())
        .stdout(Stdio::null()).stderr(Stdio::null()).spawn()?;
    let deadline = Instant::now() + Duration::from_secs(3);
    loop {
        match child.try_wait()? {
            Some(exit) => return if exit.success() { Ok(()) } else {
                Err(io::Error::new(ErrorKind::Other, format!("ip {:?}: exit {}", args, exit)))
            },
            None if Instant::now() < deadline => thread::sleep(Duration::from_millis(30)),
            None => {
                let _ = child.kill();
                let _ = child.wait();
                return Err(io::Error::new(ErrorKind::TimedOut, "ip command 3s timeout"));
            }
        }
    }
}
fn wait_read(fd: RawFd, buf: &mut [u8], limit_ms: i32) -> io::Result<usize> {
    let mut pfd = libc::pollfd { fd, events: libc::POLLIN, revents: 0 };
    let ready = unsafe { libc::poll(&mut pfd, 1, limit_ms) };
    if ready < 0 { return Err(io::Error::last_os_error()); }
    if ready == 0 { return Err(io::Error::new(ErrorKind::TimedOut, "TUN/raw read timed out")); }
    let n = unsafe { libc::read(fd, buf.as_mut_ptr().cast(), buf.len()) };
    if n < 0 { Err(io::Error::last_os_error()) } else { Ok(n as usize) }
}
fn exercise_tun() -> Value {
    let path = ["/dev/tun", "/dev/net/tun"].iter().copied().find(|x| Path::new(x).exists());
    let Some(path) = path else {
        return json!({"status":"UNAVAILABLE","action":"TUNSETIFF","evidence":"Neither /dev/tun nor /dev/net/tun exists","cleanup":"no object"});
    };
    let name = format!("wbdp{:05x}", std::process::id() % 0xfffff);
    if Path::new(&format!("/sys/class/net/{name}")).exists() {
        return json!({"status":"FAIL","action":"preflight","evidence":"owned name collision, no changes"});
    }
    let file = match OpenOptions::new().read(true).write(true)
        .custom_flags(libc::O_NONBLOCK | libc::O_CLOEXEC).open(path) {
        Ok(f) => f, Err(e) => return failure("open TUN", &e)
    };
    let mut ifr = [0u8; 40]; // ifreq: 16-byte name + 24-byte union, x86_64/aarch64
    ifr[..name.len()].copy_from_slice(name.as_bytes());
    ifr[16..18].copy_from_slice(&(IFF_TUN | IFF_NO_PI).to_ne_bytes());
    let rc = unsafe { libc::ioctl(file.as_raw_fd(), TUNSETIFF as _, ifr.as_mut_ptr()) };
    if rc < 0 {
        return failure("TUNSETIFF (non-persistent, owned)", &io::Error::last_os_error());
    }
    let work = (|| -> io::Result<Value> {
        ip(&["link","set","dev",&name,"mtu","1400"])?;
        ip(&["-4","addr","add","198.18.251.1/30","dev",&name])?;
        ip(&["link","set","dev",&name,"up"])?;
        let mtu = fs::read_to_string(format!("/sys/class/net/{name}/mtu"))?;
        if mtu.trim() != "1400" {
            return Err(io::Error::new(ErrorKind::Other, "TUN MTU readback mismatch"));
        }
        // Verify kernel ingress independently before exercising policy-routed egress.
        let recv = UdpSocket::bind("198.18.251.1:0")?;
        recv.set_read_timeout(Some(Duration::from_millis(1200)))?;
        let reply = udp_packet(PEER, LOCAL, 49492, recv.local_addr()?.port(), b"wbd-tun-in");
        let wrote = unsafe { libc::write(file.as_raw_fd(), reply.as_ptr().cast(), reply.len()) };
        if wrote < 0 { return Err(io::Error::last_os_error()); }
        if wrote as usize != reply.len() {
            return Err(io::Error::new(ErrorKind::Other, "short TUN ingress write"));
        }
        let mut got = [0u8; 64];
        let (received, from) = recv.recv_from(&mut got)?;
        if &got[..received] != b"wbd-tun-in" || from.ip().to_string() != "198.18.251.2" {
            return Err(io::Error::new(ErrorKind::Other, "TUN injected IPv4 UDP not delivered"));
        }
        // Android netd rules do not guarantee an unmarked root socket uses main table.
        // Bind only this test sender to our owned device; do not edit netd or global fwmarks.
        let sender = UdpSocket::bind("198.18.251.1:0")?;
        let device = format!("{name}\0");
        let rc = unsafe { libc::setsockopt(sender.as_raw_fd(), libc::SOL_SOCKET, libc::SO_BINDTODEVICE,
            device.as_ptr().cast(), device.len() as libc::socklen_t) };
        if rc < 0 { return Err(io::Error::new(ErrorKind::PermissionDenied,
            format!("SO_BINDTODEVICE owned TUN: {}", io::Error::last_os_error()))); }
        sender.send_to(b"wbd-tun-out", "198.18.251.2:49492")?;
        let mut buf = [0u8; 2048];
        let deadline = Instant::now() + Duration::from_millis(1500);
        let mut matched = None;
        let mut other_count = 0usize;
        let mut other_samples = Vec::new();
        while Instant::now() < deadline {
            let remain = deadline.saturating_duration_since(Instant::now()).as_millis() as i32;
            if remain <= 0 { break; }
            let n = match wait_read(file.as_raw_fd(), &mut buf, remain.min(300)) {
                Ok(n) => n,
                Err(e) if e.kind() == ErrorKind::TimedOut => continue,
                Err(e) => return Err(e),
            };
            if n >= 28 && buf[0] >> 4 == 4 && buf[9] == 17 &&
                buf[12..16] == LOCAL && buf[16..20] == PEER &&
                &buf[28..n] == b"wbd-tun-out" {
                matched = Some(n);
                break;
            }
            other_count += 1;
            if other_samples.len() < 3 {
                let proto = if n > 9 { buf[9] } else { 0 };
                let version = if n > 0 { buf[0] >> 4 } else { 0 };
                let src = if n >= 20 { format!("{:?}", &buf[12..16]) } else { "short".to_owned() };
                let dst = if n >= 20 { format!("{:?}", &buf[16..20]) } else { "short".to_owned() };
                other_samples.push(format!("len={n},v={version},proto={proto},src={src},dst={dst}"));
            }
        }
        let n = matched.ok_or_else(|| io::Error::new(ErrorKind::TimedOut,
            format!("TUN expected owned UDP not seen in 1500ms; other_count={other_count}; samples={other_samples:?}")))?;
        Ok(json!({"read_bytes":n,"write_bytes":wrote,"mtu_readback":1400,"udp_echo":"kernel delivered to local UDP socket","scope":"owned TUN only","ignored_non_target_packets":other_count,"first_ignored":other_samples}))
    })();
    drop(file); // closes non-persistent TUN on normal and failed paths
    let cleaned = !Path::new(&format!("/sys/class/net/{name}")).exists();
    match work {
        Ok(evidence) if cleaned => json!({"status":"SUPPORTED_IN_SCOPE","action":"owned TUN read/write IPv4 UDP","evidence":evidence,"created":[name],"cleanup":"interface gone after fd close"}),
        Ok(evidence) => json!({"status":"FAIL","action":"owned TUN cleanup","evidence":evidence,"created":[name],"cleanup":"interface still present"}),
        Err(e) => json!({"status":if cleaned { classify(&e) } else {"FAIL"},"action":"owned TUN setup/traffic","errno":e.raw_os_error(),"evidence":e.to_string(),"created":[name],"cleanup":if cleaned {"interface gone"} else {"interface still present"}}),
    }
}
fn exercise_raw() -> Value {
    let fd = unsafe { libc::socket(libc::AF_INET, libc::SOCK_RAW | libc::SOCK_NONBLOCK | libc::SOCK_CLOEXEC, libc::IPPROTO_TCP) };
    if fd < 0 { return failure("socket(AF_INET, SOCK_RAW, IPPROTO_TCP)", &io::Error::last_os_error()); }
    let socket = Fd(fd);
    let mut size: libc::c_int = 65536;
    let set_buf = unsafe { libc::setsockopt(fd, libc::SOL_SOCKET, libc::SO_RCVBUF, (&size as *const libc::c_int).cast(), std::mem::size_of_val(&size) as libc::socklen_t) };
    let mut length = std::mem::size_of_val(&size) as libc::socklen_t;
    let get_buf = unsafe { libc::getsockopt(fd, libc::SOL_SOCKET, libc::SO_RCVBUF, (&mut size as *mut libc::c_int).cast(), &mut length) };
    let mut one: libc::c_int = 1;
    let hdr = unsafe { libc::setsockopt(fd, libc::IPPROTO_IP, libc::IP_HDRINCL, (&mut one as *mut libc::c_int).cast(), std::mem::size_of_val(&one) as libc::socklen_t) };
    if hdr != 0 { return failure("IP_HDRINCL on raw TCP socket", &io::Error::last_os_error()); }
    let dev = b"lo\0";
    let bind_rc = unsafe { libc::setsockopt(fd, libc::SOL_SOCKET, libc::SO_BINDTODEVICE, dev.as_ptr().cast(), dev.len() as libc::socklen_t) };
    let packet = tcp_syn_packet();
    let target = libc::sockaddr_in {
        sin_family: libc::AF_INET as libc::sa_family_t,
        sin_port: 0,
        sin_addr: libc::in_addr { s_addr: u32::from_ne_bytes([127,0,0,1]) },
        sin_zero: [0;8],
    };
    let sent = unsafe { libc::sendto(fd, packet.as_ptr().cast(), packet.len(), 0, (&target as *const libc::sockaddr_in).cast(), std::mem::size_of_val(&target) as libc::socklen_t) };
    if sent < 0 { return failure("raw TCP sendto loopback", &io::Error::last_os_error()); }
    let deadline = Instant::now() + Duration::from_millis(1500);
    let mut observed_syn = false;
    let mut observed_rst = false;
    let mut buf = [0u8; 4096];
    while Instant::now() < deadline {
        let n = match wait_read(fd, &mut buf, 150) { Ok(n) => n, Err(_) => continue };
        if n < 40 || buf[0] >> 4 != 4 || buf[9] != 6 { continue; }
        let ihl = usize::from(buf[0] & 0x0f) * 4;
        if ihl + 20 > n { continue; }
        if buf[12..16] != [127,0,0,1] || buf[16..20] != [127,0,0,1] { continue; }
        let sport = u16::from_be_bytes([buf[ihl],buf[ihl+1]]);
        let dport = u16::from_be_bytes([buf[ihl+2],buf[ihl+3]]);
        let flags = buf[ihl+13];
        if sport == 49491 && dport == 49492 && flags & 2 != 0 { observed_syn = true; }
        if sport == 49492 && dport == 49491 && flags & 4 != 0 { observed_rst = true; }
        if observed_syn && observed_rst { break; }
    }
    drop(socket);
    json!({
        "status":if observed_syn && observed_rst {"SUPPORTED_IN_SCOPE"} else {"UNAVAILABLE"},
        "action":"raw IPv4/TCP SYN send and RST observation on loopback",
        "scope":"lo only; not mobile/CLAT/physical egress",
        "evidence":{"sent_bytes":sent,"observed_syn":observed_syn,"observed_rst":observed_rst,"so_rcvbuf_set_ok":set_buf==0,"so_rcvbuf_get_ok":get_buf==0,"so_rcvbuf_readback_bytes":if get_buf==0 {Some(size)} else {None},"so_bindtodevice_lo_ok":bind_rc==0},
        "cleanup":"socket closed; no netfilter or route changes"
    })
}
fn interface_snapshots() -> Value {
    let mut out = BTreeMap::new();
    if let Ok(entries) = fs::read_dir("/sys/class/net") {
        for entry in entries.flatten() {
            if let Some(name) = entry.file_name().to_str() {
                let base = format!("/sys/class/net/{name}");
                out.insert(name.to_string(), json!({
                    "ifindex":read(&format!("{base}/ifindex"), 32),
                    "mtu":read(&format!("{base}/mtu"), 32),
                    "operstate":read(&format!("{base}/operstate"), 32),
                    "type":read(&format!("{base}/type"), 32)
                }));
            }
        }
    }
    json!(out)
}
fn usage() -> Value {
    let mut r: libc::rusage = unsafe { std::mem::zeroed() };
    let rc = unsafe { libc::getrusage(libc::RUSAGE_SELF, &mut r) };
    if rc != 0 { return failure("getrusage", &io::Error::last_os_error()); }
    json!({
        "utime_sec":r.ru_utime.tv_sec, "utime_usec":r.ru_utime.tv_usec,
        "stime_sec":r.ru_stime.tv_sec, "stime_usec":r.ru_stime.tv_usec,
        "voluntary_switches":r.ru_nvcsw, "involuntary_switches":r.ru_nivcsw,
        "maxrss_kib_linux":r.ru_maxrss
    })
}
fn main() {
    let mode = std::env::args().nth(1).unwrap_or_else(||"inspect".to_owned());
    if mode == "appflow" || mode == "appflow-kill" || mode=="appflow-mainstream" {
        let uid=std::env::args().nth(2).and_then(|x|x.parse::<u32>().ok()).unwrap_or(0);
        let token=std::env::args().nth(3).unwrap_or_default();
        let result=appflow::run(uid,&token,mode=="appflow-kill",mode=="appflow-mainstream");
        println!("WBD_APPFLOW_RESULT {}",serde_json::to_string(&result).unwrap());
        if result["status"]!="SUPPORTED_IN_SCOPE"{std::process::exit(1);}
        return;
    }
    if mode=="splitpolicy" {
        let r=android_split::pure();
        println!("WBD_SPLIT_POLICY_RESULT {}",serde_json::to_string(&r).unwrap());
        if r["status"]=="FAIL"{std::process::exit(1)}
        return;
    }
    if mode=="splitvalidate" {
        let path=std::env::args().nth(2).unwrap_or_default();
        let r=android_split::validate_file(&path);
        println!("WBD_SPLIT_CONFIG_RESULT {}",serde_json::to_string(&r).unwrap());
        if r["status"]!="SUPPORTED_IN_SCOPE"{std::process::exit(1)}
        return;
    }
    if mode=="splitgate" {
        let r=splitgate::run();
        println!("WBD_SPLIT_KERNEL_RESULT {}",serde_json::to_string(&r).unwrap());
        if r["status"]=="FAIL"{std::process::exit(1)}
        return;
    }
    if mode=="devicecheck" {
        let report=devicecheck::run();
        println!("WBD_DIAG_RESULT {}",serde_json::to_string(&report).unwrap());
        if report["status"]!="SUPPORTED_IN_SCOPE"{std::process::exit(1)}
        return;
    }
    if mode=="ipv6gate" {
        let report=ipv6gate::run();
        println!("WBD_IPV6_RESULT {}",serde_json::to_string(&report).unwrap());
        if report["status"]=="FAIL"{std::process::exit(1)}
        return;
    }
    if mode == "recover" || mode == "recover-seed" {
        let uid=std::env::args().nth(2).and_then(|x|x.parse::<u32>().ok()).unwrap_or(0);
        let result=if mode=="recover"{recovery::restore(uid)}else{recovery::seed(uid)};
        println!("WBD_RECOVERY_RESULT {}",serde_json::to_string(&result).unwrap());
        let ok=if mode=="recover" {
            result["status"]=="RESTORED"||result["status"]=="ALREADY_CLEAN"
        }else{result["status"]=="FIXTURE_SEEDED"};
        if !ok{std::process::exit(1)}
        return;
    }
    if mode == "tethergate" {
        let result=tethergate::run();
        println!("WBD_TETHER_RESULT {}",serde_json::to_string(&result).unwrap());
        if result["status"]=="FAIL"{std::process::exit(1)}
        return;
    }
    if mode == "routegate" {
        let result = routegate::run();
        println!("{}", serde_json::to_string_pretty(&result).unwrap());
        if result["status"] == "FAIL" { std::process::exit(1); }
        return;
    }
    if mode == "capgate" {
        let profile = std::env::args().nth(2).unwrap_or_default();
        let operation = std::env::args().nth(3).unwrap_or_default();
        let report = capgate::run(&profile, &operation);
        println!("{}", serde_json::to_string_pretty(&report).unwrap());
        if report["status"] == "FAIL" { std::process::exit(1); }
        return;
    }
    if mode != "inspect" && mode != "exercise" {
        eprintln!("usage: android-root-probe [inspect|exercise] (default inspect; no privilege acquisition)");
        std::process::exit(2);
    }
    let status_text = fs::read_to_string("/proc/self/status").unwrap_or_default();
    let proc_fields: BTreeMap<String,String> = status_text.lines()
        .filter_map(|line| line.split_once(':'))
        .filter(|(key,_)| ["CapInh","CapPrm","CapEff","CapBnd","CapAmb","Seccomp","VmRSS","Threads"].contains(key))
        .map(|(k,v)| (k.to_string(),v.trim().to_string())).collect();
    let mut checks = json!({
        "tun":unavailable("inspect only"),
        "raw_tcp":unavailable("inspect only"),
        "app_to_su":unavailable("requires real app process plus installed user-approved su; adb-root is separate"),
        "fwmark_policy_routing":unavailable("no safe unused netd mark/table allocation established"),
        "nat_conntrack_forwarding":unavailable("no controlled two-downstream fixture; no global rules touched"),
        "dns_udp_tcp53":unavailable("no controlled DNS fixture; do not change private DNS"),
        "ipv6_capture":unavailable("must avoid disrupting physical IPv6/CLAT"),
        "underlying_network_bind_switch":unavailable("lo binding is not mobile binding or change callback"),
        "foreground_service":unavailable("requires app targetSdk 37 lifecycle test"),
        "tether_wifi_usb_offload":unavailable("AVD cannot qualify OEM hotspot, USB or offload"),
        "owned_abnormal_exit":unavailable("TUN fd closure is automatic; kill of rule owner not tested")
    });
    if mode == "exercise" {
        checks["tun"] = exercise_tun();
        checks["raw_tcp"] = exercise_raw();
    }
    let report = json!({
        "schema":"android-root-probe/v1",
        "mode":mode,
        "execution_path":"must be supplied by caller; adb-root is NOT app-su",
        "platform":{"os":std::env::consts::OS,"abi":std::env::consts::ARCH,"page_size":unsafe {libc::sysconf(libc::_SC_PAGESIZE)},"kernel":read("/proc/version", 256)},
        "identity":{"uid":unsafe{libc::getuid()},"euid":unsafe{libc::geteuid()},"gid":unsafe{libc::getgid()},"egid":unsafe{libc::getegid()},"proc_status":proc_fields,"selinux_context":read("/proc/self/attr/current", 128),"selinux_enforce":read("/sys/fs/selinux/enforce", 8)},
        "network":{"interfaces":interface_snapshots(),"ip_forward":read("/proc/sys/net/ipv4/ip_forward",8),"route_ipv4":read("/proc/net/route",2000),"route_ipv6":read("/proc/net/ipv6_route",1200),"nf_tables":Path::new("/proc/net/netfilter").exists(),"bpf_tethering_dir":Path::new("/sys/fs/bpf/tethering").exists()},
        "checks":checks,
        "usage":usage(),
        "limitations":["No VpnService, no su acquisition, no changes to system/boot/SELinux","No proof of cellular raw, real hotspot/USB, CLAT, OEM offload, Android Network callback, VPN icon or mobile power","SO_RCVBUF Linux readback is typically doubled; recorded as actual kernel value"]
    });
    println!("{}",serde_json::to_string_pretty(&report).unwrap());
    if mode == "exercise" && (report["checks"]["tun"]["status"] == "FAIL" || report["checks"]["raw_tcp"]["status"] == "FAIL") {
        std::process::exit(1);
    }
}
