//! R0 structural *opaque* TLS-like record framing. Only the real authenticated
//! Rust record open path may unmask PN, decode kind or release payload.
//! Equivalent outer layout to pinned Go internal/tlsrecord/record.go at
//! a7a82db31fe736ffedee330795a3234d358f1984. No AEAD, HP or plaintext.
#![forbid(unsafe_code)]

pub const OUTER_HEADER_LEN: usize = 5;
pub const PROTECTED_PN_LEN: usize = 8;
pub const AEAD_TAG_LEN: usize = 16;
pub const PLAIN_FIXED_LEN: usize = 2; // authenticated kind + inner marker
pub const MIN_BODY_LEN: usize = PROTECTED_PN_LEN + AEAD_TAG_LEN + PLAIN_FIXED_LEN; // 26
pub const FIXED_WIRE_OVERHEAD: usize = OUTER_HEADER_LEN + MIN_BODY_LEN; // 31
pub const MAX_BODY_LEN: usize = (1 << 14) + 256; // 16640
pub const MAX_WIRE_LEN: usize = OUTER_HEADER_LEN + MAX_BODY_LEN; // 16645
pub const OUTER_TYPE: u8 = 0x17;
pub const OUTER_VERSION: [u8; 2] = [0x03, 0x03];
/// *After successful authentication only*: plaintext[0] holds kind (0/1),
/// plaintext[1..] holds payload + inner marker 0x17 + zero padding.
/// The kind cannot be read from this framing view.
pub const AUTHENTICATED_KIND_OFFSET: usize = 0;
pub const AUTHENTICATED_LINK_KIND: u8 = 0;
pub const AUTHENTICATED_HEALTH_KIND: u8 = 1;

#[derive(Debug, Clone, Copy, Eq, PartialEq)]
pub enum FrameError {
    InvalidWireLimit,
    TruncatedHeader,
    InvalidLength,
    TruncatedBody,
    UnexpectedOuterType,
    UnexpectedOuterVersion,
    BudgetExceeded,
}

/// This view grants NO authentication and NO PN/kind information. Protected
/// PN bytes must not be used for replay, dedup, routing or delivery.
#[derive(Debug)]
pub struct OpaqueFrame<'a> {
    pub wire: &'a [u8],
    pub outer_header: &'a [u8],
    pub protected_pn: &'a [u8],
    pub ciphertext_and_tag: &'a [u8],
    /// HP uses the first 16B of ciphertext_and_tag; sample may include tag.
    pub hp_sample: &'a [u8],
    /// Last 16 bytes are opaque until AEAD validates them.
    pub tag_bytes: &'a [u8],
}

fn max_body(max_wire: usize) -> Result<usize, FrameError> {
    if max_wire < FIXED_WIRE_OVERHEAD {
        return Err(FrameError::InvalidWireLimit);
    }
    Ok((max_wire - OUTER_HEADER_LEN).min(MAX_BODY_LEN))
}

/// Generates only the unprotected *outer* header given a known sealed body
/// length. Does NOT produce a valid record and cannot seal any plaintext.
pub fn outer_header_for_body(body_len: usize, max_wire: usize) -> Result<[u8; 5], FrameError> {
    let max = max_body(max_wire)?;
    if body_len < MIN_BODY_LEN || body_len > max {
        return Err(FrameError::BudgetExceeded);
    }
    let b = (body_len as u16).to_be_bytes();
    Ok([OUTER_TYPE, OUTER_VERSION[0], OUTER_VERSION[1], b[0], b[1]])
}

