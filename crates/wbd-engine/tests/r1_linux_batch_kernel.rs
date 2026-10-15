//! M0 kernel syscall composition, not raw AF_PACKET or product V4.
//! M1-owned frozen AEAD ciphertext -> M4 full IPv4/TCP -> Linux sendmmsg
//! via an unprivileged connected UDP fixture; tests receive full exact bytes.
#![cfg(all(target_os="linux",target_arch="x86_64",target_env="gnu"))]
use std::net::UdpSocket;
use std::sync::Arc;
use std::time::{Duration,Instant};
use wbd_codec::record_crypto::{DirectionKeys,LaneTxCrypto};
use wbd_codec::record_replay::{ReplayProtectedLaneRx,ReplayWindowConfig,UniqueOpenError};
use wbd_codec::record_frame::AUTHENTICATED_LINK_KIND;
use wbd_engine::memory::Arena;
use wbd_engine::runtime::{TxOwner,TxKind,QueueLimits};
use wbd_platform::ipv4_tcp::{build,Ipv4Tuple,Presentation,PacketPersona};
use wbd_platform::linux_batch::submit_connected_udp;
use wbd_platform::rx_ipv4_tcp::{parse_data_packet,TrustedRx,RxError};
use wbd_platform::r1::{BorrowFence,BatchResult,StopResult};
use wbd_platform::{TxBatchOutcome,TxDisposition,TxError};
use wbd_types::{LaneKey,TunnelKey,MonoNs,RecordPn,SeqOffset};
use wbd_types::buffer_contract::{FrozenMetadata,BufferOrigin,FrozenRecordHandle,UniqueSealable};

