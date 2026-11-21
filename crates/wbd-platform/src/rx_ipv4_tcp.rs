//! Bounded, strict byte-only inbound IPv4/TCP-like steady DATA parser.
//!
//! This parser consumes one *complete* captured IPv4 datagram and returns a
//! borrowed **UNAUTHENTICATED** ciphertext region. It neither opens AEAD,
//! assigns PN, acknowledges a record, nor delivers business payload. M0/M3
//! must authenticate/replay-check it before exposing any bytes to the app.
//! There is no TCP stream reconstruction, raw OS socket, packet coalescing,
//! kernel checksum-offload accommodation in the default public parser, malloc
//! or unsafe code. A48 adds a separate *Android-only* untrusted M3-pending
//! entrypoint for a real RAW TCP checksum incompatibility.
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
 
// TTL is a hop-local IPv4 lifetime value, NOT a reliable persona marker.
// All reachable positive TTL values are allowed; the unchanged tuple, both
// checksums, protected TLS association, AEAD and PN replay gates enforce
// authenticity. Routers/NAT can change TTL after the sender wrote its header.
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
    parse_data_packet_checked(packet,trusted,true)
}

/// A48: Android's real Bionic RAW TCP FD returned 113/114 packets with
/// valid destination tuple, IPv4 checksum, flags and lengths, but invalid
/// TCP checksums after the physical network path. The cold original-Go
/// FakeTCP path accepts these bytes, and only the original M3 can actually
/// authenticate a DATA record. This narrowly scoped second entrypoint
/// still enforces ALL other IPv4/TCP checks; its result is *untrusted*.
/// Linux and Windows builds cannot call it outside tests.
#[cfg(any(target_os="android",test))]
pub(crate) fn parse_data_packet_android_m3_pending<'a>(
    packet: &'a [u8],
    trusted: TrustedRx<'_>,
) -> Result<UnauthenticatedData<'a>, RxError> {
    parse_data_packet_checked(packet,trusted,false)
}

fn parse_data_packet_checked<'a>(
    packet: &'a [u8],
    trusted: TrustedRx<'_>,
    require_tcp_checksum:bool,
) -> Result<UnauthenticatedData<'a>, RxError> {
    let tuple = trusted.tuple;
    if !plausible_unicast(tuple.src_ip) || !plausible_unicast(tuple.dst_ip)
        || tuple.src_port == 0 || tuple.dst_port == 0 {
        return Err(RxError::InvalidTrustedTuple);
    }
    let trusted_opts = trusted.authenticated_options.unwrap_or(&[]);
    if require_tcp_checksum && !valid_options(trusted_opts) {
        return Err(RxError::InvalidTrustedOptions);
    }
    if packet.len() > MAX_PACKET_LEN { return Err(RxError::TooLong); }
    if packet.len() > trusted.mtu {
        return Err(RxError::ExceedsMtu {actual:packet.len(),mtu:trusted.mtu});
    }
    if packet.len() < IPV4_HEADER_LEN + TCP_HEADER_LEN {
        return Err(RxError::TooShort);
    }
    if packet[0] != 0x45 { return Err(RxError::WrongVersionOrIhl); }
    // No unexpected DSCP/ECN: compatible with exactly the existing writer.
    if require_tcp_checksum && packet[1] != 0 {
        return Err(RxError::WrongIpHeader);
    }
    if usize::from(be16(&packet[2..4])) != packet.len() {
        return Err(RxError::TotalLengthMismatch);
    }
    // Old carrier transmits unfragmented IPv4 packets with DF set; reject
    // reserved bit, MF flag and every nonzero fragment offset.
    let flags=be16(&packet[6..8]);
    if flags&0x3fff!=0 || (require_tcp_checksum && flags!=DF_ONLY) {
        return Err(RxError::FragmentedOrUnexpectedFlags);
    }
    if packet[9] != TCP_PROTO { return Err(RxError::WrongProtocol); }
    if packet[8] == 0 { return Err(RxError::WrongIpHeader); }
    if &packet[12..16] != tuple.src_ip || &packet[16..20] != tuple.dst_ip {
        return Err(RxError::WrongTuple);
    }
    if require_tcp_checksum &&
        !checksum_is_valid(add_bytes(0, &packet[..IPV4_HEADER_LEN])) {
        return Err(RxError::IpChecksum);
    }
    let tcp = &packet[IPV4_HEADER_LEN..];
    if be16(&tcp[0..2]) != tuple.src_port || be16(&tcp[2..4]) != tuple.dst_port {
        return Err(RxError::WrongTuple);
    }
    // TCP offset in 32-bit words; reject all reserved bits and NS on DATA.
    if require_tcp_checksum && tcp[12] & 0x0f != 0 {
        return Err(RxError::InvalidTcpHeader);
    }
    let hdr_len = usize::from(tcp[12] >> 4) * 4;
    if hdr_len < TCP_HEADER_LEN || hdr_len > TCP_HEADER_LEN + 40
        || hdr_len > tcp.len() { return Err(RxError::InvalidTcpHeader); }
    if tcp[13] != TCP_DATA_FLAGS { return Err(RxError::InvalidDataFlags); }
    if require_tcp_checksum && (tcp[18] != 0 || tcp[19] != 0) {
        return Err(RxError::InvalidTcpHeader);
    }
    if require_tcp_checksum {
        let opts = &tcp[TCP_HEADER_LEN..hdr_len];
        if !valid_options(opts) || opts != trusted_opts {
            return Err(RxError::UnsupportedOptions);
        }
    }
    if hdr_len == tcp.len() { return Err(RxError::EmptyData); }
    // Strict Linux/Windows must verify the full TCP pseudoheader checksum.
    // A49 Android M3-pending skips the O(ciphertext length) scan entirely;
    // the ORIGINAL M3 AEAD/PN/replay must still authenticate every record.
    if require_tcp_checksum {
        let mut sum = add_bytes(0, &packet[12..20]);
        sum += u64::from(TCP_PROTO) + tcp.len() as u64;
        sum = add_bytes(sum, tcp);
        if !checksum_is_valid(sum) {
            return Err(RxError::TcpChecksum);
        }
    }
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


