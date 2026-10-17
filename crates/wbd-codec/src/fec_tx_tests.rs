//! Actual FEC source-first TX tests beneath excluded R1 LINK namespace.
use crate::fec_tx::{FecTxOwner,TxError,FLUSH_MS,MAX_RETAINED};
use crate::link_fec_wire::{inspect_fec_frame,FecShardPhase,FEC_HEADER};
fn h(wire:&[u8])->crate::link_fec_wire::FecHeader{
    inspect_fec_frame(wire,wire.len()).unwrap().header
}
#[test]
fn r1_tx_sparse_first_source_immediate_32ms_absolute_not_extended(){
    let mut tx=FecTxOwner::new(1,1024).unwrap();
    let one=tx.submit(b"abc",100,20,312,false).unwrap();
    assert_eq!((one.systematic.len(),one.parity.len()),(1,0));
    assert_eq!((h(&one.systematic[0]).block_id,h(&one.systematic[0]).shard_index),(1,0));
    assert_eq!(h(&one.systematic[0]).phase,FecShardPhase::StreamingSource);
    assert_eq!(tx.next_deadline_ms(),Some(132));
    assert!(tx.flush_due(131).unwrap().parity.is_empty());
    let two=tx.submit(b"z",131,20,312,false).unwrap();
    assert_eq!(h(&two.systematic[0]).shard_index,1);
    assert_eq!(tx.next_deadline_ms(),Some(132));
    let parity=tx.flush_due(132).unwrap().parity;
    assert_eq!(parity.len(),2);
    let f=h(&parity[0]);
    assert_eq!((f.data_count,f.parity_count,f.shard_size),(2,20,3));
    assert_eq!(f.lengths[..2],[3,1]);
    assert_eq!(tx.stats().partial_blocks,1);
    assert!(tx.flush_due(999).unwrap().parity.is_empty());
    let _=tx.submit(b"one",1000,4,100,false).unwrap();
    let p=tx.flush_due(1000+FLUSH_MS).unwrap().parity;
    assert_eq!(p.len(),1);assert_eq!(h(&p[0]).parity_count,4);
}
#[test]
fn r1_tx_full20_closes_on_twentieth_without_delay_and_profile_r(){
    let mut tx=FecTxOwner::new(33,50_000).unwrap();
    let mut parity=Vec::new();
    for i in 0..20{
        let batch=tx.submit(&vec![(i+1) as u8;64],i as u64,4,120,false).unwrap();
        assert_eq!(batch.systematic.len(),1);
        assert_eq!(h(&batch.systematic[0]).shard_index,i as u8);
        if i<19{assert!(batch.parity.is_empty());}else{parity=batch.parity;}
    }
    assert_eq!(parity.len(),4);
    for (i,w) in parity.iter().enumerate(){
        assert_eq!((h(w).shard_index,h(w).data_count,h(w).parity_count),(20+i as u8,20,4));
    }
    assert_eq!(tx.stats().full_blocks,1);
    assert_eq!(tx.stats().pending_blocks,0);
    assert!(tx.flush_due(10000).unwrap().parity.is_empty());
}
#[test]
fn r1_tx_interleaved_20_20_256_512_mtu_share_block_ids_at_start(){
    let mut tx=FecTxOwner::new(7,80_000).unwrap();
    let w=1200+FEC_HEADER;
    let a=tx.submit(&vec![1;100],10,20,w,false).unwrap();
    let b=tx.submit(&vec![2;350],11,20,w,false).unwrap();
    let c=tx.submit(&vec![3;900],12,20,w,false).unwrap();
    assert_eq!(tx.stats().class_count,3);
    assert_eq!(tx.stats().pending_blocks,3);
    assert_eq!(tx.next_block_id_ext(),10);
    assert_eq!([h(&a.systematic[0]).block_id,h(&b.systematic[0]).block_id,
        h(&c.systematic[0]).block_id],[7,8,9]);
    assert_eq!(tx.next_deadline_ms(),Some(42));
    assert!(tx.flush_due(41).unwrap().parity.is_empty());
    for (now,id) in [(42,7),(43,8),(44,9)]{
        let p=tx.flush_due(now).unwrap().parity;
        assert_eq!(p.len(),1);assert_eq!(h(&p[0]).block_id,id);
    }
    assert_eq!(tx.stats().closed_by_class_k[0][1],1);
    assert_eq!(tx.stats().closed_by_class_k[1][1],1);
    assert_eq!(tx.stats().closed_by_class_k[2][1],1);
}
#[test]
fn r1_tx_large_fragment_hint_and_lower_profile_single_group(){
    let mut tx=FecTxOwner::new(20,80_000).unwrap();
    let a=tx.submit(&vec![1;900],1,20,1429,false).unwrap();
    let b=tx.submit(&vec![2;120],2,20,1429,true).unwrap();
    assert_eq!(h(&a.systematic[0]).block_id,h(&b.systematic[0]).block_id);
    assert_eq!(h(&b.systematic[0]).shard_index,1);
    let p=tx.flush_all(3).unwrap().parity;
    assert_eq!(p.len(),2);
    assert_eq!((h(&p[0]).data_count,h(&p[0]).shard_size),(2,900));
    assert_eq!(h(&p[0]).lengths[..2],[900,120]);
    let mut low=FecTxOwner::new(1,80_000).unwrap();
    low.submit(&vec![1;100],0,10,1429,false).unwrap();
    low.submit(&vec![2;900],1,10,1429,false).unwrap();
    assert_eq!((low.stats().class_count,low.stats().pending_blocks),(1,1));
}
#[test]
fn r1_tx_reconfigure_flushes_old_profile_and_mtu_preserves_new_identity(){
    let mut tx=FecTxOwner::new(40,5_000).unwrap();
    let a=tx.submit(b"old",1,20,700,false).unwrap();
    let b=tx.submit(b"new",2,8,700,false).unwrap();
    assert_eq!(b.systematic.len(),1);assert_eq!(b.parity.len(),1);
    assert_eq!(h(&b.parity[0]).block_id,h(&a.systematic[0]).block_id);
    assert_eq!(h(&b.parity[0]).parity_count,20);
    assert_eq!((h(&b.systematic[0]).block_id,h(&b.systematic[0]).parity_count),(41,8));
    let c=tx.submit(b"mtu",3,8,100,false).unwrap();
    assert_eq!(c.parity.len(),1);
    assert_eq!(h(&c.systematic[0]).block_id,42);
    assert_eq!(tx.stats().reconfig_closes,2);
}
#[test]
fn r1_tx_capacity_closes_oldest_no_silent_drop_invalid_is_atomic(){
    let mut tx=FecTxOwner::new(1,500).unwrap();
    let a=tx.submit(&vec![1;300],0,20,1200,false).unwrap();
    let b=tx.submit(&vec![2;250],1,20,1200,false).unwrap();
    assert_eq!((b.systematic.len(),b.parity.len()),(1,1));
    assert_eq!(h(&b.parity[0]).block_id,h(&a.systematic[0]).block_id);
    assert_eq!(tx.stats().pressure_closes,1);
    assert_eq!(tx.stats().retained_bytes,250);
    let before=(tx.stats().source_shards,tx.next_block_id_ext(),tx.stats().retained_bytes);
    assert_eq!(tx.submit(&[],2,20,1200,false),Err(TxError::InvalidSource));
    assert_eq!(tx.submit(&vec![0;501],2,20,1200,false),Err(TxError::InvalidSource));
    assert_eq!(tx.submit(b"x",2,5,1200,false),Err(TxError::UnsupportedProfile));
    assert_eq!((tx.stats().source_shards,tx.next_block_id_ext(),tx.stats().retained_bytes),before);
}
#[test]
fn r1_tx_old_go_k2_parity_golden_and_final_lengths(){
    let mut tx=FecTxOwner::new(1,10000).unwrap();
    tx.submit(&[1,2,3],100,4,100,false).unwrap();
    tx.submit(&[0xa0,0xb1,0xc2,0xd3,0xe4],102,4,100,false).unwrap();
    let p=tx.flush_due(132).unwrap().parity;
    assert_eq!(p.len(),2);
    assert_eq!(&p[0][FEC_HEADER..],[0xc0,0x81,0xa7,0xe6,0xfb]);
    assert_eq!(&p[1][FEC_HEADER..],[0x67,0x58,0xbb,0x84,0xf9]);
    assert_eq!((h(&p[0]).parity_count,h(&p[0]).data_count,h(&p[0]).shard_size),(4,2,5));
    assert_eq!(h(&p[0]).lengths[..2],[3,5]);
}
#[test]
fn r1_tx_extended_id_wrap_skip_reserved_zero_and_monotone_clock(){
    let mut tx=FecTxOwner::new(u32::MAX as u64,20_000).unwrap();
    let first=tx.submit(b"A",100,4,100,false).unwrap();
    assert_eq!(h(&first.systematic[0]).block_id,u32::MAX);
    assert_eq!(tx.next_block_id_ext(),(1u64<<32)+1);
    assert!(tx.flush_due(99).unwrap().parity.is_empty());
    assert_eq!(tx.next_deadline_ms(),Some(132));
    assert_eq!(tx.flush_due(132).unwrap().parity.len(),1);
    let second=tx.submit(b"B",110,4,100,false).unwrap();
    assert_eq!(h(&second.systematic[0]).block_id,1);
    assert_eq!(tx.next_block_id_ext(),(1u64<<32)+2);
    assert_eq!(tx.next_deadline_ms(),Some(164));
    assert_eq!(FecTxOwner::new(0,20_000).err(),Some(TxError::InvalidBudget));
    assert_eq!(FecTxOwner::new(1,MAX_RETAINED+1).err(),Some(TxError::InvalidBudget));
}

