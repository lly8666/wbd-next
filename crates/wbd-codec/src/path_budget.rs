//! Single owner of IP/TCP/MSS/record/LINK/FEC/Game deductions.
//! Pinned oracle: wobuzhidao@a7a82db31fe736ffedee330795a3234d358f1984
//! internal/pathmtu/budget.go + budget_test.go. Do not subtract downstream again.
//! Game envelope applies once BEFORE LINK fragmentation; LINK20 only on fragments.
#![forbid(unsafe_code)]
use crate::link_fec_wire::{FEC_HEADER, FEC_PARITY_PROFILES, LINK_HEADER};
use crate::record_frame::{FIXED_WIRE_OVERHEAD, MAX_WIRE_LEN};

pub const MIN_CONNECTION_MTU: usize = 576;
pub const MAX_CONNECTION_MTU: usize = 9000;
pub const DEFAULT_IPV4_PEER_MSS: usize = 536;
pub const GAME_OVERHEAD: usize = 16;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum BudgetError { ConnectionMtu, InvalidHeader, InvalidMss, InvalidRecordLimit, InvalidFecProfile, PayloadExceeded }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum FecReservation {
    FixedOff,
    Fixed { parity_shards: u8 },
    /// Reserve the full FEC header even if adaptive is currently off.
    Adaptive { maximum_parity_shards: u8 },
}
impl FecReservation {
    fn overhead(self) -> Result<usize, BudgetError> {
        let r = match self {
            Self::FixedOff => return Ok(0),
            Self::Fixed { parity_shards } => parity_shards,
            Self::Adaptive { maximum_parity_shards } => maximum_parity_shards,
        };
        if !FEC_PARITY_PROFILES.contains(&r) { return Err(BudgetError::InvalidFecProfile); }
        Ok(FEC_HEADER)
    }
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct FrameBudgetInput {
    pub connection_mtu: usize,
    /// 0 means no additional local ceiling.
    pub local_packet_mtu: usize,
    pub ipv4_header_len: usize,
    pub tcp_header_len: usize,
    /// None means Go faketcp 536B IPv4 fallback; Some(0) is invalid.
    pub peer_mss: Option<u16>,
    /// Complete negotiated wire limit, including 31B record overhead.
    pub record_wire_limit: usize,
    pub fec: FecReservation,
    pub game: bool,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct FrameBudget {
    pub effective_packet_mtu: usize,
    pub ipv4_header_len: usize,
    pub tcp_header_len: usize,
    pub peer_mss: usize,
    pub peer_mss_advertised: bool,
    pub packet_payload_mtu: usize,
    pub carrier_payload_mtu: usize,
    pub record_wire_mtu: usize,
    pub record_payload_mtu: usize,
    pub record_overhead: usize,
    pub fec_overhead: usize,
    /// Complete LINK frame capacity. Pass directly to fragment_compat.
    pub link_frame_mtu: usize,
    /// ONLY a fragmented packet uses this chunk capacity.
    pub link_fragment_payload_mtu: usize,
    /// Zero for Normal; 16 bytes for a complete Game logical packet.
    pub game_overhead: usize,
    /// Single ordinary BUSINESS packet limit before required magic escape.
    pub single_business_payload_mtu: usize,
}
fn valid_header(n: usize) -> bool { (20..=60).contains(&n) && n%4 == 0 }
/// Mirrors Go ResolveConfiguredRecordWireLimit; cap=0 means automatic.
pub fn resolve_record_wire_limit(outer: usize, ip: usize, tcp: usize, cap: usize) -> Result<usize, BudgetError> {
    if !(MIN_CONNECTION_MTU..=MAX_CONNECTION_MTU).contains(&outer) { return Err(BudgetError::ConnectionMtu); }
    if !valid_header(ip) || !valid_header(tcp) { return Err(BudgetError::InvalidHeader); }
    if cap > MAX_WIRE_LEN || (cap != 0 && cap <= FIXED_WIRE_OVERHEAD+LINK_HEADER) {
        return Err(BudgetError::InvalidRecordLimit);
    }
    let nominal = (outer-ip-tcp).min(MAX_WIRE_LEN);
    let wire = if cap == 0 { nominal } else { nominal.min(cap) };
    if wire <= FIXED_WIRE_OVERHEAD+LINK_HEADER { return Err(BudgetError::ConnectionMtu); }
    Ok(wire)
}
impl FrameBudget {
    pub fn derive(i: FrameBudgetInput) -> Result<Self, BudgetError> {
        if !(MIN_CONNECTION_MTU..=MAX_CONNECTION_MTU).contains(&i.connection_mtu) ||
            (i.local_packet_mtu != 0 && i.local_packet_mtu < MIN_CONNECTION_MTU) {
            return Err(BudgetError::ConnectionMtu);
        }
        if !valid_header(i.ipv4_header_len) || !valid_header(i.tcp_header_len) {
            return Err(BudgetError::InvalidHeader);
        }
        if !(FIXED_WIRE_OVERHEAD..=MAX_WIRE_LEN).contains(&i.record_wire_limit) {
            return Err(BudgetError::InvalidRecordLimit);
        }
        let fec_overhead = i.fec.overhead()?;
        let effective = if i.local_packet_mtu == 0 { i.connection_mtu }
                        else { i.connection_mtu.min(i.local_packet_mtu) };
        let header_len = i.ipv4_header_len + i.tcp_header_len;
        if effective <= header_len { return Err(BudgetError::ConnectionMtu); }
        let packet_payload = effective-header_len;
        let (mss, advertised) = match i.peer_mss {
            None => (DEFAULT_IPV4_PEER_MSS,false),
            Some(0) => return Err(BudgetError::InvalidMss),
            Some(n) => (usize::from(n),true),
        };
        let carrier_payload = packet_payload.min(mss);
        if carrier_payload < FIXED_WIRE_OVERHEAD { return Err(BudgetError::ConnectionMtu); }
        let record_wire = carrier_payload.min(i.record_wire_limit);
        let record_payload = record_wire-FIXED_WIRE_OVERHEAD;
        let link_frame = record_payload.checked_sub(fec_overhead).ok_or(BudgetError::ConnectionMtu)?;
        if link_frame <= LINK_HEADER { return Err(BudgetError::ConnectionMtu); }
        let game_overhead = if i.game { GAME_OVERHEAD } else { 0 };
        let business = link_frame.checked_sub(game_overhead).ok_or(BudgetError::ConnectionMtu)?;
        Ok(Self {
            effective_packet_mtu: effective, ipv4_header_len:i.ipv4_header_len,
            tcp_header_len:i.tcp_header_len, peer_mss:mss, peer_mss_advertised:advertised,
            packet_payload_mtu:packet_payload, carrier_payload_mtu:carrier_payload,
            record_wire_mtu:record_wire, record_payload_mtu:record_payload,
            record_overhead:FIXED_WIRE_OVERHEAD, fec_overhead,
            link_frame_mtu:link_frame, link_fragment_payload_mtu:link_frame-LINK_HEADER,
            game_overhead, single_business_payload_mtu:business,
        })
    }
    /// Size-only test; reserved LINK magic can force escape even when this fits.
    pub fn fits_single_business_by_size(&self, n: usize) -> bool { n <= self.single_business_payload_mtu }
    /// Includes FEC header if reserved; does not mean FEC is on in adaptive-off.
    pub fn max_fec_wire_datagram(&self) -> usize { self.link_frame_mtu+self.fec_overhead }
    /// Here record_len already INCLUDES 31B record overhead.
    pub fn outer_packet_len_for_record(&self, record_len: usize) -> Option<usize> {
        if record_len > self.record_wire_mtu { return None; }
        self.ipv4_header_len.checked_add(self.tcp_header_len)?.checked_add(record_len)
    }
    /// Padding is unused record payload slack, not an advance deduction.
    pub fn padding_headroom(&self, used_record_payload: usize) -> Result<usize,BudgetError> {
        self.record_payload_mtu.checked_sub(used_record_payload).ok_or(BudgetError::PayloadExceeded)
    }
    /// Shared nominal TUN envelope excludes one lane's peer MSS.
    /// At a too-small path it uses the valid IPv4 576 floor and LINK fragments.
    pub fn tunnel_interface_mtu(mut i: FrameBudgetInput) -> Result<usize,BudgetError> {
        let effective = if i.local_packet_mtu == 0 { i.connection_mtu } else { i.connection_mtu.min(i.local_packet_mtu) };
        let headers = i.ipv4_header_len.checked_add(i.tcp_header_len).ok_or(BudgetError::ConnectionMtu)?;
        let nominal = effective.checked_sub(headers).ok_or(BudgetError::ConnectionMtu)?;
        i.peer_mss = Some(u16::try_from(nominal).map_err(|_|BudgetError::ConnectionMtu)?);
        Ok(Self::derive(i)?.single_business_payload_mtu.max(MIN_CONNECTION_MTU))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
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
}
