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