#[test]
fn r1_tx_20_20_sustained_full_blocks_ready_first_parity_bounded_chunks(){
    use crate::fec_tx::MAX_PARITY_FIRST_SEND_ROWS_PER_TURN;
    assert_eq!(MAX_PARITY_FIRST_SEND_ROWS_PER_TURN,4);
    for length in [256usize,512,1200]{
        let wire_limit=length+FEC_HEADER;
        let mut tx=FecTxOwner::new(1,200_000).unwrap();
        let mut already_sent_systematic=0usize;
        let mut fresh_parity_ready=0usize;
        let mut maximum_chunk=0usize;
        let mut parity_wire_bytes=0usize;
        // Healthy continuous 20:20: every submitted source immediately
        // creates exactly one systematic, without waiting for full block
        // or a 32ms sparse flush. No source is classified as repair.
        for block in 0..3usize{
            for i in 0..20usize{
                let source=vec![(block*20+i) as u8+1;length];
                let mut batch=tx.submit(&source,(block*20+i) as u64,
                    20,wire_limit,false).unwrap();
                assert_eq!(batch.systematic.len(),1);
                assert_eq!(batch.systematic[0].len(),length+FEC_HEADER);
                assert_eq!(h(&batch.systematic[0]).shard_index,i as u8);
                assert_eq!(h(&batch.systematic[0]).block_id,block as u32+1);
                already_sent_systematic+=batch.systematic.len();
                if i<19{
                    assert_eq!(batch.parity_pending(),0);
                }else{
                    assert_eq!(batch.parity_pending(),20);
                    while batch.parity_pending()>0{
                        // At most four parity rows per ready-scheduler turn,
                        // not a purported outer repair retransmission.
                        let chunk=batch.take_ready_parity_chunk();
                        maximum_chunk=maximum_chunk.max(chunk.len());
                        assert!(chunk.len()<=4);
                        for (p,wire) in chunk.iter().enumerate(){
                            let header=h(wire);
                            assert_eq!(header.block_id,block as u32+1);
                            assert_eq!(header.data_count,20);
                            assert_eq!(header.parity_count,20);
                            assert_eq!(header.shard_size,length as u16);
                            assert!((20..40).contains(&header.shard_index));
                            assert!(header.lengths[..20].iter().all(|&x|x==length as u16));
                            assert_eq!(wire.len(),length+FEC_HEADER);
                            assert!(p<4);
                            parity_wire_bytes+=wire.len();
                        }
                        fresh_parity_ready+=chunk.len();
                        // Between chunks an external scheduler can service
                        // fresh ordinary packets; this fixture does not
                        // claim actual dispatch timing or NIC send success.
                    }
                    assert!(batch.take_ready_parity_chunk().is_empty());
                }
            }
        }
        assert_eq!(already_sent_systematic,60);
        assert_eq!(fresh_parity_ready,60);
        assert_eq!(maximum_chunk,4);
        assert_eq!(parity_wire_bytes,60*(length+FEC_HEADER));
        assert_eq!(tx.stats().source_shards,60);
        assert_eq!(tx.stats().parity_shards,60);
        assert_eq!(tx.stats().full_blocks,3);
        assert_eq!((tx.stats().pending_blocks,tx.stats().retained_bytes),(0,0));
        assert!(tx.flush_due(3000).unwrap().parity.is_empty());
    }
}

