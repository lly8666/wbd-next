//! Real independent ChaCha20-Poly1305 TLS-like record Seal/Open.
//! WBD compatibility is NOT TLS: 5B outer + 8B protected PN + cipher/tag.
//! Pinned source: wobuzhidao@a7a82db31fe736ffedee330795a3234d358f1984
//! internal/tlsrecord/record.go and suite.go, real six Go wire oracles.
//! No AES suite / replay window / E2E product qualification in this atom.
#![forbid(unsafe_code)]

use aws_lc_rs::aead::{self, Aad, LessSafeKey, Nonce, UnboundKey};
use chacha20::cipher::{KeyIvInit, StreamCipher, StreamCipherSeek};
use chacha20::ChaCha20;

use crate::record_frame::{
    AEAD_TAG_LEN, AUTHENTICATED_HEALTH_KIND, AUTHENTICATED_LINK_KIND,
    FIXED_WIRE_OVERHEAD, MAX_WIRE_LEN, OUTER_HEADER_LEN, OUTER_TYPE,
    OUTER_VERSION, PLAIN_FIXED_LEN, PROTECTED_PN_LEN,
};

const CIPHER_OFFSET: usize = OUTER_HEADER_LEN + PROTECTED_PN_LEN;
const AAD_LEN: usize = OUTER_HEADER_LEN + PROTECTED_PN_LEN;
const HP_SAMPLE_LEN: usize = 16;
const INNER_MARKER: u8 = 0x17;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CryptoError {
    WireLimit,
    Capacity,
    InvalidLength,
    InvalidHeader,
    InvalidKind,
    InvalidInnerMarker,
    PnExhausted,
    Authentication,
    PrimitiveFailure,
}

/// Raw 76B direction material from the authenticated Go V4 exporter.
/// Caller MUST supply direction+suite-separated material from the trusted
/// admission; do not derive V4 keys by aliasing old V3 exporter bytes.
pub struct DirectionKeys {
    pub aead_key: [u8; 32],
    pub iv: [u8; 12],
    pub hp_key: [u8; 32],
}

/// A lane-local TX key and non-wrapping, never-rolled-back PN allocator.
/// Calling seal burns a PN even when capacity or validation later fails.
pub struct LaneTxCrypto {
    aead: LessSafeKey,
    iv: [u8; 12],
    hp_key: [u8; 32],
    max_wire: usize,
    next_pn: u64,
    exhausted: bool,
}

/// Lane-local authenticated record opener. Replay/epoch detection belongs
/// to the authenticated RX owner; this type does not falsely deduplicate.
pub struct LaneRxCrypto {
    aead: LessSafeKey,
    iv: [u8; 12],
    hp_key: [u8; 32],
    max_wire: usize,
}

#[derive(Debug, PartialEq, Eq)]
pub struct OpenedRecord<'a> {
    pub pn: u64,
    pub kind: u8,
    /// Borrowed from the single authenticated caller-owned record buffer;
    /// excludes the encrypted kind, trailer marker, zeros and AEAD tag.
    pub payload: &'a [u8],
}

fn new_aead(keys: &[u8; 32]) -> Result<LessSafeKey, CryptoError> {
    let unbound = UnboundKey::new(&aead::CHACHA20_POLY1305, keys)
        .map_err(|_| CryptoError::PrimitiveFailure)?;
    Ok(LessSafeKey::new(unbound))
}
fn validated_limit(limit: usize) -> Result<usize, CryptoError> {
    if !(FIXED_WIRE_OVERHEAD..=MAX_WIRE_LEN).contains(&limit) {
        return Err(CryptoError::WireLimit);
    }
    Ok(limit)
}
fn record_nonce(iv: &[u8; 12], pn: u64) -> Nonce {
    let mut bytes = *iv;
    for (nonce_byte, pn_byte) in bytes[4..].iter_mut().zip(pn.to_be_bytes()) {
        *nonce_byte ^= pn_byte;
    }
    Nonce::assume_unique_for_key(bytes)
}

/// WBD uses 8 *full* header-protection bytes, NOT a 5B QUIC HP function.
/// First 4 sample bytes form the little-endian ChaCha block counter;
/// next 12 bytes are nonce. Sample may partly overlap the authentication tag.
fn chacha_hp_mask(hp_key: &[u8; 32], ciphertext_and_tag: &[u8]) -> Result<[u8; 8], CryptoError> {
    if ciphertext_and_tag.len() < HP_SAMPLE_LEN { return Err(CryptoError::InvalidLength); }
    let sample = &ciphertext_and_tag[..HP_SAMPLE_LEN];
    let counter = u32::from_le_bytes(sample[..4].try_into().map_err(|_|CryptoError::InvalidLength)?);
    let mut nonce = [0u8; 12];
    nonce.copy_from_slice(&sample[4..16]);
    let mut cipher = ChaCha20::new(hp_key.into(), (&nonce).into());
    cipher.seek(u64::from(counter) * 64);
    let mut mask = [0u8; 8];
    cipher.apply_keystream(&mut mask);
    Ok(mask)
}

impl LaneTxCrypto {
    pub fn new(keys: DirectionKeys, max_wire: usize) -> Result<Self, CryptoError> {
        let max_wire = validated_limit(max_wire)?;
        Ok(Self { aead:new_aead(&keys.aead_key)?, iv:keys.iv, hp_key:keys.hp_key,
            max_wire, next_pn:0, exhausted:false })
    }

