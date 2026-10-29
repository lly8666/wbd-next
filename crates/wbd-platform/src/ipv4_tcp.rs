//! R1 bounded IPv4/TCP-like steady DATA envelope: *bytes*, not a raw OS sender.
//! Based on pinned wobuzhidao internal/faketcp/packet.go (legacy source
//! a7a82db31fe736ffedee330795a3234d358f1984, blob
//! 6ac1f9b3d7208278d31078be8d61e2f3a6dbbd3b).
//! The cold authenticated owner supplies tuple/persona and optional negotiated
//! TCP option bytes. The M3 sealed record/PN is read-only and never re-sealed.
//! No SYN, TLS bootstrap, socket call, kernel checksum offload or peer receipt.
use wbd_types::buffer_contract::{driver_read, FrozenRecordHandle};

pub const IPV4_HEADER_LEN: usize = 20;
pub const TCP_HEADER_LEN: usize = 20;
pub const BASE_OVERHEAD: usize = IPV4_HEADER_LEN + TCP_HEADER_LEN;
pub const MAX_TCP_OPTIONS: usize = 40;
pub const IPV4_MAX_LENGTH: usize = u16::MAX as usize;
pub const TCP_DATA_FLAGS: u8 = 0x18; // ACK | PSH; original Go steady payload.
const TCP_PROTOCOL: u8 = 6;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PacketPersona { Legacy, Windows11 }
impl PacketPersona {
    pub fn ttl(self) -> u8 {
        match self { Self::Legacy => 64, Self::Windows11 => 128 }
    }
}

/// The owner must have obtained this source/destination IPv4 tuple from trusted
/// cold setup. Slices deliberately reject accidental 16-byte IPv6 addresses.
#[derive(Clone, Copy, Debug)]
pub struct Ipv4Tuple<'a> {
    pub src_ip: &'a [u8],
    pub dst_ip: &'a [u8],
    pub src_port: u16,
    pub dst_port: u16,
}

