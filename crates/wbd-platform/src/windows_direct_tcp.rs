//! PLAN029 selected DIRECT-only Windows kernel TCP backend: one local
//! kernel listener plus one real physical-source/ifindex-bound WinSock TCP
//! socket per accepted Direct flow. The original tunnel TCP is NEVER
//! terminated or passed through this relay. No gVisor or old WFP guard.
//! The current Rust native owner has to compose one Wintun NAT dispatcher,
//! a bounded readiness scheduler and this per-flow zero-thread relay.
//! This module alone does not create an authenticated product/GUI Ready.
use std::io::{Read,Write,ErrorKind};
use std::net::{Ipv4Addr,SocketAddrV4,Shutdown,TcpStream,TcpListener};
use std::collections::VecDeque;

#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub enum DirectTcpError{
    InvalidUnderlay,
    SocketCreate(i32),
    SocketBind(i32),
    InterfaceOptionSet(i32),
    InterfaceOptionRead(i32),
    InterfaceOptionMismatch{requested:u32,observed:u32},
    SocketNonblocking(i32),
    SocketConnect(i32),
    PeerFailed,
    ListenerBind,
    RelayIo,
    BufferBudget,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub enum ConnectProgress{Pending,Connected}

#[cfg(target_os="windows")]
mod win{
    use super::*;
    use std::ffi::c_void;
    use std::os::windows::io::{FromRawSocket,AsRawSocket,RawSocket};
    const AF_INET:i32=2;
    const SOCK_STREAM:i32=1;
    const IPPROTO_TCP:i32=6;
    const IP_UNICAST_IF:i32=31;
    const FIONBIO:i32=0x8004667eu32 as i32;
    const WSAEWOULDBLOCK:i32=10035;
    const WSAEINPROGRESS:i32=10036;
    const WSAEALREADY:i32=10037;
    const INVALID_SOCKET:usize=usize::MAX;
    #[repr(C)]
    struct SockAddrIn{
        family:u16,port:u16,address:u32,zero:[u8;8],
    }
    impl SockAddrIn{
        fn new(addr:Ipv4Addr,port:u16)->Self{
            Self{family:AF_INET as u16,port:port.to_be(),
                address:u32::from_ne_bytes(addr.octets()),zero:[0;8]}
        }
    }
    #[link(name="Ws2_32")]
    extern "system" {
        fn socket(af:i32,kind:i32,proto:i32)->usize;
        fn closesocket(s:usize)->i32;
        fn bind(s:usize,name:*const c_void,len:i32)->i32;
        fn connect(s:usize,name:*const c_void,len:i32)->i32;
        fn ioctlsocket(s:usize,cmd:i32,arg:*mut u32)->i32;
        fn setsockopt(s:usize,level:i32,opt:i32,p:*const i8,len:i32)->i32;
        fn getsockopt(s:usize,level:i32,opt:i32,p:*mut i8,len:*mut i32)->i32;
        fn WSAGetLastError()->i32;
    }
    struct SocketGuard(usize);
    impl Drop for SocketGuard{
        fn drop(&mut self){if self.0!=INVALID_SOCKET{unsafe{closesocket(self.0);}}}
    }
    impl SocketGuard{
        fn disown(&mut self)->RawSocket{
            let v=self.0;
            self.0=INVALID_SOCKET;
            v as RawSocket
        }
    }
    fn last()->i32{unsafe{WSAGetLastError()}}
    /// One owned physical socket. Its remote is always the real DNS A/IP
    /// selected by current-generation Direct policy, NEVER its FakeIP.
    /// connect() is nonblocking: caller's one Rust readiness worker polls
    /// completion using poll_connected; no per-flow threads/dial timeouts.
    pub struct PhysicalTcpSocket{
        stream:TcpStream,
        remote:SocketAddrV4,
        source:Ipv4Addr,
        ifindex:u32,
        progress:ConnectProgress,
    }
    impl PhysicalTcpSocket{
        pub fn start(source:Ipv4Addr,ifindex:u32,real:SocketAddrV4)
            ->Result<Self,DirectTcpError>{
            if ifindex==0||ifindex==u32::MAX||source.is_unspecified()||
                source.is_loopback()||source.is_multicast()||source.is_broadcast()||
                real.ip().is_loopback()||real.ip().is_unspecified()||
                real.ip().is_multicast()||real.port()==0{
                return Err(DirectTcpError::InvalidUnderlay)
            }
            let raw=unsafe{socket(AF_INET,SOCK_STREAM,IPPROTO_TCP)};
            if raw==INVALID_SOCKET{
                return Err(DirectTcpError::SocketCreate(last()))
            }
            let mut guard=SocketGuard(raw);
            let nindex=ifindex.to_be();
            let rc=unsafe{setsockopt(raw,0,IP_UNICAST_IF,
                (&nindex as *const u32).cast(),4)};
            if rc!=0{return Err(DirectTcpError::InterfaceOptionSet(last()))}
            // WinSock IPv4 IP_UNICAST_IF SET uses network-order index,
            // GET returns host-order DWORD (verified by H1703 UDP Win32).
            let mut got=0u32;let mut size=4i32;
            let rc=unsafe{getsockopt(raw,0,IP_UNICAST_IF,
                (&mut got as *mut u32).cast(),&mut size)};
            if rc!=0{return Err(DirectTcpError::InterfaceOptionRead(last()))}
            if size!=4||got!=ifindex{
                return Err(DirectTcpError::InterfaceOptionMismatch{
                    requested:ifindex,observed:got})
            }
            let local=SockAddrIn::new(source,0);
            let rc=unsafe{bind(raw,(&local as *const SockAddrIn).cast(),16)};
            if rc!=0{return Err(DirectTcpError::SocketBind(last()))}
            let mut nonblocking=1u32;
            let rc=unsafe{ioctlsocket(raw,FIONBIO,&mut nonblocking)};
            if rc!=0{return Err(DirectTcpError::SocketNonblocking(last()))}
            let dst=SockAddrIn::new(*real.ip(),real.port());
            let rc=unsafe{connect(raw,(&dst as *const SockAddrIn).cast(),16)};
            let progress=if rc==0{ConnectProgress::Connected}else{
                let code=last();
                if code==WSAEWOULDBLOCK||code==WSAEINPROGRESS||code==WSAEALREADY{
                    ConnectProgress::Pending
                }else{return Err(DirectTcpError::SocketConnect(code))}
            };
            // After the nonblocking connect result, std owns CloseSocket.
            let stream=unsafe{TcpStream::from_raw_socket(guard.disown())};
            Ok(Self{stream,remote:real,source,ifindex,progress})
        }
        pub fn peer(&self)->SocketAddrV4{self.remote}
        pub fn underlay(&self)->(Ipv4Addr,u32){(self.source,self.ifindex)}
        pub fn progress(&self)->ConnectProgress{self.progress}
        pub fn poll_connected(&mut self)->Result<ConnectProgress,DirectTcpError>{
            if self.progress==ConnectProgress::Connected{
                return Ok(self.progress)
            }
            if self.stream.take_error().map_err(|_|DirectTcpError::RelayIo)?.is_some(){
                return Err(DirectTcpError::PeerFailed)
            }
            match self.stream.peer_addr(){
                Ok(std::net::SocketAddr::V4(addr)) if addr==self.remote=>{
                    self.progress=ConnectProgress::Connected;
                    Ok(self.progress)
                }
                Ok(_)=>Err(DirectTcpError::PeerFailed),
                Err(e) if matches!(e.kind(),ErrorKind::WouldBlock|
                    ErrorKind::NotConnected)=>Ok(ConnectProgress::Pending),
                Err(_)=>Err(DirectTcpError::PeerFailed),
            }
        }
        /// Must be called only after poll_connected returned Connected.
        pub fn into_connected_stream(self)->Result<TcpStream,DirectTcpError>{
            if self.progress!=ConnectProgress::Connected{
                return Err(DirectTcpError::PeerFailed)
            }
            Ok(self.stream)
        }
    }
    /// One current generation owned /32 Windows kernel listener. The
    /// caller must install exactly one synthetic-peer route and NAT key
    /// mapping; it cannot receive arbitrary raw Wintun TCP packets.
    pub fn open_kernel_tcp_listener(owned_lease:Ipv4Addr)
        ->Result<TcpListener,DirectTcpError>{
        if owned_lease.is_loopback()||owned_lease.is_unspecified(){
            return Err(DirectTcpError::InvalidUnderlay)
        }
        let listener=TcpListener::bind(SocketAddrV4::new(owned_lease,0))
            .map_err(|_|DirectTcpError::ListenerBind)?;
        listener.set_nonblocking(true).map_err(|_|DirectTcpError::ListenerBind)?;
        Ok(listener)
    }
    #[cfg(test)]
    mod tests{
        use super::*;
        #[test]
        fn plan029_tcp_selected_kernel_backend_never_unbound_or_loopback_escape(){
            assert!(matches!(PhysicalTcpSocket::start(
                Ipv4Addr::new(10,1,0,2),0,
                SocketAddrV4::new(Ipv4Addr::new(8,8,8,8),443)),
                Err(DirectTcpError::InvalidUnderlay)));
            assert!(matches!(PhysicalTcpSocket::start(
                Ipv4Addr::LOCALHOST,8,
                SocketAddrV4::new(Ipv4Addr::new(8,8,8,8),443)),
                Err(DirectTcpError::InvalidUnderlay)));
            assert!(matches!(PhysicalTcpSocket::start(
                Ipv4Addr::new(10,1,0,2),8,
                SocketAddrV4::new(Ipv4Addr::LOCALHOST,443)),
                Err(DirectTcpError::InvalidUnderlay)));
        }
    }
}
#[cfg(target_os="windows")]
pub use win::{PhysicalTcpSocket,open_kernel_tcp_listener};

