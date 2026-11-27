//! Existing Linux socket ABI, no listener, thread or polling loop.
use std::{ffi::{c_int,c_void},io,net::{SocketAddrV4,TcpStream},os::fd::{AsRawFd,FromRawFd,OwnedFd}};
#[repr(C)]
struct Addr4 { family:u16,port:u16,addr:u32,pad:[u8;8] }
unsafe extern "C" {
    fn socket(domain:c_int,kind:c_int,protocol:c_int)->c_int;
    fn connect(fd:c_int,addr:*const c_void,len:u32)->c_int;
}
pub(crate) fn connect_origin(target:SocketAddrV4)->io::Result<(TcpStream,bool)> {
    let raw=unsafe{socket(2,1|0x800|0x80000,6)};
    if raw<0 { return Err(io::Error::last_os_error()) }
    let fd=unsafe{OwnedFd::from_raw_fd(raw)};
    let addr=Addr4{family:2,port:target.port().to_be(),
        addr:u32::from_ne_bytes(target.ip().octets()),pad:[0;8]};
    let n=unsafe{connect(fd.as_raw_fd(),(&addr as *const Addr4).cast(),16)};
    let ready=if n==0 { true } else {
        let e=io::Error::last_os_error();
        if e.raw_os_error()!=Some(115) { return Err(e) }
        false
    };
    let stream=TcpStream::from(fd);
    stream.set_nodelay(true)?;
    Ok((stream,ready))
}
