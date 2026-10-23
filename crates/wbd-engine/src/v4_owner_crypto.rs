//! M0 protected Go V4 crypto installation, compiled in normal engine.
//! This is NOT a public cold installer or a credential authenticator. Only
//! the private credential-checked Go V4 callsite may supply its frozen source.
//! Test probes use these exact production-compiled methods, not a duplicate
//! crypto or business delivery path.
#![forbid(unsafe_code)]

use crate::cold_v4::{ColdV4Error, ExpectedRustOwner, UntrustedColdV4};
use crate::memory::UniqueBuffer;
use crate::runtime::{QueueLimits, RxOwner, RxPacket, TxOwner,TxDispatch};
use crate::runtime::early_rx::{EarlyAccepted, EarlyError, EarlyLimits, EarlyRetirement, EarlyRxOwner};
use crate::runtime::generation::{LoanBatch, ScopedOwner, ScopeToken};
use std::ops::Range;
use wbd_types::{MonoNs,RecordPn,SeqOffset};
use wbd_types::buffer_contract::{FrozenMetadata,UniqueSealable};
use wbd_codec::record_crypto::{LaneTxCrypto, RecordSuite};
use wbd_codec::record_frame::{AUTHENTICATED_LINK_KIND,FIXED_WIRE_OVERHEAD};
use wbd_codec::link_fec_wire::{inspect_link,LinkMode,LinkView,LINK_HEADER,LINK_MAGIC};
use wbd_codec::path_budget::FrameBudget;
#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
use wbd_platform::linux_driver_outcome_lease::ScopedUdpOwner;
#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
use wbd_platform::linux_tun_sink::{ScopedTunSink,TunError};
#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
use wbd_platform::linux_raw_carrier::{ScopedRawIpv4Tx,ScopedRawIpv4Rx};
#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
use wbd_platform::ipv4_tcp::{Ipv4Tuple,Presentation,PacketPersona};
#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
use wbd_platform::r1::BatchResult;
#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
use wbd_codec::path_budget::{FrameBudgetInput,FecReservation,MAX_CONNECTION_MTU};
#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
use wbd_platform::linux_packet_preflight::{
    observe_interface_mtu,observe_ipv4_route_mtu,
};
#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
use std::net::Ipv4Addr;
use wbd_codec::link_reassembly::{
    LinkDelivery,LinkDirection,ReassemblyScope,ReassemblyTable,
};
use wbd_codec::record_replay::{
    ReplayConfigError, ReplayProtectedLaneRx, ReplayWindowConfig,
};

#[derive(Debug)]
pub(crate) enum ProtectedCryptoError {
    Scope(ColdV4Error),
    Suite,
    Tx,
    Rx(ReplayConfigError),
    Inactive,
    Owner,
    #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    Tun(TunError),
    Early(EarlyError),
}

// Genuine codec REPAIR_HEADER is 12 bytes; its body includes a protected
// 2-byte source length. RECORD_RESERVATION=14 applies to original-source
// admission, NOT to a second check of the already-parsed repair body.
// Keep this in the product owner seal path, not a test-only acceptance rule.
#[cfg(feature="fec2_product_record")]
fn original_fec2_repair_symbol_fits(body_len:usize,record_budget:usize)->bool{
    body_len<=record_budget.saturating_sub(wbd_codec::fec_v2::REPAIR_HEADER)
}

/// The scoped owner still owns dispatch, generation, driver leases and Stop.
/// This is the reusable AEAD/PN half of that owner; no payload is delivered.
pub(crate) struct ProtectedScopedCrypto {
    tx: LaneTxCrypto,
    rx: Option<ReplayProtectedLaneRx>,
    active: bool,
    generation: u32,
    go_lane: u8,
    epoch: [u8; 16],
    tx_boundary: Option<u32>,
}

impl ProtectedScopedCrypto {
    /// Private trusted-Go-call precondition; cannot infer trust from 248 bytes.
    /// Construct BOTH directions before either can be published.
    pub(crate) fn prepare_from_protected_go(
        cold: &UntrustedColdV4, expected: &ExpectedRustOwner,
    ) -> Result<Self, ProtectedCryptoError> {
        cold.preflight_untrusted_owner(expected).map_err(ProtectedCryptoError::Scope)?;
        if expected.owner_generation != expected.lane.generation
            || expected.owner_generation != expected.lane.tunnel.generation
            || expected.lane.slot != u32::from(expected.go_lane_id)
        {
            return Err(ProtectedCryptoError::Scope(ColdV4Error::ScopeMismatch));
        }
        let identity = cold.identity();
        let suite = RecordSuite::try_from(identity.cipher)
            .map_err(|_| ProtectedCryptoError::Suite)?;
        let (c2s, s2c) = cold.internal_direction_keys();
        let (tx_keys, rx_keys, tx_limit, rx_limit) = if identity.server {
            (s2c, c2s, identity.client_limit, identity.server_limit)
        } else {
            (c2s, s2c, identity.server_limit, identity.client_limit)
        };
        let tx = LaneTxCrypto::new_for_suite(tx_keys, usize::from(tx_limit), suite)
            .map_err(|_| ProtectedCryptoError::Tx)?;
        // Bounded high-rate envelope; real AEAD still precedes replay.
        let replay = ReplayWindowConfig {
            pn_per_second: 100_000, cache_horizon_ms: 3000,
            fec_horizon_ms: 0, rtt_ms: 600, metadata_budget_bytes: 256*1024,
        };
        let rx = ReplayProtectedLaneRx::new_for_suite(
            rx_keys, usize::from(rx_limit), suite, replay,
        ).map_err(ProtectedCryptoError::Rx)?;
        Ok(Self {
            tx, rx:Some(rx), active:false, generation:expected.owner_generation,
            go_lane:expected.go_lane_id, epoch:identity.logical_epoch,
            tx_boundary:None,
        })
    }

    /// Only after protected reply, Go Detach, and both owner installations.
    /// Exact Go SenderNext after protected reply is mandatory, never guessed.
    pub(crate) fn commit_after_detach(&mut self, generation:u32,
        go_lane:u8, epoch:[u8;16], exact_tx_boundary:u32,
    ) -> Result<(),ProtectedCryptoError> {
        if self.active || generation!=self.generation
            || go_lane!=self.go_lane || epoch!=self.epoch {
            return Err(ProtectedCryptoError::Inactive)
        }
        self.tx_boundary=Some(exact_tx_boundary);
        self.active=true;
        Ok(())
    }

    // Once the original protected Go Detach has committed, move rather
    // than clone the single actual AEAD+PN replay state to the RX owner.
    #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    fn detach_rx_for_original_worker(&mut self)->Option<ReplayProtectedLaneRx>{
        if !self.active{return None}
        self.rx.take()
    }
    /// Same real AEAD/PN function to be called by the eventual RX owner.
    /// Never a standalone business delivery or test-specific decryptor.
    fn retire(&mut self) {
        self.active = false;
        self.tx_boundary = None;
    }

}

/// M0 composition of the ACTUAL M1 RX/TX scoped owner with the authenticated
/// record state. Compiled into the ordinary engine, not behind test features.
/// Go's private credential-checked control callsite is the ONLY intended
/// caller; bytes alone still cannot prove TLS identity.
pub(crate) struct ProtectedScopedOwner {
    rx_tx: EarlyRxOwner,
    token: ScopeToken,
    crypto: ProtectedScopedCrypto,
    state: OwnerPhase,
    generation: u32,
    go_lane: u8,
    epoch: [u8;16],
    rx_wire_limit:usize,
    tx_wire_limit:usize,
    peer_mss:u16,
    peer_mss_advertised:bool,
    next_tx_seq:Option<u64>,
    server:bool,
    #[cfg(feature="m0_fec2_owner_probe")]
    fec2_probe_scope:Option<Fec2ProbeScope>,
}
#[cfg(feature="m0_fec2_owner_probe")]
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
struct Fec2ProbeScope{
    generation:u32,epoch:[u8;16],owner_id:u64,go_lane:u8,
    profile:u8,revision:u64,
}
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
enum OwnerPhase { Prepared, Active, Retired }

/// Counts verified records admitted to downstream LINK parsing, not
/// application first delivery. Invalid/replayed wires are never passed to
/// the caller; HEALTH remains a separate authenticated control kind.
#[derive(Clone,Copy,Debug,Default,PartialEq,Eq)]
pub(crate) struct AuthenticatedRxReport {
    pub(crate) link_ready:u32,
    pub(crate) control_ready:u32,
    pub(crate) rejected:u32,
}

/// One *owner-bound* Normal/FEC-off LINK reassembly context. This is not a
/// second crypto or activation path; it can only receive data from the actual
/// ScopedOwner's authenticated RX batch. A new owner/generation creates a
/// new table, so retired packet IDs cannot cross sessions.
pub(crate) struct NormalOffReceive {
    table:ReassemblyTable,
    frame_mtu:usize,
    owner_id:u64,
    generation:u32,
    lane:u8,
    epoch:[u8;16],
    epoch_tag:u64,
    direction:LinkDirection,
    max_extended_id:Option<u64>,
}
#[derive(Clone,Copy,Debug,Default,PartialEq,Eq)]
pub(crate) struct NormalOffReport {
    pub(crate) authenticated:AuthenticatedRxReport,
    pub(crate) completed:u32,
    pub(crate) pending:u32,
    pub(crate) discarded:u32,
    pub(crate) malformed:u32,
}
impl NormalOffReceive {
    /// frame_mtu MUST be the effective negotiated M4/Go path budget once a
    /// live carrier is installed, NOT merely a requested record limit.
    /// Explicit configuration is required: do not quietly assume local MTU.
    pub(crate) fn new_for_owner(owner:&ProtectedScopedOwner,
        effective_link_frame_mtu:usize,minimum_link_frame_mtu:usize,
    )->Result<Self,ProtectedCryptoError>{
        if effective_link_frame_mtu<=LINK_HEADER
            || effective_link_frame_mtu>
                owner.rx_wire_limit.saturating_sub(FIXED_WIRE_OVERHEAD) {
            return Err(ProtectedCryptoError::Owner)
        }
        let table=ReassemblyTable::new(effective_link_frame_mtu,
            minimum_link_frame_mtu,LinkMode::FixedOff)
            .map_err(|_|ProtectedCryptoError::Owner)?;
        let mut first=[0u8;8];first.copy_from_slice(&owner.epoch[..8]);
        Ok(Self{
            table,frame_mtu:effective_link_frame_mtu,
            owner_id:owner.token.owner_id(),generation:owner.generation,
            lane:owner.go_lane,epoch:owner.epoch,
            epoch_tag:u64::from_be_bytes(first),
            direction:if owner.server {LinkDirection::ClientToServer}
                else {LinkDirection::ServerToClient},
            max_extended_id:None,
        })
    }
    fn accepts(&self,owner:&ProtectedScopedOwner)->bool{
        self.owner_id==owner.token.owner_id()
            && self.generation==owner.generation
            && self.lane==owner.go_lane && self.epoch==owner.epoch
    }
    /// Extend the authenticated LINK32 identifier near wrap using a
    /// half-range window; far-old ambiguous IDs are rejected, not guessed.
    /// No packet_id is read before record AEAD/PN validation.
    fn extend_packet_id(&mut self,raw:u32)->Option<u64>{
        if raw==0{return None}
        let mut value=u64::from(raw);
        if let Some(max)=self.max_extended_id{
            const FULL:u64=1u64<<32;
            const HALF:u64=1u64<<31;
            value=(max & !(FULL-1))|value;
            if value<max && max-value>HALF {
                value=value.checked_add(FULL)?;
            }else if value>max && value-max>HALF {
                value=value.checked_sub(FULL)?;
            }
            if value<max && max-value>HALF{return None}
            self.max_extended_id=Some(max.max(value));
        }else{
            self.max_extended_id=Some(value);
        }
        Some(value)
    }
}