/// Mutable *presentation only*: ACK is not an authenticated receipt, and the
/// TCP seq comes instead from the frozen record's stable SeqOffset.
#[derive(Clone, Copy, Debug)]
pub struct Presentation {
    pub ack32: u32,
    pub advertised_window: u16,
    pub ip_id: u16,
    pub persona: PacketPersona,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct WireMeasure { pub required: usize, pub overhead: usize }

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PacketError {
    InvalidIpv4Tuple,
    InvalidPort,
    EmptyRecord,
    UnsupportedOptions,
    Ipv4TooLong { required: usize },
    MtuExceeded { required: usize, mtu: usize },
    ScratchTooSmall { required: usize, available: usize },
}

/// Negotiated option bytes are explicitly passed from authenticated session
/// state. No implicit TCP timestamp is invented. Only DATA-compatible NOP,
/// EOL/padding, and negotiated timestamp option (kind=8, size=10) are accepted;
/// SYN-only options, SACK/ACK-control options, malformed lengths and duplicate
/// timestamps fail closed.
fn check_options(opts: &[u8]) -> Result<(), PacketError> {
    if opts.len() > MAX_TCP_OPTIONS || opts.len() % 4 != 0 {
        return Err(PacketError::UnsupportedOptions);
    }
    let mut i = 0;
    let mut timestamp = false;
    while i < opts.len() {
        match opts[i] {
            0 => {
                if opts[i..].iter().any(|&b| b != 0) {
                    return Err(PacketError::UnsupportedOptions);
                }
                break;
            }
            1 => i += 1,
            8 => {
                if timestamp || opts.len() - i < 10 || opts[i + 1] != 10 {
                    return Err(PacketError::UnsupportedOptions);
                }
                timestamp = true;
                i += 10;
            }
            _ => return Err(PacketError::UnsupportedOptions),
        }
    }
    Ok(())
}

/// Derive true envelope size before touching scratch; never guess a default
/// MTU, add bootstrap SYN options, or double-count LINK/record overhead.
pub fn measure(record_len: usize, authenticated_options: Option<&[u8]>)
    -> Result<WireMeasure, PacketError>
{
    if record_len == 0 { return Err(PacketError::EmptyRecord); }
    let options = authenticated_options.unwrap_or(&[]);
    check_options(options)?;
    let overhead = BASE_OVERHEAD + options.len();
    let required = overhead.checked_add(record_len)
        .ok_or(PacketError::Ipv4TooLong { required: usize::MAX })?;
    if required > IPV4_MAX_LENGTH {
        return Err(PacketError::Ipv4TooLong { required });
    }
    Ok(WireMeasure { required, overhead })
}

fn check_tuple(tuple: Ipv4Tuple<'_>) -> Result<(), PacketError> {
    fn ipv4_unicast(ip: &[u8]) -> bool {
        ip.len() == 4 && ip != [0, 0, 0, 0] && ip != [255, 255, 255, 255]
            && ip[0] != 0 && ip[0] < 224
    }
    if !ipv4_unicast(tuple.src_ip) || !ipv4_unicast(tuple.dst_ip) {
        return Err(PacketError::InvalidIpv4Tuple);
    }
    if tuple.src_port == 0 || tuple.dst_port == 0 {
        return Err(PacketError::InvalidPort);
    }
    Ok(())
}

fn sum_words(bytes: &[u8]) -> u64 {
    let mut sum = 0u64;
    let mut chunks = bytes.chunks_exact(2);
    for word in &mut chunks {
        sum += u64::from(u16::from_be_bytes([word[0], word[1]]));
    }
    if let [odd] = chunks.remainder() {
        sum += u64::from(*odd) << 8;
    }
    sum
}
fn finish_checksum(mut sum: u64) -> u16 {
    while sum >> 16 != 0 { sum = (sum & 0xffff) + (sum >> 16); }
    !(sum as u16)
}

/// Writes into *caller-owned* bounded scratch after all validation has passed.
/// A successful result is a complete IPv4 header + TCP header + the same frozen
/// wire record. No allocations, locks, Arc clones or syscall on this path.
/// 'bytes' can be submitted through the separate R1 ready-only driver, whose
/// Accepted classification never means peer ACK or authenticated receipt.
pub fn build<'b, H: FrozenRecordHandle>(
    tuple: Ipv4Tuple<'_>,
    presentation: Presentation,
    record: &H,
    authenticated_options: Option<&[u8]>,
    mtu: usize,
    scratch: &'b mut [u8],
) -> Result<&'b [u8], PacketError> {
    let read = driver_read(record);
    build_bytes(tuple, presentation, record.metadata().seq.0, read.wire,
        authenticated_options, mtu, scratch)
}

/// Same zero-allocation carrier builder for raw immutable bytes produced by
/// the authenticated Rust owner: no per-packet Go FFI or temporary Arc.
pub fn build_bytes<'b>(
    tuple: Ipv4Tuple<'_>, presentation: Presentation, seq64: u64,
    wire: &[u8], authenticated_options: Option<&[u8]>,
    mtu: usize, scratch: &'b mut [u8],
) -> Result<&'b [u8], PacketError> {
    check_tuple(tuple)?;
    let plan = measure(wire.len(), authenticated_options)?;
    if plan.required > mtu {
        return Err(PacketError::MtuExceeded { required: plan.required, mtu });
    }
    if scratch.len() < plan.required {
        return Err(PacketError::ScratchTooSmall {
            required: plan.required, available: scratch.len(),
        });
    }

    let options = authenticated_options.unwrap_or(&[]);
    let packet = &mut scratch[..plan.required];
    let header_len = plan.overhead;
    packet[..header_len].fill(0);
    let (ip, tcp) = packet.split_at_mut(IPV4_HEADER_LEN);
    ip[0] = 0x45; // v4, IHL=5; original Go does not emit IPv4 options.
    ip[2..4].copy_from_slice(&(plan.required as u16).to_be_bytes());
    ip[4..6].copy_from_slice(&presentation.ip_id.to_be_bytes());
    ip[6..8].copy_from_slice(&0x4000u16.to_be_bytes()); // DF, no fragmentation.
    ip[8] = presentation.persona.ttl();
    ip[9] = TCP_PROTOCOL;
    ip[12..16].copy_from_slice(tuple.src_ip);
    ip[16..20].copy_from_slice(tuple.dst_ip);
    let ip_checksum = finish_checksum(sum_words(ip));
    ip[10..12].copy_from_slice(&ip_checksum.to_be_bytes());

    tcp[0..2].copy_from_slice(&tuple.src_port.to_be_bytes());
    tcp[2..4].copy_from_slice(&tuple.dst_port.to_be_bytes());
    // 64-bit owner seq is stable across retransmission; only wire32 wraps.
    tcp[4..8].copy_from_slice(&(seq64 as u32).to_be_bytes());
    tcp[8..12].copy_from_slice(&presentation.ack32.to_be_bytes());
    tcp[12] = (((TCP_HEADER_LEN + options.len()) / 4) as u8) << 4;
    tcp[13] = TCP_DATA_FLAGS;
    tcp[14..16].copy_from_slice(&presentation.advertised_window.to_be_bytes());
    tcp[TCP_HEADER_LEN..TCP_HEADER_LEN + options.len()].copy_from_slice(options);
    tcp[TCP_HEADER_LEN + options.len()..].copy_from_slice(wire);

    // TCP one’s-complement pseudoheader: IPv4 src/dst, 00 06, TCP length.
    // Works with odd record lengths and every negotiated option length.
    let sum = sum_words(tuple.src_ip) + sum_words(tuple.dst_ip)
        + u64::from(TCP_PROTOCOL) + tcp.len() as u64 + sum_words(tcp);
    tcp[16..18].copy_from_slice(&finish_checksum(sum).to_be_bytes());
    Ok(&scratch[..plan.required])
}


