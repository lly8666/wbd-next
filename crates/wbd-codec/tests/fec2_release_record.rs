//! Release-mode linkage: this test is an integration crate, not cfg(test)
 //! inside the wbd-codec library. Exactly the released opt-in methods.
#![cfg(feature = "fec2-product-record")]
use wbd_codec::record_crypto::{
    DirectionKeys,LaneTxCrypto,RecordSuite,CryptoError,
};
use wbd_codec::record_replay::{
    ReplayProtectedLaneRx,ReplayWindowConfig,UniqueOpenError,
};
fn keys()->DirectionKeys{
    DirectionKeys{aead_key:[0x31;32],iv:[0x42;12],hp_key:[0x53;32]}
}
fn settings()->ReplayWindowConfig{
    ReplayWindowConfig{pn_per_second:1000,cache_horizon_ms:500,
        fec_horizon_ms:500,rtt_ms:40,metadata_budget_bytes:65536}
}
#[test]
fn release_only_explicit_fec2_record_permission_same_pn_replay_and_auth(){
    for suite in [RecordSuite::ChaCha20Poly1305,RecordSuite::Aes128Gcm,RecordSuite::Aes256Gcm]{
        let mut tx=LaneTxCrypto::new_for_suite(keys(),1400,suite).unwrap();
        let mut rx=ReplayProtectedLaneRx::new_for_suite(keys(),1400,suite,settings()).unwrap();
        let mut ordinary=vec![0u8;1400];
        ordinary[14..46].fill(1);
        assert_eq!(tx.seal_in_place(2,&mut ordinary,32,0),Err(CryptoError::InvalidKind));
        // Failed kind admission burned PN0 in the SAME real owner allocator.
        let mut src=vec![0u8;1400];
        src[14..46].fill(2);
        let (pn0,n0)=tx.seal_fec2_after_admission_in_place(2,&mut src,32,0).unwrap();
        assert_eq!(pn0,1);
        src.truncate(n0);
        let sealed_source=src.clone();
        let first=rx.open_unique_with_fec2_after_admission_in_place(&mut src).unwrap();
        assert_eq!(first.kind,2);assert_eq!(first.pn,1);
        assert_eq!(first.payload,&[2u8;32]);
        let mut dup=sealed_source.clone();
        assert!(matches!(rx.open_unique_with_fec2_after_admission_in_place(&mut dup),
            Err(UniqueOpenError::Duplicate)));
        let mut repair=vec![0u8;1400];repair[14..54].fill(3);
        let (pn1,n1)=tx.seal_fec2_after_admission_in_place(3,&mut repair,40,0).unwrap();
        assert_eq!(pn1,2);repair.truncate(n1);
        let mut tampered=repair.clone();
        tampered[20]^=1;
        assert!(matches!(rx.open_unique_with_fec2_after_admission_in_place(&mut tampered),
            Err(UniqueOpenError::InvalidRecord(_))));
        let opened=rx.open_unique_with_fec2_after_admission_in_place(&mut repair).unwrap();
        assert_eq!(opened.kind,3);assert_eq!(opened.pn,2);
        assert_eq!(opened.payload,&[3u8;40]);
        // Full ordinary method must reject FEC2 even for a valid record.
        let mut other_rx=ReplayProtectedLaneRx::new_for_suite(keys(),1400,suite,settings()).unwrap();
        let mut ordinary_attempt=sealed_source;
        assert!(matches!(other_rx.open_unique_in_place(&mut ordinary_attempt),
            Err(UniqueOpenError::InvalidRecord(CryptoError::InvalidKind))));
        let stats=rx.stats();assert_eq!(stats.delivered,2);
        assert_eq!(stats.duplicates,1);assert_eq!(stats.invalid_records,1);
    }
}
