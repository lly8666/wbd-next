//! M3-011 real AEAD + PN replay before authenticated WF56 scope gate.
use crate::fec_auth_gate::{
    AdmissionError,AuthFecScopeGate,FecOrigin,GateConfigError,
};
use crate::fec_block_id::{IdConfig,IdError};
use crate::fec_rx::{Config as RxConfig,Direction};
use crate::fec_tx::FecTxOwner;
use crate::record_crypto::{
    DirectionKeys,LaneTxCrypto,RecordSuite,CryptoError,
};
use crate::record_frame::{FIXED_WIRE_OVERHEAD,MAX_WIRE_LEN};
use crate::record_replay::{ReplayWindowConfig,UniqueOpenError};
const LANE:u64=41;
const TUNNEL:u64=987;
fn keys()->DirectionKeys{
    DirectionKeys{aead_key:[0x37;32],iv:[0x41;12],hp_key:[0x83;32]}
}
fn replay()->ReplayWindowConfig{
    ReplayWindowConfig{
        pn_per_second:1000,cache_horizon_ms:100,fec_horizon_ms:100,
        rtt_ms:0,metadata_budget_bytes:80,
    }
}
fn id_cfg(anchor:u64,floor:u64)->IdConfig{
    IdConfig{epoch:7,direction:Direction::ClientToServer,
        anchor,retired_floor:floor,max_forward:1024,max_reorder:1024,
        max_heavy:4,max_compact:4}
}
fn fec_cfg(first:u64)->RxConfig{
    RxConfig{epoch:7,direction:Direction::ClientToServer,
        max_wire:1500,max_heavy_bytes:15000,
        max_heavy_blocks:4,max_compact_blocks:4,first_id_ext:first}
}
fn origin(generation:u32)->FecOrigin{
    FecOrigin::test_only(LANE,TUNNEL,7,Direction::ClientToServer,generation)
}
fn gate(suite:RecordSuite,attested:bool)->AuthFecScopeGate{
    AuthFecScopeGate::new(keys(),suite,MAX_WIRE_LEN,replay(),
        id_cfg(0,0),fec_cfg(1),LANE,TUNNEL,attested.then(||origin(0))).unwrap()
}
fn tx(suite:RecordSuite)->LaneTxCrypto{
    LaneTxCrypto::new_for_suite(keys(),MAX_WIRE_LEN,suite).unwrap()
}
fn record(tx:&mut LaneTxCrypto,kind:u8,payload:&[u8])->Vec<u8>{
    let mut wire=vec![0;FIXED_WIRE_OVERHEAD+payload.len()];
    wire[14..14+payload.len()].copy_from_slice(payload);
    tx.seal_in_place(kind,&mut wire,payload.len(),0).unwrap();
    wire
}
fn fec(id:u64,items:&[&[u8]])->(Vec<Vec<u8>>,Vec<Vec<u8>>){
    let mut fec=FecTxOwner::new(id,10_000).unwrap();
    let mut src=Vec::new();
    for p in items{
        let batch=fec.submit(p,0,4,1500,false).unwrap();
        src.extend(batch.systematic);
        assert!(batch.parity.is_empty());
    }
    let parity=fec.flush_all(32).unwrap().parity;
    (src,parity)
}
#[test]
fn r1_authgate_absent_origin_refuses_even_valid_record_without_consuming_pn(){
    let suite=RecordSuite::Aes128Gcm;
    let mut g=gate(suite,false);
    let mut sender=tx(suite);
    let (src,_)=fec(1,&[b"first"]);
    let wire=record(&mut sender,0,&src[0]);
    for t in [1,1000,14000]{
        assert_eq!(g.accept_record_on_lane(&mut wire.clone(),LANE,TUNNEL,t),
            Err(AdmissionError::AbsentOrigin));
    }
    assert_eq!((g.block_id_stats().distinct_accepted,g.fec_stats().heavy,
        g.stats().replay_rejected),(0,0,0));
    assert_eq!(g.stats().denied_before_open,3);
}
#[test]
fn r1_authgate_real_chacha_aes128_aes256_first_systematic_and_missing_only(){
    for suite in [RecordSuite::ChaCha20Poly1305,
                  RecordSuite::Aes128Gcm,RecordSuite::Aes256Gcm]{
        let mut g=gate(suite,true);let mut sender=tx(suite);
        let (src,parity)=fec(1,&[b"A",b"BC"]);
        let r0=record(&mut sender,0,&src[0]);
        let r1=record(&mut sender,0,&parity[0]);
        let r2=record(&mut sender,0,&src[1]);
        assert_eq!(g.accept_record_on_lane(&mut r0.clone(),LANE,TUNNEL,1).unwrap().systematic,
            vec![(0,b"A".to_vec())]);
        assert_eq!(g.accept_record_on_lane(&mut r1.clone(),LANE,TUNNEL,2).unwrap().recovered,
            vec![(1,b"BC".to_vec())]);
        let late=g.accept_record_on_lane(&mut r2.clone(),LANE,TUNNEL,3).unwrap();
        assert!(late.systematic.is_empty()&&late.recovered.is_empty());
        assert_eq!((g.stats().delivered_systematic,g.stats().delivered_recovered),(1,1));
        assert_eq!(g.accept_record_on_lane(&mut r0.clone(),LANE,TUNNEL,4),
            Err(AdmissionError::Replay(UniqueOpenError::Duplicate)));
        assert_eq!(g.block_id_stats().distinct_accepted,1);
    }
}
#[test]
fn r1_authgate_wrong_route_lane_fails_before_pn_decryption_replay_or_fec(){
    let suite=RecordSuite::Aes256Gcm;
    let mut g=gate(suite,true);let mut sender=tx(suite);
    let (src,_)=fec(1,&[b"good"]);
    let r=record(&mut sender,0,&src[0]);
    assert_eq!(g.accept_record_on_lane(&mut r.clone(),LANE+1,TUNNEL,1),
        Err(AdmissionError::WrongLane));
    assert_eq!(g.accept_record_on_lane(&mut r.clone(),LANE,TUNNEL+1,1),
        Err(AdmissionError::WrongTunnel));
    assert_eq!(g.stats().replay_rejected,0);
    assert_eq!(g.block_id_stats().distinct_accepted,0);
    assert_eq!(g.accept_record_on_lane(&mut r.clone(),LANE,TUNNEL,2).unwrap().systematic,
        vec![(0,b"good".to_vec())]);
}
#[test]
fn r1_authgate_record_tamper_rejects_before_blockid_even_on_valid_fec_geometry(){
    let suite=RecordSuite::ChaCha20Poly1305;
    let mut g=gate(suite,true);let mut sender=tx(suite);
    let (src,_)=fec(1,&[b"valid"]);
    let r=record(&mut sender,0,&src[0]);
    let mut invalid=r.clone();*invalid.last_mut().unwrap()^=1;
    assert_eq!(g.accept_record_on_lane(&mut invalid,LANE,TUNNEL,1),
        Err(AdmissionError::Replay(UniqueOpenError::InvalidRecord(CryptoError::Authentication))));
    assert_eq!(g.block_id_stats().distinct_accepted,0);
    assert_eq!(g.accept_record_on_lane(&mut r.clone(),LANE,TUNNEL,2).unwrap().systematic,
        vec![(0,b"valid".to_vec())]);
}
#[test]
fn r1_authgate_duplicate_pn_rejected_before_fec_even_for_malformed_wire(){
    let suite=RecordSuite::Aes128Gcm;
    let mut g=gate(suite,true);let mut sender=tx(suite);
    let invalid=record(&mut sender,0,b"not-a-valid-WF-shard");
    let a=g.accept_record_on_lane(&mut invalid.clone(),LANE,TUNNEL,1);
    assert!(matches!(a,Err(AdmissionError::BlockId(IdError::Wire(_)))));
    assert_eq!(g.accept_record_on_lane(&mut invalid.clone(),LANE,TUNNEL,2),
        Err(AdmissionError::Replay(UniqueOpenError::Duplicate)));
    assert_eq!(g.block_id_stats().distinct_accepted,0);
    assert_eq!(g.fec_stats().heavy,0);
}
#[test]
fn r1_authgate_origin_constructor_rejects_untrusted_cross_binding(){
    let suite=RecordSuite::ChaCha20Poly1305;
    let check=|orig:FecOrigin,id:IdConfig,rx:RxConfig,lane:u64|{
        AuthFecScopeGate::new(keys(),suite,MAX_WIRE_LEN,replay(),
            id,rx,lane,TUNNEL,Some(orig))
    };
    assert!(matches!(check(origin(0),id_cfg(0,0),fec_cfg(1),LANE+1),
        Err(GateConfigError::OriginLaneMismatch)));
    assert!(matches!(check(FecOrigin::test_only(LANE,TUNNEL+1,7,Direction::ClientToServer,0),
        id_cfg(0,0),fec_cfg(1),LANE),Err(GateConfigError::OriginTunnelMismatch)));
    assert!(matches!(check(FecOrigin::test_only(LANE,TUNNEL,8,Direction::ClientToServer,0),
        id_cfg(0,0),fec_cfg(1),LANE),Err(GateConfigError::OriginEpochMismatch)));
    assert!(matches!(check(FecOrigin::test_only(LANE,TUNNEL,7,Direction::ServerToClient,0),
        id_cfg(0,0),fec_cfg(1),LANE),Err(GateConfigError::OriginDirectionMismatch)));
    assert!(matches!(check(origin(1),id_cfg(0,0),fec_cfg(1),LANE),
        Err(GateConfigError::OriginGenerationMismatch)));
    let mut mismatch=fec_cfg(1);mismatch.epoch=8;
    assert!(matches!(check(origin(0),id_cfg(0,0),mismatch,LANE),
        Err(GateConfigError::MismatchedOwners)));
}
#[test]
fn r1_authgate_half_space_ambiguous_rejected_after_real_replay_before_fec_state(){
    let mut g=gate(RecordSuite::Aes256Gcm,true);
    let mut sender=tx(RecordSuite::Aes256Gcm);
    let (src,_)=fec(1,&[b"one"]);
    let r=record(&mut sender,0,&src[0]);
    assert_eq!(g.accept_record_on_lane(&mut r.clone(),LANE,TUNNEL,1).unwrap().systematic.len(),1);
    let mut ambiguous=src[0].clone();
    ambiguous[4..8].copy_from_slice(&0x8000_0001u32.to_be_bytes());
    let r2=record(&mut sender,0,&ambiguous);
    assert_eq!(g.accept_record_on_lane(&mut r2.clone(),LANE,TUNNEL,2),
        Err(AdmissionError::BlockId(IdError::HalfSpaceAmbiguous)));
    assert_eq!(g.stats().delivered_systematic,1);
    assert_eq!(g.block_id_stats().distinct_accepted,1);
}
#[test]
fn r1_authgate_expired_block_delayed_parity_refused_no_renewal_or_reopen(){
    let mut g=gate(RecordSuite::ChaCha20Poly1305,true);
    let mut sender=tx(RecordSuite::ChaCha20Poly1305);
    let (src,parity)=fec(1,&[b"first",b"second"]);
    let r0=record(&mut sender,0,&src[0]);
    assert_eq!(g.accept_record_on_lane(&mut r0.clone(),LANE,TUNNEL,100).unwrap().systematic.len(),1);
    g.expire(100+3000+10000+1);
    let late=record(&mut sender,0,&parity[0]);
    assert_eq!(g.accept_record_on_lane(&mut late.clone(),LANE,TUNNEL,20000),
        Err(AdmissionError::BlockId(IdError::Retired)));
    assert_eq!(g.fec_stats().heavy,0);
    assert_eq!(g.block_id_stats().distinct_accepted,1);
    assert_eq!(g.stats().delivered_recovered,0);
}
#[test]
fn r1_authgate_pinned_old_go_56b_wire_oracle_and_health_kind_refusal(){
    let pinned=include_str!("../../../r0/fixtures/legacy-link-fec-wire-v1.txt");
    let hex=pinned.lines().find(|l|l.starts_with("fec-source|")).unwrap()
        .split('|').nth(1).unwrap();
    let payload=(0..hex.len()).step_by(2)
        .map(|i|u8::from_str_radix(&hex[i..i+2],16).unwrap()).collect::<Vec<_>>();
    let mut g=AuthFecScopeGate::new(keys(),RecordSuite::ChaCha20Poly1305,
        MAX_WIRE_LEN,replay(),id_cfg(0x01020303,0x01020302),
        fec_cfg(0x01020304),LANE,TUNNEL,Some(origin(0))).unwrap();
    let mut sender=tx(RecordSuite::ChaCha20Poly1305);
    let health=record(&mut sender,1,&payload);
    assert_eq!(g.accept_record_on_lane(&mut health.clone(),LANE,TUNNEL,1),
        Err(AdmissionError::NotLinkRecord));
    let good=record(&mut sender,0,&payload);
    assert_eq!(g.accept_record_on_lane(&mut good.clone(),LANE,TUNNEL,2).unwrap().systematic,
        vec![(0,payload[56..].to_vec())]);
}
#[test]
fn r1_authgate_old_generation_refused_with_explicit_origin_even_at_wrap(){
    let mut cfg=id_cfg(0xffff_fffe,0xffff_fffd);
    cfg.max_forward=1000;
    let mut rx=fec_cfg(u32::MAX as u64);
    rx.max_heavy_bytes=16000;
    let mut gate=AuthFecScopeGate::new(keys(),RecordSuite::Aes128Gcm,
        MAX_WIRE_LEN,replay(),cfg,rx,LANE,TUNNEL,Some(origin(0))).unwrap();
    let mut sender=tx(RecordSuite::Aes128Gcm);
    let (prior,_)=fec(u32::MAX as u64,&[b"prior"]);
    let (new,_)=fec(0x1_0000_0001,&[b"next"]);
    let prior_record=record(&mut sender,0,&prior[0]);
    assert!(gate.accept_record_on_lane(&mut prior_record.clone(),LANE,TUNNEL,1).is_ok());
    let next_record=record(&mut sender,0,&new[0]);
    assert_eq!(gate.accept_record_on_lane(&mut next_record.clone(),LANE,TUNNEL,2),
        Err(AdmissionError::BlockId(IdError::WrongGeneration)));
    assert_eq!(gate.stats().delivered_systematic,1);
}
