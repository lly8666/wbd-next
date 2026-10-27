//! M0 actual M1 frozen handle + M3 real crypto + M2 pure recovery + M4
//! bounded ready-only sink. Test-only trusted key/epoch; no live Go admission.
use std::io::{self,ErrorKind};
use wbd_codec::{encode_control,ControlTlv,Receipt,ReceiptPage as WirePage};
use wbd_codec::record_crypto::{DirectionKeys,LaneTxCrypto,RecordSuite,CryptoError};
use wbd_codec::record_replay::{ReplayProtectedLaneRx,ReplayWindowConfig,UniqueOpenError};
use wbd_codec::record_frame::{AUTHENTICATED_HEALTH_KIND,AUTHENTICATED_LINK_KIND,FIXED_WIRE_OVERHEAD};
use wbd_engine::memory::{Arena,FrozenRecord};
use wbd_engine::recovery_ingress::{BoundReceiptIngress,ReceiptIngressError,submit_repair_once,submit_global_repair_once};
use wbd_platform::r1::{submit_ready,ReadyPacketSink};
use wbd_platform::ipv4_tcp::{self,Ipv4Tuple,Presentation,PacketPersona,PacketError};
use wbd_recovery::{ReceiptConfig,ReceiptState,RepairSendResult,
    RepairBudget, RepairBudgetConfig, BudgetDirection, BudgetError, WireDirection, GlobalRepairAllocator, GlobalRepairConfig, GlobalRepairError};
use wbd_types::{LaneKey,MonoNs,RecordPn,SeqOffset,TunnelKey};
use wbd_types::buffer_contract::{FrozenMetadata,FrozenRecordHandle,UniqueSealable};

