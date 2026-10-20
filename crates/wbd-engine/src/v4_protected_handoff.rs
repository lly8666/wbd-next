//! M0 normal-build private Go V4 Prepare control contract.
//! This is the future *production* owner-preparation function exercised by
//! the existing native Go credential-checked bridge. It is crate-private:
//! no public C caller may submit a self-consistent 248-byte bundle to install
//! an authenticated owner. Neither this versioned command nor cold248 proves
//! TLS authentication. Source trust MUST come from the same-process private
//! credential-checked Go EstablishServerV4 callback.
//! Actual normal product installer/capability remains disabled.
#![forbid(unsafe_code)]

use crate::cold_v4::{ExpectedRustOwner,UntrustedColdV4};
use crate::v4_owner_crypto::ProtectedScopedOwner;
use wbd_types::{LaneKey,TunnelKey};

pub(crate) const HANDOFF_V1_LEN:usize=32;

#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) struct GoFlow {
    pub(crate) client_ip:[u8;4],
    pub(crate) server_ip:[u8;4],
    pub(crate) client_port:u16,
    pub(crate) server_port:u16,
}

#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) struct PrivateGoV4Handoff {
    pub(crate) flow:GoFlow,
    pub(crate) rx_boundary:u32,
    pub(crate) peer_mss:u16,
    pub(crate) peer_mss_advertised:bool,
    // Exact Go protected transcript 0x0003 or private probe 0x0007.
    // Parsed bytes are NEVER alone authority to enable FEC2 in Rust.
    pub(crate) negotiated_features:u16,
}
impl PrivateGoV4Handoff {
    pub(crate) fn decode(wire:&[u8])->Result<Self,()> {
        if wire.len()!=HANDOFF_V1_LEN || &wire[..4]!=b"WBGH" ||
            u16::from_be_bytes([wire[6],wire[7]])!=HANDOFF_V1_LEN as u16 ||
            wire[26]>1 {return Err(())}
        // V1 must retain all five trailing reserved zeros. V2 is only the
        // exact Go post-TLS bit2 set, no acceptance of arbitrary authority.
        let negotiated_features=match u16::from_be_bytes([wire[4],wire[5]]){
            1 if wire[27..].iter().all(|b|*b==0)=>3u16,
            2 if wire[27..29]==[0,7] && wire[29..].iter().all(|b|*b==0)=>7u16,
            _=>return Err(()),
        };
        let mut client_ip=[0;4];client_ip.copy_from_slice(&wire[8..12]);
        let mut server_ip=[0;4];server_ip.copy_from_slice(&wire[12..16]);
        let flow=GoFlow{
            client_ip,server_ip,
            client_port:u16::from_be_bytes([wire[16],wire[17]]),
            server_port:u16::from_be_bytes([wire[18],wire[19]]),
        };
        let unicast=|ip:[u8;4]|ip[0]!=0 && ip[0]<224 &&
            ip!=[0,0,0,0]&&ip!=[255,255,255,255];
        if !unicast(flow.client_ip)||!unicast(flow.server_ip)||
            flow.client_port==0||flow.server_port==0{return Err(())}
        let peer_mss=u16::from_be_bytes([wire[24],wire[25]]);
        let peer_mss_advertised=wire[26]==1;
        if peer_mss<64||(!peer_mss_advertised&&peer_mss!=536){return Err(())}
        Ok(Self{flow,
            rx_boundary:u32::from_be_bytes([wire[20],wire[21],wire[22],wire[23]]),
            peer_mss,peer_mss_advertised,negotiated_features,
        })
    }