impl NormalOffReceive {
    // Shared actual M3 LINK parser/reassembly, called ONLY after original
    // record AEAD+unique PN accepts the packet. The original bootstrap
    // drain and independent background RX use the identical implementation.
    fn accept_authenticated_link<F>(&mut self,pn:u64,link:&[u8],ms:u64,
        accept_packet:&mut F,out:&mut NormalOffReport)
    where F:FnMut(u64,&[u8]){
        let id=match inspect_link(link,self.frame_mtu,LinkMode::FixedOff){
            Ok(LinkView::Ordinary(_))=>Some(0),
            Ok(LinkView::Fragment(f))=>self.extend_packet_id(f.packet_id),
            Err(_)=>{out.malformed+=1;return}
        };
        let Some(id)=id else {out.malformed+=1;return};
        let scope=ReassemblyScope{
            tunnel_epoch:self.epoch_tag,
            direction:self.direction,packet_id_ext:id,
        };
        match self.table.push_after_record_auth(link,scope,ms){
            Ok(LinkDelivery::Ordinary(bytes))=>{accept_packet(pn,bytes);out.completed+=1},
            Ok(LinkDelivery::Reassembled(bytes))=>{accept_packet(pn,&bytes);out.completed+=1},
            Ok(LinkDelivery::Pending)=>out.pending+=1,
            Ok(LinkDelivery::Discarded)=>out.discarded+=1,
            Err(_)=>out.malformed+=1,
        }
    }
}

#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
pub(crate) struct ProtectedBackgroundRx{
    rx:ReplayProtectedLaneRx,
    normal:NormalOffReceive,
    generation:u32,
    #[cfg(feature="fec2_product_record")]
    fec2:Option<(
        crate::v4_fec2_live_rx::Fec2LiveRx,
        crate::v4_fec2_live_rx::VerifiedReceiveEpoch,
        std::sync::Arc<std::sync::atomic::AtomicBool>,
    )>,
}
#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[derive(Debug,Default)]
pub(crate) struct BackgroundRxReceipt{
    pub(crate) authenticated_link:u32,
    pub(crate) delivered:u32,
    pub(crate) pending:u32,
    pub(crate) invalid:u32,
    pub(crate) failed:u32,
    // Exact peer data PN, only after this SAME protected original M3
    // opener consumed an authentic, unique normal/FEC business record.
    // Never acknowledge unauthenticated tuples, replay or malformed LINK.
    pub(crate) authenticated_data_pn:Option<u64>,
    // Only created after the SAME moved original M3 AEAD + unique PN opener.
    pub(crate) reverse_kind1:Option<AuthenticatedNormalKind1>,
    // Genuine original AEAD/PN FEC counts only: source seen/accepted 0,1;
    // parity seen/accepted 2,3; systematic/recovered candidates 4,5;
    // actual TUN writes 6,7; TUN failure 8, FEC reject 9, disabled 10.
    #[cfg(feature="fec2_product_record")]
    pub(crate) fec_rx:[u32;11],
    // Successful real M4 TUN-write classification, no packet metadata stored.
    #[cfg(feature="fec2_product_record")]
    pub(crate) fec_rx_ip:[u32;8],
}
// Bounded numeric classification ONLY after authentic first delivery reaches
// original M4 TUN. Do not retain addresses, ports, seq, ACK or payload.
#[cfg(feature="fec2_product_record")]
fn original_fec_tun_ip_class(frame:&[u8],recovered:bool,tally:&mut [u32;8]){
    let index=usize::from(recovered);
    if frame.len()<20 || frame[0]>>4!=4 {
        tally[4]=tally[4].saturating_add(1);return
    }
    match frame[9]{
        17=>tally[index]=tally[index].saturating_add(1),
        6=>{
            tally[2+index]=tally[2+index].saturating_add(1);
            let ihl=usize::from(frame[0]&0x0f)*4;
            if ihl<20||frame.len()<ihl+20{
                tally[7]=tally[7].saturating_add(1);return
            }
            let tcp_h=usize::from(frame[ihl+12]>>4)*4;
            let total=usize::from(u16::from_be_bytes([frame[2],frame[3]]));
            if tcp_h<20||total>frame.len()||total<ihl+tcp_h{
                tally[7]=tally[7].saturating_add(1);return
            }
            let data_len=total-ihl-tcp_h;
            if data_len>0{tally[6]=tally[6].saturating_add(1)}
            else if frame[ihl+13]&0x10!=0{
                tally[5]=tally[5].saturating_add(1);
            }else{tally[7]=tally[7].saturating_add(1)}
        },
        _=>tally[4]=tally[4].saturating_add(1),
    }
}

#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[derive(Debug)]
pub(crate) struct AuthenticatedNormalKind1{
    pub(crate) reverse_record_pn:u64,
    pub(crate) receipt:wbd_codec::Receipt,
}
#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
impl ProtectedBackgroundRx{
    #[cfg(feature="fec2_product_record")]
    pub(crate) fn arm_fec2_original_go_only(
        &mut self,
        exact:crate::v4_fec2_live_rx::VerifiedReceiveEpoch,
        admit:std::sync::Arc<std::sync::atomic::AtomicBool>,
        wire_limit:usize,
    )->Result<(),crate::v4_fec2_live_rx::ReceiveError>{
        use crate::v4_fec2_live_rx::{Fec2LiveRx,ReceiveError};
        if self.fec2.is_some()||exact.generation!=self.generation{
            return Err(ReceiveError::Authorization)
        }
        // Does NOT allocate its own replay opener. The existing rx field
        // owns every normal+FEC PN admission in this Go generation.
        let blocks=Fec2LiveRx::from_authenticated_scope(exact,wire_limit)?;
        self.fec2=Some((blocks,exact,admit));
        Ok(())
    }
    // The ONE moved original replay bitmap and original M3 LINK table.
    // Input is M4 checked-tuple but still UNAUTHENTICATED raw ciphertext.
    // The generation-scoped TUN driver and stop fence remain mandatory.
    pub(crate) fn consume_original(&mut self,mut slab:UniqueBuffer,
        len:usize,tun:&ScopedTunSink,now:MonoNs)->BackgroundRxReceipt{
        let mut receipt=BackgroundRxReceipt::default();
        if tun.generation()!=self.generation||tun.is_stopping()
            ||len==0||len>slab.writable().len(){return receipt}
        // Under the opt-in release feature, both kind1 and FEC kinds2/3
        // consume the SAME moved original Go-authenticated replay window.
        #[cfg(feature="fec2_product_record")]
        let open_result=if self.fec2.is_some(){
            self.rx.open_unique_with_fec2_after_admission_in_place(
                &mut slab.writable()[..len])
        }else{self.rx.open_unique_in_place(&mut slab.writable()[..len])};
        #[cfg(not(feature="fec2_product_record"))]
        let open_result=self.rx.open_unique_in_place(&mut slab.writable()[..len]);
        let opened=match open_result{
            Ok(opened)=>opened,
            Err(_)=>return receipt,
        };
        #[cfg(feature="fec2_product_record")]
        if opened.kind==2||opened.kind==3{
            use std::sync::atomic::Ordering;
            if opened.kind==2{receipt.fec_rx[0]+=1}else{receipt.fec_rx[2]+=1}
            let Some((blocks,exact,enabled))=self.fec2.as_mut()else{
                receipt.invalid=1;return receipt
            };
            // Only original Go's verified Fixed APPLIED (after real
            // kernel copy), not pending/control metadata, enables RX.
            if !enabled.load(Ordering::Acquire){
                receipt.invalid=1;receipt.fec_rx[10]+=1;return receipt
            }
            receipt.authenticated_link=1;
            match blocks.accept_authenticated(*exact,opened.kind,opened.payload,now){
                Ok(deliveries)=>{
                    if opened.kind==2{receipt.fec_rx[1]+=1}else{receipt.fec_rx[3]+=1}
                    receipt.authenticated_data_pn=Some(opened.pn);
                    if deliveries.is_empty(){receipt.pending=1}
                    for first in deliveries{
                        if first.recovered{receipt.fec_rx[5]+=1}else{receipt.fec_rx[4]+=1}
                        if tun.write_authenticated_ipv4(self.generation,&first.frame)
                            .ok()==Some(first.frame.len()){
                            receipt.delivered=receipt.delivered.saturating_add(1);
                            if first.recovered{receipt.fec_rx[7]+=1}else{receipt.fec_rx[6]+=1}
                            original_fec_tun_ip_class(&first.frame,first.recovered,&mut receipt.fec_rx_ip);
                        }else{
                            receipt.fec_rx[8]+=1;
                            // A well-formed FEC symbol is not necessarily
                            // a valid business IPv4 frame. M4 remains final
                            // validator; no app delivery is inferred.
                            receipt.failed=receipt.failed.saturating_add(1);
                        }
                    }
                }
                Err(_)=>{receipt.invalid=1;receipt.fec_rx[9]+=1},
            }
            return receipt
        }
        if opened.kind==wbd_codec::record_frame::AUTHENTICATED_HEALTH_KIND{
            // The server's moved C2S opener consumed the ONLY original PN.
            // This can never be reconstructed from raw Go metadata or
            // client-supplied bitmap without AEAD + unique replay admission.
            receipt.authenticated_link=1; // authenticated seq32 anchor only
            if opened.payload.len()>512 {
                receipt.invalid=1;
                return receipt
            }
            match wbd_codec::decode_control(opened.payload,512){
                Ok(mut items) if items.len()==1 =>{
                    if let wbd_codec::ControlTlv::Receipt(received)=items.remove(0){
                        receipt.reverse_kind1=Some(AuthenticatedNormalKind1{
                            reverse_record_pn:opened.pn,receipt:received
                        });
                    }else{receipt.invalid=1;}
                },
                _=>receipt.invalid=1,
            }
            return receipt
        }
        if opened.kind!=AUTHENTICATED_LINK_KIND{return receipt}
        receipt.authenticated_link=1;
        let mut link_report=NormalOffReport::default();
        self.normal.accept_authenticated_link(
            opened.pn,opened.payload,now.0/1_000_000,
            &mut |_pn,business|{
                if tun.write_authenticated_ipv4(self.generation,business).is_ok(){
                    receipt.delivered+=1;
                }else{receipt.failed+=1}
            },&mut link_report);
        receipt.pending=link_report.pending;
        receipt.invalid=link_report.malformed.saturating_add(link_report.discarded);
        if receipt.invalid==0 && receipt.failed==0 {
            receipt.authenticated_data_pn=Some(opened.pn);
        }
        receipt
    }
}

