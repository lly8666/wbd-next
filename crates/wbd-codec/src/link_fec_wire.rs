//! R0 LINK/FEC **wire-only** schema and MTU boundaries. Neither fragment
//! reassembly nor GF(256)/parity decoding is implemented. Input must come
//! from an already authenticated record / negotiated lane mode.
#![forbid(unsafe_code)]

pub const LINK_MAGIC: &[u8; 8] = b"WBDLFRG1";
pub const LINK_HEADER: usize = 20;
pub const FEC_HEADER: usize = 56;
pub const MAX_LOGICAL_DATAGRAM: usize = 65_535;
pub const FEC_DATA_SHARDS: usize = 20;
pub const FEC_PARITY_PROFILES: [u8; 6] = [4, 8, 10, 12, 16, 20];

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum WireError {
    InvalidBudget,
    InvalidLength,
    InvalidHeader,
    InvalidFragment,
    InvalidShard,
    InvalidMode,
    PacketTooLarge,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum LinkMode {
    /// Fixed FEC off: historical "WF" user payload is NOT escaped.
    FixedOff,
    /// Auto FEC current-off path: "WF" prefix MUST be escaped.
    AdaptiveOff,
}
#[derive(Debug, PartialEq, Eq)]
pub struct Fragment<'a> {
    pub index: u16,
    pub count: u16,
    pub total_len: u16,
    pub packet_id: u32,
    pub payload: &'a [u8],
}
#[derive(Debug, PartialEq, Eq)]
pub enum LinkView<'a> {
    Ordinary(&'a [u8]),
    Fragment(Fragment<'a>),
}

fn validate_mtu(mtu: usize) -> Result<usize, WireError> {
    if !(LINK_HEADER + 1..=MAX_LOGICAL_DATAGRAM).contains(&mtu) {
        return Err(WireError::InvalidBudget);
    }
    Ok(mtu - LINK_HEADER)
}
fn be16(b: &[u8]) -> u16 { u16::from_be_bytes([b[0], b[1]]) }
fn be32(b: &[u8]) -> u32 { u32::from_be_bytes([b[0], b[1], b[2], b[3]]) }
fn need_escape(payload: &[u8], mode: LinkMode) -> bool {
    payload.starts_with(LINK_MAGIC)
        || (mode == LinkMode::AdaptiveOff && payload.starts_with(b"WF"))
}

/// The frame budget is the **already calculated LINK payload budget** after
/// outer IP/TCP/MSS, record overhead, optional FEC headroom and Game envelope.
/// Do not subtract any such overhead here a second time. A single Fragmenter
/// owner supplies monotone nonzero packet_id; this helper does not allocate IDs.
pub fn fragment_compat(
    payload: &[u8], mtu: usize, mode: LinkMode, packet_id: u32,
) -> Result<Vec<Vec<u8>>, WireError> {
    let chunk = validate_mtu(mtu)?;
    if payload.is_empty() || payload.len() > MAX_LOGICAL_DATAGRAM {
        return Err(WireError::PacketTooLarge);
    }
    if payload.len() <= mtu && !need_escape(payload, mode) {
        return Ok(vec![payload.to_vec()]);
    }
    if packet_id == 0 { return Err(WireError::InvalidFragment); }
    let count = payload.len().div_ceil(chunk);
    if count > u16::MAX as usize { return Err(WireError::PacketTooLarge); }
    let mut result = Vec::with_capacity(count);
    for (index, part) in payload.chunks(chunk).enumerate() {
        let mut wire = Vec::with_capacity(LINK_HEADER + part.len());
        wire.extend_from_slice(LINK_MAGIC);
        wire.push(1);
        wire.push(0);
        wire.extend_from_slice(&(index as u16).to_be_bytes());
        wire.extend_from_slice(&(count as u16).to_be_bytes());
        wire.extend_from_slice(&(payload.len() as u16).to_be_bytes());
        wire.extend_from_slice(&packet_id.to_be_bytes());
        wire.extend_from_slice(part);
        result.push(wire);
    }
    Ok(result)
}

/// Only called **after record authentication**. It does not reassemble,
/// allocate reassembly slots, infer live packet generation or deliver business.
pub fn inspect_link(
    wire: &[u8], mtu: usize, mode: LinkMode,
) -> Result<LinkView<'_>, WireError> {
    validate_mtu(mtu)?;
    if wire.is_empty() || wire.len() > mtu {
        return Err(WireError::InvalidLength);
    }
    if !wire.starts_with(LINK_MAGIC) {
        if mode == LinkMode::AdaptiveOff && wire.starts_with(b"WF") {
            return Err(WireError::InvalidMode);
        }
        return Ok(LinkView::Ordinary(wire));
    }
    if wire.len() < LINK_HEADER + 1 {
        return Err(WireError::InvalidFragment);
    }
    if wire[8] != 1 || wire[9] != 0 {
        return Err(WireError::InvalidHeader);
    }
    let index = be16(&wire[10..12]);
    let count = be16(&wire[12..14]);
    let total_len = be16(&wire[14..16]);
    let packet_id = be32(&wire[16..20]);
    let payload = &wire[LINK_HEADER..];
    if packet_id == 0 || total_len == 0 || count == 0 || index >= count
        || payload.len() > total_len as usize || payload.is_empty()
        || count as usize > total_len as usize
    {
        return Err(WireError::InvalidFragment);
    }
    if count == 1 && (index != 0 || payload.len() != total_len as usize) {
        return Err(WireError::InvalidFragment);
    }
    Ok(LinkView::Fragment(Fragment { index, count, total_len, packet_id, payload }))
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FecShardPhase { StreamingSource, FinalSource, FinalParity }
#[derive(Debug, PartialEq, Eq)]
pub struct FecHeader {
    pub block_id: u32,
    pub shard_index: u8,
    pub parity_count: u8,
    pub data_count: u8,
    pub shard_size: u16,
    pub lengths: [u16; FEC_DATA_SHARDS],
    pub phase: FecShardPhase,
}
#[derive(Debug, PartialEq, Eq)]
pub struct FecView<'a> {
    pub header: FecHeader,
    /// Merely an opaque shard body, NOT a recovered or authenticated business packet.
    pub shard: &'a [u8],
}
/// Inspect 56B wire format from pinned old Go FEC. Streaming source flags==1
/// are provisional: only the source's own original length is authoritative.
/// Final parity metadata becomes authoritative only in the authenticated
/// owner after checking block identity, epoch, profile, and retained shards.
pub fn inspect_fec_header(wire: &[u8]) -> Result<FecHeader, WireError> {
    if wire.len() < FEC_HEADER { return Err(WireError::InvalidLength); }
    if &wire[0..2] != b"WF" || wire[2] != 1 || wire[3] != 0 {
        return Err(WireError::InvalidHeader);
    }
    if wire[9] as usize != FEC_DATA_SHARDS || !FEC_PARITY_PROFILES.contains(&wire[10]) {
        return Err(WireError::InvalidHeader);
    }
    let index = wire[8];
    let count = wire[11];
    let shard_size = be16(&wire[12..14]);
    let flags = be16(&wire[14..16]);
    if count == 0 || count as usize > FEC_DATA_SHARDS || shard_size == 0
       || index as usize >= FEC_DATA_SHARDS + wire[10] as usize {
        return Err(WireError::InvalidShard);
    }
    let phase = match flags {
        1 if (index as usize) < FEC_DATA_SHARDS => FecShardPhase::StreamingSource,
        0 if (index as usize) < FEC_DATA_SHARDS => FecShardPhase::FinalSource,
        0 => FecShardPhase::FinalParity,
        _ => return Err(WireError::InvalidHeader),
    };
    let mut lengths = [0_u16; FEC_DATA_SHARDS];
    for (i, length) in lengths.iter_mut().enumerate() {
        *length = be16(&wire[16+i*2..18+i*2]);
    }
    match phase {
        FecShardPhase::StreamingSource => {
            if count as usize != FEC_DATA_SHARDS {
                return Err(WireError::InvalidShard);
            }
            for (i, len) in lengths.iter().enumerate() {
                if (i == index as usize && *len != shard_size)
                    || (i != index as usize && *len != 0) {
                    return Err(WireError::InvalidShard);
                }
            }
        }
        _ => {
            for (i, len) in lengths.iter().enumerate() {
                if (i >= count as usize && *len != 0)
                    || (i < count as usize && *len > shard_size) {
                    return Err(WireError::InvalidShard);
                }
            }
        }
    }
    Ok(FecHeader { block_id:be32(&wire[4..8]), shard_index:index,
       parity_count:wire[10], data_count:count, shard_size, lengths, phase })
}
pub fn inspect_fec_frame(wire: &[u8], mtu: usize) -> Result<FecView<'_>, WireError> {
    if mtu < FEC_HEADER + 1 { return Err(WireError::InvalidBudget); }
    if wire.len() > mtu { return Err(WireError::InvalidLength); }
    let header = inspect_fec_header(wire)?;
    if wire.len() != FEC_HEADER + header.shard_size as usize {
        return Err(WireError::InvalidLength);
    }
    Ok(FecView { header, shard:&wire[FEC_HEADER..] })
}

