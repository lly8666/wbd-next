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



// C01 exact old Go AES suite differential: this is NOT just Rust roundtrip.
// V3 suite-domain-separated HKDF C2S keys are pinned in the independent
// oracle's Go source comments and verified with PyCA AES/HKDF separately.
const AES_V3: &str = include_str!("../oracles/aes_wire_go_v3.txt");
fn aes_v3_keys(suite: RecordSuite) -> DirectionKeys {
    let (aead,iv,hp)=match suite {
        RecordSuite::Aes128Gcm=>(
            "05bac544ed5965eec3f555074486839cadaac6372bbb645c26dcf43c312c1cdc",
            "1cb11fe4d87e283dfb2dfa5b",
            "50920f50e971e66a1e329a6c3fab175d8ddb103fb8462a8d9100415543263eb9"),
        RecordSuite::Aes256Gcm=>(
            "8b3e7e908449fd44fecede8d34f6e29c01efdda5e9f569dd679b8847833781c3",
            "50acc6123b6403da143ac402",
            "7fbb9de569b6269d2db6c3f4dc81d14904cfade82f0dc61bc10b09dafa5b168c"),
        _=>panic!("AES suite only"),
    };
    DirectionKeys {
        aead_key: unhex(aead).try_into().unwrap(),
        iv: unhex(iv).try_into().unwrap(),
        hp_key: unhex(hp).try_into().unwrap(),
    }
}
fn aes_suite(id: u8) -> RecordSuite {
    RecordSuite::try_from(id).unwrap()
}
#[test]
fn r1_crypto_aes_14_go_stdlib_vectors_byte_exact_and_authenticated() {
    let mut count=[0usize;2];
    for line in AES_V3.lines().filter(|x|!x.starts_with('#')&&!x.is_empty()) {
        let x:Vec<_>=line.split('|').collect();
        assert_eq!(x.len(),6);
        let suite=aes_suite(x[0].parse::<u8>().unwrap());
        let idx=if suite==RecordSuite::Aes128Gcm{0}else{1};
        let pn=x[1].parse::<u64>().unwrap();
        let kind=x[2].parse::<u8>().unwrap();
        let pad=x[3].parse::<usize>().unwrap();
        let payload=unhex(x[4]);
        let expected=unhex(x[5]);
        let mut wire=vec![0u8;expected.len()];
        wire[CIPHER_OFFSET+1..CIPHER_OFFSET+1+payload.len()].copy_from_slice(&payload);
        let mut tx=LaneTxCrypto::from_test_pn_for_suite(aes_v3_keys(suite),MAX_WIRE_LEN,pn,suite);
        assert_eq!(tx.seal_in_place(kind,&mut wire,payload.len(),pad).unwrap(),(pn,expected.len()));
        assert_eq!(wire,expected,"Go AES suite={:?} PN={pn}",suite);
        let rx=LaneRxCrypto::new_for_suite(aes_v3_keys(suite),MAX_WIRE_LEN,suite).unwrap();
        let opened=rx.open_in_place(&mut wire).unwrap();
        assert_eq!((opened.pn,opened.kind,opened.payload),(pn,kind,payload.as_slice()));
        count[idx]+=1;
    }
    assert_eq!(count,[7,7]);
}
#[test]
fn r1_crypto_aes_auth_tamper_wrong_suite_and_direction_fail_closed() {
    for suite in [RecordSuite::Aes128Gcm,RecordSuite::Aes256Gcm] {
        let line=AES_V3.lines().find(|x|x.starts_with(&format!("{}|7|",suite as u8))).unwrap();
        let old=unhex(line.split('|').nth(5).unwrap());
        let rx=LaneRxCrypto::new_for_suite(aes_v3_keys(suite),MAX_WIRE_LEN,suite).unwrap();
        // Mutate every byte: must not emit any authenticated business.
        for i in 0..old.len() {
            let mut corrupted=old.clone();corrupted[i]^=0x80;
            assert!(rx.open_in_place(&mut corrupted).is_err(),
                "suite {:?} tamper at index {}",suite,i);
        }
        let other=if suite==RecordSuite::Aes128Gcm {RecordSuite::Aes256Gcm}
                  else {RecordSuite::Aes128Gcm};
        let wrong=LaneRxCrypto::new_for_suite(aes_v3_keys(other),MAX_WIRE_LEN,other).unwrap();
        assert_eq!(wrong.open_in_place(&mut old.clone()),Err(CryptoError::Authentication));
        let mut altered=aes_v3_keys(suite);
        altered.iv[0]^=1;
        let wrong_iv=LaneRxCrypto::new_for_suite(altered,MAX_WIRE_LEN,suite).unwrap();
        assert_eq!(wrong_iv.open_in_place(&mut old.clone()),Err(CryptoError::Authentication));
        let mut altered=aes_v3_keys(suite);
        altered.hp_key[0]^=1;
        let wrong_hp=LaneRxCrypto::new_for_suite(altered,MAX_WIRE_LEN,suite).unwrap();
        assert_eq!(wrong_hp.open_in_place(&mut old.clone()),Err(CryptoError::Authentication));
        assert_eq!(rx.open_in_place(&mut old.clone()).unwrap().payload,b"short");
    }
    for bad in [0,4,255] {
        assert_eq!(RecordSuite::try_from(bad),Err(CryptoError::UnsupportedSuite));
    }
}
#[test]
fn r1_crypto_aes_boundary_hp_tag_overlap_reordering_and_max_wire() {
    for suite in [RecordSuite::Aes128Gcm,RecordSuite::Aes256Gcm] {
        let mut tx=LaneTxCrypto::new_for_suite(aes_v3_keys(suite),MAX_WIRE_LEN,suite).unwrap();
        let rx=LaneRxCrypto::new_for_suite(aes_v3_keys(suite),MAX_WIRE_LEN,suite).unwrap();
        let mut wires=Vec::new();
        for len in [0,1,15,16,17,31,1024,MAX_WIRE_LEN-31] {
            let payload=(0..len).map(|i|(i%251) as u8).collect::<Vec<_>>();
            let mut wire=vec![0;31+len];
            wire[CIPHER_OFFSET+1..CIPHER_OFFSET+1+len].copy_from_slice(&payload);
            tx.seal_in_place(0,&mut wire,len,0).unwrap();
            wires.push((wire,payload));
        }
        // Reverse arrival is legal independent AEAD. Replay/window is deliberately not in M3 yet.
        for (mut wire,payload) in wires.into_iter().rev() {
            let rec=rx.open_in_place(&mut wire).unwrap();
            assert_eq!(rec.payload,payload.as_slice());
        }
        let mut short=vec![0;FIXED_WIRE_OVERHEAD-1];
        assert_eq!(tx.seal_in_place(0,&mut short,0,0),Err(CryptoError::Capacity));
    }
}
#[test]
fn r1_crypto_aes_burn_pn_on_fail_and_refuse_wrap() {
    for suite in [RecordSuite::Aes128Gcm,RecordSuite::Aes256Gcm] {
        let mut tx=LaneTxCrypto::from_test_pn_for_suite(aes_v3_keys(suite),MAX_WIRE_LEN,u64::MAX-1,suite);
        let mut tiny=[0;FIXED_WIRE_OVERHEAD];
        assert_eq!(tx.seal_in_place(0,&mut tiny,1,0),Err(CryptoError::Capacity));
        assert_eq!(tx.seal_in_place(0,&mut tiny,0,0).unwrap().0,u64::MAX);
        assert_eq!(tx.seal_in_place(0,&mut tiny,0,0),Err(CryptoError::PnExhausted));
    }
}