/// TCP-looking presentation ACK only. This consumes no AEAD PN, is not
/// an M2 receipt, and must be scheduled only after authenticated M3 delivery.
/// Bounded 40B, no allocation; TX may coalesce multiple RX ACKs into one.
pub fn build_presentation_ack<'a>(
    tuple: Ipv4Tuple<'_>, seq32: u32, ack32: u32,
    ip_id: u16, persona: PacketPersona, mtu: usize,
    scratch: &'a mut [u8],
) -> Result<&'a [u8],PacketError> {
    check_tuple(tuple)?;
    if mtu<BASE_OVERHEAD{return Err(PacketError::MtuExceeded {
        required:BASE_OVERHEAD,mtu,
    })}
    if scratch.len()<BASE_OVERHEAD{return Err(PacketError::ScratchTooSmall {
        required:BASE_OVERHEAD,available:scratch.len(),
    })}
    let packet=&mut scratch[..BASE_OVERHEAD];
    packet.fill(0);
    let (ip,tcp)=packet.split_at_mut(IPV4_HEADER_LEN);
    ip[0]=0x45;
    ip[2..4].copy_from_slice(&(BASE_OVERHEAD as u16).to_be_bytes());
    ip[4..6].copy_from_slice(&ip_id.to_be_bytes());
    ip[6..8].copy_from_slice(&0x4000u16.to_be_bytes());
    ip[8]=persona.ttl();
    ip[9]=TCP_PROTOCOL;
    ip[12..16].copy_from_slice(tuple.src_ip);
    ip[16..20].copy_from_slice(tuple.dst_ip);
    let checksum = finish_checksum(sum_words(ip));
    ip[10..12].copy_from_slice(&checksum.to_be_bytes());
    tcp[0..2].copy_from_slice(&tuple.src_port.to_be_bytes());
    tcp[2..4].copy_from_slice(&tuple.dst_port.to_be_bytes());
    tcp[4..8].copy_from_slice(&seq32.to_be_bytes());
    tcp[8..12].copy_from_slice(&ack32.to_be_bytes());
    tcp[12]=5u8<<4;
    tcp[13]=0x10; // ACK with no DATA, exactly legacy Go sendACK
    tcp[14..16].copy_from_slice(&65535u16.to_be_bytes());
    let sum=sum_words(tuple.src_ip)+sum_words(tuple.dst_ip)
        +u64::from(TCP_PROTOCOL)+tcp.len() as u64+sum_words(tcp);
    tcp[16..18].copy_from_slice(&finish_checksum(sum).to_be_bytes());
    Ok(packet)
}


