//! Pure C03/C04 authenticated replay tests kept beneath record_frame::
//! so legacy R0 codec's exact 13-test harness remains frozen.
use crate::record_crypto::{CryptoError, DirectionKeys, LaneTxCrypto, RecordSuite};
use crate::record_replay::{ReplayConfigError, ReplayProtectedLaneRx, ReplayWindowConfig, UniqueOpenError};
use crate::record_frame::{FIXED_WIRE_OVERHEAD, MAX_WIRE_LEN};
const DATA_OFFSET:usize=14;

fn keys() -> DirectionKeys {
    DirectionKeys {
        aead_key:[0x37;32], iv:[0x41;12], hp_key:[0x83;32],
    }
}
fn cfg(rate:u64,cache_ms:u64,rtt_ms:u64,bytes:usize)->ReplayWindowConfig {
    ReplayWindowConfig {pn_per_second:rate,cache_horizon_ms:cache_ms,fec_horizon_ms:0,
        rtt_ms,metadata_budget_bytes:bytes}
}
fn wire(suite:RecordSuite,pn:u64,payload:&[u8])->Vec<u8> {
    let mut tx=LaneTxCrypto::from_test_pn_for_suite(keys(),MAX_WIRE_LEN,pn,suite);
    let mut out=vec![0;FIXED_WIRE_OVERHEAD+payload.len()];
    out[DATA_OFFSET..DATA_OFFSET+payload.len()].copy_from_slice(payload);
    assert_eq!(tx.seal_in_place(0,&mut out,payload.len(),0).unwrap().0,pn);
    out
}
fn receiver(suite:RecordSuite,c:ReplayWindowConfig)->ReplayProtectedLaneRx {
    ReplayProtectedLaneRx::new_for_suite(keys(),MAX_WIRE_LEN,suite,c).unwrap()
}

#[test]
fn r1_replay_effective_config_reports_real_page_overhead_and_budget_shrink() {
    let rx=receiver(RecordSuite::ChaCha20Poly1305,cfg(1_000,100,0,80));
    let info=rx.info();
    assert_eq!(info.requested_window_pn,256);
    assert_eq!(info.effective_window_pn,256);
    assert_eq!((info.pages,info.allocated_metadata_bytes),(2,80));
    assert_eq!(info.effective_reorder_ms,256);
    assert!(!info.limited_by_budget);
    let reduced=receiver(RecordSuite::Aes256Gcm,cfg(200_000,10_000,0,120));
    let info=reduced.info();
    assert_eq!(info.requested_window_pn,4_194_304);
    assert_eq!(info.effective_window_pn,512);
    assert_eq!(info.allocated_metadata_bytes,120);
    assert_eq!(info.pages,3);
    assert!(info.limited_by_budget);
    assert_eq!(info.effective_reorder_ms,2);
    assert_eq!(info.required_horizon_ms,10_000);
}

#[test]
fn r1_replay_rejects_invalid_rate_metadata_and_overflow_without_allocating() {
    assert!(matches!(ReplayProtectedLaneRx::new(keys(),MAX_WIRE_LEN,cfg(0,100,0,80)),
        Err(ReplayConfigError::ZeroPnRate)));
    assert!(matches!(ReplayProtectedLaneRx::new(keys(),MAX_WIRE_LEN,cfg(1,100,0,79)),
        Err(ReplayConfigError::TooLittleMetadata)));
    assert!(matches!(ReplayProtectedLaneRx::new(keys(),MAX_WIRE_LEN,cfg(u64::MAX,u64::MAX,u64::MAX,usize::MAX)),
        Err(ReplayConfigError::RequestedWindowOverflow)));
    // The hard per-lane 8MiB cap stays explicit even if caller offers more.
    let rx=receiver(RecordSuite::ChaCha20Poly1305,cfg(1_000,100,0,usize::MAX));
    assert_eq!(rx.info().hard_budget_bytes,8*1024*1024);
    assert!(rx.info().allocated_metadata_bytes<=rx.info().hard_budget_bytes);
}

