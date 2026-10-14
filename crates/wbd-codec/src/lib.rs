//! R0 V4 **wire-only** codecs. Not AEAD, authenticated receipt handling,
//! a Game pipeline, an ABI, or a signal to enable production V4.
//! Byte offsets follow modules/00-CONTRACTS.md and modules/08-RECOVERY.md;
//! never serialize native Rust/C structs as protocol bytes.
#![forbid(unsafe_code)]

/// R0 opaque TLS-like record structural segmentation (not authentication).
pub mod record_frame;

use wbd_types::LogicalPacketId;

const CONTROL_MAGIC: &[u8; 4] = b"WBC4";
const GAME_MAGIC: &[u8; 4] = b"WBG4";
const CONTROL_SCHEMA: u8 = 1;
const CONTROL_HEADER: usize = 8;
const TLV_HEADER: usize = 4;
const RECEIPT_FIXED: usize = 20;
const RECEIPT_PAGE: usize = 40;
const GAME_HEADER: usize = 16;
pub const MAX_TLVS: usize = 8;
pub const MAX_RECEIPT_PAGES: usize = 8;
pub const MAX_ACK_DELAY_US: u32 = 10_000;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CodecError {
    Truncated,
    BadMagic,
    BadSchema,
    UnsupportedType,
    NonzeroFlags,
    InvalidLength,
    DuplicateReceipt,
    InvalidReceipt,
    BudgetExceeded,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ReceiptPage {
    pub base_pn: u64,
    /// 256 PNs, bit 0 is the least significant bit of bitmap[0].
    pub bitmap: [u8; 32],
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Receipt {
    pub largest_data_pn: u64,
    pub ack_delay_us: u32,
    pub report_seq: u32,
    pub pages: Vec<ReceiptPage>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ControlTlv {
    Receipt(Receipt),
    LegacyHealth(Vec<u8>),
    LegacyQuality(Vec<u8>),
}

fn be_u16(b: &[u8]) -> u16 {
    u16::from_be_bytes([b[0], b[1]])
}
fn be_u32(b: &[u8]) -> u32 {
    u32::from_be_bytes([b[0], b[1], b[2], b[3]])
}
fn be_u64(b: &[u8]) -> u64 {
    u64::from_be_bytes([b[0], b[1], b[2], b[3], b[4], b[5], b[6], b[7]])
}

fn validate_receipt(r: &Receipt) -> Result<(), CodecError> {
    if r.pages.len() > MAX_RECEIPT_PAGES || r.ack_delay_us > MAX_ACK_DELAY_US {
        return Err(CodecError::InvalidReceipt);
    }
    for (i, page) in r.pages.iter().enumerate() {
        if page.base_pn % 256 != 0 || page.base_pn > r.largest_data_pn ||
            r.pages[..i].iter().any(|before| before.base_pn == page.base_pn)
        {
            return Err(CodecError::InvalidReceipt);
        }
        for (byte, bits) in page.bitmap.iter().enumerate() {
            if *bits == 0 { continue; }
            for bit in 0..8_usize {
                if (*bits & (1_u8 << bit)) == 0 { continue; }
                let offset = (byte * 8 + bit) as u64;
                match page.base_pn.checked_add(offset) {
                    Some(pn) if pn <= r.largest_data_pn => {},
                    _ => return Err(CodecError::InvalidReceipt),
                }
            }
        }
    }
    Ok(())
}

fn encode_receipt(r: &Receipt) -> Result<Vec<u8>, CodecError> {
    validate_receipt(r)?;
    let mut out = Vec::with_capacity(RECEIPT_FIXED + RECEIPT_PAGE * r.pages.len());
    out.extend_from_slice(&r.largest_data_pn.to_be_bytes()); // offsets 0..8
    out.extend_from_slice(&r.ack_delay_us.to_be_bytes());    // offsets 8..12
    out.extend_from_slice(&r.report_seq.to_be_bytes());      // offsets 12..16
    out.push(r.pages.len() as u8);                            // offset 16
    out.push(0);                                              // flags at 17
    out.extend_from_slice(&[0, 0]);                           // reserved at 18..20
    for page in &r.pages {
        out.extend_from_slice(&page.base_pn.to_be_bytes());
        out.extend_from_slice(&page.bitmap);
    }
    Ok(out)
}

fn decode_receipt(data: &[u8]) -> Result<Receipt, CodecError> {
    if data.len() < RECEIPT_FIXED { return Err(CodecError::InvalidLength); }
    let pages = data[16] as usize;
    if pages > MAX_RECEIPT_PAGES { return Err(CodecError::InvalidReceipt); }
    if data[17..20] != [0, 0, 0] { return Err(CodecError::NonzeroFlags); }
    if data.len() != RECEIPT_FIXED + RECEIPT_PAGE * pages {
        return Err(CodecError::InvalidLength);
    }
    let mut entries = Vec::with_capacity(pages);
    for i in 0..pages {
        let at = RECEIPT_FIXED + i * RECEIPT_PAGE;
        let mut bitmap = [0_u8; 32];
        bitmap.copy_from_slice(&data[at + 8..at + 40]);
        entries.push(ReceiptPage { base_pn: be_u64(&data[at..at + 8]), bitmap });
    }
    let result = Receipt {
        largest_data_pn: be_u64(&data[0..8]),
        ack_delay_us: be_u32(&data[8..12]),
        report_seq: be_u32(&data[12..16]),
        pages: entries,
    };
    validate_receipt(&result)?;
    Ok(result)
}

/// Caller supplies effective maximum record payload bytes; this function
/// cannot infer MTU/AEAD framing. It does not reserve a PN or transmit.
pub fn encode_control(tlvs: &[ControlTlv], budget: usize) -> Result<Vec<u8>, CodecError> {
    if tlvs.len() > MAX_TLVS { return Err(CodecError::InvalidLength); }
    let mut out = vec![0_u8; CONTROL_HEADER];
    let mut saw_receipt = false;
    for tlv in tlvs {
        let (kind, value) = match tlv {
            ControlTlv::Receipt(r) => {
                if saw_receipt { return Err(CodecError::DuplicateReceipt); }
                saw_receipt = true;
                (1_u8, encode_receipt(r)?)
            },
            ControlTlv::LegacyHealth(data) => (2_u8, data.clone()),
            ControlTlv::LegacyQuality(data) => (3_u8, data.clone()),
        };
        if value.len() > u16::MAX as usize { return Err(CodecError::InvalidLength); }
        let total = out.len().checked_add(TLV_HEADER).and_then(|v| v.checked_add(value.len()))
            .ok_or(CodecError::InvalidLength)?;
        if total > u16::MAX as usize { return Err(CodecError::InvalidLength); }
        if total > budget { return Err(CodecError::BudgetExceeded); }
        out.push(kind);
        out.push(0); // TLV flags
        out.extend_from_slice(&(value.len() as u16).to_be_bytes());
        out.extend_from_slice(&value);
    }
    if out.len() > budget { return Err(CodecError::BudgetExceeded); }
    out[0..4].copy_from_slice(CONTROL_MAGIC);
    out[4] = CONTROL_SCHEMA;
    out[5] = tlvs.len() as u8;
    let length = u16::try_from(out.len()).map_err(|_| CodecError::InvalidLength)?;
    out[6..8].copy_from_slice(&length.to_be_bytes());
    Ok(out)
}

/// Parses only the explicitly negotiated V4 control format, never V3 health
/// by magic sniffing; authentication/epoch scope must be enforced by caller.
pub fn decode_control(input: &[u8], budget: usize) -> Result<Vec<ControlTlv>, CodecError> {
    if input.len() > budget { return Err(CodecError::BudgetExceeded); }
    if input.len() < CONTROL_HEADER { return Err(CodecError::Truncated); }
    if &input[0..4] != CONTROL_MAGIC { return Err(CodecError::BadMagic); }
    if input[4] != CONTROL_SCHEMA { return Err(CodecError::BadSchema); }
    let count = input[5] as usize;
    if count > MAX_TLVS { return Err(CodecError::InvalidLength); }
    if be_u16(&input[6..8]) as usize != input.len() {
        return Err(CodecError::InvalidLength);
    }
    let mut cursor = CONTROL_HEADER;
    let mut result = Vec::with_capacity(count);
    let mut saw_receipt = false;
    for _ in 0..count {
        if input.len() - cursor < TLV_HEADER { return Err(CodecError::Truncated); }
        let kind = input[cursor];
        let flags = input[cursor + 1];
        let value_len = be_u16(&input[cursor + 2..cursor + 4]) as usize;
        if flags != 0 { return Err(CodecError::NonzeroFlags); }
        cursor += TLV_HEADER;
        if input.len() - cursor < value_len { return Err(CodecError::InvalidLength); }
        let data = &input[cursor..cursor + value_len];
        let tlv = match kind {
            1 => {
                if saw_receipt { return Err(CodecError::DuplicateReceipt); }
                saw_receipt = true;
                ControlTlv::Receipt(decode_receipt(data)?)
            },
            2 => ControlTlv::LegacyHealth(data.to_vec()),
            3 => ControlTlv::LegacyQuality(data.to_vec()),
            _ => return Err(CodecError::UnsupportedType),
        };
        result.push(tlv);
        cursor += value_len;
    }
    if cursor != input.len() { return Err(CodecError::InvalidLength); }
    Ok(result)
}

/// WBG4 goes before LINK fragmentation/FEC, with a shared logical packet ID.
/// This is a wire codec, not a cross-lane deduplicator or authentication step.
pub fn encode_game(
    id: LogicalPacketId, payload: &[u8], budget: usize,
) -> Result<Vec<u8>, CodecError> {
    if payload.len() > u16::MAX as usize { return Err(CodecError::InvalidLength); }
    let total = GAME_HEADER.checked_add(payload.len()).ok_or(CodecError::InvalidLength)?;
    if total > budget { return Err(CodecError::BudgetExceeded); }
    let mut out = Vec::with_capacity(total);
    out.extend_from_slice(GAME_MAGIC);                     // 0..4
    out.extend_from_slice(&id.0.to_be_bytes());             // 4..12
    out.extend_from_slice(&(payload.len() as u16).to_be_bytes()); // 12..14
    out.extend_from_slice(&[0, 0]);                         // flags at 14..16
    out.extend_from_slice(payload);
    Ok(out)
}

/// Borrows a payload only from the exact validated full frame. A bad length,
/// unknown flags or excessive budget returns no deliverable payload.
pub fn decode_game(input: &[u8], budget: usize) -> Result<(LogicalPacketId, &[u8]), CodecError> {
    if input.len() > budget { return Err(CodecError::BudgetExceeded); }
    if input.len() < GAME_HEADER { return Err(CodecError::Truncated); }
    if &input[0..4] != GAME_MAGIC { return Err(CodecError::BadMagic); }
    if input[14] != 0 || input[15] != 0 { return Err(CodecError::NonzeroFlags); }
    let payload_len = be_u16(&input[12..14]) as usize;
    if input.len() != GAME_HEADER + payload_len { return Err(CodecError::InvalidLength); }
    Ok((LogicalPacketId(be_u64(&input[4..12])), &input[16..]))
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Independent hand-written byte constants, NOT bytes derived from encode.
    const GOLDEN_RECEIPT: [u8; 72] = [
        0x57,0x42,0x43,0x34, 0x01,0x01,0x00,0x48, // WBC4 + schema,count,total
        0x01,0x00,0x00,0x3c, // receipt, flags0, value_len60
        0x00,0x00,0x00,0x00,0x00,0x00,0x01,0x02, // largest 258
        0x00,0x00,0x09,0xc4, // ack delay 2500us
        0x00,0x00,0x00,0x07, // report_seq 7
        0x01,0x00,0x00,0x00, // page_count 1 flags0 reserved0
        0x00,0x00,0x00,0x00,0x00,0x00,0x01,0x00, // base 256
        0x05,0x00,0x00,0x00,0x00,0x00,0x00,0x00, // PN 256 and 258
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    ];
    const GOLDEN_LEGACY_TLVS: [u8; 21] = [
        0x57,0x42,0x43,0x34,0x01,0x02,0x00,0x15,
        0x02,0x00,0x00,0x02,0xaa,0x55,
        0x03,0x00,0x00,0x03,0x01,0x02,0x03,
    ];
    const GOLDEN_GAME: [u8; 19] = [
        0x57,0x42,0x47,0x34,
        0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,
        0x00,0x03,0x00,0x00,0xde,0xad,0xbe,
    ];

    fn example_receipt() -> Receipt {
        let mut bitmap = [0; 32];
        bitmap[0] = 5;
        Receipt {
            largest_data_pn: 258, ack_delay_us: 2_500, report_seq: 7,
            pages: vec![ReceiptPage { base_pn: 256, bitmap }],
        }
    }
    fn byte_mutated(source: &[u8], at: usize, value: u8) -> Vec<u8> {
        let mut bytes = source.to_vec();
        bytes[at] = value;
        bytes
    }

    #[test]
    fn r0_wbc4_golden_receipt_exact_wire_and_roundtrip() {
        let r = example_receipt();
        let input = [ControlTlv::Receipt(r.clone())];
        assert_eq!(encode_control(&input, 72).unwrap().as_slice(), GOLDEN_RECEIPT);
        assert_eq!(decode_control(&GOLDEN_RECEIPT, 72).unwrap(), input);
        assert_eq!(encode_control(&decode_control(&GOLDEN_RECEIPT, 72).unwrap(), 72).unwrap(), GOLDEN_RECEIPT);
    }
    #[test]
    fn r0_wbc4_golden_legacy_tlv_bytes_not_v3_sniffing() {
        let list = [
            ControlTlv::LegacyHealth(vec![0xaa, 0x55]),
            ControlTlv::LegacyQuality(vec![1, 2, 3]),
        ];
        assert_eq!(encode_control(&list, 21).unwrap(), GOLDEN_LEGACY_TLVS);
        assert_eq!(decode_control(&GOLDEN_LEGACY_TLVS, 21).unwrap(), list);
        assert_eq!(decode_control(&[0; 9], 21), Err(CodecError::BadMagic));
    }
    #[test]
    fn r0_wbc4_truncated_header_or_tlv_cannot_emit_output() {
        for end in 0..GOLDEN_RECEIPT.len() {
            assert!(decode_control(&GOLDEN_RECEIPT[..end], 72).is_err(), "accepted prefix {end}");
        }
        assert_eq!(decode_control(&GOLDEN_RECEIPT, 71), Err(CodecError::BudgetExceeded));
        assert_eq!(encode_control(&[ControlTlv::Receipt(example_receipt())], 71), Err(CodecError::BudgetExceeded));
        let mut trailing=GOLDEN_RECEIPT.to_vec(); trailing.push(0);
        assert_eq!(decode_control(&trailing, 100), Err(CodecError::InvalidLength));
    }
    #[test]
    fn r0_wbc4_reject_schema_magic_declared_size_and_tlv_overflow() {
        assert_eq!(decode_control(&byte_mutated(&GOLDEN_RECEIPT, 0, 0),72),Err(CodecError::BadMagic));
        assert_eq!(decode_control(&byte_mutated(&GOLDEN_RECEIPT, 4, 2),72),Err(CodecError::BadSchema));
        for (at,v) in [(6,1),(7,71),(9,1),(10,255),(11,255)] {
            let err=decode_control(&byte_mutated(&GOLDEN_RECEIPT,at,v),72);
            assert!(err.is_err(),"field at {at} accepted");
        }
        assert_eq!(decode_control(&byte_mutated(&GOLDEN_RECEIPT,8,4),72),Err(CodecError::UnsupportedType));
        assert_eq!(decode_control(&byte_mutated(&GOLDEN_RECEIPT,9,1),72),Err(CodecError::NonzeroFlags));
    }
    #[test]
    fn r0_wbc4_reject_duplicate_receipt_and_tlv_count_over_eight() {
        let r=ControlTlv::Receipt(example_receipt());
        assert_eq!(encode_control(&[r.clone(),r.clone()],144),Err(CodecError::DuplicateReceipt));
        let two = encode_control(&[r.clone(),r], 144);
        assert_eq!(two,Err(CodecError::DuplicateReceipt));
        let too_many=vec![ControlTlv::LegacyHealth(vec![]);9];
        assert_eq!(encode_control(&too_many, 200),Err(CodecError::InvalidLength));
        assert_eq!(decode_control(&byte_mutated(&GOLDEN_RECEIPT,5,9),72),Err(CodecError::InvalidLength));
        let mut both=GOLDEN_RECEIPT.to_vec();
        both.extend_from_slice(&GOLDEN_RECEIPT[8..]);
        both[5]=2;
        both[6..8].copy_from_slice(&(136_u16).to_be_bytes());
        assert_eq!(decode_control(&both, 136),Err(CodecError::DuplicateReceipt));
    }
    #[test]
    fn r0_wbc4_receipt_page_count_flags_and_fixed_length() {
        let mut bad=GOLDEN_RECEIPT.to_vec();
        bad[28]=2; // receipt page_count offset 16 after bundle8+tlv4
        assert_eq!(decode_control(&bad,72),Err(CodecError::InvalidLength));
        bad[28]=9;
        assert_eq!(decode_control(&bad,72),Err(CodecError::InvalidReceipt));
        for offset in [29_usize,30,31] {
            assert_eq!(decode_control(&byte_mutated(&GOLDEN_RECEIPT,offset,1),72),Err(CodecError::NonzeroFlags));
        }
        let mut badlen=GOLDEN_RECEIPT.to_vec();
        badlen[11]=59; // TLV length 59, no complete page
        assert!(decode_control(&badlen,72).is_err());
    }
    #[test]
    fn r0_wbc4_receipt_bit_alignment_future_and_ack_delay_bounds() {
        let r=example_receipt();
        let mut misaligned=r.clone(); misaligned.pages[0].base_pn=257;
        assert_eq!(encode_control(&[ControlTlv::Receipt(misaligned)],100),Err(CodecError::InvalidReceipt));
        let mut future=r.clone(); future.pages[0].bitmap[0] |= 0b1000;
        assert_eq!(encode_control(&[ControlTlv::Receipt(future)],100),Err(CodecError::InvalidReceipt));
        // Decoding cannot launder forged flags or a PN beyond largest.
        assert_eq!(decode_control(&byte_mutated(&GOLDEN_RECEIPT,40,13),72),Err(CodecError::InvalidReceipt));
        let mut delay=r.clone(); delay.ack_delay_us=10_001;
        assert_eq!(encode_control(&[ControlTlv::Receipt(delay)],100),Err(CodecError::InvalidReceipt));
        let mut too_small=r; too_small.largest_data_pn=255;
        assert_eq!(encode_control(&[ControlTlv::Receipt(too_small)],100),Err(CodecError::InvalidReceipt));
    }
    #[test]
    fn r0_wbc4_receipt_duplicate_page_and_eight_page_boundary() {
        let mut r=example_receipt();
        r.pages.push(r.pages[0].clone());
        assert_eq!(encode_control(&[ControlTlv::Receipt(r.clone())],400),Err(CodecError::InvalidReceipt));
        r.pages.clear();
        r.largest_data_pn=2048;
        for i in 0..8 {
            r.pages.push(ReceiptPage {base_pn: i*256, bitmap:[0;32]});
        }
        let body=encode_control(&[ControlTlv::Receipt(r.clone())],352).unwrap();
        assert_eq!(body.len(),352); // bundle8 + TLV4 + receipt20 + 8*40
        assert_eq!(decode_control(&body,352),Ok(vec![ControlTlv::Receipt(r.clone())]));
        r.pages.push(ReceiptPage{base_pn:2048,bitmap:[0;32]});
        assert_eq!(encode_control(&[ControlTlv::Receipt(r)],4096),Err(CodecError::InvalidReceipt));
    }
    #[test]
    fn r0_wbc4_max_pn_and_max_u16_budget_do_not_wrap() {
        let mut bitmap=[0;32]; bitmap[31]=0x80; // offset255 -> u64 MAX
        let r=Receipt {
            largest_data_pn:u64::MAX,ack_delay_us:10_000,report_seq:u32::MAX,
            pages:vec![ReceiptPage{base_pn:u64::MAX-255,bitmap}],
        };
        let tlvs=[ControlTlv::Receipt(r.clone())];
        assert_eq!(decode_control(&encode_control(&tlvs,72).unwrap(),72),Ok(vec![ControlTlv::Receipt(r)]));
        let too_large = ControlTlv::LegacyHealth(vec![0xaa;u16::MAX as usize + 1]);
        assert_eq!(encode_control(&[too_large],usize::MAX),Err(CodecError::InvalidLength));
    }
    #[test]
    fn r0_wbc4_empty_and_eight_tlvs_are_bounded() {
        let empty=encode_control(&[],8).unwrap();
        assert_eq!(empty,b"WBC4\x01\x00\x00\x08");
        assert_eq!(decode_control(&empty,8),Ok(vec![]));
        let eight=vec![ControlTlv::LegacyQuality(vec![0]);8];
        assert_eq!(decode_control(&encode_control(&eight,48).unwrap(),48),Ok(eight));
    }
    #[test]
    fn r0_wbg4_golden_exact_big_endian_and_roundtrip() {
        let id=LogicalPacketId(0x0102030405060708);
        let payload=[0xde,0xad,0xbe];
        assert_eq!(encode_game(id,&payload,19),Ok(GOLDEN_GAME.to_vec()));
        assert_eq!(decode_game(&GOLDEN_GAME,19),Ok((id,payload.as_slice())));
    }
    #[test]
    fn r0_wbg4_game_reject_all_truncations_and_malformed_frames() {
        for end in 0..GOLDEN_GAME.len() {
            assert!(decode_game(&GOLDEN_GAME[..end],19).is_err(),"accepted prefix {end}");
        }
        assert_eq!(decode_game(&byte_mutated(&GOLDEN_GAME,0,0),19),Err(CodecError::BadMagic));
        assert_eq!(decode_game(&byte_mutated(&GOLDEN_GAME,14,1),19),Err(CodecError::NonzeroFlags));
        assert_eq!(decode_game(&byte_mutated(&GOLDEN_GAME,15,1),19),Err(CodecError::NonzeroFlags));
        assert_eq!(decode_game(&byte_mutated(&GOLDEN_GAME,13,4),19),Err(CodecError::InvalidLength));
        assert_eq!(decode_game(&byte_mutated(&GOLDEN_GAME,13,2),19),Err(CodecError::InvalidLength));
        let mut with_tail=GOLDEN_GAME.to_vec();with_tail.push(0);
        assert_eq!(decode_game(&with_tail,20),Err(CodecError::InvalidLength));
        assert_eq!(encode_game(LogicalPacketId(1),&[1,2,3],18),Err(CodecError::BudgetExceeded));
        assert_eq!(decode_game(&GOLDEN_GAME,18),Err(CodecError::BudgetExceeded));
    }
    #[test]
    fn r0_wbg4_zero_and_max_payload_id_preserve_bytes() {
        let zero=encode_game(LogicalPacketId(0),&[],16).unwrap();
        assert_eq!(&zero[..],b"WBG4\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00");
        assert_eq!(decode_game(&zero,16).unwrap(),(LogicalPacketId(0),&[][..]));
        let bytes=vec![0x5a;u16::MAX as usize];
        let max=encode_game(LogicalPacketId(u64::MAX),&bytes,65551).unwrap();
        assert_eq!(max.len(),65551);
        assert_eq!(&max[4..12],&u64::MAX.to_be_bytes());
        assert_eq!(&max[12..14],&u16::MAX.to_be_bytes());
        assert_eq!(decode_game(&max,65551).unwrap(),(LogicalPacketId(u64::MAX),bytes.as_slice()));
        assert_eq!(encode_game(LogicalPacketId(7),&bytes,65550),Err(CodecError::BudgetExceeded));
        assert_eq!(encode_game(LogicalPacketId(7),&vec![0;65536],65552),Err(CodecError::InvalidLength));
    }
}
