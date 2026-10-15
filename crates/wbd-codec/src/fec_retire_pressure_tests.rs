//! M0 task 010: deterministic fake-monotone-clock, authenticated-input
//! multi-block FEC RX / BlockID pressure and timer adversarial regressions.
//! Tests are intentionally scoped below link_fec_wire (frozen R0 selector).
use crate::fec_rx::{
    Config as RxConfig,Direction,FecRxOwner,RxError,Scope,
    HEAVY_TTL_MS as RX_HEAVY,COMPACT_TTL_MS as RX_COMPACT,
};
use crate::fec_block_id::{
    AuthenticatedContext,FecBlockIdOwner,IdConfig,IdError,
    HEAVY_MS as ID_HEAVY,COMPACT_MS as ID_COMPACT,
};
use crate::fec_tx::FecTxOwner;
use crate::link_fec_wire::{inspect_fec_frame,FEC_HEADER,FEC_PARITY_PROFILES};

fn rx_cfg(bytes:usize,heavy:usize,compact:usize,first:u64)->RxConfig{
    RxConfig{epoch:7,direction:Direction::ClientToServer,
        max_wire:1500,max_heavy_bytes:bytes,max_heavy_blocks:heavy,
        max_compact_blocks:compact,first_id_ext:first}
}
fn scope(id:u64)->Scope{
    Scope{epoch:7,direction:Direction::ClientToServer,id_ext:id}
}
fn ctx(generation:u32)->AuthenticatedContext{
    AuthenticatedContext{epoch:7,direction:Direction::ClientToServer,
        trusted_generation:generation}
}
fn id_cfg(anchor:u64,floor:u64,heavy:usize,compact:usize)->IdConfig{
    IdConfig{epoch:7,direction:Direction::ClientToServer,
        anchor,retired_floor:floor,max_forward:1024,max_reorder:1024,
        max_heavy:heavy,max_compact:compact}
}
fn tx_wires(id:u64,r:u8,bodies:&[&[u8]])->(Vec<Vec<u8>>,Vec<Vec<u8>>){
    let mut tx=FecTxOwner::new(id,100_000).unwrap();
    let mut source=Vec::new();let mut parity=Vec::new();
    for body in bodies{
        let mut batch=tx.submit(body,0,r,1500,false).unwrap();
        source.append(&mut batch.systematic);parity.append(&mut batch.parity);
    }
    parity.append(&mut tx.flush_all(32).unwrap().parity);
    (source,parity)
}
#[test]
fn r1_retire_late_heavy_timer_catches_up_through_compact_10s_without_resurrection(){
    let (source,parity)=tx_wires(1,4,&[b"AAAA",b"BBBB"]);
    let mut rx=FecRxOwner::new(rx_cfg(256,2,4,1)).unwrap();
    assert_eq!(rx.push_after_auth(&source[0],scope(1),100).unwrap().systematic,
        vec![(0,b"AAAA".to_vec())]);
    // Callback fires after BOTH immutable horizons elapsed. A single call
    // MUST expire both stages, rather than starting a fresh 10s at now.
    rx.expire(100+RX_HEAVY+RX_COMPACT+1);
    assert_eq!((rx.stats().heavy,rx.stats().compact),(0,0));
    assert!(rx.stats().floor.unwrap_or(0)>=1);
    assert_eq!(rx.push_after_auth(&source[0],scope(1),99_999),Err(RxError::Retired));
    assert_eq!(rx.push_after_auth(&parity[0],scope(1),100_000),Err(RxError::Retired));
    assert_eq!((rx.stats().systematic,rx.stats().recovered),(1,0));
}
#[test]
fn r1_retire_multi_block_oldest_pressure_late_systematic_compact_first_delivery(){
    let (a,ap)=tx_wires(10,4,&[b"aaaaa",b"bbbbb"]);
    let (b,_)=tx_wires(11,4,&[b"ccccc"]);
    let mut rx=FecRxOwner::new(rx_cfg(5,1,3,1)).unwrap();
    assert_eq!(rx.push_after_auth(&a[0],scope(10),1).unwrap().systematic,
        vec![(0,b"aaaaa".to_vec())]);
    assert_eq!(rx.push_after_auth(&b[0],scope(11),2).unwrap().systematic,
        vec![(0,b"ccccc".to_vec())]);
    assert_eq!((rx.stats().heavy,rx.stats().compact,rx.stats().heavy_bytes),(1,1,5));
    assert!(rx.push_after_auth(&ap[0],scope(10),3).unwrap().recovered.is_empty());
    assert_eq!(rx.push_after_auth(&a[1],scope(10),4).unwrap().systematic,
        vec![(1,b"bbbbb".to_vec())]);
    assert!(rx.push_after_auth(&a[1],scope(10),5).unwrap().systematic.is_empty());
    assert!(rx.stats().heavy_bytes<=5);
    assert_eq!(rx.stats().systematic,3);
}
#[test]
fn r1_retire_parity_first_r_profiles_recover_only_missing_never_redeliver(){
    for r in FEC_PARITY_PROFILES{
        let (source,parity)=tx_wires(50,r,&[b"A",b"BB",b"CCC"]);
        assert_eq!(parity.len(),3);
        let h=inspect_fec_frame(&parity[0],1500).unwrap().header;
        assert_eq!(h.parity_count,r);
        assert_eq!(h.data_count,3);
        assert_eq!(&h.lengths[..3],&[1,2,3]);
        let mut rx=FecRxOwner::new(rx_cfg(256,2,3,1)).unwrap();
        // One systematic delivered immediately despite no final metadata.
        assert_eq!(rx.push_after_auth(&source[0],scope(50),10).unwrap().systematic,
            vec![(0,b"A".to_vec())]);
        assert!(rx.push_after_auth(&parity[0],scope(50),11).unwrap().recovered.is_empty());
        assert_eq!(rx.push_after_auth(&parity[1],scope(50),12).unwrap().recovered,
            vec![(1,b"BB".to_vec()),(2,b"CCC".to_vec())]);
        assert_eq!((rx.stats().heavy,rx.stats().compact),(0,1));
        for wire in source.iter().chain(parity.iter()){
            let out=rx.push_after_auth(wire,scope(50),13).unwrap();
            assert!(out.systematic.is_empty()&&out.recovered.is_empty());
        }
        assert_eq!((rx.stats().systematic,rx.stats().recovered),(1,2));
    }
}
#[test]
fn r1_retire_malformed_final_conflict_tombstones_while_other_blocks_survive(){
    let (one,parity)=tx_wires(1,4,&[b"ab",b"XYZ"]);
    let (two,_)=tx_wires(2,4,&[b"OK"]);
    let mut rx=FecRxOwner::new(rx_cfg(100,2,2,1)).unwrap();
    rx.push_after_auth(&one[0],scope(1),1).unwrap();
    rx.push_after_auth(&two[0],scope(2),2).unwrap();
    let mut bad=parity[0].clone();
    bad[17]=3; // wrong known source len: 2 -> 3, still valid header
    assert_eq!(rx.push_after_auth(&bad,scope(1),3),Err(RxError::Metadata));
    assert_eq!(rx.push_after_auth(&parity[0],scope(1),4),Err(RxError::Metadata));
    assert!(rx.push_after_auth(&two[0],scope(2),5).unwrap().systematic.is_empty());
    assert_eq!(rx.stats().systematic,2);
    assert_eq!(rx.stats().conflicts,1); // tombstone retry not a second conflict
}
#[test]
fn r1_retire_capacity_floor_cannot_recreate_old_unseen_block_or_old_parity(){
    let (ten,_)=tx_wires(10,4,&[b"AAAAA"]);
    let (twenty,_)=tx_wires(20,4,&[b"BBBBB"]);
    let (five,fp)=tx_wires(5,4,&[b"CCCCC"]);
    let mut rx=FecRxOwner::new(rx_cfg(5,1,1,1)).unwrap();
    rx.push_after_auth(&ten[0],scope(10),1).unwrap();
    rx.push_after_auth(&twenty[0],scope(20),2).unwrap();
    assert_eq!(rx.push_after_auth(&five[0],scope(5),3),Err(RxError::Retired));
    assert!(rx.stats().floor.unwrap_or(0)>=10);
    assert_eq!(rx.push_after_auth(&fp[0],scope(5),4),Err(RxError::Retired));
    assert!(rx.push_after_auth(&twenty[0],scope(20),5).unwrap().systematic.is_empty());
    assert_eq!(rx.stats().systematic,2);
}
#[test]
fn r1_retire_wire_wrap_trusted_epoch_direction_generation_and_rx_delivery(){
    let (end,_)=tx_wires(u32::MAX as u64,4,&[b"OLD"]);
    let (next,parity)=tx_wires(0x1_0000_0001,4,&[b"NEW",b"TAIL"]);
    let mut ids=FecBlockIdOwner::new(id_cfg(0xffff_fffe,0xffff_fffd,2,2)).unwrap();
    let mut rx=FecRxOwner::new(rx_cfg(100,2,4,u32::MAX as u64)).unwrap();
    let o=ids.observe_wire_after_auth(&end[0],1500,ctx(0),1).unwrap();
    assert_eq!(rx.push_after_auth(&end[0],o.rx_scope(ctx(0)),1).unwrap().systematic,
        vec![(0,b"OLD".to_vec())]);
    assert!(matches!(ids.observe_wire_after_auth(&next[0],1500,ctx(0),2),
        Err(IdError::WrongGeneration)));
    let mut wrong=ctx(1);wrong.direction=Direction::ServerToClient;
    assert_eq!(ids.observe_wire_after_auth(&next[0],1500,wrong,2),Err(IdError::WrongDirection));
    wrong=ctx(1);wrong.epoch=8;
    assert_eq!(ids.observe_wire_after_auth(&next[0],1500,wrong,2),Err(IdError::WrongEpoch));
    let o=ids.observe_wire_after_auth(&next[0],1500,ctx(1),3).unwrap();
    assert_eq!(o.id_ext,0x1_0000_0001);
    assert_eq!(rx.push_after_auth(&next[0],o.rx_scope(ctx(1)),3).unwrap().systematic,
        vec![(0,b"NEW".to_vec())]);
    let o=ids.observe_wire_after_auth(&parity[0],1500,ctx(1),4).unwrap();
    assert_eq!(rx.push_after_auth(&parity[0],o.rx_scope(ctx(1)),4).unwrap().recovered,
        vec![(1,b"TAIL".to_vec())]);
    ids.advance_retired_floor(u32::MAX as u64);
    assert_eq!(ids.observe_wire_after_auth(&end[0],1500,ctx(0),5),Err(IdError::Retired));
    assert!(rx.push_after_auth(&next[1],o.rx_scope(ctx(1)),6).unwrap().systematic.is_empty());
}
#[test]
fn r1_retire_blockid_late_timer_heavy_and_compact_expire_in_single_event(){
    let mut ids=FecBlockIdOwner::new(id_cfg(0,0,2,2)).unwrap();
    ids.observe_id_after_auth(1,ctx(0),100).unwrap();
    ids.expire(100+ID_HEAVY+ID_COMPACT+1);
    assert_eq!((ids.stats().heavy,ids.stats().compact,ids.stats().retired_floor),(0,0,1));
    assert_eq!(ids.observe_id_after_auth(1,ctx(0),99_999),Err(IdError::Retired));
}
#[test]
fn r1_retire_go_pinned_56b_source_oracle_wrong_generation_does_not_alloc(){
    let fixture=include_str!("../../../r0/fixtures/legacy-link-fec-wire-v1.txt");
    let src=fixture.lines().find(|x|x.starts_with("fec-source|")).unwrap()
        .split('|').nth(1).unwrap();
    let wire=(0..src.len()).step_by(2)
        .map(|i|u8::from_str_radix(&src[i..i+2],16).unwrap()).collect::<Vec<_>>();
    assert_eq!(wire.len(),FEC_HEADER+3);
    let mut ids=FecBlockIdOwner::new(id_cfg(0x01020303,0x01020302,2,2)).unwrap();
    assert_eq!(ids.observe_wire_after_auth(&wire,59,ctx(1),10),Err(IdError::WrongGeneration));
    assert_eq!(ids.stats().distinct_accepted,0);
    let got=ids.observe_wire_after_auth(&wire,59,ctx(0),10).unwrap();
    assert_eq!(got.id_ext,0x01020304);
    assert_eq!(ids.stats().distinct_accepted,1);
}