#[cfg(test)]
mod tests {
    use super::*;
    const FIXTURE: &str = include_str!("../../../r0/fixtures/legacy-link-fec-wire-v1.txt");
    fn from_hex(s: &str) -> Vec<u8> {
        assert_eq!(s.len()%2,0);
        (0..s.len()).step_by(2).map(|i|u8::from_str_radix(&s[i..i+2],16).unwrap()).collect()
    }
    fn v(name: &str) -> Vec<u8> {
        FIXTURE.lines().filter(|s| !s.starts_with('#') && !s.is_empty())
            .map(|s|s.split('|').collect::<Vec<_>>()).find(|x|x[0]==name)
            .map(|x|from_hex(x[1])).expect("pinned Go wire case")
    }
    #[test]
    fn r0_l01_pinned_go_mtu_minus_equal_plus_one_exact_link_bytes() {
        let payload=vec![0x5a;65];
        for n in [63,64] {
            let emitted=fragment_compat(&payload[..n],64,LinkMode::FixedOff,1).unwrap();
            assert_eq!(emitted,vec![payload[..n].to_vec()]);
            assert_eq!(inspect_link(&emitted[0],64,LinkMode::FixedOff),
                       Ok(LinkView::Ordinary(&payload[..n])));
        }
        let parts=fragment_compat(&payload,64,LinkMode::FixedOff,1).unwrap();
        assert_eq!(parts,vec![v("link64-first"),v("link64-last")]);
        assert_eq!((parts[0].len(),parts[1].len()),(64,41));
        for (i,frame) in parts.iter().enumerate() {
            match inspect_link(frame,64,LinkMode::FixedOff).unwrap() {
                LinkView::Fragment(f) => {
                    assert_eq!((f.index,f.count,f.total_len,f.packet_id),
                               (i as u16,2,65,1));
                    assert_eq!(f.payload, &payload[i*44..(i*44+f.payload.len())]);
                }
                _ => panic!("escaped fragment silently treated as ordinary"),
            }
        }
    }
    #[test]
    fn r0_l01_magic_and_wf_escape_exact_old_go_wire_modes() {
        let magic=b"WBDLFRG1";
        let a=fragment_compat(magic,64,LinkMode::FixedOff,1).unwrap();
        assert_eq!(a,vec![v("link-magic-escaped")]);
        assert!(matches!(inspect_link(&a[0],64,LinkMode::FixedOff),Ok(LinkView::Fragment(_))));
        let wf=b"WF!";
        assert_eq!(fragment_compat(wf,64,LinkMode::FixedOff,1),Ok(vec![wf.to_vec()]));
        let b=fragment_compat(wf,64,LinkMode::AdaptiveOff,1).unwrap();
        assert_eq!(b,vec![v("link-wf-escaped")]);
        assert!(matches!(inspect_link(wf,64,LinkMode::AdaptiveOff),Err(WireError::InvalidMode)));
        assert!(matches!(inspect_link(wf,64,LinkMode::FixedOff),Ok(LinkView::Ordinary(_))));
    }
    #[test]
    fn r0_l01_invalid_index_count_total_id_flags_and_truncation_reject() {
        let good=v("link64-first");
        for end in 8..21 {
            assert!(inspect_link(&good[..end],64,LinkMode::FixedOff).is_err(),"end {end}");
        }
        for (off,val) in [(8,2),(9,1),(10,1),(11,2),(13,0),(15,0),(19,0)] {
            let mut corrupted=good.clone();
            corrupted[off]=val;
            // packet_id=1 requires wiping last byte to become 0
            assert!(inspect_link(&corrupted,64,LinkMode::FixedOff).is_err(),"offset {off}");
        }
        assert!(matches!(inspect_link(&good,63,LinkMode::FixedOff),Err(WireError::InvalidLength)));
        assert!(matches!(inspect_link(&[],64,LinkMode::FixedOff),Err(WireError::InvalidLength)));
        assert!(matches!(fragment_compat(b"x",20,LinkMode::FixedOff,1),Err(WireError::InvalidBudget)));
        assert!(matches!(fragment_compat(&vec![7;65536],1400,LinkMode::FixedOff,1),Err(WireError::PacketTooLarge)));
    }
    #[test]
    fn r0_l01_fragment_max_length_65535_and_zero_or_invalid_budget() {
        let max=vec![0x6a;65_535];
        let frames=fragment_compat(&max,1400,LinkMode::FixedOff,9).unwrap();
        assert_eq!(frames.len(),48);
        assert!(frames.iter().all(|f|f.len()<=1400));
        let first=inspect_link(&frames[0],1400,LinkMode::FixedOff).unwrap();
        let last=inspect_link(frames.last().unwrap(),1400,LinkMode::FixedOff).unwrap();
        match (first,last) {
            (LinkView::Fragment(a),LinkView::Fragment(b)) => {
                assert_eq!((a.count,b.index,a.total_len),(48,47,65_535));
                assert_eq!((a.packet_id,b.packet_id),(9,9));
            }
            _ => panic!("missing header"),
        }
        assert_eq!(fragment_compat(b"WBDLFRG1",64,LinkMode::FixedOff,0),
                   Err(WireError::InvalidFragment));
        assert_eq!(fragment_compat(&[],64,LinkMode::FixedOff,1),Err(WireError::PacketTooLarge));
    }
    #[test]
    fn r0_fec_go_streaming_header_56b_exact_and_small_mtu_boundary() {
        let real=v("fec-source");
        assert_eq!(real.len(),59);
        let x=inspect_fec_frame(&real,59).unwrap();
        assert_eq!(x.header.block_id,0x01020304);
        assert_eq!((x.header.shard_index,x.header.data_count,x.header.parity_count),(0,20,4));
        assert_eq!(x.header.phase,FecShardPhase::StreamingSource);
        assert_eq!(x.header.lengths[0],3);
        assert!(x.header.lengths[1..].iter().all(|p|*p==0));
        assert_eq!(x.shard,&[0xaa,0xbb,0xcc]);
        assert_eq!(inspect_fec_frame(&real,58),Err(WireError::InvalidLength));
        assert_eq!(inspect_fec_frame(&real[..58],59),Err(WireError::InvalidLength));
        assert_eq!(inspect_fec_frame(&real,56),Err(WireError::InvalidBudget));
    }
    #[test]
    fn r0_fec_go_final_parity_header_only_profile_and_length() {
        let header=v("fec-final-parity-header-only");
        assert_eq!(header.len(),FEC_HEADER);
        let h=inspect_fec_header(&header).unwrap();
        assert_eq!(h.phase,FecShardPhase::FinalParity);
        assert_eq!((h.block_id,h.shard_index,h.parity_count,h.data_count,h.shard_size),
                   (0x01020304,20,4,1,3));
        assert_eq!((h.lengths[0],h.lengths[1]),(3,0));
        // Synthetic body only checks frame layout; it is NOT claimed as
        // genuine old-Go parity, GF generator, decoding or recovered payload.
        let mut framed=header.clone();
        framed.extend_from_slice(&[0,0,0]);
        assert_eq!(inspect_fec_frame(&framed,59).unwrap().shard,&[0,0,0]);
        framed.push(0);
        assert_eq!(inspect_fec_frame(&framed,60),Err(WireError::InvalidLength));
    }
    #[test]
    fn r0_fec_reject_incompatible_headers_profile_flags_lengths() {
        let good=v("fec-source");
        let mut f=good.clone();
        for (off,val) in [(0,0),(2,2),(3,1),(9,19),(10,5),(11,0),(12,1),(13,0),
                          (14,1),(15,2),(16,1),(17,4),(18,1),(35,1)] {
            f.copy_from_slice(&good);
            f[off]=val;
            assert!(inspect_fec_frame(&f,59).is_err(),"bad FEC field at {off}");
        }
        let final_header=v("fec-final-parity-header-only");
        let mut parity=final_header.clone();
        parity[8]=24; // 20 data + configured parity=4, index24 invalid
        assert_eq!(inspect_fec_header(&parity),Err(WireError::InvalidShard));
    }
}

// R1 tests are scoped under LINK so R0 legacy codec --skip link_fec_wire::
// still runs EXACTLY its historical 13-test list, without root CI edits.
#[cfg(test)]
#[path = "path_budget_tests.rs"]
mod path_budget_tests;
