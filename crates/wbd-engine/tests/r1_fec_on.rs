//! M0 test-only: authenticated FEC-on, true frozen record and M4 full IPv4/TCP DATA bytes.
//! In-process sink, NOT real raw socket, Go V4 production or performance qualification.
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
use wbd_platform::r1::ReadyPacketSink;
use wbd_platform::ipv4_tcp::{build,measure,Ipv4Tuple,PacketPersona,Presentation,PacketError};
use wbd_types::{LaneKey,TunnelKey,MonoNs,RecordPn,SeqOffset};
use wbd_types::buffer_contract::{FrozenMetadata,FrozenRecordHandle,UniqueSealable};
fn keys()->DirectionKeys{DirectionKeys{aead_key:[7;32],iv:[3;12],hp_key:[9;32]}}
fn lane()->LaneKey{LaneKey{tunnel:TunnelKey{slot:3,generation:2},slot:4,generation:5}}
fn limits()->QueueLimits{QueueLimits{slots:8,bytes:4096,max_age_ns:1_000_000_000}}
fn budget()->FrameBudget{
 FrameBudget::derive(FrameBudgetInput{connection_mtu:576,local_packet_mtu:0,
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

fn tuple()->Ipv4Tuple<'static>{
 Ipv4Tuple{src_ip:&[192,0,2,40],dst_ip:&[198,51,100,40],src_port:43000,dst_port:443}
}
fn presentation(pn:u64)->Presentation{
 Presentation{ack32:500,advertised_window:1024,ip_id:21+pn as u16,persona:PacketPersona::Legacy}
}
// Independent byte-oriented one's complement oracle; does not call M4's checksum helpers.
fn checksum(bytes:&[u8])->u16{
 let mut sum=0u64;
 for (i,b) in bytes.iter().enumerate(){sum+=u64::from(*b) << (if i%2==0{8}else{0});}
 while sum>0xffff{sum=(sum&0xffff)+(sum>>16);}
 !(sum as u16)
}
fn check_outer(packet:&[u8],record:&[u8],seq:u32){
 assert_eq!(packet.len(),40+record.len());
 assert!(packet.len()<=budget().effective_packet_mtu);
 assert_eq!(u16::from_be_bytes([packet[2],packet[3]]) as usize,packet.len());
 assert_eq!(packet[0],0x45);
 assert_eq!(packet[6..8],[0x40,0]);
 assert_eq!(packet[8],64);assert_eq!(packet[9],6);
 assert_eq!(packet[12..16],[192,0,2,40]);assert_eq!(packet[16..20],[198,51,100,40]);
 assert_eq!(checksum(&packet[..20]),0,"IPv4 header checksum");
 assert_eq!(packet[32]>>4,5);assert_eq!(packet[33],0x18);
 assert_eq!(&packet[24..28],&seq.to_be_bytes());
 assert_eq!(&packet[40..],record);
 let tcp=&packet[20..];
 let mut pseudo=Vec::from(&packet[12..20]);
 pseudo.extend_from_slice(&[0,6]);pseudo.extend_from_slice(&(tcp.len() as u16).to_be_bytes());
 pseudo.extend_from_slice(tcp);
 assert_eq!(checksum(&pseudo),0,"TCP pseudoheader checksum");
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
 let mtu=budget().effective_packet_mtu;
 let mut scratch=[0xa5u8;576];
 let packet=build(tuple(),presentation(pn),&ready.record,None,mtu,&mut scratch).unwrap();
 check_outer(packet,&orig,ready.record.metadata().seq.0 as u32);
 assert_eq!(sink.try_send(packet).unwrap(),packet.len()); // in-process copy, not kernel ACK
 check_outer(sink.frames.last().unwrap(),&orig,ready.record.metadata().seq.0 as u32);
 // Only mutable *presentation* on a repair; PN, TCP seq and ciphertext stay frozen.
 let mut other=presentation(pn);other.ack32+=1;other.ip_id+=1;
 let mut repair_scratch=[0u8;576];
 let repair=build(tuple(),other,&ready.record,None,mtu,&mut repair_scratch).unwrap();
 assert_ne!(packet,repair);
 check_outer(repair,&orig,ready.record.metadata().seq.0 as u32);
 assert_eq!(ready.record.bytes(),orig);
 drop(ready);assert_eq!(a.drain_returns(),1);
 pn
}
fn receive(a:&mut Arena,owner:&mut RxOwner,
 rx:&mut ReplayProtectedLaneRx,fec:&mut FecRxOwner,wire:&[u8],at:u64,seq:u32)->Deliver{
 let mut unique=a.allocate().unwrap();
 assert_eq!(wire[0],0x45);
 assert_eq!(u16::from_be_bytes([wire[2],wire[3]]) as usize,wire.len());
 let record=&wire[40..];
 check_outer(wire,record,seq); // independent expected seq from the original TX
 unique.writable()[..record.len()].copy_from_slice(record);
 owner.offer(unique,0..record.len(),MonoNs(at)).unwrap();
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
 let d=receive(&mut ra,&mut ro,&mut rx,&mut fec,&sink.frames[0],1,0);
 assert_eq!(d.systematic,vec![(0,payload.to_vec())]);assert!(d.recovered.is_empty());
 assert_eq!(sink.calls,1);
 let mut duplicate=sink.frames[0][40..].to_vec();
 assert_eq!(rx.open_unique_in_place(&mut duplicate),Err(UniqueOpenError::Duplicate));
 let mut corrupted=sink.frames[0][40..].to_vec();let last=corrupted.len()-1;corrupted[last]^=1;
 assert_eq!(rx.open_unique_in_place(&mut corrupted),
  Err(UniqueOpenError::InvalidRecord(CryptoError::Authentication)));
 assert_eq!(rx.max_seen(),Some(0));assert_eq!(fec.stats().systematic,1);
 assert!(ftx.flush_due(31).unwrap().parity.is_empty());
 assert!(!ftx.flush_due(32).unwrap().parity.is_empty());
 // Tight IPv4 576, MSS536, record31, FEC56: 449 business bytes exactly.
 // No double subtraction and no invisible TCP options on a steady DATA packet.
 let edge_payload=vec![0x55u8;b.single_business_payload_mtu];
 assert_eq!(edge_payload.len(),449);
 let mut edge_fec=FecTxOwner::new(10,4096).unwrap();
 let edge_batch=edge_fec.submit(&edge_payload,0,4,b.max_fec_wire_datagram(),false).unwrap();
 assert_eq!(edge_batch.systematic[0].len(),b.max_fec_wire_datagram());
 let mut edge_tx=LaneTxCrypto::new(keys(),b.record_wire_mtu).unwrap();
 let mut edge_arena=Arena::new(309,1,768,1,100_000).unwrap();
 let mut edge_unique=edge_arena.allocate().unwrap();
 let edge_shard=&edge_batch.systematic[0];
 edge_unique.writable()[14..14+edge_shard.len()].copy_from_slice(edge_shard);
 let (edge_pn,edge_len)=edge_tx.seal_in_place(
     AUTHENTICATED_LINK_KIND,edge_unique.writable(),edge_shard.len(),0).unwrap();
 assert_eq!(edge_len,b.record_wire_mtu);assert_eq!(edge_len,536);
 let edge_record=edge_unique.freeze(0..edge_len,FrozenMetadata{
     lane:lane(),pn:RecordPn(edge_pn),seq:SeqOffset(0xffff_fffe),
     carrier_snapshot:4}).unwrap();
 let original=edge_record.bytes().to_vec();
 let mut tight=[0x5au8;576];
 assert_eq!(build(tuple(),presentation(edge_pn),&edge_record,None,575,&mut tight),
   Err(PacketError::MtuExceeded{required:576,mtu:575}));
 assert!(tight.iter().all(|x|*x==0x5a));
 assert_eq!(build(tuple(),presentation(edge_pn),&edge_record,None,576,&mut tight[..575]),
   Err(PacketError::ScratchTooSmall{required:576,available:575}));
 assert!(tight.iter().all(|x|*x==0x5a));
 let full=build(tuple(),presentation(edge_pn),&edge_record,None,576,&mut tight).unwrap();
 assert_eq!(full.len(),576);check_outer(full,&original,0xffff_fffe);
 assert_eq!(measure(edge_len,Some(&[1,1,1,1])).unwrap().required,580);
 assert_eq!(build(tuple(),presentation(edge_pn),&edge_record,Some(&[1,1,1,1]),576,&mut tight),
   Err(PacketError::MtuExceeded{required:580,mtu:576}));
 assert_eq!(edge_record.bytes(),original);
 drop(edge_record);assert_eq!(edge_arena.drain_returns(),1);
 assert_eq!(edge_arena.stop().loaned,0);
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
 let d=receive(&mut ra,&mut ro,&mut rx,&mut fec,&sink.frames[1],2,1);
 assert_eq!(d.systematic,vec![(1,right.to_vec())]);assert!(d.recovered.is_empty());
 let p=receive(&mut ra,&mut ro,&mut rx,&mut fec,&sink.frames[2],34_000_000,2);
 assert!(p.systematic.is_empty());assert_eq!(p.recovered,vec![(0,left.to_vec())]);
 let late=receive(&mut ra,&mut ro,&mut rx,&mut fec,&sink.frames[0],35_000_000,0);
 assert!(late.systematic.is_empty()&&late.recovered.is_empty());
 assert_eq!((fec.stats().systematic,fec.stats().recovered),(1,1));
 let mut replay=sink.frames[2][40..].to_vec();
 assert_eq!(rx.open_unique_in_place(&mut replay),Err(UniqueOpenError::Duplicate));
 assert_eq!(rx.max_seen(),Some(2));
 assert_eq!(to.stop(),0);assert_eq!(ro.stop(),0);
 assert_eq!(ta.stop().loaned,0);assert!(ta.quiesced());
 assert_eq!(ra.stop().loaned,0);assert!(ra.quiesced());
}
