//! V4 cold boundary **UNTRUSTED** byte grammar for a future authenticated
//! Go->Rust control call. Parsing bytes is NEVER authority to install a lane.
//! An attacker able to write these bytes can supply self-consistent keys.
//! Production ABI is still capabilities=0 and has no cold install command.
#![forbid(unsafe_code)]

use wbd_types::{LaneKey, TunnelKey};
use wbd_codec::record_crypto::DirectionKeys;

pub const COLD_V4_LEN: usize = 248;
const MAGIC: &[u8; 4] = b"WBCO";
const PREFIX: usize = 96;
const KEYS_LEN: usize = 76;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ColdV4Error {
    BadLength, BadMagic, BadVersion, BadSize, BadRole,
    BadLane, BadCipher, BadReserved, BadIdentity,
    BadLimit, BadKeys, ScopeMismatch, MissingRustOwner,
}

/// Owns a copy of untrusted, possibly sensitive caller bytes. No Debug/Clone,
/// no way to transform this value into an authenticated Rust FEC origin.
pub struct UntrustedColdV4 {
    bytes: [u8; COLD_V4_LEN],
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ColdIdentity {
    pub server: bool,
    pub go_lane_id: u8,
    pub cipher: u8,
    pub tunnel_id: [u8; 16],
    pub logical_epoch: [u8; 16],
    pub incarnation: [u8; 16],
    pub principal_hash: [u8; 32],
    pub client_limit: u16,
    pub server_limit: u16,
}

/// Expected local scope is a guard against accidental misrouting, NOT proof
/// of TLS authentication. Only a future owner/ABI authority may install.
pub struct ExpectedRustOwner {
    pub lane: LaneKey,
    pub owner_generation: u32,
    pub logical_epoch: [u8;16],
    pub tunnel_id: [u8;16],
    pub go_lane_id: u8,
    pub server: bool,
}

impl UntrustedColdV4 {
    pub fn parse(input: &[u8]) -> Result<Self, ColdV4Error> {
        if input.len() != COLD_V4_LEN { return Err(ColdV4Error::BadLength); }
        if &input[..4] != MAGIC { return Err(ColdV4Error::BadMagic); }
        if u16::from_be_bytes([input[4], input[5]]) != 1 { return Err(ColdV4Error::BadVersion); }
        if usize::from(u16::from_be_bytes([input[6], input[7]])) != COLD_V4_LEN {
            return Err(ColdV4Error::BadSize);
        }
        if input[8] > 1 { return Err(ColdV4Error::BadRole); }
        if !(1..=4).contains(&input[9]) { return Err(ColdV4Error::BadLane); }
        if !(1..=3).contains(&input[10]) { return Err(ColdV4Error::BadCipher); }
        if input[11] != 0 { return Err(ColdV4Error::BadReserved); }
        if input[12..60].chunks_exact(16).any(|chunk| chunk.iter().all(|b| *b == 0)) ||
            input[64..96].iter().all(|b| *b == 0) {
            return Err(ColdV4Error::BadIdentity);
        }
        if input[60..62] == [0,0] || input[62..64] == [0,0] {
            return Err(ColdV4Error::BadLimit);
        }
        let c2s = &input[PREFIX..PREFIX+KEYS_LEN];
        let s2c = &input[PREFIX+KEYS_LEN..];
        if c2s == s2c ||
           c2s.iter().all(|b| *b == 0) || s2c.iter().all(|b| *b == 0) {
            return Err(ColdV4Error::BadKeys);
        }
        let mut bytes = [0u8; COLD_V4_LEN];
        bytes.copy_from_slice(input);
        Ok(Self { bytes })
    }
    pub fn identity(&self) -> ColdIdentity {
        let mut tunnel_id=[0;16];tunnel_id.copy_from_slice(&self.bytes[12..28]);
        let mut logical_epoch=[0;16];logical_epoch.copy_from_slice(&self.bytes[28..44]);
        let mut incarnation=[0;16];incarnation.copy_from_slice(&self.bytes[44..60]);
        let mut principal_hash=[0;32];principal_hash.copy_from_slice(&self.bytes[64..96]);
        ColdIdentity {
            server:self.bytes[8] == 1,
            go_lane_id:self.bytes[9],
            cipher:self.bytes[10],
            tunnel_id,logical_epoch,incarnation,principal_hash,
            client_limit:u16::from_be_bytes([self.bytes[60],self.bytes[61]]),
            server_limit:u16::from_be_bytes([self.bytes[62],self.bytes[63]]),
        }
    }
    pub fn preflight_untrusted_owner(&self, expected: &ExpectedRustOwner) -> Result<(), ColdV4Error> {
        let x = self.identity();
        if expected.owner_generation == 0 ||
           expected.lane.generation == 0 ||
           expected.lane.tunnel.generation == 0 ||
           expected.lane.tunnel.slot == 0 {
            return Err(ColdV4Error::MissingRustOwner);
        }
        if x.tunnel_id != expected.tunnel_id ||
           x.logical_epoch != expected.logical_epoch ||
           x.server != expected.server ||
           x.go_lane_id != expected.go_lane_id {
            return Err(ColdV4Error::ScopeMismatch);
        }
        // Local generations have no corresponding Go wire field; they MUST
        // be validated and allocated by the future Rust owner/engine.
        Ok(())
    }
    /// Only available to the internal private Go-session owner composition.
    /// Format-valid untrusted bytes MUST NOT authorize calling an installer.
    pub(crate) fn internal_direction_keys(&self) -> (DirectionKeys,DirectionKeys) {
        let direction=|start:usize| {
            let mut aead_key=[0;32];
            aead_key.copy_from_slice(&self.bytes[start..start+32]);
            let mut iv=[0;12];iv.copy_from_slice(&self.bytes[start+32..start+44]);
            let mut hp_key=[0;32];hp_key.copy_from_slice(&self.bytes[start+44..start+76]);
            DirectionKeys{aead_key,iv,hp_key}
        };
        (direction(PREFIX),direction(PREFIX+KEYS_LEN))
    }
    /// No FecOrigin, live owner install, ABI call or key getter is exposed.
    pub fn direction_materials_distinct(&self) -> bool {
        self.bytes[PREFIX..PREFIX+KEYS_LEN] != self.bytes[PREFIX+KEYS_LEN..]
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn fixture() -> [u8; COLD_V4_LEN] {
        let mut x = [0u8; COLD_V4_LEN];
        x[..4].copy_from_slice(MAGIC);
        x[4..6].copy_from_slice(&1u16.to_be_bytes());
        x[6..8].copy_from_slice(&(COLD_V4_LEN as u16).to_be_bytes());
        x[8]=0;x[9]=1;x[10]=1;
        x[12..28].fill(1);x[28..44].fill(2);x[44..60].fill(3);
        x[60..62].copy_from_slice(&1400u16.to_be_bytes());
        x[62..64].copy_from_slice(&1400u16.to_be_bytes());
        x[64..96].fill(4);
        x[96..172].fill(5);x[172..].fill(6);x
    }
    #[test]
    fn r0_cold_v4_exact_big_endian_and_owner_scope() {
        let p=UntrustedColdV4::parse(&fixture()).unwrap();
        let i=p.identity();
        assert!(!i.server);assert_eq!(i.go_lane_id,1);
        assert_eq!(i.client_limit,1400);
        assert_eq!(i.cipher,1);assert_eq!(i.logical_epoch,[2;16]);
        assert!(p.direction_materials_distinct());
        let scope=ExpectedRustOwner{
            lane:LaneKey{tunnel:TunnelKey{slot:1,generation:7},slot:1,generation:9},
            owner_generation:9,logical_epoch:i.logical_epoch,
            tunnel_id:i.tunnel_id,go_lane_id:1,server:false,
        };
        assert_eq!(p.preflight_untrusted_owner(&scope),Ok(()));
        let bad=ExpectedRustOwner{go_lane_id:2,..scope};
        assert_eq!(p.preflight_untrusted_owner(&bad),Err(ColdV4Error::ScopeMismatch));
        let dead=ExpectedRustOwner{owner_generation:0,..scope};
        assert_eq!(p.preflight_untrusted_owner(&dead),Err(ColdV4Error::MissingRustOwner));
    }
    #[test]
    fn r0_cold_v4_exact_length_header_and_unknown_fields() {
        let f=fixture();
        assert!(matches!(UntrustedColdV4::parse(&f[..247]),Err(ColdV4Error::BadLength)));
        let mut a=f;a[0]=0;
        assert!(matches!(UntrustedColdV4::parse(&a),Err(ColdV4Error::BadMagic)));
        let mut a=f;a[4]=1;
        assert!(matches!(UntrustedColdV4::parse(&a),Err(ColdV4Error::BadVersion)));
        let mut a=f;a[7]=247;
        assert!(matches!(UntrustedColdV4::parse(&a),Err(ColdV4Error::BadSize)));
        for (pos,err) in [(8,ColdV4Error::BadRole),(9,ColdV4Error::BadLane),
            (10,ColdV4Error::BadCipher),(11,ColdV4Error::BadReserved)] {
            let mut a=f;a[pos]=255;
            assert!(matches!(UntrustedColdV4::parse(&a),Err(z) if z==err));
        }
    }
    #[test]
    fn r0_cold_v4_identity_and_key_downgrade_rejected() {
        let f=fixture();
        for (start,end) in [(12,28),(28,44),(44,60),(64,96)] {
            let mut a=f;a[start..end].fill(0);
            assert!(matches!(UntrustedColdV4::parse(&a),Err(ColdV4Error::BadIdentity)));
        }
        let mut a=f;a[60..62].fill(0);
        assert!(matches!(UntrustedColdV4::parse(&a),Err(ColdV4Error::BadLimit)));
        let mut a=f;a[172..].copy_from_slice(&f[96..172]);
        assert!(matches!(UntrustedColdV4::parse(&a),Err(ColdV4Error::BadKeys)));
    }
    #[test]
    fn r0_cold_v4_real_tls_ephemeral_go_fixture() {
        let path=match std::env::var("WBD_COLD_FIXTURE") {
            Ok(p)=>p,Err(_)=>return // separate native workflow sets fixture and proves real Go interop
        };
        let raw=std::fs::read(path).expect("Go TLS ephemeral fixture");
        let p=UntrustedColdV4::parse(&raw).expect("exact Go TLS V4 snapshot wire bytes");
        let i=p.identity();
        assert_eq!(i.go_lane_id,1);assert_eq!(i.cipher,1);
        assert_eq!(i.client_limit,1400);assert_eq!(i.server_limit,1400);
        assert!(!i.server);assert_ne!(i.logical_epoch,[0;16]);
        assert_ne!(i.incarnation,[0;16]);assert!(p.direction_materials_distinct());
    }
}