/// Immutable owner-bound *kernel interface MTU*, not path PMTU, socket
/// capability, driver lease or peer authentication. Private fields prevent
/// a later caller from minting its own unrestricted FrameBudget.
#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
pub(crate) struct ScopedLinuxBudget {
    pub(crate) frame:FrameBudget,
    owner_id:u64,
    generation:u32,
    epoch:[u8;16],
    pub(crate) observed_ifindex:u32,
    pub(crate) observed_interface_mtu:u32,
    pub(crate) observed_route_mtu:Option<u32>,
    ifname:String,
    route_destination:Option<Ipv4Addr>,
}

impl ProtectedScopedOwner {
    /// The exact Normal/off first-send observer is allocated only after the
    /// original Go credential-checked TLS/Detach commit. This identity is
    /// NOT a client-supplied receipt, ACK or permission to enable FEC2.
    #[cfg(any(target_os="windows",all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl"))))]
    pub(crate) fn normal_firstsend_identity(&self)->Option<(wbd_types::LaneKey,[u8;16])>{
        (self.state==OwnerPhase::Active && self.crypto.active
         && self.rx_tx.detached() && self.epoch!=[0u8;16])
        .then_some((self.token.lane(),self.epoch))
    }
    /// Transfer the SAME protected Go-authenticated RX replay opener,
    /// original Normal-off table and generation to one RX worker exactly
    /// once; the original TX queue/sealer remain with the control Entry.
    #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    pub(crate) fn detach_background_rx(&mut self,normal:NormalOffReceive)
      ->Result<ProtectedBackgroundRx,(ProtectedCryptoError,NormalOffReceive)>{
        if self.state!=OwnerPhase::Active||!self.rx_tx.detached()
            ||!normal.accepts(self){
            return Err((ProtectedCryptoError::Inactive,normal))
        }
        let Some(rx)=self.crypto.detach_rx_for_original_worker() else{
            return Err((ProtectedCryptoError::Inactive,normal))
        };
        Ok(ProtectedBackgroundRx{
            rx,normal,generation:self.generation,
            #[cfg(feature="fec2_product_record")]
            fec2:None,
        })
    }
    pub(crate) fn prepare_from_protected_go(
        cold:&UntrustedColdV4, expected:&ExpectedRustOwner,
        owner_id:u64, exact_rx_boundary:u32,
        peer_mss:u16,peer_mss_advertised:bool,
    )->Result<Self,ProtectedCryptoError>{
        // A peer's original SYN MSS is an untrusted cap, not TLS identity,
        // and MUST be bound once at the same private protected Go Prepare.
        // A later driver/CLI-provided FrameBudget must not enlarge it.
        if peer_mss<64 || (!peer_mss_advertised && peer_mss!=536){
            return Err(ProtectedCryptoError::Owner)
        }
        // Construct all resources locally; NONE is published on half failure.
        let crypto=ProtectedScopedCrypto::prepare_from_protected_go(cold,expected)?;
        // Limits name the RECEIVER. The client receives up to client_limit,
        // not server_limit; unequal authenticated MTUs must remain directional.
        let id=cold.identity();
        let wire=usize::from(if expected.server{id.server_limit}else{id.client_limit});
        let tx_wire=usize::from(if expected.server{id.client_limit}else{id.server_limit});
        let limits=QueueLimits {
            slots:32,bytes:tx_wire.saturating_mul(32),max_age_ns:50_000_000,
        };
        let rx_limits=QueueLimits {
            slots:64,bytes:wire.saturating_mul(64),max_age_ns:50_000_000,
        };
        let tx=TxOwner::new(limits,limits).ok_or(ProtectedCryptoError::Owner)?;
        let rx=RxOwner::new(rx_limits).ok_or(ProtectedCryptoError::Owner)?;
        let inner=ScopedOwner::new(owner_id,expected.owner_generation,
            expected.lane,tx,rx).ok_or(ProtectedCryptoError::Owner)?;
        let mut rx_tx=EarlyRxOwner::new(inner,EarlyLimits{
            slots:32,bytes:wire.saturating_mul(32),
        }).ok_or(ProtectedCryptoError::Owner)?;
        let token=rx_tx.token();
        rx_tx.prepare(&token,u64::from(exact_rx_boundary))
            .map_err(ProtectedCryptoError::Early)?;
        Ok(Self {
            rx_tx,token,crypto,state:OwnerPhase::Prepared,
            generation:expected.owner_generation,go_lane:expected.go_lane_id,
            epoch:expected.logical_epoch,rx_wire_limit:wire,
            tx_wire_limit:tx_wire,
            peer_mss,peer_mss_advertised,
            next_tx_seq:None,server:expected.server,
            #[cfg(feature="m0_fec2_owner_probe")]
            fec2_probe_scope:None,
        })
    }
    /// TEST ONLY: private Go callback after credential TLS + original Detach
    /// Commit. Untrusted v2 metadata/cold248 NEVER grants this authority.
    /// Test-only Go->Rust policy intent now carries the ORIGINAL Go
    /// controller's selected profile and revision AFTER TLS/Detach;
    /// production catalog/GUI and runtime reconfiguration stay OFF.
    #[cfg(feature="m0_fec2_owner_probe")]
    pub(crate) fn bind_fec2_probe_from_private_go(
        &mut self,features:u16,epoch:[u8;16],profile:u8,revision:u64,
    )->Result<(),ProtectedCryptoError>{
        if self.state!=OwnerPhase::Active||!self.crypto.active
           ||!self.rx_tx.detached()||self.crypto.tx_boundary.is_none()
           ||self.fec2_probe_scope.is_some()||features!=7||epoch!=self.epoch
           ||self.generation!=self.crypto.generation
           ||self.go_lane!=self.crypto.go_lane
           ||profile>6||revision==0 {
            return Err(ProtectedCryptoError::Inactive)
        }
        self.fec2_probe_scope=Some(Fec2ProbeScope{
            generation:self.generation,epoch,owner_id:self.token.owner_id(),
            go_lane:self.go_lane,profile,revision,
        });
        Ok(())
    }
    /// Opt-in M0-only new-FEC-block commit. Never accept a same/older
    /// applied revision, stopped owner or caller lacking the exact epoch.
    /// Actual new M1 parity work is prepared before calling this commit.
    #[cfg(feature="m0_fec2_owner_probe")]
    pub(crate) fn apply_fec2_probe_new_block_policy(
        &mut self,epoch:[u8;16],profile:u8,revision:u64
    )->Result<(),ProtectedCryptoError>{
        if !self.is_fec2_probe_bound_to(epoch)||profile>6||revision==0 {
            return Err(ProtectedCryptoError::Inactive)
        }
        let current=self.fec2_probe_scope.ok_or(ProtectedCryptoError::Inactive)?;
        if revision<=current.revision{return Err(ProtectedCryptoError::Inactive)}
        self.fec2_probe_scope=Some(Fec2ProbeScope{
            profile,revision,..current
        });
        Ok(())
    }

    // Feature-only authenticated/quiescent OFF is not a zero-parity grade:
    // 7 is a strictly INTERNAL owner state, never an on-wire profile.
    // The caller must prove no in-flight M1 loans or unsettled M2 shadow.
    // Existing ciphertext/record identities are not regenerated/refunded.
    #[cfg(feature="m0_fec2_owner_probe")]
    pub(crate) fn apply_fec2_probe_quiescent_off(
        &mut self,epoch:[u8;16],revision:u64
    )->Result<(),ProtectedCryptoError>{
        if !self.is_fec2_probe_bound_to(epoch)||revision==0{
            return Err(ProtectedCryptoError::Inactive)
        }
        let current=self.fec2_probe_scope.ok_or(ProtectedCryptoError::Inactive)?;
        if revision<=current.revision{return Err(ProtectedCryptoError::Inactive)}
        self.fec2_probe_scope=Some(Fec2ProbeScope{
            profile:7,revision,..current
        });
        Ok(())
    }

    #[cfg(feature="m0_fec2_owner_probe")]
    pub(crate) fn is_fec2_probe_bound_to(&self,epoch:[u8;16])->bool{
        self.state==OwnerPhase::Active&&self.crypto.active
        &&self.fec2_probe_scope.is_some_and(|s|
            s.generation==self.generation&&s.epoch==epoch
            &&s.owner_id==self.token.owner_id()
            &&s.go_lane==self.go_lane&&s.profile<=7&&s.revision!=0)
    }

    #[cfg(feature="m0_fec2_owner_probe")]
    pub(crate) fn fec2_probe_applied_policy(&self)->Option<(u8,u64)>{
        if !self.is_fec2_probe_bound(){return None}
        self.fec2_probe_scope.map(|scope|(scope.profile,scope.revision))
    }

    #[cfg(feature="m0_fec2_owner_probe")]
    pub(crate) fn is_fec2_probe_bound(&self)->bool{
        self.is_fec2_probe_bound_to(self.epoch)
    }