fn lane()->LaneKey{
    LaneKey{tunnel:TunnelKey{slot:5,generation:3},slot:2,generation:7}
}
fn different_lane()->LaneKey{
    LaneKey{tunnel:TunnelKey{slot:5,generation:3},slot:99,generation:7}
}
fn data_keys()->DirectionKeys{
    DirectionKeys{aead_key:[7;32],iv:[3;12],hp_key:[9;32]}
}
fn reverse_keys()->DirectionKeys{
    DirectionKeys{aead_key:[19;32],iv:[23;12],hp_key:[29;32]}
}
fn epoch()->[u8;16]{[42;16]}
fn state()->ReceiptState<FrozenRecord>{
    ReceiptState::new(lane(),ReceiptConfig{
        max_shadow_entries:8,pto_ns:100,reorder_window_ns:5
    }).unwrap()
}
fn budget_with(tunnel:TunnelKey,outer_mtu:u64)->RepairBudget{
    RepairBudget::new(BudgetDirection{tunnel,direction:WireDirection::ClientToServer},
        RepairBudgetConfig {
            outer_mtu,max_repair_bytes_per_epoch:100_000,
            max_pending_reservations:8,max_pending_bytes:4_096,
            io_timeout_ns:1_000_000,
        },MonoNs(0)).unwrap()
}
fn budget()->RepairBudget {budget_with(lane().tunnel,536)}
fn trusted_tuple()->Ipv4Tuple<'static>{
    Ipv4Tuple{src_ip:&[192,0,2,40],dst_ip:&[198,51,100,40],
              src_port:43000,dst_port:443}
}
fn presentation()->Presentation{
    Presentation{ack32:200,advertised_window:1024,ip_id:21,persona:PacketPersona::Legacy}
}
fn outer_wire_bytes(frozen:&FrozenRecord)->u64 {
    ipv4_tcp::measure(frozen.bytes().len(),None).unwrap().required as u64
}
fn submit_test<S:ReadyPacketSink>(
    shadow:&mut ReceiptState<FrozenRecord>, budget:&mut RepairBudget,
    candidate:&wbd_recovery::RepairCandidate<FrozenRecord>,
    sink:&mut S,now:MonoNs,
)->Result<RepairSendResult,ReceiptIngressError>{
    let mut scratch=[0u8;536];
    submit_repair_once(shadow,budget,candidate,sink,trusted_tuple(),
                       presentation(),None,536,&mut scratch,now)
}
// Independent arithmetic checksum oracle: not M4's code path.
fn packet_checksum(bytes:&[u8])->u16{
    let mut n=0u64;
    for (i,&v) in bytes.iter().enumerate() {
        n+=(v as u64)<<if i%2==0 {8} else {0};
    }
    while n>65535{n=(n&65535)+(n>>16);}
    !(n as u16)
}
fn assert_valid_packet(pkt:&[u8],frozen:&FrozenRecord,overhead:usize){
    assert_eq!(pkt[0],0x45);
    assert_eq!(pkt.len(),u16::from_be_bytes([pkt[2],pkt[3]]) as usize);
    assert_eq!(packet_checksum(&pkt[..20]),0);
    let mut pseudo=Vec::from(&pkt[12..20]);
    pseudo.extend_from_slice(&[0,6]);
    pseudo.extend_from_slice(&((pkt.len()-20) as u16).to_be_bytes());
    pseudo.extend_from_slice(&pkt[20..]);
    assert_eq!(packet_checksum(&pseudo),0);
    assert_eq!(&pkt[24..28], &(frozen.metadata().seq.0 as u32).to_be_bytes());
    assert_eq!(&pkt[overhead..],frozen.bytes());
}
fn original(a:&mut Arena,pn_expected:u64)->FrozenRecord{
    let business=b"\x00R2-original\xff";
    let mut tx=LaneTxCrypto::new(data_keys(),536).unwrap();
    let mut b=a.allocate().unwrap();
    b.writable()[14..14+business.len()].copy_from_slice(business);
    // This fixture may construct a *new, distinct* authenticated PN after
    // a terminal one-opportunity repair. Burn prior non-published PN in
    // the test crypto owner; never re-use a previously sealed nonce.
    for _ in 0..pn_expected {
        let mut unpublished=[0u8;64];
        unpublished[14..14+business.len()].copy_from_slice(business);
        tx.seal_in_place(AUTHENTICATED_LINK_KIND,&mut unpublished,
            business.len(),0).unwrap();
    }
    let (pn,n)=tx.seal_in_place(AUTHENTICATED_LINK_KIND,b.writable(),business.len(),0).unwrap();
    assert_eq!(pn,pn_expected);
    b.freeze(0..n,FrozenMetadata{
        lane:lane(),pn:RecordPn(pn),seq:SeqOffset(0),carrier_snapshot:11
    }).unwrap()
}
fn reply_with_tx(tx:&mut LaneTxCrypto,received:bool,seq:u32)->Vec<u8>{
    let mut bitmap=[0u8;32];
    if received {bitmap[0]=1;}
    let body=encode_control(&[ControlTlv::Receipt(Receipt{
        largest_data_pn:0,ack_delay_us:100,report_seq:seq,
        pages:vec![WirePage{base_pn:0,bitmap}]
    })],512).unwrap();
    let mut w=vec![0;body.len()+FIXED_WIRE_OVERHEAD];
    w[14..14+body.len()].copy_from_slice(&body);
    let (_,used)=tx.seal_in_place(AUTHENTICATED_HEALTH_KIND,&mut w,body.len(),0).unwrap();
    assert_eq!(w.len(),used);
    w
}
fn reply(received:bool)->Vec<u8>{
    let mut bitmap=[0u8;32];
    if received {bitmap[0]=1;}
    let body=encode_control(&[ControlTlv::Receipt(Receipt{
        largest_data_pn:0,ack_delay_us:100,report_seq:1,
        pages:vec![WirePage{base_pn:0,bitmap}]
    })],512).unwrap();
    let mut w=vec![0;body.len()+FIXED_WIRE_OVERHEAD];
    w[14..14+body.len()].copy_from_slice(&body);
    let mut seal=LaneTxCrypto::new(reverse_keys(),536).unwrap();
    let (pn,n)=seal.seal_in_place(AUTHENTICATED_HEALTH_KIND,&mut w,body.len(),0).unwrap();
    assert_eq!(pn,0);
    assert_eq!(n,w.len());
    w
}
fn replay_config()->ReplayWindowConfig {
    ReplayWindowConfig { pn_per_second:1_000,cache_horizon_ms:100,
        fec_horizon_ms:0,rtt_ms:0,metadata_budget_bytes:80 }
}
fn reverse_receiver(suite:RecordSuite)->ReplayProtectedLaneRx{
    ReplayProtectedLaneRx::new_for_suite(reverse_keys(),536,suite,replay_config()).unwrap()
}
fn bound()->BoundReceiptIngress{
    BoundReceiptIngress::from_verified_session(
        reverse_receiver(RecordSuite::ChaCha20Poly1305),
        lane(),lane(),epoch(),epoch(),512
    ).unwrap()
}
#[derive(Default)]
struct Sink{datagrams:Vec<Vec<u8>>,mode:u8}
impl ReadyPacketSink for Sink{
    fn try_send(&mut self,wire:&[u8])->io::Result<usize>{
        if self.mode==1{return Err(io::Error::from(ErrorKind::WouldBlock))}
        if self.mode==2{self.datagrams.push(wire.to_vec());return Ok(wire.len()-1)}
        self.datagrams.push(wire.to_vec());
        Ok(wire.len())
    }
}
#[test]
fn r2_m0_real_authenticated_health_only_releases_original_m1_shadow() {
    let mut arena=Arena::new(66,2,256,1,100_000).unwrap();
    let original=original(&mut arena,0);
    let old=original.bytes().to_vec();
    let mut tx=Sink::default();
    let accepted=submit_ready(&mut tx,std::slice::from_ref(&original));
    assert_eq!(accepted.accepted_prefix,1); // syscall copy, NOT peer ACK
    assert_eq!(tx.datagrams[0],old);
    let mut shadow=state();
    shadow.on_sent(original.clone(),MonoNs(0),MonoNs(2000)).unwrap();
    assert_eq!(shadow.outstanding(),1);
    let mut ingress=bound();

    let mut corrupt=reply(true);
    let last=corrupt.len()-1;
    corrupt[last]^=0x80;
    assert!(matches!(ingress.accept_one(&mut corrupt,&mut shadow,MonoNs(11)),
        Err(ReceiptIngressError::Crypto(_))));
    assert_eq!(shadow.outstanding(),1);
    let mut false_kind=vec![0;FIXED_WIRE_OVERHEAD];
    let mut data_seal=LaneTxCrypto::new(reverse_keys(),536).unwrap();
    // The wire PN must be genuinely unique. Burn a local PN0 (never published)
    // and authenticate an unrelated LINK record at PN1. The genuine
    // Health PN0 may then arrive out of order within the same replay window.
    let mut unpublished=[0;FIXED_WIRE_OVERHEAD];
    data_seal.seal_in_place(AUTHENTICATED_HEALTH_KIND,&mut unpublished,0,0).unwrap();
    assert_eq!(data_seal.seal_in_place(AUTHENTICATED_LINK_KIND,&mut false_kind,0,0).unwrap().0,1);
    assert!(matches!(ingress.accept_one(&mut false_kind,&mut shadow,MonoNs(11)),
        Err(ReceiptIngressError::NotHealth)));
    assert_eq!(shadow.outstanding(),1);

    let mut authentic=reply(true);
    let released=ingress.accept_one(&mut authentic,&mut shadow,MonoNs(12)).unwrap();
    assert_eq!(released.len(),1);
    assert_eq!(released[0].pn,RecordPn(0));
    assert!(std::ptr::eq(released[0].frozen.bytes().as_ptr(),original.bytes().as_ptr()));
    assert_eq!(released[0].frozen.bytes(),old);
    assert_eq!(shadow.outstanding(),0);
    let mut another=reply(true);
    assert!(matches!(ingress.accept_one(&mut another,&mut shadow,MonoNs(13)),
        Err(ReceiptIngressError::Replay(UniqueOpenError::Duplicate))));
    assert_eq!(ingress.replay_stats().delivered,2); // LINK PN1 + Health PN0
    assert_eq!(ingress.replay_stats().duplicates,1);
    drop(released);drop(original);
    assert_eq!(arena.drain_returns(),1);
    assert_eq!(arena.report().loaned,0);
}

