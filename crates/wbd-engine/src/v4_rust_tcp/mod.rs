//! M0 dual native TCP: shared endpoints and native owner integration.
#![allow(dead_code)]
mod pktkit;
mod ipv4;
mod flow;
#[cfg(target_os="linux")]
mod linux_socket;
#[cfg(target_os="linux")]
pub(crate) mod linux_owner;
#[cfg(target_os="linux")]
pub(crate) use flow::ClientOutput;

use pktkit::vtcp::Conn;
use pktkit::vtcp::ecn::IpEcn;

pub(crate) struct Segments {
    pub(crate) packets: Vec<Vec<u8>>,
    pub(crate) ecn: Vec<IpEcn>,
}

impl Segments {
    fn from_conn(conn: &Conn, packets: Vec<Vec<u8>>) -> Self {
        let ecn = conn.ecn_marks(&packets);
        Self { packets, ecn }
    }
}

/// Transfer only bytes the destination TCP send buffer actually accepts.
/// The caller delivers both outputs; the receiving ring is consumed directly.
/// No extra per-flow relay queue, thread or tunnel retransmission layer.
pub(crate) fn transfer(
    from: &mut Conn,
    to: &mut Conn,
    limit: usize,
) -> (usize, Segments, Segments) {
    let limit = limit.min(to.relay_send_available());
    let mut to_packets = Vec::new();
    let n = from.read_to(limit, |bytes| {
        let (n, packets) = to.write(bytes);
        to_packets = packets;
        Ok(n)
    }).expect("TCP buffer write is infallible");
    let from_packets = from.take_outgoing();
    (n, Segments::from_conn(from, from_packets), Segments::from_conn(to, to_packets))
}

#[cfg(test)]
mod tests {
    use super::*;
    use super::pktkit::vtcp::{ConnConfig, Segment};

    fn endpoint(local: u16, remote: u16) -> Conn {
        Conn::new(ConnConfig {
            local_port: local,
            remote_port: remote,
            pacing: false,
            nodelay: true,
            autotune: false,
            ..ConnConfig::default()
        })
    }

    fn linked() -> (Conn, Conn) {
        let mut a = endpoint(40000, 80);
        let mut b = endpoint(80, 40000);
        let syn = a.connect();
        let synack = b.accept_syn(&Segment::parse(&syn[0]).unwrap());
        let ack = a.handle_segment(&Segment::parse(&synack[0]).unwrap());
        for p in ack {
            b.handle_segment(&Segment::parse(&p).unwrap());
        }
        assert!(a.is_established() && b.is_established());
        (a, b)
    }

    #[test]
    fn relay_keeps_unaccepted_bytes_then_delivers_exact_payload() {
        let (mut source, mut ingress) = linked();
        let payload = [0x59; 128];
        let (n, packets) = source.write(&payload);
        assert_eq!(n, payload.len());
        for p in packets {
            ingress.handle_segment(&Segment::parse(&p).unwrap());
        }
        assert_eq!(ingress.readable(), payload.len());
        let mut blocked = endpoint(40001, 80);
        assert_eq!(transfer(&mut ingress, &mut blocked, 128).0, 0);
        assert_eq!(ingress.readable(), payload.len());
        let (mut egress, mut sink) = linked();
        let (n, up, down) = transfer(&mut ingress, &mut egress, 128);
        assert_eq!(n, payload.len());
        assert_eq!(up.packets.len(), up.ecn.len());
        assert_eq!(down.packets.len(), down.ecn.len());
        assert_eq!(ingress.readable(), 0);
        for p in down.packets {
            sink.handle_segment(&Segment::parse(&p).unwrap());
        }
        let mut got = [0; 128];
        assert_eq!(sink.read(&mut got), payload.len());
        assert_eq!(got, payload);
    }
}
