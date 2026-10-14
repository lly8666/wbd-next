//! Old Go fragment wire/MTU oracle and stricter current LINK conflict rule.
use crate::link_reassembly::*;
use crate::link_fec_wire::{fragment_compat,LinkMode,WireError};
use crate::path_budget::{FrameBudget,FrameBudgetInput,FecReservation};
use crate::record_frame::MAX_WIRE_LEN;
fn id(n:u64)->ReassemblyScope{ReassemblyScope{tunnel_epoch:1,direction:LinkDirection::ClientToServer,packet_id_ext:n}}
fn receiver(mtu:usize,mode:LinkMode)->ReassemblyTable{ReassemblyTable::new(mtu,mtu,mode).unwrap()}
fn fixture(name:&str)->Vec<u8>{
    let txt=include_str!("../../../r0/fixtures/legacy-link-fec-wire-v1.txt");
    let row=txt.lines().find(|x|x.starts_with(&format!("{name}|"))).unwrap();
    let h=row.split('|').nth(1).unwrap();
    (0..h.len()).step_by(2).map(|n|u8::from_str_radix(&h[n..n+2],16).unwrap()).collect()
}
#[test]
fn r1_link_mtu_go_64_minus_equal_plus_one_exact_wire_reverse_delivery(){
    let mut r=receiver(64,LinkMode::FixedOff);
    for n in [63,64]{
        let data=vec![0x5a;n];
        let frames=fragment_compat(&data,64,LinkMode::FixedOff,1).unwrap();
        assert_eq!(frames,vec![data.clone()]);
        assert_eq!(r.push_after_record_auth(&frames[0],id(1),1),Ok(LinkDelivery::Ordinary(data.as_slice())));
        assert_eq!(r.state(),ReassemblyState::default());
    }
    let input=vec![0x5a;65];
    let frames=fragment_compat(&input,64,LinkMode::FixedOff,1).unwrap();
    assert_eq!(frames,vec![fixture("link64-first"),fixture("link64-last")]);
    assert_eq!(r.push_after_record_auth(&frames[1],id(1),2),Ok(LinkDelivery::Pending));
    assert_eq!(r.push_after_record_auth(&frames[1],id(1),3),Ok(LinkDelivery::Pending));
    assert_eq!(r.state().buffered_fragments,1);
    assert_eq!(r.push_after_record_auth(&frames[0],id(1),4),Ok(LinkDelivery::Reassembled(input)));
    assert_eq!(r.push_after_record_auth(&frames[0],id(1),5),Ok(LinkDelivery::Discarded));
}
#[test]
fn r1_link_magic_wf_escape_go_bytes_normal_hot_bypass(){
    for (mode,data,which) in [
        (LinkMode::FixedOff,b"WBDLFRG1".as_slice(),"link-magic-escaped"),
        (LinkMode::AdaptiveOff,b"WF!".as_slice(),"link-wf-escaped")
    ]{
        let frames=fragment_compat(data,64,mode,1).unwrap();
        assert_eq!(frames,vec![fixture(which)]);
        let mut rx=receiver(64,mode);
        assert_eq!(rx.push_after_record_auth(&frames[0],id(1),1),Ok(LinkDelivery::Reassembled(data.to_vec())));
    }
    let mut rx=receiver(64,LinkMode::FixedOff);
    assert_eq!(rx.push_after_record_auth(b"WF!",id(0),1),Ok(LinkDelivery::Ordinary(b"WF!")));
    assert_eq!(rx.state(),ReassemblyState::default());
    let mut auto=receiver(64,LinkMode::AdaptiveOff);
    assert_eq!(auto.push_after_record_auth(b"WF!",id(0),1),Err(ReassemblyError::Wire(WireError::InvalidMode)));
}
#[test]
fn r1_link_out_of_order_missing_a_does_not_block_b(){
    let a=vec![b'A';100];let b=vec![b'B';90];
    let af=fragment_compat(&a,48,LinkMode::FixedOff,1).unwrap();
    let bf=fragment_compat(&b,48,LinkMode::FixedOff,2).unwrap();
    let mut r=receiver(48,LinkMode::FixedOff);
    for (i,frag) in af.iter().enumerate(){
        if i!=1{assert_eq!(r.push_after_record_auth(frag,id(1),10),Ok(LinkDelivery::Pending));}
    }
    let mut result=LinkDelivery::Pending;
    for frag in &bf{result=r.push_after_record_auth(frag,id(2),11).unwrap();}
    assert_eq!(result,LinkDelivery::Reassembled(b));
    assert_eq!(r.state().assemblies,1);
    assert_eq!(r.push_after_record_auth(&af[1],id(1),12),Ok(LinkDelivery::Reassembled(a)));
}
#[test]
fn r1_link_conflict_stronger_than_go_retires_and_fails_closed(){
    let data=vec![0x3c;100];
    let frames=fragment_compat(&data,48,LinkMode::FixedOff,1).unwrap();
    let mut r=receiver(48,LinkMode::FixedOff);
    assert_eq!(r.push_after_record_auth(&frames[0],id(1),1),Ok(LinkDelivery::Pending));
    let mut changed=frames[0].clone();*changed.last_mut().unwrap()^=0xff;
    assert_eq!(r.push_after_record_auth(&changed,id(1),2),Err(ReassemblyError::ConflictingFragment));
    assert_eq!(r.state().assemblies,0);
    assert_eq!(r.push_after_record_auth(&frames[1],id(1),3),Ok(LinkDelivery::Discarded));
    let second=fragment_compat(&data,48,LinkMode::FixedOff,2).unwrap();
    assert_eq!(r.push_after_record_auth(&second[0],id(2),4),Ok(LinkDelivery::Pending));
    let mut bad_meta=second[1].clone();bad_meta[15]^=1;
    assert_eq!(r.push_after_record_auth(&bad_meta,id(2),5),Err(ReassemblyError::ConflictingFragment));
    assert_eq!(r.push_after_record_auth(&second[1],id(2),5),Ok(LinkDelivery::Discarded));
    let third=fragment_compat(&data,48,LinkMode::FixedOff,3).unwrap();
    assert_eq!(r.push_after_record_auth(third.last().unwrap(),id(3),6),Ok(LinkDelivery::Pending));
    let mut stride=third[0].clone();stride.pop();
    assert_eq!(r.push_after_record_auth(&stride,id(3),7),Err(ReassemblyError::ConflictingFragment));
    assert_eq!(r.push_after_record_auth(&third[0],id(3),8),Ok(LinkDelivery::Discarded));
}
#[test]
fn r1_link_ttl_absolute_5s_compact_10s_no_duplicate_extension(){
    let frames=fragment_compat(&vec![0x44;100],48,LinkMode::FixedOff,1).unwrap();
    let mut r=receiver(48,LinkMode::FixedOff);
    assert_eq!(r.push_after_record_auth(&frames[0],id(1),100),Ok(LinkDelivery::Pending));
    assert_eq!(r.push_after_record_auth(&frames[0],id(1),5000),Ok(LinkDelivery::Pending));
    r.expire(5099);assert_eq!(r.state().assemblies,1);
    r.expire(5100);assert_eq!((r.state().assemblies,r.state().retired_packet_ids),(0,1));
    assert_eq!(r.push_after_record_auth(&frames[1],id(1),5101),Ok(LinkDelivery::Discarded));
    assert_eq!(r.push_after_record_auth(b"ordinary",id(0),5101),Ok(LinkDelivery::Ordinary(b"ordinary")));
    r.expire(15100);assert_eq!(r.state().retired_packet_ids,0);
    assert_eq!(r.push_after_record_auth(&frames[0],id(1),15101),Ok(LinkDelivery::Pending));
    r.expire(10);assert_eq!(r.state().assemblies,1);
    r.expire(20101);assert_eq!(r.state().assemblies,0);
}
#[test]
fn r1_link_sixteen_slots_seventeenth_evicts_no_small_packet_hol(){
    let frames=fragment_compat(&vec![0x77;100],48,LinkMode::FixedOff,1).unwrap();
    let mut r=receiver(48,LinkMode::FixedOff);
    for packet_id in 1u64..=17{
        let mut frame=frames[0].clone();
        frame[16..20].copy_from_slice(&(packet_id as u32).to_be_bytes());
        assert_eq!(r.push_after_record_auth(&frame,id(packet_id),packet_id),Ok(LinkDelivery::Pending));
        let state=r.state();
        assert!(state.assemblies<=MAX_ASSEMBLIES && state.buffered_bytes<=MAX_BUFFERED_BYTES
            && state.buffered_fragments<=MAX_BUFFERED_FRAGMENTS &&
            state.retired_packet_ids<=MAX_RETIRED && state.metadata_charged_bytes<=MAX_METADATA_BYTES);
    }
    assert_eq!((r.state().assemblies,r.state().retired_packet_ids),(16,1));
    assert_eq!(r.push_after_record_auth(&frames[1],id(1),18),Ok(LinkDelivery::Discarded));
    assert_eq!(r.push_after_record_auth(b"healthy",id(0),18),Ok(LinkDelivery::Ordinary(b"healthy")));
}
#[test]
fn r1_link_malformed_count_id_epoch_and_generation_are_scoped(){
    let frames=fragment_compat(&vec![0x5a;65],64,LinkMode::FixedOff,1).unwrap();
    let mut r=receiver(64,LinkMode::FixedOff);
    assert_eq!(r.push_after_record_auth(&frames[0],id(2),0),Err(ReassemblyError::InvalidScope));
    let mut bad=frames[0].clone();bad[12..14].copy_from_slice(&u16::MAX.to_be_bytes());
    assert_eq!(r.push_after_record_auth(&bad,id(1),0),Err(ReassemblyError::InvalidLayout));
    assert_eq!(r.state().assemblies,0);
    let mut epoch=id(1);epoch.tunnel_epoch=2;
    assert_eq!(r.push_after_record_auth(&frames[0],epoch,1),Ok(LinkDelivery::Pending));
    assert_eq!(r.push_after_record_auth(&frames[1],epoch,2),Ok(LinkDelivery::Reassembled(vec![0x5a;65])));
    assert_eq!(r.push_after_record_auth(&frames[0],id(1),3),Ok(LinkDelivery::Discarded));
    let mut next=id((1u64<<32)|1);next.tunnel_epoch=3;
    assert_eq!(r.push_after_record_auth(&frames[0],next,4),Ok(LinkDelivery::Pending));
    assert_eq!(r.push_after_record_auth(&frames[1],next,5),Ok(LinkDelivery::Reassembled(vec![0x5a;65])));
}
#[test]
fn r1_link_max_65535_datagram_1400_1500_and_framebudget_plusone(){
    let data=(0..65_535).map(|i|(i%251) as u8).collect::<Vec<_>>();
    for (mtu,expected_count) in [(1400,48),(1500,45)]{
        let frames=fragment_compat(&data,mtu,LinkMode::FixedOff,1).unwrap();
        assert_eq!(frames.len(),expected_count);
        let mut r=receiver(mtu,LinkMode::FixedOff);
        let mut got=LinkDelivery::Pending;
        for f in frames.iter().rev(){got=r.push_after_record_auth(f,id(1),10).unwrap();}
        assert_eq!(got,LinkDelivery::Reassembled(data.clone()));
        assert_eq!(r.state().assemblies,0);
    }
    let b=FrameBudget::derive(FrameBudgetInput{
        connection_mtu:1500,local_packet_mtu:0,ipv4_header_len:20,tcp_header_len:20,
        peer_mss:Some(1460),record_wire_limit:MAX_WIRE_LEN,
        fec:FecReservation::FixedOff,game:false}).unwrap();
    assert_eq!(b.link_frame_mtu,1429);
    let p=vec![0x41;b.link_frame_mtu+1];
    let frames=fragment_compat(&p,b.link_frame_mtu,LinkMode::FixedOff,7).unwrap();
    assert!(frames.iter().all(|f|b.outer_packet_len_for_record(f.len()+31).unwrap()<=1500));
    let mut r=receiver(b.link_frame_mtu,LinkMode::FixedOff);
    assert_eq!(r.push_after_record_auth(&frames[1],id(7),1),Ok(LinkDelivery::Pending));
    assert_eq!(r.push_after_record_auth(&frames[0],id(7),2),Ok(LinkDelivery::Reassembled(p)));
}