/// A checksum/tuple-validated but UNAUTHENTICATED presentation ACK. It
/// never proves M3 DATA, refreshes Health or advances an application stream.
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct UnauthenticatedAck {
    pub seq32:u32,
    pub ack32:u32,
    sacks:[crate::ipv4_tcp::SackRange32;4],
    sack_count:u8,
}
impl UnauthenticatedAck {
    pub fn sacks(&self)->&[crate::ipv4_tcp::SackRange32]{
        &self.sacks[..usize::from(self.sack_count)]
    }
}
/// Strict pure ACK/SACK parser, no allocations. SACK must be explicitly
/// enabled from the authenticated cold capability; DATA remains M3-gated
/// through parse_data_packet. Scope and sent-range validation belong to the
/// per-lane OuterAckIndex, not this unauthenticated packet parser.
pub fn parse_ack_packet(packet:&[u8],trusted:TrustedRx<'_>,
    sack_negotiated:bool)->Result<UnauthenticatedAck,RxError>{
    let tuple=trusted.tuple;
    if !plausible_unicast(tuple.src_ip)||!plausible_unicast(tuple.dst_ip)
        ||tuple.src_port==0||tuple.dst_port==0{
        return Err(RxError::InvalidTrustedTuple)
    }
    if packet.len()>MAX_PACKET_LEN{return Err(RxError::TooLong)}
    if packet.len()>trusted.mtu{return Err(RxError::ExceedsMtu{
        actual:packet.len(),mtu:trusted.mtu})}
    if packet.len()<IPV4_HEADER_LEN+TCP_HEADER_LEN{return Err(RxError::TooShort)}
    if packet[0]!=0x45{return Err(RxError::WrongVersionOrIhl)}
    if packet[1]!=0{return Err(RxError::WrongIpHeader)}
    if usize::from(be16(&packet[2..4]))!=packet.len(){
        return Err(RxError::TotalLengthMismatch)
    }
    if be16(&packet[6..8])!=DF_ONLY{
        return Err(RxError::FragmentedOrUnexpectedFlags)
    }
    if packet[9]!=TCP_PROTO{return Err(RxError::WrongProtocol)}
    if packet[8]==0{return Err(RxError::WrongIpHeader)}
    if &packet[12..16]!=tuple.src_ip||&packet[16..20]!=tuple.dst_ip{
        return Err(RxError::WrongTuple)
    }
    if !checksum_is_valid(add_bytes(0,&packet[..IPV4_HEADER_LEN])){
        return Err(RxError::IpChecksum)
    }
    let tcp=&packet[IPV4_HEADER_LEN..];
    if be16(&tcp[0..2])!=tuple.src_port||be16(&tcp[2..4])!=tuple.dst_port{
        return Err(RxError::WrongTuple)
    }
    if tcp[12]&15!=0{return Err(RxError::InvalidTcpHeader)}
    let header=usize::from(tcp[12]>>4)*4;
    if header<TCP_HEADER_LEN||header>TCP_HEADER_LEN+40||header!=tcp.len(){
        return Err(RxError::InvalidTcpHeader)
    }
    if tcp[13]!=0x10{return Err(RxError::InvalidDataFlags)}
    if tcp[18]!=0||tcp[19]!=0{return Err(RxError::InvalidTcpHeader)}
    let opts=&tcp[TCP_HEADER_LEN..];
    let mut sacks=[crate::ipv4_tcp::SackRange32{start:0,end:0};4];
    let mut count=0usize;
    if !opts.is_empty(){
        if !sack_negotiated||opts.len()<12||opts.len()>36
            ||(opts.len()-4)%8!=0{
            return Err(RxError::UnsupportedOptions)
        }
        count=(opts.len()-4)/8;
        if count==0||count>4||
            opts[..4]!=[1,1,5,(2+8*count) as u8]{
            return Err(RxError::UnsupportedOptions)
        }
        for (i,slot) in sacks.iter_mut().take(count).enumerate(){
            let at=4+8*i;
            *slot=crate::ipv4_tcp::SackRange32{
                start:be32(&opts[at..at+4]),
                end:be32(&opts[at+4..at+8]),
            };
            if slot.start==slot.end{return Err(RxError::UnsupportedOptions)}
        }
    }
    let mut sum=add_bytes(0,&packet[12..20]);
    sum+=u64::from(TCP_PROTO)+tcp.len() as u64;
    sum=add_bytes(sum,tcp);
    if !checksum_is_valid(sum){return Err(RxError::TcpChecksum)}
    Ok(UnauthenticatedAck{seq32:be32(&tcp[4..8]),
        ack32:be32(&tcp[8..12]),sacks,sack_count:count as u8})
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ipv4_tcp::{build,build_presentation_ack,Presentation};
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
    fn a48_android_m3_pending_accepts_only_tcp_checksum_drift_as_untrusted(){
        let original=wire(b"original sealed M3 bytes",0x1_0000_000a,None);
        assert_eq!(
            parse_data_packet_android_m3_pending(&original,trusted(None,1500))
                .unwrap().ciphertext,
            b"original sealed M3 bytes"
        );
        // Real Bionic returned the exact original outer tuple and IP
        // checksum. Only the transport checksum was rejected 113 times.
        let mut drift=original.clone();
        drift[36]^=0x40;
        assert_eq!(
            parse_data_packet(&drift,trusted(None,1500)),
            Err(RxError::TcpChecksum)
        );
        let provisional=parse_data_packet_android_m3_pending(
            &drift,trusted(None,1500)).unwrap();
        assert_eq!(provisional.ciphertext,b"original sealed M3 bytes");
        assert_eq!(provisional.seq32,10); // wire wraps; M1 still extends

        // A forged valid tuple is not an authenticated M3 record: even
        // payload mutation is only returned as UNAUTHENTICATED bytes;
        // original M3 AEAD+PN remains the sole final admission.
        let mut altered=original.clone();
        altered[40]^=1;
        assert_eq!(parse_data_packet(&altered,trusted(None,1500)),
            Err(RxError::TcpChecksum));
        assert_ne!(
            parse_data_packet_android_m3_pending(
                &altered,trusted(None,1500)).unwrap().ciphertext,
            b"original sealed M3 bytes"
        );

        // Only structural/tuple gates precede the authenticated M3 opener.
        // Checksums are deliberately not a DATA admission condition.
        for (offset,mask,expected) in [
            (12,1,RxError::WrongTuple),
            (33,1,RxError::InvalidDataFlags),
            (2,1,RxError::TotalLengthMismatch),
            (22,1,RxError::WrongTuple),
        ] {
            let mut bad=original.clone();
            bad[offset]^=mask;
            assert_eq!(
                parse_data_packet_android_m3_pending(&bad,trusted(None,1500)),
                Err(expected),"offset={offset}"
            );
        }
        assert_eq!(
            parse_data_packet_android_m3_pending(&original,trusted(None,39)),
            Err(RxError::ExceedsMtu{actual:original.len(),mtu:39})
        );
        // A real checksum-validated pure ACK stays control, not M3 DATA.
        let mut ack_buf=[0u8;64];
        let ack=build_presentation_ack(
            tuple(),13,25,2,PacketPersona::Legacy,1500,&mut ack_buf
        ).unwrap();
        assert!(parse_ack_packet(ack,trusted(None,1500),false).is_ok());
        assert_eq!(parse_data_packet_android_m3_pending(
            ack,trusted(None,1500)),Err(RxError::InvalidDataFlags));
    }

    #[test]
    fn a49_single_pass_matches_a48_two_pass_android_admission(){
        let original=wire(b"original sealed M3 bytes",0x1_0000_000a,None);
        let mut bad_tcp=original.clone();bad_tcp[36]^=0x40;
        let mut bad_tuple=original.clone();bad_tuple[12]^=1;
        let mut bad_ip=original.clone();bad_ip[10]^=1;
        let mut bad_flags=original.clone();bad_flags[33]^=1;
        for packet in [&original[..],&bad_tcp[..],&bad_tuple[..],
                       &bad_flags[..]]{
            let old=match parse_data_packet(packet,trusted(None,1500)){
                Ok(data)=>Ok(data),
                Err(RxError::TcpChecksum)=>
                    parse_data_packet_android_m3_pending(packet,trusted(None,1500)),
                Err(other)=>Err(other),
            };
            // The M3-pending result stays UNAUTHENTICATED in BOTH cases.
            let fast=parse_data_packet_android_m3_pending(
                packet,trusted(None,1500));
            assert_eq!(fast,old);
        }
        // A short IPv4 checksum mismatch may occur with offload, and M3
        // still decides whether ciphertext is usable. The strict diagnostic
        // parser remains explicit, but no Android DATA requires it.
        assert_eq!(parse_data_packet(&bad_ip,trusted(None,1500)),
                   Err(RxError::IpChecksum));
        assert!(parse_data_packet_android_m3_pending(
            &bad_ip,trusted(None,1500)).is_ok());
        assert_eq!(parse_data_packet(&bad_tcp,trusted(None,1500)),
                   Err(RxError::TcpChecksum));
        let mut changed_dscp=original.clone();changed_dscp[1]=0x03;
        assert!(parse_data_packet_android_m3_pending(
            &changed_dscp,trusted(None,1500)).is_ok());
        let mut no_df=original.clone();no_df[6]=0;
        assert!(parse_data_packet_android_m3_pending(
            &no_df,trusted(None,1500)).is_ok());
        let mut fragmented=original.clone();fragmented[6]=0x20;
        assert_eq!(parse_data_packet_android_m3_pending(
            &fragmented,trusted(None,1500)),
            Err(RxError::FragmentedOrUnexpectedFlags));
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
        let mut empty=original[..40].to_vec();
        empty[2..4].copy_from_slice(&40u16.to_be_bytes());
        // Keep the IP checksum valid, so EmptyData is the actual failure gate.
        empty[10..12].fill(0);
        let ck = independent_sum(&empty[..20]);
        empty[10..12].copy_from_slice(&ck.to_be_bytes());
        assert_eq!(parse_data_packet(&empty,trusted(None,1500)),Err(RxError::EmptyData));
    }
    #[test]
    fn r1_rx_ipv4_tcp_wrong_ip_port_mutated_ttl_checksum_fails_closed() {
        let original=wire(b"record!",100,None);
        let cases=[
            (12,0u8,RxError::WrongTuple),
            (16,0u8,RxError::WrongTuple),
            (20,0u8,RxError::WrongTuple),
            (22,0u8,RxError::WrongTuple),
            (8,128u8,RxError::IpChecksum),
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

#[cfg(test)]
mod plan027_ack_tests{
    use super::*;
    use crate::ipv4_tcp::{build_presentation_ack_sack,PacketPersona,SackRange32};
    fn trusted_ack()->TrustedRx<'static>{
        TrustedRx{tuple:Ipv4Tuple{src_ip:&[192,0,2,10],
            dst_ip:&[198,51,100,10],src_port:43000,dst_port:443},
            persona:PacketPersona::Legacy,mtu:1500,
            authenticated_options:None}
    }
    #[test]
    fn r1_plan027_pure_ack_sack_checksum_capability_and_data_isolation(){
        let t=trusted_ack();
        let mut buf=[0u8;128];
        let blocks=[SackRange32{start:100,end:200},
            SackRange32{start:u32::MAX-5,end:3}];
        let ack=build_presentation_ack_sack(t.tuple,10,20,1,
            PacketPersona::Legacy,1500,&blocks,&mut buf).unwrap().to_vec();
        let parsed=parse_ack_packet(&ack,t,true).unwrap();
        assert_eq!(parsed.ack32,20);
        assert_eq!(parsed.seq32,10);
        assert_eq!(parsed.sacks(),&blocks);
        assert_eq!(parse_ack_packet(&ack,t,false),
            Err(RxError::UnsupportedOptions));
        assert_eq!(parse_data_packet(&ack,t).err(),Some(RxError::InvalidDataFlags));
        let mut corrupt=ack.clone();
        corrupt[44]^=1;
        assert_eq!(parse_ack_packet(&corrupt,t,true),Err(RxError::TcpChecksum));
        let mut bad=ack.clone();
        bad[12]^=1;
        assert_eq!(parse_ack_packet(&bad,t,true),Err(RxError::WrongTuple));
        let mut malformed=ack.clone();
        malformed[42]=4;
        assert_eq!(parse_ack_packet(&malformed,t,true),
            Err(RxError::UnsupportedOptions));
        let no_sack=build_presentation_ack_sack(t.tuple,10,20,1,
            PacketPersona::Legacy,1500,&[],&mut buf).unwrap();
        assert!(parse_ack_packet(no_sack,t,false).unwrap().sacks().is_empty());
    }
}

 
#[cfg(test)]
mod h2216_public_nat_ttl_tests {
    use super::*;
    use crate::ipv4_tcp::{build_bytes, build_presentation_ack, Presentation};

    // Reproduce ordinary IPv4 router TTL decrements while keeping a genuine
    // valid IPv4 checksum. TCP pseudoheader and opaque record do not change.
    fn routed(mut packet: Vec<u8>, ttl: u8) -> Vec<u8> {
        packet[8] = ttl;
        packet[10] = 0;
        packet[11] = 0;
        let mut sum: u32 = packet[..20]
            .chunks_exact(2)
            .map(|w| u32::from(u16::from_be_bytes([w[0], w[1]])))
            .sum();
        while sum > 0xffff {
            sum = (sum & 0xffff) + (sum >> 16);
        }
        packet[10..12].copy_from_slice(&(!(sum as u16)).to_be_bytes());
        packet
    }

    #[test]
    fn h2216_original_windows_128_to_116_client_public_nat_data_and_ack() {
        // The observed client-to-server WAN TTL in the user's sanitized pcap
        // was 116. The original Windows sender writes 128: two NATs plus WAN.
        for (persona, routed_ttl) in [
            (PacketPersona::Windows11, 116u8),
            (PacketPersona::Legacy, 52u8),
        ] {
            // Representative post-NAT addresses are documentation networks,
            // never the real subscriber's public/private IP from captures.
            let src = [198, 51, 100, 47];
            let dst = [192, 0, 2, 31];
            let tuple = Ipv4Tuple {
                src_ip: &src, dst_ip: &dst, src_port: 40005, dst_port: 443,
            };
            let trusted = TrustedRx {
                tuple, persona, mtu: 1400, authenticated_options: None,
            };
            let mut raw = [0u8; 256];
            let opaque = b"not-authenticated-until-M3-AEAD";
            let wire = build_bytes(tuple, Presentation {
                ack32: 200, advertised_window: 4096, ip_id: 7, persona,
            }, 100, opaque, None, 1400, &mut raw).unwrap().to_vec();
            assert_eq!(wire[8], persona.ttl());
            let routed_data = routed(wire.clone(), routed_ttl);
            assert_eq!(
                parse_data_packet(&routed_data, trusted).unwrap().ciphertext,
                opaque,
                "routed TTL {routed_ttl} must reach the still-mandatory M3 AEAD"
            );
            let mut ack_storage = [0u8; 128];
            let ack = build_presentation_ack(
                tuple, 101, 201, 8, persona, 1400, &mut ack_storage
            ).unwrap().to_vec();
            assert!(parse_ack_packet(&routed(ack.clone(), routed_ttl), trusted, false).is_ok());
            // A router can deliver an on-wire TTL larger than the chosen
            // sender persona's initial TTL, e.g. after middlebox rewriting.
            // Reject only the impossible zero-TTL header, never persona.
            assert!(parse_data_packet(&routed(wire.clone(), 255), trusted).is_ok());
            assert!(parse_ack_packet(&routed(ack.clone(), 255), trusted, false).is_ok());
            assert_eq!(
                parse_data_packet(&routed(wire.clone(), 0), trusted),
                Err(RxError::WrongIpHeader)
            );
            assert_eq!(
                parse_ack_packet(&routed(ack, 0), trusted, false),
                Err(RxError::WrongIpHeader)
            );
            let bad_ip_checksum = {
                let mut changed = routed_data.clone();
                changed[10] ^= 0x01;
                changed
            };
            assert_eq!(
                parse_data_packet(&bad_ip_checksum, trusted),
                Err(RxError::IpChecksum)
            );
        }
    }
}