#[test]
fn r1_replay_three_real_suites_auth_first_duplicate_tamper_wrong_key() {
    for suite in [RecordSuite::ChaCha20Poly1305,RecordSuite::Aes128Gcm,RecordSuite::Aes256Gcm] {
        let mut rx=receiver(suite,cfg(1000,100,0,80));
        let original=wire(suite,4,b"a\0b");
        let mut tampered=original.clone();
        *tampered.last_mut().unwrap() ^= 0x40;
        assert_eq!(rx.open_unique_in_place(&mut tampered),Err(UniqueOpenError::InvalidRecord(CryptoError::Authentication)));
        assert_eq!(rx.max_seen(),None);
        assert_eq!(rx.stats().invalid_records,1);
        let mut first_wire=original.clone();
        let first=rx.open_unique_in_place(&mut first_wire).unwrap();
        assert_eq!((first.pn,first.payload),(4,b"a\0b".as_slice()));
        assert_eq!(rx.open_unique_in_place(&mut original.clone()),Err(UniqueOpenError::Duplicate));
        assert_eq!(rx.max_seen(),Some(4));
        assert_eq!(rx.stats().delivered,1);
        assert_eq!(rx.stats().duplicates,1);
        // Cipher/key-isolated lane never changes this window on a failed auth.
        let other=if suite==RecordSuite::ChaCha20Poly1305 {RecordSuite::Aes128Gcm}
            else {RecordSuite::ChaCha20Poly1305};
        let corrupted=wire(other,100,b"wrong suite");
        assert!(matches!(rx.open_unique_in_place(&mut corrupted.clone()),Err(UniqueOpenError::InvalidRecord(_))));
        assert_eq!(rx.max_seen(),Some(4));
    }
}

#[test]
fn r1_replay_256_tagged_boundary_no_resurrection_with_two_physical_pages() {
    let mut rx=receiver(RecordSuite::ChaCha20Poly1305,cfg(1_000,100,0,80));
    // With a 256-PN interval, [1..256] occupies two pages; allocating only
    // one 256-bit page would falsely treat PN 1 as fresh after PN 256.
    for (pn,expected) in [
        (1u64,"first"),(256,"first"),(255,"first"),
        (1,"duplicate"),(256,"duplicate"),(512,"first"),
        (257,"first"),(255,"retired"),(257,"duplicate"),
    ] {
        let mut owned=wire(RecordSuite::ChaCha20Poly1305,pn,b"tag");
        let actual=rx.open_unique_in_place(&mut owned);
        match expected {
            "duplicate"=>assert_eq!(actual,Err(UniqueOpenError::Duplicate),"pn {pn}"),
            "retired"=>assert_eq!(actual,Err(UniqueOpenError::Retired),"pn {pn}"),
            _=>assert!(actual.is_ok(),"pn {pn} result {actual:?}"),
        };
    }
}

#[test]
fn r1_replay_large_authenticated_jump_is_constant_page_rotation_and_floor_monotone() {
    let mut rx=receiver(RecordSuite::Aes128Gcm,cfg(1_000,100,0,80));
    assert!(rx.open_unique_in_place(&mut wire(RecordSuite::Aes128Gcm,0,b"first")).is_ok());
    let distant=1u64<<52;
    assert!(rx.open_unique_in_place(&mut wire(RecordSuite::Aes128Gcm,distant,b"jump")).is_ok());
    assert_eq!(rx.retired_floor(),distant-255);
    assert_eq!(rx.open_unique_in_place(&mut wire(RecordSuite::Aes128Gcm,0,b"first")),Err(UniqueOpenError::Retired));
    assert!(rx.open_unique_in_place(&mut wire(RecordSuite::Aes128Gcm,distant-255,b"boundary")).is_ok());
    assert_eq!(rx.open_unique_in_place(&mut wire(RecordSuite::Aes128Gcm,distant-255,b"boundary")),Err(UniqueOpenError::Duplicate));
    assert_eq!(rx.max_seen(),Some(distant));
    assert_eq!(rx.retired_floor(),distant-255);
}

#[test]
fn r1_replay_max_u64_never_wraps_or_reaccepts_expired_pn() {
    let suite=RecordSuite::Aes256Gcm;
    let mut rx=receiver(suite,cfg(1000,100,0,80));
    let end=u64::MAX;
    for pn in [end-1,end,end-255] {
        assert!(rx.open_unique_in_place(&mut wire(suite,pn,b"Z")).is_ok());
    }
    assert_eq!(rx.max_seen(),Some(end));
    assert_eq!(rx.retired_floor(),end-255);
    assert_eq!(rx.open_unique_in_place(&mut wire(suite,end-256,b"Z")),Err(UniqueOpenError::Retired));
    assert_eq!(rx.open_unique_in_place(&mut wire(suite,end,b"Z")),Err(UniqueOpenError::Duplicate));
    assert_eq!(rx.stats().delivered,3);
}

#[test]
fn r1_replay_authenticated_out_of_order_and_independent_lane_windows() {
    let suite=RecordSuite::ChaCha20Poly1305;
    let mut a=receiver(suite,cfg(2_000,500,0,400));
    let mut b=receiver(suite,cfg(2_000,500,0,400));
    for pn in [1000,998,999,1001,997] {
        let mut packet=wire(suite,pn,b"ordered");
        assert_eq!(a.open_unique_in_place(&mut packet).unwrap().pn,pn);
    }
    assert_eq!(a.max_seen(),Some(1001));
    assert_eq!(a.stats().delivered,5);
    assert_eq!(a.open_unique_in_place(&mut wire(suite,998,b"ordered")),Err(UniqueOpenError::Duplicate));
    assert_eq!(b.open_unique_in_place(&mut wire(suite,998,b"ordered")).unwrap().pn,998);
    assert_eq!(b.stats().delivered,1);
}