/** Untrusted presentation SACK range, NEVER application delivery or
 * authenticated liveness. The owner must scope/extend/validate against
 * definite sent spans before releasing optional immutable repair shadows.
 */
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct SackRange32 { pub start:u32,pub end:u32 }

/// Strict pure TCP-looking ACK with optional 1..4 SACK blocks. No AEAD PN,
/// ciphertext, heap allocation, or DATA acknowledgement loop. The caller
/// MUST have negotiated SACK in the original protected cold handshake.
pub fn build_presentation_ack_sack<'a>(
    tuple:Ipv4Tuple<'_>,seq32:u32,ack32:u32,ip_id:u16,
    persona:PacketPersona,mtu:usize,sacks:&[SackRange32],
    scratch:&'a mut [u8],
)->Result<&'a [u8],PacketError>{
    if sacks.is_empty(){
        return build_presentation_ack(tuple,seq32,ack32,ip_id,persona,mtu,scratch)
    }
    if sacks.len()>4||sacks.iter().any(|r|r.start==r.end){
        return Err(PacketError::UnsupportedOptions)
    }
    check_tuple(tuple)?;
    // NOP,NOP,SACK(kind5,length2+8*n), then exactly n pairs.
    let options=4+8*sacks.len();
    let required=BASE_OVERHEAD+options;
    if required>mtu{return Err(PacketError::MtuExceeded{required,mtu})}
    if required>scratch.len(){return Err(PacketError::ScratchTooSmall{
        required,available:scratch.len()})}
    let packet=&mut scratch[..required];
    packet.fill(0);
    let (ip,tcp)=packet.split_at_mut(IPV4_HEADER_LEN);
    ip[0]=0x45;
    ip[2..4].copy_from_slice(&(required as u16).to_be_bytes());
    ip[4..6].copy_from_slice(&ip_id.to_be_bytes());
    ip[6..8].copy_from_slice(&0x4000u16.to_be_bytes());
    ip[8]=persona.ttl();ip[9]=TCP_PROTOCOL;
    ip[12..16].copy_from_slice(tuple.src_ip);
    ip[16..20].copy_from_slice(tuple.dst_ip);
    ip[10..12].copy_from_slice(&finish_checksum(sum_words(ip)).to_be_bytes());
    tcp[0..2].copy_from_slice(&tuple.src_port.to_be_bytes());
    tcp[2..4].copy_from_slice(&tuple.dst_port.to_be_bytes());
    tcp[4..8].copy_from_slice(&seq32.to_be_bytes());
    tcp[8..12].copy_from_slice(&ack32.to_be_bytes());
    tcp[12]=((TCP_HEADER_LEN+options)/4) as u8<<4;
    tcp[13]=0x10;
    tcp[14..16].copy_from_slice(&65535u16.to_be_bytes());
    tcp[20..24].copy_from_slice(&[1,1,5,(2+8*sacks.len()) as u8]);
    for (i,range) in sacks.iter().enumerate(){
        let at=24+8*i;
        tcp[at..at+4].copy_from_slice(&range.start.to_be_bytes());
        tcp[at+4..at+8].copy_from_slice(&range.end.to_be_bytes());
    }
    let sum=sum_words(tuple.src_ip)+sum_words(tuple.dst_ip)
        +u64::from(TCP_PROTOCOL)+tcp.len() as u64+sum_words(tcp);
    tcp[16..18].copy_from_slice(&finish_checksum(sum).to_be_bytes());
    Ok(packet)
}

