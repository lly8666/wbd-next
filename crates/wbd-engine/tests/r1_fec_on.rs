//! M0 test-only: genuine FEC on, real M1 owner, AEAD+PN, M3 FEC, M4 sink.
use std::io;
use wbd_codec::fec_tx::FecTxOwner;
use wbd_codec::fec_rx::{FecRxOwner,Config,Direction,Scope,Deliver};
use wbd_codec::link_fec_wire::{inspect_fec_header,FEC_HEADER,FecShardPhase};
use wbd_codec::path_budget::{FrameBudget,FrameBudgetInput,FecReservation};
use wbd_codec::record_crypto::{DirectionKeys,LaneTxCrypto,CryptoError,RecordSuite};
use wbd_codec::record_replay::{ReplayProtectedLaneRx,ReplayWindowConfig,UniqueOpenError};
use wbd_codec::record_frame::{AUTHENTICATED_LINK_KIND,FIXED_WIRE_OVERHEAD};
use wbd_engine::memory::Arena;
use wbd_engine::runtime::{TxOwner,RxOwner,QueueLimits,TxKind};
use wbd_platform::r1::{ReadyPacketSink,submit_ready};
use wbd_types::{LaneKey,TunnelKey,MonoNs,RecordPn,SeqOffset};
use wbd_types::buffer_contract::{FrozenMetadata,FrozenRecordHandle,UniqueSealable};
fn keys()->DirectionKeys{DirectionKeys{aead_key:[7;32],iv:[3;12],hp_key:[9;32]}}
fn lane()->LaneKey{LaneKey{tunnel:TunnelKey{slot:3,generation:2},slot:4,generation:5}}
fn limits()->QueueLimits{QueueLimits{slots:8,bytes:4096,max_age_ns:1_000_000_000}}
fn budget()->FrameBudget{
 FrameBudget::derive(FrameBudgetInput{connection_mtu:1200,local_packet_mtu:0,
 ipv4_header_len:20,tcp_header_len:20,peer_mss:Some(536),record_wire_limit:536,
 fec:FecReservation::Fixed{parity_shards:4},game:false}).unwrap()
}
fn replay_config()->ReplayWindowConfig{
 ReplayWindowConfig{pn_per_second:1_000,cache_horizon_ms:100,
 fec_horizon_ms:10_000,rtt_ms:0,metadata_budget_bytes:80}
}
fn fec_rx(b:&FrameBudget)->FecRxOwner{
 FecRxOwner::new(Config{epoch:77,direction:Direction::ClientToServer,
 max_wire:b.max_fec_wire_datagram(),max_heavy_bytes:4096,
 max_heavy_blocks:4,max_compact_blocks:8,first_id_ext:1}).unwrap()
}
#[derive(Default)]
struct Sink{frames:Vec<Vec<u8>>,calls:usize}
impl ReadyPacketSink for Sink{
 fn try_send(&mut self,w:&[u8])->io::Result<usize>{
  self.calls+=1;self.frames.push(w.to_vec());Ok(w.len())
 }
}
fn send(a:&mut Arena,tx:&mut LaneTxCrypto,owner:&mut TxOwner,
 sink:&mut Sink,shard:&[u8],at:u64)->u64{
 assert!(shard.len()+FIXED_WIRE_OVERHEAD<=256);
 let mut unique=a.allocate().unwrap();
 unique.writable()[14..14+shard.len()].copy_from_slice(shard);
 let(pn,len)=tx.seal_in_place(AUTHENTICATED_LINK_KIND,unique.writable(),shard.len(),0).unwrap();
 let f=unique.freeze(0..len,FrozenMetadata{
  lane:lane(),pn:RecordPn(pn),seq:SeqOffset(pn),carrier_snapshot:4}).unwrap();
 let orig=f.bytes().to_vec();
 owner.offer_fresh(f,MonoNs(at)).unwrap();
 let ready=owner.next_ready(MonoNs(at)).unwrap();
 assert_eq!(ready.kind,TxKind::Fresh);
 assert_eq!(submit_ready(sink,std::slice::from_ref(&ready.record)).accepted_prefix,1);
 assert_eq!(sink.frames.last().unwrap(),&orig);
 drop(ready);assert_eq!(a.drain_returns(),1);
 pn
}
fn receive(a:&mut Arena,owner:&mut RxOwner,
 rx:&mut ReplayProtectedLaneRx,fec:&mut FecRxOwner,wire:&[u8],at:u64)->Deliver{
 let mut unique=a.allocate().unwrap();
 unique.writable()[..wire.len()].copy_from_slice(wire);
 owner.offer(unique,0..wire.len(),MonoNs(at)).unwrap();
 let mut packet=owner.take_ready(MonoNs(at)).expect("no block wait");
 let open=rx.open_unique_in_place(packet.wire_mut()).unwrap();
 assert_eq!(open.kind,AUTHENTICATED_LINK_KIND);
 assert_eq!(inspect_fec_header(open.payload).unwrap().block_id,1);
 let result=fec.push_after_auth(open.payload,Scope{
  epoch:77,direction:Direction::ClientToServer,id_ext:1
 },at/1_000_000).unwrap();
 drop(packet);assert_eq!(a.drain_returns(),1);result
}
#[test]
fn r1_m0_fec_on_systematic_first_business_before_parity_and_replay(){
 let b=budget();assert_eq!(b.fec_overhead,FEC_HEADER);
 let mut ftx=FecTxOwner::new(1,4096).unwrap();
 let payload=b"\x00fec-first\xff";
 let batch=ftx.submit(payload,0,4,b.max_fec_wire_datagram(),false).unwrap();
 assert_eq!(batch.systematic.len(),1);assert!(batch.parity.is_empty());
 assert_eq!(inspect_fec_header(&batch.systematic[0]).unwrap().phase,FecShardPhase::StreamingSource);
 let mut tx=LaneTxCrypto::new(keys(),b.record_wire_mtu).unwrap();
 let mut rx=ReplayProtectedLaneRx::new(keys(),b.record_wire_mtu,replay_config()).unwrap();
 let mut fec=fec_rx(&b);
 let mut ta=Arena::new(301,8,256,1,80000).unwrap();
 let mut ra=Arena::new(302,8,256,1,80000).unwrap();
 let mut to=TxOwner::new(limits(),limits()).unwrap();
 let mut ro=RxOwner::new(limits()).unwrap();
 let mut sink=Sink::default();
 assert_eq!(send(&mut ta,&mut tx,&mut to,&mut sink,&batch.systematic[0],0),0);
 let d=receive(&mut ra,&mut ro,&mut rx,&mut fec,&sink.frames[0],1);
 assert_eq!(d.systematic,vec![(0,payload.to_vec())]);assert!(d.recovered.is_empty());
 assert_eq!(sink.calls,1);
 let mut duplicate=sink.frames[0].clone();
 assert_eq!(rx.open_unique_in_place(&mut duplicate),Err(UniqueOpenError::Duplicate));
 let mut corrupted=sink.frames[0].clone();let last=corrupted.len()-1;corrupted[last]^=1;
 assert_eq!(rx.open_unique_in_place(&mut corrupted),
  Err(UniqueOpenError::InvalidRecord(CryptoError::Authentication)));
 assert_eq!(rx.max_seen(),Some(0));assert_eq!(fec.stats().systematic,1);
 assert!(ftx.flush_due(31).unwrap().parity.is_empty());
 assert!(!ftx.flush_due(32).unwrap().parity.is_empty());
 assert_eq!(to.stop(),0);assert_eq!(ro.stop(),0);
 assert_eq!(ta.stop().loaned,0);assert!(ta.quiesced());
 assert_eq!(ra.stop().loaned,0);assert!(ra.quiesced());
}
#[test]
fn r1_m0_fec_on_missing_real_rs20_source_recovers_only_once(){
 let b=budget();let mut ftx=FecTxOwner::new(1,4096).unwrap();
 let left=b"\x00fec-left\xfe";let right=b"\x00fec-right\xfd";
 let a=ftx.submit(left,0,4,b.max_fec_wire_datagram(),false).unwrap();
 let z=ftx.submit(right,1,4,b.max_fec_wire_datagram(),false).unwrap();
 let parity=ftx.flush_due(33).unwrap().parity;assert_eq!(parity.len(),2);
 assert_eq!(inspect_fec_header(&parity[0]).unwrap().phase,FecShardPhase::FinalParity);
 let mut tx=LaneTxCrypto::new_for_suite(keys(),b.record_wire_mtu,RecordSuite::Aes128Gcm).unwrap();
 let mut rx=ReplayProtectedLaneRx::new_for_suite(
  keys(),b.record_wire_mtu,RecordSuite::Aes128Gcm,replay_config()).unwrap();
 let mut fec=fec_rx(&b);
 let mut ta=Arena::new(303,8,256,1,80000).unwrap();
 let mut ra=Arena::new(304,8,256,1,80000).unwrap();
 let mut to=TxOwner::new(limits(),limits()).unwrap();
 let mut ro=RxOwner::new(limits()).unwrap();
 let mut sink=Sink::default();
 send(&mut ta,&mut tx,&mut to,&mut sink,&a.systematic[0],0); // original PN0 lost
 send(&mut ta,&mut tx,&mut to,&mut sink,&z.systematic[0],1); // PN1 received
 send(&mut ta,&mut tx,&mut to,&mut sink,&parity[0],33_000_000); // PN2 received
 let d=receive(&mut ra,&mut ro,&mut rx,&mut fec,&sink.frames[1],2);
 assert_eq!(d.systematic,vec![(1,right.to_vec())]);assert!(d.recovered.is_empty());
 let p=receive(&mut ra,&mut ro,&mut rx,&mut fec,&sink.frames[2],34_000_000);
 assert!(p.systematic.is_empty());assert_eq!(p.recovered,vec![(0,left.to_vec())]);
 let late=receive(&mut ra,&mut ro,&mut rx,&mut fec,&sink.frames[0],35_000_000);
 assert!(late.systematic.is_empty()&&late.recovered.is_empty());
 assert_eq!((fec.stats().systematic,fec.stats().recovered),(1,1));
 let mut replay=sink.frames[2].clone();
 assert_eq!(rx.open_unique_in_place(&mut replay),Err(UniqueOpenError::Duplicate));
 assert_eq!(rx.max_seen(),Some(2));
 assert_eq!(to.stop(),0);assert_eq!(ro.stop(),0);
 assert_eq!(ta.stop().loaned,0);assert!(ta.quiesced());
 assert_eq!(ra.stop().loaned,0);assert!(ra.quiesced());
}