#[test]
fn r1_replay_metadata_pressure_fails_closed_and_no_invalid_record_advances_floor() {
    let suite=RecordSuite::Aes128Gcm;
    let mut rx=receiver(suite,cfg(250_000,1_000,0,80));
    let info=rx.info();
    assert!(info.limited_by_budget);
    assert_eq!(info.effective_window_pn,256);
    let mut junk=wire(suite,u64::MAX,b"junk");
    junk[14]^=0xff;
    assert!(matches!(rx.open_unique_in_place(&mut junk),Err(UniqueOpenError::InvalidRecord(_))));
    assert_eq!(rx.max_seen(),None);
    assert!(rx.open_unique_in_place(&mut wire(suite,1000,b"valid")).is_ok());
    assert_eq!(rx.retired_floor(),745);
    assert_eq!(rx.open_unique_in_place(&mut wire(suite,744,b"old")),Err(UniqueOpenError::Retired));
    assert_eq!(rx.stats().invalid_records,1);
}

#[test]
fn r1_m0_fec2_three_suite_real_replay_shared_with_link_no_kind_bypass(){
    use crate::fec_v2::{source_owned,AUTHENTICATED_FEC2_SOURCE_KIND};
    let f2=source_owned(4097,0,b"independently authenticated source",1400).unwrap();
    for suite in [
        RecordSuite::ChaCha20Poly1305,RecordSuite::Aes128Gcm,RecordSuite::Aes256Gcm
    ] {
        let mut tx=LaneTxCrypto::new_for_suite(keys(),MAX_WIRE_LEN,suite).unwrap();
        let mut normal=receiver(suite,cfg(1000,200,0,8192));
        let mut admitted=receiver(suite,cfg(1000,200,0,8192));
        let build=|tx:&mut LaneTxCrypto,kind:u8,payload:&[u8]|{
            let mut out=vec![0u8;FIXED_WIRE_OVERHEAD+payload.len()];
            out[DATA_OFFSET..DATA_OFFSET+payload.len()].copy_from_slice(payload);
            let (pn,used)=if kind==0 {
                tx.seal_in_place(0,&mut out,payload.len(),0).unwrap()
            } else {
                tx.seal_fec2_after_admission_in_place(kind,&mut out,payload.len(),0).unwrap()
            };
            assert_eq!(used,out.len());
            (pn,out)
        };
        let (p0,ordinary)=build(&mut tx,0,b"old ordinary");
        let (p1,source)=build(&mut tx,AUTHENTICATED_FEC2_SOURCE_KIND,&f2);
        let (p2,later)=build(&mut tx,0,b"later ordinary");
        assert_eq!((p0,p1,p2),(0,1,2));
        // Original unnegotiated opener sees the real authenticated PN but
        // DENIES kind2 before entering the replay bitmap or FEC table.
        assert!(matches!(
            normal.open_unique_in_place(&mut source.clone()),
            Err(UniqueOpenError::InvalidRecord(CryptoError::InvalidKind))
        ));
        assert_eq!(normal.max_seen(),None);
        // FEC2 gated path shares ONE original replay window for all kinds.
        // Out-of-order and small independent ordinary remains permitted.
        let r=admitted.open_unique_with_fec2_after_admission_in_place(
            &mut later.clone()).unwrap();
        assert_eq!((r.pn,r.kind,r.payload),(2,0,b"later ordinary".as_slice()));
        let r=admitted.open_unique_with_fec2_after_admission_in_place(
            &mut source.clone()).unwrap();
        assert_eq!((r.pn,r.kind,r.payload),(1,2,f2.as_slice()));
        assert_eq!(admitted.max_seen(),Some(2));
        assert!(matches!(
            admitted.open_unique_with_fec2_after_admission_in_place(
                &mut source.clone()
            ), Err(UniqueOpenError::Duplicate)
        ));
        let mut modified=ordinary.clone();
        let idx=modified.len()-1;
        modified[idx]^=1;
        assert!(matches!(
            admitted.open_unique_with_fec2_after_admission_in_place(&mut modified),
            Err(UniqueOpenError::InvalidRecord(CryptoError::Authentication))
        ));
        // Failed PN0 authentication did NOT use or retire PN0.
        assert_eq!(admitted.open_unique_with_fec2_after_admission_in_place(
            &mut ordinary.clone()).unwrap().pn,0);
        assert!(matches!(
            admitted.open_unique_in_place(&mut ordinary.clone()),
            Err(UniqueOpenError::Duplicate)
        ));
        assert_eq!(admitted.stats().delivered,3);
    }
}