/// Build only the original IPv4+TCP header into the caller's preallocated
/// scratch. The checksum reads frozen ciphertext without copying it; the
/// Linux scatter sendmmsg backend lends TWO iovecs (header, original record)
/// to the kernel synchronously. No new packet, record PN or payload buffer.
pub fn build_scatter_header<H:FrozenRecordHandle>(
    tuple:Ipv4Tuple<'_>,presentation:Presentation,record:&H,
    authenticated_options:Option<&[u8]>,mtu:usize,header:&mut [u8]
)->Result<usize,PacketError>{
    check_tuple(tuple)?;
    let frozen=driver_read(record);
    let plan=measure(frozen.wire.len(),authenticated_options)?;
    if plan.required>mtu{
        return Err(PacketError::MtuExceeded{required:plan.required,mtu});
    }
    if header.len()<plan.overhead{
        return Err(PacketError::ScratchTooSmall{
            required:plan.overhead,available:header.len()
        });
    }
    let options=authenticated_options.unwrap_or(&[]);
    let bytes=&mut header[..plan.overhead];
    bytes.fill(0);
    let (ip,tcp)=bytes.split_at_mut(IPV4_HEADER_LEN);
    ip[0]=0x45;
    ip[2..4].copy_from_slice(&(plan.required as u16).to_be_bytes());
    ip[4..6].copy_from_slice(&presentation.ip_id.to_be_bytes());
    ip[6..8].copy_from_slice(&0x4000u16.to_be_bytes());
    ip[8]=presentation.persona.ttl();
    ip[9]=TCP_PROTOCOL;
    ip[12..16].copy_from_slice(tuple.src_ip);
    ip[16..20].copy_from_slice(tuple.dst_ip);
    let ip_sum=finish_checksum(sum_words(ip));
    ip[10..12].copy_from_slice(&ip_sum.to_be_bytes());
    tcp[0..2].copy_from_slice(&tuple.src_port.to_be_bytes());
    tcp[2..4].copy_from_slice(&tuple.dst_port.to_be_bytes());
    tcp[4..8].copy_from_slice(&(record.metadata().seq.0 as u32).to_be_bytes());
    tcp[8..12].copy_from_slice(&presentation.ack32.to_be_bytes());
    tcp[12]=(((TCP_HEADER_LEN+options.len())/4) as u8)<<4;
    tcp[13]=TCP_DATA_FLAGS;
    tcp[14..16].copy_from_slice(&presentation.advertised_window.to_be_bytes());
    tcp[TCP_HEADER_LEN..].copy_from_slice(options);
    // Header is even length; split checksum terms are exact even for odd
    // payload bytes. The checksum field was zero-filled above.
    let sum=sum_words(tuple.src_ip)+sum_words(tuple.dst_ip)
        +u64::from(TCP_PROTOCOL)
        +(plan.required-IPV4_HEADER_LEN) as u64
        +sum_words(tcp)+sum_words(frozen.wire);
    tcp[16..18].copy_from_slice(&finish_checksum(sum).to_be_bytes());
    Ok(plan.overhead)
}

#[cfg(test)]
mod tests {
    use super::*;
    use wbd_types::{BufferKey, LaneKey, RecordPn, SeqOffset, TunnelKey};
    use wbd_types::buffer_contract::{BufferOrigin, FrozenMetadata};

