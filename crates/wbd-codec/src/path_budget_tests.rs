//! R1 FrameBudget tests located under LINK module to isolate legacy R0 13-test harness.
use crate::path_budget::*;
    use crate::link_fec_wire::{fragment_compat,inspect_link,LinkMode,LinkView,LINK_MAGIC};
    fn input(outer:usize,fec:FecReservation)->FrameBudgetInput {
        FrameBudgetInput { connection_mtu:outer, local_packet_mtu:0, ipv4_header_len:20,
            tcp_header_len:20, peer_mss:Some((outer-40) as u16),
            record_wire_limit:MAX_WIRE_LEN,fec,game:false }
    }
    /// Literal pinned Go oracle, NOT computed from Rust implementation.
    #[test]
    fn r1_budget_go_six_mtu_oracle_and_exact_overheads() {
        const GO:&[(usize,usize,usize,usize,usize,usize,usize)]=&[
            (576,536,505,505,449,485,429),
            (1280,1240,1209,1209,1153,1189,1133),
            (1400,1360,1329,1329,1273,1309,1253),
            (1500,1460,1429,1429,1373,1409,1353),
            (1600,1560,1529,1529,1473,1509,1453),
            (9000,8960,8929,8929,8873,8909,8853)];
        for &(outer,carrier,record,off,on,chunk_off,chunk_on) in GO {
            for fec in [FecReservation::FixedOff,FecReservation::Fixed {parity_shards:4},
                        FecReservation::Fixed {parity_shards:20}] {
                let b=FrameBudget::derive(input(outer,fec)).unwrap();
                let enabled=fec!=FecReservation::FixedOff;
                assert_eq!((b.effective_packet_mtu,b.packet_payload_mtu,b.carrier_payload_mtu),
                    (outer,carrier,carrier));
                assert_eq!((b.record_wire_mtu,b.record_payload_mtu,b.record_overhead),
                    (carrier,record,31));
                assert_eq!(b.fec_overhead,if enabled {56}else{0});
                assert_eq!(b.link_frame_mtu,if enabled {on}else{off});
                assert_eq!(b.link_fragment_payload_mtu,if enabled {chunk_on}else{chunk_off});
                assert_eq!(b.max_fec_wire_datagram(),record);
                assert_eq!(b.outer_packet_len_for_record(carrier),Some(outer));
                assert_eq!(b.padding_headroom(record),Ok(0));
                assert_eq!(b.padding_headroom(record-1),Ok(1));
            }
        }
    }
    #[test]
    fn r1_budget_go_mss_headers_local_and_record_limit() {
        let mut i=input(9000,FecReservation::FixedOff);
        i.peer_mss=None;
        let b=FrameBudget::derive(i).unwrap();
        assert_eq!((b.peer_mss,b.peer_mss_advertised,b.carrier_payload_mtu,b.record_payload_mtu),
            (536,false,536,505));
        i=input(1500,FecReservation::FixedOff); i.peer_mss=Some(1200);
        assert_eq!(FrameBudget::derive(i).unwrap().record_wire_mtu,1200);
        i=input(1500,FecReservation::FixedOff); i.tcp_header_len=32;
        assert_eq!(FrameBudget::derive(i).unwrap().carrier_payload_mtu,1448);
        i=input(1500,FecReservation::FixedOff); i.local_packet_mtu=1400;
        assert_eq!(FrameBudget::derive(i).unwrap().carrier_payload_mtu,1360);
        i=input(1500,FecReservation::FixedOff); i.record_wire_limit=1000;
        let b=FrameBudget::derive(i).unwrap();
        assert_eq!((b.carrier_payload_mtu,b.record_wire_mtu,b.record_payload_mtu,b.link_frame_mtu),
            (1460,1000,969,969));
        assert_eq!(b.padding_headroom(970),Err(BudgetError::PayloadExceeded));
    }
    #[test]
    fn r1_budget_normal_off_minus_equal_plus_one_no_new_link_header() {
        let b=FrameBudget::derive(input(1500,FecReservation::FixedOff)).unwrap();
        for n in [b.link_frame_mtu-1,b.link_frame_mtu] {
            let p=vec![0x5a;n];
            let wire=fragment_compat(&p,b.link_frame_mtu,LinkMode::FixedOff,7).unwrap();
            assert_eq!(wire,vec![p.clone()]);
            assert_eq!(inspect_link(&wire[0],b.link_frame_mtu,LinkMode::FixedOff),
                       Ok(LinkView::Ordinary(p.as_slice())));
            let outer=b.outer_packet_len_for_record(wire[0].len()+31).unwrap();
            assert!(outer<=b.effective_packet_mtu);
        }
        let p=vec![0x5a;b.link_frame_mtu+1];
        let wire=fragment_compat(&p,b.link_frame_mtu,LinkMode::FixedOff,7).unwrap();
        assert_eq!(wire.len(),2);
        assert!(wire.iter().all(|f|f.starts_with(LINK_MAGIC) && f.len()<=b.link_frame_mtu));
        assert_eq!(wire[0].len()-LINK_HEADER,b.link_fragment_payload_mtu);
        let escape=fragment_compat(LINK_MAGIC,b.link_frame_mtu,LinkMode::FixedOff,7).unwrap();
        assert_eq!(escape.len(),1);
        assert_eq!(escape[0].len(),LINK_HEADER+LINK_MAGIC.len());
    }
    #[test]
    fn r1_budget_adaptive_current_off_and_game_once_per_logical_packet() {
        let fixed=FrameBudget::derive(input(1400,FecReservation::FixedOff)).unwrap();
        let adaptive=FrameBudget::derive(input(1400,FecReservation::Adaptive { maximum_parity_shards:20 })).unwrap();
        let on=FrameBudget::derive(input(1400,FecReservation::Fixed { parity_shards:20 })).unwrap();
        assert_eq!(adaptive.link_frame_mtu,on.link_frame_mtu);
        assert_eq!(fixed.link_frame_mtu-adaptive.link_frame_mtu,56);
        let p=vec![0x5a;adaptive.link_frame_mtu];
        assert_eq!(fragment_compat(&p,adaptive.link_frame_mtu,LinkMode::AdaptiveOff,1).unwrap(),vec![p]);
        for fec in [FecReservation::FixedOff,FecReservation::Fixed {parity_shards:4},
                    FecReservation::Adaptive {maximum_parity_shards:20}] {
            let mut i=input(1500,fec);
            let normal=FrameBudget::derive(i).unwrap();
            i.game=true;
            let game=FrameBudget::derive(i).unwrap();
            assert_eq!(normal.link_frame_mtu,game.link_frame_mtu);
            assert_eq!(normal.link_fragment_payload_mtu,game.link_fragment_payload_mtu);
            assert_eq!(normal.single_business_payload_mtu-game.single_business_payload_mtu,16);
            assert!(game.fits_single_business_by_size(game.single_business_payload_mtu));
            assert!(!game.fits_single_business_by_size(game.single_business_payload_mtu+1));
        }
    }
    #[test]
    fn r1_budget_go_tun_floor_and_auto_record_cap() {
        for (outer,cap,parity,want) in [(1400,1300,0,1269),(1500,1300,0,1269),
            (1400,1250,0,1219),(1400,1250,20,1163),(1400,1300,4,1213),
            (576,1300,20,576),(1400,800,20,713)] {
            let fec=if parity==0 { FecReservation::FixedOff } else {FecReservation::Fixed {parity_shards:parity as u8}};
            let mut i=input(outer,fec);i.record_wire_limit=cap;
            assert_eq!(FrameBudget::tunnel_interface_mtu(i),Ok(want));
        }
        for (outer,cap,want) in [(576,0,536),(1300,0,1260),(1400,0,1360),
            (1500,0,1460),(1500,1250,1250),(1400,2000,1360)] {
            assert_eq!(resolve_record_wire_limit(outer,20,20,cap),Ok(want));
        }
        assert_eq!(resolve_record_wire_limit(1400,20,32,0),Ok(1348));
    }
    #[test]
    fn r1_budget_go_invalid_boundary_fail_closed() {
        let mut i=input(1500,FecReservation::FixedOff);
        for bad in [575,9001] {i.connection_mtu=bad;assert_eq!(FrameBudget::derive(i),Err(BudgetError::ConnectionMtu));}
        i=input(1500,FecReservation::FixedOff);i.local_packet_mtu=575;
        assert_eq!(FrameBudget::derive(i),Err(BudgetError::ConnectionMtu));
        i=input(1500,FecReservation::FixedOff);i.ipv4_header_len=21;
        assert_eq!(FrameBudget::derive(i),Err(BudgetError::InvalidHeader));
        i=input(1500,FecReservation::FixedOff);i.tcp_header_len=16;
        assert_eq!(FrameBudget::derive(i),Err(BudgetError::InvalidHeader));
        i=input(1500,FecReservation::FixedOff);i.peer_mss=Some(0);
        assert_eq!(FrameBudget::derive(i),Err(BudgetError::InvalidMss));
        i=input(1500,FecReservation::FixedOff);i.record_wire_limit=MAX_WIRE_LEN+1;
        assert_eq!(FrameBudget::derive(i),Err(BudgetError::InvalidRecordLimit));
        i=input(1500,FecReservation::Fixed {parity_shards:9});
        assert_eq!(FrameBudget::derive(i),Err(BudgetError::InvalidFecProfile));
        for fec in [FecReservation::FixedOff,FecReservation::Fixed {parity_shards:4}] {
            i=input(1500,fec);
            i.record_wire_limit=31+20+if fec==FecReservation::FixedOff {0}else{56};
            assert_eq!(FrameBudget::derive(i),Err(BudgetError::ConnectionMtu));
            i.record_wire_limit+=1;
            assert_eq!(FrameBudget::derive(i).unwrap().link_fragment_payload_mtu,1);
        }
        assert_eq!(resolve_record_wire_limit(1400,20,20,51),Err(BudgetError::InvalidRecordLimit));
    }

