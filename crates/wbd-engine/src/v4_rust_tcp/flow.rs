//! Shared dual-leg business TCP endpoints. The native owner supplies
//! authenticated tunnel packets, TUN packets, socket readiness and deadlines.
//! No autonomous polling loop, second transport, or Go hot-path callback.
use std::{io, io::{Read, Write}, net::{Shutdown, SocketAddr, TcpStream}, time::Instant};
use super::{Segments, transfer, ipv4::{self, Packet, Tuple}};
use super::pktkit::vtcp::{Conn, ConnConfig, CongestionKind, MtuProbing};

// Selected paired Normal profile: local CUBIC, middle BBR1 for measured
// Linux comparison, ACK2, SACK compression, actual native send grants.
const TURN_BYTES: usize = 64 * 1024;
type Packets = Vec<Vec<u8>>;

struct Endpoint {
    tuple: Tuple,
    mtu: u16,
    conn: Conn,
}
impl Endpoint {
    fn new(tuple: Tuple, mtu: u16, cc: CongestionKind, middle: bool) -> io::Result<Self> {
        // IPv4/TCP options are subtracted from the MSS by pktkit itself.
        let mss = mtu.checked_sub(40).filter(|&v| v >= 64)
            .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidInput, "inner TCP MTU"))?;
        // Selected research-branch default. Explicit 0 is a laboratory
        // comparison choice, never a runtime fallback or peer negotiation.
        let parity = std::env::var_os("WBD_M0_LINUX_PARITY").as_deref() != Some(std::ffi::OsStr::new("0"));
        let max_buf = if parity || middle && std::env::var_os("WBD_M0_TCP_EXPERIMENT").as_deref() == Some(std::ffi::OsStr::new("cap64")) {64 << 20} else {16 << 20};
        let cc = if middle { match std::env::var_os("WBD_M0_MIDDLE_CC").as_deref().and_then(|s|s.to_str()) {
            Some("cubic") => CongestionKind::Cubic,
            Some("bbr1") => CongestionKind::Bbr1,
            Some("bbr3") => CongestionKind::Bbr,
            _ if parity => CongestionKind::Bbr1,
            _ => cc,
        }} else {cc};
        let quantum_mss=if middle&&parity&&std::env::var_os("WBD_M0_NATIVE_PACE_QUANTUM8").as_deref()==Some(std::ffi::OsStr::new("1")){8}else{32};
        if quantum_mss==8{eprintln!("WBD_M0_TCP_PACE_QUANTUM mss=8");}
        let conn = Conn::new(ConnConfig {
            local_addr: Some(SocketAddr::V4(tuple.src)),
            remote_addr: Some(SocketAddr::V4(tuple.dst)),
            local_port: tuple.src.port(),
            remote_port: tuple.dst.port(),
            mss,
            congestion: cc,
            nodelay: !parity,
            linux_parity: parity,
            send_buf_max: max_buf,
            recv_buf_max: max_buf,
            // Temporary causal experiment: both variants use the same instrumented build.
            middle_ack_three: !parity && middle && std::env::var_os("WBD_M0_ACK_PROBE").as_deref() != Some(std::ffi::OsStr::new("2")),
            middle_sack_compress: parity || middle && std::env::var_os("WBD_M0_SACK_COMPRESS").as_deref() == Some(std::ffi::OsStr::new("1")),
            native_owner_turn: parity,
            rack_keep_reo_window:middle&&parity&&std::env::var_os("WBD_M0_RACK_KEEP_WINDOW").as_deref()==Some(std::ffi::OsStr::new("1")),
            native_pace_quantum_mss:quantum_mss,
            // Selected paired research default; explicit 0 retains the old admission.
            relay_pending_limit:if parity&&std::env::var_os("WBD_M0_RELAY_PENDING_CREDIT").as_deref()!=Some(std::ffi::OsStr::new("0")){Some(2*TURN_BYTES)}else{None},
            native_pace_ceiling:if middle&&parity{
                match std::env::var_os("WBD_M0_NATIVE_PACE_MBPS").as_deref().and_then(|s|s.to_str()){
                    Some("160")=>Some(20_000_000),
                    Some("80")=>Some(10_000_000),
                    _ if std::env::var_os("WBD_M0_NATIVE_PACE80").as_deref()==Some(std::ffi::OsStr::new("1"))=>Some(10_000_000),
                    _=>None,
                }
            }else{None},
            gentle_bbr1_startup:middle&&parity&&std::env::var_os("WBD_M0_BBR1_STARTUP15").as_deref()==Some(std::ffi::OsStr::new("1")),
            native_bounded_pacing: parity || std::env::var_os("WBD_M0_BOUNDED_PACE").as_deref() == Some(std::ffi::OsStr::new("1")),
            mtu_probing: MtuProbing::Off,
            ..ConnConfig::default()
        });
        Ok(Self { tuple, mtu, conn })
    }
    fn append(&self, segments: Segments, out: &mut Packets) -> io::Result<()> {
        for (tcp, ecn) in segments.packets.into_iter().zip(segments.ecn) {
            out.push(ipv4::encode(self.tuple, tcp, ecn, self.mtu)?);
        }
        Ok(())
    }
    fn emit(&self, packets: Vec<Vec<u8>>, out: &mut Packets) -> io::Result<()> {
        self.append(Segments::from_conn(&self.conn, packets), out)
    }
    fn open(&mut self, out: &mut Packets) -> io::Result<()> {
        let p = self.conn.connect();
        self.emit(p, out)
    }
    fn accept(&mut self, p: &Packet, out: &mut Packets) -> io::Result<()> {
        let response = self.conn.accept_syn_ecn(&p.segment, p.ecn);
        self.emit(response, out)
    }
    fn receive(&mut self, p: &Packet, out: &mut Packets) -> io::Result<()> {
        if p.tuple != self.tuple.reverse() {
            return Err(io::Error::new(io::ErrorKind::InvalidInput, "TCP flow tuple mismatch"));
        }
        let response = self.conn.handle_segment_ecn(&p.segment, p.ecn);
        self.emit(response, out)
    }
    fn close(&mut self, out: &mut Packets) -> io::Result<()> {
        let packets = self.conn.close();
        self.emit(packets, out)
    }
    fn abort(&mut self, out: &mut Packets) -> io::Result<()> {
        let packets = self.conn.abort();
        self.emit(packets, out)
    }
    fn tick(&mut self, now: Instant, out: &mut Packets) -> io::Result<()> {
        if self.conn.next_deadline().is_some_and(|d| d <= now) {
            let packets = self.conn.tick();
            self.emit(packets, out)?;
        }
        Ok(())
    }
    fn deadline(&self) -> Option<Instant> { self.conn.next_deadline() }
}