    /// The same M1 owner stages before the protected reply/Detach; no
    /// application payload may be exposed while state is Prepared.
    pub(crate) fn offer_early(&mut self,buffer:UniqueBuffer,wire:Range<usize>,
        offset:u64,now:MonoNs,
    )->Result<EarlyAccepted,(EarlyError,UniqueBuffer)>{
        if self.state!=OwnerPhase::Prepared {
            return Err((EarlyError::NotPrepared,buffer));
        }
        self.rx_tx.offer(&self.token,buffer,wire,offset,now)
    }
    pub(crate) fn commit_after_detach(&mut self,
        exact_tx_boundary:u32,
    )->Result<(),ProtectedCryptoError>{
        if self.state!=OwnerPhase::Prepared {
            return Err(ProtectedCryptoError::Inactive);
        }
        // Ensure all possible crypto commit errors precede RX Detach.
        if self.crypto.active || self.generation!=self.crypto.generation
           || self.go_lane!=self.crypto.go_lane || self.epoch!=self.crypto.epoch {
            return Err(ProtectedCryptoError::Inactive);
        }
        self.rx_tx.detach(&self.token).map_err(ProtectedCryptoError::Early)?;
        self.crypto.commit_after_detach(
            self.generation,self.go_lane,self.epoch,exact_tx_boundary,
        )?;
        self.next_tx_seq=Some(u64::from(exact_tx_boundary));
        self.state=OwnerPhase::Active;
        Ok(())
    }

