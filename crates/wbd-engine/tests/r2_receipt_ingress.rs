//! M0 actual M1 frozen handle + M3 real crypto + M2 pure recovery + M4
//! bounded ready-only sink. Test-only trusted key/epoch; no live Go admission.
use std::io::{self,ErrorKind};
use wbd_codec::{encode_control,ControlTlv,Receipt,ReceiptPage as WirePage};
use wbd_codec::record_crypto::{DirectionKeys,LaneRxCrypto,LaneTxCrypto};
use wbd_codec::record_frame::{AUTHENTICATED_HEALTH_KIND,AUTHENTICATED_LINK_KIND,FIXED_WIRE_OVERHEAD};
use wbd_engine::memory::{Arena,FrozenRecord};
use wbd_engine::recovery_ingress::{BoundReceiptIngress,ReceiptIngressError,submit_repair_once};
use wbd_platform::r1::{submit_ready,ReadyPacketSink};
use wbd_recovery::{ReceiptConfig,ReceiptState,RepairSendResult};
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
fn original(a:&mut Arena,pn_expected:u64)->FrozenRecord{
    let business=b"\x00R2-original\xff";
    let mut tx=LaneTxCrypto::new(data_keys(),536).unwrap();
    let mut b=a.allocate().unwrap();
    b.writable()[14..14+business.len()].copy_from_slice(business);
    let (pn,n)=tx.seal_in_place(AUTHENTICATED_LINK_KIND,b.writable(),business.len(),0).unwrap();
    assert_eq!(pn,pn_expected);
    b.freeze(0..n,FrozenMetadata{
        lane:lane(),pn:RecordPn(pn),seq:SeqOffset(0),carrier_snapshot:11
    }).unwrap()
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
fn bound()->BoundReceiptIngress{
    BoundReceiptIngress::from_verified_session(
        LaneRxCrypto::new(reverse_keys(),536).unwrap(),
        lane(),lane(),epoch(),epoch(),512
    ).unwrap()
}
#[derive(Default)]
struct Sink{datagrams:Vec<Vec<u8>>,mode:u8}
impl ReadyPacketSink for Sink{
    fn try_send(&mut self,wire:&[u8])->io::Result<usize>{
        if self.mode==1{return Err(io::Error::from(ErrorKind::WouldBlock))}
        if self.mode==2{return Ok(wire.len()-1)}
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
    let ingress=bound();

    let mut corrupt=reply(true);
    corrupt[corrupt.len()-1]^=0x80;
    assert!(matches!(ingress.accept_one(&mut corrupt,&mut shadow,MonoNs(11)),
        Err(ReceiptIngressError::Crypto(_))));
    assert_eq!(shadow.outstanding(),1);
    let mut false_kind=vec![0;FIXED_WIRE_OVERHEAD];
    let mut data_seal=LaneTxCrypto::new(reverse_keys(),536).unwrap();
    data_seal.seal_in_place(AUTHENTICATED_LINK_KIND,&mut false_kind,0,0).unwrap();
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
    assert!(ingress.accept_one(&mut another,&mut shadow,MonoNs(13)).unwrap().is_empty());
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
            LaneRxCrypto::new(reverse_keys(),536).unwrap(),
            data_lane,feedback_lane,ep,reverse_ep,512
        ),Err(ReceiptIngressError::UnboundLaneEpoch)));
    }
    let mut arena=Arena::new(77,1,256,1,60_000).unwrap();
    let frozen=original(&mut arena,0);
    let mut shadow=state();
    shadow.on_sent(frozen.clone(),MonoNs(0),MonoNs(2000)).unwrap();
    let wrong=BoundReceiptIngress::from_verified_session(
        LaneRxCrypto::new(data_keys(),536).unwrap(),
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
    let mut arena=Arena::new(88,1,256,1,60_000).unwrap();
    let frozen=original(&mut arena,0);
    let sealed=frozen.bytes().to_vec();
    let mut shadow=state();
    shadow.on_sent(frozen.clone(),MonoNs(0),MonoNs(1000)).unwrap();
    let first=shadow.on_timer(MonoNs(100)).candidates.remove(0);
    assert!(std::ptr::eq(first.frozen().bytes().as_ptr(),frozen.bytes().as_ptr()));
    let mut wouldblock=Sink{mode:1,..Sink::default()};
    assert!(matches!(submit_repair_once(&mut shadow,&first,&mut wouldblock,MonoNs(100)),
        Ok(RepairSendResult::NotSent)));
    assert_eq!(shadow.outstanding(),1);
    let noimmediate=shadow.on_timer(MonoNs(101));
    assert!(noimmediate.candidates.is_empty());
    let second=shadow.on_timer(MonoNs(200)).candidates.remove(0);
    let mut short=Sink{mode:2,..Sink::default()};
    assert!(matches!(submit_repair_once(&mut shadow,&second,&mut short,MonoNs(200)),
        Ok(RepairSendResult::Uncertain)));
    assert!(matches!(submit_repair_once(&mut shadow,&second,&mut short,MonoNs(200)),
        Err(ReceiptIngressError::StaleCandidate)));
    assert_eq!(frozen.bytes(),sealed);
    assert_eq!(shadow.outstanding(),1); // unknown syscall outcome is NOT receipt
    drop(first);drop(second);drop(shadow);drop(frozen);
    assert_eq!(arena.drain_returns(),1);
}