    /// All original M1 RX/TX and real M3 AEAD/PN owners are constructed
    /// together BEFORE protected reply/Detach. No Active or business delivery
    /// is possible until caller later commits the *actual* Go TX boundary.
    /// Call only through private Go's verified session; command validity
    /// by itself is NOT authorization.
    pub(crate) fn prepare_scoped_owner(
        &self,cold:&UntrustedColdV4,generation:u32,owner_id:u64,
    )->Result<ProtectedScopedOwner,()>{
        self.prepare_scoped_owner_for_side(cold,generation,owner_id,true)
    }
    // Both original-Go TLS sides are cryptographically symmetric after real
    // verified post-reply/Detach. A caller may NEVER substitute server cold
    // into client owner or vice versa; the C entrypoint chooses the role.
    pub(crate) fn prepare_scoped_owner_for_side(
        &self,cold:&UntrustedColdV4,generation:u32,owner_id:u64,server:bool,
    )->Result<ProtectedScopedOwner,()>{
        if generation==0 || cold.identity().server!=server{return Err(())}
        let identity=cold.identity();
        let lane=LaneKey{
            tunnel:TunnelKey{slot:1,generation},
            slot:u32::from(identity.go_lane_id),generation,
        };
        let expected=ExpectedRustOwner{
            lane,owner_generation:generation,
            logical_epoch:identity.logical_epoch,
            tunnel_id:identity.tunnel_id,
            go_lane_id:identity.go_lane_id,server,
        };
        ProtectedScopedOwner::prepare_from_protected_go(
            cold,&expected,owner_id,self.rx_boundary,
            self.peer_mss,self.peer_mss_advertised,
        ).map_err(|_|())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn valid()->[u8;HANDOFF_V1_LEN]{
        let mut a=[0u8;HANDOFF_V1_LEN];
        a[..4].copy_from_slice(b"WBGH");
        a[4..6].copy_from_slice(&1u16.to_be_bytes());
        a[6..8].copy_from_slice(&(HANDOFF_V1_LEN as u16).to_be_bytes());
        a[8..12].copy_from_slice(&[10,0,0,2]);
        a[12..16].copy_from_slice(&[10,0,1,1]);
        a[16..18].copy_from_slice(&41001u16.to_be_bytes());
        a[18..20].copy_from_slice(&443u16.to_be_bytes());
        a[20..24].copy_from_slice(&u32::MAX.to_be_bytes());
        a[24..26].copy_from_slice(&1360u16.to_be_bytes());
        a[26]=1;a
    }
    #[test]
    fn m0_normal_build_v4_go_private_handoff_version_and_scope(){
        let a=valid();let p=PrivateGoV4Handoff::decode(&a).unwrap();
        assert_eq!(p.flow.client_port,41001);
        assert_eq!(p.flow.server_port,443);
        assert_eq!(p.rx_boundary,u32::MAX);
        assert_eq!(p.negotiated_features,3);
        assert!(PrivateGoV4Handoff::decode(&a[..31]).is_err());
        // Mutate only fields whose zero value REALLY violates grammar.
        // Changing a valid, nonzero port/MTU or an exact RX boundary is not
        // automatically invalid; reject semantics, not arbitrary bytes.
        for index in [0usize,5,7,8,12,26]{
            let mut wrong=a;wrong[index]=0;
            assert!(PrivateGoV4Handoff::decode(&wrong).is_err(),"byte={index}");
        }
        let mut wrong=a;wrong[16..18].fill(0); // zero source port
        assert!(PrivateGoV4Handoff::decode(&wrong).is_err());
        let mut wrong=a;wrong[18..20].fill(0); // zero destination port
        assert!(PrivateGoV4Handoff::decode(&wrong).is_err());
        let mut wrong=a;wrong[24..26].fill(0); // zero original SYN MSS
        assert!(PrivateGoV4Handoff::decode(&wrong).is_err());
        let mut wrong=a;wrong[27]=1; // reserved extension
        assert!(PrivateGoV4Handoff::decode(&wrong).is_err());
        let mut wrong=a;wrong[26]=2;
        assert!(PrivateGoV4Handoff::decode(&wrong).is_err());
        let mut wrong=a;wrong[26]=0;
        assert!(PrivateGoV4Handoff::decode(&wrong).is_err()); // 1360 without MSS advertisement
        let mut fallback=a;fallback[24..26].copy_from_slice(&536u16.to_be_bytes());
        fallback[26]=0;
        assert!(PrivateGoV4Handoff::decode(&fallback).is_ok());
    }
    #[test]
    fn m0_private_v4_real_go_fec2_bit2_handoff_is_metadata_not_permission(){
        let mut a=valid();
        a[4..6].copy_from_slice(&2u16.to_be_bytes());
        a[27..29].copy_from_slice(&7u16.to_be_bytes());
        let parsed=PrivateGoV4Handoff::decode(&a).unwrap();
        assert_eq!(parsed.negotiated_features,7);
        assert_eq!(parsed.flow.client_port,41001);
        assert_eq!(parsed.rx_boundary,u32::MAX);
        for index in [28usize,29,30,31]{
            let mut bad=a;bad[index]^=1;
            assert!(PrivateGoV4Handoff::decode(&bad).is_err(),"byte={index}");
        }
        let mut bad=a;bad[4..6].copy_from_slice(&1u16.to_be_bytes());
        assert!(PrivateGoV4Handoff::decode(&bad).is_err(),"V1 reserved dirty");
        let mut bad=a;bad[27..29].copy_from_slice(&3u16.to_be_bytes());
        assert!(PrivateGoV4Handoff::decode(&bad).is_err(),"V2 no bit2");
        let mut bad=a;bad[27..29].copy_from_slice(&15u16.to_be_bytes());
        assert!(PrivateGoV4Handoff::decode(&bad).is_err(),"V2 unknown bits");
    }
}
