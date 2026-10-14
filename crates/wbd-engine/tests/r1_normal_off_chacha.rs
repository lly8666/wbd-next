//! M0 R1 ChaCha-only first business packet integration.
 //! This is deterministic in-process sink/RX copying, NOT an OS raw carrier,
 //! production V4, full AES, replay or FEC/repair product qualification.
 use std::io;
 use std::sync::Arc;
 use std::time::Instant;
 use wbd_codec::path_budget::{FecReservation,FrameBudget,FrameBudgetInput};
 use wbd_codec::record_crypto::{CryptoError,DirectionKeys,LaneRxCrypto,LaneTxCrypto,RecordSuite};
 use wbd_codec::record_replay::{ReplayProtectedLaneRx,ReplayWindowConfig,UniqueOpenError};
 use wbd_codec::record_frame::{AUTHENTICATED_LINK_KIND,FIXED_WIRE_OVERHEAD};
 use wbd_engine::memory::Arena;
 use wbd_engine::runtime::{QueueLimits,RxOwner,TxKind,TxOwner};
 use wbd_platform::r1::{submit_ready,BorrowFence,ReadyPacketSink,ReadyTxLedger,StopResult};
 use wbd_platform::TxDisposition;
 use wbd_types::{LaneKey,MonoNs,RecordPn,SeqOffset,TunnelKey};
 use wbd_types::buffer_contract::{FrozenMetadata,FrozenRecordHandle,UniqueSealable};

 fn keys() -> DirectionKeys {
     // Deterministic already-supplied direction material. This test does NOT
     // run Go admission/KDF. M3 separately checked actual legacy Go V1 vectors.
     DirectionKeys {aead_key:[7;32],iv:[3;12],hp_key:[9;32]}
 }
 fn lane() -> LaneKey {
     LaneKey {tunnel:TunnelKey {slot:3,generation:2},slot:4,generation:5}
 }
 fn limits() -> QueueLimits {
     QueueLimits {slots:4,bytes:1024,max_age_ns:1_000_000}
 }
 fn replay_config() -> ReplayWindowConfig {
     // 1000 PN/s, 100ms cache, 0 FEC, no real time signal: 256 PN
     // coverage uses exactly TWO tagged pages = 80 bytes.
     ReplayWindowConfig {
         pn_per_second:1_000,cache_horizon_ms:100,
         fec_horizon_ms:0,rtt_ms:0,metadata_budget_bytes:80
     }
 }
 fn budget() -> FrameBudget {
     FrameBudget::derive(FrameBudgetInput {
         connection_mtu:1200,local_packet_mtu:0,
         ipv4_header_len:20,tcp_header_len:20,peer_mss:Some(536),
         record_wire_limit:536,fec:FecReservation::FixedOff,game:false,
     }).unwrap()
 }
 #[derive(Default)]
 struct InProcessSink { frames:Vec<Vec<u8>>, calls:usize }
 impl ReadyPacketSink for InProcessSink {
     fn try_send(&mut self,wire:&[u8]) -> io::Result<usize> {
         self.calls+=1;
         // Models a completed OS copy into a distinct receiver buffer;
         // sender FrozenRecord remains immutable and is not re-sealed.
         self.frames.push(wire.to_vec());
         Ok(wire.len())
     }
 }

 #[test]
 fn r1_normal_off_chacha_real_owner_seal_frozen_ready_driver_authenticated_delivery() {
     let mtu=budget();
     assert_eq!(mtu.fec_overhead,0);
     assert_eq!(mtu.game_overhead,0);
     assert_eq!(mtu.link_frame_mtu,mtu.record_payload_mtu);
     assert_eq!(mtu.record_wire_mtu,536);
     let business=b"\x00first-normal\xff\x00packet";
     assert!(mtu.fits_single_business_by_size(business.len()));
     let mut arena=Arena::new(31,4,256,1,100_000).unwrap();
     let mut unique=arena.allocate().unwrap();
     let origin=unique.origin();
     let range=14..14+business.len();
     unique.writable()[range.clone()].copy_from_slice(business);
     let mut seal=LaneTxCrypto::new(keys(),mtu.record_wire_mtu).unwrap();
     let (pn,used)=seal.seal_in_place(
         AUTHENTICATED_LINK_KIND,unique.writable(),business.len(),0).unwrap();
     assert_eq!(pn,0);
     assert_eq!(used,business.len()+FIXED_WIRE_OVERHEAD);
     assert!(mtu.outer_packet_len_for_record(used).is_some());
     let meta=FrozenMetadata {
         lane:lane(),seq:SeqOffset(100),pn:RecordPn(pn),carrier_snapshot:12
     };
     let frozen=unique.freeze(0..used,meta).unwrap();
     let shadow=frozen.clone();
     assert_eq!(shadow.origin(),origin);
     assert!(std::ptr::eq(frozen.bytes().as_ptr(),shadow.bytes().as_ptr()));
     let before=frozen.bytes().to_vec();
     let mut owner=TxOwner::new(limits(),limits()).unwrap();
     owner.offer_repair(frozen.clone(),MonoNs(0)).unwrap();
     owner.offer_fresh(frozen.clone(),MonoNs(1)).unwrap();
     let dispatch=owner.next_ready(MonoNs(1)).unwrap();
     assert_eq!(dispatch.kind,TxKind::Fresh); // repair cannot block fresh
     assert!(std::ptr::eq(dispatch.record.bytes().as_ptr(),frozen.bytes().as_ptr()));
     let mut sink=InProcessSink::default();
     let mut ledger=ReadyTxLedger::default();
     let batch=ledger.record(submit_ready(&mut sink,std::slice::from_ref(&dispatch.record)),1).unwrap();
     assert_eq!(batch.disposition_at(0),Some(TxDisposition::Accepted));
     assert_eq!((ledger.accepted,ledger.uncertain,ledger.not_attempted),(1,0,0));
     assert_eq!(sink.calls,1); // exactly one Seal and one initial send
     assert_eq!(sink.frames[0],before);
     assert_eq!(frozen.bytes(),before);
     assert_eq!(owner.queued(),(0,1)); // repair remains pending, not sent

     let mut opener=ReplayProtectedLaneRx::new(keys(),mtu.record_wire_mtu,replay_config()).unwrap();
     assert_eq!((opener.info().effective_window_pn,opener.info().allocated_metadata_bytes),(256,80));
     let mut altered=sink.frames[0].clone();
     let last=altered.len()-1;
     altered[last]^=0x40;
     assert_eq!(opener.open_unique_in_place(&mut altered),
         Err(UniqueOpenError::InvalidRecord(CryptoError::Authentication)));
     assert_eq!(opener.max_seen(),None); // invalid unauthenticated PN cannot shift floor
     assert_eq!(opener.stats().invalid_records,1);
     // Only an authenticated opener may create application delivery.
     let mut rx_arena=Arena::new(32,2,256,1,80_000).unwrap();
     let mut rx_owner=RxOwner::new(limits()).unwrap();
     let mut rx_unique=rx_arena.allocate().unwrap();
     rx_unique.writable()[..used].copy_from_slice(&sink.frames[0]);
     rx_owner.offer(rx_unique,0..used,MonoNs(2)).unwrap();
     let mut packet=rx_owner.take_ready(MonoNs(2)).expect("ready, no ACK/FEC wait");
     let authenticated=opener.open_unique_in_place(packet.wire_mut()).unwrap();
     assert_eq!(authenticated.pn,pn);
     assert_eq!(authenticated.kind,AUTHENTICATED_LINK_KIND);
     let delivered=authenticated.payload.to_vec();
     assert_eq!(delivered,business);
     assert_eq!(opener.stats().delivered,1);
     drop(packet);
     // Another valid, already sealed repair copy must never reach business.
     let mut repair_duplicate=sink.frames[0].clone();
     assert_eq!(opener.open_unique_in_place(&mut repair_duplicate),Err(UniqueOpenError::Duplicate));
     assert_eq!(opener.stats().delivered,1);
     assert_eq!(opener.stats().duplicates,1);
     assert_eq!(rx_arena.report().loaned,0);
     assert_eq!(rx_owner.stop(),0);
     assert!(rx_arena.stop().stopping);
     assert!(rx_arena.quiesced());

     // A long-lived kernel loan MUST retain the exact encrypted allocation
     // across stop; this is a synthetic completion, NOT an OS-driver test.
     let fence=Arc::new(BorrowFence::default());
     let loan=fence.try_loan(frozen.clone()).ok().unwrap();
     assert_eq!(loan.read().wire,before);
     assert_eq!(fence.wait_drained_until(Instant::now()),
         StopResult::Pending{outstanding:1});
     assert_eq!(owner.stop(),1); // cancel unsent repair handle, not an ACK
     drop(dispatch);
     drop(shadow);
     drop(frozen);
     assert_eq!(arena.stop().loaned,1); // loan still alive and immutable
     assert_eq!(loan.read().wire,before);
     drop(loan); // ONLY simulated completion releases loan
     assert_eq!(fence.wait_drained_until(Instant::now()),StopResult::Drained);
     assert!(arena.quiesced());
     assert_eq!(arena.report().loaned,0);
     // Recycled slab MUST advance the generation instead of aliasing old key.
     assert_ne!(arena.report().free,0);
 }

 #[test]
 fn r1_normal_off_chacha_invalid_capacity_burns_pn_without_publishing_business() {
     let mut arena=Arena::new(42,1,256,1,60_000).unwrap();
     let mut tx=LaneTxCrypto::new(keys(),536).unwrap();
     let mut unique=arena.allocate().unwrap();
     assert_eq!(tx.seal_in_place(AUTHENTICATED_LINK_KIND,&mut [],0,0),Err(CryptoError::Capacity));
     unique.writable()[14..18].copy_from_slice(&[0,0x91,0,0xff]);
     let (pn,len)=tx.seal_in_place(AUTHENTICATED_LINK_KIND,unique.writable(),4,0).unwrap();
     assert_eq!((pn,len),(1,35));
     let frozen=unique.freeze(0..len,FrozenMetadata{
         lane:lane(),seq:SeqOffset(0),pn:RecordPn(pn),carrier_snapshot:12}).unwrap();
     let mut corrupted=frozen.bytes().to_vec();
     corrupted[5]^=1;
     let rx=LaneRxCrypto::new(keys(),536).unwrap();
     assert!(matches!(rx.open_in_place(&mut corrupted),Err(CryptoError::Authentication)));
     // The application has no receive-side delivery in this failure path.
     let mut owner=RxOwner::new(limits()).unwrap();
     assert_eq!(owner.queued(),0);
     assert_eq!(owner.stop(),0);
     drop(frozen);
     assert_eq!(arena.drain_returns(),1);
     assert_eq!(arena.report().loaned,0);
 }


 #[test]
 fn r1_normal_off_three_actual_suites_replay_is_checked_after_auth_not_wire_pn() {
     let mtu=budget();
     for suite in [RecordSuite::ChaCha20Poly1305,RecordSuite::Aes128Gcm,RecordSuite::Aes256Gcm] {
         let mut tx=LaneTxCrypto::new_for_suite(keys(),mtu.record_wire_mtu,suite).unwrap();
         let mut rx=ReplayProtectedLaneRx::new_for_suite(
             keys(),mtu.record_wire_mtu,suite,replay_config()).unwrap();
         assert_eq!(rx.info().allocated_metadata_bytes,80);
         let mut send_arena=Arena::new(60+suite as u32,1,256,1,60_000).unwrap();
         let mut receive_arena=Arena::new(70+suite as u32,1,256,1,60_000).unwrap();
         let mut owner=RxOwner::new(limits()).unwrap();
         let mut sink=InProcessSink::default();
         let payloads:[&[u8];2]=[b"\x00safe\xff",b"\x00next\x00packet"];
         for (index,payload) in payloads.into_iter().enumerate() {
             // This is an actual M1-owned buffer, not a fake FrozenRecord.
             let mut unique=send_arena.allocate().unwrap();
             unique.writable()[14..14+payload.len()].copy_from_slice(payload);
             let (pn,len)=tx.seal_in_place(
                 AUTHENTICATED_LINK_KIND,unique.writable(),payload.len(),0).unwrap();
             assert_eq!(pn,index as u64);
             assert_eq!(len,payload.len()+FIXED_WIRE_OVERHEAD); // no LINK/FEC tax
             let frozen=unique.freeze(0..len,FrozenMetadata {
                 lane:lane(),pn:RecordPn(pn),seq:SeqOffset(index as u64),
                 carrier_snapshot:99
             }).unwrap();
             let outcome=submit_ready(&mut sink,std::slice::from_ref(&frozen));
             assert_eq!(outcome.accepted_prefix,1);
             assert_eq!(outcome.uncertain_index,None);
             assert_eq!(frozen.bytes(),&sink.frames[index]);
             drop(frozen);
             assert_eq!(send_arena.drain_returns(),1);
             let mut recv=receive_arena.allocate().unwrap();
             recv.writable()[..len].copy_from_slice(&sink.frames[index]);
             owner.offer(recv,0..len,MonoNs(index as u64)).unwrap();
             let mut packet=owner.take_ready(MonoNs(index as u64)).unwrap();
             let opened=rx.open_unique_in_place(packet.wire_mut()).unwrap();
             assert_eq!(opened.pn,pn);
             assert_eq!(opened.kind,AUTHENTICATED_LINK_KIND);
             assert_eq!(opened.payload,payload);
             drop(packet);
             assert_eq!(receive_arena.drain_returns(),1);
         }
         assert_eq!(sink.calls,2);
         assert_eq!(rx.stats().delivered,2);
         let mut duplicate=sink.frames[0].clone();
         assert_eq!(rx.open_unique_in_place(&mut duplicate),Err(UniqueOpenError::Duplicate));
         let mut tampered=sink.frames[1].clone();
         let last=tampered.len()-1;
         tampered[last]^=0x40; // authentic PN check must NOT happen before tag
         assert_eq!(rx.open_unique_in_place(&mut tampered),
             Err(UniqueOpenError::InvalidRecord(CryptoError::Authentication)));
         assert_eq!(rx.max_seen(),Some(1));
         assert_eq!(rx.stats().delivered,2);
         assert_eq!((rx.stats().duplicates,rx.stats().invalid_records),(1,1));
         assert_eq!(owner.stop(),0);
         assert_eq!(receive_arena.stop().loaned,0);
         assert!(receive_arena.quiesced());
         assert_eq!(send_arena.stop().loaned,0);
         assert!(send_arena.quiesced());
     }
 }
