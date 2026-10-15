//! Bounded, strict byte-only inbound IPv4/TCP-like steady DATA parser.
//!
//! This parser consumes one *complete* captured IPv4 datagram and returns a
//! borrowed **UNAUTHENTICATED** ciphertext region. It neither opens AEAD,
//! assigns PN, acknowledges a record, nor delivers business payload. M0/M3
//! must authenticate/replay-check it before exposing any bytes to the app.
//! There is no TCP stream reconstruction, raw OS socket, packet coalescing,
//! kernel checksum-offload accommodation, malloc or unsafe code in this module.
//!
//! Outbound compatibility: crate::ipv4_tcp, pinned historical Go packet.go
//! wobuzhidao@a7a82db31fe736ffedee330795a3234d358f1984.
//! Expected tuple, persona and options MUST originate in trusted cold state.
use crate::ipv4_tcp::{Ipv4Tuple, PacketPersona, TCP_DATA_FLAGS};

const IPV4_HEADER_LEN: usize = 20;
const TCP_HEADER_LEN: usize = 20;
const MAX_PACKET_LEN: usize = u16::MAX as usize;
const TCP_PROTO: u8 = 6;
const DF_ONLY: u16 = 0x4000;

#[derive(Clone, Copy, Debug)]
pub struct TrustedRx<'a> {
    pub tuple: Ipv4Tuple<'a>,
    pub persona: PacketPersona,
    pub mtu: usize,
    /// None means *no* TCP options were negotiated for steady DATA.
    /// Some bytes MUST match the authenticated session's exact options.
    /// A timestamp value may change each packet only if the caller explicitly
    /// updates the authenticated session snapshot for that packet.
    pub authenticated_options: Option<&'a [u8]>,
}

