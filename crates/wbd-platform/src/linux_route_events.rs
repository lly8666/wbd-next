//! One bounded Linux route/link netlink listener shared by live Rust owner sessions.
//! A notification invalidates an owner-scoped snapshot; it is NOT proof of a
//! new MTU or permission to send. The owner must re-observe its existing M4
//! route and link constraints before accepting another DATA packet.
//! This opt-in development path retains M4's per-send kernel/MTU protection.
#![cfg(all(target_os="linux",target_arch="x86_64",target_env="gnu"))]
use std::ffi::{c_int,c_void};
use std::io;
use std::os::fd::{AsRawFd,FromRawFd,OwnedFd};
use std::sync::{Arc,Mutex,OnceLock,Weak,atomic::{AtomicBool,AtomicU64,Ordering}};
use std::time::{Duration,Instant};

const AF_NETLINK:c_int=16;
const SOCK_RAW:c_int=3;
const SOCK_NONBLOCK:c_int=0x800;
const SOCK_CLOEXEC:c_int=0x80000;
const NETLINK_ROUTE:c_int=0;
const RTMGRP_LINK:u32=1;
const RTMGRP_IPV4_ROUTE:u32=0x40;
const POLLIN:i16=1;
const EINTR:i32=4;
const EAGAIN:i32=11;
const ENOBUFS:i32=105;
const REFRESH_COALESCE:Duration=Duration::from_millis(100);
#[repr(C)]
#[derive(Default)]
struct SockAddrNl {family:u16,pad:u16,pid:u32,groups:u32}
#[repr(C)]
struct PollFd {fd:c_int,events:i16,revents:i16}
unsafe extern "C" {
    fn socket(domain:c_int,kind:c_int,protocol:c_int)->c_int;
    fn bind(fd:c_int,address:*const c_void,len:u32)->c_int;
    fn poll(fds:*mut PollFd,count:usize,timeout:c_int)->c_int;
    fn recvfrom(fd:c_int,buf:*mut c_void,len:usize,flags:c_int,
        address:*mut c_void,address_len:*mut u32)->isize;
}
fn errno()->i32{io::Error::last_os_error().raw_os_error().unwrap_or(5)}

/// No packet path syscall and no per-lane listener. Weak ownership causes the
/// sole watcher to release its FD shortly after the last session stops.
static WATCH:OnceLock<Mutex<Weak<RouteEvents>>>=OnceLock::new();
pub struct RouteEvents {revision:AtomicU64,healthy:AtomicBool}
#[derive(Clone,Copy,Debug)]
pub struct RouteEventSnapshot {pub revision:u64,pub healthy:bool}
impl RouteEvents {
    pub fn snapshot(&self)->RouteEventSnapshot{
        RouteEventSnapshot{
            revision:self.revision.load(Ordering::Acquire),
            healthy:self.healthy.load(Ordering::Acquire),
        }
    }
    fn changed(&self){self.revision.fetch_add(1,Ordering::AcqRel);}
    fn failed(&self){
        self.healthy.store(false,Ordering::Release);
        self.changed();
    }
}
fn open_listener()->io::Result<OwnedFd>{
    let fd=unsafe{socket(AF_NETLINK,SOCK_RAW|SOCK_NONBLOCK|SOCK_CLOEXEC,NETLINK_ROUTE)};
    if fd<0{return Err(io::Error::last_os_error())}
    let owned=unsafe{OwnedFd::from_raw_fd(fd)};
    let addr=SockAddrNl{
        family:AF_NETLINK as u16,groups:RTMGRP_LINK|RTMGRP_IPV4_ROUTE,
        ..SockAddrNl::default()
    };
    let rc=unsafe{bind(owned.as_raw_fd(),&addr as *const _ as *const c_void,
        std::mem::size_of::<SockAddrNl>() as u32)};
    if rc<0{return Err(io::Error::last_os_error())}
    Ok(owned)
}
/// Called only on owner start, never on per-DATA path.
pub fn subscribe()->Arc<RouteEvents>{
    let mutex=WATCH.get_or_init(||Mutex::new(Weak::new()));
    let mut previous=mutex.lock().expect("route watcher registry poisoned");
    if let Some(existing)=previous.upgrade(){return existing}
    let new=Arc::new(RouteEvents{
        revision:AtomicU64::new(1),healthy:AtomicBool::new(false)
    });
    match open_listener(){
        Ok(fd)=>{
            let weak=Arc::downgrade(&new);
            // Publish initial health BEFORE starting the worker. Otherwise
            // an immediate poll/recv failure could be overwritten as healthy.
            new.healthy.store(true,Ordering::Release);
            if std::thread::Builder::new().name("wbd-route-link-watch".into())
                .spawn(move||watch(fd,weak)).is_err(){
                new.failed();
            }
        }
        Err(_)=>{} // 1s owner fallback and live M4 check remain mandatory
    }
    *previous=Arc::downgrade(&new);
    new
}
fn watch(fd:OwnedFd, weak:Weak<RouteEvents>){
    let mut last_bump:Option<Instant>=None;
    let mut pending=false;
    let mut buf=[0u8;8192]; // never heap-allocate per netlink event
    loop{
        let Some(state)=weak.upgrade() else {break};
        let mut p=PollFd{fd:fd.as_raw_fd(),events:POLLIN,revents:0};
        let n=unsafe{poll(&mut p,1,25)};
        if n<0{
            if errno()==EINTR{continue}
            state.failed();break
        }
        if n>0 && p.revents&POLLIN==0{state.failed();break}
        if n>0 {
            // Drain all currently ready notifications into one invalidation.
            loop{
                let mut sender=SockAddrNl::default();
                let mut sender_len=std::mem::size_of::<SockAddrNl>() as u32;
                let received=unsafe{recvfrom(fd.as_raw_fd(),buf.as_mut_ptr() as *mut c_void,
                    buf.len(),0,&mut sender as *mut _ as *mut c_void,&mut sender_len)};
                if received<0{
                    match errno(){
                        EINTR=>continue,
                        EAGAIN=>break,
                        ENOBUFS=>{pending=true;break}, // lost notification => invalidate
                        _=>{state.failed();return}
                    }
                }
                if received==0{break}
                if sender_len as usize==std::mem::size_of::<SockAddrNl>()
                    && sender.pid==0{pending=true}
            }
        }
        if pending && last_bump.is_none_or(|t|t.elapsed()>=REFRESH_COALESCE){
            state.changed();
            pending=false;
            last_bump=Some(Instant::now());
        }
    }
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub enum EventRefresh {Unchanged,Defer,Refresh}
/// Debounce a storm: do not repeatedly query the kernel on every DATA.
/// Defer means FAIL CLOSED for this scope until a bounded refresh is allowed.
pub fn classify(cached:u64,observed:u64,age:Duration)->EventRefresh{
    if cached==observed {EventRefresh::Unchanged}
    else if age<REFRESH_COALESCE {EventRefresh::Defer}
    else {EventRefresh::Refresh}
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn event_storm_coalesces_without_using_old_budget(){
        assert_eq!(classify(3,3,Duration::ZERO),EventRefresh::Unchanged);
        assert_eq!(classify(3,4,Duration::ZERO),EventRefresh::Defer);
        assert_eq!(classify(3,4,Duration::from_millis(99)),EventRefresh::Defer);
        assert_eq!(classify(3,4,Duration::from_millis(100)),EventRefresh::Refresh);
        assert_eq!(classify(3,5,Duration::from_secs(1)),EventRefresh::Refresh);
    }
}