/// Parse EXACTLY one framing boundary, returning remaining bytes without
/// scanning for magic or delivering content. Length inconsistency is terminal:
/// callers must drop the remaining stream, not search for the next 0x17.
/// A well-framed record is NOT a successfully authenticated record.
pub fn split_one(input: &[u8], max_wire: usize) -> Result<(OpaqueFrame<'_>, &[u8]), FrameError> {
    let max = max_body(max_wire)?;
    if input.len() < OUTER_HEADER_LEN {
        return Err(FrameError::TruncatedHeader);
    }
    let body = u16::from_be_bytes([input[3], input[4]]) as usize;
    if body < MIN_BODY_LEN || body > max {
        return Err(FrameError::InvalidLength);
    }
    let total = OUTER_HEADER_LEN + body;
    if input.len() < total {
        return Err(FrameError::TruncatedBody);
    }
    if input[0] != OUTER_TYPE {
        return Err(FrameError::UnexpectedOuterType);
    }
    if input[1..3] != OUTER_VERSION {
        return Err(FrameError::UnexpectedOuterVersion);
    }
    let wire = &input[..total];
    let encrypted_offset = OUTER_HEADER_LEN + PROTECTED_PN_LEN;
    let opaque = &wire[encrypted_offset..];
    let frame = OpaqueFrame {
        wire,
        outer_header: &wire[..OUTER_HEADER_LEN],
        protected_pn: &wire[OUTER_HEADER_LEN..encrypted_offset],
        ciphertext_and_tag: opaque,
        hp_sample: &opaque[..AEAD_TAG_LEN], // min two encrypted plain bytes + 16 tag
        tag_bytes: &opaque[opaque.len()-AEAD_TAG_LEN..],
    };
    Ok((frame, &input[total..]))
}

#[cfg(test)]
#[path = "fec_v2_tests.rs"]
mod fec_v2_oracle_tests;

#[cfg(test)]
mod tests {
    use super::*;
    const OLD_GO_FIXTURE: &str = include_str!("../../../r0/fixtures/legacy-record-wire-v1.txt");