#[test]
fn r2_m0_bad_lane_epoch_or_key_never_authorizes_receipt() {
    for (data_lane,feedback_lane,ep,reverse_ep) in [
        (lane(),different_lane(),epoch(),epoch()),
        (lane(),lane(),epoch(),[43;16]),
        (lane(),lane(),[0;16],[0;16]),
    ] {
        assert!(matches!(BoundReceiptIngress::from_verified_session(
            reverse_receiver(RecordSuite::ChaCha20Poly1305),
            data_lane,feedback_lane,ep,reverse_ep,512
        ),Err(ReceiptIngressError::UnboundLaneEpoch)));
    }
    let mut arena=Arena::new(77,1,256,1,60_000).unwrap();
    let frozen=original(&mut arena,0);
    let mut shadow=state();
    shadow.on_sent(frozen.clone(),MonoNs(0),MonoNs(2000)).unwrap();
    let mut wrong=BoundReceiptIngress::from_verified_session(
        ReplayProtectedLaneRx::new(data_keys(),536,replay_config()).unwrap(),
        lane(),lane(),epoch(),epoch(),512
    ).unwrap();
    let mut feedback=reply(true);
    assert!(matches!(wrong.accept_one(&mut feedback,&mut shadow,MonoNs(8)),
        Err(ReceiptIngressError::Crypto(_))));
    assert_eq!(shadow.outstanding(),1);
    drop(shadow);drop(frozen);
    assert_eq!(arena.drain_returns(),1);
}