    /// Observe the actual Linux kernel's LOCAL interface MTU and bind the
    /// M3 frame budget to this owner's full epoch and generation. Uses the
    /// one protected-session SYN peer MSS already stored at Prepare; there
    /// is no caller MSS parameter and no operator-controlled cold authority.
    /// The caller must still independently verify OS routing / real peer
    /// path PMTU and own a driver lease before any product activation.
    #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    pub(crate) fn observe_linux_normal_off_budget(
        &self,ifname:&str,expected_ifindex:u32,
    )->Result<ScopedLinuxBudget,ProtectedCryptoError>{
        if self.state!=OwnerPhase::Active || !self.rx_tx.detached(){
            return Err(ProtectedCryptoError::Inactive)
        }
        let kernel=observe_interface_mtu(ifname,expected_ifindex)
            .map_err(|_|ProtectedCryptoError::Owner)?;
        let observed=usize::try_from(kernel.kernel_mtu)
            .map_err(|_|ProtectedCryptoError::Tx)?;
        let connection_mtu=observed.min(MAX_CONNECTION_MTU);
        let frame=FrameBudget::derive(FrameBudgetInput{
            connection_mtu,local_packet_mtu:observed,
            ipv4_header_len:20,tcp_header_len:20,
            peer_mss:if self.peer_mss_advertised{Some(self.peer_mss)}else{None},
            record_wire_limit:self.tx_wire_limit,
            fec:FecReservation::FixedOff,game:false,
        }).map_err(|_|ProtectedCryptoError::Tx)?;
        Ok(ScopedLinuxBudget{
            frame,owner_id:self.token.owner_id(),
            generation:self.generation,epoch:self.epoch,
            observed_ifindex:kernel.ifindex,
            observed_interface_mtu:kernel.kernel_mtu,
            observed_route_mtu:None,ifname:ifname.to_owned(),
            route_destination:None,
        })
    }
    /// Kernel IPv4 connected UDP route lookup with SO_BINDTODEVICE, then
    /// IP_MTU. No datagram is sent. This is a local kernel route PMTU
    /// snapshot and never evidence of a received business packet. Real
    /// M4 carrier lease / peer end-to-end PMTUD are still required.
    #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    pub(crate) fn observe_linux_normal_off_route_budget(
        &self,ifname:&str,expected_ifindex:u32,destination:Ipv4Addr,
    )->Result<ScopedLinuxBudget,ProtectedCryptoError>{
        if self.state!=OwnerPhase::Active || !self.rx_tx.detached(){
            return Err(ProtectedCryptoError::Inactive)
        }
        let route=observe_ipv4_route_mtu(ifname,expected_ifindex,destination)
            .map_err(|_|ProtectedCryptoError::Owner)?;
        let route_mtu=usize::try_from(route.route_mtu)
            .map_err(|_|ProtectedCryptoError::Tx)?;
        let frame=FrameBudget::derive(FrameBudgetInput{
            connection_mtu:route_mtu.min(MAX_CONNECTION_MTU),
            local_packet_mtu:usize::try_from(route.interface_mtu)
                .map_err(|_|ProtectedCryptoError::Tx)?,
            ipv4_header_len:20,tcp_header_len:20,
            peer_mss:if self.peer_mss_advertised{Some(self.peer_mss)}else{None},
            record_wire_limit:self.tx_wire_limit,
            fec:FecReservation::FixedOff,game:false,
        }).map_err(|_|ProtectedCryptoError::Tx)?;
        Ok(ScopedLinuxBudget{
            frame,owner_id:self.token.owner_id(),
            generation:self.generation,epoch:self.epoch,
            observed_ifindex:route.ifindex,
            observed_interface_mtu:route.interface_mtu,
            observed_route_mtu:Some(route.route_mtu),
            ifname:ifname.to_owned(),
            route_destination:Some(destination),
        })
    }
    /// No caller-invented budget can be substituted for this kernel-observed
    /// and original-owner-scoped constraint. This still does NOT submit any
    /// packet to a kernel device; M4 driver-held Stop remains unqualified.
    #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    pub(crate) fn seal_normal_off_with_linux_budget(
        &mut self,buffer:UniqueBuffer,payload_len:usize,
        scoped:&ScopedLinuxBudget,carrier_snapshot:u64,now:MonoNs,
    )->Result<(u64,u32,usize),ProtectedCryptoError>{
        if self.state!=OwnerPhase::Active || self.generation!=scoped.generation
            || self.epoch!=scoped.epoch
            || self.token.owner_id()!=scoped.owner_id {
            return Err(ProtectedCryptoError::Inactive)
        }
        // A stale route snapshot (ifindex, interface MTU, route PMTU) never
        // authorizes sealing with an old budget. Recheck BEFORE consuming PN.
        // Route changes or an interface replacement fail closed; caller must
        // reconstruct the carrier snapshot and its M4 driver lease.
        if let Some(destination)=scoped.route_destination {
            let fresh=observe_ipv4_route_mtu(&scoped.ifname,
                scoped.observed_ifindex,destination)
                .map_err(|_|ProtectedCryptoError::Tx)?;
            if scoped.observed_route_mtu!=Some(fresh.route_mtu)
                || scoped.observed_interface_mtu!=fresh.interface_mtu {
                return Err(ProtectedCryptoError::Tx)
            }
        }else{
            let fresh=observe_interface_mtu(&scoped.ifname,scoped.observed_ifindex)
                .map_err(|_|ProtectedCryptoError::Tx)?;
            if fresh.kernel_mtu!=scoped.observed_interface_mtu {
                return Err(ProtectedCryptoError::Tx)
            }
        }
        self.seal_normal_off_one(buffer,payload_len,scoped.frame,carrier_snapshot,now)
    }

    /// Real kernel route observation and Normal/off sealing as one owner
    /// operation. Unlike seal_normal_off_with_linux_budget (which correctly
    /// rejects a cached/stale external snapshot), no kernel-observed budget
    /// escapes this call or can be saved/reused by its caller. Observe and
    /// validate ifindex/interface/route PMTU against the original SYN MSS
    /// before spending PN. The M4 raw driver still independently rechecks
    /// local interface MTU immediately before its DF sendto, and the Linux
    /// kernel rejects an oversize changed path instead of fragmenting it.
    ///
    /// This removes exactly ONE duplicated per-DATA kernel ROUTE query in
    /// the autonomous S2C Rust owner, NOT the remaining per-packet route
    /// observation. Event-scoped revision caching is still task024 OPEN.
    #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    pub(crate) fn seal_normal_off_with_fresh_route_budget(
        &mut self,buffer:UniqueBuffer,payload_len:usize,
        ifname:&str,expected_ifindex:u32,destination:Ipv4Addr,
        carrier_snapshot:u64,now:MonoNs,
    )->Result<(u64,u32,usize),ProtectedCryptoError>{
        let fresh=self.observe_linux_normal_off_route_budget(
            ifname,expected_ifindex,destination
        )?;
        if payload_len>fresh.frame.single_business_payload_mtu {
            return Err(ProtectedCryptoError::Tx)
        }
        // The snapshot is owner-created in this exact call; cannot race a
        // second observer/caller or be reused on another generation.
        self.seal_normal_off_one(
            buffer,payload_len,fresh.frame,carrier_snapshot,now
        )
    }
    /// Private, owner-created route snapshot maintained inside the same active
    /// generation's Rust worker. Unlike the compatibility API above it does
    /// not re-read kernel route on every DATA; the M4 raw sender still checks
    /// the live local link MTU and kernel DF/EMSGSIZE on every real send.
    /// Route/link netlink event invalidation is not wired yet: a bounded 1s
    /// refresh and M4 send-error invalidation are conservative interim gates.
    /// It is NOT a perpetual or caller-constructed MTU authorization.
    #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    pub(crate) fn seal_normal_off_with_worker_snapshot(
        &mut self,buffer:UniqueBuffer,payload_len:usize,
        snapshot:&ScopedLinuxBudget,expected_ifindex:u32,
        expected_destination:Ipv4Addr,carrier_snapshot:u64,now:MonoNs,
    )->Result<(u64,u32,usize),ProtectedCryptoError>{
        if self.state!=OwnerPhase::Active || !self.rx_tx.detached()
            || self.generation!=snapshot.generation
            || self.epoch!=snapshot.epoch
            || self.token.owner_id()!=snapshot.owner_id
            || snapshot.observed_ifindex!=expected_ifindex
            || snapshot.route_destination!=Some(expected_destination)
            || snapshot.observed_route_mtu.is_none(){
            return Err(ProtectedCryptoError::Inactive)
        }
        if payload_len>snapshot.frame.single_business_payload_mtu {
            return Err(ProtectedCryptoError::Tx)
        }
        self.seal_normal_off_one(
            buffer,payload_len,snapshot.frame,carrier_snapshot,now
        )
    }
    /// The original worker retains an owner-created path snapshot for one
    /// bounded TX turn. A fragment requires precisely the same generation,
    /// epoch, owner and original SYN MSS as an ordinary packet. The kernel
    /// raw sender independently enforces the live route/MTU at syscall time.
    #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    pub(crate) fn seal_fragment_with_worker_snapshot(
        &mut self,buffer:UniqueBuffer,payload_len:usize,
        snapshot:&ScopedLinuxBudget,expected_ifindex:u32,
        expected_destination:Ipv4Addr,carrier_snapshot:u64,now:MonoNs,
    )->Result<(u64,u32,usize),ProtectedCryptoError>{
        if self.state!=OwnerPhase::Active || !self.rx_tx.detached()
            || self.generation!=snapshot.generation
            || self.epoch!=snapshot.epoch
            || self.token.owner_id()!=snapshot.owner_id
            || snapshot.observed_ifindex!=expected_ifindex
            || snapshot.route_destination!=Some(expected_destination)
            || snapshot.observed_route_mtu.is_none()
            || payload_len>snapshot.frame.link_frame_mtu {
            return Err(ProtectedCryptoError::Inactive)
        }
        self.seal_normal_off_fragment_one(
            buffer,payload_len,snapshot.frame,carrier_snapshot,now)
    }
    /// Actual OS TUN app packet -> original M1 slab (no intermediate copy)
    /// -> original protected Rust owner Normal/off LINK -> S2C AEAD/PN and
    /// scoped FrozenRecord TX queue. Only packet sizes fitting the current
    /// underlying carrier are supported; oversized packets fail closed and
    /// require M3 fragmentation before production qualification.
    #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    pub(crate) fn seal_tun_ipv4_normal_off(
        &mut self,tun:&ScopedTunSink,mut slab:UniqueBuffer,
        scoped:&ScopedLinuxBudget,carrier_snapshot:u64,now:MonoNs,
    )->Result<(u64,u32,usize,usize),ProtectedCryptoError>{
        if self.state!=OwnerPhase::Active || tun.generation()!=self.generation
            || tun.is_stopping(){
            return Err(ProtectedCryptoError::Inactive)
        }
        let space=slab.writable().len().checked_sub(14)
            .ok_or(ProtectedCryptoError::Tx)?;
        if space<20{return Err(ProtectedCryptoError::Tx)}
        let read=tun.read_ipv4_into(self.generation,&mut slab.writable()[14..])
            .map_err(ProtectedCryptoError::Tun)?;
        if read>scoped.frame.single_business_payload_mtu{
            return Err(ProtectedCryptoError::Tx)
        }
        let (pn,seq,used)=self.seal_normal_off_with_linux_budget(
            slab,read,scoped,carrier_snapshot,now
        )?;
        Ok((pn,seq,used,read))
    }

    /// The actual normal-build S2C/C2S TX: one application Normal/off
    /// packet, already placed by the caller in the SAME M1 UniqueBuffer at
    /// [14 .. 14+payload_len]. Only an explicitly supplied effective M4
    /// FrameBudget can grant the wire size; never infer MSS from cold bytes.
    ///
    /// A LINK packet needing magic escape/fragmentation is rejected here,
    /// never emitted as ambiguous raw ordinary bytes. It will use the same
    /// M3 fragmenter in a subsequent bounded TX path.
    /// AEAD/PN and TCP sequence are consumed BEFORE queue publication.
    pub(crate) fn seal_normal_off_one(
        &mut self,buffer:UniqueBuffer,payload_len:usize,
        budget:FrameBudget,carrier_snapshot:u64,now:MonoNs,
    )->Result<(u64,u32,usize),ProtectedCryptoError>{
        self.seal_normal_off_validated_link(
            buffer,payload_len,budget,carrier_snapshot,now,false)
    }

    /// M0 authenticated Normal/off LINK slow path; the M3 fragmenter is
    /// the only producer. Reject magic lookalikes BEFORE spending PN or
    /// allocating a driver loan. Same normal-build M1 owner/AEAD/Seq path.
    pub(crate) fn seal_normal_off_fragment_one(
        &mut self,mut buffer:UniqueBuffer,payload_len:usize,
        budget:FrameBudget,carrier_snapshot:u64,now:MonoNs,
    )->Result<(u64,u32,usize),ProtectedCryptoError>{
        let end=14usize.checked_add(payload_len).ok_or(ProtectedCryptoError::Tx)?;
        let wire=buffer.writable().get(14..end).ok_or(ProtectedCryptoError::Tx)?;
        if !matches!(inspect_link(wire,budget.link_frame_mtu,LinkMode::FixedOff),
            Ok(LinkView::Fragment(_))) {
            return Err(ProtectedCryptoError::Tx)
        }
        self.seal_normal_off_validated_link(
            buffer,payload_len,budget,carrier_snapshot,now,true)
    }

    /// Test-build owner integration only; not a second Go permission or
    /// credential path. An actual protected feature-bit2/KDF/epoch admission
    /// has NOT been wired. In production this symbol is absent.
    /// Crucially, once such admission exists the original owner issues the
    /// same immutable M1 FrozenRecord / monotone PN and stream Seq as LINK.
    #[cfg(feature="m0_fec2_owner_probe")]
    pub(crate) fn seal_fec2_probe_one(
        &mut self,mut buffer:UniqueBuffer,payload_len:usize,kind:u8,
        budget:FrameBudget,carrier_snapshot:u64,now:MonoNs,
    )->Result<(u64,u32,usize),ProtectedCryptoError>{
        if !self.is_fec2_probe_bound_to(self.epoch){
            return Err(ProtectedCryptoError::Inactive)
        }
        let end=14usize.checked_add(payload_len).ok_or(ProtectedCryptoError::Tx)?;
        let frame=buffer.writable().get(14..end).ok_or(ProtectedCryptoError::Tx)?;
        if budget.fec_overhead!=0 || budget.game_overhead!=0
            || budget.record_payload_mtu<14
            || payload_len>budget.record_payload_mtu{return Err(ProtectedCryptoError::Tx)}
        match kind{
            2=>{
                let src=wbd_codec::fec_v2::parse_source(frame,budget.record_payload_mtu)
                    .map_err(|_|ProtectedCryptoError::Tx)?;
                if src.frame.is_empty()
                    || src.frame.len()>budget.record_payload_mtu-14{
                    return Err(ProtectedCryptoError::Tx)
                }
            },
            3=>{
                let rep=wbd_codec::fec_v2::parse_repair(frame,budget.record_payload_mtu)
                    .map_err(|_|ProtectedCryptoError::Tx)?;
                if rep.body.len()>budget.record_payload_mtu-14{
                    return Err(ProtectedCryptoError::Tx)
                }
            },
            _=>return Err(ProtectedCryptoError::Tx),
        }
        self.seal_scoped_authenticated_one(
            buffer,payload_len,budget,carrier_snapshot,now,false,kind
        )
    }

    /// Release-only original Go TLS verified FEC source/repair sealing.
    /// The caller supplies exact verified epoch/feature7/Fixed revision,
    /// while the SAME owner burns its ordinary AEAD PN and TCP seq and
    /// publishes immutable M1 records. Queue success is NOT kernel APPLIED.
    #[cfg(feature="fec2_product_record")]
    pub(crate) fn seal_fec2_product_one(
        &mut self,mut buffer:UniqueBuffer,payload_len:usize,kind:u8,
        budget:FrameBudget,carrier_snapshot:u64,epoch:[u8;16],now:MonoNs,
    )->Result<(u64,u32,usize),ProtectedCryptoError>{
        if epoch==[0;16]||epoch!=self.epoch||
            self.state!=OwnerPhase::Active||!self.rx_tx.detached(){
            return Err(ProtectedCryptoError::Inactive)
        }
        let end=14usize.checked_add(payload_len).ok_or(ProtectedCryptoError::Tx)?;
        let frame=buffer.writable().get(14..end).ok_or(ProtectedCryptoError::Tx)?;
        if budget.fec_overhead!=0||budget.game_overhead!=0||
            budget.record_payload_mtu<=14||
            payload_len>budget.record_payload_mtu{return Err(ProtectedCryptoError::Tx)}
        match kind{
            2=>{
                let src=wbd_codec::fec_v2::parse_source(
                    frame,budget.record_payload_mtu)
                    .map_err(|_|ProtectedCryptoError::Tx)?;
                if src.frame.is_empty()||src.frame.len()>budget.record_payload_mtu-14{
                    return Err(ProtectedCryptoError::Tx)
                }
            }
            3=>{
                let rep=wbd_codec::fec_v2::parse_repair(
                    frame,budget.record_payload_mtu)
                    .map_err(|_|ProtectedCryptoError::Tx)?;
                if !original_fec2_repair_symbol_fits(
                    rep.body.len(),budget.record_payload_mtu
                ){
                    return Err(ProtectedCryptoError::Tx)
                }
            }
            _=>return Err(ProtectedCryptoError::Tx)
        }
        self.seal_scoped_authenticated_one(
            buffer,payload_len,budget,carrier_snapshot,now,false,kind)
    }

    fn seal_normal_off_validated_link(
        &mut self,buffer:UniqueBuffer,payload_len:usize,
        budget:FrameBudget,carrier_snapshot:u64,now:MonoNs,
        allow_fragment:bool,
    )->Result<(u64,u32,usize),ProtectedCryptoError>{
        self.seal_scoped_authenticated_one(
            buffer,payload_len,budget,carrier_snapshot,now,
            allow_fragment,AUTHENTICATED_LINK_KIND,
        )
    }

    fn seal_scoped_authenticated_one(
        &mut self,mut buffer:UniqueBuffer,payload_len:usize,
        budget:FrameBudget,carrier_snapshot:u64,now:MonoNs,
        allow_fragment:bool,kind:u8,
    )->Result<(u64,u32,usize),ProtectedCryptoError>{
        if self.state!=OwnerPhase::Active || !self.rx_tx.detached()
            || !self.crypto.active || self.crypto.tx_boundary.is_none(){
            return Err(ProtectedCryptoError::Inactive)
        }
        if budget.peer_mss != usize::from(self.peer_mss)
            || budget.peer_mss_advertised != self.peer_mss_advertised {
            return Err(ProtectedCryptoError::Tx)
        }
        if budget.fec_overhead!=0 || budget.game_overhead!=0
            || budget.record_wire_mtu>self.tx_wire_limit
            || budget.link_frame_mtu>budget.record_payload_mtu
            || payload_len==0 || payload_len>if kind==AUTHENTICATED_LINK_KIND {
                budget.single_business_payload_mtu
            }else{budget.record_payload_mtu} {
            return Err(ProtectedCryptoError::Tx)
        }
        let used=payload_len.checked_add(FIXED_WIRE_OVERHEAD)
            .ok_or(ProtectedCryptoError::Tx)?;
        if used>budget.record_wire_mtu || buffer.writable().len()<used {
            return Err(ProtectedCryptoError::Tx)
        }
        let business=&buffer.writable()[14..14+payload_len];
        if kind==AUTHENTICATED_LINK_KIND
            && business.starts_with(LINK_MAGIC) && !allow_fragment{
            return Err(ProtectedCryptoError::Tx)
        }
        let seq64=self.next_tx_seq.ok_or(ProtectedCryptoError::Inactive)?;
        // Keep the true monotone TCP-appearance stream offset in 64 bits;
        // only the wire header projects to seq32. The old u32.checked_add
        // prematurely rejected legitimate long-lived streams at rollover.
        let next=seq64.checked_add(
            u64::try_from(used).map_err(|_|ProtectedCryptoError::Tx)?
        ).ok_or(ProtectedCryptoError::Tx)?;
        let seq=seq64 as u32;
        let (pn,sealed_len)=if matches!(kind,
            AUTHENTICATED_LINK_KIND |
            wbd_codec::record_frame::AUTHENTICATED_HEALTH_KIND
        ){
            self.crypto.tx.seal_in_place(
                kind,buffer.writable(),payload_len,0
            )
        }else{
            #[cfg(any(feature="m0_fec2_owner_probe",feature="fec2_product_record"))]
            {self.crypto.tx.seal_fec2_after_admission_in_place(
                kind,buffer.writable(),payload_len,0
            )}
            #[cfg(not(any(feature="m0_fec2_owner_probe",feature="fec2_product_record")))]
            {return Err(ProtectedCryptoError::Tx)}
        }.map_err(|_|ProtectedCryptoError::Tx)?;
        // No sequence reuse even if freezing/queue admission fails.
        self.next_tx_seq=Some(next);
        let frozen=buffer.freeze(0..sealed_len,FrozenMetadata {
            lane:self.token.lane(),seq:SeqOffset(seq64),
            pn:RecordPn(pn),carrier_snapshot,
        }).map_err(|_|ProtectedCryptoError::Tx)?;
        self.rx_tx.offer_tx_fresh(&self.token,frozen,now)
            .map_err(|_|ProtectedCryptoError::Owner)?;
        Ok((pn,seq,sealed_len))
    }

    /// Original Go TLS-bound bidirectional M2 feedback uses the SAME
    /// original active lane AEAD/PN and M1 frozen kernel queue as real DATA.
    /// Control does not create another sealer or another epoch, and never
    /// authorizes an FEC APPLIED revision by itself.
    #[cfg(feature="fec2_product_record")]
    pub(crate) fn seal_original_authenticated_receipt(
        &mut self,mut slab:UniqueBuffer,tlv:&[u8],budget:FrameBudget,
        carrier_snapshot:u64,now:MonoNs,
    )->Result<(u64,u32,usize),ProtectedCryptoError>{
        if tlv.is_empty() || tlv.len()>512 ||
            tlv.len()+14>slab.writable().len() {
            return Err(ProtectedCryptoError::Tx)
        }
        slab.writable()[14..14+tlv.len()].copy_from_slice(tlv);
        self.seal_scoped_authenticated_one(
            slab,tlv.len(),budget,carrier_snapshot,now,false,
            wbd_codec::record_frame::AUTHENTICATED_HEALTH_KIND
        )
    }

    /// The actual M1 generation-fenced FrozenRecord ready batch. It keeps
    /// cipher bytes immutable until its TX loan is recycled or dropped, and
    /// MUST be submitted to M4 only while this current owner is Active.
    pub(crate) fn drain_tx(&mut self,now:MonoNs,
        storage:Vec<TxDispatch>,
    )->Result<LoanBatch<TxDispatch>,(ProtectedCryptoError,Vec<TxDispatch>)>{
        if self.state!=OwnerPhase::Active {
            return Err((ProtectedCryptoError::Inactive,storage))
        }
        self.rx_tx.drain_tx(&self.token,now,storage)
            .map_err(|(_,s)|(ProtectedCryptoError::Owner,s))
    }
    pub(crate) fn checked_tx_ready<'a>(
        &self,batch:&'a LoanBatch<TxDispatch>,
    )->Result<&'a [TxDispatch],ProtectedCryptoError>{
        if self.state!=OwnerPhase::Active {
            return Err(ProtectedCryptoError::Inactive)
        }
        self.rx_tx.checked_tx_ready(&self.token,batch)
            .map_err(|_|ProtectedCryptoError::Owner)
    }

    /// Actual M4 Linux synchronous sendmmsg of the current protected V4
    /// owner's M1 immutable FrozenRecord TX loans. One syscall is bounded
    /// to 32 entries; payloads are NOT copied/resealed. The cloned Arc handles
    /// hold original M1 slabs through the kernel read. Never auto-replay an
    /// uncertain record: caller MUST inspect BatchResult dispositions.
    ///
    /// This is the existing M4 unprivileged UDP kernel backend; not a raw
    /// TCP/TUN adapter or proof of product business delivery. The whole
    /// driver lifetime, correct peer tuple and subsequent auth ingress
    /// remain work for the real runtime.
    #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    pub(crate) fn submit_scoped_udp_tx(&mut self,
        driver:&ScopedUdpOwner,now:MonoNs,
    )->Result<BatchResult,ProtectedCryptoError>{
        if self.state!=OwnerPhase::Active || !self.rx_tx.detached()
            || driver.generation()!=self.generation || driver.is_stopping() {
            return Err(ProtectedCryptoError::Inactive)
        }
        let batch=self.drain_tx(now,Vec::with_capacity(32))
            .map_err(|_|ProtectedCryptoError::Owner)?;
        let checked=self.checked_tx_ready(&batch)?;
        if checked.is_empty() || checked.len()>32 ||
            checked.iter().any(|x|x.kind!=crate::runtime::TxKind::Fresh){
            return Err(ProtectedCryptoError::Tx)
        }
        // Clone only the Arc-backed immutable HANDLE, never the ciphertext.
        // This Vec is bounded to <=32 and only exists until syscall returns;
        // original loan batch stays in scope across M4's BorrowFence guard.
        let records=checked.iter().map(|x|x.record.clone())
            .collect::<Vec<_>>();
        let outcome=driver.submit(self.generation,&records)
            .map_err(|_|ProtectedCryptoError::Owner)?;
        drop(batch);
        Ok(outcome)
    }

    /// Actual AF_INET/IPPROTO_RAW kernel IPv4/TCP delivery of SAME M1
    /// FrozenRecord after the protected V4 Detach/Commit. The TCP seq
    /// comes from original AEAD wire metadata; no caller-made TCP seq.
    /// Kernel acceptance is NOT peer receipt; no blind PN retransmission.
    #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    pub(crate) fn submit_scoped_raw_tx(
        &mut self,driver:&ScopedRawIpv4Tx,
        tuple:Ipv4Tuple<'_>,presentation:Presentation,now:MonoNs,
    )->Result<usize,ProtectedCryptoError>{
        if self.state!=OwnerPhase::Active || !self.rx_tx.detached()
            || driver.generation()!=self.generation || driver.is_stopping(){
            return Err(ProtectedCryptoError::Inactive)
        }
        // Compatibility caller remains legal, but the continuous Rust
        // TX worker supplies/recycles ONE original M1 ready storage vector.
        let mut storage=Vec::with_capacity(1);
        self.submit_scoped_raw_tx_reusing(
            driver,tuple,presentation,now,&mut storage
        )
    }

    /// Same actual original M1 ScopedOwner TX loan and M4 raw sender;
    /// worker owns `storage` across packets. `LoanBatch::recycle` first
    /// releases immutable frozen handles AND its generation-held lease,
    /// then returns the original Vec capacity to the same TX worker.
    /// Failed dispatch never leaks or silently retries ciphertext.
    #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    pub(crate) fn submit_scoped_raw_tx_reusing(
        &mut self,driver:&ScopedRawIpv4Tx,
        tuple:Ipv4Tuple<'_>,presentation:Presentation,now:MonoNs,
        storage:&mut Vec<TxDispatch>,
    )->Result<usize,ProtectedCryptoError>{
        if self.state!=OwnerPhase::Active || !self.rx_tx.detached()
            || driver.generation()!=self.generation || driver.is_stopping(){
            return Err(ProtectedCryptoError::Inactive)
        }
        if !storage.is_empty() || storage.capacity()==0 {
            return Err(ProtectedCryptoError::Tx)
        }
        let available=std::mem::take(storage);
        let batch=match self.drain_tx(now,available){
            Ok(batch)=>batch,
            Err((_,returned))=>{
                *storage=returned;
                return Err(ProtectedCryptoError::Owner)
            }
        };
        let outcome=(||{
            let ready=self.checked_tx_ready(&batch)?;
            if ready.len()!=1 || ready[0].kind!=crate::runtime::TxKind::Fresh {
                return Err(ProtectedCryptoError::Tx)
            }
            driver.send_one(self.generation,&ready[0].record,tuple,presentation)
                .map_err(|_|ProtectedCryptoError::Owner)
        })();
        *storage=batch.recycle();
        outcome
    }

    // Test-scope only: retain the exact M1 FrozenRecord that the original M4
    // raw driver definitely copied. No new PN, second seal, retransmission or
    // cloned ciphertext bytes. A failed/uncertain syscall grants NO shadow.
    #[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    pub(crate) fn submit_scoped_raw_tx_shadow_probe_reusing(
        &mut self,driver:&ScopedRawIpv4Tx,
        tuple:Ipv4Tuple<'_>,presentation:Presentation,now:MonoNs,
        storage:&mut Vec<TxDispatch>,
    )->Result<(usize,crate::memory::FrozenRecord),ProtectedCryptoError>{
        if self.state!=OwnerPhase::Active || !self.rx_tx.detached()
            ||driver.generation()!=self.generation||driver.is_stopping()
            ||!self.is_fec2_probe_bound()||!storage.is_empty()
            ||storage.capacity()==0{return Err(ProtectedCryptoError::Inactive)}
        let available=std::mem::take(storage);
        let batch=match self.drain_tx(now,available){
            Ok(v)=>v,Err((_,back))=>{
                *storage=back;return Err(ProtectedCryptoError::Owner)
            }
        };
        let outcome=(||{
            let ready=self.checked_tx_ready(&batch)?;
            if ready.len()!=1 ||ready[0].kind!=crate::runtime::TxKind::Fresh{
                return Err(ProtectedCryptoError::Tx)
            }
            let copied=driver.send_one(self.generation,
                &ready[0].record,tuple,presentation)
                .map_err(|_|ProtectedCryptoError::Owner)?;
            Ok((copied,ready[0].record.clone()))
        })();
        *storage=batch.recycle();
        outcome
    }

    // Original protected owner C2S M3 replay bitmap. Restricted to active,
    // privately verified Go TLS bit2 and no detached background RX worker.
    // Returning a borrowed authenticated record cannot attest a peer by itself:
    // M0 separately pins exact epoch/direction/lane before M2 admission.
    #[cfg(feature="m0_fec2_owner_probe")]
    pub(crate) fn open_reverse_health_probe<'a>(
        &mut self,wire:&'a mut [u8],
    )->Result<wbd_codec::record_crypto::OpenedRecord<'a>,ProtectedCryptoError>{
        if self.state!=OwnerPhase::Active||!self.rx_tx.detached()
            ||!self.is_fec2_probe_bound(){return Err(ProtectedCryptoError::Inactive)}
        let rx=self.crypto.rx.as_mut().ok_or(ProtectedCryptoError::Inactive)?;
        let record=rx.open_unique_in_place(wire)
            .map_err(|_|ProtectedCryptoError::Tx)?;
        if record.kind!=wbd_codec::record_frame::AUTHENTICATED_HEALTH_KIND{
            return Err(ProtectedCryptoError::Tx)
        }
        Ok(record)
    }
    #[cfg(feature="m0_fec2_owner_probe")]
    pub(crate) fn receipt_probe_identity(&self)->Option<(wbd_types::LaneKey,[u8;16])>{
        self.is_fec2_probe_bound().then_some((self.token.lane(),self.epoch))
    }

    /// Consume frozen M4-013 Linux sendmmsg scatter path from the SAME original
    /// protected Go-authenticated Rust M1 LoanBatch. This invokes one real
    /// sendmmsg syscall over header iovec + borrowed immutable ciphertext.
    /// The current worker publishes ONE packet per ready turn (not yet a 32
    /// packet aggregated syscall); never wait to fill the batch. No second
    /// AEAD/PN or copied ciphertext. Kernel copy is NOT peer delivery.
    /// Returns the copied prefix and explicit uncertain classification;
    /// ALWAYS recycle original M1 generation-held loan on every outcome.
    #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    pub(crate) fn submit_scoped_raw_tx_report_reusing(
        &mut self,driver:&ScopedRawIpv4Tx,
        tuple:Ipv4Tuple<'_>,presentation:Presentation,now:MonoNs,
        storage:&mut Vec<TxDispatch>,
    )->Result<wbd_platform::linux_batch::KernelSendReport,ProtectedCryptoError>{
        if self.state!=OwnerPhase::Active || !self.rx_tx.detached()
            || driver.generation()!=self.generation || driver.is_stopping(){
            return Err(ProtectedCryptoError::Inactive)
        }
        if !storage.is_empty() || storage.capacity()==0 {
            return Err(ProtectedCryptoError::Tx)
        }
        let available=std::mem::take(storage);
        let batch=match self.drain_tx(now,available){
            Ok(batch)=>batch,
            Err((_,returned))=>{
                *storage=returned;
                return Err(ProtectedCryptoError::Owner)
            }
        };
        let outcome=(||{
            let ready=self.checked_tx_ready(&batch)?;
            if ready.len()!=1 || ready[0].kind!=crate::runtime::TxKind::Fresh {
                return Err(ProtectedCryptoError::Tx)
            }
            // Slice of original immutable Arc-backed frozen handle, not an
            // extra Arc clone or temporary ciphertext/driver buffer.
            Ok(driver.send_kernel_multimsg(
                self.generation,std::slice::from_ref(&ready[0].record),
                tuple,std::slice::from_ref(&presentation),
            ))
        })();
        *storage=batch.recycle();
        outcome
    }

    /// Real raw IPv4/TCP RX directly into ORIGINAL M1 mutable slab, strict
    /// trusted FakeTCP tuple + TCP checksums + seq32 extension, followed
    /// by SAME scoped owner AEAD/PN replay and M3 LINK/TUN path.
    #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    pub(crate) fn receive_scoped_raw_into_owner(
        &mut self,driver:&ScopedRawIpv4Rx,mut slab:UniqueBuffer,
        tuple:Ipv4Tuple<'_>,persona:PacketPersona,
        trusted_rx_anchor:u64,now:MonoNs,
    )->Result<usize,(ProtectedCryptoError,UniqueBuffer)>{
        if self.state!=OwnerPhase::Active || !self.rx_tx.detached()
            || driver.generation()!=self.generation || driver.is_stopping(){
            return Err((ProtectedCryptoError::Inactive,slab))
        }
        let (len,seq)=match driver.recv_one_into(
            self.generation,slab.writable(),tuple,persona){
            Ok(v)=>v,
            Err(_)=>return Err((ProtectedCryptoError::Owner,slab))
        };
        if len<FIXED_WIRE_OVERHEAD {
            return Err((ProtectedCryptoError::Tx,slab))
        }
        let absolute=match wbd_platform::rx_ipv4_tcp::extend_seq32(
            trusted_rx_anchor,seq){
            Ok(v)=>v,
            Err(_)=>return Err((ProtectedCryptoError::Owner,slab))
        };
        self.offer_after_active(slab,0..len,absolute,now)
            .map_err(|(_,slab)|(ProtectedCryptoError::Owner,slab))?;
        Ok(len)
    }

    /// One genuine kernel recvmmsg directly INTO the ORIGINAL M1-owned
    /// mutable ingress slab, with M4 BorrowFence guarding the syscall.
    /// The bytes are UNAUTHENTICATED here; only the SAME normal owner
    /// RX AEAD/PN + M3 LINK drain may publish a complete business candidate.
    /// No temporary Go->Rust payload copy and no alternate RX queue.
    /// On no complete datagram the original UniqueBuffer is returned.
    #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    pub(crate) fn receive_scoped_udp_into_owner(
        &mut self,driver:&ScopedUdpOwner,mut slab:UniqueBuffer,
        absolute_seq:u64,now:MonoNs,
    )->Result<usize,(ProtectedCryptoError,UniqueBuffer)>{
        if self.state!=OwnerPhase::Active || !self.rx_tx.detached()
            || driver.generation()!=self.generation || driver.is_stopping(){
            return Err((ProtectedCryptoError::Inactive,slab))
        }
        use wbd_platform::linux_rx_batch::{RxEntry,RxStatus};
        // Recvmmsg's entire 1-slot iovec is a mutable borrow of M1 slab,
        // not of a new temporary or an arbitrary ciphertext slice.
        let outcome={
            let mut slots=[slab.writable()];
            driver.receive(self.generation,&mut slots)
        };
        let received=match outcome{
            Ok(report) if report.received==1 &&
                report.status==RxStatus::Ready =>
                match report.entry(0) {
                    Some(RxEntry::Complete{len}) if len>=FIXED_WIRE_OVERHEAD
                        && len<=slab.writable().len()=>len,
                    _=>return Err((ProtectedCryptoError::Tx,slab)),
                },
            _=>return Err((ProtectedCryptoError::Owner,slab)),
        };
        self.offer_after_active(slab,0..received,absolute_seq,now)
            .map_err(|(_,returned)|(ProtectedCryptoError::Owner,returned))?;
        Ok(received)
    }

    /// Accept an existing owned ingress slab ONLY after Go's trusted Detach
    /// and commit. The exact sequence hint enforces the bootstrap/record
    /// boundary; record PN+payload remain untrusted until AEAD validates.
    pub(crate) fn offer_after_active(&mut self,buffer:UniqueBuffer,
        wire:Range<usize>,absolute_seq:u64,now:MonoNs,
    )->Result<(),(EarlyError,UniqueBuffer)>{
        if self.state!=OwnerPhase::Active || !self.rx_tx.detached() {
            return Err((EarlyError::NotPrepared,buffer))
        }
        self.rx_tx.offer(&self.token,buffer,wire,absolute_seq,now)
            .map(|accepted| {
                // The only allowed post-Detach result is Ready.
                debug_assert_eq!(accepted,EarlyAccepted::Ready);
            })
    }

    /// The production-compiled RX path uses the REAL M1 owner queue and
    /// generation-fenced borrowed batch. Decrypt IN PLACE inside that owned
    /// slab; publish LINK data only after both AEAD and unique PN admission.
    /// The caller owns onward LINK parsing/reassembly and application
    /// delivery. No untrusted bytes, HEALTH or replay reach this callback.
    ///
    /// Supply a caller-preallocated Vec: the batch returns the same storage
    /// after its original generation ledger has been released, with no
    /// second copy or per-packet allocation.
    pub(crate) fn drain_authenticated<F>(&mut self,now:MonoNs,
        storage:Vec<RxPacket>,mut accept_link:F,
    )->Result<(Vec<RxPacket>,AuthenticatedRxReport),(ProtectedCryptoError,Vec<RxPacket>)>
    where F:FnMut(u64,&[u8]){
        if self.state!=OwnerPhase::Active {
            return Err((ProtectedCryptoError::Inactive,storage))
        }
        let mut borrowed=self.rx_tx.drain_rx(&self.token,now,storage)
            .map_err(|(err,st)|(ProtectedCryptoError::Early(err),st))?;
        let mut report=AuthenticatedRxReport::default();
        for packet in borrowed.as_mut_slice(){
            let Some(rx)=self.crypto.rx.as_mut() else{
                report.rejected+=1;
                continue
            };
            match rx.open_unique_in_place(packet.wire_mut()){
                Ok(record) if record.kind==AUTHENTICATED_LINK_KIND=>{
                    // The payload reference is tied to this mutable owner
                    // batch and cannot outlive this synchronous callback.
                    accept_link(record.pn,record.payload);
                    report.link_ready+=1;
                }
                Ok(_)=>report.control_ready+=1,
                Err(_)=>report.rejected+=1,
            }
        }
        Ok((borrowed.recycle(),report))
    }

    /// Windows M0's SAME original credential-TLS-scoped RX owner admits
    /// canonical M2 kind1 only AFTER genuine M3 AEAD and UNIQUE replay-PN.
    /// This does NOT construct a second opener, take Go's TCP ACK as trust,
    /// or implement repair dispatch. The typed callback must be paired with
    /// the current tunnel epoch/directional M2 receipt scope by its caller.
    #[cfg(target_os="windows")]
    pub(crate) fn drain_windows_authenticated_kind1<F,G>(
        &mut self,now:MonoNs,storage:Vec<RxPacket>,
        mut accept_link:F,mut accept_kind1:G,
    )->Result<(Vec<RxPacket>,AuthenticatedRxReport),
               (ProtectedCryptoError,Vec<RxPacket>)>
    where F:FnMut(u64,&[u8]), G:FnMut(u64,wbd_codec::Receipt) {
        if self.state!=OwnerPhase::Active {
            return Err((ProtectedCryptoError::Inactive,storage))
        }
        let mut borrowed=self.rx_tx.drain_rx(&self.token,now,storage)
            .map_err(|(err,st)|(ProtectedCryptoError::Early(err),st))?;
        let mut report=AuthenticatedRxReport::default();
        for packet in borrowed.as_mut_slice(){
            let Some(rx)=self.crypto.rx.as_mut() else{
                report.rejected+=1;continue
            };
            match rx.open_unique_in_place(packet.wire_mut()){
                Ok(record) if record.kind==AUTHENTICATED_LINK_KIND=>{
                    accept_link(record.pn,record.payload);
                    report.link_ready+=1;
                },
                Ok(record) if record.kind==
                    wbd_codec::record_frame::AUTHENTICATED_HEALTH_KIND=>{
                    if record.payload.len()>512 {
                        report.rejected+=1;continue
                    }
                    match wbd_codec::decode_control(record.payload,512){
                        Ok(mut items) if items.len()==1=>{
                            if let wbd_codec::ControlTlv::Receipt(receipt)=items.remove(0){
                                accept_kind1(record.pn,receipt);
                                report.control_ready+=1;
                            } else {report.rejected+=1}
                        },
                        _=>report.rejected+=1,
                    }
                },
                Ok(_)=>report.rejected+=1,
                Err(_)=>report.rejected+=1,
            }
        }
        Ok((borrowed.recycle(),report))
    }

    /// Windows original-Go feature7: the exact SAME original M1 RX owner
    /// and SAME protected M3 replay/AEAD opener admit FEC2 kind2/3.
    /// No independent second PN bitmap is created; callbacks receive only
    /// authenticated payloads. This alone is NOT a verified Go M2 APPLIED.
    #[cfg(all(target_os="windows",feature="fec2_product_record"))]
    pub(crate) fn drain_windows_authenticated_fec2<F>(
        &mut self,now:MonoNs,storage:Vec<RxPacket>,mut accept:F,
    )->Result<(Vec<RxPacket>,AuthenticatedRxReport),
               (ProtectedCryptoError,Vec<RxPacket>)>
    where F:FnMut(u64,u8,&[u8]){
        if self.state!=OwnerPhase::Active {
            return Err((ProtectedCryptoError::Inactive,storage))
        }
        let mut borrowed=self.rx_tx.drain_rx(&self.token,now,storage)
            .map_err(|(err,st)|(ProtectedCryptoError::Early(err),st))?;
        let mut report=AuthenticatedRxReport::default();
        for packet in borrowed.as_mut_slice(){
            let Some(rx)=self.crypto.rx.as_mut()else{
                report.rejected+=1;continue
            };
            match rx.open_unique_with_fec2_after_admission_in_place(
                packet.wire_mut()
            ){
                Ok(record) if matches!(record.kind,2|3)=>{
                    accept(record.pn,record.kind,record.payload);
                    report.link_ready+=1;
                },
                Ok(_)=>report.control_ready+=1,
                Err(_)=>report.rejected+=1,
            }
        }
        Ok((borrowed.recycle(),report))
    }

    /// Single normal-build ingress: owner LoanBatch -> AEAD & PN unique ->
    /// M3 LINK wire inspection / bounded reassembly -> complete packet sink.
    /// Incomplete, conflicting, stale and malformed fragments never call
    /// the sink; one new ordinary packet does not wait for any old hole.
    pub(crate) fn drain_normal_off<F>(&mut self,receiver:&mut NormalOffReceive,
        now:MonoNs,storage:Vec<RxPacket>,mut accept_packet:F,
    )->Result<(Vec<RxPacket>,NormalOffReport),(ProtectedCryptoError,Vec<RxPacket>)>
    where F:FnMut(u64,&[u8]){
        if self.state!=OwnerPhase::Active || !receiver.accepts(self){
            return Err((ProtectedCryptoError::Inactive,storage))
        }
        let ms=now.0/1_000_000;
        let mut out=NormalOffReport::default();
        let (returned,authenticated)=self.drain_authenticated(
            now,storage,|pn,link|{
                receiver.accept_authenticated_link(
                    pn,link,ms,&mut accept_packet,&mut out);

            })?;
        out.authenticated=authenticated;
        Ok((returned,out))
    }

    /// Real Linux kernel TUN application sink: ONLY the complete authenticated
    /// M3 Normal/off LINK business packet enters the attached OS TUN FD.
    /// No unauthenticated record, replay, malformed or pending fragment
    /// can reach the write. A syscall error is a LOST application delivery,
    /// not permission to reuse the consumed AEAD packet number.
    #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    pub(crate) fn drain_normal_off_to_tun(
        &mut self,receiver:&mut NormalOffReceive,tun:&ScopedTunSink,
        now:MonoNs,storage:Vec<RxPacket>,
    )->Result<(Vec<RxPacket>,NormalOffReport,u32,u32),
        (ProtectedCryptoError,Vec<RxPacket>)>{
        if self.state!=OwnerPhase::Active || tun.generation()!=self.generation
            || tun.is_stopping(){
            return Err((ProtectedCryptoError::Inactive,storage))
        }
        let generation=self.generation;
        let mut delivered=0u32;
        let mut failed=0u32;
        let (returned,report)=self.drain_normal_off(
            receiver,now,storage,|_pn,payload|{
                if tun.write_authenticated_ipv4(generation,payload).is_ok(){
                    delivered+=1;
                }else{
                    failed+=1;
                }
            }
        )?;
        Ok((returned,report,delivered,failed))
    }

    pub(crate) fn drain_rx(&mut self,now:MonoNs,storage:Vec<RxPacket>)
        ->Result<LoanBatch<RxPacket>,(EarlyError,Vec<RxPacket>)>{
        if self.state!=OwnerPhase::Active {
            return Err((EarlyError::NotPrepared,storage));
        }
        self.rx_tx.drain_rx(&self.token,now,storage)
    }
    /// Stops BOTH actual owner queues and AEAD/PN admission. Retained loan
    /// batches still own their original generation; repeat Stop is safe.
    pub(crate) fn stop(&mut self)->Result<EarlyRetirement,EarlyError>{
        self.state=OwnerPhase::Retired;
        self.crypto.retire();
        self.next_tx_seq=None;
        #[cfg(feature="m0_fec2_owner_probe")]
        {self.fec2_probe_scope=None;}
        self.rx_tx.stop(&self.token)
    }
}


