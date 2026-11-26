//! Shared dual-leg business TCP endpoints. The native owner supplies
//! authenticated tunnel packets, TUN packets, socket readiness and deadlines.
//! No autonomous polling loop, second transport, or Go hot-path callback.
use std::{io, io::{Read, Write}, net::{Shutdown, SocketAddr, TcpStream}, time::Instant};
use super::{Segments, transfer, ipv4::{self, Packet, Tuple}};
use super::pktkit::vtcp::{Conn, ConnConfig, CongestionKind, MtuProbing};

const TURN_BYTES: usize = 64 * 1024;
type Packets = Vec<Vec<u8>>;

struct Endpoint {
    tuple: Tuple,
    mtu: u16,
    conn: Conn,
}
impl Endpoint {
    fn new(tuple: Tuple, mtu: u16, cc: CongestionKind) -> io::Result<Self> {
        // IPv4/TCP options are subtracted from the MSS by pktkit itself.
        let mss = mtu.checked_sub(40).filter(|&v| v >= 64)
            .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidInput, "inner TCP MTU"))?;
        let conn = Conn::new(ConnConfig {
            local_addr: Some(SocketAddr::V4(tuple.src)),
            remote_addr: Some(SocketAddr::V4(tuple.dst)),
            local_port: tuple.src.port(),
            remote_port: tuple.dst.port(),
            mss,
            congestion: cc,
            nodelay: true,
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
}
impl ClientFlow {
    pub(crate) fn open(syn: &Packet, local_mtu: u16, middle_mtu: u16)
        -> io::Result<(Self, ClientOutput)>
    {
        if !syn.initial_syn() {
            return Err(io::Error::new(io::ErrorKind::InvalidInput, "TCP open requires SYN"));
        }
        let mut flow = Self {
            local: Endpoint::new(syn.tuple.reverse(), local_mtu, CongestionKind::Cubic)?,
            middle: Endpoint::new(syn.tuple, middle_mtu, CongestionKind::Bbr)?,
            local_fin_forwarded: false,
            middle_fin_forwarded: false,
        };
        let mut out = ClientOutput::default();
        flow.local.accept(syn, &mut out.local)?;
        flow.middle.open(&mut out.tunnel)?;
        Ok((flow, out))
    }
    pub(crate) fn tuple(&self) -> Tuple { self.middle.tuple }
    pub(crate) fn on_local(&mut self, p: &Packet) -> io::Result<ClientOutput> {
        let mut out = ClientOutput::default();
        self.local.receive(p, &mut out.local)?;
        self.drive(&mut out)?;
        Ok(out)
    }
    pub(crate) fn on_middle(&mut self, p: &Packet) -> io::Result<ClientOutput> {
        let mut out = ClientOutput::default();
        self.middle.receive(p, &mut out.tunnel)?;
        self.drive(&mut out)?;
        Ok(out)
    }
    pub(crate) fn tick(&mut self, now: Instant) -> io::Result<ClientOutput> {
        let mut out = ClientOutput::default();
        self.local.tick(now, &mut out.local)?;
        self.middle.tick(now, &mut out.tunnel)?;
        self.drive(&mut out)?;
        Ok(out)
    }
    pub(crate) fn next_deadline(&self) -> Option<Instant> {
        self.local.deadline().into_iter().chain(self.middle.deadline()).min()
    }
    pub(crate) fn finished(&self) -> bool {
        self.local.conn.is_closed() && self.middle.conn.is_closed()
    }
    fn drive(&mut self, out: &mut ClientOutput) -> io::Result<()> {
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
            while from.conn.readable() != 0 && to.conn.send_available() != 0 {
                let (n, a, b) = transfer(&mut from.conn, &mut to.conn, TURN_BYTES);
                from.append(a, from_out)?;
                to.append(b, to_out)?;
                if n == 0 { break }
            }
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
        let mut middle = Endpoint::new(syn.tuple.reverse(), mtu, CongestionKind::Bbr)?;
        let mut out = Vec::new();
        middle.accept(syn, &mut out)?;
        Ok((Self { middle, stream, connected, origin_eof: false, origin_write_closed: false }, out))
    }
    pub(crate) fn tuple(&self) -> Tuple { self.middle.tuple.reverse() }
    pub(crate) fn socket(&self) -> &TcpStream { &self.stream }
    pub(crate) fn interest(&self) -> Interest {
        if self.middle.conn.is_closed() { return Interest { read: false, write: false } }
        if !self.connected { return Interest { read: false, write: true } }
        Interest {
            read: !self.origin_eof && self.middle.conn.send_available() != 0,
            write: !self.origin_write_closed && self.middle.conn.readable() != 0,
        }
    }
    pub(crate) fn on_packet(&mut self, p: &Packet) -> io::Result<Packets> {
        let mut out = Vec::new();
        self.middle.receive(p, &mut out)?;
        self.finish_write(&mut out)?;
        Ok(out)
    }
    pub(crate) fn next_deadline(&self) -> Option<Instant> { self.middle.deadline() }
    pub(crate) fn finished(&self) -> bool { self.middle.conn.is_closed() }
    pub(crate) fn tick(&mut self, now: Instant) -> io::Result<Packets> {
        let mut out = Vec::new();
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
                Err(_) => self.middle.abort(out)?,
            }
        }
        Ok(())
    }
    pub(crate) fn on_socket_ready(
        &mut self, readable: bool, writable: bool, scratch: &mut [u8],
    ) -> io::Result<Packets> {
        let mut out = Vec::new();
        if self.middle.conn.is_closed() { return Ok(out) }
        if self.stream.take_error()?.is_some() {
            self.middle.abort(&mut out)?;
            return Ok(out)
        }
        if !self.connected {
            if !writable { return Ok(out) }
            if self.stream.peer_addr().is_err() {
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
                    Ok(0) => { self.middle.abort(&mut out)?; return Ok(out) }
                    Ok(n) => budget -= n,
                    Err(e) if e.kind() == io::ErrorKind::WouldBlock => break,
                    Err(e) if e.kind() == io::ErrorKind::Interrupted => continue,
                    Err(_) => { self.middle.abort(&mut out)?; return Ok(out) }
                }
            }
            let packets = self.middle.conn.take_outgoing();
            self.middle.emit(packets, &mut out)?;
        }
        self.finish_write(&mut out)?;
        if readable && !self.origin_eof && !self.middle.conn.is_closed() {
            let mut budget = TURN_BYTES;
            while budget != 0 {
                let n = self.middle.conn.send_available().min(budget).min(scratch.len());
                if n == 0 { break }
                match self.stream.read(&mut scratch[..n]) {
                    Ok(0) => {
                        self.origin_eof = true;
                        self.middle.close(&mut out)?;
                        break
                    }
                    Ok(n) => {
                        let (accepted, packets) = self.middle.conn.write(&scratch[..n]);
                        assert_eq!(accepted, n);
                        self.middle.emit(packets, &mut out)?;
                        budget -= n;
                    }
                    Err(e) if e.kind() == io::ErrorKind::WouldBlock => break,
                    Err(e) if e.kind() == io::ErrorKind::Interrupted => continue,
                    Err(_) => { self.middle.abort(&mut out)?; break }
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
    fn exchange_client_to_server(server: &mut ServerFlow, packets: Packets) {
        for p in packets { server.on_packet(&parse(&p)).unwrap(); }
    }
    #[test]
    fn dual_leg_wire_and_real_nonblocking_origin_bidirectional() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let SocketAddr::V4(dst) = listener.local_addr().unwrap() else { panic!() };
        let tuple = Tuple { src:"10.66.0.2:40201".parse().unwrap(), dst };
        let mut app = Endpoint::new(tuple, 1280, CongestionKind::Cubic).unwrap();
        let mut syn = Vec::new();
        app.open(&mut syn).unwrap();
        let (mut client, out) = ClientFlow::open(&parse(&syn[0]), 1280, 1100).unwrap();
        let (mut server, reverse_syn) = ServerFlow::open(&parse(&out.tunnel[0]), 1100).unwrap();
        let (mut origin, _) = listener.accept().unwrap();
        origin.set_read_timeout(Some(Duration::from_secs(2))).unwrap();
        let mut scratch = [0; 65536];
        server.on_socket_ready(false, true, &mut scratch).unwrap();

        let mut ack = Vec::new();
        for p in out.local { app.receive(&parse(&p), &mut ack).unwrap(); }
        for p in ack { client.on_local(&parse(&p)).unwrap(); }
        for p in reverse_syn {
            let out = client.on_middle(&parse(&p)).unwrap();
            exchange_client_to_server(&mut server, out.tunnel);
        }

        let request = b"real origin request / first payload";
        let (n, data) = app.conn.write(request);
        assert_eq!(n, request.len());
        let mut wire = Vec::new();
        app.emit(data, &mut wire).unwrap();
        for p in wire {
            let out = client.on_local(&parse(&p)).unwrap();
            exchange_client_to_server(&mut server, out.tunnel);
        }
        assert!(server.interest().write);
        let response = server.on_socket_ready(false, true, &mut scratch).unwrap();
        for p in response { client.on_middle(&parse(&p)).unwrap(); }
        let mut got = vec![0; request.len()];
        origin.read_exact(&mut got).unwrap();
        assert_eq!(got, request);

        let reply = b"actual kernel origin response";
        origin.write_all(reply).unwrap();
        origin.shutdown(Shutdown::Write).unwrap();
        let response = server.on_socket_ready(true, false, &mut scratch).unwrap();
        let mut client_ack = Vec::new();
        for p in response {
            let out = client.on_middle(&parse(&p)).unwrap();
            exchange_client_to_server(&mut server, out.tunnel);
            for p in out.local { app.receive(&parse(&p), &mut client_ack).unwrap(); }
        }
        for p in client_ack {
            let out = client.on_local(&parse(&p)).unwrap();
            exchange_client_to_server(&mut server, out.tunnel);
        }
        let mut got = vec![0; reply.len()];
        assert_eq!(app.conn.read(&mut got), reply.len());
        assert_eq!(got, reply);
        // The app sees the origin's genuine half-close; the upstream leg
        // remains writable until the app itself closes.
        assert!(app.conn.fin_received());
        assert!(!app.conn.abnormal_end());
        let close = app.conn.close();
        assert!(close.iter().any(|p| super::super::pktkit::vtcp::Segment::parse(p)
            .unwrap().has_flag(flags::FIN)));
    }
}