#[test]
fn r2_m0_repair_result_maps_ready_driver_without_new_cipher_or_false_ack(){
    let mut arena=Arena::new(88,2,256,1,60_000).unwrap();
    let frozen=original(&mut arena,0);
    let second_frozen=original(&mut arena,1); // distinct true PN
    let sealed=second_frozen.bytes().to_vec();
    let wire=outer_wire_bytes(&frozen);
    let wire2=outer_wire_bytes(&second_frozen);
    let mut budget=budget();
    // Only a truthful native ReadyPacketSink definite prefix earns F.
    // Make that precondition explicit for each separate immutable M1 PN.
    let mut copied_first=Sink::default();
    let result=submit_ready(&mut copied_first,std::slice::from_ref(&frozen));
    assert_eq!(result.accepted_prefix,1);
    assert_eq!(copied_first.datagrams.as_slice(),&[frozen.bytes().to_vec()]);
    budget.on_fresh_accepted(wire,MonoNs(0)).unwrap();
    assert_eq!(budget.snapshot().fresh_confirmed_bytes,wire);
    assert_eq!(budget.snapshot().epoch_repair_limit,32_768);
    let mut shadow=state();
    shadow.on_sent(frozen.clone(),MonoNs(0),MonoNs(1000)).unwrap();
    let first=shadow.on_timer(MonoNs(100)).candidates.remove(0);
    assert!(std::ptr::eq(first.frozen().bytes().as_ptr(),frozen.bytes().as_ptr()));
    let mut wouldblock=Sink{mode:1,..Sink::default()};
    assert!(matches!(submit_test(&mut shadow,&mut budget,&first,&mut wouldblock,MonoNs(100)),
        Ok(RepairSendResult::NotSent)));
    // v3 is one opportunity: proven NotSent returns the optional frozen
    // shadow immediately, but does NOT invent a peer receipt or F credit.
    assert_eq!(shadow.outstanding(),0);
    assert!(!shadow.preflight(&first,MonoNs(101)));
    assert_eq!(budget.snapshot().charged_repair_bytes,0); // definite EAGAIN refund
    assert_eq!(budget.snapshot().pending_count,0);
    assert!(shadow.on_timer(MonoNs(101)).candidates.is_empty());
    // A *new* original M1 PN can still enter the recovery budget after
    // the old candidate retired; it is not a second retry of PN0.
    let mut copied_second=Sink::default();
    let result=submit_ready(&mut copied_second,std::slice::from_ref(&second_frozen));
    assert_eq!(result.accepted_prefix,1);
    assert_eq!(copied_second.datagrams.as_slice(),&[sealed.clone()]);
    shadow.on_sent(second_frozen.clone(),MonoNs(101),MonoNs(1101)).unwrap();
    budget.on_fresh_accepted(wire2,MonoNs(101)).unwrap();
    let second=shadow.on_timer(MonoNs(300)).candidates.remove(0);
    let mut short=Sink{mode:2,..Sink::default()};
    assert!(matches!(submit_test(&mut shadow,&mut budget,&second,&mut short,MonoNs(300)),
        Ok(RepairSendResult::Uncertain)));
    assert!(matches!(submit_test(&mut shadow,&mut budget,&second,&mut short,MonoNs(300)),
        Err(ReceiptIngressError::StaleCandidate)));
    assert_eq!(second_frozen.bytes(),sealed);
    assert_eq!(budget.snapshot().charged_repair_bytes,wire2);
    assert_eq!(budget.snapshot().pending_count,0);
    assert_eq!(budget.snapshot().fresh_confirmed_bytes,wire+wire2);
    assert_eq!(short.datagrams.len(),1);
    assert_valid_packet(&short.datagrams[0],&second_frozen,40);
    assert_eq!(&short.datagrams[0][40..],sealed.as_slice());
    // An uncertain kernel syscall is NOT a receipt: all charged bytes
    // remain charged, while optional one-chance ciphertext retention ends.
    assert_eq!(shadow.outstanding(),0);
    assert!(!shadow.preflight(&second,MonoNs(301)));
    drop(first);drop(second);drop(shadow);drop(frozen);drop(second_frozen);
    assert_eq!(arena.drain_returns(),2);
}