#[cfg(all(test,feature="fec2_product_record"))]
mod m0_fec_rx_ip_class_contract {
    use super::original_fec_tun_ip_class;
    #[test]
    fn m0_original_fec_tun_classifies_only_post_m4_ipv4_protocol(){
        let mut c=[0u32;8];
        let mut udp=[0u8;28];udp[0]=0x45;
        udp[2..4].copy_from_slice(&28u16.to_be_bytes());udp[9]=17;
        original_fec_tun_ip_class(&udp,false,&mut c);
        original_fec_tun_ip_class(&udp,true,&mut c);
        let mut tcp=[0u8;40];tcp[0]=0x45;
        tcp[2..4].copy_from_slice(&40u16.to_be_bytes());
        tcp[9]=6;tcp[32]=0x50;tcp[33]=0x10;
        original_fec_tun_ip_class(&tcp,false,&mut c);
        let mut data=tcp.to_vec();data.push(123);
        data[2..4].copy_from_slice(&41u16.to_be_bytes());
        original_fec_tun_ip_class(&data,true,&mut c);
        let mut other=udp;other[9]=1;
        original_fec_tun_ip_class(&other,false,&mut c);
        assert_eq!(c,[1,1,1,1,1,1,1,0]);
        original_fec_tun_ip_class(&[],true,&mut c);
        assert_eq!(c[4],2);
    }
}