#[derive(Default)]
pub(crate) struct ClientOutput {
    pub(crate) local: Packets,
    pub(crate) tunnel: Packets,
}

/// One application 4-tuple, with distinct TCP sequence spaces for the
/// local OS peer and middle peer. The original destination remains the
/// middle IPv4 destination, protected by the existing session AEAD.
pub(crate) struct ClientFlow {
    local: Endpoint,
    middle: Endpoint,
    local_fin_forwarded: bool,
    middle_fin_forwarded: bool,
    drive_due: Option<Instant>,
}
impl ClientFlow {
    pub(crate) fn open(syn: &Packet, local_mtu: u16, middle_mtu: u16)
        -> io::Result<(Self, ClientOutput)>
    {
        if !syn.initial_syn() {
            return Err(io::Error::new(io::ErrorKind::InvalidInput, "TCP open requires SYN"));
        }
        let mut flow = Self {
            local: Endpoint::new(syn.tuple.reverse(), local_mtu, CongestionKind::Cubic, false)?,
            middle: Endpoint::new(syn.tuple, middle_mtu, CongestionKind::Bbr, true)?,
            local_fin_forwarded: false,
            middle_fin_forwarded: false,
            drive_due:None,
        };
        let mut out = ClientOutput::default();
        flow.local.accept(syn, &mut out.local)?;
        flow.middle.open(&mut out.tunnel)?;
        Ok((flow, out))
    }
    pub(crate) fn probe(&self, id:u64, wall_ns:u128) {
        self.local.conn.m0_probe("client-local",id,wall_ns);
        self.middle.conn.m0_probe("client-middle",id,wall_ns);
    }
    pub(crate) fn tuple(&self) -> Tuple { self.middle.tuple }
    fn begin_turn(&mut self){self.local.conn.begin_native_turn();self.middle.conn.begin_native_turn();}
    pub(crate) fn admit(&mut self,local:bool,seq:u32,len:u32,now:Instant)->bool{
        if local{self.local.conn.native_admit(seq,len,now)}else{self.middle.conn.native_admit(seq,len,now)}
    }
    pub(crate) fn on_local(&mut self, p: &Packet) -> io::Result<ClientOutput> {
        self.begin_turn();let mut out = ClientOutput::default();
        self.local.receive(p, &mut out.local)?;
        self.drive(&mut out)?;
        Ok(out)
    }
    pub(crate) fn on_middle(&mut self, p: &Packet) -> io::Result<ClientOutput> {
        self.begin_turn();let mut out = ClientOutput::default();
        self.middle.receive(p, &mut out.tunnel)?;
        self.drive(&mut out)?;
        Ok(out)
    }
    pub(crate) fn tick(&mut self, now: Instant) -> io::Result<ClientOutput> {
        self.begin_turn();let mut out = ClientOutput::default();
        self.local.tick(now, &mut out.local)?;
        self.middle.tick(now, &mut out.tunnel)?;
        self.drive(&mut out)?;
        Ok(out)
    }
    pub(crate) fn next_deadline(&self) -> Option<Instant> {
        self.local.deadline().into_iter().chain(self.middle.deadline()).chain(self.drive_due).min()
    }
    pub(crate) fn finished(&self) -> bool {
        self.local.conn.is_closed() && self.middle.conn.is_closed()
    }
    fn drive(&mut self, out: &mut ClientOutput) -> io::Result<()> {
        self.drive_due=None;
        let bounded=self.local.conn.native_turn_enabled();
        if self.local.conn.abnormal_end() || self.middle.conn.abnormal_end() {
            self.local.abort(&mut out.local)?;
            self.middle.abort(&mut out.tunnel)?;
            return Ok(());
        }
        for up in [true, false] {
            let (from, to, from_out, to_out, fin_forwarded) = if up {
                (&mut self.local, &mut self.middle, &mut out.local,
                 &mut out.tunnel, &mut self.local_fin_forwarded)
            } else {
                (&mut self.middle, &mut self.local, &mut out.tunnel,
                 &mut out.local, &mut self.middle_fin_forwarded)
            };
            // The receive ring itself is the relay buffer. No bytes
            // leave it until the peer leg accepts them. A ring wraps at
            // most once; the destination capacity is re-read each time.
            let mut budget=if bounded{TURN_BYTES}else{usize::MAX};
            while budget!=0&&from.conn.readable() != 0 && to.conn.relay_send_available() != 0 {
                let (n, a, b) = transfer(&mut from.conn, &mut to.conn, TURN_BYTES.min(budget));
                from.append(a, from_out)?;
                to.append(b, to_out)?;
                if n == 0 { break }
                budget-=n;
            }
            if from.conn.readable()==0 { to.conn.note_native_source_dry(); }
            if bounded&&budget==0&&from.conn.readable()!=0&&to.conn.relay_send_available()!=0{self.drive_due=Some(Instant::now());}
            if !*fin_forwarded && from.conn.fin_received() &&
                from.conn.readable() == 0 && to.conn.is_established() {
                to.close(to_out)?;
                *fin_forwarded = true;
            }
        }
        Ok(())
    }
}