#[test]
fn r2_m0_authenticated_reverse_replay_duplicate_and_bad_tag_never_repeat_receipt() {
    let mut arena=Arena::new(89,1,256,1,60_000).unwrap();
    let frozen=original(&mut arena,0);
    let original_bytes=frozen.bytes().to_vec();
    let mut shadow=state();
    shadow.on_sent(frozen.clone(),MonoNs(0),MonoNs(2000)).unwrap();
    let mut ingress=bound();
    assert_eq!(ingress.replay_info().effective_window_pn,256);
    assert_eq!(ingress.replay_info().allocated_metadata_bytes,80);
    let mut tx=LaneTxCrypto::new(reverse_keys(),536).unwrap();
    let first=reply_with_tx(&mut tx,false,1); // PN0: authentic negative evidence
    assert!(ingress.accept_one(&mut first.clone(),&mut shadow,MonoNs(10)).unwrap().is_empty());
    assert_eq!(shadow.outstanding(),1);
    assert_eq!(ingress.replay_max_seen(),Some(0));
    // This is an actually valid AEAD record: it must not even REENTER M2,
    // despite M2's independent idempotent receipts/late positive handling.
    assert!(matches!(ingress.accept_one(&mut first.clone(),&mut shadow,MonoNs(11)),
        Err(ReceiptIngressError::Replay(UniqueOpenError::Duplicate))));
    assert_eq!(ingress.replay_stats().duplicates,1);
    let second=reply_with_tx(&mut tx,true,2); // PN1
    let mut tampered=second.clone();
    let last=tampered.len()-1;tampered[last]^=1;
    assert!(matches!(ingress.accept_one(&mut tampered,&mut shadow,MonoNs(12)),
        Err(ReceiptIngressError::Crypto(CryptoError::Authentication))));
    assert_eq!(ingress.replay_max_seen(),Some(0)); // failed tag cannot poison floor
    assert_eq!(shadow.outstanding(),1);
    let released=ingress.accept_one(&mut second.clone(),&mut shadow,MonoNs(13)).unwrap();
    assert_eq!(released.len(),1);
    assert_eq!(released[0].frozen.bytes(),original_bytes);
    assert_eq!(shadow.outstanding(),0);
    assert!(matches!(ingress.accept_one(&mut second.clone(),&mut shadow,MonoNs(14)),
        Err(ReceiptIngressError::Replay(UniqueOpenError::Duplicate))));
    assert_eq!(ingress.replay_stats().delivered,2);
    assert_eq!(ingress.replay_stats().duplicates,2);
    assert_eq!(ingress.replay_stats().invalid_records,1);
    drop(released);drop(shadow);drop(frozen);
    assert_eq!(arena.drain_returns(),1);
}

#[test]
fn r2_m0_retired_valid_health_cannot_release_shadow_after_authenticated_pn_jump() {
    let mut arena=Arena::new(90,1,256,1,60_000).unwrap();
    let frozen=original(&mut arena,0);
    let mut shadow=state();
    shadow.on_sent(frozen.clone(),MonoNs(0),MonoNs(2000)).unwrap();
    let mut ingress=bound();
    let mut tx=LaneTxCrypto::new(reverse_keys(),536).unwrap();
    let low=reply_with_tx(&mut tx,false,1); // PN0
    let retired_positive=reply_with_tx(&mut tx,true,2); // PN1
    assert!(ingress.accept_one(&mut low.clone(),&mut shadow,MonoNs(10)).unwrap().is_empty());
    for _ in 2..257 { let _=reply_with_tx(&mut tx,false,1); } // legal unique PN2..256, unsent
    let advanced=reply_with_tx(&mut tx,false,3); // PN257 -> retired floor 2
    assert!(ingress.accept_one(&mut advanced.clone(),&mut shadow,MonoNs(11)).unwrap().is_empty());
    assert_eq!(ingress.replay_max_seen(),Some(257));
    assert_eq!(ingress.replay_stats().retired,0);
    assert!(matches!(ingress.accept_one(&mut retired_positive.clone(),&mut shadow,MonoNs(12)),
        Err(ReceiptIngressError::Replay(UniqueOpenError::Retired))));
    assert_eq!(ingress.replay_stats().retired,1);
    assert_eq!(shadow.outstanding(),1);
    let high=reply_with_tx(&mut tx,true,4); // PN258, authentic new acknowledgement
    let released=ingress.accept_one(&mut high.clone(),&mut shadow,MonoNs(13)).unwrap();
    assert_eq!(released.len(),1);
    assert_eq!(shadow.outstanding(),0);
    assert_eq!(ingress.replay_stats().delivered,3);
    drop(released);drop(shadow);drop(frozen);
    assert_eq!(arena.drain_returns(),1);
}

#[test]
fn r2_m0_reverse_three_actual_suites_health_is_aead_first_and_one_time() {
    for (i,suite) in [RecordSuite::ChaCha20Poly1305,RecordSuite::Aes128Gcm,
                      RecordSuite::Aes256Gcm].into_iter().enumerate() {
        let mut ingress=BoundReceiptIngress::from_verified_session(
            reverse_receiver(suite),lane(),lane(),epoch(),epoch(),512).unwrap();
        let mut arena=Arena::new(91+i as u32,1,256,1,60_000).unwrap();
        let frozen=original(&mut arena,0);
        let mut shadow=state();
        shadow.on_sent(frozen.clone(),MonoNs(0),MonoNs(2000)).unwrap();
        let mut tx=LaneTxCrypto::new_for_suite(reverse_keys(),536,suite).unwrap();
        let valid=reply_with_tx(&mut tx,true,1);
        let mut broken=valid.clone();broken[14]^=0x80;
        assert!(matches!(ingress.accept_one(&mut broken,&mut shadow,MonoNs(5)),
            Err(ReceiptIngressError::Crypto(_))));
        assert_eq!(ingress.replay_max_seen(),None);
        assert_eq!(shadow.outstanding(),1);
        let result=ingress.accept_one(&mut valid.clone(),&mut shadow,MonoNs(6)).unwrap();
        assert_eq!(result.len(),1);
        assert_eq!(result[0].pn,RecordPn(0));
        assert_eq!(shadow.outstanding(),0);
        assert!(matches!(ingress.accept_one(&mut valid.clone(),&mut shadow,MonoNs(7)),
            Err(ReceiptIngressError::Replay(UniqueOpenError::Duplicate))));
        assert_eq!(ingress.replay_stats().delivered,1);
        drop(result);drop(shadow);drop(frozen);
        assert_eq!(arena.drain_returns(),1);
    }
}