#[cfg(test)]
mod m0_tx_seq64_contract {
    #[test]
    fn m0_original_tx_seq64_never_restarts_pn_at_wire32_wrap(){
        let near=u64::from(u32::MAX)-15;
        let first=near.checked_add(1400).unwrap();
        let next=first.checked_add(1200).unwrap();
        assert_eq!(near as u32,u32::MAX-15);
        assert_eq!(first as u32,1384);
        assert_eq!(next as u32,2584);
        // Wire projection must not shrink the monotone owner offset.
        assert!(first>u64::from(u32::MAX) && next>first);
        assert_eq!(u64::MAX.checked_add(1),None);
    }
}


#[cfg(all(test,feature="fec2_product_record"))]
mod m0_fec2_full_mtu_repair_body_contract {
    use super::original_fec2_repair_symbol_fits;
    use wbd_codec::fec_v2::{
        parse_repair,BackendChoice,Profile,Rs16,RECORD_RESERVATION,REPAIR_HEADER,
    };
    #[test]
    fn m0_fec2_kind3_full_mtu_repair_budget_invariant(){
        // Outer 1500 / auth record budget for Fixed: one genuine near-TUN-MTU
        // source reaches maximum, and protected repair length adds 2B.
        let record_budget=1329usize;
        let frame=vec![0x6a;record_budget-RECORD_RESERVATION];
        let (encoded,_)=Rs16::new().encode_owned(
            1,&[frame.as_slice()],Profile::Maximum,0,1,
            record_budget,BackendChoice::Scalar,
        ).expect("actual codec encodes in-budget full-sized source");
        let rep=parse_repair(&encoded[0],record_budget).expect(
            "real codec accepts repair length exactly at record budget"
        );
        assert_eq!(encoded[0].len(),record_budget);
        assert_eq!(rep.body.len(),record_budget-REPAIR_HEADER);
        assert!(original_fec2_repair_symbol_fits(rep.body.len(),record_budget));
        // Source's fourteen-byte reservation cannot be charged again to
        // this already-encoded body. Still reject any truly oversized body.
        assert!(rep.body.len()>record_budget-RECORD_RESERVATION);
        assert!(!original_fec2_repair_symbol_fits(rep.body.len()+1,record_budget));
        assert!(!original_fec2_repair_symbol_fits(1,0));
    }
}