#[derive(Clone)]
struct Outer { wire:Arc<[u8]>,meta:FrozenMetadata,origin:BufferOrigin }
impl FrozenRecordHandle for Outer {
 fn bytes(&self)->&[u8]{&self.wire}
 fn metadata(&self)->FrozenMetadata{self.meta}
 fn origin(&self)->BufferOrigin{self.origin}
}
fn keys()->DirectionKeys{DirectionKeys{aead_key:[7;32],iv:[3;12],hp_key:[9;32]}}
fn lane()->LaneKey{LaneKey{tunnel:TunnelKey{slot:21,generation:3},slot:4,generation:1}}
fn limits()->QueueLimits{QueueLimits{slots:8,bytes:4096,max_age_ns:1_000_000_000}}
fn tuple()->Ipv4Tuple<'static>{
 Ipv4Tuple{src_ip:&[192,0,2,25],dst_ip:&[198,51,100,25],src_port:43122,dst_port:443}
}
fn pres(i:usize)->Presentation{
 Presentation{ack32:999,advertised_window:65535,ip_id:200+i as u16,persona:PacketPersona::Legacy}
}
fn checksum(bytes:&[u8])->u16{
 let mut s=0u64;
 for(i,b)in bytes.iter().enumerate(){s+=(u64::from(*b))<<(if i%2==0{8}else{0});}
 while s>0xffff{s=(s&0xffff)+(s>>16);}
 !(s as u16)
}
fn verify(packet:&[u8],cipher:&[u8],meta:FrozenMetadata){
 assert!(packet.len()<=576&&packet.len()>=40);
 assert_eq!(packet[0],0x45);
 assert_eq!(u16::from_be_bytes([packet[2],packet[3]]) as usize,packet.len());
 assert_eq!(checksum(&packet[..20]),0);
 assert_eq!(&packet[12..16],&[192,0,2,25]);
 assert_eq!(&packet[16..20],&[198,51,100,25]);
 assert_eq!(&packet[24..28],&(meta.seq.0 as u32).to_be_bytes());
 assert_eq!(packet[32]>>4,5);assert_eq!(packet[33],0x18);
 let tcp=&packet[20..];let mut pseudo=Vec::from(&packet[12..20]);
 pseudo.extend_from_slice(&[0,6]);
 pseudo.extend_from_slice(&(tcp.len() as u16).to_be_bytes());
 pseudo.extend_from_slice(tcp);
 assert_eq!(checksum(&pseudo),0);
 assert_eq!(&packet[40..],cipher);
}
fn sockets()->(UdpSocket,UdpSocket){
 let rx=UdpSocket::bind("127.0.0.1:0").unwrap();
 rx.set_read_timeout(Some(Duration::from_millis(200))).unwrap();
 let tx=UdpSocket::bind("127.0.0.1:0").unwrap();
 tx.connect(rx.local_addr().unwrap()).unwrap();(tx,rx)
}
fn make()->(Arena,TxOwner,Vec<wbd_engine::runtime::TxDispatch>,Vec<Vec<u8>>,Vec<Outer>){
 let mut arena=Arena::new(911,4,256,1,80_000).unwrap();
 let mut owner=TxOwner::new(limits(),limits()).unwrap();
 let mut tx=LaneTxCrypto::new(keys(),536).unwrap();
 for (i,b) in [b"\x00first\xff".as_slice(),b"\x01second",b"\x00third"].iter().enumerate(){
  let mut u=arena.allocate().unwrap();
  u.writable()[14..14+b.len()].copy_from_slice(b);
  let(pn,len)=tx.seal_in_place(AUTHENTICATED_LINK_KIND,u.writable(),b.len(),0).unwrap();
  assert_eq!(pn,i as u64);
  let frozen=u.freeze(0..len,FrozenMetadata{
   lane:lane(),seq:SeqOffset(1000+i as u64*256),
   pn:RecordPn(pn),carrier_snapshot:4
  }).unwrap();
  owner.offer_fresh(frozen,MonoNs(i as u64)).unwrap();
 }
 let mut ready=Vec::new();
 for i in 0..3{
  let d=owner.next_ready(MonoNs(3+i)).unwrap();
  assert_eq!(d.kind,TxKind::Fresh);
  ready.push(d);
 }
 let mut originals=Vec::new();let mut packets=Vec::new();
 for (i,d) in ready.iter().enumerate(){
  let mut scratch=[0u8;576];
  let wire=build(tuple(),pres(i),&d.record,None,576,&mut scratch).unwrap();
  verify(wire,d.record.bytes(),d.record.metadata());
  originals.push(d.record.bytes().to_vec());
  packets.push(Outer{wire:Arc::from(wire),meta:d.record.metadata(),origin:d.record.origin()});
 }
 (arena,owner,ready,originals,packets)
}
#[test]
fn r1_m0_linux_batch_real_kernel_full_tcp_m1_frozen_aead_replay(){
 let(mut arena,mut owner,ready,originals,packets)=make();
 let(tx,rx_sock)=sockets();
 let fence=BorrowFence::default();
 let out=submit_connected_udp(&tx,&packets,&fence);
 assert_eq!(out,TxBatchOutcome::copied_all(3));
 assert!(BatchResult::new(out,3).unwrap().iter().all(|x|x==TxDisposition::Accepted));
 assert_eq!(fence.outstanding(),0);
 let mut rx=ReplayProtectedLaneRx::new(keys(),536,ReplayWindowConfig{
  pn_per_second:1000,cache_horizon_ms:100,fec_horizon_ms:0,rtt_ms:0,metadata_budget_bytes:80
 }).unwrap();
 let business:[&[u8];3]=[b"\x00first\xff",b"\x01second",b"\x00third"];
 for (i,expected) in packets.iter().enumerate(){
  let mut packet=[0u8;576];
  let len=rx_sock.recv(&mut packet).unwrap();
  assert_eq!(&packet[..len],expected.bytes());
  verify(&packet[..len],&originals[i],ready[i].record.metadata());
  let untrusted=parse_data_packet(&packet[..len],TrustedRx{tuple:tuple(),persona:PacketPersona::Legacy,mtu:576,authenticated_options:None}).unwrap();
  assert_eq!(untrusted.seq32,ready[i].record.metadata().seq.0 as u32);
  assert_eq!(untrusted.extend_seq_against(ready[i].record.metadata().seq.0),Ok(ready[i].record.metadata().seq.0));
  assert_eq!(untrusted.ciphertext,&originals[i]);
  // The outer parser has NOT authenticated anything. AEAD/PN opens later.
  let mut cipher=untrusted.ciphertext.to_vec();
  let opened=rx.open_unique_in_place(&mut cipher).unwrap();
  assert_eq!(opened.pn,i as u64);
  assert_eq!(opened.payload,business[i]);
  assert_eq!(ready[i].record.bytes(),originals[i]);
 }
 let mut dup=packets[0].wire[40..].to_vec();
 assert_eq!(rx.open_unique_in_place(&mut dup),Err(UniqueOpenError::Duplicate));
 assert_eq!(rx.stats().delivered,3);
 assert_eq!(owner.stop(),0);
 drop(packets);drop(ready);
 assert_eq!(arena.drain_returns(),3);
 assert_eq!(arena.stop().loaned,0);assert!(arena.quiesced());
 assert_eq!(fence.wait_drained_until(Instant::now()),StopResult::Drained);
}
#[test]
fn r1_m0_linux_batch_cap32_stop_and_unattempted_suffix_udp(){
 let(mut arena,mut owner,ready,_,packets)=make();
 // Duplicates only demonstrate syscall cap, NOT 33 unique record PNs.
 let batch=vec![packets[0].clone();33];
 let(tx,rx)=sockets();let fence=BorrowFence::default();
 let out=submit_connected_udp(&tx,&batch,&fence);
 assert_eq!(out.accepted_prefix,32);
 assert_eq!(out.uncertain_index,None);
 assert_eq!(out.error,Some(TxError::WouldBlock));
 let b=BatchResult::new(out,33).unwrap();
 assert_eq!(b.disposition_at(31),Some(TxDisposition::Accepted));
 assert_eq!(b.disposition_at(32),Some(TxDisposition::NotAttempted));
 let mut wire=[0u8;576];
 for _ in 0..32{
  let n=rx.recv(&mut wire).unwrap();
  assert_eq!(&wire[..n],batch[0].bytes());
 }
 assert!(rx.recv(&mut wire).is_err()); // no datagram #33
 assert_eq!(fence.wait_drained_until(Instant::now()),StopResult::Drained);
 assert_eq!(submit_connected_udp(&tx,&batch,&fence).error,Some(TxError::Stopping));
 assert_eq!(fence.outstanding(),0);
 assert_eq!(owner.stop(),0);
 drop(batch);drop(packets);drop(ready);
 assert_eq!(arena.drain_returns(),3);
 assert_eq!(arena.stop().loaned,0);
}