#[test]
fn r2_m0_budget_real_frozen_m4_accepted_charges_exact_outer_wire_without_ack(){
    let mut arena=Arena::new(92,1,256,1,60_000).unwrap();
    let frozen=original(&mut arena,0);
    let sealed=frozen.bytes().to_vec();
    let wire=outer_wire_bytes(&frozen);
    let mut budget=budget();
    let mut shadow=state();
    shadow.on_sent(frozen.clone(),MonoNs(0),MonoNs(1000)).unwrap();
    let candidate=shadow.on_timer(MonoNs(100)).candidates.remove(0);
    let mut sink=Sink::default();
    assert_eq!(submit_test(&mut shadow,&mut budget,&candidate,&mut sink,MonoNs(100))
        .unwrap(),RepairSendResult::Accepted);
    assert_eq!(sink.datagrams.len(),1);
    assert_valid_packet(&sink.datagrams[0],&frozen,40);
    assert_eq!(&sink.datagrams[0][40..],sealed.as_slice());
    assert_eq!(frozen.bytes(),sealed);
    assert_eq!(budget.snapshot().charged_repair_bytes,wire);
    assert_eq!(budget.snapshot().fresh_confirmed_bytes,0); // repair does NOT earn F
    assert_eq!(budget.snapshot().pending_count,0);
    assert_eq!(shadow.outstanding(),0); // one optional repair completed; not peer ACK
    assert!(!shadow.preflight(&candidate,MonoNs(101)));
    assert!(matches!(submit_test(
        &mut shadow,&mut budget,&candidate,&mut sink,MonoNs(100)),
        Err(ReceiptIngressError::StaleCandidate)));
    assert_eq!(sink.datagrams.len(),1);
    assert_eq!(budget.snapshot().charged_repair_bytes,wire);
    drop(candidate);drop(shadow);drop(frozen);
    assert_eq!(arena.drain_returns(),1);
}

#[test]
fn r2_m0_budget_rejects_small_mtu_and_other_tunnel_before_driver(){
    let mut arena=Arena::new(93,1,256,1,60_000).unwrap();
    let frozen=original(&mut arena,0);
    let wire=outer_wire_bytes(&frozen);
    let mut shadow=state();
    shadow.on_sent(frozen.clone(),MonoNs(0),MonoNs(1000)).unwrap();
    let candidate=shadow.on_timer(MonoNs(100)).candidates.remove(0);
    let mut sink=Sink::default();
    let mut smaller=budget_with(lane().tunnel,wire-1);
    assert!(matches!(submit_test(
        &mut shadow,&mut smaller,&candidate,&mut sink,MonoNs(100)),
        Err(ReceiptIngressError::Budget(BudgetError::InvalidFrame))));
    assert_eq!(smaller.snapshot().charged_repair_bytes,0);
    assert_eq!(sink.datagrams.len(),0);
    let mut other=budget_with(
        TunnelKey{slot:99,generation:3},536);
    assert!(matches!(submit_test(
        &mut shadow,&mut other,&candidate,&mut sink,MonoNs(100)),
        Err(ReceiptIngressError::Budget(BudgetError::WrongTunnel))));
    assert_eq!(other.snapshot().charged_repair_bytes,0);
    assert_eq!(shadow.outstanding(),1);
    assert_eq!(ipv4_tcp::measure(frozen.bytes().len(),None).unwrap().required as u64,wire);
    drop(candidate);drop(shadow);drop(frozen);
    assert_eq!(arena.drain_returns(),1);
}


