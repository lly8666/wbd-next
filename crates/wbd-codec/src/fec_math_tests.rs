//! True R1 GF RS proof. Old-Go native stdlib oracle pinned to a7a82db3.
//! Kept inside LINK tree to protect frozen historical R0 13-case selection.
use crate::fec_math::{ReedSolomon20,FecMathError};
use crate::link_fec_wire::{
    inspect_fec_frame,FecHeader,FecShardPhase,FEC_DATA_SHARDS,FEC_HEADER,
};
fn source(k:usize,len:usize)->Vec<Vec<u8>>{
    (0..k).map(|i|(0..len).map(|j|(i*13+j*7+5) as u8).collect()).collect()
}
fn meta(k:usize,len:usize,profile:u8)->FecHeader{
    let mut lengths=[0u16;FEC_DATA_SHARDS];
    for n in lengths.iter_mut().take(k){*n=len as u16;}
    FecHeader {block_id:0x01020304,shard_index:20,parity_count:profile,
        data_count:k as u8,shard_size:len as u16,lengths,phase:FecShardPhase::FinalParity}
}
#[test]
fn r1_fec_original_go_generator_20x20_rows_and_identity() {
    let rs=ReedSolomon20::new().unwrap();
    for i in 0..20 {for j in 0..20{
        assert_eq!(rs.generator_row(i).unwrap()[j],u8::from(i==j));
    }}
    // Literal Go1.23.2 oracle from pinned Go fec.go buildGenerator(), not Rust-computed expectation.
    assert_eq!(rs.generator_row(20).unwrap().as_slice(),
        &[0xad,0x78,0x44,0x97,0x7b,0x13,0x6e,0x1d,0x3d,0x0f,0x80,0xc8,0x2d,0xcb,0x81,0x6f,0xd5,0xbd,0x39,0x3f]);
    assert_eq!(rs.generator_row(39).unwrap().as_slice(),
        &[0x2d,0x31,0x16,0x11,0x5a,0x13,0x70,0xcc,0xaa,0xe0,0x49,0x03,0x66,0x0f,0xc1,0x06,0x76,0x73,0xe3,0xa7]);
}
#[test]
fn r1_fec_old_go_independent_k2_partial_parity_exact_bytes() {
    let rs=ReedSolomon20::new().unwrap();
    let a=[1u8,2,3];let b=[0xa0,0xb1,0xc2,0xd3,0xe4];
    let out=rs.encode_active(&[&a,&b],4).unwrap();
    assert_eq!(out,vec![vec![0xc0,0x81,0xa7,0xe6,0xfb],
                        vec![0x67,0x58,0xbb,0x84,0xf9],
                        vec![0xf3,0xdf,0x1b,0x37,0x10],
                        vec![0xed,0x71,0xb4,0x28,0xcc]]);
    let mut hdr=meta(2,5,4);hdr.lengths[0]=3;
    let candidates=vec![(20,out[0].as_slice()),(22,out[2].as_slice())];
    let recovered=rs.recover_missing(&hdr,&[None,None],&candidates).unwrap();
    assert_eq!(recovered,vec![(0,a.to_vec()),(1,b.to_vec())]);
}
#[test]
fn r1_fec_go_full20_generator_parity_first_and_last_exact_bytes() {
    let rs=ReedSolomon20::new().unwrap();
    let src=source(20,17);
    let refs=src.iter().map(Vec::as_slice).collect::<Vec<_>>();
    let parity=rs.encode_active(&refs,20).unwrap();
    assert_eq!(parity.len(),20);
    assert_eq!(parity[0],
        vec![0x38,0xea,0x8c,0x70,0x4d,0xc0,0x2f,0xc2,0x60,0x3e,0xb8,0xe3,0xbc,0x6b,0x5e,0xf1,0x1f]);
    assert_eq!(parity[19],
        vec![0xe2,0xef,0x1c,0x2c,0xc4,0xfe,0xc5,0x5f,0xa1,0xe4,0x6f,0xb2,0x90,0x33,0xe6,0x6a,0x85]);
    let p=parity.iter().enumerate().map(|(i,p)|((20+i) as u8,p.as_slice())).collect::<Vec<_>>();
    assert_eq!(rs.recover_missing(&meta(20,17,20),&vec![None;20],&p).unwrap(),
        src.into_iter().enumerate().collect::<Vec<_>>());
}
#[test]
fn r1_fec_go_streaming_header_and_partial_final_wire_exact_geometry() {
    let rs=ReedSolomon20::new().unwrap();
    let src=[0xaa,0xbb,0xcc];
    let wire=rs.streaming_wire(0x01020304,0,&src,4,59).unwrap();
    let golden="5746010001020304001404140003000100030000000000000000000000000000000000000000000000000000000000000000000000000000000000aabbcc";
    let expected=(0..golden.len()).step_by(2).map(|i|u8::from_str_radix(&golden[i..i+2],16).unwrap()).collect::<Vec<_>>();
    assert_eq!(wire,expected);
    let head=inspect_fec_frame(&wire,59).unwrap();
    assert_eq!(head.header.phase,FecShardPhase::StreamingSource);
    assert_eq!(head.shard,&src);
    assert_eq!(rs.streaming_wire(1,0,&src,4,58),Err(FecMathError::InvalidLength));
    let packet=rs.final_parity_wires(7,&[&src],20,59).unwrap();
    assert_eq!(packet.len(),1);
    let decoded=inspect_fec_frame(&packet[0],59).unwrap();
    assert_eq!(decoded.header.parity_count,20);
    assert_eq!((decoded.header.data_count,decoded.header.shard_index),(1,20));
    assert_eq!(decoded.header.lengths[0],3);
    assert_eq!(decoded.shard.len(),3);
}
#[test]
fn r1_fec_all_k1_to20_all_six_profiles_e_direct_inverse_and_lengths() {
    let rs=ReedSolomon20::new().unwrap();
    for k in 1..=20 {
        for profile in [4u8,8,10,12,16,20] {
            for len in [1,15,31,32,63,64,65,512] {
                let src=source(k,len);
                let refs=src.iter().map(Vec::as_slice).collect::<Vec<_>>();
                let parity=rs.encode_active(&refs,profile).unwrap();
                assert_eq!(parity.len(),k.min(profile as usize));
                for e in [1usize,2,3,4] {
                    if e>k || e>parity.len(){continue;}
                    let missing=(0..e).map(|j|(j*7)%k).collect::<Vec<_>>();
                    // Deduplicate deterministic sample, e.g. k=7 => select first e.
                    let missing=if missing.iter().collect::<std::collections::BTreeSet<_>>().len()==e {
                        missing
                    } else {(0..e).collect::<Vec<_>>()};
                    let inputs=(0..k).map(|i|if missing.contains(&i){None}else{Some(src[i].as_slice())})
                        .collect::<Vec<_>>();
                    let selected=parity.iter().enumerate().rev()
                        .take(e).map(|(idx,p)|((20+idx) as u8,p.as_slice())).collect::<Vec<_>>();
                    let decoded=rs.recover_missing(&meta(k,len,profile),&inputs,&selected).unwrap();
                    assert_eq!(decoded.len(),e);
                    for (i,recovered) in decoded{assert_eq!(recovered,src[i],
                        "k={k} profile={profile} L={len} missing={i}");}
                }
            }
        }
    }
}
#[test]
fn r1_fec_short_block_zero_tail_and_inactive_poison_does_not_leak() {
    let rs=ReedSolomon20::new().unwrap();
    let a=[0xaau8,0xbb,0xcc];let b=[0x10u8];
    let expected=rs.encode_active(&[&a,&b],20).unwrap();
    let oversized=[0x10,0xf3,0xf4];
    let poisoned=rs.encode_active(&[&a,&oversized],20).unwrap();
    assert_ne!(expected,poisoned);
    let mut h=meta(2,3,20);h.lengths[0]=3;h.lengths[1]=1;
    let rebuilt=rs.recover_missing(&h,&[Some(&a),None],
        &[(20,expected[0].as_slice())]).unwrap();
    assert_eq!(rebuilt,vec![(1,b.to_vec())]);
}
#[test]
fn r1_fec_invalid_profile_lengths_missing_and_bad_parity_fail_closed() {
    let rs=ReedSolomon20::new().unwrap();
    assert_eq!(rs.encode_active(&[],4),Err(FecMathError::InvalidSource));
    assert_eq!(rs.encode_active(&[b"x"],5),Err(FecMathError::UnsupportedProfile));
    assert_eq!(rs.encode_active(&[b""],4),Err(FecMathError::InvalidSource));
    let one=[1u8];
    let too_many=[one.as_slice();21];
    assert_eq!(rs.encode_active(&too_many,4),Err(FecMathError::InvalidSource));
    let src=[1u8,2,3];
    assert_eq!(rs.streaming_wire(0,20,&src,4,4096),Err(FecMathError::InvalidSource));
    assert_eq!(rs.final_parity_wires(1,&[&src],4,FEC_HEADER),Err(FecMathError::InvalidLength));
    let p=rs.encode_active(&[&src],4).unwrap();
    assert_eq!(rs.recover_missing(&meta(1,3,4),&[None],&[]),Err(FecMathError::TooManyMissing));
    assert_eq!(rs.recover_missing(&meta(1,3,4),&[None],&[(19,&p[0])]),
        Err(FecMathError::InvalidIndex));
    assert_eq!(rs.recover_missing(&meta(1,3,4),&[None],&[(20,&p[0]),(20,&p[0])]),
        Err(FecMathError::DuplicateParity));
    let mut m=meta(1,3,4);m.lengths[0]=4;
    assert_eq!(rs.recover_missing(&m,&[None],&[(20,&p[0])]),Err(FecMathError::InvalidLength));
}
