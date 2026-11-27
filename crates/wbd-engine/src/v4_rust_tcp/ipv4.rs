//! Real inner IPv4/TCP, not the TCP-like outer carrier.
use std::{io, net::{Ipv4Addr, SocketAddrV4}};
use super::pktkit::vtcp::{Segment, flags};
use super::pktkit::vtcp::ecn::IpEcn;

#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash, Ord, PartialOrd)]
pub(crate) struct Tuple {
    pub(crate) src: SocketAddrV4,
    pub(crate) dst: SocketAddrV4,
}

impl Tuple {
    pub(crate) fn reverse(self) -> Self { Self { src: self.dst, dst: self.src } }
}

pub(crate) struct Packet {
    pub(crate) tuple: Tuple,
    pub(crate) segment: Segment,
    pub(crate) ecn: IpEcn,
}

fn invalid() -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, "invalid inner IPv4/TCP")
}
fn sum(bytes: &[u8]) -> u64 {
    let mut words = bytes.chunks_exact(2);
    let n: u64 = words.by_ref().map(|w| u16::from_be_bytes([w[0], w[1]]) as u64).sum();
    n + words.remainder().first().map_or(0, |b| (*b as u64) << 8)
}
fn checksum(mut n: u64) -> u16 {
    while n >> 16 != 0 { n = (n & 0xffff) + (n >> 16); }
    !(n as u16)
}
fn tcp_sum(src: Ipv4Addr, dst: Ipv4Addr, tcp: &[u8]) -> u64 {
    sum(&src.octets()) + sum(&dst.octets()) + 6 + tcp.len() as u64 + sum(tcp)
}

impl Packet {
    /// Non-TCP IPv4 stays on the existing business path. A malformed TCP
    /// datagram is not a flow event. IP fragmentation is handled outside
    /// this endpoint; middle TCP sends DF within its derived inner budget.
    pub(crate) fn parse(ip: &[u8]) -> io::Result<Option<Self>> {
        Self::parse_reuse(ip,&mut Segment::default())
    }
    pub(crate) fn parse_reuse(ip:&[u8],scratch:&mut Segment)->io::Result<Option<Self>>{
        if ip.len() < 20 || ip[0] >> 4 != 4 { return Err(invalid()) }
        if ip[9] != 6 { return Ok(None) }
        let ihl = (ip[0] & 15) as usize * 4;
        if ihl < 20 || ip.len() < ihl + 20 ||
            u16::from_be_bytes([ip[2], ip[3]]) as usize != ip.len() ||
            u16::from_be_bytes([ip[6], ip[7]]) & 0xbfff != 0 ||
            checksum(sum(&ip[..ihl])) != 0 {
            return Err(invalid())
        }
        let src = Ipv4Addr::new(ip[12], ip[13], ip[14], ip[15]);
        let dst = Ipv4Addr::new(ip[16], ip[17], ip[18], ip[19]);
        let tcp = &ip[ihl..];
        if checksum(tcp_sum(src, dst, tcp)) != 0 { return Err(invalid()) }
        scratch.parse_into(tcp)?;
        if scratch.src_port==0||scratch.dst_port==0{return Err(invalid())}
        let segment=std::mem::take(scratch);
        Ok(Some(Self {
            tuple: Tuple { src: SocketAddrV4::new(src, segment.src_port),
                           dst: SocketAddrV4::new(dst, segment.dst_port) },
            segment,
            ecn: IpEcn::from_bits(ip[1]),
        }))
    }
    pub(crate) fn initial_syn(&self) -> bool {
        self.segment.flags & (flags::SYN | flags::ACK | flags::RST | flags::FIN) == flags::SYN
    }
}

/// Emit a complete IPv4 datagram, including the real TCP pseudoheader
/// checksum. The caller supplies the Rust-derived inner MTU for this leg.
pub(crate) fn encode(tuple: Tuple, mut tcp: Vec<u8>, ecn: IpEcn, mtu: u16) -> io::Result<Vec<u8>> {
    let len = 20 + tcp.len();
    if tcp.len() < 20 || len > mtu as usize { return Err(invalid()) }
    let src = *tuple.src.ip();
    let dst = *tuple.dst.ip();
    tcp[16..18].fill(0);
    let check = checksum(tcp_sum(src, dst, &tcp));
    tcp[16..18].copy_from_slice(&check.to_be_bytes());
    let tcp_len=tcp.len();tcp.resize(len,0);tcp.copy_within(..tcp_len,20);tcp[..20].fill(0);
    let mut ip=tcp;
    ip[0] = 0x45;
    ip[1] = ecn.0;
    ip[2..4].copy_from_slice(&(len as u16).to_be_bytes());
    ip[6] = 0x40; // DF; ID zero for an atomic datagram.
    ip[8] = 64;
    ip[9] = 6;
    ip[12..16].copy_from_slice(&src.octets());
    ip[16..20].copy_from_slice(&dst.octets());
    let check = checksum(sum(&ip[..20]));
    ip[10..12].copy_from_slice(&check.to_be_bytes());
    Ok(ip)
}

pub(crate) fn reset_for(packet: &Packet, mtu: u16) -> io::Result<Vec<u8>> {
    let incoming = &packet.segment;
    let acknowledged = incoming.has_flag(flags::ACK);
    let seg = Segment {
        src_port: incoming.dst_port, dst_port: incoming.src_port,
        seq: if acknowledged { incoming.ack } else { 0 },
        ack: if acknowledged { 0 } else { incoming.seq.wrapping_add(incoming.seg_len()) },
        flags: flags::RST | if acknowledged { 0 } else { flags::ACK },
        ..Segment::default()
    };
    encode(packet.tuple.reverse(), seg.marshal(), IpEcn::NOT_ECT, mtu)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn real_tcp_checksum_odd_payload_ecn_mtu_and_corruption() {
        let tuple = Tuple { src:"10.66.0.2:43210".parse().unwrap(),
                            dst:"192.0.2.1:443".parse().unwrap() };
        let tcp = Segment { src_port:43210, dst_port:443, seq:9, ack:3,
            flags:flags::ACK, payload:vec![1,2,3], ..Default::default() }.marshal();
        assert!(encode(tuple,tcp.clone(),IpEcn::CE,42).is_err());
        let mut ip=encode(tuple,tcp,IpEcn::CE,43).unwrap();
        let parsed=Packet::parse(&ip).unwrap().unwrap();
        assert_eq!(parsed.tuple,tuple);
        assert_eq!(parsed.segment.payload,[1,2,3]);
        assert_eq!(parsed.ecn,IpEcn::CE);
        *ip.last_mut().unwrap() ^= 1;
        assert!(Packet::parse(&ip).is_err());
    }
}