#[test]
fn r2_m0_m4_actual_ipv4_tcp_options_wire_bytes_budget_and_checksum(){
    let mut arena=Arena::new(95,1,256,1,60_000).unwrap();
    let frozen=original(&mut arena,0);
    let mut shadow=state();
    shadow.on_sent(frozen.clone(),MonoNs(0),MonoNs(1000)).unwrap();
    let candidate=shadow.on_timer(MonoNs(100)).candidates.remove(0);
    let options=[1,1,8,10,0,0,0,1,0,0,0,2,0,0,0,0];
    let measure=ipv4_tcp::measure(frozen.bytes().len(),Some(&options)).unwrap();
    assert_eq!(measure.overhead,56);
    let mut budget=budget();
    let mut sink=Sink::default();
    let mut scratch=[0x5a;536];
    let mut ack=presentation();ack.ack32=345;ack.ip_id=123;
    let result=submit_repair_once(&mut shadow,&mut budget,&candidate,
        &mut sink,trusted_tuple(),ack,Some(&options),536,&mut scratch,MonoNs(100));
    assert_eq!(result.unwrap(),RepairSendResult::Accepted);
    assert_eq!(sink.datagrams.len(),1);
    assert_eq!(sink.datagrams[0].len(),measure.required);
    assert_eq!(sink.datagrams[0][32]>>4,9);
    assert_eq!(&sink.datagrams[0][40..56],&options);
    assert_eq!(&sink.datagrams[0][28..32],&345u32.to_be_bytes());
    assert_valid_packet(&sink.datagrams[0],&frozen,56);
    assert_eq!(budget.snapshot().charged_repair_bytes,measure.required as u64);
    assert_eq!(budget.snapshot().fresh_confirmed_bytes,0);
    assert_eq!(shadow.outstanding(),0);
    assert!(!shadow.preflight(&candidate,MonoNs(101))); // no duplicate repair
    drop(candidate);drop(shadow);drop(frozen);
    assert_eq!(arena.drain_returns(),1);
}
#[test]
fn r2_m0_m4_invalid_outer_packet_scratch_mtu_tuple_never_debits_or_sends(){
    let mut arena=Arena::new(96,1,256,1,60_000).unwrap();
    let frozen=original(&mut arena,0);
    let mut shadow=state();
    shadow.on_sent(frozen.clone(),MonoNs(0),MonoNs(1000)).unwrap();
    let candidate=shadow.on_timer(MonoNs(100)).candidates.remove(0);
    let wire=outer_wire_bytes(&frozen) as usize;
    let mut budget=budget();
    let mut sink=Sink::default();
    let mut scratch=[0x5a;536];
    assert!(matches!(submit_repair_once(&mut shadow,&mut budget,&candidate,
        &mut sink,trusted_tuple(),presentation(),None,wire-1,
        &mut scratch,MonoNs(100)),
        Err(ReceiptIngressError::Packet(PacketError::MtuExceeded{..}))));
    let mut too_small=[0u8;1];
    assert!(matches!(submit_repair_once(&mut shadow,&mut budget,&candidate,
        &mut sink,trusted_tuple(),presentation(),None,536,
        &mut too_small,MonoNs(100)),
        Err(ReceiptIngressError::Packet(PacketError::ScratchTooSmall{..}))));
    let bad=Ipv4Tuple{src_ip:&[0,0,0,0],..trusted_tuple()};
    assert!(matches!(submit_repair_once(&mut shadow,&mut budget,&candidate,
        &mut sink,bad,presentation(),None,536,
        &mut scratch,MonoNs(100)),
        Err(ReceiptIngressError::Packet(PacketError::InvalidIpv4Tuple))));
    assert!(scratch.iter().all(|x|*x==0x5a)); // preflight failure is atomic
    assert_eq!(budget.snapshot().charged_repair_bytes,0);
    assert_eq!(budget.snapshot().pending_count,0);
    assert!(sink.datagrams.is_empty());
    assert_eq!(shadow.outstanding(),1);
    drop(candidate);drop(shadow);drop(frozen);
    assert_eq!(arena.drain_returns(),1);
}