/// Result intentionally has no authenticated or delivered bit; 'ciphertext'
/// is untrusted *even after* tuple, header and checksum verification. A valid
/// ones-complement checksum is NOT proof of cryptographic authenticity.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct UnauthenticatedData<'a> {
    pub ciphertext: &'a [u8],
    pub seq32: u32,
    pub presentation_ack32: u32,
    pub presentation_window: u16,
    pub ip_id: u16,
    pub ip_header_len: usize,
    pub tcp_header_len: usize,
}
impl UnauthenticatedData<'_> {
    pub fn extend_seq_against(&self, trusted_anchor: u64) -> Result<u64, SeqExtendError> {
        extend_seq32(trusted_anchor, self.seq32)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RxError {
    InvalidTrustedTuple,
    InvalidTrustedOptions,
    TooShort,
    TooLong,
    ExceedsMtu { actual: usize, mtu: usize },
    WrongVersionOrIhl,
    WrongIpHeader,
    FragmentedOrUnexpectedFlags,
    TotalLengthMismatch,
    WrongTuple,
    WrongPersona,
    WrongProtocol,
    IpChecksum,
    InvalidTcpHeader,
    UnsupportedOptions,
    InvalidDataFlags,
    TcpChecksum,
    EmptyData,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SeqExtendError {
    /// wire32 is exactly 2^31 from the trusted reference modulo 2^32;
    /// there are two equidistant 64-bit candidates. Do not choose either.
    HalfSpaceAmbiguous,
    /// The nearest candidate would fall outside 0..=u64::MAX.
    OutsideU64,
}

/// Extend a TCP appearance seq32 to a *candidate* near a trusted u64 anchor.
/// Never update an owner's trusted anchor here; caller must first authenticate
/// AEAD+PN and apply its own replay, discontinuity and delivery decisions.
/// The chosen distance is strictly less than 2^31. Exact half-space fails.
pub fn extend_seq32(trusted_anchor: u64, seq32: u32) -> Result<u64, SeqExtendError> {
    let wrapped_delta = seq32.wrapping_sub(trusted_anchor as u32);
    if wrapped_delta == 0x8000_0000 {
        return Err(SeqExtendError::HalfSpaceAmbiguous);
    }
    if wrapped_delta < 0x8000_0000 {
        trusted_anchor.checked_add(u64::from(wrapped_delta))
            .ok_or(SeqExtendError::OutsideU64)
    } else {
        let backwards = u64::from((!wrapped_delta).wrapping_add(1));
        trusted_anchor.checked_sub(backwards).ok_or(SeqExtendError::OutsideU64)
    }
}

fn plausible_unicast(ip: &[u8]) -> bool {
    ip.len() == 4 && ip != [0, 0, 0, 0] && ip != [255, 255, 255, 255]
        && ip[0] != 0 && ip[0] < 224
}
fn valid_options(opts: &[u8]) -> bool {
    if opts.len() > 40 || opts.len() % 4 != 0 { return false; }
    let mut i = 0;
    let mut timestamp = false;
    while i < opts.len() {
        match opts[i] {
            0 => return opts[i..].iter().all(|&b| b == 0),
            1 => i += 1,
            8 if !timestamp && opts.len() - i >= 10 && opts[i + 1] == 10 => {
                timestamp = true;
                i += 10;
            }
            _ => return false,
        }
    }
    true
}
fn be16(b: &[u8]) -> u16 { u16::from_be_bytes([b[0], b[1]]) }
fn be32(b: &[u8]) -> u32 { u32::from_be_bytes([b[0], b[1], b[2], b[3]]) }

/// Independent receive-side Internet checksum implementation: byte-wise
/// carry-folding, rather than reusing the outbound word-chunk checksum.
/// A complete checksum-covered byte slice must fold to 0.
fn add_bytes(mut acc: u64, data: &[u8]) -> u64 {
    for (index, &byte) in data.iter().enumerate() {
        acc += u64::from(byte) << if index & 1 == 0 { 8 } else { 0 };
    }
    acc
}
fn checksum_is_valid(mut acc: u64) -> bool {
    while acc >> 16 != 0 { acc = (acc & 0xffff) + (acc >> 16); }
    acc == 0xffff
}

/// Parse a SINGLE full raw IPv4 packet, with no length-prefix, short-packet
/// buffering or concatenated TCP segments. Caller must supply precisely one
/// kernel-delimited packet; any padded/trailing bytes are rejected.
pub fn parse_data_packet<'a>(
    packet: &'a [u8],
    trusted: TrustedRx<'_>,
) -> Result<UnauthenticatedData<'a>, RxError> {
    let tuple = trusted.tuple;
    if !plausible_unicast(tuple.src_ip) || !plausible_unicast(tuple.dst_ip)
        || tuple.src_port == 0 || tuple.dst_port == 0 {
        return Err(RxError::InvalidTrustedTuple);
    }
    let trusted_opts = trusted.authenticated_options.unwrap_or(&[]);
    if !valid_options(trusted_opts) { return Err(RxError::InvalidTrustedOptions); }
    if packet.len() > MAX_PACKET_LEN { return Err(RxError::TooLong); }
    if packet.len() > trusted.mtu {
        return Err(RxError::ExceedsMtu {actual:packet.len(),mtu:trusted.mtu});
    }
    if packet.len() < IPV4_HEADER_LEN + TCP_HEADER_LEN {
        return Err(RxError::TooShort);
    }
    if packet[0] != 0x45 { return Err(RxError::WrongVersionOrIhl); }
    // No unexpected DSCP/ECN: compatible with exactly the existing writer.
    if packet[1] != 0 { return Err(RxError::WrongIpHeader); }
    if usize::from(be16(&packet[2..4])) != packet.len() {
        return Err(RxError::TotalLengthMismatch);
    }
    // Old carrier transmits unfragmented IPv4 packets with DF set; reject
    // reserved bit, MF flag and every nonzero fragment offset.
    if be16(&packet[6..8]) != DF_ONLY {
        return Err(RxError::FragmentedOrUnexpectedFlags);
    }
    if packet[9] != TCP_PROTO { return Err(RxError::WrongProtocol); }
    if packet[8] != trusted.persona.ttl() { return Err(RxError::WrongPersona); }
    if &packet[12..16] != tuple.src_ip || &packet[16..20] != tuple.dst_ip {
        return Err(RxError::WrongTuple);
    }
    if !checksum_is_valid(add_bytes(0, &packet[..IPV4_HEADER_LEN])) {
        return Err(RxError::IpChecksum);
    }
    let tcp = &packet[IPV4_HEADER_LEN..];
    if be16(&tcp[0..2]) != tuple.src_port || be16(&tcp[2..4]) != tuple.dst_port {
        return Err(RxError::WrongTuple);
    }
    // TCP offset in 32-bit words; reject all reserved bits and NS on DATA.
    if tcp[12] & 0x0f != 0 { return Err(RxError::InvalidTcpHeader); }
    let hdr_len = usize::from(tcp[12] >> 4) * 4;
    if hdr_len < TCP_HEADER_LEN || hdr_len > TCP_HEADER_LEN + 40
        || hdr_len > tcp.len() { return Err(RxError::InvalidTcpHeader); }
    if tcp[13] != TCP_DATA_FLAGS { return Err(RxError::InvalidDataFlags); }
    if tcp[18] != 0 || tcp[19] != 0 {
        return Err(RxError::InvalidTcpHeader); // urgent pointer on DATA
    }
    let opts = &tcp[TCP_HEADER_LEN..hdr_len];
    if !valid_options(opts) || opts != trusted_opts {
        return Err(RxError::UnsupportedOptions);
    }
    if hdr_len == tcp.len() { return Err(RxError::EmptyData); }
    // TCP pseudoheader: src/dst, zero, protocol=6, 16-bit TCP byte length.
    // A single add_bytes() per independent even-length segment preserves the
    // odd-tail alignment inside the TCP segment, even with odd ciphertext.
    let mut sum = add_bytes(0, &packet[12..20]);
    sum += u64::from(TCP_PROTO) + tcp.len() as u64;
    sum = add_bytes(sum, tcp);
    if !checksum_is_valid(sum) { return Err(RxError::TcpChecksum); }
    Ok(UnauthenticatedData {
        ciphertext: &tcp[hdr_len..],
        seq32: be32(&tcp[4..8]),
        presentation_ack32: be32(&tcp[8..12]),
        presentation_window: be16(&tcp[14..16]),
        ip_id: be16(&packet[4..6]),
        ip_header_len: IPV4_HEADER_LEN,
        tcp_header_len: hdr_len,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ipv4_tcp::{build, Presentation};
    use wbd_types::{BufferKey,LaneKey,RecordPn,SeqOffset,TunnelKey};
    use wbd_types::buffer_contract::{BufferOrigin, FrozenMetadata, FrozenRecordHandle};

    #[derive(Clone)]
    struct Frozen {bytes: Vec<u8>, seq:u64}
    impl FrozenRecordHandle for Frozen {
        fn origin(&self) -> BufferOrigin {
            BufferOrigin{owner_arena:7,key:BufferKey{slot:1,generation:1}}
        }
        fn metadata(&self) -> FrozenMetadata {
            FrozenMetadata{lane:LaneKey{tunnel:TunnelKey{slot:1,generation:1},slot:2,generation:1},
                seq:SeqOffset(self.seq),pn:RecordPn(99),carrier_snapshot:8}
        }
        fn bytes(&self) -> &[u8] {&self.bytes}
    }
    fn tuple<'a>() -> Ipv4Tuple<'a> {
        Ipv4Tuple{src_ip:&[192,0,2,40],dst_ip:&[198,51,100,40],
            src_port:43000,dst_port:443}
    }
    fn trusted<'a>(opts: Option<&'a [u8]>, mtu:usize) -> TrustedRx<'a> {
        TrustedRx{tuple:tuple(),persona:PacketPersona::Legacy,mtu,
            authenticated_options:opts}
    }
    fn wire(payload: &[u8], seq:u64, opts:Option<&[u8]>) -> Vec<u8> {
        let mut scratch=vec![0x88;4096];
        build(tuple(),Presentation{
            ack32:200,advertised_window:65535,ip_id:123,
            persona:PacketPersona::Legacy},
            &Frozen{bytes:payload.to_vec(),seq},opts,4096,&mut scratch)
            .unwrap().to_vec()
    }
    fn raw_hex(s:&str)->Vec<u8> {
        (0..s.len()).step_by(2).map(|i|u8::from_str_radix(&s[i..i+2],16).unwrap()).collect()
    }
    fn independent_sum(data:&[u8])->u16 {
        let mut sum=0u64;
        for (i,b) in data.iter().enumerate() {
            sum += u64::from(*b) << if i%2==0 {8} else {0};
        }
        while sum>>16!=0 {sum=(sum&0xffff)+(sum>>16);}
        !(sum as u16)
    }
    fn checksums(packet:&[u8]){
        assert_eq!(independent_sum(&packet[..20]),0);
        let mut pseudo=Vec::from(&packet[12..20]);
        pseudo.extend_from_slice(&[0,6]);
        pseudo.extend_from_slice(&((packet.len()-20) as u16).to_be_bytes());
        pseudo.extend_from_slice(&packet[20..]);
        assert_eq!(independent_sum(&pseudo),0);
    }

    #[test]
    fn r1_rx_ipv4_tcp_round_trip_real_tx_bytes_even_odd_and_immutable() {
        for body in [b"abc".as_slice(), b"abcd", &[0,255,0,1,2]] {
            let pkt=wire(body,100,None);
            let original=pkt.clone();
            checksums(&pkt);
            let data=parse_data_packet(&pkt,trusted(None,pkt.len())).unwrap();
            assert_eq!(data.ciphertext,body);
            assert_eq!(data.seq32,100);
            assert_eq!(data.presentation_ack32,200);
            assert_eq!(data.presentation_window,65535);
            assert_eq!(data.ip_id,123);
            assert_eq!((data.ip_header_len,data.tcp_header_len),(20,20));
            assert_eq!(pkt,original);
        }
    }
    #[test]
    fn r1_rx_ipv4_tcp_pinned_old_go_packet_golden() {
        // Go packet.go pinned 6ac1f9...: fixed legacy IPID21/ACK200/TCP window1024.
        let golden=raw_hex("4500002e0015400040064e31c0000228c6336428a7f801bb00000064000000c850180400cc2900007265636f7264");
        checksums(&golden);
        let result=parse_data_packet(&golden,trusted(None,46)).unwrap();
        assert_eq!(result.ciphertext,b"record");
        assert_eq!(result.ip_id,21);
        assert_eq!(result.presentation_window,1024);
        assert_eq!(result.extend_seq_against(100),Ok(100));
    }
    #[test]
    fn r1_rx_ipv4_tcp_mtu_exact_minus_one_and_overlong() {
        let pkt=wire(b"record",100,None);
        assert_eq!(pkt.len(),46);
        assert_eq!(parse_data_packet(&pkt,trusted(None,45)),
            Err(RxError::ExceedsMtu{actual:46,mtu:45}));
        assert!(parse_data_packet(&pkt,trusted(None,46)).is_ok());
        let too_long=vec![0u8;65536];
        assert_eq!(parse_data_packet(&too_long,trusted(None,70000)),Err(RxError::TooLong));
    }
    #[test]
    fn r1_rx_ipv4_tcp_fail_closed_version_ihl_fragment_length_and_trailing() {
        let original=wire(b"record",100,None);
        for (offset,newval,expected) in [
            (0,0x65,RxError::WrongVersionOrIhl),
            (0,0x46,RxError::WrongVersionOrIhl),
            (1,0x01,RxError::WrongIpHeader),
            (6,0x20,RxError::FragmentedOrUnexpectedFlags),
            (6,0x60,RxError::FragmentedOrUnexpectedFlags),
            (7,0x01,RxError::FragmentedOrUnexpectedFlags),
            (9,0x11,RxError::WrongProtocol),
            (2,0x01,RxError::TotalLengthMismatch),
        ] {
            let mut bad=original.clone();bad[offset]=newval;
            assert_eq!(parse_data_packet(&bad,trusted(None,1500)),Err(expected), "offset {offset}");
        }
        let mut padded=original.clone();padded.push(0);
        assert_eq!(parse_data_packet(&padded,trusted(None,1500)),
            Err(RxError::TotalLengthMismatch));
        assert_eq!(parse_data_packet(&original[..45],trusted(None,1500)),
            Err(RxError::TotalLengthMismatch));
        for n in 0..40 {
            assert!(parse_data_packet(&original[..n],trusted(None,1500)).is_err(),"n={n}");
        }
    }
    #[test]
    fn r1_rx_ipv4_tcp_data_offset_flags_truncation_and_zero_payload() {
        let original=wire(b"record",100,None);
        for (off,value,expected) in [
            (32,0x40,RxError::InvalidTcpHeader),
            (32,0x60,RxError::UnsupportedOptions),
            (32,0xf0,RxError::InvalidTcpHeader),
            (32,0x51,RxError::InvalidTcpHeader),
            (33,0x12,RxError::InvalidDataFlags),
            (33,0x10,RxError::InvalidDataFlags),
            (33,0x19,RxError::InvalidDataFlags),
            (38,0x00,RxError::InvalidTcpHeader),
        ] {
            let mut bad=original.clone();bad[off]=value;
            // urgent pointer original 0, so set nonzero for that case.
            if off==38 {bad[38]=1;}
            assert_eq!(parse_data_packet(&bad,trusted(None,1500)),Err(expected), "off {off}");
        }
        let mut empty=original[..40].to_vec();empty[2..4].copy_from_slice(&40u16.to_be_bytes());
        assert_eq!(parse_data_packet(&empty,trusted(None,1500)),Err(RxError::EmptyData));
    }
    #[test]
    fn r1_rx_ipv4_tcp_wrong_ip_port_ttl_and_independent_checksums() {
        let original=wire(b"record!",100,None);
        let cases=[
            (12,0u8,RxError::WrongTuple),
            (16,0u8,RxError::WrongTuple),
            (20,0u8,RxError::WrongTuple),
            (22,0u8,RxError::WrongTuple),
            (8,128u8,RxError::WrongPersona),
            (10,0u8,RxError::IpChecksum),
            (36,0u8,RxError::TcpChecksum),
            (40,0u8,RxError::TcpChecksum),
        ];
        for (off,val,expected) in cases {
            let mut bad=original.clone();bad[off]=val;
            // If a test value accidentally already matches, flip one bit.
            if bad[off]==original[off] {bad[off]^=0x80;}
            assert_eq!(parse_data_packet(&bad,trusted(None,1500)),Err(expected),"off={off}");
        }
        let mut t=tuple();t.src_ip=&[0u8;16];
        assert_eq!(parse_data_packet(&original,TrustedRx{tuple:t,..trusted(None,1500)}),
            Err(RxError::InvalidTrustedTuple));
    }
    #[test]
    fn r1_rx_ipv4_tcp_options_require_exact_authenticated_snapshot() {
        let options=[1,1,8,10,0,0,0,1,0,0,0,2,0,0,0,0];
        let pkt=wire(b"odd",0x1_0000_0001,Some(&options));
        checksums(&pkt);
        assert_eq!(pkt[32]>>4,9);
        assert_eq!(parse_data_packet(&pkt,trusted(None,1500)),Err(RxError::UnsupportedOptions));
        let parsed=parse_data_packet(&pkt,trusted(Some(&options),1500)).unwrap();
        assert_eq!(parsed.ciphertext,b"odd");
        assert_eq!(parsed.tcp_header_len,36);
        let mut wrong=options;wrong[5]^=1;
        assert_eq!(parse_data_packet(&pkt,trusted(Some(&wrong),1500)),
            Err(RxError::UnsupportedOptions));
        assert_eq!(parse_data_packet(&pkt,trusted(Some(&[1u8;3]),1500)),
            Err(RxError::InvalidTrustedOptions));
        let mut tx=wire(b"record",100,None);
        tx[32]=0x60;
        assert_eq!(parse_data_packet(&tx,trusted(None,1500)),
            Err(RxError::UnsupportedOptions));
    }
    #[test]
    fn r1_rx_ipv4_tcp_seq32_wrap_nearest_and_halfspace_fail_closed() {
        let p=wire(b"packet",0x2_0000_0001,None);
        let parsed=parse_data_packet(&p,trusted(None,1500)).unwrap();
        assert_eq!(parsed.seq32,1);
        assert_eq!(parsed.extend_seq_against(0x1_ffff_fffe),Ok(0x2_0000_0001));
        assert_eq!(extend_seq32(0x2_0000_0001,0xffff_fffe),Ok(0x1_ffff_fffe));
        assert_eq!(extend_seq32(0x1_ffff_fffe,0xffff_fffe),Ok(0x1_ffff_fffe));
        assert_eq!(extend_seq32(0,0x8000_0000),Err(SeqExtendError::HalfSpaceAmbiguous));
        assert_eq!(extend_seq32(0x1_0000_0000,0x8000_0000),Err(SeqExtendError::HalfSpaceAmbiguous));
        assert_eq!(extend_seq32(0,0xffff_ffff),Err(SeqExtendError::OutsideU64));
        assert_eq!(extend_seq32(u64::MAX,0),Err(SeqExtendError::OutsideU64));
    }
    #[test]
    fn r1_rx_ipv4_tcp_unrelated_bad_packet_cannot_block_next_valid() {
        let good=wire(b"second-valid",101,None);
        let mut unrelated=wire(b"noise",88,None);
        unrelated[12]=203;
        assert_eq!(parse_data_packet(&unrelated,trusted(None,1500)),Err(RxError::WrongTuple));
        // Independent parser invocation, no stream/HOL buffer or stale anchor.
        let parsed=parse_data_packet(&good,trusted(None,1500)).unwrap();
        assert_eq!(parsed.ciphertext,b"second-valid");
        assert_eq!(parsed.extend_seq_against(101),Ok(101));
    }
    #[test]
    fn r1_rx_ipv4_tcp_never_confuses_checksum_with_aead_authentication() {
        let arbitrary=b"not a sealed/authenticated record";
        let pkt=wire(arbitrary,999,None);
        // An attacker can build valid IP/TCP checksums too. Parser only
        // returns an untrusted slice and provides no business delivery API.
        let untrusted=parse_data_packet(&pkt,trusted(None,1500)).unwrap();
        assert_eq!(untrusted.ciphertext,arbitrary);
        assert_eq!(untrusted.seq32,999);
    }
}