    #[test]
    fn presentation_ack_is_exact_40_bytes_and_not_data() {
        let tuple=Ipv4Tuple{src_ip:&[192,0,2,1],dst_ip:&[192,0,2,2],
            src_port:49152,dst_port:443};
        let mut buf=[0u8;64];
        let raw=build_presentation_ack(tuple,0xffff_fffe,100,7,
            PacketPersona::Windows11,1400,&mut buf).unwrap();
        assert_eq!(raw.len(),40);
        assert_eq!(raw[8],128);
        assert_eq!(raw[20+13],0x10);
        assert_eq!(&raw[24..28],&0xffff_fffeu32.to_be_bytes());
        assert_eq!(&raw[28..32],&100u32.to_be_bytes());
        assert_eq!(finish_checksum(sum_words(&raw[..20])),0);
    }
    #[test]
    fn build_bytes_is_identical_to_frozen_builder() {
        let frozen=TestFrozen {wire:vec![1,2,3,4,5,6,7],seq:SeqOffset(0xffff_fffe)};
        let tuple=Ipv4Tuple {src_ip:&[10,2,0,1],dst_ip:&[10,2,0,2],
            src_port:4001,dst_port:443};
        let p=Presentation {ack32:100,advertised_window:65535,ip_id:7,
            persona:PacketPersona::Windows11};
        let mut old=[0u8;256];let mut native=[0u8;256];
        let a=build(tuple,p,&frozen,None,1500,&mut old).unwrap();
        let b=build_bytes(tuple,p,frozen.seq.0,&frozen.wire,None,1500,&mut native).unwrap();
        assert_eq!(a,b);
    }
    #[derive(Clone)]
    struct TestFrozen { wire: Vec<u8>, seq: SeqOffset }
    impl FrozenRecordHandle for TestFrozen {
        fn origin(&self) -> BufferOrigin {
            BufferOrigin { owner_arena: 1, key: BufferKey {slot: 2, generation: 1} }
        }
        fn metadata(&self) -> FrozenMetadata {
            FrozenMetadata {
                lane: LaneKey { tunnel: TunnelKey {slot: 3, generation: 1},
                    slot: 4, generation: 1 },
                seq: self.seq, pn: RecordPn(99), carrier_snapshot: 1,
            }
        }
        fn bytes(&self) -> &[u8] { &self.wire }
    }
    fn packet_tuple<'a>() -> Ipv4Tuple<'a> {
        Ipv4Tuple {src_ip: &[192,0,2,40], dst_ip: &[198,51,100,40],
            src_port:43000, dst_port:443}
    }
    fn state() -> Presentation {
        Presentation {ack32:200, advertised_window:1024, ip_id:21,
            persona:PacketPersona::Legacy}
    }
    fn frame(s: &[u8], seq: u64) -> TestFrozen {
        TestFrozen {wire:s.to_vec(), seq:SeqOffset(seq)}
    }
    fn bytes(s: &str) -> Vec<u8> {
        (0..s.len()).step_by(2)
            .map(|i| u8::from_str_radix(&s[i..i+2], 16).unwrap()).collect()
    }
    // Independent byte-wise reference from old Go packet.go checksum model,
    // rather than reusing the production sum_words/finish_checksum.
    fn oracle_cksum(data: &[u8]) -> u16 {
        let mut accumulator: u64 = 0;
        for (idx,b) in data.iter().enumerate() {
            accumulator += (u64::from(*b)) << (if idx % 2 == 0 {8} else {0});
        }
        while accumulator > 65535 { accumulator = (accumulator & 65535) + (accumulator >> 16); }
        !(accumulator as u16)
    }
    fn check_packet(wire: &[u8]) {
        assert_eq!(oracle_cksum(&wire[..20]), 0, "IPv4 checksum");
        let tcp = &wire[20..];
        let mut pseudo = Vec::from(&wire[12..20]);
        pseudo.extend_from_slice(&[0, 6]);
        pseudo.extend_from_slice(&(tcp.len() as u16).to_be_bytes());
        pseudo.extend_from_slice(tcp);
        assert_eq!(oracle_cksum(&pseudo), 0, "TCP pseudoheader checksum");
    }


    #[test]
    fn r1_m4_013_scatter_header_matches_full_packet_even_odd_opts_and_seq32(){
        let tests=[b"record".as_slice(),b"record!".as_slice(),&[1,2,3][..]];
        for (i,payload) in tests.iter().enumerate(){
            let f=frame(payload,0x1_ffff_fffdu64+i as u64);
            let opts=if i==2{Some(&[1u8,1,1,1][..])}else{None};
            let mut header=[0xaau8;80];let mut full=[0x55u8;256];
            let len=build_scatter_header(packet_tuple(),state(),&f,opts,1500,
                &mut header).unwrap();
            let actual=build(packet_tuple(),state(),&f,opts,1500,&mut full)
                .unwrap();
            assert_eq!(&header[..len],&actual[..len]);
            assert_eq!(&actual[len..],f.bytes());
            assert!(header[len..].iter().all(|x|*x==0xaa));
            assert_eq!(f.metadata().pn,RecordPn(99));
            check_packet(actual);
        }
        let f=frame(b"x",1);let mut small=[0xabu8;39];
        assert!(matches!(build_scatter_header(packet_tuple(),state(),&f,
            None,1500,&mut small),Err(PacketError::ScratchTooSmall{..})));
        assert_eq!(small,[0xab;39]);
        let mut header=[0x55u8;80];
        assert!(matches!(build_scatter_header(packet_tuple(),state(),&f,
            None,40,&mut header),Err(PacketError::MtuExceeded{..})));
        assert_eq!(header,[0x55;80]);
    }
    #[test]
    fn r1_ipv4_tcp_go_pinned_legacy_exact_golden_even_record() {
        // wobuzhidao packet.go: IPv4 v4/IHL5, DF, TTL64, TCP ACK|PSH,
        // window 1024, ports 43000/443, seq100/ack200, ipID21.
        let f=frame(b"record",100);let mut out=[0xa5u8;100];
        let got=build(packet_tuple(),state(),&f,None,1500,&mut out).unwrap();
        let want=bytes("4500002e0015400040064e31c0000228c6336428a7f801bb00000064000000c850180400cc2900007265636f7264");
        assert_eq!(got,want);
        assert_eq!(got.len(),46);
        assert_eq!(&out[46..],[0xa5;54]);
        check_packet(&want);
    }