    fn from_hex(s: &str) -> Vec<u8> {
        assert_eq!(s.len()%2,0);
        (0..s.len()).step_by(2).map(|i| u8::from_str_radix(&s[i..i+2],16).unwrap()).collect()
    }
    struct Oracle {
        name: String,
        pn: u64,
        kind: u8,
        padding: usize,
        payload: Vec<u8>,
        wire: Vec<u8>,
    }
    fn vectors() -> Vec<Oracle> {
        let mut cases = Vec::new();
        for line in OLD_GO_FIXTURE.lines().filter(|x| !x.is_empty() && !x.starts_with('#')) {
            let a:Vec<_> = line.split('|').collect();
            assert_eq!(a.len(),6);
            cases.push(Oracle { name:a[0].into(), pn:a[1].parse().unwrap(),
                kind:a[2].parse().unwrap(), padding:a[3].parse().unwrap(),
                payload:from_hex(a[4]), wire:from_hex(a[5]) });
        }
        assert_eq!(cases.len(),6);
        cases
    }
    #[test]
    fn r0_record_pinned_go_six_real_wire_oracles_have_exact_offsets() {
        for c in vectors() {
            assert_eq!(c.kind,AUTHENTICATED_LINK_KIND);
            let (f,tail)=split_one(&c.wire,MAX_WIRE_LEN).unwrap();
            assert!(tail.is_empty(), "{}",c.name);
            assert_eq!(f.wire,c.wire.as_slice());
            assert_eq!(f.outer_header.len(),5);
            assert_eq!(f.protected_pn.len(),8);
            assert_eq!(f.ciphertext_and_tag.len(),c.payload.len()+c.padding+PLAIN_FIXED_LEN+AEAD_TAG_LEN);
            assert_eq!(f.hp_sample,&c.wire[13..29]);
            assert_eq!(f.tag_bytes,&c.wire[c.wire.len()-16..]);
            assert_eq!(f.protected_pn,&c.wire[5..13]);
            assert_eq!(outer_header_for_body(c.wire.len()-5,MAX_WIRE_LEN).unwrap().as_slice(),&c.wire[0..5]);
            assert_eq!(c.wire.len(),FIXED_WIRE_OVERHEAD+c.payload.len()+c.padding);
            assert!(c.pn==0 || c.pn==1 || c.pn==4294967297 || c.pn==u64::MAX-1 ||
                    c.pn==u64::MAX || c.pn==7);
        }
    }
    #[test]
    fn r0_record_multi_frame_opaque_prefix_no_delivery_or_magic_scan() {
        let all=vectors();
        let mut stream=Vec::new();
        for x in [&all[2],&all[0],&all[5]] { stream.extend_from_slice(&x.wire); }
        let (a,rest)=split_one(&stream,MAX_WIRE_LEN).unwrap();
        assert_eq!(a.wire,all[2].wire);
        let (b,rest)=split_one(rest,MAX_WIRE_LEN).unwrap();
        assert_eq!(b.wire,all[0].wire);
        let (c,rest)=split_one(rest,MAX_WIRE_LEN).unwrap();
        assert_eq!(c.wire,all[5].wire);
        assert!(rest.is_empty());
        let mut malicious=vec![0x17,0x03,0x03,0x00,0x01];
        malicious.extend_from_slice(&all[1].wire);
        assert!(matches!(split_one(&malicious,MAX_WIRE_LEN),Err(FrameError::InvalidLength)));
        assert!(matches!(split_one(&malicious[1..],MAX_WIRE_LEN),Err(FrameError::InvalidLength)|Err(FrameError::TruncatedBody)));
    }
    #[test]
    fn r0_record_zero_to_minimum_and_all_truncated_prefixes_fail_closed() {
        let minimum=&vectors()[0].wire;
        assert_eq!(minimum.len(),31);
        for end in 0..minimum.len() {
            let result=split_one(&minimum[..end],MAX_WIRE_LEN);
            assert!(result.is_err(),"prefix {end} accepted");
        }
        assert_eq!(split_one(minimum,30).unwrap_err(),FrameError::InvalidWireLimit);
        assert_eq!(split_one(minimum,31).unwrap().0.wire,minimum);
        assert_eq!(outer_header_for_body(26,31),Ok([0x17,0x03,0x03,0x00,0x1a]));
        assert_eq!(outer_header_for_body(25,31),Err(FrameError::BudgetExceeded));
        assert_eq!(outer_header_for_body(27,31),Err(FrameError::BudgetExceeded));
    }
    #[test]
    fn r0_record_header_type_version_length_and_wire_budget_reject() {
        let sample=vectors()[1].wire.clone();
        for (i,value,err) in [(0,0,FrameError::UnexpectedOuterType),
            (1,0,FrameError::UnexpectedOuterVersion),(2,4,FrameError::UnexpectedOuterVersion),
            (3,0x7f,FrameError::InvalidLength),(4,0,FrameError::InvalidLength)] {
            let mut invalid=sample.clone(); invalid[i]=value;
            assert_eq!(split_one(&invalid,MAX_WIRE_LEN).unwrap_err(),err,"offset {i}");
        }
        let mut tiny=sample.clone();
        tiny[3]=0; tiny[4]=25;
        assert_eq!(split_one(&tiny,MAX_WIRE_LEN).unwrap_err(),FrameError::InvalidLength);
        assert_eq!(split_one(&sample,35).unwrap_err(),FrameError::InvalidLength);
        assert_eq!(outer_header_for_body(MAX_BODY_LEN,MAX_WIRE_LEN),
            Ok([0x17,0x03,0x03,0x41,0x00]));
        assert_eq!(outer_header_for_body(MAX_BODY_LEN+1,usize::MAX),Err(FrameError::BudgetExceeded));
    }
    #[test]
    fn r0_record_hp_sample_can_overlap_tag_of_short_record() {
        let v=vectors();
        let f=split_one(&v[0].wire,MAX_WIRE_LEN).unwrap().0;
        assert_eq!(f.ciphertext_and_tag.len(),18); // two encrypted plain bytes + 16 tag
        assert_eq!(f.hp_sample.len(),16);
        assert_eq!(f.hp_sample,&v[0].wire[13..29]);
        assert_eq!(&f.hp_sample[2..],&f.tag_bytes[..14]);
        // This is opaque ciphertext only: no PN, inner-kind or deliverable payload.
    }
    #[test]
    fn r0_record_kind_is_encrypted_not_a_wire_field_and_pn_is_masked() {
        let v=vectors();
        for c in &v {
            let f=split_one(&c.wire,MAX_WIRE_LEN).unwrap().0;
            assert_eq!(AUTHENTICATED_KIND_OFFSET,0);
            assert_eq!(AUTHENTICATED_LINK_KIND,0);
            assert_eq!(AUTHENTICATED_HEALTH_KIND,1);
            assert_ne!(f.protected_pn,c.pn.to_be_bytes().as_slice());
            assert_eq!(f.ciphertext_and_tag.len(),c.payload.len()+c.padding+18);
        }
    }
}

// Worker R1 real-crypto tests are scoped beneath record_frame so the frozen
// historical R0 wire-codec --skip record_frame:: remains exactly 13 tests.
#[cfg(test)]
#[path = "record_crypto_tests.rs"]
mod record_crypto_tests;

// R1 replay verification belongs to the record_frame:: namespace, ensuring
// frozen legacy R0 codec still selects the same historical 13 wire tests.
#[cfg(test)]
#[path = "record_replay_tests.rs"]
mod record_replay_tests;