#[test]
fn r1_tx_incremental_real_gf_four_row_job_full_partial_wire_match(){
    use crate::fec_tx::FecParityJob;
    use crate::fec_math::ReedSolomon20;
    let codec=ReedSolomon20::new().unwrap();
    for k in 1..=20usize{
        for r in [4u8,8,10,12,16,20]{
            for length in [1usize,63,64,65,257,512,1200]{
                if length==1200 && k!=20{continue;}
                let mut parts=(0..k).map(|i|{
                    let n=1+(i*17+3)%length;
                    (0..n).map(|j|((i*19+j*7+3)%251) as u8).collect::<Vec<_>>()
                }).collect::<Vec<_>>();
                parts[k-1]=(0..length).map(|j|((k*19+j*7+3)%251) as u8).collect();
                let refs=parts.iter().map(Vec::as_slice).collect::<Vec<_>>();
                let all=codec.final_parity_wires(0x01020304,&refs,r,length+FEC_HEADER).unwrap();
                let expected_bytes=parts.iter().map(Vec::len).sum::<usize>();
                let mut job=FecParityJob::new(0x01020304,parts,r,length+FEC_HEADER).unwrap();
                assert_eq!(job.retained_bytes(),expected_bytes);
                assert_eq!(job.pending_rows(),k.min(r as usize));
                let mut emitted=Vec::new();
                while !job.is_done(){
                    let first=job.first_parity_index();
                    let chunk=job.take_next_rows(&codec).unwrap();
                    assert!(!chunk.is_empty()&&chunk.len()<=4);
                    assert_eq!(h(&chunk[0]).shard_index,first);
                    for (i,wire) in chunk.iter().enumerate(){
                        let head=h(wire);
                        assert_eq!(head.shard_index,first+i as u8);
                        assert_eq!(head.parity_count,r); // configured, NOT min(k,r)
                        assert_eq!(head.data_count,k as u8);
                        assert_eq!(head.shard_size,length as u16);
                    }
                    emitted.extend(chunk);
                }
                assert_eq!(emitted,all,"k={k} r={r} L={length}");
                assert_eq!(job.retained_bytes(),0);
                assert_eq!(job.pending_rows(),0);
                assert!(job.take_next_rows(&codec).unwrap().is_empty());
            }
        }
    }
}
#[test]
fn r1_tx_incremental_job_invalid_input_terminal_and_minimal_budget(){
    use crate::fec_tx::FecParityJob;
    use crate::fec_math::{ReedSolomon20,FecMathError};
    assert!(matches!(FecParityJob::new(0,vec![b"x".to_vec()],4,57),Err(TxError::IdExhausted)));
    assert!(matches!(FecParityJob::new(1,vec![b"x".to_vec()],5,57),Err(TxError::UnsupportedProfile)));
    assert!(matches!(FecParityJob::new(1,vec![b"x".to_vec()],4,56),Err(TxError::InvalidBudget)));
    assert!(matches!(FecParityJob::new(1,vec![vec![]],4,100),Err(TxError::InvalidSource)));
    assert!(matches!(FecParityJob::new(1,vec![vec![7;45]],4,100),Err(TxError::InvalidSource)));
    assert!(matches!(FecParityJob::new(1,vec![vec![1];21],4,100),Err(TxError::InvalidSource)));
    let rs=ReedSolomon20::new().unwrap();
    let a=[1u8];let b=[2u8];
    assert_eq!(rs.encode_rows_active(&[&a,&b],4,0,0),Err(FecMathError::InvalidIndex));
    assert_eq!(rs.encode_rows_active(&[&a,&b],4,2,1),Err(FecMathError::InvalidIndex));
    assert_eq!(rs.encode_rows_active(&[&a,&b],4,1,2),Err(FecMathError::InvalidIndex));
    let mut job=FecParityJob::new(99,vec![b"X".to_vec()],20,57).unwrap();
    assert_eq!(job.take_next_rows(&rs).unwrap().len(),1);
    assert!(job.is_done());assert_eq!(job.retained_bytes(),0);
}