#[test]
fn r1_m0_ipv4_tcp_parser_checksum_forgery_cannot_bypass_aead_or_hol(){
 let(mut arena,mut owner,ready,_,packets)=make();
 let policy=TrustedRx{tuple:tuple(),persona:PacketPersona::Legacy,mtu:576,authenticated_options:None};
 let mut forged=packets[0].wire.to_vec();
 forged[40]^=0x80;
 assert_eq!(parse_data_packet(&forged,policy),Err(RxError::TcpChecksum));
 // Attacker can recompute an ordinary TCP checksum; that does not give AEAD.
 forged[36]=0;forged[37]=0;
 let tcp=&forged[20..];let mut pseudo=Vec::from(&forged[12..20]);
 pseudo.extend_from_slice(&[0,6]);
 pseudo.extend_from_slice(&(tcp.len() as u16).to_be_bytes());
 pseudo.extend_from_slice(tcp);
 let check=checksum(&pseudo);
 forged[36..38].copy_from_slice(&check.to_be_bytes());
 let untrusted=parse_data_packet(&forged,policy).unwrap();
 let mut rx=ReplayProtectedLaneRx::new(keys(),536,ReplayWindowConfig{
  pn_per_second:1000,cache_horizon_ms:100,fec_horizon_ms:0,rtt_ms:0,metadata_budget_bytes:80
 }).unwrap();
 let mut bad=untrusted.ciphertext.to_vec();
 assert!(matches!(rx.open_unique_in_place(&mut bad),
     Err(UniqueOpenError::InvalidRecord(_))));
 assert_eq!(rx.max_seen(),None);
 // An unrelated malformed packet must not suppress this first real business.
 let good=parse_data_packet(packets[0].bytes(),policy).unwrap();
 let mut sealed=good.ciphertext.to_vec();
 let opened=rx.open_unique_in_place(&mut sealed).unwrap();
 assert_eq!(opened.pn,0);
 assert_eq!(opened.payload,b"\x00first\xff");
 assert_eq!(rx.stats().delivered,1);
 assert_eq!(owner.stop(),0);
 drop(packets);drop(ready);
 assert_eq!(arena.drain_returns(),3);
 assert_eq!(arena.stop().loaned,0);
}