/// Native origin connection; the platform event owner supplies readiness.
/// TCP windows remain coupled to actual accepted stream bytes, not an
/// additional relay queue or a successful socket-read intention.
pub(crate) struct ServerFlow {
    middle: Endpoint,
    stream: TcpStream,
    connected: bool,
    origin_eof: bool,
    origin_write_closed: bool,
    ack_drain:bool,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct Interest {
    pub(crate) read: bool,
    pub(crate) write: bool,
}
impl ServerFlow {
    /// Only called for an authenticated, lease-admitted SYN and allowed
    /// original destination. Linux opens the nonblocking origin socket
    /// while the middle handshake proceeds; no thread or blocking Dial.
    #[cfg(target_os="linux")]
    pub(crate) fn open(syn: &Packet, mtu: u16) -> io::Result<(Self, Packets)> {
        if !syn.initial_syn() {
            return Err(io::Error::new(io::ErrorKind::InvalidInput, "TCP open requires SYN"));
        }
        let (stream, connected) = super::linux_socket::connect_origin(syn.tuple.dst)?;
        Self::with_socket(syn, mtu, stream, connected)
    }
    fn with_socket(syn: &Packet, mtu: u16, stream: TcpStream, connected: bool)
        -> io::Result<(Self, Packets)>
    {
        let mut middle = Endpoint::new(syn.tuple.reverse(), mtu, CongestionKind::Bbr, true)?;
        let mut out = Vec::new();
        middle.accept(syn, &mut out)?;
        let ack_drain=middle.conn.native_turn_enabled()&&std::env::var_os("WBD_M0_SERVER_ACK_DRAIN").as_deref()==Some(std::ffi::OsStr::new("1"));
        Ok((Self { middle, stream, connected, origin_eof: false, origin_write_closed: false,ack_drain }, out))
    }
    pub(crate) fn probe(&self, id:u64, wall_ns:u128) {
        self.middle.conn.m0_probe("server-middle",id,wall_ns);
        eprintln!("WBD_M0_TCP_ORIGIN wall_ns={} id={} connected={} interest={:?} eof={} write_closed={} ack_drain={}",
            wall_ns,id,self.connected,self.interest(),self.origin_eof,self.origin_write_closed,self.ack_drain);
    }
    pub(crate) fn tuple(&self) -> Tuple { self.middle.tuple.reverse() }
    pub(crate) fn socket(&self) -> &TcpStream { &self.stream }
    pub(crate) fn interest(&self) -> Interest {
        if self.middle.conn.is_closed() { return Interest { read: false, write: false } }
        if !self.connected { return Interest { read: false, write: true } }
        Interest {
            read: !self.origin_eof && self.middle.conn.relay_send_available() != 0,
            write: !self.origin_write_closed && self.middle.conn.readable() != 0,
        }
    }
    pub(crate) fn admit(&mut self,seq:u32,len:u32,now:Instant)->bool{self.middle.conn.native_admit(seq,len,now)}
    pub(crate) fn on_packet(&mut self, p: &Packet) -> io::Result<Packets> {
        if self.ack_drain{self.middle.conn.begin_native_ack_turn(&p.segment);}else{self.middle.conn.begin_native_turn();}
        let mut out = Vec::new();
        self.middle.receive(p, &mut out)?;
        self.finish_write(&mut out)?;
        Ok(out)
    }
    pub(crate) fn next_deadline(&self) -> Option<Instant> { self.middle.deadline() }
    pub(crate) fn finished(&self) -> bool { self.middle.conn.is_closed() }
    pub(crate) fn tick(&mut self, now: Instant) -> io::Result<Packets> {
        self.middle.conn.begin_native_turn();let mut out = Vec::new();
        self.middle.tick(now, &mut out)?;
        self.finish_write(&mut out)?;
        Ok(out)
    }
    fn finish_write(&mut self, out: &mut Packets) -> io::Result<()> {
        if self.middle.conn.abnormal_end() {
            // Origin must observe a transport error, not a synthesized FIN.
            // The native owner drops this exact socket on removal.
            return Ok(())
        }
        if self.connected && !self.origin_write_closed && self.middle.conn.fin_received() &&
            self.middle.conn.readable() == 0 {
            match self.stream.shutdown(Shutdown::Write) {
                Ok(()) => self.origin_write_closed = true,
                Err(e) => { eprintln!("WBD_M0_TCP_ORIGIN_ERROR tuple={:?} op=shutdown_write error={:?}",self.tuple(),e); self.middle.abort(out)?; },
            }
        }
        Ok(())
    }
    pub(crate) fn on_socket_ready(
        &mut self, readable: bool, writable: bool, scratch: &mut [u8],
    ) -> io::Result<Packets> {
        self.middle.conn.begin_native_turn();let mut out = Vec::new();
        if self.middle.conn.is_closed() { return Ok(out) }
        if let Some(e)=self.stream.take_error()? {
            eprintln!("WBD_M0_TCP_ORIGIN_ERROR tuple={:?} op=socket_error error={:?}",self.tuple(),e);
            self.middle.abort(&mut out)?;
            return Ok(out)
        }
        if !self.connected {
            if !writable { return Ok(out) }
            if let Err(e)=self.stream.peer_addr() {
                eprintln!("WBD_M0_TCP_ORIGIN_ERROR tuple={:?} op=connect_peer error={:?}",self.tuple(),e);
                self.middle.abort(&mut out)?;
                return Ok(out)
            }
            self.connected = true;
        }
        if writable && !self.origin_write_closed {
            let mut budget = TURN_BYTES;
            while budget != 0 && self.middle.conn.readable() != 0 {
                let stream = &mut self.stream;
                match self.middle.conn.read_to(budget, |bytes| stream.write(bytes)) {
                    Ok(0) => { eprintln!("WBD_M0_TCP_ORIGIN_ERROR tuple={:?} op=write_zero",self.tuple()); self.middle.abort(&mut out)?; return Ok(out) }
                    Ok(n) => budget -= n,
                    Err(e) if e.kind() == io::ErrorKind::WouldBlock => break,
                    Err(e) if e.kind() == io::ErrorKind::Interrupted => continue,
                    Err(e) => { eprintln!("WBD_M0_TCP_ORIGIN_ERROR tuple={:?} op=write error={:?}",self.tuple(),e); self.middle.abort(&mut out)?; return Ok(out) }
                }
            }
            let packets = self.middle.conn.take_outgoing();
            self.middle.emit(packets, &mut out)?;
        }
        self.finish_write(&mut out)?;
        if readable && !self.origin_eof && !self.middle.conn.is_closed() {
            let mut budget = TURN_BYTES;
            while budget != 0 {
                let n = self.middle.conn.relay_send_available().min(budget).min(scratch.len());
                if n == 0 { break }
                match self.stream.read(&mut scratch[..n]) {
                    Ok(0) => {
                        self.origin_eof = true;
                        self.middle.conn.note_native_source_dry();
                        self.middle.close(&mut out)?;
                        break
                    }
                    Ok(n) => {
                        let (accepted, packets) = self.middle.conn.write(&scratch[..n]);
                        assert_eq!(accepted, n);
                        self.middle.emit(packets, &mut out)?;
                        budget -= n;
                    }
                    Err(e) if e.kind() == io::ErrorKind::WouldBlock => { self.middle.conn.note_native_source_dry(); break; }
                    Err(e) if e.kind() == io::ErrorKind::Interrupted => continue,
                    Err(e) => { eprintln!("WBD_M0_TCP_ORIGIN_ERROR tuple={:?} op=read error={:?}",self.tuple(),e); self.middle.abort(&mut out)?; break }
                }
            }
        }
        Ok(out)
    }
}

#[cfg(all(test,target_os="linux"))]
mod tests {
    use super::*;
    use super::super::pktkit::vtcp::flags;
    use std::{net::TcpListener,time::Duration};
    fn parse(p: &[u8]) -> Packet { Packet::parse(p).unwrap().unwrap() }
    // Emulated wire is the actual test send attempt, before delivery.
    enum Leg { App, Local, Up, Down }
    fn enqueue(q:&mut std::collections::VecDeque<(Leg,Vec<u8>)>,out:ClientOutput){
        q.extend(out.local.into_iter().map(|p|(Leg::Local,p)));
        q.extend(out.tunnel.into_iter().map(|p|(Leg::Up,p)));
    }
    fn pump(app:&mut Endpoint,client:&mut ClientFlow,server:&mut ServerFlow,
        mut q:std::collections::VecDeque<(Leg,Vec<u8>)>){
        for _ in 0..64{
            while let Some((leg,wire))=q.pop_front(){
                let p=parse(&wire);
                let n=p.segment.payload.len() as u32;
                let now=Instant::now();
                match leg{
                    Leg::App=>{
                        if n!=0{app.conn.native_admit(p.segment.seq,n,now);}
                        enqueue(&mut q,client.on_local(&p).unwrap());
                    },
                    Leg::Local=>{
                        if n!=0{client.admit(true,p.segment.seq,n,now);}
                        let mut out=Vec::new();app.receive(&p,&mut out).unwrap();
                        q.extend(out.into_iter().map(|p|(Leg::App,p)));
                    },
                    Leg::Up=>{
                        if n!=0{client.admit(false,p.segment.seq,n,now);}
                        q.extend(server.on_packet(&p).unwrap().into_iter().map(|p|(Leg::Down,p)));
                    },
                    Leg::Down=>{
                        if n!=0{server.admit(p.segment.seq,n,now);}
                        enqueue(&mut q,client.on_middle(&p).unwrap());
                    },
                }
            }
            let now=Instant::now();
            if client.next_deadline().is_some_and(|d|d<=now){
                enqueue(&mut q,client.tick(now).unwrap());
            }
            if server.next_deadline().is_some_and(|d|d<=now){
                q.extend(server.tick(now).unwrap().into_iter().map(|p|(Leg::Down,p)));
            }
            if app.deadline().is_some_and(|d|d<=now){
                let mut out=Vec::new();app.conn.begin_native_turn();app.tick(now,&mut out).unwrap();
                q.extend(out.into_iter().map(|p|(Leg::App,p)));
            }
            if q.is_empty(){return}
        }
        panic!("test wire did not quiesce");
    }
    #[test]
    fn dual_leg_wire_and_real_nonblocking_origin_bidirectional() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let SocketAddr::V4(dst) = listener.local_addr().unwrap() else { panic!() };
        let tuple = Tuple { src:"10.66.0.2:40201".parse().unwrap(), dst };
        let mut app = Endpoint::new(tuple, 1280, CongestionKind::Cubic, false).unwrap();
        let mut syn = Vec::new();
        app.open(&mut syn).unwrap();
        let (mut client, out) = ClientFlow::open(&parse(&syn[0]), 1280, 1100).unwrap();
        let (mut server, reverse_syn) = ServerFlow::open(&parse(&out.tunnel[0]), 1100).unwrap();
        let (mut origin, _) = listener.accept().unwrap();
        origin.set_read_timeout(Some(Duration::from_secs(2))).unwrap();
        let mut scratch = [0; 65536];
        let ready=server.on_socket_ready(false, true, &mut scratch).unwrap();
        let mut q=std::collections::VecDeque::new();
        q.extend(out.local.into_iter().map(|p|(Leg::Local,p)));
        q.extend(reverse_syn.into_iter().chain(ready).map(|p|(Leg::Down,p)));
        pump(&mut app,&mut client,&mut server,q);

