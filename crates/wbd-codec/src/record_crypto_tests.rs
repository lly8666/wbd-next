//! Separate R1 authentic crypto tests, under record_frame:: for frozen R0 13-test isolation.
use crate::record_crypto::*;
    use crate::record_frame::{FIXED_WIRE_OVERHEAD, MAX_WIRE_LEN};
    const CIPHER_OFFSET:usize=13;
    const LEGACY: &str = include_str!("../../../r0/fixtures/legacy-record-wire-v1.txt");
    // Independent Go HKDF-SHA256 testKeys: master [0..31], nonce [0..15],
    // info "WBD-TLSLIKE-V1/c2s". NOT the V4 exporter. Tests only old V1 wire.
    fn keys() -> DirectionKeys {
        DirectionKeys {
            aead_key:[0xd0,0x29,0x4f,0xa8,0x35,0xaa,0xd9,0x0e,0xda,0xc2,0x41,0x79,0x3a,0x9e,0x5f,0xc1,
                      0x29,0xc9,0x8d,0xe3,0x46,0x76,0x52,0x9e,0xe7,0x62,0x0e,0xc0,0x2a,0xde,0x7a,0x99],
            iv:[0x1a,0x66,0xf5,0x26,0xac,0x13,0x36,0x1d,0x3c,0xd0,0xdd,0xae],
            hp_key:[0xba,0x46,0xfc,0x4a,0x61,0x8d,0x23,0x56,0x29,0x3c,0xcc,0x9c,0x5d,0xbd,0x17,0x33,
                    0x27,0xe5,0x85,0x00,0xf1,0x8b,0x50,0x7c,0x5d,0x0b,0xdf,0x74,0x95,0x3d,0x54,0xe7],
        }
    }
    fn unhex(s:&str)->Vec<u8> {
        assert_eq!(s.len()%2,0);
        (0..s.len()).step_by(2).map(|i|u8::from_str_radix(&s[i..i+2],16).unwrap()).collect()
    }
    #[test]
    fn r1_crypto_chacha_six_pinned_real_go_wire_vectors_exact() {
        let mut n=0;
        for line in LEGACY.lines().filter(|x|!x.is_empty()&&!x.starts_with('#')) {
            let x:Vec<_>=line.split('|').collect();
            assert_eq!(x.len(),6);
            let pn=x[1].parse::<u64>().unwrap();
            let kind=x[2].parse::<u8>().unwrap();
            let padding=x[3].parse::<usize>().unwrap();
            let payload=unhex(x[4]);let old_wire=unhex(x[5]);
            let mut wire=vec![0u8;old_wire.len()];
            wire[CIPHER_OFFSET+1..CIPHER_OFFSET+1+payload.len()].copy_from_slice(&payload);
            let mut tx=LaneTxCrypto::from_test_pn(keys(),MAX_WIRE_LEN,pn);
            let (reserved,len)=tx.seal_in_place(kind,&mut wire,payload.len(),padding).unwrap();
            assert_eq!((reserved,len),(pn,old_wire.len()),"{}",x[0]);
            assert_eq!(wire,old_wire,"exact Go wire mismatch {}",x[0]);
            let rx=LaneRxCrypto::new(keys(),MAX_WIRE_LEN).unwrap();
            let opened=rx.open_in_place(&mut wire).unwrap();
            assert_eq!((opened.pn,opened.kind,opened.payload),(pn,kind,payload.as_slice()),"{}",x[0]);
            n+=1;
        }
        assert_eq!(n,6);
    }
    #[test]
    fn r1_crypto_chacha_authentication_tampering_never_delivers_payload() {
        let sample=LEGACY.lines().find(|x|x.starts_with("pn1-ascii|")).unwrap();
        let old=unhex(sample.split('|').nth(5).unwrap());
        let rx=LaneRxCrypto::new(keys(),MAX_WIRE_LEN).unwrap();
        for pos in [0,1,2,3,4,5,12,13,14,old.len()-17,old.len()-1] {
            let mut tampered=old.clone();tampered[pos]^=0x01;
            assert!(rx.open_in_place(&mut tampered).is_err(),"tampered byte {pos} authenticated");
        }
        let mut extra=old.clone();extra.push(0);
        assert_eq!(rx.open_in_place(&mut extra),Err(CryptoError::InvalidLength));
        let mut short=old.clone();short.pop();
        assert_eq!(rx.open_in_place(&mut short),Err(CryptoError::InvalidLength));
    }
    #[test]
    fn r1_crypto_chacha_failed_seal_burns_pn_and_does_not_return_wire() {
        let mut tx=LaneTxCrypto::new(keys(),FIXED_WIRE_OVERHEAD).unwrap();
        let mut wire=vec![0;FIXED_WIRE_OVERHEAD];
        assert_eq!(tx.seal_in_place(0,&mut wire,1,0),Err(CryptoError::InvalidLength));
        let (pn,used)=tx.seal_in_place(0,&mut wire,0,0).unwrap();
        assert_eq!((pn,used),(1,FIXED_WIRE_OVERHEAD));
        let mut bad=LaneTxCrypto::new(keys(),MAX_WIRE_LEN).unwrap();
        assert_eq!(bad.seal_in_place(0,&mut [],0,0),Err(CryptoError::Capacity));
        let mut w=vec![0;FIXED_WIRE_OVERHEAD];
        assert_eq!(bad.seal_in_place(255,&mut w,0,0),Err(CryptoError::InvalidKind));
        assert_eq!(bad.seal_in_place(0,&mut w,0,0).unwrap().0,2);
    }
    #[test]
    fn r1_crypto_chacha_max_pn_exhausts_without_wrap() {
        let mut tx=LaneTxCrypto::from_test_pn(keys(),MAX_WIRE_LEN,u64::MAX-1);
        let rx=LaneRxCrypto::new(keys(),MAX_WIRE_LEN).unwrap();
        for pn in [u64::MAX-1,u64::MAX] {
            let mut wire=[0u8;FIXED_WIRE_OVERHEAD];
            assert_eq!(tx.seal_in_place(0,&mut wire,0,0).unwrap().0,pn);
            assert_eq!(rx.open_in_place(&mut wire).unwrap().pn,pn);
        }
        assert_eq!(tx.seal_in_place(0,&mut [0;FIXED_WIRE_OVERHEAD],0,0),Err(CryptoError::PnExhausted));
    }
    #[test]
    fn r1_crypto_chacha_health_padding_and_zero_business_payload() {
        let mut tx=LaneTxCrypto::new(keys(),1200).unwrap();
        let rx=LaneRxCrypto::new(keys(),1200).unwrap();
        for (kind,payload,padding) in [(0u8,vec![],0),(1,vec![0,0xff,0,0],7),(0,vec![0u8;1169],0)] {
            let mut wire=vec![0;FIXED_WIRE_OVERHEAD+payload.len()+padding];
            wire[CIPHER_OFFSET+1..CIPHER_OFFSET+1+payload.len()].copy_from_slice(&payload);
            let (_,used)=tx.seal_in_place(kind,&mut wire,payload.len(),padding).unwrap();
            assert_eq!(used,wire.len());
            let rec=rx.open_in_place(&mut wire).unwrap();
            assert_eq!(rec.kind,kind);
            assert_eq!(rec.payload,payload);
        }
    }