fn multi_broker(wire:u64)->GlobalRepairAllocator{
 GlobalRepairAllocator::new(GlobalRepairConfig{
     max_bytes_per_epoch:2*wire, max_directions:4,
     max_grant_bytes:wire, max_grant_lifetime_ns:50_000_000,
     max_pending:4,max_pending_bytes:4*wire
 },MonoNs(0)).unwrap()
}
fn other_lane()->LaneKey{
 LaneKey{tunnel:TunnelKey{slot:6,generation:3},slot:2,generation:7}
}
fn other_original(a:&mut Arena)->FrozenRecord{
 let payload=b"other";
 let mut tx=LaneTxCrypto::new(data_keys(),536).unwrap();
 let mut b=a.allocate().unwrap();
 b.writable()[14..14+payload.len()].copy_from_slice(payload);
 let (pn,len)=tx.seal_in_place(AUTHENTICATED_LINK_KIND,b.writable(),payload.len(),0).unwrap();
 b.freeze(0..len,FrozenMetadata{
   lane:other_lane(),pn:RecordPn(pn),seq:SeqOffset(0),carrier_snapshot:11
 }).unwrap()
}
fn local_cfg()->RepairBudgetConfig{
 RepairBudgetConfig{outer_mtu:536,max_repair_bytes_per_epoch:100_000,
 max_pending_reservations:8,max_pending_bytes:4096,io_timeout_ns:1_000_000}
}
#[test]
fn r2_m0_global_sparse_exact_outer_bytes_multi_tunnel_direction_and_notsent(){
 let mut a=Arena::new(401,2,256,1,80_000).unwrap();
 let first=original(&mut a,0);
 let second=other_original(&mut a);
 let first_bytes=first.bytes().to_vec();
 let second_bytes=second.bytes().to_vec();
 let first_wire=outer_wire_bytes(&first);
 let second_wire=outer_wire_bytes(&second);
 assert!(first_wire>=second_wire);
 let dir1=BudgetDirection{tunnel:lane().tunnel,direction:WireDirection::ClientToServer};
 let dir2=BudgetDirection{tunnel:other_lane().tunnel,direction:WireDirection::ClientToServer};
 let reverse=BudgetDirection{tunnel:lane().tunnel,direction:WireDirection::ServerToClient};
 let mut global=multi_broker(first_wire);
 for dir in [dir1,dir2,reverse]{
    global.register(dir,local_cfg(),MonoNs(0)).unwrap();
 }
 assert_eq!(global.local_snapshot(dir1).unwrap().fresh_confirmed_bytes,0);
 assert_eq!(global.local_snapshot(dir2).unwrap().epoch_repair_limit,32768);
 let g1=global.grant(dir1,first_wire,10_000_000,MonoNs(1)).unwrap();
 let g2=global.grant(dir2,second_wire,10_000_000,MonoNs(1)).unwrap();
 assert_eq!(global.grant(reverse,first_wire,10_000_000,MonoNs(1)),
     Err(GlobalRepairError::GlobalCap));
 let mut s1=state();
 let mut s2=ReceiptState::new(other_lane(),ReceiptConfig{
     max_shadow_entries:8,pto_ns:100,reorder_window_ns:5}).unwrap();
 s1.on_sent(first.clone(),MonoNs(0),MonoNs(500_000_000)).unwrap();
 s2.on_sent(second.clone(),MonoNs(0),MonoNs(500_000_000)).unwrap();
 let c1=s1.on_timer(MonoNs(100)).candidates.remove(0);
 let c2=s2.on_timer(MonoNs(100)).candidates.remove(0);
 let mut blocked=Sink{mode:1,..Sink::default()};
 let mut scratch=[0u8;536];
 assert_eq!(submit_global_repair_once(&mut s1,&mut global,g1,&c1,
     &mut blocked,trusted_tuple(),presentation(),None,536,&mut scratch,MonoNs(100)).unwrap(),
     RepairSendResult::NotSent);
 assert_eq!(global.snapshot().charged_repairs,0);
 assert_eq!(global.snapshot().held_unused_grants,first_wire+second_wire);
 assert_eq!(blocked.datagrams.len(),0);
 global.revoke(g1,MonoNs(101)).unwrap();
 assert_eq!(global.snapshot().held_unused_grants,second_wire);
 let gv=global.grant(reverse,first_wire,10_000_000,MonoNs(102)).unwrap();
 assert_eq!(gv.direction(),reverse);
 let mut uncertain=Sink{mode:2,..Sink::default()};
 assert_eq!(submit_global_repair_once(&mut s2,&mut global,g2,&c2,
     &mut uncertain,trusted_tuple(),presentation(),None,536,&mut scratch,MonoNs(103)).unwrap(),
     RepairSendResult::Uncertain);
 assert_eq!(global.snapshot().charged_repairs,second_wire);
 assert_eq!(global.snapshot().pending,0);
 assert_eq!(global.snapshot().held_unused_grants,first_wire);
 assert_eq!(uncertain.datagrams.len(),1);
 assert_valid_packet(&uncertain.datagrams[0],&second,40);
 assert_eq!(&uncertain.datagrams[0][40..],second_bytes);
 assert_eq!(first.bytes(),first_bytes);
 assert_eq!(second.bytes(),second_bytes);
 assert_eq!(s1.outstanding(),0); // definitely NotSent retired PN0 opportunity
 assert_eq!(s2.outstanding(),0); // Uncertain charged, one chance finished
 assert!(!s2.preflight(&c2,MonoNs(104))); // cannot double-charge/reseal
 // Confirmed F on the process owner is never blocked by repair caps:
 global.on_fresh_accepted(dir1,first_wire,MonoNs(104)).unwrap();
 assert_eq!(global.local_snapshot(dir1).unwrap().fresh_confirmed_bytes,first_wire);
 assert_eq!(global.snapshot().charged_repairs,second_wire);
 assert_eq!(global.grant(dir1,first_wire,10_000_000,MonoNs(105)),
     Err(GlobalRepairError::GlobalCap)); // reverse grant held and uncertainty still charged
 global.revoke(gv,MonoNs(106)).unwrap();
 assert_eq!(global.snapshot().held_unused_grants,0);
 assert_eq!(global.snapshot().charged_repairs,second_wire);
 drop(c1);drop(c2);drop(s1);drop(s2);drop(first);drop(second);
 assert_eq!(a.drain_returns(),2); // two independently frozen tunnel records
}