    #[test]
    fn r1_ipv4_tcp_odd_and_even_checksum_independent_and_corruption() {
        for payload in [b"record".as_slice(), b"record!".as_slice(), &[0,255,1]] {
            let f=frame(payload,100);let mut out=[0;256];
            let got=build(packet_tuple(),state(),&f,None,1500,&mut out).unwrap();
            check_packet(got);
            if payload==b"record!" {
                assert_eq!(got,bytes("4500002f0015400040064e30c0000228c6336428a7f801bb00000064000000c850180400ab2800007265636f726421"));
            }
            let mut corrupted=got.to_vec();corrupted[40]^=1;
            let mut pseudo=Vec::from(&corrupted[12..20]);
            pseudo.extend_from_slice(&[0,6]);
            pseudo.extend_from_slice(&((corrupted.len()-20) as u16).to_be_bytes());
            pseudo.extend_from_slice(&corrupted[20..]);
            assert_ne!(oracle_cksum(&pseudo),0);
            corrupted=got.to_vec();corrupted[8]^=1;
            assert_ne!(oracle_cksum(&corrupted[..20]),0);
        }
    }

    #[test]
    fn r1_ipv4_tcp_exact_mtu_minus_one_and_scratch_failure_atomic() {
        let f=frame(b"record!",100);
        let mut out=[0x7a;80];
        let plan=measure(f.wire.len(),None).unwrap();
        assert_eq!(plan,WireMeasure{required:47,overhead:40});
        assert_eq!(build(packet_tuple(),state(),&f,None,46,&mut out),
            Err(PacketError::MtuExceeded{required:47,mtu:46}));
        assert!(out.iter().all(|x|*x==0x7a));
        assert_eq!(build(packet_tuple(),state(),&f,None,47,&mut out[..46]),
            Err(PacketError::ScratchTooSmall{required:47,available:46}));
        assert!(out.iter().all(|x|*x==0x7a));
        assert_eq!(build(packet_tuple(),state(),&f,None,47,&mut out).unwrap().len(),47);
        let long=frame(&vec![9u8;65536],1);
        assert_eq!(build(packet_tuple(),state(),&long,None,100000,&mut out),
            Err(PacketError::Ipv4TooLong{required:65576}));
    }

    #[test]
    fn r1_ipv4_tcp_seq32_wrap_preserves_sealed_record_on_repair() {
        let f=frame(&[0,2,4,0xff,1],0x1_ffff_fffe);
        let original=f.wire.clone();let mut first=[0;100];let mut second=[0;100];
        let p1=build(packet_tuple(),state(),&f,None,100,&mut first).unwrap().to_vec();
        let mut s2=state();s2.ack32+=1;s2.ip_id+=1;
        let p2=build(packet_tuple(),s2,&f,None,100,&mut second).unwrap().to_vec();
        assert_eq!(&p1[24..28], &[255,255,255,254]);
        assert_eq!(&p2[24..28], &[255,255,255,254]);
        assert_eq!(&p1[40..],&original);
        assert_eq!(&p2[40..],&original);
        assert_ne!(p1,p2);
        check_packet(&p1);check_packet(&p2);
        let next=frame(b"X",0x2_0000_0001);
        let mut buf=[0;100];
        let p=build(packet_tuple(),state(),&next,None,100,&mut buf).unwrap();
        assert_eq!(&p[24..28],&[0,0,0,1]);
        assert_eq!(next.metadata().pn,RecordPn(99)); // seq wrap != PN wrap.
    }

