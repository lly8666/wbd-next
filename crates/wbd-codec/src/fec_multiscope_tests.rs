//! M3-012: concurrent REAL AEAD + PN replay FEC scope tests.
//! The FecOrigin constructors used here are cfg(test)-only stand-ins;
//! there is no production handshake/exporter or authenticated route source.
use crate::fec_auth_gate::{AdmissionError,AuthFecScopeGate,FecOrigin,GateConfigError};
use crate::fec_block_id::{IdConfig,IdError};
use crate::fec_rx::{Config as RxConfig,Direction};
use crate::fec_tx::FecTxOwner;
use crate::record_crypto::{CryptoError,DirectionKeys,LaneTxCrypto,RecordSuite};
use crate::record_frame::{FIXED_WIRE_OVERHEAD,MAX_WIRE_LEN};
use crate::record_replay::{ReplayWindowConfig,UniqueOpenError};

const LANE:u64=51;
const TUN_A:u64=101;
const TUN_B:u64=202;
const EPOCH:u64=9;
fn keys(seed:u8)->DirectionKeys{
    DirectionKeys{aead_key:[seed;32],iv:[seed.wrapping_add(1);12],
        hp_key:[seed.wrapping_add(2);32]}
}
fn replay()->ReplayWindowConfig{
    ReplayWindowConfig{pn_per_second:1000,cache_horizon_ms:100,
        fec_horizon_ms:100,rtt_ms:0,metadata_budget_bytes:80}
}
fn id_config(epoch:u64,dir:Direction,anchor:u64,floor:u64,heavy:usize,compact:usize)->IdConfig{
    IdConfig{epoch,direction:dir,anchor,retired_floor:floor,
        max_forward:1024,max_reorder:1024,max_heavy:heavy,max_compact:compact}
}
fn rx_config(epoch:u64,dir:Direction,first:u64,bytes:usize,heavy:usize,compact:usize)->RxConfig{
    RxConfig{epoch,direction:dir,max_wire:1500,max_heavy_bytes:bytes,
        max_heavy_blocks:heavy,max_compact_blocks:compact,first_id_ext:first}
}
fn gate(tunnel:u64,dir:Direction,epoch:u64,seed:u8,
    anchor:u64,floor:u64,first:u64,heavy:usize,compact:usize,bytes:usize
)->AuthFecScopeGate{
    let origin=FecOrigin::test_only(LANE,tunnel,epoch,dir,(anchor>>32) as u32);
    AuthFecScopeGate::new(keys(seed),RecordSuite::ChaCha20Poly1305,
        MAX_WIRE_LEN,replay(),
        id_config(epoch,dir,anchor,floor,heavy,compact),
        rx_config(epoch,dir,first,bytes,heavy,compact),
        LANE,tunnel,Some(origin)).unwrap()
}
fn sender(seed:u8)->LaneTxCrypto{
    LaneTxCrypto::new_for_suite(keys(seed),MAX_WIRE_LEN,RecordSuite::ChaCha20Poly1305).unwrap()
}
fn seal(tx:&mut LaneTxCrypto,frame:&[u8])->Vec<u8>{
    let mut out=vec![0;FIXED_WIRE_OVERHEAD+frame.len()];
    out[14..14+frame.len()].copy_from_slice(frame);
    tx.seal_in_place(0,&mut out,frame.len(),0).unwrap();
    out
}
fn wires(id:u64,items:&[&[u8]])->(Vec<Vec<u8>>,Vec<Vec<u8>>){
    let mut tx=FecTxOwner::new(id,10000).unwrap();
    let mut src=Vec::new();let mut parity=Vec::new();
    for item in items {
        let mut emitted=tx.submit(item,0,4,1500,false).unwrap();
        src.append(&mut emitted.systematic);
        parity.append(&mut emitted.parity);
    }
    parity.append(&mut tx.flush_all(32).unwrap().parity);
    (src,parity)
}
#[test]
fn r1_multiscope_four_live_tunnel_direction_scopes_pn0_blockid1_independent(){
    let cases=[
        (TUN_A,Direction::ClientToServer,0x21u8,b"a-up".as_slice()),
        (TUN_A,Direction::ServerToClient,0x31,b"a-down".as_slice()),
        (TUN_B,Direction::ClientToServer,0x41,b"b-up".as_slice()),
        (TUN_B,Direction::ServerToClient,0x51,b"b-down".as_slice()),
    ];
    let mut scopes=cases.iter().map(|&(tunnel,dir,seed,body)|{
        let (src,_)=wires(1,&[body]);
        let mut tx=sender(seed);
        (gate(tunnel,dir,EPOCH,seed,0,0,1,2,2,1000),
         seal(&mut tx,&src[0]),tunnel,body.to_vec())
    }).collect::<Vec<_>>();
    // All four records independently use real AEAD PN=0 and wire BlockID=1.
    // Interleave processing to defeat a global replay or global FEC ID floor.
    for index in [3usize,1,2,0] {
        let (g,wire,tunnel,body)=&mut scopes[index];
        let out=g.accept_record_on_lane(&mut wire.clone(),LANE,*tunnel,100).unwrap();
        assert_eq!(out.systematic,vec![(0,body.clone())]);
        assert_eq!(g.block_id_stats().highest,1);
        assert_eq!(g.stats().delivered_systematic,1);
    }
    for (g,wire,tunnel,_) in &mut scopes {
        assert_eq!(g.accept_record_on_lane(&mut wire.clone(),LANE,*tunnel,101),
            Err(AdmissionError::Replay(UniqueOpenError::Duplicate)));
        assert_eq!(g.stats().delivered_systematic,1);
    }
    scopes[0].0.expire(100+3000+10000+1);
    assert_eq!(scopes[0].0.block_id_stats().retired_floor,1);
    for index in 1..4 {
        assert_eq!(scopes[index].0.block_id_stats().retired_floor,0);
        assert_eq!(scopes[index].0.fec_stats().heavy,1);
    }
}
#[test]
fn r1_multiscope_misrouted_true_aead_ciphertext_denied_without_peer_pn_mutation(){
    let mut ga=gate(TUN_A,Direction::ClientToServer,EPOCH,0x21,0,0,1,2,2,1000);
    let mut gb=gate(TUN_B,Direction::ClientToServer,EPOCH,0x41,0,0,1,2,2,1000);
    let mut sa=sender(0x21);let mut sb=sender(0x41);
    let (src,_)=wires(1,&[b"same-blockid"]);
    let wa=seal(&mut sa,&src[0]);let wb=seal(&mut sb,&src[0]);
    // Misrouting on A's external tunnel route is stopped before any AEAD.
    assert_eq!(gb.accept_record_on_lane(&mut wa.clone(),LANE,TUN_A,1),
        Err(AdmissionError::WrongTunnel));
    assert_eq!(gb.stats().replay_rejected,0);
    // Forging B's route cannot turn A's genuine ciphertext into B's key.
    assert!(matches!(
        gb.accept_record_on_lane(&mut wa.clone(),LANE,TUN_B,2),
        Err(AdmissionError::Replay(UniqueOpenError::InvalidRecord(CryptoError::Authentication)))
    ));
    assert_eq!(gb.block_id_stats().distinct_accepted,0);
    assert_eq!(gb.accept_record_on_lane(&mut wb.clone(),LANE,TUN_B,3).unwrap().systematic,
        vec![(0,b"same-blockid".to_vec())]);
    assert_eq!(ga.accept_record_on_lane(&mut wa.clone(),LANE,TUN_A,4).unwrap().systematic,
        vec![(0,b"same-blockid".to_vec())]);
    assert_eq!((ga.stats().delivered_systematic,gb.stats().delivered_systematic),(1,1));
}
#[test]
fn r1_multiscope_opposite_direction_keys_and_replayed_ciphertext_do_not_cross(){
    let mut up=gate(TUN_A,Direction::ClientToServer,EPOCH,0x21,0,0,1,2,2,1000);
    let mut down=gate(TUN_A,Direction::ServerToClient,EPOCH,0x31,0,0,1,2,2,1000);
    let mut su=sender(0x21);let mut sd=sender(0x31);
    let (src,_)=wires(1,&[b"duplex"]);
    let wu=seal(&mut su,&src[0]);let wd=seal(&mut sd,&src[0]);
    assert!(matches!(down.accept_record_on_lane(&mut wu.clone(),LANE,TUN_A,1),
        Err(AdmissionError::Replay(UniqueOpenError::InvalidRecord(_)))));
    assert_eq!(down.block_id_stats().highest,0);
    assert_eq!(down.accept_record_on_lane(&mut wd.clone(),LANE,TUN_A,2).unwrap().systematic,
        vec![(0,b"duplex".to_vec())]);
    assert_eq!(up.accept_record_on_lane(&mut wu.clone(),LANE,TUN_A,3).unwrap().systematic,
        vec![(0,b"duplex".to_vec())]);
    assert_eq!(up.accept_record_on_lane(&mut wu.clone(),LANE,TUN_A,4),
        Err(AdmissionError::Replay(UniqueOpenError::Duplicate)));
    assert_eq!(down.accept_record_on_lane(&mut wd.clone(),LANE,TUN_A,5),
        Err(AdmissionError::Replay(UniqueOpenError::Duplicate)));
}
#[test]
fn r1_multiscope_one_tunnel_expiration_and_delayed_parity_do_not_retire_peer(){
    let mut a=gate(TUN_A,Direction::ClientToServer,EPOCH,0x21,0,0,1,2,2,1000);
    let mut b=gate(TUN_B,Direction::ClientToServer,EPOCH,0x41,0,0,1,2,2,1000);
    let mut sa=sender(0x21);let mut sb=sender(0x41);
    let (src,parity)=wires(1,&[b"left",b"right"]);
    let pa=seal(&mut sa,&src[0]);let pb=seal(&mut sb,&src[0]);
    assert_eq!(a.accept_record_on_lane(&mut pa.clone(),LANE,TUN_A,100).unwrap().systematic.len(),1);
    assert_eq!(b.accept_record_on_lane(&mut pb.clone(),LANE,TUN_B,101).unwrap().systematic.len(),1);
    a.expire(13101);
    assert_eq!(a.block_id_stats().retired_floor,1);
    assert_eq!(b.block_id_stats().retired_floor,0);
    // A new authenticated parity PN may not resurrect A's expired shard.
    let old_parity=seal(&mut sa,&parity[0]);
    assert_eq!(a.accept_record_on_lane(&mut old_parity.clone(),LANE,TUN_A,14000),
        Err(AdmissionError::BlockId(IdError::Retired)));
    let valid_parity=seal(&mut sb,&parity[0]);
    assert_eq!(b.accept_record_on_lane(&mut valid_parity.clone(),LANE,TUN_B,102).unwrap().recovered,vec![(1,b"right".to_vec())]);
    assert_eq!(b.fec_stats().compact,1);
    assert_eq!((b.stats().delivered_systematic,b.stats().delivered_recovered),(1,1));
}
#[test]
fn r1_multiscope_one_tunnel_pressure_exhausts_compact_without_peer_revival(){
    let mut a=gate(TUN_A,Direction::ClientToServer,EPOCH,0x21,0,0,1,1,1,4);
    let mut b=gate(TUN_B,Direction::ClientToServer,EPOCH,0x41,0,0,1,1,1,4);
    let mut sa=sender(0x21);let mut sb=sender(0x41);
    let (w1,_)=wires(1,&[b"1111"]);
    let (w2,_)=wires(2,&[b"2222"]);
    let (w3,_)=wires(3,&[b"3333"]);
    let ba=seal(&mut sa,&w1[0]);let bb=seal(&mut sb,&w1[0]);
    assert_eq!(a.accept_record_on_lane(&mut ba.clone(),LANE,TUN_A,1).unwrap().systematic.len(),1);
    assert_eq!(b.accept_record_on_lane(&mut bb.clone(),LANE,TUN_B,1).unwrap().systematic.len(),1);
    for (at,w) in [(2,&w2[0]),(3,&w3[0])] {
        let record=seal(&mut sa,w);
        assert_eq!(a.accept_record_on_lane(&mut record.clone(),LANE,TUN_A,at).unwrap().systematic.len(),1);
        assert!(a.fec_stats().heavy<=1);
        assert!(a.block_id_stats().heavy<=1);
        assert!(a.block_id_stats().compact<=1);
    }
    assert!(a.block_id_stats().retired_floor>=1);
    assert_eq!(a.accept_record_on_lane(&mut seal(&mut sa,&w1[0]),LANE,TUN_A,4),
        Err(AdmissionError::BlockId(IdError::Retired)));
    assert_eq!(b.block_id_stats().retired_floor,0);
    assert_eq!(b.fec_stats().heavy,1);
    assert_eq!(b.stats().delivered_systematic,1);
}
#[test]
fn r1_multiscope_rekey_isolation_old_ciphertext_parity_and_pn0_new_epoch(){
    let mut old=gate(TUN_A,Direction::ClientToServer,EPOCH,0x21,0,0,1,2,2,1000);
    let mut new=gate(TUN_A,Direction::ClientToServer,EPOCH+1,0x61,
        0x1_0000_0000,0x1_0000_0000,0x1_0000_0001,2,2,1000);
    let mut so=sender(0x21);let mut sn=sender(0x61);
    let (old_src,old_parity)=wires(1,&[b"obsolete",b"source"]);
    let (new_src,_)=wires(0x1_0000_0001,&[b"new-session"]);
    let pre=seal(&mut so,&old_src[0]);
    assert_eq!(old.accept_record_on_lane(&mut pre.clone(),LANE,TUN_A,1).unwrap().systematic.len(),1);
    let stale_parity=seal(&mut so,&old_parity[0]);
    assert!(matches!(new.accept_record_on_lane(&mut stale_parity.clone(),LANE,TUN_A,2),
        Err(AdmissionError::Replay(UniqueOpenError::InvalidRecord(_)))));
    assert_eq!(new.block_id_stats().highest,0x1_0000_0000);
    // Newly rekeyed sender restarts PN at zero; must not inherit old replay.
    let fresh=seal(&mut sn,&new_src[0]);
    assert_eq!(new.accept_record_on_lane(&mut fresh.clone(),LANE,TUN_A,3).unwrap().systematic,
        vec![(0,b"new-session".to_vec())]);
    old.expire(15000);
    assert!(old.block_id_stats().retired_floor>=1);
    assert_eq!(new.block_id_stats().highest,0x1_0000_0001);
    assert_eq!(new.stats().delivered_systematic,1);
}
#[test]
fn r1_multiscope_blockid_wrap_ffffffff_to_one_in_distinct_trusted_generations(){
    let mut prev=gate(TUN_A,Direction::ClientToServer,EPOCH,0x21,
        0xffff_fffe,0xffff_fffd,0xffff_ffff,2,2,1000);
    let mut next=gate(TUN_B,Direction::ClientToServer,EPOCH+1,0x41,
        0x1_0000_0000,0x1_0000_0000,0x1_0000_0001,2,2,1000);
    let mut sp=sender(0x21);let mut sn=sender(0x41);
    let (last,_)=wires(0xffff_ffff,&[b"last"]);
    let (first,_)=wires(0x1_0000_0001,&[b"first"]);
    assert_eq!(prev.accept_record_on_lane(&mut seal(&mut sp,&last[0]),LANE,TUN_A,1).unwrap().systematic,
        vec![(0,b"last".to_vec())]);
    assert_eq!(next.accept_record_on_lane(&mut seal(&mut sn,&first[0]),LANE,TUN_B,1).unwrap().systematic,
        vec![(0,b"first".to_vec())]);
    let wrong=seal(&mut sp,&first[0]);
    assert_eq!(prev.accept_record_on_lane(&mut wrong.clone(),LANE,TUN_A,2),
        Err(AdmissionError::BlockId(IdError::WrongGeneration)));
    assert_eq!(prev.block_id_stats().highest,0xffff_ffff);
    assert_eq!(next.block_id_stats().highest,0x1_0000_0001);
}
#[test]
fn r1_multiscope_old_go_56b_oracle_identical_wire_separately_aead_admitted(){
    let fixture=include_str!("../../../r0/fixtures/legacy-link-fec-wire-v1.txt");
    let hex=fixture.lines().find(|line|line.starts_with("fec-source|"))
        .unwrap().split('|').nth(1).unwrap();
    let wire=(0..hex.len()).step_by(2)
        .map(|i|u8::from_str_radix(&hex[i..i+2],16).unwrap())
        .collect::<Vec<_>>();
    assert_eq!(wire.len(),59);
    let make=|tunnel:u64,dir:Direction,seed:u8|{
        gate(tunnel,dir,EPOCH,seed,0x01020303,0x01020302,
             0x01020304,2,2,1000)
    };
    let mut a=make(TUN_A,Direction::ClientToServer,0x21);
    let mut b=make(TUN_B,Direction::ServerToClient,0x31);
    let mut sa=sender(0x21);let mut sb=sender(0x31);
    let ra=seal(&mut sa,&wire);let rb=seal(&mut sb,&wire);
    assert_eq!(a.accept_record_on_lane(&mut ra.clone(),LANE,TUN_A,1).unwrap().systematic,
        vec![(0,wire[56..].to_vec())]);
    assert_eq!(b.accept_record_on_lane(&mut rb.clone(),LANE,TUN_B,1).unwrap().systematic,
        vec![(0,wire[56..].to_vec())]);
    a.expire(14000);
    assert_eq!(a.block_id_stats().retired_floor,0x01020304);
    assert_eq!(b.block_id_stats().retired_floor,0x01020303);
    assert_eq!(b.stats().delivered_systematic,1);
}
#[test]
fn r1_multiscope_unbound_and_origin_mismatch_cannot_admit_other_scope(){
    let mut absent=AuthFecScopeGate::new(keys(0x21),
        RecordSuite::ChaCha20Poly1305,MAX_WIRE_LEN,replay(),
        id_config(EPOCH,Direction::ClientToServer,0,0,2,2),
        rx_config(EPOCH,Direction::ClientToServer,1,1000,2,2),
        LANE,TUN_A,None).unwrap();
    let (src,_)=wires(1,&[b"valid"]);
    let mut tx=sender(0x21);let r=seal(&mut tx,&src[0]);
    assert_eq!(absent.accept_record_on_lane(&mut r.clone(),LANE,TUN_A,1),
        Err(AdmissionError::AbsentOrigin));
    assert_eq!(absent.block_id_stats().distinct_accepted,0);
    assert_eq!(absent.stats().replay_rejected,0);
    let bad=AuthFecScopeGate::new(keys(0x21),
        RecordSuite::ChaCha20Poly1305,MAX_WIRE_LEN,replay(),
        id_config(EPOCH,Direction::ClientToServer,0,0,2,2),
        rx_config(EPOCH,Direction::ClientToServer,1,1000,2,2),
        LANE,TUN_A,Some(FecOrigin::test_only(LANE,TUN_B,EPOCH,Direction::ClientToServer,0)));
    assert!(matches!(bad,Err(GateConfigError::OriginTunnelMismatch)));
}
