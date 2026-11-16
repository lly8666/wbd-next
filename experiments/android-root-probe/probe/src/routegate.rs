//! One live policy-route packet, only inside a provably separate EMPTY Linux netns.
//! If namespace creation/verification fails, stop before modifying ANY network state.
use super::{ip,wait_read,IFF_NO_PI,IFF_TUN,TUNSETIFF};
use serde_json::{json,Value};
use std::fs::{self,File,OpenOptions};
use std::io::{self,ErrorKind};
use std::net::UdpSocket;
use std::os::fd::AsRawFd;
use std::os::unix::fs::OpenOptionsExt;
use std::path::Path;
use std::time::{Instant,Duration};
const DATA:&[u8]=b"wbd-ns-mark";
fn ns()->io::Result<String>{
    Ok(fs::read_link("/proc/self/ns/net")?.to_string_lossy().into_owned())
}
fn tun()->io::Result<(File,String)>{
    let p=["/dev/tun","/dev/net/tun"].iter().copied()
        .find(|x|Path::new(x).exists())
        .ok_or_else(||io::Error::new(ErrorKind::NotFound,"no TUN device"))?;
    let name=format!("wbdn{:05x}",std::process::id()%0xfffff);
    if Path::new(&format!("/sys/class/net/{name}")).exists(){
        return Err(io::Error::new(ErrorKind::AlreadyExists,"TUN collision"));
    }
    let f=OpenOptions::new().read(true).write(true)
        .custom_flags(libc::O_NONBLOCK|libc::O_CLOEXEC).open(p)?;
    let mut ifr=[0u8;40];
    ifr[..name.len()].copy_from_slice(name.as_bytes());
    ifr[16..18].copy_from_slice(&(IFF_TUN|IFF_NO_PI).to_ne_bytes());
    if unsafe{libc::ioctl(f.as_raw_fd(),TUNSETIFF as _,ifr.as_mut_ptr())}<0{
        return Err(io::Error::last_os_error());
    }
    Ok((f,name))
}
fn fixture(f:&File,name:&str)->io::Result<Value>{
    // Every child inherits the freshly verified network namespace.
    ip(&["link","set","dev",name,"mtu","1400"])?;
    ip(&["-4","addr","add","198.18.253.1/30","dev",name])?;
    ip(&["link","set","dev",name,"up"])?;
    ip(&["-4","route","add","198.18.254.2/32","dev",name,
        "src","198.18.253.1","table","235"])?;
    ip(&["-4","rule","add","pref","12000","fwmark",
        "0x23500/0xffffffff","lookup","235"])?;
    let no=UdpSocket::bind("198.18.253.1:0")?
        .send_to(DATA,"198.18.254.2:49492");
    if !matches!(no,Err(ref e) if e.raw_os_error()==Some(libc::ENETUNREACH)
            ||e.raw_os_error()==Some(libc::EHOSTUNREACH)){
        return Err(io::Error::new(ErrorKind::Other,format!("unmarked negative failed: {no:?}")));
    }
    let s=UdpSocket::bind("198.18.253.1:0")?;
    const SO_MARK_ANDROID:libc::c_int=36;
    let mark:libc::c_int=0x23500;
    if unsafe{libc::setsockopt(s.as_raw_fd(),libc::SOL_SOCKET,SO_MARK_ANDROID,
        (&mark as *const libc::c_int).cast(),
        std::mem::size_of_val(&mark) as libc::socklen_t)}<0{
        return Err(io::Error::last_os_error());
    }
    let mut got:libc::c_int=0;
    let mut len=std::mem::size_of_val(&got) as libc::socklen_t;
    if unsafe{libc::getsockopt(s.as_raw_fd(),libc::SOL_SOCKET,SO_MARK_ANDROID,
        (&mut got as *mut libc::c_int).cast(),&mut len)}<0{
        return Err(io::Error::last_os_error());
    }
    if got!=mark{return Err(io::Error::new(ErrorKind::Other,"SO_MARK readback differs"));}
    let sent=s.send_to(DATA,"198.18.254.2:49492")?;
    if sent!=DATA.len(){return Err(io::Error::new(ErrorKind::Other,"UDP short send"));}
    let end=Instant::now()+Duration::from_millis(1500);
    let mut buf=[0u8;2048];
    let mut matched=0usize;
    let mut ignored=0usize;
    while Instant::now()<end{
        let left=end.saturating_duration_since(Instant::now()).as_millis() as i32;
        if left<=0{break;}
        let n=match wait_read(f.as_raw_fd(),&mut buf,left.min(300)){
            Ok(n)=>n,
            Err(e) if e.kind()==ErrorKind::TimedOut=>continue,
            Err(e)=>return Err(e),
        };
        if n>=28 && buf[0]>>4==4 && buf[9]==17 &&
           buf[12..16]==[198,18,253,1] && buf[16..20]==[198,18,254,2] &&
           &buf[28..n]==DATA {matched=n;break;}
        ignored+=1;
    }
    if matched==0{return Err(io::Error::new(ErrorKind::TimedOut,
        format!("no marked packet on owned TUN; ignored={ignored}")));}
    let mtu=fs::read_to_string(format!("/sys/class/net/{name}/mtu"))?;
    if mtu.trim()!="1400"{return Err(io::Error::new(ErrorKind::Other,"MTU mismatch"));}
    Ok(json!({"unmarked_negative":true,"marked_udp_tun_read_bytes":matched,
        "SO_MARK_readback":got,"mtu_readback":1400,"ignored_packets":ignored,
        "scope":"private netns route table235/rule12000 only; not Android netd/NAT/tether"}))
}
pub(super) fn run()->Value{
    let before=match ns(){
        Ok(x)=>x,
        Err(e)=>return json!({"status":"ENV_BLOCKED","action":"read /proc/self/ns/net",
            "errno":e.raw_os_error(),"evidence":e.to_string(),"global_changes":false}),
    };
    if unsafe{libc::geteuid()}!=0{return json!({"status":"PERMISSION_DENIED",
        "action":"externally supplied adb-root required","global_changes":false});}
    if unsafe{libc::unshare(libc::CLONE_NEWNET)}!=0{
        let e=io::Error::last_os_error();
        return json!({"status":"ENV_BLOCKED","action":"unshare(CLONE_NEWNET)",
            "errno":e.raw_os_error(),"evidence":e.to_string(),"before":before,
            "global_changes":false,"route":"NOT_RUN"});
    }
    let after=match ns(){
        Ok(x)=>x,
        Err(e)=>return json!({"status":"ENV_BLOCKED","action":"read new netns ID",
            "errno":e.raw_os_error(),"global_changes":false,"route":"NOT_RUN"}),
    };
    if before==after{return json!({"status":"FAIL","action":"namespace not distinct",
        "before":before,"after":after,"global_changes":false});}
    let mut interfaces=Vec::new();
    match fs::read_dir("/sys/class/net"){
        Ok(xs)=>for x in xs.flatten(){
            if let Some(n)=x.file_name().to_str(){interfaces.push(n.to_owned());}
        },
        Err(e)=>return json!({"status":"ENV_BLOCKED","action":"network namespace inventory",
            "errno":e.raw_os_error(),"global_changes":false,"route":"NOT_RUN"}),
    }
    interfaces.sort();
    if interfaces.len()!=1 || interfaces[0]!="lo"{
        return json!({"status":"ENV_BLOCKED","action":"netns not empty lo-only",
            "interfaces":interfaces,"before":before,"after":after,
            "global_changes":false,"route":"NOT_RUN"});
    }
    // No netlink mutation is reachable above this exact distinct-netns + lo-only guard.
    let (f,name)=match tun(){
        Ok(x)=>x,
        Err(e)=>return json!({"status":"FAIL","action":"create only private owned TUN",
            "errno":e.raw_os_error(),"evidence":e.to_string(),"global_changes":false}),
    };
    let v=fixture(&f,&name);
    drop(f);
    let clean=!Path::new(&format!("/sys/class/net/{name}")).exists();
    match v{
        Ok(data) if clean=>json!({"status":"SUPPORTED_IN_SCOPE","before":before,
            "after":after,"interfaces_before":["lo"],"evidence":data,
            "cleanup":"owned TUN interface gone; private namespace exits with process",
            "global_changes":false,"real_netd_nat_tether":"NOT_RUN"}),
        Ok(data)=>json!({"status":"FAIL","action":"owned cleanup","evidence":data,
            "global_changes":false}),
        Err(e)=>json!({"status":"FAIL","action":"isolated policy-route live packet",
            "errno":e.raw_os_error(),"evidence":e.to_string(),
            "before":before,"after":after,"cleanup":if clean {"TUN gone"}else{"namespace exit"},
            "global_changes":false}),
    }
}
