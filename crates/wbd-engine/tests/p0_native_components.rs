//! P0 executable microbench observations on unprivileged Linux x86_64 GNU.
//! Component timings only, NOT end-to-end Go V4, raw AF_PACKET or 500Mbps.
#![cfg(all(target_os="linux",target_arch="x86_64",target_env="gnu"))]
use std::hint::black_box;
use std::net::UdpSocket;
use std::sync::Arc;
use std::time::{Duration,Instant};
use wbd_codec::record_crypto::{DirectionKeys,LaneTxCrypto};
use wbd_codec::record_replay::{ReplayProtectedLaneRx,ReplayWindowConfig};
use wbd_codec::record_frame::AUTHENTICATED_LINK_KIND;
use wbd_platform::linux_batch::submit_connected_udp;
use wbd_platform::linux_rx_batch::{receive_ready_udp,RxEntry,RxStatus};
use wbd_platform::r1::BorrowFence;
use wbd_platform::TxBatchOutcome;
use wbd_types::buffer_contract::{FrozenRecordHandle,FrozenMetadata,BufferOrigin};
use wbd_types::{BufferKey,LaneKey,RecordPn,SeqOffset,TunnelKey};

fn keys()->DirectionKeys { DirectionKeys{aead_key:[7;32],iv:[3;12],hp_key:[9;32]} }
fn quantiles(mut v:Vec<u64>)->(u64,u64,u64){
 assert!(!v.is_empty());
 v.sort_unstable();
 let n=v.len();
 (v[n/2],v[(n*95/100).min(n-1)],v[(n*99/100).min(n-1)])
}
fn report(case:&str,samples:Vec<u64>,ops:u64,bytes:u64,elapsed_ns:u64){
 assert!(ops>0&&bytes>0&&elapsed_ns>0);
 let(p50,p95,p99)=quantiles(samples);
 let bps= (bytes as f64)*1e9/(elapsed_ns as f64);
 println!("P0_RESULT {{\"case\":\"{case}\",\"ops\":{ops},\"business_bytes\":{bytes},\"elapsed_ns\":{elapsed_ns},\"bytes_per_second\":{bps:.3},\"sample_p50_ns\":{p50},\"sample_p95_ns\":{p95},\"sample_p99_ns\":{p99},\"qualifies_product\":false}}");
}
#[test]
fn p0_aead_1000b_seal_verified_unique_open() {
 const WARM:usize=1024;
 const N:usize=25000;
 const PAYLOAD:usize=1000;
 let mut tx=LaneTxCrypto::new(keys(),1200).unwrap();
 let mut rx=ReplayProtectedLaneRx::new(keys(),1200,ReplayWindowConfig{
     pn_per_second:100000,cache_horizon_ms:200,fec_horizon_ms:0,
     rtt_ms:0,metadata_budget_bytes:65536,
 }).unwrap();
 let mut wire=[0u8;1200];
 let mut samples=Vec::with_capacity(N);
 let mut start=Instant::now();
 for i in 0..(WARM+N) {
     wire[14..14+PAYLOAD].fill((i%251) as u8);
     let t=Instant::now();
     let(pn,len)=tx.seal_in_place(AUTHENTICATED_LINK_KIND,&mut wire,PAYLOAD,0).unwrap();
     let o=rx.open_unique_in_place(&mut wire[..len]).unwrap();
     assert_eq!(o.pn,pn);
     assert_eq!(o.payload.len(),PAYLOAD);
     assert_eq!(o.payload[0],(i%251) as u8);
     black_box(o.payload[PAYLOAD-1]);
     if i==WARM-1 {start=Instant::now();}
     if i>=WARM {samples.push(t.elapsed().as_nanos() as u64);}
 }
 let elapsed=start.elapsed().as_nanos() as u64;
 assert_eq!(rx.stats().delivered,(WARM+N) as u64);
 report("real_aead_hp_pn_replay_chacha1000",samples,N as u64,(N*PAYLOAD) as u64,elapsed);
}
#[derive(Clone)]
struct Frame { bytes:Arc<[u8]>,meta:FrozenMetadata }
impl FrozenRecordHandle for Frame {
 fn bytes(&self)->&[u8]{&self.bytes}
 fn metadata(&self)->FrozenMetadata{self.meta}
 fn origin(&self)->BufferOrigin{BufferOrigin{
     owner_arena:42,key:BufferKey{slot:1,generation:1}}}
}
#[test]
fn p0_linux_udp_sendmmsg_recvmmsg_batch32() {
 const BATCH:usize=32;const PAYLOAD:usize=256;
 const WARM:usize=64;const N:usize=1500;
 let rx=UdpSocket::bind("127.0.0.1:0").unwrap();
 rx.set_read_timeout(Some(Duration::from_millis(200))).unwrap();
 let tx=UdpSocket::bind("127.0.0.1:0").unwrap();
 tx.connect(rx.local_addr().unwrap()).unwrap();
 let meta=FrozenMetadata{lane:LaneKey{
      tunnel:TunnelKey{slot:21,generation:3},slot:4,generation:1},
      seq:SeqOffset(1000),pn:RecordPn(1),carrier_snapshot:4};
 let frames:Vec<Frame>=(0..BATCH).map(|i|{
     let mut bytes=vec![0u8;PAYLOAD];
     bytes[0]=i as u8;bytes[1]=0xa5;
     Frame{bytes:Arc::from(bytes),meta}
 }).collect();
 let send_fence=BorrowFence::default();
 let recv_fence=BorrowFence::default();
 let mut bufs=[[0u8;PAYLOAD];BATCH];
 let mut samples=Vec::with_capacity(N);
 let mut start=Instant::now();
 for iteration in 0..WARM+N {
     let t=Instant::now();
     assert_eq!(submit_connected_udp(&tx,&frames,&send_fence),TxBatchOutcome::copied_all(BATCH));
     let mut accepted=0usize;
     let mut spins=0usize;
     while accepted<BATCH {
         let mut views:Vec<&mut [u8]>=bufs[accepted..].iter_mut().map(|b|b.as_mut_slice()).collect();
         let got=receive_ready_udp(&rx,&mut views,&recv_fence);
         drop(views);
         if got.received==0{
             assert!(matches!(got.status,RxStatus::WouldBlock),"{:?}",got.status);
             spins+=1;assert!(spins<500,"kernel UDP receive failed to drain bounded batch");
             std::thread::yield_now();continue
         }
         for idx in 0..got.received{
             assert_eq!(got.entries[idx],RxEntry::Complete{len:PAYLOAD});
             assert_eq!(bufs[accepted+idx][0],(accepted+idx) as u8);
             assert_eq!(bufs[accepted+idx][1],0xa5);
         }
         accepted+=got.received;
     }
     if iteration==WARM-1 {start=Instant::now();}
     if iteration>=WARM {samples.push(t.elapsed().as_nanos() as u64);}
 }
 let elapsed=start.elapsed().as_nanos() as u64;
 assert_eq!(send_fence.outstanding(),0);
 assert_eq!(recv_fence.outstanding(),0);
 report("real_linux_udp_sendmmsg_recvmmsg_32x256",samples,(N*BATCH) as u64,(N*BATCH*PAYLOAD) as u64,elapsed);
}