        let request = b"real origin request / first payload";
        app.conn.begin_native_turn();
        let (n, data) = app.conn.write(request);
        assert_eq!(n, request.len());
        let mut wire = Vec::new();
        app.emit(data, &mut wire).unwrap();
        pump(&mut app,&mut client,&mut server,wire.into_iter().map(|p|(Leg::App,p)).collect());
        assert!(server.interest().write);
        let response = server.on_socket_ready(false, true, &mut scratch).unwrap();
        pump(&mut app,&mut client,&mut server,response.into_iter().map(|p|(Leg::Down,p)).collect());
        let mut got = vec![0; request.len()];
        origin.read_exact(&mut got).unwrap();
        assert_eq!(got, request);

        let reply = b"actual kernel origin response";
        origin.write_all(reply).unwrap();
        origin.shutdown(Shutdown::Write).unwrap();
        let response = server.on_socket_ready(true, false, &mut scratch).unwrap();
        pump(&mut app,&mut client,&mut server,response.into_iter().map(|p|(Leg::Down,p)).collect());
        let mut got = vec![0; reply.len()];
        assert_eq!(app.conn.read(&mut got), reply.len());
        assert_eq!(got, reply);
        // The app sees the origin's genuine half-close; the upstream leg
        // remains writable until the app itself closes.
        assert!(app.conn.fin_received());
        assert!(!app.conn.abnormal_end());
        app.conn.begin_native_turn();
        let close = app.conn.close();
        assert!(close.iter().any(|p| super::super::pktkit::vtcp::Segment::parse(p)
            .unwrap().has_flag(flags::FIN)));
    }
}