    #[test]
    fn r1_ipv4_tcp_reject_ipv6_zero_ports_options_and_empty() {
        let f=frame(b"x",1);let mut out=[0x5a;100];
        let mut bad=packet_tuple();bad.src_ip=&[0;16];
        assert_eq!(build(bad,state(),&f,None,1500,&mut out),Err(PacketError::InvalidIpv4Tuple));
        bad=packet_tuple();bad.src_port=0;
        assert_eq!(build(bad,state(),&f,None,1500,&mut out),Err(PacketError::InvalidPort));
        let bad_addr=Ipv4Tuple{src_ip:&[224,0,0,1],..packet_tuple()};
        assert_eq!(build(bad_addr,state(),&f,None,1500,&mut out),Err(PacketError::InvalidIpv4Tuple));
        assert_eq!(measure(1,Some(&[1;41])),Err(PacketError::UnsupportedOptions));
        assert_eq!(measure(1,Some(&[1;3])),Err(PacketError::UnsupportedOptions));
        assert_eq!(measure(1,Some(&[2,4,5,0])),Err(PacketError::UnsupportedOptions)); // MSS on DATA
        assert_eq!(measure(1,Some(&[8,10,0,0])),Err(PacketError::UnsupportedOptions));
        assert_eq!(measure(1,Some(&[0,1,0,0])),Err(PacketError::UnsupportedOptions));
        let empty=frame(b"",2);
        assert_eq!(build(packet_tuple(),state(),&empty,None,1500,&mut out),Err(PacketError::EmptyRecord));
        assert!(out.iter().all(|x|*x==0x5a));
    }

    #[test]
    fn r1_ipv4_tcp_authenticated_timestamp_explicit_not_implicit() {
        let opts=[1,1,8,10,0,0,0,1,0,0,0,2,0,0,0,0];
        let f=frame(b"odd",55);let mut first=[0;100];let mut second=[0;100];
        let baseline=build(packet_tuple(),state(),&f,None,100,&mut first).unwrap();
        assert_eq!(baseline[32]>>4,5);
        let pkt=build(packet_tuple(),state(),&f,Some(&opts),100,&mut second).unwrap();
        assert_eq!(pkt.len(),59);
        assert_eq!(pkt[32]>>4,9);
        assert_eq!(&pkt[40..56],&opts);
        assert_eq!(&pkt[56..],b"odd");
        check_packet(pkt);
        let mut persona=state();persona.persona=PacketPersona::Windows11;
        let p=build(packet_tuple(),persona,&f,None,100,&mut first).unwrap();
        assert_eq!(p[8],128);check_packet(p);
    }
}

#[cfg(test)]
mod plan027_sack_builder_tests{
    use super::*;
    fn tuple()->Ipv4Tuple<'static>{
        Ipv4Tuple{src_ip:&[192,0,2,10],dst_ip:&[198,51,100,10],
            src_port:43000,dst_port:443}
    }
    #[test]
    fn r1_plan027_presentation_sack_builder_bounded_and_original_ack_unchanged(){
        let mut a=[0u8;128];let mut b=[0u8;128];
        let old=build_presentation_ack(tuple(),10,20,1,
            PacketPersona::Legacy,1500,&mut a).unwrap().to_vec();
        let empty=build_presentation_ack_sack(tuple(),10,20,1,
            PacketPersona::Legacy,1500,&[],&mut b).unwrap().to_vec();
        assert_eq!(old,empty);
        let ranges=[SackRange32{start:100,end:200};4];
        let full=build_presentation_ack_sack(tuple(),10,20,1,
            PacketPersona::Legacy,1500,&ranges,&mut a).unwrap();
        assert_eq!(full.len(),76);
        assert_eq!(&full[40..44],&[1,1,5,34]);
        assert_eq!(build_presentation_ack_sack(tuple(),10,20,1,
            PacketPersona::Legacy,75,&ranges,&mut a),
            Err(PacketError::MtuExceeded{required:76,mtu:75}));
        assert_eq!(build_presentation_ack_sack(tuple(),10,20,1,
            PacketPersona::Legacy,1500,&[ranges[0];5],&mut a),
            Err(PacketError::UnsupportedOptions));
    }
}
