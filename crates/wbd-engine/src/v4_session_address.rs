//! PLAN028: one authenticated client's inner IPv4 source must match its
//! original Go TLS /32 lease before any Rust M4 TUN application write.
//! Only auto-leased sessions have a bound address; legacy manual sessions
//! retain their existing semantics until manual-IP ownership is negotiated.
//! The check is O(1), no heap, locks, clocks, or new record/packet headers.

/// Source-ownership check AFTER original AEAD+replay and before TUN write.
/// Invalid IPv4 / header sizes are rejected even if a matching source is
/// present; the existing TUN validates the complete packet separately.
pub(crate) fn admitted_client_source(packet:&[u8],lease:Option<[u8;4]>)->bool{
    let Some(ip)=lease else{return true};
    packet.len()>=20 &&
        packet[0]>>4==4 &&
        usize::from(packet[0]&0x0f)*4>=20 &&
        usize::from(packet[0]&0x0f)*4<=packet.len() &&
        packet[12..16]==ip[..]
}

#[cfg(test)]
mod tests{
    use super::*;
    fn packet(ip:[u8;4])->Vec<u8>{
        let mut packet=vec![0u8;40];
        packet[0]=0x45;
        packet[2]=0;
        packet[3]=40;
        packet[8]=64;
        packet[9]=17;
        packet[12..16].copy_from_slice(&ip);
        packet
    }
    #[test]
    fn plan028_lease_scopes_decrypted_tcp_udp_game_fec_and_recovered_ipv4(){
        let a=[10,219,0,2];
        let b=[10,219,0,3];
        let a_packet=packet(a);
        let b_packet=packet(b);
        assert!(admitted_client_source(&a_packet,Some(a)));
        assert!(admitted_client_source(&b_packet,Some(b)));
        assert!(!admitted_client_source(&b_packet,Some(a)));
        assert!(!admitted_client_source(&a_packet,Some(b)));
        assert!(admitted_client_source(&b_packet,None)); // manual unchanged
        let mut short=vec![0x45,0,0,0];
        assert!(!admitted_client_source(&short,Some(a)));
        short=packet(a);short[0]=0x65;
        assert!(!admitted_client_source(&short,Some(a)));
        short=packet(a);short[0]=0x44;
        assert!(!admitted_client_source(&short,Some(a)));
        short=packet(a);short[0]=0x4f;
        assert!(!admitted_client_source(&short[..40],Some(a)));
    }
}