const DEFAULT_PER_DIRECTION_CAP:usize=16*1024;
const QUANTUM_BYTES:usize=4096;
/// Small per-flow buffers allocated lazily ONLY for an accepted Direct
/// socket. The scheduler accounts their bytes against one shared cap.
/// No per-flow thread, whole-table scan or global packet mutex here.
pub struct TcpDirectRelay{
    inner:TcpStream,
    outer:TcpStream,
    to_outer:VecDeque<u8>,
    to_inner:VecDeque<u8>,
    inner_eof:bool,outer_eof:bool,
    inner_write_closed:bool,outer_write_closed:bool,
    max_pending_per_direction:usize,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct RelayTick{
    pub bytes_read:usize,
    pub bytes_written:usize,
    pub buffered:usize,
    pub finished:bool,
}
impl TcpDirectRelay{
    pub fn new(inner:TcpStream,outer:TcpStream)->Result<Self,DirectTcpError>{
        Self::with_budget(inner,outer,DEFAULT_PER_DIRECTION_CAP)
    }
    pub fn with_budget(inner:TcpStream,outer:TcpStream,cap:usize)
        ->Result<Self,DirectTcpError>{
        if cap<QUANTUM_BYTES||cap>64*1024{
            return Err(DirectTcpError::BufferBudget)
        }
        inner.set_nonblocking(true).map_err(|_|DirectTcpError::RelayIo)?;
        outer.set_nonblocking(true).map_err(|_|DirectTcpError::RelayIo)?;
        Ok(Self{inner,outer,to_outer:VecDeque::new(),to_inner:VecDeque::new(),
            inner_eof:false,outer_eof:false,
            inner_write_closed:false,outer_write_closed:false,
            max_pending_per_direction:cap})
    }
    /// One bounded service turn, called only for a ready flow by the
    /// original Rust scheduler. A congested physical stream stops reading
    /// THAT flow. It never sleeps/stops other Tunnel or Direct UDP flows.
    pub fn service_once(&mut self)->Result<RelayTick,DirectTcpError>{
        let mut scratch=[0u8;QUANTUM_BYTES];
        let mut read=0usize;let mut wrote=0usize;
        if !self.inner_eof && self.to_outer.len()<self.max_pending_per_direction{
            let allowed=(self.max_pending_per_direction-self.to_outer.len()).min(QUANTUM_BYTES);
            match self.inner.read(&mut scratch[..allowed]){
                Ok(0)=>self.inner_eof=true,
                Ok(n)=>{self.to_outer.extend(&scratch[..n]);read+=n}
                Err(e) if e.kind()==ErrorKind::WouldBlock=>{}
                Err(_)=>return Err(DirectTcpError::RelayIo),
            }
        }
        if !self.outer_eof && self.to_inner.len()<self.max_pending_per_direction{
            let allowed=(self.max_pending_per_direction-self.to_inner.len()).min(QUANTUM_BYTES);
            match self.outer.read(&mut scratch[..allowed]){
                Ok(0)=>self.outer_eof=true,
                Ok(n)=>{self.to_inner.extend(&scratch[..n]);read+=n}
                Err(e) if e.kind()==ErrorKind::WouldBlock=>{}
                Err(_)=>return Err(DirectTcpError::RelayIo),
            }
        }
        if !self.to_outer.is_empty(){
            let (first,_)=self.to_outer.as_slices();
            match self.outer.write(first){
                Ok(n)=>{self.to_outer.drain(..n);wrote+=n}
                Err(e) if e.kind()==ErrorKind::WouldBlock=>{}
                Err(_)=>return Err(DirectTcpError::RelayIo),
            }
        }
        if !self.to_inner.is_empty(){
            let (first,_)=self.to_inner.as_slices();
            match self.inner.write(first){
                Ok(n)=>{self.to_inner.drain(..n);wrote+=n}
                Err(e) if e.kind()==ErrorKind::WouldBlock=>{}
                Err(_)=>return Err(DirectTcpError::RelayIo),
            }
        }
        if self.inner_eof && self.to_outer.is_empty() && !self.outer_write_closed{
            self.outer.shutdown(Shutdown::Write).map_err(|_|DirectTcpError::RelayIo)?;
            self.outer_write_closed=true;
        }
        if self.outer_eof && self.to_inner.is_empty() && !self.inner_write_closed{
            self.inner.shutdown(Shutdown::Write).map_err(|_|DirectTcpError::RelayIo)?;
            self.inner_write_closed=true;
        }
        Ok(RelayTick{bytes_read:read,bytes_written:wrote,
            buffered:self.to_outer.len()+self.to_inner.len(),
            finished:self.inner_eof&&self.outer_eof&&
                self.to_outer.is_empty()&&self.to_inner.is_empty()})
    }
    pub fn pending_bytes(&self)->usize{self.to_outer.len()+self.to_inner.len()}
}
