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
    RelayIo{stage:&'static str,code:i32},
    BufferBudget,
    SocketEvent(i32),
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
    const POLLERR:i16=0x0001;
    const POLLHUP:i16=0x0002;
    const POLLNVAL:i16=0x0004;
    const POLLWRNORM:i16=0x0010;
    // Exactly 16 manual-reset WinSock events: all sockets join one
    // original TX WaitForMultipleObjects, never a per-flow thread/event.
    pub const TCP_EVENT_SHARDS:usize=16;
    const FD_READ:i32=1;
    const FD_WRITE:i32=2;
    const FD_ACCEPT:i32=8;
    const FD_CONNECT:i32=16;
    const FD_CLOSE:i32=32;
    pub const EVENT_ACCEPT:i32=FD_ACCEPT|FD_CLOSE;
    pub const EVENT_CONNECT:i32=FD_READ|FD_WRITE|FD_CONNECT|FD_CLOSE;
    // Cold metrics observe the existing WinSock mask, never re-register it.
    pub const EVENT_READ:i32=FD_READ;
    pub const EVENT_WRITE:i32=FD_WRITE;
    pub const EVENT_CONNECTED:i32=FD_CONNECT;
    pub const EVENT_CLOSED:i32=FD_CLOSE;
    #[repr(C)]
    struct WsaNetworkEvents{mask:i32,errors:[i32;10]}

    #[repr(C)]
    struct WsaPollFd{socket:usize,events:i16,revents:i16}

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
    #[link(name="ws2_32")]
    extern "system" {
        fn socket(af:i32,kind:i32,proto:i32)->usize;
        fn closesocket(s:usize)->i32;
        fn bind(s:usize,name:*const c_void,len:i32)->i32;
        fn connect(s:usize,name:*const c_void,len:i32)->i32;
        fn ioctlsocket(s:usize,cmd:i32,arg:*mut u32)->i32;
        fn setsockopt(s:usize,level:i32,opt:i32,p:*const i8,len:i32)->i32;
        fn getsockopt(s:usize,level:i32,opt:i32,p:*mut i8,len:*mut i32)->i32;
        fn WSAGetLastError()->i32;
        fn WSAPoll(fds:*mut WsaPollFd,count:u32,timeout_ms:i32)->i32;
        fn WSACreateEvent()->usize;
        fn WSACloseEvent(handle:usize)->i32;
        fn WSAResetEvent(handle:usize)->i32;
        fn WSAEventSelect(s:usize,event:usize,events:i32)->i32;
        fn WSAEnumNetworkEvents(s:usize,event:usize,out:*mut WsaNetworkEvents)->i32;
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
    /// Shared wake shards, not one event or thread per flow. The original
    /// Rust TX owns all 16 event handles and polls socket events only for
    /// the signaled shard. Drop comes after owned sockets close.
    pub struct SocketReadiness{events:Vec<usize>}
    impl SocketReadiness{
        pub fn new()->Result<Self,DirectTcpError>{
            let mut this=Self{events:Vec::with_capacity(TCP_EVENT_SHARDS)};
            for _ in 0..TCP_EVENT_SHARDS{
                let event=unsafe{WSACreateEvent()};
                if event==0||event==usize::MAX{
                    return Err(DirectTcpError::SocketEvent(last()))
                }
                this.events.push(event);
            }
            Ok(this)
        }
        pub fn handles(&self)->&[usize]{&self.events}
        pub fn shard(port:u16)->usize{usize::from(port)%TCP_EVENT_SHARDS}
        pub fn watch(&self,socket:usize,shard:usize,events:i32)
            ->Result<(),DirectTcpError>{
            if shard>=TCP_EVENT_SHARDS||socket==usize::MAX{
                return Err(DirectTcpError::SocketEvent(-1))
            }
            if unsafe{WSAEventSelect(socket,self.events[shard],events)}!=0{
                return Err(DirectTcpError::SocketEvent(last()))
            }
            Ok(())
        }
        /// The first socket of a signaled shard atomically resets the
        /// shard event while acknowledging its own recorded WinSock flags.
        /// Remaining sockets use a NULL event to avoid resetting a new
        /// wake in the middle of the scan. No lost FD_READ/FD_ACCEPT edges.
        pub fn take(&self,socket:usize,shard:usize,reset:bool)
            ->Result<i32,DirectTcpError>{
            let mut item=WsaNetworkEvents{mask:0,errors:[0;10]};
            let event=if reset{self.events[shard]}else{0};
            if unsafe{WSAEnumNetworkEvents(socket,event,&mut item)}!=0{
                return Err(DirectTcpError::SocketEvent(last()))
            }
            // A reported socket error is still actionable by the owner
            // via its existing nonblocking connect/read/write error path.
            Ok(item.mask)
        }
        pub fn clear_unused(&self,shard:usize)->Result<(),DirectTcpError>{
            if unsafe{WSAResetEvent(self.events[shard])}==0{
                return Err(DirectTcpError::SocketEvent(last()))
            }
            Ok(())
        }
        pub fn is_accept(mask:i32)->bool{mask&FD_ACCEPT!=0}
    }
    impl Drop for SocketReadiness{
        fn drop(&mut self){for &event in &self.events{
            unsafe{WSACloseEvent(event);}
        }}
    }
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
        pub fn raw_socket(&self)->usize{self.stream.as_raw_socket() as usize}
        pub fn peer(&self)->SocketAddrV4{self.remote}
        /// A Wintun-bound internal Tunnel DNS TCP socket is registered
        /// by original Rust TX before its next Wintun packet quantum.
        /// This is the actual WinSock assigned source port, not a guess.
        pub fn local_port(&self)->Result<u16,DirectTcpError>{
            match self.stream.local_addr(){
                Ok(std::net::SocketAddr::V4(addr)) if addr.port()!=0=>
                    Ok(addr.port()),
                _=>Err(DirectTcpError::PeerFailed),
            }
        }
        pub fn underlay(&self)->(Ipv4Addr,u32){(self.source,self.ifindex)}
        pub fn progress(&self)->ConnectProgress{self.progress}
        pub fn poll_connected(&mut self)->Result<ConnectProgress,DirectTcpError>{
            if self.progress==ConnectProgress::Connected{
                return Ok(self.progress)
            }
            // WinSock nonblocking connect(): getpeername/peer_addr alone is
            // not a write-ready guarantee. Wait for FD_WRITE then inspect
            // SO_ERROR via take_error, as specified by Microsoft WSAPoll.
            // The worker schedules this bounded ZERO-timeout check only
            // while a new Direct socket is pending; never on ordinary DATA.
            let mut fd=WsaPollFd{
                socket:self.stream.as_raw_socket() as usize,
                events:POLLWRNORM,revents:0,
            };
            let rc=unsafe{WSAPoll(&mut fd,1,0)};
            if rc<0{return Err(DirectTcpError::SocketConnect(last()))}
            if rc==0{return Ok(ConnectProgress::Pending)}
            let os_error=self.stream.take_error().map_err(|e|DirectTcpError::RelayIo{
                stage:"connect_take_error",code:e.raw_os_error().unwrap_or(-1)})?;
            if os_error.is_some()||
               fd.revents&(POLLERR|POLLHUP|POLLNVAL)!=0{
                return Err(DirectTcpError::PeerFailed)
            }
            if fd.revents&POLLWRNORM==0{return Ok(ConnectProgress::Pending)}
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
pub use win::{PhysicalTcpSocket,open_kernel_tcp_listener,SocketReadiness,TCP_EVENT_SHARDS,
    EVENT_ACCEPT,EVENT_CONNECT,EVENT_READ,EVENT_WRITE,
    EVENT_CONNECTED,EVENT_CLOSED};

// A 4-KiB relay turn on the existing 10-ms Direct I/O wake required >=512
// turns to shuttle a 1-MiB request and 1-MiB reply (H1820: 6.485 s).
// Transfer at most 64 KiB in each direction per scheduled *flow* turn;
// this is a work quantum, not a preallocated per-flow TCP window.
// Each direction still has its own bounded queue, and the owner rotates
// at most eight flows per turn without waiting on slow physical sockets.
// H1948 signed-test-only first real physical socket events, same-Windows QPC.
#[cfg(target_os="windows")]
#[link(name="kernel32")]
unsafe extern "system" { fn QueryPerformanceCounter(out:*mut i64)->i32; }
#[inline]
fn signed_reply_path_qpc_tick()->i64{
    #[cfg(target_os="windows")]
    {
        let mut tick=0i64;
        if unsafe{QueryPerformanceCounter(&mut tick)}!=0{return tick}
    }
    0
}
#[derive(Clone,Copy,Debug,Default,Eq,PartialEq)]
pub struct RelayReplyPathQpc{
    // H1953 source-locked test only: timestamp first inner kernel recv.
    pub first_inner_read:i64,
    pub first_outer_write:i64,
    pub first_outer_read:i64,
}
const DEFAULT_PER_DIRECTION_CAP:usize=64*1024;
const QUANTUM_BYTES:usize=64*1024;
// Do not read new bytes from one Direct socket when its own buffer or
// the WHOLE Rust TCP relay pool is under pressure. No global wait.
fn bounded_relay_read(queued:usize,per_direction_cap:usize,global_free:usize)->usize{
    per_direction_cap.saturating_sub(queued)
        .min(QUANTUM_BYTES).min(global_free)
}
/// Small per-flow buffers allocated lazily ONLY for an accepted Direct
/// socket. The scheduler accounts their bytes against one shared cap.
/// No per-flow thread, whole-table scan or global packet mutex here.
fn relay_error(stage:&'static str,e:std::io::Error)->DirectTcpError{
    DirectTcpError::RelayIo{stage,code:e.raw_os_error().unwrap_or(-1)}
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
struct ForwardResult{
    written:usize,
    copied_to_queue:usize,
    attempted_direct_write:bool,
    blocked:bool,
    short_write:bool,
}
/// Fresh bytes bypass per-flow VecDeque only when there is NO earlier
/// buffered byte. A partial/blocked write queues its exact unsent suffix;
/// this never admits a newer byte in front of older TCP stream data.
fn forward_or_queue<W:Write>(
    destination:&mut W,oldest:&mut VecDeque<u8>,fresh:&[u8],
    stage:&'static str,
)->Result<ForwardResult,DirectTcpError>{
    if fresh.is_empty(){return Ok(ForwardResult{
        written:0,copied_to_queue:0,attempted_direct_write:false,
        blocked:false,short_write:false
    })}
    if !oldest.is_empty(){
        oldest.extend(fresh.iter().copied());
        return Ok(ForwardResult{written:0,
            copied_to_queue:fresh.len(),attempted_direct_write:false,
            blocked:false,short_write:false})
    }
    let mut blocked=false;
    let written=match destination.write(fresh){
        Ok(n)=>n.min(fresh.len()),
        Err(e) if e.kind()==ErrorKind::WouldBlock=>{blocked=true;0},
        Err(e) if e.kind()==ErrorKind::Interrupted=>0,
        Err(e)=>return Err(relay_error(stage,e)),
    };
    let rest=fresh.len()-written;
    if rest>0{oldest.extend(fresh[written..].iter().copied());}
    Ok(ForwardResult{written,copied_to_queue:rest,attempted_direct_write:true,
        blocked,short_write:written>0&&written<fresh.len()})
}
pub struct TcpDirectRelay{
    inner:TcpStream,
    outer:TcpStream,
    to_outer:VecDeque<u8>,
    to_inner:VecDeque<u8>,
    inner_eof:bool,outer_eof:bool,
    inner_write_closed:bool,outer_write_closed:bool,
    max_pending_per_direction:usize,
    // Product always ON. Only an explicit source-locked Win2025 probe
    // A-B-B-A fixture may select legacy copy for a known test flow.
    fast_forward:bool,
    // Each kernel TCP leg has its OWN FD_READ subscription. One side
    // returning WouldBlock disarms only that side until the original TX
    // owner harvests a genuine FD_READ/FD_CLOSE for that socket.
    // Start permissive: connect-time events may predate relay admission.
    read_armed:[bool;2],
    // A coalesced FD_CLOSE may be consumed before recv reaches EOF.
    // Preserve the one-shot real kernel hint separately for both legs.
    close_hint:[bool;2],
    // Standalone platform tests use legacy caller-driven polling; the
    // genuine Windows TX actor enables this only after owning BOTH
    // WSAEventSelect registrations. This prevents a component caller
    // without a Windows event pump from deadlocking after WouldBlock.
    read_event_driven:bool,
    // None for ordinary product. No clock syscall or log unless signed P2.
    reply_path_qpc:Option<RelayReplyPathQpc>,
    // Signed original Win/WSL2 steady-state experiment only. No QPC
    // syscall, allocation or per-packet log in an ordinary product.
    steady_qpc_enabled:bool,
}
// Index 0: listener-facing inner socket, index 1: physical outer socket.
// Bounded integer counts only; no syscall, clock or log added by metrics.
#[derive(Clone,Copy,Debug,Default,Eq,PartialEq)]
pub struct RelayIoCounts{
    pub read_calls:[u16;2],
    pub read_wouldblock:[u16;2],
    // A one-time non-consuming EOF check after actual FD_CLOSE and a
    // positive recv: no per-packet syscall on an unclosed TCP stream.
    pub fin_peek_calls:[u16;2],
    pub fin_peek_eof:[u16;2],
    pub write_calls:[u16;2],
    pub write_wouldblock:[u16;2],
    pub short_writes:[u16;2],
    pub gated_reads:[u16;2],
    // The recv was deliberately SKIPPED because THIS leg has not
    // received new FD_READ/FD_CLOSE since its last WouldBlock. Unlike
    // gated_reads, this is not pressure or a pending queue limit.
    pub event_suppressed_reads:[u16;2],
}
/// Each timestamp is observed AFTER its positive WinSock syscall.
/// A successful socket write is NOT proof of Linux receipt or an ACK.
#[derive(Clone,Copy,Debug,Default,Eq,PartialEq)]
pub struct RelaySteadyQpc{
    pub inner_read_done:i64,
    pub outer_write_done:i64,
    pub outer_read_done:i64,
    pub inner_write_done:i64,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct RelayTick{
    pub bytes_read:usize,
    pub bytes_written:usize,
    // Optional cold diagnostic only; distinguish which kernel TCP leg
    // stopped making progress without attributing timeout to WSAPoll.
    pub inner_read:usize,
    pub outer_read:usize,
    pub inner_write:usize,
    pub outer_write:usize,
    pub forwarded_without_queue:usize,
    pub copied_to_queue:usize,
    /// A leg received FD_CLOSE, consumed positive bytes, but not recv(0).
    /// Only this case needs a bounded extra ready turn after short reads.
    pub close_probe_due:bool,
    pub io:RelayIoCounts,
    pub steady_qpc:Option<RelaySteadyQpc>,
    pub buffered:usize,
    pub finished:bool,
}
impl TcpDirectRelay{
    pub fn new(inner:TcpStream,outer:TcpStream)->Result<Self,DirectTcpError>{
        Self::with_budget(inner,outer,DEFAULT_PER_DIRECTION_CAP)
    }
    pub fn with_budget(inner:TcpStream,outer:TcpStream,cap:usize)
        ->Result<Self,DirectTcpError>{
        Self::with_budget_and_fast_forward(inner,outer,cap,true)
    }
    /// Probe control applies only to this relay object, never a global
    /// product/runtime policy. Ordinary new()/with_budget() ALWAYS enable
    /// the proven strict-FIFO fast-forward implementation.
    pub fn with_fast_forward(inner:TcpStream,outer:TcpStream,enabled:bool)
        ->Result<Self,DirectTcpError>{
        Self::with_budget_and_fast_forward(
            inner,outer,DEFAULT_PER_DIRECTION_CAP,enabled)
    }
    fn with_budget_and_fast_forward(
        inner:TcpStream,outer:TcpStream,cap:usize,enabled:bool)
        ->Result<Self,DirectTcpError>{
        if cap<QUANTUM_BYTES||cap>64*1024{
            return Err(DirectTcpError::BufferBudget)
        }
        inner.set_nonblocking(true).map_err(|e|relay_error("inner_nonblocking",e))?;
        outer.set_nonblocking(true).map_err(|e|relay_error("outer_nonblocking",e))?;
        // Once per accepted Direct flow, both owned kernel TCP legs use
        // TCP_NODELAY. With two independent ACK clocks, forwarding small
        // writes while Nagle waits for a delayed ACK can create avoidable
        // multi-turn stalls (H1823: 64KiB relay turns still took 6.141s
        // vs 281ms physical for 1MiB). This hypothesis is NOT confirmed
        // until one new signed same-VM P2 run; never change Tunnel sockets.
        inner.set_nodelay(true).map_err(|e|relay_error("inner_nodelay",e))?;
        outer.set_nodelay(true).map_err(|e|relay_error("outer_nodelay",e))?;
        Ok(Self{inner,outer,to_outer:VecDeque::new(),to_inner:VecDeque::new(),
            inner_eof:false,outer_eof:false,
            inner_write_closed:false,outer_write_closed:false,
            max_pending_per_direction:cap,fast_forward:enabled,
            read_armed:[true,true],close_hint:[false,false],
            read_event_driven:false,reply_path_qpc:None,
            steady_qpc_enabled:false})
    }
    // The original source-locked Windows TX enables this only for H1948.
    pub fn enable_signed_reply_path_qpc(&mut self){
        self.reply_path_qpc=Some(RelayReplyPathQpc::default());
    }
    pub fn signed_reply_path_qpc(&self)->Option<RelayReplyPathQpc>{
        self.reply_path_qpc
    }
    /// Arm only on a single source-locked original kernel TCP flow.
    pub fn enable_signed_steady_qpc(&mut self){
        self.steady_qpc_enabled=true;
    }
    #[inline]
    fn note_first_inner_read_qpc(&mut self){
        if let Some(row)=self.reply_path_qpc.as_mut(){
            if row.first_inner_read==0{row.first_inner_read=signed_reply_path_qpc_tick();}
        }
    }
    #[inline]
    fn note_first_outer_write_qpc(&mut self){
        if let Some(row)=self.reply_path_qpc.as_mut(){
            if row.first_outer_write==0{row.first_outer_write=signed_reply_path_qpc_tick();}
        }
    }
    #[inline]
    fn note_first_outer_read_qpc(&mut self){
        if let Some(row)=self.reply_path_qpc.as_mut(){
            if row.first_outer_read==0{row.first_outer_read=signed_reply_path_qpc_tick();}
        }
    }
    /// Only the real Windows TX with registered WinSock events may turn
    /// this on; other callers keep their original polling semantics.
    pub fn enable_event_driven_reads(&mut self){
        self.read_event_driven=true;
    }
    /// Called only by the original owner after WSAEnumNetworkEvents.
    /// The two independent bits are NOT collapsed into one flow-wide
    /// readiness flag; an FD_WRITE from one leg cannot enable an
    /// unrelated FD_READ on the other. FD_CLOSE must allow recv(0).
    pub fn note_read_event(&mut self,inner:bool,outer:bool){
        if inner{self.read_armed[0]=true}
        if outer{self.read_armed[1]=true}
    }
    /// Only the original TX owner calls this after an actual per-socket
    /// WSAEnumNetworkEvents FD_CLOSE. DATA may precede EOF in the next
    /// recv despite this single kernel close notification being consumed.
    pub fn note_close_event(&mut self,inner:bool,outer:bool){
        if inner{self.close_hint[0]=true;self.read_armed[0]=true}
        if outer{self.close_hint[1]=true;self.read_armed[1]=true}
    }
    /// One bounded service turn, called only for a ready flow by the
    /// original Rust scheduler. A congested physical stream stops reading
    /// THAT flow. It never sleeps/stops other Tunnel or Direct UDP flows.
    pub fn service_once(&mut self)->Result<RelayTick,DirectTcpError>{
        self.service_once_with_read_budget(usize::MAX)
    }
    // The owner provides its GLOBAL free *allocated capacity* budget.
    // Existing pending writes drain even when all new reads are paused.
    // If there is less than a full two-direction growth reserve, reads
    // may use only already-allocated spare queue capacity; this prevents
    // geometric VecDeque growth silently exceeding the global pool.
    pub fn service_once_with_read_budget(&mut self,read_budget:usize)
        ->Result<RelayTick,DirectTcpError>{
        // Production passes one reusable per-owner scratch to this same
        // bounded relay. Keep the old API for component-only callers.
        let mut scratch=[0u8;QUANTUM_BYTES];
        self.service_once_with_scratch(read_budget,&mut scratch)
    }
    pub fn service_once_with_scratch(&mut self,read_budget:usize,
        scratch:&mut [u8])->Result<RelayTick,DirectTcpError>{
        if scratch.len()<QUANTUM_BYTES{return Err(DirectTcpError::BufferBudget)}
        let mut remaining_capacity=read_budget;
        let mut read=0usize;let mut wrote=0usize;
        let mut inner_read=0usize;let mut outer_read=0usize;
        let mut inner_write=0usize;let mut outer_write=0usize;
        let mut forwarded_without_queue=0usize;let mut copied_to_queue=0usize;
        let mut attempted_outer=false;let mut attempted_inner=false;
        let mut io=RelayIoCounts::default();
        let mut steady=self.steady_qpc_enabled.then(RelaySteadyQpc::default);
        let inner_read_allowed=!self.inner_eof &&
            self.to_outer.len()<self.max_pending_per_direction &&
            (remaining_capacity>=2*DEFAULT_PER_DIRECTION_CAP ||
             self.to_outer.capacity()>self.to_outer.len());
        if !self.inner_eof && !inner_read_allowed{io.gated_reads[0]+=1;}
        if !self.inner_eof && self.read_event_driven && !self.read_armed[0]{
            io.event_suppressed_reads[0]+=1;
        }
        if inner_read_allowed && (!self.read_event_driven || self.read_armed[0]){
            let spare=self.to_outer.capacity().saturating_sub(self.to_outer.len());
            let growth=remaining_capacity>=2*DEFAULT_PER_DIRECTION_CAP;
            let allowed=bounded_relay_read(self.to_outer.len(),
                self.max_pending_per_direction,if growth{usize::MAX}else{spare});
            let before=self.to_outer.capacity();
            io.read_calls[0]+=1;
            match self.inner.read(&mut scratch[..allowed]){
                Ok(0)=>{self.inner_eof=true;self.read_armed[0]=false},
                Ok(n)=>{
                    if n>0{
                        self.note_first_inner_read_qpc();
                        if let Some(t)=steady.as_mut(){t.inner_read_done=signed_reply_path_qpc_tick();}
                    }
                    // First try direct scratch->physical kernel send, only then
                    // allocate a bounded suffix queue if needed.
                    if self.fast_forward{
                        let f=forward_or_queue(&mut self.outer,
                            &mut self.to_outer,&scratch[..n],"outer_write")?;
                        attempted_outer=f.attempted_direct_write;
                        if f.written>0{
                            self.note_first_outer_write_qpc();
                            if let Some(t)=steady.as_mut(){t.outer_write_done=signed_reply_path_qpc_tick();}
                        }
                        if f.attempted_direct_write{
                            io.write_calls[1]+=1;
                            io.write_wouldblock[1]+=u16::from(f.blocked);
                            io.short_writes[1]+=u16::from(f.short_write);
                        }
                        forwarded_without_queue+=f.written;
                        copied_to_queue+=f.copied_to_queue;
                        wrote+=f.written;outer_write+=f.written;
                    }else{
                        // Original H1877 bounded read->queue->socket
                        // semantics. A/B is a change to data movement
                        // only: sockets, traffic, scheduling and NAT
                        // remain byte-identical.
                        self.to_outer.extend(&scratch[..n]);
                        copied_to_queue+=n;
                    }
                    read+=n;inner_read+=n;
                    remaining_capacity=remaining_capacity.saturating_sub(
                        self.to_outer.capacity().saturating_sub(before));
                }
                Err(e) if e.kind()==ErrorKind::WouldBlock=>{
                    io.read_wouldblock[0]+=1;
                    self.read_armed[0]=false;
                }
                Err(e) if e.kind()==ErrorKind::Interrupted=>{}
                Err(e)=>return Err(relay_error("inner_read",e)),
            }
        }
        let outer_read_allowed=!self.outer_eof &&
            self.to_inner.len()<self.max_pending_per_direction &&
            (remaining_capacity>=2*DEFAULT_PER_DIRECTION_CAP ||
             self.to_inner.capacity()>self.to_inner.len());
        if !self.outer_eof && !outer_read_allowed{io.gated_reads[1]+=1;}
        if !self.outer_eof && self.read_event_driven && !self.read_armed[1]{
            io.event_suppressed_reads[1]+=1;
        }
        if outer_read_allowed && (!self.read_event_driven || self.read_armed[1]){
            let spare=self.to_inner.capacity().saturating_sub(self.to_inner.len());
            let growth=remaining_capacity>=2*DEFAULT_PER_DIRECTION_CAP;
            let allowed=bounded_relay_read(self.to_inner.len(),
                self.max_pending_per_direction,if growth{usize::MAX}else{spare});
            let before=self.to_inner.capacity();
            io.read_calls[1]+=1;
            match self.outer.read(&mut scratch[..allowed]){
                Ok(0)=>{self.outer_eof=true;self.read_armed[1]=false},
                Ok(n)=>{
                    if n>0{
                        self.note_first_outer_read_qpc();
                        if let Some(t)=steady.as_mut(){t.outer_read_done=signed_reply_path_qpc_tick();}
                    }
                    if self.fast_forward{
                        let f=forward_or_queue(&mut self.inner,
                            &mut self.to_inner,&scratch[..n],"inner_write")?;
                        attempted_inner=f.attempted_direct_write;
                        if f.attempted_direct_write{
                            io.write_calls[0]+=1;
                            io.write_wouldblock[0]+=u16::from(f.blocked);
                            io.short_writes[0]+=u16::from(f.short_write);
                        }
                        if f.written>0{
                            if let Some(t)=steady.as_mut(){t.inner_write_done=signed_reply_path_qpc_tick();}
                        }
                        forwarded_without_queue+=f.written;
                        copied_to_queue+=f.copied_to_queue;
                        wrote+=f.written;inner_write+=f.written;
                    }else{
                        self.to_inner.extend(&scratch[..n]);
                        copied_to_queue+=n;
                    }
                    read+=n;outer_read+=n;
                    remaining_capacity=remaining_capacity.saturating_sub(
                        self.to_inner.capacity().saturating_sub(before));
                }
                Err(e) if e.kind()==ErrorKind::WouldBlock=>{
                    io.read_wouldblock[1]+=1;
                    self.read_armed[1]=false;
                }
                Err(e) if e.kind()==ErrorKind::Interrupted=>{}
                Err(e)=>return Err(relay_error("outer_read",e)),
            }
        }
        // The real Windows FD_CLOSE may be coalesced with final short
        // DATA. recv(DATA) needs another TX ticket to discover recv(0),
        // delaying server echo when it waits for our forwarded FIN.
        // MSG_PEEK never consumes data. Exactly one nonblocking probe
        // per leg/turn ONLY after actual FD_CLOSE + positive recv.
        // If data remains or WouldBlock, the H1920 any-progress
        // self-ticket remains unchanged; no periodic polling.
        if self.close_hint[0]&&!self.inner_eof&&inner_read>0{
            io.fin_peek_calls[0]+=1;
            let mut probe=[0u8;1];
            match self.inner.peek(&mut probe){
                Ok(0)=>{self.inner_eof=true;self.read_armed[0]=false;
                         io.fin_peek_eof[0]+=1;},
                Ok(_)=>{},
                Err(e) if matches!(e.kind(),ErrorKind::WouldBlock|
                    ErrorKind::Interrupted)=>{},
                Err(e)=>return Err(relay_error("inner_fin_peek",e)),
            }
        }
        if self.close_hint[1]&&!self.outer_eof&&outer_read>0{
            io.fin_peek_calls[1]+=1;
            let mut probe=[0u8;1];
            match self.outer.peek(&mut probe){
                Ok(0)=>{self.outer_eof=true;self.read_armed[1]=false;
                         io.fin_peek_eof[1]+=1;},
                Ok(_)=>{},
                Err(e) if matches!(e.kind(),ErrorKind::WouldBlock|
                    ErrorKind::Interrupted)=>{},
                Err(e)=>return Err(relay_error("outer_fin_peek",e)),
            }
        }
        // A short or WouldBlock immediate write is not repeated in this
        // same service quantum; FD_WRITE will re-arm that kernel leg.
        if !attempted_outer && !self.to_outer.is_empty(){
            let (first,_)=self.to_outer.as_slices();
            let first_len=first.len();
            io.write_calls[1]+=1;
            match self.outer.write(first){
                Ok(n)=>{
                    io.short_writes[1]+=u16::from(n>0&&n<first_len);
                    self.to_outer.drain(..n);wrote+=n;outer_write+=n;
                    if n>0{
                        self.note_first_outer_write_qpc();
                        if let Some(t)=steady.as_mut(){t.outer_write_done=signed_reply_path_qpc_tick();}
                    }
                }
                Err(e) if e.kind()==ErrorKind::WouldBlock=>{
                    io.write_wouldblock[1]+=1;
                }
                Err(e) if e.kind()==ErrorKind::Interrupted=>{}
                Err(e)=>return Err(relay_error("outer_write",e)),
            }
        }
        if !attempted_inner && !self.to_inner.is_empty(){
            let (first,_)=self.to_inner.as_slices();
            let first_len=first.len();
            io.write_calls[0]+=1;
            match self.inner.write(first){
                Ok(n)=>{
                    io.short_writes[0]+=u16::from(n>0&&n<first_len);
                    self.to_inner.drain(..n);wrote+=n;inner_write+=n;
                    if n>0{
                        if let Some(t)=steady.as_mut(){t.inner_write_done=signed_reply_path_qpc_tick();}
                    }
                }
                Err(e) if e.kind()==ErrorKind::WouldBlock=>{
                    io.write_wouldblock[0]+=1;
                }
                Err(e) if e.kind()==ErrorKind::Interrupted=>{}
                Err(e)=>return Err(relay_error("inner_write",e)),
            }
        }
        if self.inner_eof && self.to_outer.is_empty() && !self.outer_write_closed{
            self.outer.shutdown(Shutdown::Write).map_err(|e|relay_error("outer_close_write",e))?;
            self.outer_write_closed=true;
        }
        if self.outer_eof && self.to_inner.is_empty() && !self.inner_write_closed{
            self.inner.shutdown(Shutdown::Write).map_err(|e|relay_error("inner_close_write",e))?;
            self.inner_write_closed=true;
        }
        Ok(RelayTick{bytes_read:read,bytes_written:wrote,
            inner_read,outer_read,inner_write,outer_write,
            forwarded_without_queue,copied_to_queue,
            close_probe_due:(self.close_hint[0]&&!self.inner_eof&&inner_read>0)||
                (self.close_hint[1]&&!self.outer_eof&&outer_read>0),
            io,steady_qpc:steady,
            buffered:self.to_outer.len()+self.to_inner.len(),
            finished:self.inner_eof&&self.outer_eof&&
                self.to_outer.is_empty()&&self.to_inner.is_empty()})
    }
    #[cfg(target_os="windows")]
    pub fn socket_handles(&self)->(usize,usize){
        use std::os::windows::io::AsRawSocket;
        (self.inner.as_raw_socket() as usize,self.outer.as_raw_socket() as usize)
    }
    /// Cold observation only. Order: local app-side recv(0), physical
    /// recv(0), physical shutdown(SHUT_WR), app-side shutdown(SHUT_WR).
    /// This does NOT infer remote ACK, driver delivery or Linux FIN receipt.
    /// The real original TX can compare transitions after one bounded
    /// service quantum without adding a system call to the hot path.
    pub fn half_close_state(&self)->[bool;4]{
        [self.inner_eof,self.outer_eof,
         self.outer_write_closed,self.inner_write_closed]
    }
    pub fn pending_bytes(&self)->usize{self.to_outer.len()+self.to_inner.len()}
    pub fn resident_bytes(&self)->usize{self.to_outer.capacity()+self.to_inner.capacity()}
    /// Coarse, idle-only release; NEVER shrink each successful TCP write.
    pub fn release_idle_capacity(&mut self){
        if self.to_outer.is_empty(){self.to_outer.shrink_to_fit();}
        if self.to_inner.is_empty(){self.to_inner.shrink_to_fit();}
    }
}

#[cfg(test)]
mod plan029_global_backpressure_tests{
    use super::*;
    #[test]
    fn idle_relay_releases_retained_capacity_not_only_pending_length(){
        let listener=TcpListener::bind((Ipv4Addr::LOCALHOST,0)).unwrap();
        let a=TcpStream::connect(listener.local_addr().unwrap()).unwrap();
        let (b,_)=listener.accept().unwrap();
        let listener2=TcpListener::bind((Ipv4Addr::LOCALHOST,0)).unwrap();
        let c=TcpStream::connect(listener2.local_addr().unwrap()).unwrap();
        let (d,_)=listener2.accept().unwrap();
        let mut relay=TcpDirectRelay::new(a,c).unwrap();
        relay.to_outer.extend(std::iter::repeat(5).take(32*1024));
        relay.to_inner.extend(std::iter::repeat(7).take(32*1024));
        assert_eq!(relay.pending_bytes(),64*1024);
        relay.to_outer.clear();relay.to_inner.clear();
        assert_eq!(relay.pending_bytes(),0);
        assert!(relay.resident_bytes()>=64*1024);
        relay.release_idle_capacity();
        assert_eq!(relay.resident_bytes(),0);
        drop((b,d));
    }
    /// The original TX may have acknowledged FD_READ while this socket
    /// was still in Connecting. A newly created relay must drain bytes
    /// ALREADY resident in the original kernel TCP receive buffer on
    /// its single bounded first handoff ticket, with no later FD_READ.
    #[test]
    fn plan029_h1938_first_relay_probe_reads_existing_kernel_bytes_no_new_event(){
        let inbound=TcpListener::bind((Ipv4Addr::LOCALHOST,0)).unwrap();
        let mut application=TcpStream::connect(inbound.local_addr().unwrap()).unwrap();
        let (inner,_)=inbound.accept().unwrap();
        application.write_all(b"EARLY").unwrap();
        // Prove initial payload was already in the kernel socket before
        // TcpDirectRelay/FD_READ admission. peek does not consume bytes.
        let mut seen=[0u8;5];
        assert_eq!(inner.peek(&mut seen).unwrap(),5);
        assert_eq!(&seen,b"EARLY");
        let outbound=TcpListener::bind((Ipv4Addr::LOCALHOST,0)).unwrap();
        let outside=TcpStream::connect(outbound.local_addr().unwrap()).unwrap();
        let (mut destination,_)=outbound.accept().unwrap();
        let mut relay=TcpDirectRelay::with_fast_forward(inner,outside,true).unwrap();
        relay.enable_event_driven_reads();
        let mut scratch=[0u8;QUANTUM_BYTES];
        let first=relay.service_once_with_scratch(usize::MAX,&mut scratch).unwrap();
        assert_eq!(first.inner_read,5);
        assert_eq!(first.outer_write,5);
        assert_eq!(first.io.read_wouldblock[0],0);
        let mut received=[0u8;5];
        destination.read_exact(&mut received).unwrap();
        assert_eq!(&received,b"EARLY");
    }
    #[test]
    fn two_owned_direct_relay_legs_disable_nagle_at_admission_only(){
        fn accepted()->(TcpStream,TcpStream){
            let listener=TcpListener::bind((Ipv4Addr::LOCALHOST,0)).unwrap();
            let peer=TcpStream::connect(listener.local_addr().unwrap()).unwrap();
            let (accepted,_)=listener.accept().unwrap();
            (accepted,peer)
        }
        let (inner,application)=accepted();
        let (outer,remote)=accepted();
        let relay=TcpDirectRelay::new(inner,outer).unwrap();
        assert!(relay.inner.nodelay().unwrap());
        assert!(relay.outer.nodelay().unwrap());
        // The application/remote endpoints aren't owned by the relay.
        assert!(!application.nodelay().unwrap());
        assert!(!remote.nodelay().unwrap());
    }
    /// No fresh TCP byte is allowed to bypass an older short-send tail.
    #[test]
    fn plan029_direct_tcp_fast_forward_fifo_short_and_wouldblock(){
        struct Sink{max:usize,blocked:bool,out:Vec<u8>,calls:usize}
        impl Write for Sink{
            fn write(&mut self,data:&[u8])->std::io::Result<usize>{
                self.calls+=1;
                if self.blocked{return Err(ErrorKind::WouldBlock.into())}
                let n=data.len().min(self.max);
                self.out.extend_from_slice(&data[..n]);
                Ok(n)
            }
            fn flush(&mut self)->std::io::Result<()>{Ok(())}
        }
        let mut s=Sink{max:3,blocked:false,out:Vec::new(),calls:0};
        let mut q=VecDeque::new();
        let a=forward_or_queue(&mut s,&mut q,b"ABCDEFG","test").unwrap();
        assert_eq!(a,ForwardResult{written:3,copied_to_queue:4,
            attempted_direct_write:true,blocked:false,short_write:true});
        assert_eq!(s.out,b"ABC");
        assert_eq!(q.iter().copied().collect::<Vec<_>>(),b"DEFG");
        let b=forward_or_queue(&mut s,&mut q,b"HI","test").unwrap();
        assert_eq!(b,ForwardResult{written:0,copied_to_queue:2,
            attempted_direct_write:false,blocked:false,short_write:false});
        assert_eq!(s.calls,1);
        assert_eq!(q.iter().copied().collect::<Vec<_>>(),b"DEFGHI");
        let mut blocked=Sink{max:8,blocked:true,out:Vec::new(),calls:0};
        let mut other=VecDeque::new();
        let b=forward_or_queue(&mut blocked,&mut other,b"XYZ","test").unwrap();
        assert_eq!(b,ForwardResult{written:0,copied_to_queue:3,
            attempted_direct_write:true,blocked:true,short_write:false});
        assert_eq!(other.iter().copied().collect::<Vec<_>>(),b"XYZ");
    }
    /// Two actual kernel TCP legs, 4KiB in each direction and both FINs:
    /// direct writes should not allocate a per-flow pending queue at all.
    #[test]
    fn plan029_direct_tcp_both_kernel_legs_no_queue_and_fin(){
        use std::time::Duration;
        fn pair()->(TcpStream,TcpStream){
            let l=TcpListener::bind((Ipv4Addr::LOCALHOST,0)).unwrap();
            let client=TcpStream::connect(l.local_addr().unwrap()).unwrap();
            let (server,_)=l.accept().unwrap();
            (server,client)
        }
        let (inner,mut app)=pair();
        let (outer,mut guest)=pair();
        app.set_read_timeout(Some(Duration::from_secs(2))).unwrap();
        guest.set_read_timeout(Some(Duration::from_secs(2))).unwrap();
        let mut relay=TcpDirectRelay::new(inner,outer).unwrap();
        let mut scratch=vec![0u8;QUANTUM_BYTES];
        let input=vec![0x41;4096];
        app.write_all(&input).unwrap();
        let mut direct=0;
        for _ in 0..200{
            let tick=relay.service_once_with_scratch(usize::MAX,&mut scratch).unwrap();
            direct+=tick.forwarded_without_queue;
            if direct>=input.len(){break}
            std::thread::sleep(Duration::from_millis(1));
        }
        assert_eq!(direct,input.len());
        assert_eq!(relay.resident_bytes(),0);
        let mut recv=vec![0;input.len()];
        guest.read_exact(&mut recv).unwrap();
        assert_eq!(recv,input);
        let echo=vec![0x42;4096];
        guest.write_all(&echo).unwrap();
        let mut reverse=0;
        for _ in 0..200{
            let tick=relay.service_once_with_scratch(usize::MAX,&mut scratch).unwrap();
            reverse+=tick.forwarded_without_queue;
            if reverse>=echo.len(){break}
            std::thread::sleep(Duration::from_millis(1));
        }
        assert_eq!(reverse,echo.len());
        assert_eq!(relay.resident_bytes(),0);
        app.read_exact(&mut recv).unwrap();
        assert_eq!(recv,echo);
        app.shutdown(Shutdown::Write).unwrap();
        guest.shutdown(Shutdown::Write).unwrap();
        let mut finished=false;
        for _ in 0..300{
            let tick=relay.service_once_with_scratch(usize::MAX,&mut scratch).unwrap();
            if tick.finished{finished=true;break}
            std::thread::sleep(Duration::from_millis(1));
        }
        assert!(finished,"no lost half-close or pending tail");
        assert_eq!(relay.pending_bytes(),0);
        assert_eq!(relay.half_close_state(),[true,true,true,true],
            "both original kernel TCP recv EOFs and both local SHUT_WR must finish");
    }
    /// A/B control must reproduce the previously shipped queued-copy
    /// path on two genuine kernel sockets, without changing payload or FIN.
    /// Genuine two-legged kernel TCP: after an actual WouldBlock, a
    /// different leg's progress must not cause a syscall on the idle leg.
    /// Explicit simulated FD_READ/FD_CLOSE from the owner re-arms only
    /// the addressed leg. Full bidirectional payload and FIN still work.
    /// H1915 real signed 32KiB regression: one FD_READ|FD_CLOSE is
    /// consumed before the first data-bearing recv, so another recv(0)
    /// is needed even if this was only a SHORT fully forwarded packet.
    #[test]
    fn plan029_h1916_coalesced_close_short_read_fin_and_reverse_echo(){
        use std::time::Duration;
        fn tcp_pair()->(TcpStream,TcpStream){
            let l=TcpListener::bind((Ipv4Addr::LOCALHOST,0)).unwrap();
            let a=TcpStream::connect(l.local_addr().unwrap()).unwrap();
            let (b,_)=l.accept().unwrap();
            (b,a)
        }
        let (inner,mut app)=tcp_pair();
        let (outer,mut guest)=tcp_pair();
        app.set_read_timeout(Some(Duration::from_secs(3))).unwrap();
        guest.set_read_timeout(Some(Duration::from_secs(3))).unwrap();
        let mut relay=TcpDirectRelay::new(inner,outer).unwrap();
        relay.enable_event_driven_reads();
        let payload=vec![0x55;32768];
        let mut scratch=[0u8;QUANTUM_BYTES];
        app.write_all(&payload).unwrap();
        app.shutdown(Shutdown::Write).unwrap();
        std::thread::sleep(Duration::from_millis(15));
        relay.note_read_event(true,false);
        relay.note_close_event(true,false);
        let mut uploaded=0;let mut saw_probe=false;let mut eof=false;
        for _ in 0..100{
            let t=relay.service_once_with_scratch(usize::MAX,&mut scratch).unwrap();
            uploaded+=t.inner_read;
            saw_probe|=t.close_probe_due||(t.inner_read>0&&relay.half_close_state()[0]);
            eof=relay.half_close_state()[0];
            if eof{break}
            // No new event; must be a close-correlated continuation,
            // an unsent tail or an actually full 64KiB read quantum.
            if t.bytes_read>0 || t.bytes_written>0 {
                assert!(t.close_probe_due||t.buffered>0||
                    t.inner_read==QUANTUM_BYTES||relay.half_close_state()[0]);
            }
            std::thread::sleep(Duration::from_millis(1));
        }
        assert_eq!(uploaded,payload.len());
        assert!(saw_probe&&eof);
        let mut got=vec![0;payload.len()];
        guest.read_exact(&mut got).unwrap();
        assert_eq!(got,payload);
        let mut b=[0u8;1];
        assert_eq!(guest.read(&mut b).unwrap(),0,"physical kernel FIN");
        guest.write_all(&payload).unwrap();
        guest.shutdown(Shutdown::Write).unwrap();
        std::thread::sleep(Duration::from_millis(15));
        relay.note_read_event(false,true);
        relay.note_close_event(false,true);
        let mut downloaded=0;let mut done=false;
        for _ in 0..100{
            let t=relay.service_once_with_scratch(usize::MAX,&mut scratch).unwrap();
            downloaded+=t.outer_read;
            if t.finished{done=true;break}
            if t.bytes_read>0 || t.bytes_written>0 {
                assert!(t.close_probe_due||t.buffered>0||
                    t.outer_read==QUANTUM_BYTES||relay.half_close_state()[1]);
            }
            std::thread::sleep(Duration::from_millis(1));
        }
        assert_eq!(downloaded,payload.len());
        assert!(done,"both real FINs must propagate");
        app.read_exact(&mut got).unwrap();
        assert_eq!(got,payload);
        assert_eq!(app.read(&mut b).unwrap(),0);
    }
    /// The real kernel may have short DATA and FIN buffered before one
    /// FD_READ|FD_CLOSE. Both half closes propagate without relying on a
    /// second Rust TX scheduling opportunity.
    #[test]
    fn plan029_h1941_coalesced_fin_peek_one_turn_short_kernel_tcp(){
        use std::time::Duration;
        fn pair()->(TcpStream,TcpStream){
            let listener=TcpListener::bind((Ipv4Addr::LOCALHOST,0)).unwrap();
            let client=TcpStream::connect(listener.local_addr().unwrap()).unwrap();
            let (server,_)=listener.accept().unwrap();
            (server,client)
        }
        let (inner,mut app)=pair();
        let (outer,mut guest)=pair();
        app.set_read_timeout(Some(Duration::from_secs(3))).unwrap();
        guest.set_read_timeout(Some(Duration::from_secs(3))).unwrap();
        let mut relay=TcpDirectRelay::new(inner,outer).unwrap();
        relay.enable_event_driven_reads();
        let mut scratch=[0u8;QUANTUM_BYTES];
        let input=[0x57u8;64];
        app.write_all(&input).unwrap();
        app.shutdown(Shutdown::Write).unwrap();
        std::thread::sleep(Duration::from_millis(20));
        relay.note_read_event(true,false);
        relay.note_close_event(true,false);
        let upload=relay.service_once_with_scratch(usize::MAX,&mut scratch).unwrap();
        assert_eq!(upload.inner_read,64);
        assert_eq!(upload.io.fin_peek_calls,[1,0]);
        assert_eq!(upload.io.fin_peek_eof,[1,0]);
        assert!(!upload.close_probe_due);
        assert!(relay.half_close_state()[0]&&relay.half_close_state()[2]);
        let mut got=[0u8;64];
        guest.read_exact(&mut got).unwrap();
        assert_eq!(got,input);
        let mut eof=[0u8;1];
        assert_eq!(guest.read(&mut eof).unwrap(),0);
        guest.write_all(&input).unwrap();
        guest.shutdown(Shutdown::Write).unwrap();
        std::thread::sleep(Duration::from_millis(20));
        relay.note_read_event(false,true);
        relay.note_close_event(false,true);
        let download=relay.service_once_with_scratch(usize::MAX,&mut scratch).unwrap();
        assert_eq!(download.outer_read,64);
        assert_eq!(download.io.fin_peek_calls,[0,1]);
        assert_eq!(download.io.fin_peek_eof,[0,1]);
        assert!(download.finished);
        assert_eq!(relay.half_close_state(),[true,true,true,true]);
        app.read_exact(&mut got).unwrap();
        assert_eq!(got,input);
        assert_eq!(app.read(&mut eof).unwrap(),0);
    }
    #[test]
    fn plan029_per_leg_read_wouldblock_disarm_fd_read_rearm_and_fin(){
        use std::time::Duration;
        fn pair()->(TcpStream,TcpStream){
            let listener=TcpListener::bind((Ipv4Addr::LOCALHOST,0)).unwrap();
            let client=TcpStream::connect(listener.local_addr().unwrap()).unwrap();
            let (server,_)=listener.accept().unwrap();
            (server,client)
        }
        let (inner,mut app)=pair();
        let (outer,mut remote)=pair();
        let mut relay=TcpDirectRelay::new(inner,outer).unwrap();
        relay.enable_event_driven_reads();
        let mut scratch=[0u8;QUANTUM_BYTES];
        app.set_read_timeout(Some(Duration::from_secs(3))).unwrap();
        remote.set_read_timeout(Some(Duration::from_secs(3))).unwrap();
        let idle=relay.service_once_with_scratch(usize::MAX,&mut scratch).unwrap();
        assert_eq!(idle.io.read_wouldblock,[1,1]);
        let payload=vec![0x51u8;2048];
        app.write_all(&payload).unwrap();
        let no_signal=relay.service_once_with_scratch(usize::MAX,&mut scratch).unwrap();
        assert_eq!(no_signal.io.read_calls,[0,0]);
        assert_eq!(no_signal.io.event_suppressed_reads,[1,1]);
        relay.note_read_event(true,false);
        let forward=relay.service_once_with_scratch(usize::MAX,&mut scratch).unwrap();
        assert_eq!(forward.inner_read,payload.len());
        assert_eq!(forward.io.read_calls,[1,0]);
        let mut got=vec![0;payload.len()];
        remote.read_exact(&mut got).unwrap();
        assert_eq!(got,payload);
        // Now only the physical outer socket is signaled. Keep the
        // earlier inner read state independent of the outer FD_READ.
        let response=vec![0x52u8;3072];
        remote.write_all(&response).unwrap();
        relay.note_read_event(false,true);
        let backward=relay.service_once_with_scratch(usize::MAX,&mut scratch).unwrap();
        assert_eq!(backward.outer_read,response.len());
        assert_eq!(backward.inner_read,0);
        let mut response_got=vec![0;response.len()];
        app.read_exact(&mut response_got).unwrap();
        assert_eq!(response_got,response);
        // FD_CLOSE is allowed to re-arm recv(0), so neither half-close
        // waits for a fake timeout or application payload.
        app.shutdown(Shutdown::Write).unwrap();
        remote.shutdown(Shutdown::Write).unwrap();
        relay.note_read_event(true,true);
        let mut finished=false;
        for _ in 0..100{
            let t=relay.service_once_with_scratch(usize::MAX,&mut scratch).unwrap();
            if t.finished{finished=true;break}
            std::thread::sleep(Duration::from_millis(1));
        }
        assert!(finished,"both TCP FINs must propagate without a timer");
        assert_eq!(relay.pending_bytes(),0);
    }
    #[test]
    fn plan029_same_binary_probe_copy_mode_preserves_old_queue_path(){
        use std::time::Duration;
        fn pair()->(TcpStream,TcpStream){
            let l=TcpListener::bind((Ipv4Addr::LOCALHOST,0)).unwrap();
            let a=TcpStream::connect(l.local_addr().unwrap()).unwrap();
            let (b,_)=l.accept().unwrap();
            (b,a)
        }
        let (inner,mut app)=pair();let (outer,mut remote)=pair();
        remote.set_read_timeout(Some(Duration::from_secs(3))).unwrap();
        let mut relay=TcpDirectRelay::with_fast_forward(inner,outer,false).unwrap();
        let payload=vec![0x5a;4096];
        app.write_all(&payload).unwrap();
        let mut scratch=[0u8;QUANTUM_BYTES];
        let mut copied=0;let mut forwarded=0;
        for _ in 0..200{
            let tick=relay.service_once_with_scratch(usize::MAX,&mut scratch).unwrap();
            copied+=tick.copied_to_queue;forwarded+=tick.forwarded_without_queue;
            if tick.inner_read>0{break}
            std::thread::sleep(Duration::from_millis(1));
        }
        assert_eq!(copied,payload.len());
        assert_eq!(forwarded,0);
        let mut echo=vec![0u8;payload.len()];
        remote.read_exact(&mut echo).unwrap();
        assert_eq!(echo,payload);
    }
    #[test]
    fn borrowed_relay_scratch_is_bounded_and_preserved_when_idle(){
        let l1=TcpListener::bind((Ipv4Addr::LOCALHOST,0)).unwrap();
        let s1=TcpStream::connect(l1.local_addr().unwrap()).unwrap();
        let (peer1,_)=l1.accept().unwrap();
        let l2=TcpListener::bind((Ipv4Addr::LOCALHOST,0)).unwrap();
        let s2=TcpStream::connect(l2.local_addr().unwrap()).unwrap();
        let (peer2,_)=l2.accept().unwrap();
        let mut relay=TcpDirectRelay::new(s1,s2).unwrap();
        let mut scratch=vec![0xA5;QUANTUM_BYTES];
        assert_eq!(relay.service_once_with_scratch(0,&mut scratch[..QUANTUM_BYTES-1]),
            Err(DirectTcpError::BufferBudget));
        relay.service_once_with_scratch(0,&mut scratch).unwrap();
        assert!(scratch.iter().all(|byte|*byte==0xA5));
        drop((peer1,peer2));
    }
    #[test]
    fn sharded_socket_readiness_bounds_fixed_wait_handles_and_ports(){
        #[cfg(target_os="windows")]
        {
            use super::win::{SocketReadiness,TCP_EVENT_SHARDS};
            assert_eq!(TCP_EVENT_SHARDS,16);
            assert_eq!(SocketReadiness::shard(0),0);
            assert_eq!(SocketReadiness::shard(16),0);
            assert_eq!(SocketReadiness::shard(17),1);
            let event=SocketReadiness::new().unwrap();
            assert_eq!(event.handles().len(),TCP_EVENT_SHARDS);
            assert!(event.handles().iter().all(|handle|*handle!=0));
        }
    }
    /// Actual 128 Windows loopback kernel socket pairs with only two
    /// readable, both sharing ONE manual-reset event. Enumerating the first
    /// socket and resetting the group MUST NOT erase the second socket's
    /// recorded FD_READ or force per-idle-flow polling.
    #[cfg(target_os="windows")]
    #[test]
    fn plan029_sharded_wsa_128_idle_two_active_same_event_no_lost_read(){
        use std::io::{Read,Write};
        use std::os::windows::io::AsRawSocket;
        use crate::windows_native_io::{wait_ready,WaitResult};
        let listener=TcpListener::bind((Ipv4Addr::LOCALHOST,0)).unwrap();
        let events=SocketReadiness::new().unwrap();
        let mut sockets=Vec::with_capacity(128);
        for i in 0..128{
            let client=TcpStream::connect(listener.local_addr().unwrap()).unwrap();
            let (server,_)=listener.accept().unwrap();
            // FD_READ | FD_CLOSE: no false initial FD_WRITE storms for 128
            // genuinely idle connections. This is one owned event group.
            events.watch(server.as_raw_socket() as usize,
                i%TCP_EVENT_SHARDS,1|32).unwrap();
            sockets.push((client,server));
        }
        assert_eq!(wait_ready(events.handles(),0).unwrap(),WaitResult::Timeout);
        // Ports 15 and 31 share shard15 while 126 other sockets are idle.
        sockets[15].0.write_all(b"A").unwrap();
        sockets[31].0.write_all(b"B").unwrap();
        assert_eq!(wait_ready(events.handles(),3000).unwrap(),
            WaitResult::Ready(15));
        let mut seen=Vec::new();
        let mut first=true;
        for i in (0..128).filter(|i|i%TCP_EVENT_SHARDS==15){
            let flags=events.take(sockets[i].1.as_raw_socket() as usize,
                15,first).unwrap();
            first=false;
            if flags&1!=0{seen.push(i)}
        }
        assert_eq!(seen,[15,31]);
        let mut reply=[0u8;1];
        sockets[15].1.read_exact(&mut reply).unwrap();
        assert_eq!(reply[0],b'A');
        sockets[31].1.read_exact(&mut reply).unwrap();
        assert_eq!(reply[0],b'B');
        // All socket RAII closes before the event group; no thread or
        // extra Wintun owner was introduced by this test.
    }
    #[test]
    fn one_global_pool_blocks_only_new_direct_reads_not_drains(){
        assert_eq!(bounded_relay_read(0,64*1024,0),0);
        assert_eq!(bounded_relay_read(48*1024,64*1024,4096),4096);
        assert_eq!(bounded_relay_read(63*1024,64*1024,4096),1024);
        assert_eq!(bounded_relay_read(64*1024,64*1024,8192),0);
        assert_eq!(bounded_relay_read(0,64*1024,usize::MAX),64*1024);
        assert_eq!(bounded_relay_read(0,64*1024,8192),8192);
    }
}
