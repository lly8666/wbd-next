use super::*;
use crate::memory::Arena;
use wbd_types::buffer_contract::UniqueSealable;

fn owner(mode:FecMode, bytes:usize)->Fec2Owner {
    Fec2Owner::new(mode,Profile::Strong,ConfigRevision(1),
        Limits{pending_bytes:bytes,pending_jobs:64,max_frame:1536}).unwrap()
}
fn arena(id:u32,count:usize,slab:usize)->Arena {
    Arena::new(id,count,slab,1,10_000_000).unwrap()
}
fn push(owner:&mut Fec2Owner,a:&mut Arena,n:usize,at:u64)->Accepted {
    let mut b=a.allocate().unwrap();
    b.writable()[..n].fill(0x5a);
    owner.push_source(b,0..n,MonoNs(at),|ready| {
        assert_eq!(ready.frame.len(),n);
        assert!(ready.frame.iter().all(|&x|x==0x5a));
        true
    }).unwrap()
}
fn drain(o:&mut Fec2Owner,at:u64) {
    while let Some(job)=o.take_parity(MonoNs(at)).unwrap() {
        let r=job.r;
        o.finish_parity(job,r,true);
    }
}
#[test]
fn r1_fec2_f2_sched_zero_one_sixteen_32_33_first_ready() {
    let mut o=owner(FecMode::Normal,PENDING_BYTES_DEFAULT);
    let mut a=arena(901,64,256);
    assert_eq!(o.on_due(MonoNs(0)).unwrap(),0);
    assert_eq!(o.report().queued_jobs,0);
    let mut seen=Vec::new();
    for i in 0..16 {
        let mut b=a.allocate().unwrap();
        b.writable()[0]=i;
        let outcome=o.push_source(b,0..1,MonoNs(i as u64),|s| {
            seen.push((s.ticket.unwrap().index,s.frame[0]));
            true
        }).unwrap();
        assert_eq!(outcome.ticket.unwrap().block_id,1);
        assert_eq!(outcome.closed_full,i==15);
    }
    assert_eq!(seen,(0..16u8).map(|x|(x,x)).collect::<Vec<_>>());
    assert_eq!(o.report().classes[0].k_hist[16],1);
    let mut job=o.take_parity(MonoNs(16)).unwrap().unwrap();
    assert_eq!((job.k,job.r,job.source_count()),(16,16,16));
    for i in 0..16 {assert_eq!(job.source(i).unwrap(),&[i as u8]);}
    o.finish_parity(job,15,true);
    assert_eq!(o.report().classes[0].r_sent,15);
    assert_eq!(a.report().loaned,0);
    for i in 0..33 {
        let t=100+i as u64;
        let outcome=push(&mut o,&mut a,1,t);
        if i==15||i==31 {assert!(outcome.closed_full);}
    }
    assert_eq!(o.report().classes[0].full,3);
    assert_eq!(o.report().queued_jobs,2);
    drain(&mut o,200);
    o.on_due(MonoNs(6_000_200)).unwrap();
    assert_eq!(o.report().classes[0].k_hist[1],1);
    drain(&mut o,6_000_200);
    o.stop(); a.stop(); assert!(a.quiesced());
}
#[test]
fn r1_fec2_f2_sched_sparse_absolute_deadline_and_profile_revision() {
    let mut o=owner(FecMode::Normal,PENDING_BYTES_DEFAULT);
    let mut a=arena(902,8,256);
    assert_eq!(o.deadline_span_ns(Class::Small),6_000_000);
    let first=push(&mut o,&mut a,1,0).ticket.unwrap();
    assert_eq!(first.deadline,MonoNs(6_000_000));
    o.on_due(MonoNs(5_999_999)).unwrap();
    assert_eq!(o.report().classes[0].closed,0);
    let again=push(&mut o,&mut a,1,5_999_999).ticket.unwrap();
    assert_eq!((again.block_id,again.index,again.deadline),
        (first.block_id,1,first.deadline));
    o.change_policy(FecMode::Normal,Profile::Maximum,ConfigRevision(2),1536,
        MonoNs(5_999_999)).unwrap();
    let j=o.take_parity(MonoNs(5_999_999)).unwrap().unwrap();
    assert_eq!((j.k,j.r,j.revision),(2,2,ConfigRevision(1)));
    o.finish_parity(j,2,true);
    let new=push(&mut o,&mut a,1,6_000_000).ticket.unwrap();
    assert_eq!((new.index,new.revision),(0,ConfigRevision(2)));
    assert_ne!(new.block_id,first.block_id);
    o.on_due(new.deadline).unwrap();
    let j=o.take_parity(new.deadline).unwrap().unwrap();
    assert_eq!((j.k,j.r),(1,2));
    o.finish_parity(j,2,true);
    o.stop();a.stop();assert!(a.quiesced());
}
#[test]
fn r1_fec2_f2_sched_rtt_caps_min_trusted_and_no_update_under_two_seconds() {
    let mut normal=owner(FecMode::Normal,PENDING_BYTES_DEFAULT);
    let mut game=owner(FecMode::Game,PENDING_BYTES_DEFAULT);
    assert!(normal.trusted_rtt(&[None,Some(600_000_000),Some(150_000_000)],MonoNs(0)).unwrap());
    assert!(game.trusted_rtt(&[Some(600_000_000),Some(10_000_000)],MonoNs(0)).unwrap());
    assert_eq!(normal.deadline_span_ns(Class::Small),6_000_000); // no lambda yet
    assert_eq!(game.deadline_span_ns(Class::Small),3_000_000);
    assert!(!game.trusted_rtt(&[Some(600_000_000)],MonoNs(1_999_999_999)).unwrap());
    assert!(game.trusted_rtt(&[Some(600_000_000)],MonoNs(2_000_000_000)).unwrap());
    let mut a=arena(903,8,256);
    let t=push(&mut game,&mut a,1,2_000_000_000).ticket.unwrap();
    assert_eq!(t.deadline,MonoNs(2_003_000_000));
    assert_eq!(game.on_due(MonoNs(2_003_000_000)).unwrap(),1);
    drain(&mut game,2_003_000_000);
    game.stop();a.stop();assert!(a.quiesced());
}
#[test]
fn r1_fec2_f2_sched_partial_30mbps_three_logical_class_rates() {
    // Each class receives *source* 10 Mbps (30Mbps total); never multiply
    // Game source PPS by lane count, and do not count parity as source.
    for mode in [FecMode::Normal,FecMode::Game] {
        let mut o=owner(mode,PENDING_BYTES_DEFAULT);
        o.trusted_rtt(&[Some(150_000_000)],MonoNs(0)).unwrap();
        let mut small=arena(904,64,256);
        let mut medium=arena(905,64,512);
        let mut big=arena(906,64,1536);
        let mut arrivals=Vec::new();
        for (size,step) in [(200usize,160_000u64),(500,400_000),(1200,960_000)] {
            let mut t=0;
            while t<=275_000_000 {
                arrivals.push((t,size));
                t+=step;
            }
        }
        arrivals.sort_unstable();
        for (t,size) in arrivals {
            o.on_due(MonoNs(t)).unwrap();
            drain(&mut o,t);
            let a=if size==200 {&mut small} else if size==500 {&mut medium} else {&mut big};
            push(&mut o,a,size,t);
        }
        let spans=[
            o.deadline_span_ns(Class::Small),
            o.deadline_span_ns(Class::Medium),
            o.deadline_span_ns(Class::Mtu)];
        assert!(spans[0]>=2_000_000 && spans[0]<=4_000_000,"{spans:?}");
        assert!((7_500_000..=10_500_000).contains(&spans[1]),"{spans:?}");
        if mode==FecMode::Normal {
            assert!((19_000_000..=24_000_000).contains(&spans[2]),"{spans:?}");
        } else {
            assert_eq!(spans[2],12_000_000);
        }
        o.on_due(MonoNs(300_000_000)).unwrap();
        drain(&mut o,300_000_000);
        let stats=o.report().classes;
        assert!(stats[2].partial>0 && stats[0].k_hist[16]>0,
            "mixed 30Mbps class split has partial and full: {stats:?}");
        assert!(stats.iter().all(|s|s.accepted>200 && s.closed>0));
        o.stop();
        assert_eq!(small.report().loaned,0);
        assert_eq!(medium.report().loaned,0);
        assert_eq!(big.report().loaned,0);
    }
}
#[test]
fn r1_fec2_f2_mem_expiry_is_independent_of_forming_t_and_stop_preserves_loan() {
    let mut o=owner(FecMode::Game,PENDING_BYTES_DEFAULT);
    let mut a=arena(907,16,256);
    push(&mut o,&mut a,3,0);
    o.on_due(MonoNs(3_000_000)).unwrap();
    let retained=o.take_parity(MonoNs(3_000_000)).unwrap().unwrap();
    assert_eq!(o.report().outstanding_jobs,1);
    assert!(o.report().charged_bytes>0);
    o.stop();
    a.stop();
    assert_eq!(o.report().queued_jobs,0);
    assert_eq!(a.report().loaned,1);
    assert!(!a.quiesced()); // Stop cannot reclaim an external encoder loan
    drop(retained);
    assert_eq!(o.report().outstanding_jobs,0);
    assert!(a.quiesced());
    let mut p=owner(FecMode::Game,PENDING_BYTES_DEFAULT);
    let mut b=arena(908,16,256);
    push(&mut p,&mut b,1,0);
    p.on_due(MonoNs(3_000_000)).unwrap();
    assert_eq!(p.report().queued_jobs,1);
    p.on_due(MonoNs(8_000_001)).unwrap(); // 5ms post CLOSE, NOT T
    assert_eq!(p.report().classes[0].expired_jobs,1);
    assert_eq!(p.report().outstanding_jobs,0);
    p.stop();b.stop();assert!(b.quiesced());
}
#[test]
fn r1_fec2_f2_mem_pressure_source_first_ready_no_out_of_range_index() {
    let mut o=owner(FecMode::Normal,500);
    let mut a=arena(909,16,256);
    let first=push(&mut o,&mut a,1,0);
    assert_eq!(first.ticket.unwrap().index,0);
    assert!(first.fec_retained);
    let second=push(&mut o,&mut a,1,1);
    assert!(second.source_enqueued && !second.fec_retained);
    assert_eq!(second.ticket.unwrap().index,0);
    assert_ne!(first.ticket.unwrap().block_id,second.ticket.unwrap().block_id);
    assert_eq!(o.report().classes[0].k_hist[1],2);
    assert_eq!(o.report().classes[0].unknown_capacity,1);
    drain(&mut o,1);
    o.stop();a.stop();assert!(a.quiesced());
}
#[test]
fn r1_fec2_f2_sched_off_is_immediate_and_uses_no_encoder_timer() {
    let mut o=owner(FecMode::Off,PENDING_BYTES_DEFAULT);
    let mut a=arena(910,8,256);
    for i in 0..4 {
        let accepted=push(&mut o,&mut a,16,i);
        assert_eq!(accepted.ticket,None);
        assert!(!accepted.fec_retained && accepted.source_enqueued);
    }
    assert_eq!(o.next_deadline(),None);
    assert_eq!(o.report().charged_bytes,0);
    assert_eq!(o.report().classes[0].accepted,0);
    o.stop();a.stop();assert!(a.quiesced());
}
#[test]
fn r1_fec2_f2_sched_game_source_single_logical_offer_no_lane_barrier() {
    // The already-accepted Game013 GameTx handles bounded per-lane key queues;
    // FEC2 only offers ONE original logical shard to its callback.
    let mut o=owner(FecMode::Game,PENDING_BYTES_DEFAULT);
    let mut a=arena(911,8,256);
    let mut shared_calls=0;
    let mut b=a.allocate().unwrap();
    b.writable()[..32].fill(7);
    let out=o.push_source(b,0..32,MonoNs(0),|view| {
        shared_calls+=1;
        assert_eq!(view.ticket.unwrap().index,0);
        assert_eq!(view.frame,&[7u8;32]);
        // Real per-lane AEAD and transport are delegated; no shared key,
        // nonce or ciphertext, and a blocked lane cannot gate this callback.
        true
    }).unwrap();
    assert_eq!(shared_calls,1);
    assert!(out.source_enqueued);
    o.on_due(MonoNs(3_000_000)).unwrap();
    drain(&mut o,3_000_000);
    o.stop();a.stop();assert!(a.quiesced());
}
#[test]
fn r1_fec2_f2_sched_profile_k1_to16_all_seven_and_unknown_completion() {
    let ps=[
        (Profile::Light,2),(Profile::Mild,4),(Profile::Medium,6),
        (Profile::Balanced,8),(Profile::High,12),(Profile::Strong,16),
        (Profile::Maximum,20),
    ];
    for (p,expected) in ps {
        assert_eq!(p.redundancy(16),expected);
        assert!(p.redundancy(1)>=1 && p.redundancy(1)<=2);
        assert_eq!(p.redundancy(0),0);
    }
    let mut o=owner(FecMode::Normal,PENDING_BYTES_DEFAULT);
    let mut a=arena(912,32,256);
    push(&mut o,&mut a,1,0);
    o.on_due(MonoNs(6_000_000)).unwrap();
    let j=o.take_parity(MonoNs(6_000_000)).unwrap().unwrap();
    o.finish_parity(j,0,false);
    assert_eq!(o.report().classes[0].r_sent,0);
    assert_eq!(o.report().classes[0].unknown_capacity,1);
    o.stop();a.stop();assert!(a.quiesced());
}