    /// Input: OWNED unique wire buffer whose business bytes already occupy
    /// [14 .. 14+payload_len]. This method never copies the business packet
    /// into another Vec and never allocates a second record buffer.
    ///
    /// On success, returns (reserved_pn, exact_full_wire_len). A failure burns
    /// that PN and MUST NOT be published as a FrozenRecord.
    pub fn seal_in_place(
        &mut self, kind: u8, wire: &mut [u8], payload_len: usize, padding: usize,
    ) -> Result<(u64, usize), CryptoError> {
        if self.exhausted { return Err(CryptoError::PnExhausted); }
        let pn = self.next_pn;
        if pn == u64::MAX { self.exhausted = true; } else { self.next_pn += 1; }

        if kind != AUTHENTICATED_LINK_KIND && kind != AUTHENTICATED_HEALTH_KIND {
            return Err(CryptoError::InvalidKind);
        }
        let used = FIXED_WIRE_OVERHEAD
            .checked_add(payload_len)
            .and_then(|v|v.checked_add(padding))
            .ok_or(CryptoError::InvalidLength)?;
        if used > self.max_wire { return Err(CryptoError::InvalidLength); }
        if wire.len() < used { return Err(CryptoError::Capacity); }

        let body_len = used - OUTER_HEADER_LEN;
        let header = crate::record_frame::outer_header_for_body(body_len,self.max_wire)
            .map_err(|_|CryptoError::InvalidLength)?;
        wire[..OUTER_HEADER_LEN].copy_from_slice(&header);
        wire[OUTER_HEADER_LEN..CIPHER_OFFSET].copy_from_slice(&pn.to_be_bytes());
        let mut aad = [0u8; AAD_LEN];
        aad.copy_from_slice(&wire[..AAD_LEN]);

        let plain_end = used - AEAD_TAG_LEN;
        let plain = &mut wire[CIPHER_OFFSET..plain_end];
        plain[0] = kind;
        plain[1+payload_len] = INNER_MARKER;
        plain[2+payload_len..].fill(0);
        let tag = match self.aead.seal_in_place_separate_tag(
            record_nonce(&self.iv,pn),Aad::from(aad),plain)
        {
            Ok(tag) => tag,
            Err(_) => {
                wire[..used].fill(0);
                return Err(CryptoError::PrimitiveFailure);
            }
        };
        wire[plain_end..used].copy_from_slice(tag.as_ref());
        let mask = chacha_hp_mask(&self.hp_key,&wire[CIPHER_OFFSET..used])?;
        for (byte,m) in wire[OUTER_HEADER_LEN..CIPHER_OFFSET].iter_mut().zip(mask) {
            *byte ^= m;
        }
        Ok((pn,used))
    }

    #[cfg(test)]
    pub(crate) fn from_test_pn(keys: DirectionKeys, max_wire: usize, pn: u64) -> Self {
        let mut tx = Self::new(keys,max_wire).unwrap();
        tx.next_pn = pn;
        tx
    }
}

impl LaneRxCrypto {
    pub fn new(keys: DirectionKeys, max_wire: usize) -> Result<Self, CryptoError> {
        let max_wire = validated_limit(max_wire)?;
        Ok(Self { aead:new_aead(&keys.aead_key)?, iv:keys.iv, hp_key:keys.hp_key,max_wire })
    }

    /// Opens EXACTLY one record in place, only returns bytes after real AEAD
    /// success. Authentication failure taints wire memory; caller must discard.
    /// Framing length mismatch is terminal for the stream (no magic resync).
    pub fn open_in_place<'a>(&self, wire: &'a mut [u8]) -> Result<OpenedRecord<'a>, CryptoError> {
        if wire.len() < FIXED_WIRE_OVERHEAD || wire.len() > self.max_wire {
            return Err(CryptoError::InvalidLength);
        }
        if wire[0] != OUTER_TYPE || wire[1..3] != OUTER_VERSION {
            return Err(CryptoError::InvalidHeader);
        }
        let declared = u16::from_be_bytes([wire[3],wire[4]]) as usize;
        if declared + OUTER_HEADER_LEN != wire.len() {
            return Err(CryptoError::InvalidLength);
        }
        let mask = chacha_hp_mask(&self.hp_key,&wire[CIPHER_OFFSET..])?;
        let mut pn_bytes = [0u8; PROTECTED_PN_LEN];
        pn_bytes.copy_from_slice(&wire[OUTER_HEADER_LEN..CIPHER_OFFSET]);
        for (byte,m) in pn_bytes.iter_mut().zip(mask) { *byte ^= m; }
        let pn = u64::from_be_bytes(pn_bytes);
        let mut aad = [0u8; AAD_LEN];
        aad[..OUTER_HEADER_LEN].copy_from_slice(&wire[..OUTER_HEADER_LEN]);
        aad[OUTER_HEADER_LEN..].copy_from_slice(&pn_bytes);
        let plain = self.aead.open_in_place(
            record_nonce(&self.iv,pn),Aad::from(aad),&mut wire[CIPHER_OFFSET..]
        ).map_err(|_|CryptoError::Authentication)?;
        if plain.len() < PLAIN_FIXED_LEN { return Err(CryptoError::InvalidLength); }
        let mut marker_at = plain.len()-1;
        while marker_at>=1 && plain[marker_at]==0 {marker_at-=1;}
        if marker_at < 1 || plain[marker_at] != INNER_MARKER {
            return Err(CryptoError::InvalidInnerMarker);
        }
        let kind=plain[0];
        if kind != AUTHENTICATED_LINK_KIND && kind != AUTHENTICATED_HEALTH_KIND {
            return Err(CryptoError::InvalidKind);
        }
        Ok(OpenedRecord { pn, kind, payload:&plain[1..marker_at] })
    }
}
