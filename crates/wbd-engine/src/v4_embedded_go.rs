//! Opt-in, non-_test in-process Go→Rust V4 control adapter.
//! Linux x86_64/aarch64 GNU share the audited 64-bit raw/TUN ABI; ARM64 requires native OS CI.
//! This uses the ordinary ProtectedScopedOwner (real M1/M3 AEAD/PN).
//! It is NOT a standalone credential validator: only package-private Go
//! code after verified TLS credentials may call the feature-gated adapter.
//! Never distribute the feature-enabled shared library as a public installer.
//! Default production ABI features stay zero; M4 driver-held stop NOT_RUN.
#![allow(clippy::missing_safety_doc)]
use std::collections::{BTreeMap,VecDeque};
use std::sync::{Mutex,OnceLock,Arc,atomic::{AtomicBool,AtomicU64,Ordering}};
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
use std::thread::{self,JoinHandle};
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
use std::ffi::c_int;
use wbd_types::MonoNs;
use wbd_types::buffer_contract::{UniqueSealable,FrozenRecordHandle};
use crate::memory::Arena;
use crate::cold_v4::{UntrustedColdV4,COLD_V4_LEN};
use crate::v4_protected_handoff::{PrivateGoV4Handoff,HANDOFF_V1_LEN};
use crate::v4_owner_crypto::{ProtectedScopedOwner,NormalOffReceive};
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
use crate::v4_owner_crypto::ScopedLinuxBudget;
use wbd_codec::record_frame::FIXED_WIRE_OVERHEAD;
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
use wbd_codec::link_fec_wire::{LinkPacketPlan,LinkMode};
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
use wbd_platform::linux_raw_carrier::{ScopedRawIpv4Rx,ScopedRawIpv4Tx};
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
use wbd_platform::linux_tun_sink::{ScopedTunSink,TunReadyEntry,TunError};
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
use wbd_platform::ipv4_tcp::{Ipv4Tuple,PacketPersona,Presentation};
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
use std::os::fd::BorrowedFd;
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
use std::time::Instant;
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
use std::net::Ipv4Addr;
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
use wbd_platform::r1::StopResult;
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
use wbd_platform::rx_ipv4_tcp::extend_seq32;
use crate::runtime::early_rx::EarlyAccepted;
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
use crate::runtime::RxPacket;
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
use crate::runtime::TxDispatch;
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
use std::time::Duration;
const OK:i32=0;
const INVALID:i32=1;
const UNKNOWN:i32=2;
const BAD_STAGE:i32=3;
const FULL:i32=4;
const STOP_INCOMPLETE:i32=5;
const MAX_SESSIONS:usize=16;
const MAX_EARLY:u32=32;
const PH_PREPARED:u32=1;
const PH_ACTIVE:u32=2;
const PH_STOPPED:u32=3;
const PH_STOPPING:u32=4;
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
struct WorkerRouteBudget {
    scoped:ScopedLinuxBudget,
    observed_at:Instant,
    ifindex:u32,
    destination:Ipv4Addr,
    revision:u64,
    route_event_revision:u64,
}
// Test-only independent receiver for ACTUAL ciphertext observed from the
// kernel raw peer. It reuses M3's actual authenticated replay owner and RS16,
// never another sender/PN allocator. The Go test owns/compares the recovered
// bytes; this is NOT product client ingress or an M2 receipt.
#[cfg(feature="m0_fec2_owner_probe")]
struct Fec2ActualPeerRxProbe{
    opener:wbd_codec::record_replay::ReplayProtectedLaneRx,
    codec:wbd_codec::fec_v2::Rs16,
    block_id:Option<u64>,
    source0:Option<Vec<u8>>,
    finished:bool,
    // Original M2 bounded receive-side feedback, fed only after successful
    // original M3 AEAD/replay + legal FEC2 kind/body checks.
    feedback:wbd_recovery::RxFeedbackState,
    // Only original M3 AEAD-unique first accepted DATA/repair counts.
    // Not a mature loss denominator or fabricated network quality.
    first_sources:u64,
    first_repairs:u64,
    recovered_sources:u64,
}
#[cfg(feature="m0_fec2_owner_probe")]
impl Fec2ActualPeerRxProbe{
    fn consume(&mut self,mut wire:Vec<u8>,budget:usize)
        ->Result<(u64,u8,Vec<u8>),()>{
        // Do real replay/AEAD first even for a completed block, never
        // mistake application-completion status for a PN replay check.
        let decoded=self.opener.open_unique_with_fec2_after_admission_in_place(
            wire.as_mut_slice()
        ).map_err(|_|())?;
        if self.finished||decoded.pn>1{return Err(())}
        let result=match (decoded.pn,decoded.kind){
            (0,2)=>{
                let src=wbd_codec::fec_v2::parse_source(decoded.payload,budget)
                    .map_err(|_|())?;
                if src.block_id==0||src.source_index!=0||
                    self.block_id.is_some(){return Err(())}
                self.block_id=Some(src.block_id);
                self.source0=Some(src.frame.to_vec());
                Ok((decoded.pn,2,Vec::new()))
            }
            (1,3)=>{
                let repair=wbd_codec::fec_v2::parse_repair(decoded.payload,budget)
                    .map_err(|_|())?;
                if repair.block_id!=self.block_id.ok_or(())?||
                   repair.actual_k!=2||repair.parity_row!=0{
                    return Err(())
                }
                let first=self.source0.as_deref().ok_or(())?;
                let (recovered,_)=self.codec.recover_missing(
                    repair.block_id,&[Some(first),None],&[repair],budget,
                    wbd_codec::fec_v2::BackendChoice::Scalar
                ).map_err(|_|())?;
                if recovered.len()!=1||recovered[0].0!=1{return Err(())}
                self.finished=true;
                Ok((decoded.pn,3,recovered.into_iter().next().ok_or(())?.1))
            }
            _=>Err(()),
        };
        if let Ok((pn,kind,recovered))=&result {
            use wbd_recovery::FeedbackReceive;
            if self.feedback.on_authenticated_data(
                wbd_types::RecordPn(*pn),MonoNs(0)
            )!=FeedbackReceive::First {return Err(())}
            match kind {
                2=>self.first_sources=self.first_sources.saturating_add(1),
                3=>{
                    self.first_repairs=self.first_repairs.saturating_add(1);
                    if !recovered.is_empty(){
                        self.recovered_sources=self.recovered_sources.saturating_add(1);
                    }
                },
                _=>return Err(())
            }
        }
        result
    }
}
// M0 single original-session TEST-ONLY sender shadow. It holds the exact
// M1 frozen ciphertext cloned only after synchronous M4 raw kernel copy.
// Receipt admission relies on original M3 reverse AEAD/unique-PN opener.
#[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
struct Fec2ProbeReceiptSender{
    shadow:wbd_recovery::ReceiptState<crate::memory::FrozenRecord>,
    direction:wbd_recovery::BudgetDirection,
    route:wbd_recovery::ReceiptRouteScope,
    start_ns:u64,
    repair_submitted:bool,
    // Copied-first-send denominator from ORIGINAL M4, never RX counters.
    mature:wbd_recovery::MatureFirstSend,
    mature_2s:wbd_recovery::MatureWindow,
    mature_8s:wbd_recovery::MatureWindow,
    mature_invalid:bool,
}
// Exactly ONE opt-in M0 process owner budget shared by all original
// verified Go TLS sessions (not a per-connection "global" copy).
// Underlying M2 allocator is original M2 and owns all directions/debt.
// A single mutex is ONLY the M0 integration adapter; never hold it while
// a blocking raw kernel syscall is in progress.
#[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
struct Fec2ProbeProcessQuota{
    broker:wbd_recovery::GlobalRepairAllocator,
    now_ns:u64,
}
#[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
impl Fec2ProbeProcessQuota{
    fn at_least(&mut self,requested:u64)->MonoNs{
        self.now_ns=self.now_ns.max(requested);
        MonoNs(self.now_ns)
    }
}
#[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn fec2_probe_process_quota()->&'static Mutex<Fec2ProbeProcessQuota>{
    static QUOTA:OnceLock<Mutex<Fec2ProbeProcessQuota>>=OnceLock::new();
    QUOTA.get_or_init(||{
        use wbd_recovery::{GlobalRepairAllocator,GlobalRepairConfig};
        let broker=GlobalRepairAllocator::new(GlobalRepairConfig{
            max_bytes_per_epoch:65_536,max_directions:32,
            max_grant_bytes:32_768,max_grant_lifetime_ns:100_000_000,
            max_pending:32,max_pending_bytes:65_536,
        },MonoNs(0)).expect("private bounded owner config");
        Mutex::new(Fec2ProbeProcessQuota{broker,now_ns:0})
    })
}
// Sole real NORMAL/off sender-owned M2 maturity denominator. The
// original Rust TX loop is the ONLY event source: M4 definite copied
// prefix / one explicitly uncertain index / definitely-not-sent suffix.
// Without authenticated reverse kind1 the matured result is UNKNOWN,
// never zero loss or a fabricated receipt. All state is scoped to this
// Go TLS credential-bound lane+epoch and bounded by M2 capacity.
#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
struct NormalFirstSendM2 {
    lane:wbd_types::LaneKey,
    route:wbd_recovery::ReceiptRouteScope,
    reverse_direction:wbd_recovery::WireDirection,
    epoch:[u8;16],
    state:wbd_recovery::MatureFirstSend,
    accepted:u64,unknown_2s:u64,unknown_8s:u64,
    covered_2s:u64,covered_8s:u64,positive_2s:u64,
    // Bounded authenticated 2s cohort; reset on uncovered source.
    clean_2s:u64,clean_positive_2s:u64,
    authenticated_reverse_reports:u64,censored:bool,
}
#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
impl NormalFirstSendM2 {
    fn new(lane:wbd_types::LaneKey,epoch:[u8;16],server_side:bool,now:MonoNs)->Result<Self,i32>{
        use wbd_recovery::{ReceiptRouteScope,WireDirection,MaturityConfig,MatureFirstSend};
        let all=(wbd_types::RecordPn(0),wbd_types::RecordPn(u64::MAX));
        let (outbound,reverse_direction)=if server_side{
            (WireDirection::ServerToClient,WireDirection::ClientToServer)
        }else{
            (WireDirection::ClientToServer,WireDirection::ServerToClient)
        };
        let route=ReceiptRouteScope::checked(
            lane,lane,outbound,epoch,all,all
        ).map_err(|_|INVALID)?;
        // Fixed high-rate logical metadata ceiling; payload shadow is separate.
        let state=MatureFirstSend::new(route,MaturityConfig{max_live_data:131_072},now)
            .map_err(|_|INVALID)?;
        Ok(Self{lane,route,reverse_direction,epoch,state,accepted:0,unknown_2s:0,unknown_8s:0,
            covered_2s:0,covered_8s:0,positive_2s:0,
            clean_2s:0,clean_positive_2s:0,
            authenticated_reverse_reports:0,censored:false})
    }
    fn poll(&mut self,now:MonoNs){
        match self.state.on_due(now){
            Ok(result)=>{
                // Only actual M4 source first sends covered by original
                // reverse AEAD+PN can advance. Never erase old UNKNOWN.
                if result.window_2s.uncovered>0 || result.capacity_limited {
                    self.clean_2s=0;
                    self.clean_positive_2s=0;
                }else{
                    self.clean_2s=self.clean_2s.saturating_add(result.window_2s.covered());
                    self.clean_positive_2s=self.clean_positive_2s.saturating_add(
                        result.window_2s.unambiguous_positive);
                }
                self.unknown_2s=self.unknown_2s.saturating_add(
                    result.window_2s.uncovered);
                self.unknown_8s=self.unknown_8s.saturating_add(
                    result.window_8s.uncovered);
                self.covered_2s=self.covered_2s.saturating_add(
                    result.window_2s.covered());
                self.positive_2s=self.positive_2s.saturating_add(
                    result.window_2s.unambiguous_positive);
                self.covered_8s=self.covered_8s.saturating_add(
                    result.window_8s.covered());
                if result.capacity_limited{self.censored=true}
            }
            Err(_)=>self.censored=true,
        }
    }
    fn has_clean_fixed_m2(&self)->bool{
        self.authenticated_reverse_reports>0 && !self.censored &&
        self.clean_2s>0 && self.clean_positive_2s>0
    }
    // The only telemetry bridge from the SAME original moved server RX
    // (C2S original AEAD/PN) into M2. A real WBC4 kind1 receipt is parsed
    // ONLY by ProtectedBackgroundRx after authenticating ciphertext.
    // No synthetic ACK or alternate C2S decryptor may call this on wire.
    fn on_original_authenticated_reverse(
        &mut self,opened:crate::v4_owner_crypto::AuthenticatedNormalKind1,
        now:MonoNs
    )->Result<wbd_recovery::ScopedAuthenticatedReceipt,wbd_types::DataError>{
        use wbd_recovery::{ReceiptOpenFacts,ReceiptPage,ScopedAuthenticatedReceipt,WireDirection};
        let facts=ReceiptOpenFacts{
            verified_reverse_lane:self.lane,
            verified_reverse_direction:self.reverse_direction,
            verified_tunnel_epoch:self.epoch,
            control_record_pn:wbd_types::RecordPn(opened.reverse_record_pn),
        };
        let pages=opened.receipt.pages.into_iter().map(|page|ReceiptPage{
            base_pn:wbd_types::RecordPn(page.base_pn),bitmap:page.bitmap
        }).collect();
        let scoped=ScopedAuthenticatedReceipt::checked_after_open(
            self.route,facts,wbd_types::RecordPn(opened.receipt.largest_data_pn),
            opened.receipt.report_seq,pages)?;
        // M2 may reject time reversal/capacity without inventing coverage;
        // that case must censor auto observations, not roll back AEAD replay.
        if self.state.on_authenticated_receipt(&scoped,now).is_err(){
            self.censored=true;
            return Err(wbd_types::DataError::Stale)
        }
        self.authenticated_reverse_reports=self.authenticated_reverse_reports.saturating_add(1);
        Ok(scoped)
    }
    fn on_possible_recovery(&mut self,pn:wbd_types::RecordPn,
        result:wbd_recovery::RepairSendResult,now:MonoNs){
        if self.state.on_possible_recovery(self.lane,pn,result,now).is_err(){
            self.censored=true;
        }
    }
    fn on_real_kernel_turn(&mut self,records:&[(wbd_types::RecordPn,u64)],
        result:TxTurnCompletion,now:MonoNs){
        use wbd_recovery::{FirstSendKind,FirstSendOutcome};
        for (index,&(pn,outer_wire_bytes)) in records.iter().enumerate(){
            let outcome=if index < result.copied as usize {
                self.accepted=self.accepted.saturating_add(1);
                FirstSendOutcome::Accepted{pn,wire_bytes:outer_wire_bytes}
            }else if result.uncertain==1 && index==result.copied as usize {
                FirstSendOutcome::Uncertain{pn,wire_bytes:outer_wire_bytes}
            }else{
                FirstSendOutcome::DefinitelyNotSent{pn}
            };
            if self.state.on_first_send(self.lane,FirstSendKind::Data,outcome,now).is_err(){
                // A capacity/error interval is never a valid zero-loss sample.
                self.censored=true;
            }
        }
        self.poll(now);
    }
}
// Actual production V4 original-Go M2 outer retransmit. One shadow of
// immutable first-copied M1 frozen ciphertext per authenticated direction.
// No separate sealer, PN allocator, or Go V3 retransmit is reachable.
#[cfg(all(feature="fec2_product_record",target_os="linux",
    any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[repr(usize)]
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
enum OriginalRepairBlockReason{
    FreshGlobal=0,FreshShadow=1,Grant=2,Burst=3,Quota=4,
    Capacity=5,Stale=6,LocalOther=7,GlobalOther=8,Invariant=9,
}
const ORIGINAL_REPAIR_BLOCK_REASON_COUNT:usize=10;
fn original_repair_reserve_block_reason(
    err:wbd_recovery::GlobalRepairError
)->OriginalRepairBlockReason{
    use wbd_recovery::{BudgetError as B,GlobalRepairError as G};
    match err{
        G::Local(B::BurstPaced)=>OriginalRepairBlockReason::Burst,
        G::Local(B::QuotaExhausted)=>OriginalRepairBlockReason::Quota,
        G::Local(B::NoCapacity)|G::PendingCapacity|G::GlobalCap=>
            OriginalRepairBlockReason::Capacity,
        G::StaleCandidate|G::StaleGrant=>OriginalRepairBlockReason::Stale,
        G::Local(_)=>OriginalRepairBlockReason::LocalOther,
        _=>OriginalRepairBlockReason::GlobalOther,
    }
}
struct OriginalOuterRepair{
    shadow:wbd_recovery::ReceiptState<crate::memory::FrozenRecord>,
    direction:wbd_recovery::BudgetDirection,
    route:wbd_recovery::ReceiptRouteScope,
    sent_fresh:u64,
    authentic_ack:u64,
    repair_copied:u64,
    repair_uncertain:u64,
    repair_blocked:u64,
    block_reasons:[u64;ORIGINAL_REPAIR_BLOCK_REASON_COUNT],
    retired:u64,
}
impl OriginalOuterRepair{
    fn note_block(&mut self,reason:OriginalRepairBlockReason){
        self.repair_blocked=self.repair_blocked.saturating_add(1);
        let slot=&mut self.block_reasons[reason as usize];
        *slot=slot.saturating_add(1);
    }
}
#[cfg(all(feature="fec2_product_record",target_os="linux",
    any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn original_process_repair_quota()->&'static Mutex<wbd_recovery::GlobalRepairAllocator>{
    static BROKER:OnceLock<Mutex<wbd_recovery::GlobalRepairAllocator>>=OnceLock::new();
    BROKER.get_or_init(||{
        let cfg=wbd_recovery::GlobalRepairConfig{
            max_bytes_per_epoch:16*1024*1024,max_directions:32,
            max_grant_bytes:256*1024,max_grant_lifetime_ns:50_000_000,
            max_pending:256,max_pending_bytes:4*1024*1024,
        };
        Mutex::new(wbd_recovery::GlobalRepairAllocator::new(
            cfg,MonoNs(0)).expect("constant bounded global M2 repair config"))
    })
}
struct Entry{
    generation:u32,
    server_side:bool,
    owner:ProtectedScopedOwner,normal:Option<NormalOffReceive>,
    #[cfg(feature="m0_fec2_owner_probe")]
    protected_fec2_features:u16,
    #[cfg(feature="m0_fec2_owner_probe")]
    fec2_actual_peer_rx:Option<Fec2ActualPeerRxProbe>,
    #[cfg(all(feature="m0_fec2_owner_probe",feature="fec2_product_record",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    fec2_live_peer_rx:Option<crate::v4_fec2_live_rx::Fec2LiveRx>,
    // Developer-only separate original-Go TLS client TUN sink. Not a
    // product receive device or public capability grant.
    #[cfg(all(feature="m0_fec2_owner_probe",feature="fec2_product_record",
        target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    fec2_live_peer_tun:Option<Arc<ScopedTunSink>>,
    #[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    fec2_receipt_sender:Option<Fec2ProbeReceiptSender>,
    #[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    fec2_probe_budget_direction:Option<wbd_recovery::BudgetDirection>,
    #[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    fec2_probe_budget_start_ns:u64,
    #[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    fec2_probe_pending_policy:Option<(u8,u64)>,
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    tx_route:Option<WorkerRouteBudget>,
    // Original Go TLS-scoped verified interface used by every M4 RX/TX,
    // route, MTU and worker turn. Never accept a different device at Stop.
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    raw_ifname:Option<String>,
    #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    normal_firstsend_m2:Option<Arc<Mutex<NormalFirstSendM2>>>,
    // Authentic first-delivery feedback, generated by the original moved
    // M3 replay opener; the native TX owner seals on its own PN allocator.
    #[cfg(feature="fec2_product_record")]
    rx_feedback:Option<Arc<Mutex<wbd_recovery::RxFeedbackState>>>,
    #[cfg(feature="fec2_product_record")]
    original_public_feedback_armed:bool,
    #[cfg(feature="fec2_product_record")]
    feedback_queued:Option<(wbd_recovery::FeedbackDraft,u64)>,
    #[cfg(feature="fec2_product_record")]
    original_outer:Option<Arc<Mutex<OriginalOuterRepair>>>,
    #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    normal_off_applied_revision:u64,
    // Ordinary non-probe owner: only Go verified TLS feature7 may stage FEC2
    // Fixed. This is an intent, NEVER an applied claim before kernel FEC.
    #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    protected_features:u16,
    // One original credential-checked Go TLS GoLane snapshot. This remains
    // dormant until a complete original 2/4 lane set consumes it exactly
    // once into ONE native GameAdapter. Never hand caller raw key bytes.
    #[cfg(feature="fec2_product_record")]
    game_pending_cold:Option<UntrustedColdV4>,
    #[cfg(feature="fec2_product_record")]
    game_joined:bool,
    #[cfg(feature="fec2_product_record")]
    game_tx_boundary:u32,
    #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    fixed_pending:Option<(u8,u64)>,
    #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    fixed_applied:Option<(u8,u64)>,
    #[cfg(all(feature="fec2_product_record",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    fec2_live_tx:Option<crate::v4_fixed_stream::FixedStream>,
    // Actual pending driver loans, each tagged with its original same
    // M3 AEAD PN and source/repair kind. Reset only after synchronous M4.
    #[cfg(all(feature="fec2_product_record",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    fec2_staged_pns:Vec<(u64,u8)>,
    #[cfg(all(feature="fec2_product_record",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    fec2_copied_source:u64,
    #[cfg(all(feature="fec2_product_record",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    fec2_copied_repair:u64,
    // Fixed-size existing TX-owner diagnosis, no payload or hot tracing.
    // source: payload/arena/seal; parity: policy/arena/seal;
    // real M4 noncopy: parity/source. Read once before Stop.
    #[cfg(all(feature="fec2_product_record",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    fec2_fail_reasons:[u64;8],
    // Original Go's EXACT applied policy controls the background FEC
    // receiver, not a second untrusted mode bit or a guessed TLS epoch.
    #[cfg(all(feature="fec2_product_record",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    fec2_rx_admit:Arc<AtomicBool>,
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    tx_route_revision:u64,
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    raw_tx_lease_mtu:u32,
    // Generation/epoch-scoped, never wrap into an active fragment ID.
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    next_link_packet_id:u32,
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    workers:Option<LoopWorkers>,
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    joining:bool,
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    counters:Arc<LoopCounts>,
    arena:Arena,phase:u32,
    rx_boundary:u32,wire_limit:u16,staged_count:u32,staged_bytes:u32,
    // Extended only after this same-session AEAD+PN opener admits real data.
    // The fixed Go bootstrap boundary cannot serve as the seq32 anchor forever.
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    rx_seq_anchor:u64,
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    flow:crate::v4_protected_handoff::GoFlow,
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    raw_rx:Option<Arc<ScopedRawIpv4Rx>>,
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    raw_tx:Option<Arc<ScopedRawIpv4Tx>>,
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    tun_sink:Option<Arc<ScopedTunSink>>,
}
// Global registry only handles lifetime lookup. Once the original
// authenticated Go control starts perpetual workers, RX's actual AEAD+PN,
// LINK and M1 arena are MOVED to RX; this Entry guards TX/control only.
struct GameGroupNative{
    adapter:Arc<Mutex<crate::v4_game_lane::GameAdapter>>,
    handles:Vec<u64>,stopped:bool,stopping:bool,
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    server:bool,
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    flows:Vec<crate::v4_protected_handoff::GoFlow>,
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    tx_seqs:Vec<u64>,
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    drivers:Option<crate::v4_game_public_kernel::GameKernelOwner>,
}
// Dedicated group handles have different low tag from existing original
// committed per-lane Go owner. Both must be stopped/released together.
struct Registry{
    generation:u32,entries:BTreeMap<u64,Arc<Mutex<Entry>>>,
    #[cfg(feature="fec2_product_record")]
    game_groups:BTreeMap<u64,GameGroupNative>,
}
fn registry()->&'static Mutex<Registry>{
    static R:OnceLock<Mutex<Registry>>=OnceLock::new();
    R.get_or_init(||Mutex::new(Registry{
        generation:1,entries:BTreeMap::new(),
        #[cfg(feature="fec2_product_record")]
        game_groups:BTreeMap::new(),
    }))
}
fn session(handle:u64)->Result<Arc<Mutex<Entry>>,i32>{
    let r=registry().lock().map_err(|_|BAD_STAGE)?;
    r.entries.get(&handle).cloned().ok_or(UNKNOWN)
}
fn prepare(cold:&[u8],command:&[u8])->Result<u64,i32>{
    prepare_side(cold,command,true)
}
fn prepare_side(cold:&[u8],command:&[u8],server_side:bool)->Result<u64,i32>{
    let handoff=PrivateGoV4Handoff::decode(command).map_err(|_|INVALID)?;
    let data=UntrustedColdV4::parse(cold).map_err(|_|INVALID)?;
    if data.identity().server!=server_side{return Err(INVALID)}
    // Feature7 is permitted only in the genuine pinned original-Go V4 TLS
    // post-reply/Detach owner and only with compiled M3 source/repair record,
    // true client-side RX, and original M2 reverse feedback native integration.
    if !server_side && handoff.negotiated_features!=3 {
        #[cfg(feature="fec2_product_record")]
        if handoff.negotiated_features!=7{return Err(INVALID)}
        #[cfg(not(feature="fec2_product_record"))]
        {return Err(INVALID)}
    }
    let mut r=registry().lock().map_err(|_|BAD_STAGE)?;
    if r.entries.len()>=MAX_SESSIONS{return Err(FULL)}
    let generation=r.generation;
    r.generation=generation.checked_add(1).ok_or(FULL)?;
    let handle=(u64::from(generation)<<32)|0x5742;
    // Only in the opt-in trusted original Go TLS callback: create a
    // separate CLIENT receive replay bitmap using the original authenticated
    // Go server-to-client direction key. This is an independent PEER RX for
    // an actual kernel packet, not a new Rust TX owner or product pathway.
    #[cfg(feature="m0_fec2_owner_probe")]
    let fec2_actual_peer_rx=if handoff.negotiated_features==7{
        let (_,s2c)=data.internal_direction_keys();
        let suite=wbd_codec::record_crypto::RecordSuite::try_from(
            data.identity().cipher).map_err(|_|INVALID)?;
        let replay=wbd_codec::record_replay::ReplayWindowConfig{
            pn_per_second:1000,cache_horizon_ms:3000,
            fec_horizon_ms:1000,rtt_ms:500,metadata_budget_bytes:8192
        };
        let opener=wbd_codec::record_replay::ReplayProtectedLaneRx::new_for_suite(
            s2c,usize::from(data.identity().client_limit),suite,replay
        ).map_err(|_|INVALID)?;
        let feedback=wbd_recovery::RxFeedbackState::new(
            wbd_recovery::RxFeedbackConfig{
                max_retained_pages:8,max_pages_per_report:8,
                retention_ns:100_000_000,srtt_ns:8_000_000,
            }
        ).map_err(|_|INVALID)?;
        Some(Fec2ActualPeerRxProbe{
            opener,codec:wbd_codec::fec_v2::Rs16::new(),
            block_id:None,source0:None,finished:false,feedback,
            first_sources:0,first_repairs:0,recovered_sources:0
        })
    }else{None};
    #[cfg(all(feature="m0_fec2_owner_probe",feature="fec2_product_record",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    let fec2_live_peer_rx=if handoff.negotiated_features==7{
        let (_,s2c)=data.internal_direction_keys();
        let suite=wbd_codec::record_crypto::RecordSuite::try_from(
            data.identity().cipher).map_err(|_|INVALID)?;
        let rx=wbd_codec::record_replay::ReplayProtectedLaneRx::new_for_suite(
            s2c,usize::from(data.identity().client_limit),suite,
            wbd_codec::record_replay::ReplayWindowConfig{
                pn_per_second:20000,cache_horizon_ms:200,
                fec_horizon_ms:150,rtt_ms:100,metadata_budget_bytes:256*1024,
            }
        ).map_err(|_|INVALID)?;
        let exact=crate::v4_fec2_live_rx::VerifiedReceiveEpoch{
            generation,epoch:data.identity().logical_epoch,
            negotiated_features:handoff.negotiated_features,
            direction_s2c:true,
        };
        Some(crate::v4_fec2_live_rx::Fec2LiveRx::from_original_owner(
            exact,rx,usize::from(data.identity().client_limit))
            .map_err(|_|INVALID)?)
    }else{None};
    let owner=handoff.prepare_scoped_owner_for_side(
        &data,generation,handle,server_side
    ).map_err(|_|INVALID)?;
    let link_mtu=usize::from(if server_side {
        data.identity().server_limit
    }else{
        data.identity().client_limit
    })
        .checked_sub(FIXED_WIRE_OVERHEAD).ok_or(INVALID)?;
    let normal=NormalOffReceive::new_for_owner(&owner,link_mtu,link_mtu)
        .map_err(|_|INVALID)?;
    // The genuine FEC2 owner keeps one original M1 plaintext loan until
    // its short parity job retires PLUS a separate immutable ciphertext loan
    // in the <=2s M2 receipt/repair shadow. At ~100+ actual outer first
    // sends/s, 600ms RTT and partial feedback, the original 128-slot pool
    // starved BOTH fresh systematic and parity (S013 measured 5k/18k
    // NoCapacity failures per side with zero seal/driver failures).
    // In the real 2Mbps/408ms RTT Normal scenario the 128 shared M1 slabs
    // were exhausted (227/234 already-consumed TUN packets lost). The shadow
    // retains immutable M1 slab references until verified ACK or completion.
    // Original Normal/off at 10Mbps with RTT400ms ran out of 496 DATA
    // loans even after reserving 16 receipt slots: zero-netem A/B showed
    // >11k deferred reads per side and 819/936 TUN TX drops during steady.
    // RX unique-to-TUN and successful TX sealing conserve; this is a source
    // flight-capacity boundary, not lost encrypted packets or VM pressure.
    // At Normal/off TCP1 10Mbps/direction, 0% netem loss and RTT ~400ms,
    // actual M1 peak reached 1009/1024 with 16 feedback slots reserved;
    // source TUN kernel TX drops rose 132/359 and inner TCP retransmitted
    // 97/303 times (run39937279597). Enlarging the fixed small-slab backing
    // to 2048 (~4.5MiB charged per endpoint) restores spare source flight
    // capacity without allowing TUN reads before an owned slab exists.
    // This is not the 500Mbps lazy-payload-pool design.
    // FEC feature7 shares the constructor, so its passive cold backing also
    // grows; FEC data algorithms/configuration and tests are not changed.
    // Neither receipt expiry, retry quota, crypto nor Stop changes.
    #[cfg(all(feature="fec2_product_record",target_os="linux"))]
    let fec2_product_pool=handoff.negotiated_features==7;
    #[cfg(not(all(feature="fec2_product_record",target_os="linux")))]
    let fec2_product_pool=false;
    let public_normal_pool=cfg!(target_os="linux")
        && cfg!(feature="fec2_product_record");
    let (slots,bytes)=if fec2_product_pool || public_normal_pool {
        (2048,4_800_000)
    }else{(128,1_000_000)};
    let arena=Arena::new(generation,slots,2048,128,bytes)
        .map_err(|_|FULL)?;
    r.entries.insert(handle,Arc::new(Mutex::new(Entry{
        generation,server_side,owner,normal:Some(normal),arena,phase:PH_PREPARED,rx_boundary:handoff.rx_boundary,
        #[cfg(feature="m0_fec2_owner_probe")]
        protected_fec2_features:handoff.negotiated_features,
        #[cfg(feature="m0_fec2_owner_probe")]
        fec2_actual_peer_rx,
        #[cfg(all(feature="m0_fec2_owner_probe",feature="fec2_product_record",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        fec2_live_peer_rx,
        #[cfg(all(feature="m0_fec2_owner_probe",feature="fec2_product_record",
            target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        fec2_live_peer_tun:None,
        #[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        fec2_receipt_sender:None,
        #[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        fec2_probe_budget_direction:None,
        #[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        fec2_probe_budget_start_ns:0,
        #[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        fec2_probe_pending_policy:None,
        #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        rx_seq_anchor:u64::from(handoff.rx_boundary),
        wire_limit:if server_side{data.identity().server_limit}else{data.identity().client_limit},
        staged_count:0,staged_bytes:0,
        #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        flow:handoff.flow,
        #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        tx_route:None,
        #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        raw_ifname:None,
        #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        normal_firstsend_m2:None,
        #[cfg(feature="fec2_product_record")]
        rx_feedback:None,
        #[cfg(feature="fec2_product_record")]
        original_public_feedback_armed:false,
        #[cfg(feature="fec2_product_record")]
        feedback_queued:None,
        #[cfg(feature="fec2_product_record")]
        original_outer:None,
        #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        normal_off_applied_revision:0,
        #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        protected_features:handoff.negotiated_features,
        #[cfg(feature="fec2_product_record")]
        game_pending_cold:if handoff.negotiated_features==7{Some(data)}else{None},
        #[cfg(feature="fec2_product_record")]
        game_joined:false,
        #[cfg(feature="fec2_product_record")]
        game_tx_boundary:0,
        #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        fixed_pending:None,
        #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        fixed_applied:None,
        #[cfg(all(feature="fec2_product_record",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        fec2_live_tx:None,
        #[cfg(all(feature="fec2_product_record",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        fec2_staged_pns:Vec::new(),
        #[cfg(all(feature="fec2_product_record",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        fec2_copied_source:0,
        #[cfg(all(feature="fec2_product_record",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        fec2_copied_repair:0,
        #[cfg(all(feature="fec2_product_record",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        fec2_fail_reasons:[0;8],
        #[cfg(all(feature="fec2_product_record",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        fec2_rx_admit:Arc::new(AtomicBool::new(false)),
        #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        tx_route_revision:0,
        #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        raw_tx_lease_mtu:0,
        #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        next_link_packet_id:1,
        #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        workers:None,
        #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        joining:false,
        #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        counters:Arc::new(LoopCounts::default()),
        #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        raw_rx:None,
        #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        raw_tx:None,
        #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        tun_sink:None,
    })));
    Ok(handle)
}
fn stage(handle:u64,seq:u32,payload:&[u8])->i32{
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_PREPARED{return BAD_STAGE}
    let len=payload.len();
    let max=u32::from(e.wire_limit)*64;
    let delta=seq.wrapping_sub(e.rx_boundary);
    if len==0||len>usize::from(e.wire_limit)||e.staged_count>=MAX_EARLY
       ||e.staged_bytes.saturating_add(len as u32)>u32::from(e.wire_limit)*MAX_EARLY
       ||delta>=max||delta.saturating_add(len as u32)>max{return INVALID}
    let Ok(mut slab)=e.arena.allocate()else{return FULL};
    slab.writable()[..len].copy_from_slice(payload);
    let boundary=e.rx_boundary;
    match e.owner.offer_early(slab,0..len,u64::from(boundary)+u64::from(delta),MonoNs(0)){
        Ok(EarlyAccepted::Staged)=>{e.staged_count+=1;e.staged_bytes+=len as u32;OK}
        _=>INVALID
    }
}
fn commit(handle:u64,count:u32,bytes:u32,tx_boundary:u32)->i32{
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_PREPARED{return BAD_STAGE}
    if count!=e.staged_count||bytes!=e.staged_bytes||count>MAX_EARLY
       ||bytes>u32::from(e.wire_limit)*MAX_EARLY{return INVALID}
    // Only Go's private callback after protected reply and successful
    // DetachTransition knows the exact post-reply SenderNext boundary.
    if e.owner.commit_after_detach(tx_boundary).is_err(){return BAD_STAGE}
    #[cfg(feature="fec2_product_record")]
    {e.game_tx_boundary=tx_boundary;}
    e.phase=PH_ACTIVE;
    OK
}
// This probe binding is distinct from parsing untrusted WBGH/v2.
// It is called only from the original Go package's credential-checked
// private callback, after actual protected reply, Detach and Rust Commit.
// It is NOT compiled into default production (no public feature enable).
// Restricted, one-shot live M4 raw-kernel SEND probe for the same Go TLS
// authorized generation. It does NOT establish a production FEC2 data
// loop, receive repair, or deliver to a real TUN app.
// First completely materialize M3 source/repair in two original M1 slabs;
// use the SAME ProtectedScopedOwner / AEAD / PN / Seq / FrozenRecord,
// SAME M4 ScopedRawIpv4Tx, and definite synchronous kernel send result.
// Valid IPv4 UDP (127B total, 99B app), not a fake arbitrary RS symbol.
// The Go kernel app independently checks the UDP delivery and payload.
// Underlying original FEC2 parity geometry remains k2, e1.
#[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn fec2_probe_expected_udp_ipv4()->Vec<u8>{
    let mut b=vec![0u8;127];
    b[0]=0x45;b[8]=64;b[9]=17;
    b[2..4].copy_from_slice(&127u16.to_be_bytes());
    b[4..6].copy_from_slice(&9102u16.to_be_bytes());
    b[12..16].copy_from_slice(&[10,241,20,2]);
    b[16..20].copy_from_slice(&[10,241,20,1]);
    b[20..22].copy_from_slice(&42001u16.to_be_bytes());
    b[22..24].copy_from_slice(&49231u16.to_be_bytes());
    b[24..26].copy_from_slice(&107u16.to_be_bytes());
    for (i,v) in b[28..].iter_mut().enumerate(){
        *v=((i*7+5)%251) as u8
    }
    let mut sum=0u32;
    for pair in b[..20].chunks_exact(2){
        sum+=u32::from(u16::from_be_bytes([pair[0],pair[1]]));
    }
    while sum>0xffff{sum=(sum&0xffff)+(sum>>16)}
    b[10..12].copy_from_slice(&(!(sum as u16)).to_be_bytes());
    b
}
#[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn fec2_probe_real_kernel_raw_once(
    handle:u64,ifindex:u32
)->Result<[(u64,u32,usize);2],i32>{
    use crate::v4_fixed_stream::{FixedStream,DriverProof};
    use crate::runtime::fec2_owner::SourceTicket;
    use wbd_types::ConfigRevision;
    let cell=session(handle)?;
    let mut guard=cell.lock().map_err(|_|BAD_STAGE)?;
    let e:&mut Entry=&mut guard;
    if e.phase!=PH_ACTIVE || e.workers.is_some()
        ||e.protected_fec2_features!=7
        ||!e.owner.is_fec2_probe_bound()
        ||e.fec2_receipt_sender.is_some(){
        return Err(BAD_STAGE)
    }
    // Actual OFF means no new M1 source/parity or M3 PN can be sealed.
    // A newer requested enable may only become applied after M4 copies a
    // new authenticated block; a stale OFF status cannot send anything.
    if e.owner.fec2_probe_applied_policy().is_some_and(|(p,_)|p==7)
        && e.fec2_probe_pending_policy.is_none()
        && e.fixed_pending.is_none(){return Err(BAD_STAGE)}
    if e.raw_tx.is_none(){
        let raw=ScopedRawIpv4Tx::open("lo",ifindex,e.generation)
            .map_err(|_|INVALID)?;
        e.raw_tx=Some(Arc::new(raw));
    }
    let route=e.owner.observe_linux_normal_off_route_budget(
        "lo",ifindex,Ipv4Addr::from(e.flow.client_ip)
    ).map_err(|_|INVALID)?;
    let budget=route.frame;
    let flow=e.flow;
    let tuple=Ipv4Tuple{
        src_ip:&flow.server_ip,dst_ip:&flow.client_ip,
        src_port:flow.server_port,dst_port:flow.client_port,
    };
    let presentation=Presentation{
        ack32:1,advertised_window:4096,ip_id:43,
        persona:PacketPersona::Legacy,
    };
    let raw=Arc::clone(e.raw_tx.as_ref().ok_or(BAD_STAGE)?);
    let a=(0..113).map(|n|(n%251) as u8).collect::<Vec<_>>();
    let b=fec2_probe_expected_udp_ipv4();
    // Source policy actually chosen by the ORIGINAL Go FecV2Step and
    // bound after its authenticated TLS/Detach commit. No cold/peer
    // unauthenticated value can supply this setting. This is still only
    // the feature-gated one-shot probe, NOT a product continuous scheduler.
    let (policy,revision)=e.fixed_pending
        .or(e.fec2_probe_pending_policy)
        .or_else(||e.owner.fec2_probe_applied_policy())
        .ok_or(BAD_STAGE)?;
    // M0's already Actions-frozen bounded multi-block owner composition,
    // reused by this SAME original Go TLS->Rust owner and M4 raw kernel.
    // The probe requests only one k2 source pair (real multi-block kernel
    // delivery still separately unqualified).
    let mut stream=FixedStream::new(
        policy,revision,budget.record_payload_mtu
    ).ok_or(INVALID)?;
    let mut storage=Vec::with_capacity(1);
    let mut out=[(0u64,0u32,0usize);2];
    let mut tickets:[Option<SourceTicket>;2]=[None,None];
    let mut confirmed:Vec<(crate::memory::FrozenRecord,usize)>=Vec::with_capacity(2);
    for (i,frame) in [&a[..],&b[..]].into_iter().enumerate(){
        let mut source_slab=e.arena.allocate().map_err(|_|FULL)?;
        let end=14usize.checked_add(frame.len()).ok_or(INVALID)?;
        if end>source_slab.writable().len(){return Err(INVALID)}
        source_slab.writable()[14..end].copy_from_slice(frame);
        let mut callback_error=None;
        let accepted=stream.offer_source(
            source_slab,14..end,MonoNs((i as u64)*1_000),
            |ticket,first_frame|{
                if ticket.index!=i as u8 ||
                    ticket.revision!=ConfigRevision(revision) ||
                    first_frame!=frame{
                    callback_error=Some(INVALID);return false
                }
                tickets[i]=Some(ticket);
                // Inject ONE known lost source at the network boundary:
                // source1 was accepted and retained by M1, but not sent.
                // It MUST count as not-enqueued, never as a driver ACK.
                if i==1{return false}
                let sent=(||->Result<(u64,u32,usize),i32>{
                    let payload=wbd_codec::fec_v2::source_owned(
                        ticket.block_id,ticket.index,first_frame,
                        budget.record_payload_mtu
                    ).map_err(|_|INVALID)?;
                    let mut slab=e.arena.allocate().map_err(|_|FULL)?;
                    let last=14usize.checked_add(payload.len()).ok_or(INVALID)?;
                    if last>slab.writable().len(){return Err(INVALID)}
                    slab.writable()[14..last].copy_from_slice(&payload);
                    let sealed=e.owner.seal_fec2_probe_one(
                        slab,payload.len(),2,budget,15,loop_now()
                    ).map_err(|_|INVALID)?;
                    let (copied,frozen)=e.owner.submit_scoped_raw_tx_shadow_probe_reusing(
                        &raw,tuple,presentation,loop_now(),&mut storage
                    ).map_err(|_|INVALID)?;
                    if copied<=sealed.2||frozen.metadata().pn.0!=sealed.0 {
                        return Err(INVALID)
                    }
                    confirmed.push((frozen,copied));
                    Ok(sealed)
                })();
                match sent{
                    Ok(sealed)=>{out[0]=sealed;true},
                    Err(err)=>{callback_error=Some(err);false},
                }
            },
        ).map_err(|_|INVALID)?;
        if let Some(err)=callback_error{return Err(err)}
        if !accepted.fec_retained||accepted.ticket!=tickets[i]
            ||accepted.source_enqueued!=(i==0){
            return Err(INVALID)
        }
    }
    let first=tickets[0].ok_or(INVALID)?;
    let missing=tickets[1].ok_or(INVALID)?;
    if first.block_id!=missing.block_id ||first.index!=0||missing.index!=1{
        return Err(INVALID)
    }
    // Original bounded M1 scheduler closes the sparse k2 block at its
    // due deadline. M3's prepared RS16 quantum is shared with the true
    // multi-block production-composition interface. For this *one-shot*
    // proof only row0 is sent; any other profile-planned rows are strictly
    // NOT_SENT, not a fabricated kernel copy or recovered peer delivery.
    let mut parity_error=None;
    let (emitted,confirmed_rows)=stream.poll_parity(
        MonoNs(8_000_001),|parity,block_id,row,actual_revision|{
            if block_id!=first.block_id ||
                actual_revision!=ConfigRevision(revision){
                parity_error=Some(INVALID);
                return DriverProof::NotSent
            }
            if row!=0{return DriverProof::NotSent}
            let attempt=(||->Result<(u64,u32,usize),i32>{
                let mut repair_slab=e.arena.allocate().map_err(|_|FULL)?;
                let end=14usize.checked_add(parity.len()).ok_or(INVALID)?;
                if end>repair_slab.writable().len(){return Err(INVALID)}
                repair_slab.writable()[14..end].copy_from_slice(parity);
                let sealed=e.owner.seal_fec2_probe_one(
                    repair_slab,parity.len(),3,budget,15,loop_now()
                ).map_err(|_|INVALID)?;
                let (copied,frozen)=e.owner.submit_scoped_raw_tx_shadow_probe_reusing(
                    &raw,tuple,presentation,loop_now(),&mut storage
                ).map_err(|_|INVALID)?;
                if copied<=sealed.2||frozen.metadata().pn.0!=sealed.0{
                    return Err(INVALID)
                }
                confirmed.push((frozen,copied));
                Ok(sealed)
            })();
            match attempt{
                Ok(sealed)=>{out[1]=sealed;DriverProof::Copied},
                Err(err)=>{parity_error=Some(err);DriverProof::NotSent},
            }
        }
    ).map_err(|_|INVALID)?;
    if let Some(err)=parity_error{return Err(err)}
    if emitted==0||confirmed_rows!=1{return Err(INVALID)}
    let report=stream.report();
    if report.outstanding_jobs!=0||report.queued_jobs!=0
        ||report.charged_bytes!=0||report.classes[0].r_sent!=1
        ||report.classes[0].source_not_ready!=1{
        return Err(INVALID)
    }
    stream.stop();
    if stream.poll_parity(MonoNs(8_000_002),|_,_,_,_|DriverProof::Copied).is_ok(){
        return Err(INVALID)
    }
    if confirmed.len()!=2{return Err(INVALID)}
    // Only now has the actual original M1 block formed with the chosen
    // profile and the original M4 kernel positively copied its immutable
    // source+repair. Before this point Go requested != Rust applied.
    if let Some((p,r))=e.fixed_pending {
        let (_,exact_epoch)=e.owner.receipt_probe_identity().ok_or(BAD_STAGE)?;
        e.owner.apply_fec2_probe_new_block_policy(exact_epoch,p,r)
            .map_err(|_|BAD_STAGE)?;
        e.fixed_pending=None;
        e.fixed_applied=Some((p,r)); // confirmed source+repair raw kernel copy
        #[cfg(feature="fec2_product_record")]
        e.fec2_rx_admit.store(true,Ordering::Release);
    }else if let Some((p,r))=e.fec2_probe_pending_policy {
        let (_,exact_epoch)=e.owner.receipt_probe_identity().ok_or(BAD_STAGE)?;
        e.owner.apply_fec2_probe_new_block_policy(exact_epoch,p,r)
            .map_err(|_|BAD_STAGE)?;
        e.fec2_probe_pending_policy=None;
    }
    let (lane,epoch)=e.owner.receipt_probe_identity().ok_or(BAD_STAGE)?;
    use wbd_recovery::{
        BudgetDirection,WireDirection,ReceiptState,ReceiptConfig,
        ReceiptRouteScope,
    };
    let direction=BudgetDirection{
        tunnel:lane.tunnel,direction:WireDirection::ServerToClient
    };
    let route=ReceiptRouteScope::checked(
        lane,lane,WireDirection::ServerToClient,epoch,
        (wbd_types::RecordPn(out[0].0),wbd_types::RecordPn(out[1].0)),
        (wbd_types::RecordPn(0),wbd_types::RecordPn(10))
    ).map_err(|_|INVALID)?;
    let mut shadow=ReceiptState::new(lane,ReceiptConfig{
        max_shadow_entries:4,pto_ns:30_000_000,reorder_window_ns:2_000_000
    }).map_err(|_|INVALID)?;
    if e.fec2_probe_budget_direction!=Some(direction){
        return Err(BAD_STAGE)
    }
    let mut process=fec2_probe_process_quota().lock().map_err(|_|BAD_STAGE)?;
    let start=process.at_least(e.fec2_probe_budget_start_ns);
    process.broker.bind_receipt_route(direction,route,start)
        .map_err(|_|INVALID)?;
    use wbd_recovery::{MatureFirstSend,MaturityConfig,FirstSendKind,FirstSendOutcome};
    let mut mature=MatureFirstSend::new(
        route,MaturityConfig{max_live_data:4096},start
    ).map_err(|_|INVALID)?;
    for (frozen,outer_bytes) in confirmed {
        // This is the FINAL synchronous original M4 kernel copied prefix:
        // firstsent is never estimated from RX, repair or allocation.
        mature.on_first_send(lane,FirstSendKind::Data,
            FirstSendOutcome::Accepted{
                pn:frozen.metadata().pn,wire_bytes:outer_bytes as u64
            },start).map_err(|_|INVALID)?;
        shadow.on_sent(frozen,start,MonoNs(start.0.saturating_add(150_000_000)))
            .map_err(|_|INVALID)?;
        process.broker.on_fresh_accepted(direction,outer_bytes as u64,start)
            .map_err(|_|INVALID)?;
    }
    if shadow.outstanding()!=2{return Err(INVALID)}
    e.fec2_receipt_sender=Some(Fec2ProbeReceiptSender{
        shadow,direction,route,start_ns:start.0,repair_submitted:false,
        mature,mature_2s:wbd_recovery::MatureWindow::default(),
        mature_8s:wbd_recovery::MatureWindow::default(),mature_invalid:false
    });
    e.arena.drain_returns();
    Ok(out)
}
// Real release-code client FEC2 ingress owner: the ONLY Go caller is the
// verified V4ClientSession ColdSnapshot after original TLS feature7.
// Not reachable from the default engine ABI or the ordinary feature3 Go
// build. Go must still supply a real raw/TCP checked ingress and authenticated
// M2 acknowledgment before this can become a product feature.
#[cfg(all(feature="fec2_product_record",target_os="linux",
    any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
struct ReleaseClientRx {
    epoch:[u8;16],generation:u32,
    rx:crate::v4_fec2_live_rx::Fec2LiveRx,
    tun:ScopedTunSink,
    // C2S feedback comes only from AEAD-unique S2C DATA, never raw
    // metadata, and never grants remote APPLIED until actual kernel copy.
    feedback:wbd_recovery::RxFeedbackState,
    feedback_tx:wbd_codec::record_crypto::LaneTxCrypto,
    feedback_pending:Option<(wbd_recovery::FeedbackDraft,u64)>,
    delivered:u64,
}
#[cfg(all(feature="fec2_product_record",target_os="linux",
    any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
struct ReleaseClientRegistry {
    next:u32,clients:BTreeMap<u64,ReleaseClientRx>,
}
#[cfg(all(feature="fec2_product_record",target_os="linux",
    any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn release_clients()->&'static Mutex<ReleaseClientRegistry>{
    static REG:OnceLock<Mutex<ReleaseClientRegistry>>=OnceLock::new();
    REG.get_or_init(||Mutex::new(ReleaseClientRegistry{
        next:1,clients:BTreeMap::new(),
    }))
}
#[cfg(all(feature="fec2_product_record",target_os="linux",
    any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_release_client_fec2_prepare(
    cold:*const u8,cold_len:usize,fd:i32,
    name:*const u8,name_len:usize,out:*mut u64
)->i32{
    if cold.is_null()||cold_len!=COLD_V4_LEN||
       fd<3||name.is_null()||name_len==0||name_len>15||
       out.is_null(){return INVALID}
    let Ok(name)=std::str::from_utf8(unsafe{
        std::slice::from_raw_parts(name,name_len)
    })else{return INVALID};
    let Ok(cold)=UntrustedColdV4::parse(unsafe{
        std::slice::from_raw_parts(cold,cold_len)
    })else{return INVALID};
    let id=cold.identity();
    if id.server||id.logical_epoch==[0;16]{return INVALID}
    let Ok(suite)=wbd_codec::record_crypto::RecordSuite::try_from(id.cipher)
        else{return INVALID};
    let (send,recv)=cold.internal_direction_keys();
    let feedback=match wbd_recovery::RxFeedbackState::new(
        wbd_recovery::RxFeedbackConfig{
            max_retained_pages:8,max_pages_per_report:8,
            retention_ns:100_000_000,srtt_ns:8_000_000,
        }){Ok(f)=>f,Err(_)=>return INVALID};
    let feedback_tx=match wbd_codec::record_crypto::LaneTxCrypto::new_for_suite(
        send,usize::from(id.server_limit),suite,
    ){Ok(tx)=>tx,Err(_)=>return INVALID};
    let mut r=match release_clients().lock(){Ok(v)=>v,Err(_)=>return BAD_STAGE};
    if r.clients.len()>=MAX_SESSIONS||r.next==u32::MAX{return FULL}
    let generation=r.next;r.next+=1;
    let Some(handle)=(u64::from(generation)<<32).checked_add(0x434Cu64)
        else{return FULL};
    let exact=crate::v4_fec2_live_rx::VerifiedReceiveEpoch{
        generation,epoch:id.logical_epoch,negotiated_features:7,
        direction_s2c:true,
    };
    let wire_max=usize::from(id.client_limit);
    let opener=match wbd_codec::record_replay::ReplayProtectedLaneRx::new_for_suite(
        recv,wire_max,suite,wbd_codec::record_replay::ReplayWindowConfig{
            pn_per_second:20000,cache_horizon_ms:200,fec_horizon_ms:150,
            rtt_ms:100,metadata_budget_bytes:256*1024,
        }){Ok(rx)=>rx,Err(_)=>return INVALID};
    let rx=match crate::v4_fec2_live_rx::Fec2LiveRx::from_original_owner(
        exact,opener,wire_max){Ok(rx)=>rx,Err(_)=>return INVALID};
    let Ok(dup)=unsafe{BorrowedFd::borrow_raw(fd)}.try_clone_to_owned()
        else{return INVALID};
    let Ok(tun)=ScopedTunSink::from_owned_fd(dup,generation,name)
        else{return INVALID};
    r.clients.insert(handle,ReleaseClientRx{
        epoch:id.logical_epoch,generation,rx,tun,
        feedback,feedback_tx,feedback_pending:None,delivered:0,
    });
    unsafe{out.write(handle)};
    OK
}
#[cfg(all(feature="fec2_product_record",target_os="linux",
    any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_release_client_fec2_receive(
    handle:u64,epoch:*const u8,epoch_len:usize,
    record:*const u8,record_len:usize,
    delivered:*mut u32,recovered:*mut u32
)->i32{
    if handle==0||epoch.is_null()||epoch_len!=16||
        record.is_null()||record_len<31||record_len>2048||
        delivered.is_null()||recovered.is_null(){return INVALID}
    let epoch=unsafe{std::slice::from_raw_parts(epoch,16)};
    let record=unsafe{std::slice::from_raw_parts(record,record_len)};
    let Ok(mut r)=release_clients().lock()else{return BAD_STAGE};
    let Some(client)=r.clients.get_mut(&handle)else{return UNKNOWN};
    if epoch!=client.epoch||client.tun.is_stopping(){return BAD_STAGE}
    let exact=crate::v4_fec2_live_rx::VerifiedReceiveEpoch{
        generation:client.generation,epoch:client.epoch,
        negotiated_features:7,direction_s2c:true,
    };
    // Keep the original M3 replay bitmap local to this authenticated
    // generation. AEAD/replay rejects raw, duplicate and tampered frames.
    let mut input=record.to_vec();
    let now=loop_now();
    let Ok((authenticated_pn,packets))=client.rx.consume_with_pn(
        exact,&mut input,now)else{return INVALID};
    // Data with authentic AEAD/PN is an M2 received packet even if its
    // FEC repair row yields no new client IPv4. No ACK-of-ACK is possible.
    use wbd_types::RecordPn;
    client.feedback.on_authenticated_data(RecordPn(authenticated_pn),now);
    let mut n=0u32;let mut recovered_n=0u32;
    for packet in packets{
        if client.tun.write_authenticated_ipv4(client.generation,&packet.frame)
            .ok()!=Some(packet.frame.len()){return INVALID}
        n=n.saturating_add(1);
        if packet.recovered{recovered_n=recovered_n.saturating_add(1)}
    }
    client.delivered=client.delivered.saturating_add(u64::from(n));
    unsafe{delivered.write(n);recovered.write(recovered_n)}
    OK
}
// Prepare at most one original-M2 C2S AEAD control record when the
// bounded feedback scheduler says due. The result is ONLY ciphertext:
// Go's real kernel sender must report copied/unsent/uncertain separately.
#[cfg(all(feature="fec2_product_record",target_os="linux",
    any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_release_client_fec2_feedback_due(
    handle:u64,epoch:*const u8,epoch_len:usize,
    out:*mut u8,capacity:usize,used:*mut usize,record_pn:*mut u64
)->i32{
    if handle==0||epoch.is_null()||epoch_len!=16||out.is_null()||
       capacity<512||capacity>2048||used.is_null()||record_pn.is_null(){
        return INVALID
    }
    let scope=unsafe{std::slice::from_raw_parts(epoch,16)};
    let Ok(mut r)=release_clients().lock()else{return BAD_STAGE};
    let Some(client)=r.clients.get_mut(&handle)else{return UNKNOWN};
    if scope!=client.epoch||client.tun.is_stopping()||
        client.feedback_pending.is_some(){return BAD_STAGE}
    let now=loop_now();
    let Some(draft)=client.feedback.on_due(now)else{
        unsafe{used.write(0);record_pn.write(0)};
        return OK
    };
    let msg=wbd_codec::Receipt{
        largest_data_pn:draft.largest_data_pn().0,
        ack_delay_us:0,
        report_seq:draft.report_seq(),
        pages:draft.pages().iter().map(|p|wbd_codec::ReceiptPage{
            base_pn:p.base_pn.0,bitmap:p.bitmap,
        }).collect(),
    };
    let bytes=match wbd_codec::encode_control(
        &[wbd_codec::ControlTlv::Receipt(msg)],512
    ){
        Ok(b)=>b,Err(_)=>{
            let _=client.feedback.on_send_result(&draft,
                wbd_recovery::FeedbackSendResult::NotSent,now);
            return INVALID
        }
    };
    if bytes.len()+31>capacity{
        let _=client.feedback.on_send_result(&draft,
            wbd_recovery::FeedbackSendResult::NotSent,now);
        return FULL
    }
    let mut wire=vec![0u8;capacity];
    wire[14..14+bytes.len()].copy_from_slice(&bytes);
    let (pn,n)=match client.feedback_tx.seal_in_place(
        wbd_codec::record_frame::AUTHENTICATED_HEALTH_KIND,
        &mut wire,bytes.len(),0
    ){
        Ok(a)=>a,Err(_)=>{
            let _=client.feedback.on_send_result(&draft,
                wbd_recovery::FeedbackSendResult::NotSent,now);
            return INVALID
        }
    };
    unsafe{
        std::ptr::copy_nonoverlapping(wire.as_ptr(),out,n);
        used.write(n);record_pn.write(pn);
    }
    client.feedback_pending=Some((draft,pn));
    OK
}
#[cfg(all(feature="fec2_product_record",target_os="linux",
    any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_release_client_fec2_feedback_result(
    handle:u64,epoch:*const u8,epoch_len:usize,pn:u64,outcome:u32
)->i32{
    if handle==0||epoch.is_null()||epoch_len!=16||outcome>2{return INVALID}
    let scope=unsafe{std::slice::from_raw_parts(epoch,16)};
    let Ok(mut r)=release_clients().lock()else{return BAD_STAGE};
    let Some(client)=r.clients.get_mut(&handle)else{return UNKNOWN};
    if client.epoch!=scope||client.tun.is_stopping(){return BAD_STAGE}
    let Some((draft,expected))=client.feedback_pending.as_ref()
        else{return BAD_STAGE};
    if *expected!=pn{return BAD_STAGE}
    let res=match outcome{
        1=>wbd_recovery::FeedbackSendResult::Accepted,
        2=>wbd_recovery::FeedbackSendResult::Uncertain,
        _=>wbd_recovery::FeedbackSendResult::NotSent
    };
    if client.feedback.on_send_result(draft,res,loop_now()).is_err(){
        return BAD_STAGE
    }
    client.feedback_pending=None;
    OK
}

#[cfg(all(feature="fec2_product_record",target_os="linux",
    any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_release_client_fec2_stop(
    handle:u64,epoch:*const u8,epoch_len:usize
)->i32{
    if handle==0||epoch.is_null()||epoch_len!=16{return INVALID}
    let bytes=unsafe{std::slice::from_raw_parts(epoch,16)};
    let Ok(mut r)=release_clients().lock()else{return BAD_STAGE};
    let Some(client)=r.clients.get_mut(&handle)else{return UNKNOWN};
    if bytes!=client.epoch{return BAD_STAGE}
    client.tun.begin_stop();
    if client.tun.stop_until(Instant::now())!=StopResult::Drained{
        return STOP_INCOMPLETE
    }
    client.rx.stop();
    r.clients.remove(&handle);
    OK
}

// The independent authenticated client test owns a separate real Linux
// IFF_TUN+NO_PI descriptor, moved to original M4 ScopedTunSink semantics.
// Opt-in BOTH developer and release-code features, never public product.
#[cfg(all(feature="m0_fec2_owner_probe",feature="fec2_product_record",
    target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_fec2_probe_live_peer_attach_tun(
    h:u64,fd:i32,name:*const u8,name_len:usize
)->i32{
    if fd<3||name.is_null()||name_len==0||name_len>15{return INVALID}
    let Ok(label)=std::str::from_utf8(unsafe{
        std::slice::from_raw_parts(name,name_len)
    })else{return INVALID};
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.protected_features!=7||
        e.fec2_live_peer_rx.is_none()||e.fec2_live_peer_tun.is_some(){
        return BAD_STAGE
    }
    let Ok(dup)=unsafe{BorrowedFd::borrow_raw(fd)}.try_clone_to_owned()
        else{return INVALID};
    let Ok(tun)=ScopedTunSink::from_owned_fd(dup,e.generation,label)
        else{return INVALID};
    e.fec2_live_peer_tun=Some(Arc::new(tun));
    OK
}
// Developer ONLY: independent verified-original-Go TLS CLIENT FEC receiver
// consumes ciphertext captured from actual M4 Linux raw socket. It is NOT
// a product client, TUN applied ACK, nor a second server replay bitmap.
#[cfg(all(feature="m0_fec2_owner_probe",feature="fec2_product_record",
    target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_fec2_probe_live_peer_consume(
    handle:u64,wire:*const u8,wire_len:usize,
    count:*mut u32,block:*mut u64,index:*mut u8,
    recovered:*mut u32,original:*mut u8,capacity:usize,
    used:*mut usize
)->i32{
    if wire.is_null()||wire_len<31||wire_len>2048||count.is_null()||
        block.is_null()||index.is_null()||recovered.is_null()||
        original.is_null()||used.is_null()||capacity<2048{return INVALID}
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.protected_features!=7{return BAD_STAGE}
    let exact=crate::v4_fec2_live_rx::VerifiedReceiveEpoch{
        generation:e.generation,
        epoch:match e.owner.normal_firstsend_identity(){
            Some((_,epoch))=>epoch,None=>return BAD_STAGE,
        },negotiated_features:7,direction_s2c:true,
    };
    // Require the real OS device BEFORE spending an authenticated PN.
    let Some(tun)=e.fec2_live_peer_tun.as_ref().cloned()else{return BAD_STAGE};
    let generation=e.generation;
    let Some(client)=e.fec2_live_peer_rx.as_mut()else{return BAD_STAGE};
    let mut ciphertext=unsafe{std::slice::from_raw_parts(wire,wire_len)}.to_vec();
    let Ok(candidates)=client.consume(exact,&mut ciphertext,loop_now())
    else{return INVALID};
    if candidates.len()>1{return FULL}
    unsafe{count.write(candidates.len() as u32);used.write(0)}
    if let Some(first)=candidates.into_iter().next(){
        if first.frame.len()>capacity{return FULL}
        // The same scoped Rust kernel sink validates complete IPv4,
        // real synchronous bytes copied, no count on failure.
        if tun.write_authenticated_ipv4(generation,&first.frame)
            .ok()!=Some(first.frame.len()){return INVALID}
        unsafe{
            block.write(first.block_id);
            index.write(first.index);
            recovered.write(u32::from(first.recovered));
            std::ptr::copy_nonoverlapping(
                first.frame.as_ptr(),original,first.frame.len());
            used.write(first.frame.len());
        }
    }
    OK
}
#[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_fec2_probe_real_raw_tx(
    handle:u64,ifindex:u32,source_pn:*mut u64,repair_pn:*mut u64,
    source_seq:*mut u32,repair_seq:*mut u32,
    source_len:*mut u32,repair_len:*mut u32
)->i32{
    if source_pn.is_null()||repair_pn.is_null()||
       source_seq.is_null()||repair_seq.is_null()||
       source_len.is_null()||repair_len.is_null(){return INVALID}
    let Ok(sent)=fec2_probe_real_kernel_raw_once(handle,ifindex)
    else{return BAD_STAGE};
    let Ok(slen)=u32::try_from(sent[0].2)else{return INVALID};
    let Ok(rlen)=u32::try_from(sent[1].2)else{return INVALID};
    unsafe{
        source_pn.write(sent[0].0);repair_pn.write(sent[1].0);
        source_seq.write(sent[0].1);repair_seq.write(sent[1].1);
        source_len.write(slen);repair_len.write(rlen);
    }
    OK
}

// Authenticate ciphertext captured by the INDEPENDENT original Go raw
// kernel peer with the original Rust M3 AEAD+PN replay receiver and decode
// exactly the missing original source1 using M3 RS16 (not a fixture result).
// No FEC2 data is admitted before live owner grant or after Stop.
#[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn fec2_peer_received_actual_cipher(
    handle:u64,wire:&[u8],out:&mut [u8]
)->Result<(u64,u8,usize),i32>{
    if wire.is_empty()||wire.len()>2048||out.len()>2048{return Err(INVALID)}
    let cell=session(handle)?;
    let mut e=cell.lock().map_err(|_|BAD_STAGE)?;
    if e.phase!=PH_ACTIVE||e.protected_fec2_features!=7
        ||!e.owner.is_fec2_probe_bound(){return Err(BAD_STAGE)}
    let budget=usize::from(e.wire_limit).checked_sub(
        wbd_codec::record_frame::FIXED_WIRE_OVERHEAD).ok_or(INVALID)?;
    let receiver=e.fec2_actual_peer_rx.as_mut().ok_or(BAD_STAGE)?;
    let (pn,kind,frame)=receiver.consume(wire.to_vec(),budget)
        .map_err(|_|INVALID)?;
    if frame.len()>out.len(){return Err(INVALID)}
    if kind==3 {
        // Only the actual AEAD-unique M3 RS16 result, never Go-supplied
        // plaintext. The ORIGINAL M4 TUN sink owns fd/loan/Stop/generation.
        // A write is kernel copy, not a claim of application delivery.
        let tun=e.tun_sink.as_ref().ok_or(BAD_STAGE)?;
        if tun.write_authenticated_ipv4(e.generation,&frame)
            .ok()!=Some(frame.len()){return Err(INVALID)}
    }
    out[..frame.len()].copy_from_slice(&frame);
    Ok((pn,kind,frame.len()))
}
#[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_fec2_probe_actual_peer_consume(
    handle:u64,wire:*const u8,wire_len:usize,
    output:*mut u8,output_len:usize,
    pn:*mut u64,kind:*mut u8,recovered_len:*mut u32
)->i32{
    if wire.is_null()||output.is_null()||pn.is_null()||kind.is_null()
        ||recovered_len.is_null()||wire_len==0||wire_len>2048
        ||output_len==0||output_len>2048{return INVALID}
    let input=unsafe{std::slice::from_raw_parts(wire,wire_len)};
    let target=unsafe{std::slice::from_raw_parts_mut(output,output_len)};
    let Ok((received_pn,received_kind,actual_len))=
        fec2_peer_received_actual_cipher(handle,input,target)
    else{return INVALID};
    unsafe{pn.write(received_pn);kind.write(received_kind);
        recovered_len.write(actual_len as u32)}
    OK
}


//// M0 test-scope actual reverse raw kernel C2S kind1, opened by the
//// ORIGINAL scoped owner M3 AEAD+unique PN. No independent decryptor or
//// cold metadata may authorize a receipt. 52B test wire grammar only;
//// product kind1 receipt encoder/peer application remains NOT_RUN.
#[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn fec2_probe_reverse_raw_one(handle:u64)->Result<(u32,u32),i32>{
    use wbd_types::RecordPn;
    use wbd_recovery::{ReceiptOpenFacts,ReceiptPage,admit_opened_receipt};
    let cell=session(handle)?;
    let mut e=cell.lock().map_err(|_|BAD_STAGE)?;
    if e.phase!=PH_ACTIVE||e.workers.is_some()
        ||e.protected_fec2_features!=7
        ||!e.owner.is_fec2_probe_bound(){return Err(BAD_STAGE)}
    let raw=Arc::clone(e.raw_rx.as_ref().ok_or(BAD_STAGE)?);
    if raw.generation()!=e.generation||raw.is_stopping(){return Err(BAD_STAGE)}
    let f=e.flow;
    let tuple=Ipv4Tuple{
        src_ip:&f.client_ip,dst_ip:&f.server_ip,
        src_port:f.client_port,dst_port:f.server_port
    };
    let mut slab=e.arena.allocate().map_err(|_|FULL)?;
    let (len,seq)=raw.recv_one_into(
        e.generation,slab.writable(),tuple,PacketPersona::Legacy
    ).map_err(|_|INVALID)?;
    if len<FIXED_WIRE_OVERHEAD||seq!=e.rx_boundary{return Err(INVALID)}
    // Borrow the ORIGINAL M3 C2S replay and health opener in the one
    // scoped ProtectedScopedOwner. Failed AEAD never reaches M2.
    let opened=e.owner.open_reverse_health_probe(
        &mut slab.writable()[..len]
    ).map_err(|_|INVALID)?;
    if opened.payload.len()!=52{return Err(INVALID)}
    let p=opened.payload;
    let report_seq=u32::from_be_bytes(p[..4].try_into().map_err(|_|INVALID)?);
    let largest=RecordPn(u64::from_be_bytes(
        p[4..12].try_into().map_err(|_|INVALID)?));
    let base=RecordPn(u64::from_be_bytes(
        p[12..20].try_into().map_err(|_|INVALID)?));
    let mut bitmap=[0u8;32];
    bitmap.copy_from_slice(&p[20..52]);
    let (_,verified_epoch)=e.owner.receipt_probe_identity().ok_or(BAD_STAGE)?;
    let peer=e.fec2_receipt_sender.as_mut().ok_or(BAD_STAGE)?;
    let verified=ReceiptOpenFacts{
        verified_reverse_lane:peer.route.outbound_lane(),
        verified_reverse_direction:wbd_recovery::WireDirection::ClientToServer,
        verified_tunnel_epoch:verified_epoch,
        control_record_pn:RecordPn(opened.pn),
    };
    // Deterministic opt-in probe clock: before first PTO at 12ms, after
    // ACTUAL M4 repair / M2 grant at 31ms at 32ms. Never call the global
    // process quota owner with a synthetic backwards time; production must
    // use one real monotonic owner clock rather than this one-shot probe.
    let target=peer.start_ns.saturating_add(
        if peer.repair_submitted{32_000_000}else{12_000_000}
    );
    let mut process=fec2_probe_process_quota().lock().map_err(|_|BAD_STAGE)?;
    let now=process.at_least(target);
    let pages=vec![ReceiptPage{base_pn:base,bitmap}];
    // Build M2's checked scope only AFTER the ORIGINAL Rust C2S
    // AEAD/replay opener succeeded. The exact same facts must first pass
    // the original process-wide M2 admission, never a raw Go bitmap.
    let scoped=wbd_recovery::ScopedAuthenticatedReceipt::checked_after_open(
        peer.route,verified,largest,report_seq,pages.clone()
    ).map_err(|_|INVALID)?;
    let released=admit_opened_receipt(
        &mut process.broker,peer.direction,&mut peer.shadow,peer.route,
        verified,largest,report_seq,pages,now
    ).map_err(|_|INVALID)?;
    if peer.mature.on_authenticated_receipt(&scoped,now).is_err(){
        // Telemetry errors must not refund or undo a valid receipt.
        // Disable AUTO and report censored, not a guessed zero loss.
        peer.mature_invalid=true;
    }
    let count=released.len() as u32;
    let left=peer.shadow.outstanding() as u32;
    // Original frozen loan releases here; kernel copied bytes are NOT an
    // authenticated ACK, only the admitted reverse control retires it.
    drop(released);
    e.arena.drain_returns();
    Ok((count,left))
}
#[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_fec2_probe_reverse_raw_receipt(
    handle:u64,released:*mut u32,outstanding:*mut u32
)->i32{
    if released.is_null()||outstanding.is_null(){return INVALID}
    match fec2_probe_reverse_raw_one(handle){
        Ok((done,left))=>{
            unsafe{released.write(done);outstanding.write(left)};
            OK
        },
        Err(err)=>err,
    }
}
#[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_fec2_probe_sender_shadow_status(
    handle:u64,outstanding:*mut u32
)->i32{
    if outstanding.is_null(){return INVALID}
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||!e.owner.is_fec2_probe_bound(){
        return BAD_STAGE
    }
    let Some(sender)=e.fec2_receipt_sender.as_ref()else{return BAD_STAGE};
    unsafe{outstanding.write(sender.shadow.outstanding() as u32)}
    OK
}

// Test-only REAL M4 raw repair. An M2 PTO candidate borrows the identical
// original FrozenRecord, debits the ONE global process broker through a
// scoped grant, then the original M4 send_one submits exactly the SAME
// authenticated PN/Seq/ciphertext. Its synchronous copied prefix is
// translated using M2's typed driver settlement (never peer delivery).
// Ambiguous send failure is always Unproven and stays charged.
#[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn fec2_probe_real_frozen_repair_one(
    handle:u64
)->Result<(u64,u32,u32,u64),i32>{
    use wbd_recovery::{
        reserve_frozen_submission,complete_driver_prefix,
        DriverPrefixObservation,BatchSuffixEvidence,RepairSendResult,
    };
    let cell=session(handle)?;
    let mut e=cell.lock().map_err(|_|BAD_STAGE)?;
    if e.phase!=PH_ACTIVE||e.workers.is_some()
        ||e.protected_fec2_features!=7
        ||!e.owner.is_fec2_probe_bound(){return Err(BAD_STAGE)}
    let raw=Arc::clone(e.raw_tx.as_ref().ok_or(BAD_STAGE)?);
    if raw.generation()!=e.generation || raw.is_stopping(){return Err(BAD_STAGE)}
    let generation=e.generation;
    let flow=e.flow;
    let tuple=Ipv4Tuple{
        src_ip:&flow.server_ip,dst_ip:&flow.client_ip,
        src_port:flow.server_port,dst_port:flow.client_port,
    };
    let presentation=Presentation{
        ack32:1,advertised_window:4096,ip_id:43,
        persona:PacketPersona::Legacy,
    };
    let sender=e.fec2_receipt_sender.as_mut().ok_or(BAD_STAGE)?;
    // A positive peer receipt for SOURCE PN0 already retired that shadow.
    // The negative PN1 evidence can only form a candidate after its PTO.
    let mut process=fec2_probe_process_quota().lock().map_err(|_|BAD_STAGE)?;
    let now=process.at_least(sender.start_ns.saturating_add(31_000_000));
    let mut poll=sender.shadow.on_timer(now);
    if !poll.releases.is_empty()||poll.candidates.len()!=1 {
        return Err(INVALID)
    }
    let candidate=poll.candidates.pop().ok_or(INVALID)?;
    if candidate.pn().0!=1||!sender.shadow.preflight(&candidate,now){
        return Err(INVALID)
    }
    let original=candidate.frozen().metadata();
    let outer_bytes=candidate.frozen().bytes().len()
        .checked_add(40).ok_or(INVALID)? as u64;
    // Whole global grant is process-scoped, not a per-lane sparse mint.
    let before=process.broker.snapshot().charged_repairs;
    let lease=process.broker.grant(
        sender.direction,outer_bytes,20_000_000,now
    ).map_err(|_|INVALID)?;
    let submission=reserve_frozen_submission(
        &mut process.broker,lease,sender.route,&sender.shadow,
        &candidate,outer_bytes,now
    ).map_err(|_|INVALID)?;
    if submission.driver.metadata!=original
        ||submission.driver.wire.as_ptr()!=candidate.frozen().bytes().as_ptr()
        ||!sender.shadow.preflight(&candidate,now){return Err(INVALID)}
    let ordered=[(submission.reservation_id,sender.route)];
    drop(process);
    // No process-wide quota lock over a blocking M4 kernel write.
    let driver_result=raw.send_one(
        generation,candidate.frozen(),tuple,presentation
    );
    let mut process=fec2_probe_process_quota().lock().map_err(|_|BAD_STAGE)?;
    let now=process.at_least(now.0);
    // No fabricated "proven-not-attempted" from a syscall failure.
    let observation=if driver_result.is_ok(){
        DriverPrefixObservation::checked(
            1,1,None,BatchSuffixEvidence::Unproven
        )
    }else{
        DriverPrefixObservation::checked(
            1,0,Some(0),BatchSuffixEvidence::Unproven
        )
    }.map_err(|_|INVALID)?;
    let settlement=complete_driver_prefix(
        &mut process.broker,&ordered,observation,now
    ).map_err(|_|INVALID)?;
    if settlement.len()!=1{return Err(INVALID)}
    let status=settlement.shadow_result(0).ok_or(INVALID)?;
    sender.shadow.on_send_result(&candidate,status,now)
        .map_err(|_|INVALID)?;
    if sender.mature.on_possible_recovery(
        sender.route.outbound_lane(),candidate.pn(),status,now
    ).is_err(){sender.mature_invalid=true;}
    if driver_result.is_err(){return Err(INVALID)}
    if status!=RepairSendResult::Accepted || settlement.counts.accepted!=1
        ||settlement.counts.uncertain!=0 || settlement.counts.held_unproven!=0
        ||settlement.counts.definitely_not_sent!=0
        ||process.broker.snapshot().pending!=0
        ||process.broker.snapshot().charged_repairs!=before+outer_bytes
        ||sender.shadow.outstanding()!=1 {return Err(INVALID)}
    sender.repair_submitted=true;
    let copied=driver_result.map_err(|_|INVALID)?;
    if copied as u64!=outer_bytes{return Err(INVALID)}
    Ok((candidate.pn().0,original.seq.0 as u32,
        u32::try_from(candidate.frozen().bytes().len()).map_err(|_|INVALID)?,
        outer_bytes))
}
#[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_fec2_probe_real_frozen_repair(
    handle:u64,pn:*mut u64,seq:*mut u32,wire:*mut u32,
    charged:*mut u64
)->i32{
    if pn.is_null()||seq.is_null()||wire.is_null()||charged.is_null(){
        return INVALID
    }
    let Ok((p,s,w,c))=fec2_probe_real_frozen_repair_one(handle)
    else{return BAD_STAGE};
    unsafe{pn.write(p);seq.write(s);wire.write(w);charged.write(c)}
    OK
}

// Test-only original-Go-verified live session process capacity probe.
// No forged cold, global grant cannot be minted per connection.
#[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn fec2_probe_process_quota_snapshot(handle:u64)->Result<(u32,u64,u64),i32>{
    let cell=session(handle)?;
    let e=cell.lock().map_err(|_|BAD_STAGE)?;
    if e.phase!=PH_ACTIVE||!e.owner.is_fec2_probe_bound()
        ||e.fec2_probe_budget_direction.is_none(){return Err(BAD_STAGE)}
    let process=fec2_probe_process_quota().lock().map_err(|_|BAD_STAGE)?;
    let snapshot=process.broker.snapshot();
    Ok((snapshot.registered_directions as u32,
        snapshot.held_unused_grants,snapshot.hard_cap))
}
#[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_fec2_probe_process_quota_snapshot(
    handle:u64,count:*mut u32,held:*mut u64,cap:*mut u64
)->i32{
    if count.is_null()||held.is_null()||cap.is_null(){return INVALID}
    match fec2_probe_process_quota_snapshot(handle){
        Ok((c,h,b))=>{unsafe{count.write(c);held.write(h);cap.write(b)};OK},
        Err(v)=>v,
    }
}
#[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub extern "C" fn wbd_m0_embedded_go_fec2_probe_process_quota_hold(
    handle:u64,bytes:u64
)->i32{
    if bytes==0{return INVALID}
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||!e.owner.is_fec2_probe_bound(){return BAD_STAGE}
    let Some(direction)=e.fec2_probe_budget_direction else{return BAD_STAGE};
    let Ok(mut process)=fec2_probe_process_quota().lock()else{return BAD_STAGE};
    let prior=process.now_ns;
    let now=process.at_least(prior);
    if process.broker.grant(direction,bytes,50_000_000,now).is_err(){
        return INVALID
    }
    OK
}

// Shared M0 adapter: the original M4 KernelSendReport is the ONLY
// source of definite copied prefix. Linux sendmmsg positive-short loses
// errno, while EINTR/short-completion can be ambiguous. M0 conservatively
// holds all not-positively-proven suffix reservation debt; only an
// independently verified never-syscalled suffix may be NotSent.
#[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn m0_fec2_observe_native_m4_repair_prefix(
    report:&wbd_platform::linux_batch::KernelSendReport,total:usize,
)->Result<wbd_recovery::DriverPrefixObservation,wbd_recovery::GlobalRepairError>{
    use wbd_recovery::{DriverPrefixObservation,BatchSuffixEvidence,GlobalRepairError};
    // Fail closed before touching the broker if M4 provides an invalid
    // prefix/uncertain marker, never truncate an out-of-range driver count.
    if total>32||report.outcome.accepted_prefix>total{
        return Err(GlobalRepairError::InvalidBatch)
    }
    let count=report.outcome.accepted_prefix;
    let uncertain=report.outcome.uncertain_index;
    DriverPrefixObservation::checked(
        total,count,uncertain,BatchSuffixEvidence::Unproven
    )
}

// M0 opt-in integration of TWO original M1 FrozenRecord repair candidates
// with the original M4 raw syscall and the original M2 scoped batch contract.
// The first slot is REALLY submitted to Linux; the second is deliberately
// stopped BEFORE the syscall. Only this explicit no-attempt decision makes
// the second suffix ProvenNotAttempted; EAGAIN/short/unknown can NEVER do so.
// It is not a kernel sendmmsg prefix/uncertain classifier, and does not claim
// production M4 batch completion semantics.
#[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn fec2_probe_real_frozen_repair_prefix_two(
    handle:u64,actual_kernel_batch:bool,
)->Result<(u64,u32,u32,u64,u64),i32>{
    use wbd_recovery::{
        reserve_frozen_submission,complete_driver_prefix,
        DriverPrefixObservation,BatchSuffixEvidence,RepairSendResult,
    };
    let cell=session(handle)?;
    let mut e=cell.lock().map_err(|_|BAD_STAGE)?;
    if e.phase!=PH_ACTIVE||e.workers.is_some()
        ||e.protected_fec2_features!=7
        ||!e.owner.is_fec2_probe_bound(){return Err(BAD_STAGE)}
    let raw=Arc::clone(e.raw_tx.as_ref().ok_or(BAD_STAGE)?);
    if raw.generation()!=e.generation||raw.is_stopping(){return Err(BAD_STAGE)}
    let generation=e.generation;
    let flow=e.flow;
    let tuple=Ipv4Tuple{
        src_ip:&flow.server_ip,dst_ip:&flow.client_ip,
        src_port:flow.server_port,dst_port:flow.client_port,
    };
    let presentation=Presentation{
        ack32:1,advertised_window:4096,ip_id:43,
        persona:PacketPersona::Legacy,
    };
    let sender=e.fec2_receipt_sender.as_mut().ok_or(BAD_STAGE)?;
    if sender.repair_submitted{return Err(INVALID)}
    let mut process=fec2_probe_process_quota().lock().map_err(|_|BAD_STAGE)?;
    let now=process.at_least(sender.start_ns.saturating_add(31_000_000));
    let poll=sender.shadow.on_timer(now);
    if !poll.releases.is_empty()||poll.candidates.len()!=2{return Err(INVALID)}
    let mut iter=poll.candidates.into_iter();
    let first=iter.next().ok_or(INVALID)?;
    let second=iter.next().ok_or(INVALID)?;
    if first.pn().0!=0||second.pn().0!=1
        ||!sender.shadow.preflight(&first,now)
        ||!sender.shadow.preflight(&second,now){return Err(INVALID)}
    let first_meta=first.frozen().metadata();
    let second_meta=second.frozen().metadata();
    let first_outer=first.frozen().bytes().len()
        .checked_add(40).ok_or(INVALID)? as u64;
    let second_outer=second.frozen().bytes().len()
        .checked_add(40).ok_or(INVALID)? as u64;
    let total=first_outer.checked_add(second_outer).ok_or(INVALID)?;
    let before=process.broker.snapshot().charged_repairs;
    let lease=process.broker.grant(
        sender.direction,total,20_000_000,now
    ).map_err(|_|INVALID)?;
    let reserved_first=reserve_frozen_submission(
        &mut process.broker,lease,sender.route,&sender.shadow,
        &first,first_outer,now
    ).map_err(|_|INVALID)?;
    let reserved_second=reserve_frozen_submission(
        &mut process.broker,lease,sender.route,&sender.shadow,
        &second,second_outer,now
    ).map_err(|_|INVALID)?;
    if reserved_first.driver.metadata!=first_meta
        ||reserved_second.driver.metadata!=second_meta
        ||reserved_first.driver.wire.as_ptr()!=first.frozen().bytes().as_ptr()
        ||reserved_second.driver.wire.as_ptr()!=second.frozen().bytes().as_ptr()
        ||!sender.shadow.preflight(&first,now)
        ||!sender.shadow.preflight(&second,now){return Err(INVALID)}
    let ordered=[
        (reserved_first.reservation_id,sender.route),
        (reserved_second.reservation_id,sender.route),
    ];
    drop(process);
    // Actual native M4 sendmmsg consumes BOTH ORIGINAL FrozenRecord Arcs
    // in ONE kernel call, with no plaintext clone, re-seal or PN mutation.
    // The alternate control case remains a REAL single M4 sendto and an
    // explicit, verifiably NEVER-entered-kernel second slot.
    // DO NOT hold global M2 mutex across either blocking syscall.
    let actual_report=if actual_kernel_batch{
        let frozen=[first.frozen().clone(),second.frozen().clone()];
        Some(raw.send_kernel_multimsg(
            generation,&frozen,tuple,&[presentation,presentation]
        ))
    }else{None};
    let first_result=if actual_kernel_batch{None}else{
        Some(raw.send_one(generation,first.frozen(),tuple,presentation))
    };
    let mut process=fec2_probe_process_quota().lock().map_err(|_|BAD_STAGE)?;
    let now=process.at_least(now.0);
    // The original kernel report is the ONLY source of Accepted count.
    // Any positive-short/errno-unknown remainder is Unproven and keeps
    // M2 process debt; NEVER relabel it definitely NotSent.
    let observation=if let Some(report)=actual_report.as_ref(){
        m0_fec2_observe_native_m4_repair_prefix(report,2)
    }else if first_result.as_ref().is_some_and(|r|r.is_ok()){
        DriverPrefixObservation::checked(
            2,1,None,BatchSuffixEvidence::ProvenNotAttempted
        )
    }else{
        DriverPrefixObservation::checked(
            2,0,Some(0),BatchSuffixEvidence::Unproven
        )
    }.map_err(|_|INVALID)?;
    let settled=complete_driver_prefix(
        &mut process.broker,&ordered,observation,now
    ).map_err(|_|INVALID)?;
    if settled.len()!=2{return Err(INVALID)}
    for (index,candidate) in [&first,&second].into_iter().enumerate(){
        let status=settled.shadow_result(index).ok_or(INVALID)?;
        sender.shadow.on_send_result(candidate,status,now)
            .map_err(|_|INVALID)?;
        if sender.mature.on_possible_recovery(
            sender.route.outbound_lane(),candidate.pn(),status,now
        ).is_err(){sender.mature_invalid=true;}
    }
    let all_kernel_copied=actual_report.as_ref().is_some_and(
        |r|r.outcome.accepted_prefix==2
            &&r.outcome.uncertain_index.is_none()
            &&r.outcome.error.is_none()
            &&r.signal==wbd_platform::linux_batch::KernelSendSignal::None
    );
    if actual_kernel_batch&&!all_kernel_copied{return Err(INVALID)}
    if !actual_kernel_batch&&first_result.as_ref().is_none_or(|x|x.is_err()){
        return Err(INVALID)
    }
    let charged=if actual_kernel_batch{total}else{first_outer};
    if settled.shadow_result(0)!=Some(RepairSendResult::Accepted)
        ||settled.shadow_result(1)!=Some(if actual_kernel_batch{
            RepairSendResult::Accepted
        }else{RepairSendResult::NotSent})
        ||settled.counts.accepted!=if actual_kernel_batch{2}else{1}
        ||settled.counts.definitely_not_sent!=if actual_kernel_batch{0}else{1}
        ||settled.counts.uncertain!=0
        ||settled.counts.held_unproven!=0
        ||process.broker.snapshot().pending!=0
        ||process.broker.snapshot().charged_repairs!=before+charged
        ||sender.shadow.outstanding()!=2{return Err(INVALID)}
    // Successful sendmmsg means kernel copies, NOT peer receipt.
    // Unsent test slot explicitly never reached kernel; both scenarios
    // retire FrozenRecord only on subsequent original reverse AEAD receipt.
    process.broker.revoke(lease,now).map_err(|_|INVALID)?;
    sender.repair_submitted=true;
    if !actual_kernel_batch &&
        first_result.as_ref().is_none_or(|r|r.as_ref().ok()
            .is_none_or(|n|*n as u64!=first_outer)){
        return Err(INVALID)
    }
    Ok((first.pn().0,first_meta.seq.0 as u32,
        u32::try_from(first.frozen().bytes().len()).map_err(|_|INVALID)?,
        charged,second_outer))
}
#[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_fec2_probe_real_frozen_prefix_two(
    handle:u64,pn:*mut u64,seq:*mut u32,wire:*mut u32,
    accepted:*mut u64,not_attempted:*mut u64,
)->i32{
    if pn.is_null()||seq.is_null()||wire.is_null()
        ||accepted.is_null()||not_attempted.is_null(){return INVALID}
    match fec2_probe_real_frozen_repair_prefix_two(handle,false){
        Ok((p,s,w,a,n))=>{
            unsafe{pn.write(p);seq.write(s);wire.write(w);
                accepted.write(a);not_attempted.write(n)};
            OK
        },
        Err(v)=>v,
    }
}

// Same original session/FrozenRecord/M2 setup, but two messages in ONE
// original M4 Linux sendmmsg kernel syscall. The second output denotes
// per-slot outer bytes charged, NOT an unsent/refunded slot.
#[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_fec2_probe_real_kernel_multimsg_two(
    handle:u64,pn:*mut u64,seq:*mut u32,wire:*mut u32,
    accepted:*mut u64,second_outer:*mut u64,
)->i32{
    if pn.is_null()||seq.is_null()||wire.is_null()
        ||accepted.is_null()||second_outer.is_null(){return INVALID}
    match fec2_probe_real_frozen_repair_prefix_two(handle,true){
        Ok((p,s,w,a,n))=>{
            unsafe{pn.write(p);seq.write(s);wire.write(w);
                accepted.write(a);second_outer.write(n)};
            OK
        },
        Err(v)=>v,
    }
}

// Receiver observability for the ORIGINAL Go policy starvation guard.
// Counts ONLY M3 AEAD/unique-PN first admissions. Incomplete data/repair
// are NOT inferred as mature packet loss (and must not trigger auto).
// Feature-gated integration, not deployed telemetry.
#[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_fec2_probe_verified_peer_counts(
    handle:u64,epoch:*const u8,len:usize,
    source:*mut u64,repair:*mut u64,recovered:*mut u64
)->i32{
    if epoch.is_null()||len!=16||source.is_null()||repair.is_null()
        ||recovered.is_null(){return INVALID}
    let mut exact=[0u8;16];
    exact.copy_from_slice(unsafe{std::slice::from_raw_parts(epoch,len)});
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.workers.is_some()
        ||e.protected_fec2_features!=7
        ||!e.owner.is_fec2_probe_bound_to(exact){return BAD_STAGE}
    let Some(rx)=e.fec2_actual_peer_rx.as_ref()else{return BAD_STAGE};
    unsafe{
        source.write(rx.first_sources);
        repair.write(rx.first_repairs);
        recovered.write(rx.recovered_sources);
    }
    OK
}

// Actual M2 RX feedback draft created ONLY from authenticated M3 data
// observed above. This stage is not a peer-authenticated receipt encoder,
// not a control kind1 send, and not a quota release or kernel ACK.
#[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn fec2_peer_feedback_draft(
    handle:u64,now_ns:u64,send_result:u8
)->Result<(u32,u64,u64,u8),i32>{
    use wbd_recovery::FeedbackSendResult;
    let send=match send_result{
        0=>FeedbackSendResult::NotSent,
        1=>FeedbackSendResult::Accepted,
        2=>FeedbackSendResult::Uncertain,
        _=>return Err(INVALID),
    };
    let cell=session(handle)?;
    let mut e=cell.lock().map_err(|_|BAD_STAGE)?;
    if e.phase!=PH_ACTIVE || e.protected_fec2_features!=7
        ||!e.owner.is_fec2_probe_bound(){return Err(BAD_STAGE)}
    let rx=e.fec2_actual_peer_rx.as_mut().ok_or(BAD_STAGE)?;
    let draft=rx.feedback.on_due(MonoNs(now_ns)).ok_or(INVALID)?;
    if draft.pages().len()!=1{return Err(INVALID)}
    let base=draft.pages()[0].base_pn.0;
    let bits=draft.pages()[0].bitmap[0];
    let output=(draft.report_seq(),draft.largest_data_pn().0,base,bits);
    rx.feedback.on_send_result(&draft,send,MonoNs(now_ns))
        .map_err(|_|INVALID)?;
    Ok(output)
}
#[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_fec2_probe_actual_m2_rx_feedback(
    handle:u64,now_ns:u64,send_result:u8,
    report_seq:*mut u32,largest:*mut u64,base:*mut u64,bits:*mut u8
)->i32{
    if report_seq.is_null()||largest.is_null()||base.is_null()
        ||bits.is_null(){return INVALID}
    let Ok((seq,max,first,mask))=
        fec2_peer_feedback_draft(handle,now_ns,send_result)
    else{return INVALID};
    unsafe{report_seq.write(seq);largest.write(max);base.write(first);
        bits.write(mask)}
    OK
}

// Actual sender-local M2 observation, feature-gated and validated under
// this SAME original TLS/Detach owner. Eight words are
// firstsent, covered, missing, uncovered for 2s and 8s. Ambiguous
// repair observations are returned separately as CENSORED, never loss=0.
#[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn m0_add_mature_window(
    dst:&mut wbd_recovery::MatureWindow,src:wbd_recovery::MatureWindow
){
    dst.first_sent=dst.first_sent.saturating_add(src.first_sent);
    dst.first_sent_wire_bytes=dst.first_sent_wire_bytes.saturating_add(src.first_sent_wire_bytes);
    dst.unambiguous_positive=dst.unambiguous_positive.saturating_add(src.unambiguous_positive);
    dst.positive_wire_bytes=dst.positive_wire_bytes.saturating_add(src.positive_wire_bytes);
    dst.covered_missing=dst.covered_missing.saturating_add(src.covered_missing);
    dst.missing_wire_bytes=dst.missing_wire_bytes.saturating_add(src.missing_wire_bytes);
    dst.repaired_or_ambiguous=dst.repaired_or_ambiguous.saturating_add(src.repaired_or_ambiguous);
    dst.ambiguous_wire_bytes=dst.ambiguous_wire_bytes.saturating_add(src.ambiguous_wire_bytes);
    dst.uncovered=dst.uncovered.saturating_add(src.uncovered);
    dst.uncovered_wire_bytes=dst.uncovered_wire_bytes.saturating_add(src.uncovered_wire_bytes);
}
#[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_fec2_probe_mature_firstsend(
    handle:u64,epoch:*const u8,len:usize,elapsed_ns:u64,
    fast:*mut u64,slow:*mut u64,validity:*mut u8,
)->i32{
    if epoch.is_null()||len!=16||fast.is_null()||slow.is_null()||
       validity.is_null(){return INVALID}
    let mut exact=[0u8;16];
    exact.copy_from_slice(unsafe{std::slice::from_raw_parts(epoch,len)});
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE || e.protected_fec2_features!=7 ||
       !e.owner.is_fec2_probe_bound_to(exact){return BAD_STAGE}
    let Some(sender)=e.fec2_receipt_sender.as_mut()else{return BAD_STAGE};
    let Some(when)=sender.start_ns.checked_add(elapsed_ns)else{return INVALID};
    let pol=sender.mature.on_due(MonoNs(when));
    match pol {
        Ok(pol)=>{
            m0_add_mature_window(&mut sender.mature_2s,pol.window_2s);
            m0_add_mature_window(&mut sender.mature_8s,pol.window_8s);
            if pol.capacity_limited{sender.mature_invalid=true;}
        },
        Err(_)=>sender.mature_invalid=true,
    };
    let a=&sender.mature_2s;
    let b=&sender.mature_8s;
    if !a.conserved()||!b.conserved(){sender.mature_invalid=true;}
    // Distinguish no information (UNKNOWN), uncovered (UNKNOWN), and
    // a true original M4 repair (CENSORED). They are not a zero-loss ACK.
    let state=if sender.mature_invalid {3u8}
        else if a.first_sent==0||b.first_sent==0||a.uncovered!=0||b.uncovered!=0 {1u8}
        else if a.repaired_or_ambiguous!=0||b.repaired_or_ambiguous!=0 {2u8}
        else {0u8};
    let data=|m:&wbd_recovery::MatureWindow|{
        [m.first_sent,
         m.unambiguous_positive.saturating_add(m.covered_missing),
         m.covered_missing,m.uncovered,m.repaired_or_ambiguous]
    };
    let one=data(a);
    let two=data(b);
    unsafe{
        for i in 0..5{fast.add(i).write(one[i]);slow.add(i).write(two[i]);}
        validity.write(state);
    }
    OK
}

#[cfg(feature="m0_fec2_owner_probe")]
fn bind_fec2_from_private_go(
    handle:u64,epoch:[u8;16],features:u16,profile:u8,revision:u64
)->i32{
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.protected_fec2_features!=7
        ||features!=e.protected_fec2_features{return INVALID}
    if e.owner.bind_fec2_probe_from_private_go(
        features,epoch,profile,revision).is_err(){return INVALID}
    #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    {
        use wbd_recovery::{BudgetDirection,WireDirection,RepairBudgetConfig};
        if e.fec2_probe_budget_direction.is_some(){return INVALID}
        let Some((lane,_))=e.owner.receipt_probe_identity()else{return INVALID};
        let direction=BudgetDirection{
            tunnel:lane.tunnel,direction:WireDirection::ServerToClient
        };
        let Ok(mut process)=fec2_probe_process_quota().lock()else{return BAD_STAGE};
        let prior=process.now_ns;
    let now=process.at_least(prior);
        if process.broker.register(direction,RepairBudgetConfig{
            outer_mtu:1400,max_repair_bytes_per_epoch:65_536,
            max_pending_reservations:4,max_pending_bytes:5600,
            io_timeout_ns:10_000_000
        },now).is_err(){return INVALID}
        e.fec2_probe_budget_start_ns=now.0;
        e.fec2_probe_budget_direction=Some(direction);
    }
    OK
}
// Pending means requested but NOT applied. The authenticated Go/Detach
// owner, not cold metadata or a peer control frame, may stage a profile.
#[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_fec2_probe_stage_policy(
    handle:u64,epoch:*const u8,len:usize,profile:u8,revision:u64
)->i32{
    if epoch.is_null()||len!=16||profile>7||revision==0{return INVALID}
    let mut exact=[0u8;16];
    exact.copy_from_slice(unsafe{std::slice::from_raw_parts(epoch,len)});
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.workers.is_some()
        ||e.protected_fec2_features!=7
        ||!e.owner.is_fec2_probe_bound_to(exact){return BAD_STAGE}
    let Some((_,applied))=e.owner.fec2_probe_applied_policy()else{return BAD_STAGE};
    let latest=e.fec2_probe_pending_policy.map_or(applied,|(_,r)|r);
    if revision<=latest{return INVALID}
    if profile==7 {
        // M0: no new FEC block can be admitted while an old immutable
        // shadow remains unsettled. A process-global repair grant is never
        // inferred released; the existing Stop owner retires its budget.
        if e.arena.report().loaned!=0||
           e.fec2_receipt_sender.as_ref().is_some_and(
               |s|s.shadow.outstanding()!=0
           ){return BAD_STAGE}
        if e.owner.apply_fec2_probe_quiescent_off(exact,revision).is_err(){
            return BAD_STAGE
        }
        e.fec2_probe_pending_policy=None;
        return OK
    }
    e.fec2_probe_pending_policy=Some((profile,revision));
    OK
}
#[cfg(feature="m0_fec2_owner_probe")]
fn scoped_fec2_probe_bound(handle:u64,epoch:[u8;16])->i32{
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.phase==PH_ACTIVE&&e.protected_fec2_features==7
       &&e.owner.is_fec2_probe_bound_to(epoch){OK}else{INVALID}
}
#[cfg(feature="m0_fec2_owner_probe")]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_bind_fec2_probe_after_verified_tls(
    h:u64,epoch:*const u8,len:usize,features:u16,profile:u8,revision:u64
)->i32{
    if epoch.is_null()||len!=16{return INVALID}
    let mut bytes=[0u8;16];
    bytes.copy_from_slice(unsafe{std::slice::from_raw_parts(epoch,len)});
    bind_fec2_from_private_go(h,bytes,features,profile,revision)
}
// A configuration is "applied" only after original Rust accepted it
// under the verified Go TLS/Detach owner. Go FecV2Apply must additionally
// compare profile/revision/client/direction to its own requested intent.
#[cfg(feature="m0_fec2_owner_probe")]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_fec2_probe_applied_policy(
    handle:u64,profile:*mut u8,revision:*mut u64
)->i32{
    if profile.is_null()||revision.is_null(){return INVALID}
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE{return BAD_STAGE}
    let Some((p,r))=e.owner.fec2_probe_applied_policy()else{return BAD_STAGE};
    unsafe{profile.write(p);revision.write(r)}
    OK
}

#[cfg(feature="m0_fec2_owner_probe")]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_fec2_probe_scope_status(
    h:u64,epoch:*const u8,len:usize
)->i32{
    if epoch.is_null()||len!=16{return INVALID}
    let mut bytes=[0u8;16];
    bytes.copy_from_slice(unsafe{std::slice::from_raw_parts(epoch,len)});
    scoped_fec2_probe_bound(h,bytes)
}

fn abort(handle:u64)->i32{
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if e.phase==PH_ACTIVE{return OK} // Go defer after commit
    if e.phase!=PH_PREPARED{return BAD_STAGE}
    // Terminal before unlink, including for racing cloned references.
    let _=e.owner.stop();
    e.phase=PH_STOPPED;
    drop(e);
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    if r.entries.get(&handle).is_some_and(|x|Arc::ptr_eq(x,&cell)){
        r.entries.remove(&handle);
    }
    OK
}
fn stop(handle:u64)->i32{
    // Leave registry unlocked while joining. Driver handles and owner slabs
    // cannot be released while either Rust worker still references them.
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    {
        let Ok(cell)=session(handle)else{return UNKNOWN};
        let workers={
            let Ok(mut e)=cell.lock()else{return BAD_STAGE};
            if e.phase==PH_STOPPED{return OK}
            if e.phase!=PH_ACTIVE && e.phase!=PH_STOPPING{return BAD_STAGE}
            if e.joining{return STOP_INCOMPLETE}
            let w=e.workers.take();
            if let Some(ref w)=w{
                w.shutdown.store(true,Ordering::Release);
                e.joining=true;
            }
            #[cfg(all(feature="fec2_product_record",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
            e.fec2_rx_admit.store(false,Ordering::Release);
            e.phase=PH_STOPPING;
            w
        };
        if let Some(w)=workers{
            let rx=w.rx.join();
            let tx=w.tx.join();
            if rx.is_err()||tx.is_err(){
                // A failed join cannot authorize driver/slab retirement.
                return STOP_INCOMPLETE
            }
            let Ok(mut e)=cell.lock()else{return BAD_STAGE};
            e.joining=false;
        }
    }
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if e.phase==PH_STOPPED{return OK}
    if e.phase!=PH_ACTIVE&&e.phase!=PH_STOPPING{return BAD_STAGE}
    // Stop the REAL M4 raw driver and TUN sink before quiescing original
    // M1 owner. Both were opened on the same verified generation, never
    // inferred from cold248. A live in-flight kernel borrow must stay held.
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    {
        if let Some(ref raw)=e.raw_rx {raw.begin_stop()}
        if let Some(ref raw)=e.raw_tx {raw.begin_stop()}
        if let Some(ref tun)=e.tun_sink {tun.begin_stop()}
        #[cfg(all(feature="m0_fec2_owner_probe",feature="fec2_product_record",
            target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        if let Some(ref tun)=e.fec2_live_peer_tun {tun.begin_stop()}
    }
    #[cfg(all(feature="fec2_product_record",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    {
        // Both kernel workers are joined: M1 retained FEC source/parity
        // slabs may now be retired exactly once, never while M4 borrows
        // cipher bytes or original driver's synchronous call is in flight.
        if let Some(stream)=e.fec2_live_tx.as_mut(){stream.stop()}
        e.fec2_live_tx=None;
        e.fec2_staged_pns.clear();
    }
    let Ok(retired)=e.owner.stop()else{return BAD_STAGE};
    let mut drained=retired.ready.batch_handles_released();
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    {
        if let Some(ref raw)=e.raw_rx{
            drained &= raw.stop_until(Instant::now())==StopResult::Drained;
        }
        if let Some(ref raw)=e.raw_tx{
            drained &= raw.stop_until(Instant::now())==StopResult::Drained;
        }
        if let Some(ref tun)=e.tun_sink{
            drained &= tun.stop_until(Instant::now())==StopResult::Drained;
        }
        #[cfg(all(feature="m0_fec2_owner_probe",feature="fec2_product_record",
            target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        if let Some(ref tun)=e.fec2_live_peer_tun{
            drained &= tun.stop_until(Instant::now())==StopResult::Drained;
        }
    }
    if !drained{
        e.phase=PH_STOPPING;return STOP_INCOMPLETE
    }
    #[cfg(all(feature="fec2_product_record",target_os="linux",
        any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    if let Some(outer)=e.original_outer.take(){
        let Ok(active)=outer.lock()else{return BAD_STAGE};
        let Ok(mut broker)=original_process_repair_quota().lock()
            else{return BAD_STAGE};
        // Only AFTER joined RX/TX and original M4 kernel borrow drain.
        // An uncertain syscall debt remains charged until this whole
        // generation is retired; per-session Stop never refunds it.
        if broker.retire_tunnel(active.direction.tunnel,loop_now()).ok()
            !=Some(1){return BAD_STAGE}
    }
    #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    if let Some(first)=e.normal_firstsend_m2.take(){
        let Ok(mut first)=first.lock()else{return BAD_STAGE};
        let now=loop_now();
        first.poll(now);
        if first.state.stop(now).is_err(){return BAD_STAGE}
    }
    #[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    if let Some(direction)=e.fec2_probe_budget_direction{
        let Ok(mut process)=fec2_probe_process_quota().lock()else{return BAD_STAGE};
        let prior=process.now_ns;
        let now=process.at_least(prior);
        // Do not lose the registered identity if M2 retirement failed.
        // A stopped generation must retire exactly its own direction;
        // ambiguous/unknown retirement must fail closed, not invent credit.
        if process.broker.retire_tunnel(direction.tunnel,now).ok()!=Some(1){
            return BAD_STAGE
        }
        e.fec2_probe_budget_direction=None;
        e.fec2_receipt_sender.take();
    }
    e.phase=PH_STOPPED;OK
}
// A native Game group consumes only already COMMITTED original-Go credential
// TLS lane handles. No exported cold248, KDF material, FakeTCP flow or
// untrusted caller byte can create the group. This is a true shared AEAD/PN
// GameAdapter, but no M4 driver or CLI APPLIED until separately installed.
#[cfg(feature="fec2_product_record")]
fn game_group_join_original(handles:&[u64],server:bool)->Result<u64,i32>{
    if !matches!(handles.len(),2|4){return Err(INVALID)}
    let mut ids=handles.to_vec();
    ids.sort_unstable();
    ids.dedup();
    if ids.len()!=handles.len(){return Err(INVALID)}
    // Resolve references with registry lock released before Entry locks, so
    // original Stop never deadlocks against a group constructor.
    let cells={
        let r=registry().lock().map_err(|_|BAD_STAGE)?;
        ids.iter().map(|id|r.entries.get(id).cloned().ok_or(UNKNOWN))
            .collect::<Result<Vec<_>,_>>()?
    };
    let mut locks=cells.iter().map(|cell|cell.lock().map_err(|_|BAD_STAGE))
        .collect::<Result<Vec<_>,_>>()?;
    let mut epoch=None;
    let mut tunnel=None;
    let mut seen:u8=0;
    for e in &locks{
        if e.phase!=PH_ACTIVE||e.server_side!=server||
           e.protected_features!=7||e.game_joined||
           e.game_pending_cold.is_none(){
            return Err(BAD_STAGE)
        }
        #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        if e.workers.is_some()||e.raw_tx.is_some()||
           e.raw_rx.is_some()||e.tun_sink.is_some(){
            return Err(BAD_STAGE)
        }
        let id=e.game_pending_cold.as_ref().ok_or(BAD_STAGE)?.identity();
        if id.server!=server||id.logical_epoch==[0;16]||
           id.go_lane_id==0||usize::from(id.go_lane_id)>handles.len(){
            return Err(INVALID)
        }
        let bit=1u8<<(id.go_lane_id-1);
        if seen&bit!=0{return Err(INVALID)}
        seen|=bit;
        if epoch.is_some_and(|old|old!=id.logical_epoch)||
           tunnel.is_some_and(|old|old!=id.tunnel_id){return Err(INVALID)}
        epoch=Some(id.logical_epoch);tunnel=Some(id.tunnel_id);
    }
    if seen!=((1u8<<handles.len())-1){return Err(INVALID)}
    let mut r=registry().lock().map_err(|_|BAD_STAGE)?;
    if r.game_groups.len()>=MAX_SESSIONS/2{return Err(FULL)}
    let generation=r.generation;
    r.generation=generation.checked_add(1).ok_or(FULL)?;
    let group_handle=(u64::from(generation)<<32)|0x474Du64;
    let mut cold=Vec::with_capacity(handles.len());
    for e in &mut locks{
        // Consume the sole per-lane original-Go cold authority. Failure in
        // any subsequent native constructor is terminal fail-closed; no
        // duplicate AEAD/PN allocator may be activated on these lane handles.
        e.game_joined=true;
        cold.push(e.game_pending_cold.take().ok_or(BAD_STAGE)?);
    }
    let adapter=crate::v4_game_lane::GameAdapter::from_private_original_go_tls(
        cold,server,wbd_types::TunnelKey{slot:14,generation},generation
    ).map_err(|_|INVALID)?;
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    let (flows,tx_seqs)={
        let mut ordered=locks.iter().map(|e|{
            let lane=e.owner.normal_firstsend_identity()
                .map(|(k,_)|k.slot).unwrap_or(0);
            (lane,e.flow,u64::from(e.game_tx_boundary))
        }).collect::<Vec<_>>();
        ordered.sort_by_key(|v|v.0);
        if ordered.iter().enumerate().any(|(i,x)|x.0!=i as u32+1||x.2==0){
            return Err(INVALID)
        }
        (ordered.iter().map(|v|v.1).collect::<Vec<_>>(),
         ordered.iter().map(|v|v.2).collect::<Vec<_>>())
    };
    r.game_groups.insert(group_handle,GameGroupNative{
        adapter:Arc::new(Mutex::new(adapter)),handles:ids,
        stopped:false,stopping:false,
        #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        server,
        #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        flows,
        #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        tx_seqs,
        #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        drivers:None,
    });
    Ok(group_handle)
}
#[cfg(feature="fec2_product_record")]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_game_group_join(
    handles:*const u64,count:usize,server:u32,out:*mut u64
)->i32{
    if handles.is_null()||out.is_null()||!matches!(count,2|4)||server>1{
        return INVALID
    }
    let hs=unsafe{std::slice::from_raw_parts(handles,count)};
    match game_group_join_original(hs,server!=0){
        Ok(h)=>{unsafe{out.write(h)};OK},Err(e)=>e
    }
}
#[cfg(feature="fec2_product_record")]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_game_group_state(
    group:u64,lanes:*mut u32,drivers_installed:*mut u32,
)->i32{
    if lanes.is_null()||drivers_installed.is_null(){return INVALID}
    let Ok(r)=registry().lock()else{return BAD_STAGE};
    let Some(e)=r.game_groups.get(&group)else{return UNKNOWN};
    if e.stopped{return BAD_STAGE}
    unsafe{
        lanes.write(e.handles.len() as u32);
        #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
        drivers_installed.write(u32::from(e.drivers.is_some()));
        #[cfg(not(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl"))))]
        drivers_installed.write(0);
    }
    // Explicit zero is critical: this is authenticated shared crypto owner
    // installation ONLY, not a positive M4 kernel/TUN product readiness.
    OK
}
#[cfg(feature="fec2_product_record")]
#[no_mangle]
pub extern "C" fn wbd_m0_embedded_go_game_group_stop(group:u64)->i32{
    let (adapter,mut driver)={
        let Ok(mut r)=registry().lock()else{return BAD_STAGE};
        let Some(e)=r.game_groups.get_mut(&group)else{return UNKNOWN};
        if e.stopped{return OK}
        if e.stopping{return STOP_INCOMPLETE}
        e.stopping=true;
        (Arc::clone(&e.adapter),
         {
             #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
             {e.drivers.take()}
             #[cfg(not(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl"))))]
             {None::<()>}
         })
    };
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    if let Some(ref mut native)=driver{
        if native.stop_and_drain().is_err(){
            let Ok(mut r)=registry().lock()else{return BAD_STAGE};
            let Some(e)=r.game_groups.get_mut(&group)else{return UNKNOWN};
            e.drivers=driver;e.stopping=false;
            return STOP_INCOMPLETE
        }
    }
    let Ok(mut game)=adapter.lock()else{return STOP_INCOMPLETE};
    game.stop();drop(game);
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    let Some(e)=r.game_groups.get_mut(&group)else{return UNKNOWN};
    e.stopped=true;e.stopping=false;OK
}
#[cfg(all(feature="fec2_product_record",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_game_group_loop_start(
    group:u64,ifname:*const u8,ifname_len:usize,ifindex:u32,
    fd:i32,tunname:*const u8,tunname_len:usize,
)->i32{
    if ifname.is_null()||ifname_len==0||ifname_len>15||
       tunname.is_null()||tunname_len==0||tunname_len>15||
       ifindex==0||fd<3{return INVALID}
    let Ok(ifname)=std::str::from_utf8(unsafe{
        std::slice::from_raw_parts(ifname,ifname_len)
    })else{return INVALID};
    let Ok(tunname)=std::str::from_utf8(unsafe{
        std::slice::from_raw_parts(tunname,tunname_len)
    })else{return INVALID};
    // Duplicate real Go-owned TUN FD. Original Go retains its descriptor
    // until native joined Stop has reclaimed raw/TUN worker loans.
    let Ok(dup)=unsafe{BorrowedFd::borrow_raw(fd)}.try_clone_to_owned()
    else{return INVALID};
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    let Some(e)=r.game_groups.get_mut(&group)else{return UNKNOWN};
    if e.stopped||e.stopping||e.drivers.is_some(){return BAD_STAGE}
    let owner=crate::v4_game_public_kernel::GameKernelOwner::start(
        Arc::clone(&e.adapter),e.flows.clone(),e.tx_seqs.clone(),e.server,
        ifname,ifindex,dup,tunname,(group>>32) as u32
    );
    let Ok(owner)=owner else{return BAD_STAGE};
    e.drivers=Some(owner);
    OK
}
#[cfg(all(feature="fec2_product_record",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_game_group_kernel_counters(
    group:u64,copied:*mut u64,delivered:*mut u64,rejected:*mut u64,
)->i32{
    if copied.is_null()||delivered.is_null()||rejected.is_null(){return INVALID}
    let Ok(r)=registry().lock()else{return BAD_STAGE};
    let Some(e)=r.game_groups.get(&group)else{return UNKNOWN};
    if e.stopped{return BAD_STAGE}
    let Some(native)=e.drivers.as_ref()else{return BAD_STAGE};
    let (a,b,c)=native.counters();
    unsafe{copied.write(a);delivered.write(b);rejected.write(c)}
    OK
}

#[cfg(all(feature="fec2_product_record",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_game_group_rx_diagnostics(
    group:u64,raw_copied:*mut u64,auth_rejected:*mut u64,
)->i32{
    if raw_copied.is_null()||auth_rejected.is_null(){return INVALID}
    let Ok(r)=registry().lock()else{return BAD_STAGE};
    let Some(e)=r.game_groups.get(&group)else{return UNKNOWN};
    if e.stopped{return BAD_STAGE}
    let Some(driver)=e.drivers.as_ref()else{return BAD_STAGE};
    let (raw,auth)=driver.receive_diagnostics();
    unsafe{raw_copied.write(raw);auth_rejected.write(auth)}
    OK
}
#[cfg(feature="fec2_product_record")]
#[no_mangle]
pub extern "C" fn wbd_m0_embedded_go_game_group_release(group:u64)->i32{
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    let Some(e)=r.game_groups.get(&group)else{return UNKNOWN};
    if !e.stopped{return BAD_STAGE}
    // Native group cannot release a still-live protected Go lane. Original
    // per-lane M4/owner StopAndRelease is a separate hard requirement.
    let ids=e.handles.clone();
    for h in ids{
        let Some(cell)=r.entries.get(&h)else{continue};
        let Ok(guard)=cell.lock()else{return BAD_STAGE};
        if guard.phase!=PH_STOPPED{return BAD_STAGE}
    }
    r.game_groups.remove(&group);
    OK
}

fn release(handle:u64)->i32{
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_STOPPED{return BAD_STAGE}
    drop(e);
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    if r.entries.get(&handle).is_some_and(|x|Arc::ptr_eq(x,&cell)){
        r.entries.remove(&handle);
    }
    OK
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_prepare(
    cold:*const u8,cold_len:usize,cmd:*const u8,cmd_len:usize,out:*mut u64
)->i32{
    if cold.is_null()||cmd.is_null()||out.is_null()
        ||cold_len!=COLD_V4_LEN||cmd_len!=HANDOFF_V1_LEN{return INVALID}
    let cold=unsafe{std::slice::from_raw_parts(cold,cold_len)};
    let cmd=unsafe{std::slice::from_raw_parts(cmd,cmd_len)};
    match prepare(cold,cmd){Ok(h)=>{unsafe{out.write(h)};OK},Err(e)=>e}
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_prepare_client(
    cold:*const u8,cold_len:usize,cmd:*const u8,cmd_len:usize,out:*mut u64
)->i32{
    if cold.is_null()||cmd.is_null()||out.is_null()
        ||cold_len!=COLD_V4_LEN||cmd_len!=HANDOFF_V1_LEN{return INVALID}
    let cold=unsafe{std::slice::from_raw_parts(cold,cold_len)};
    let cmd=unsafe{std::slice::from_raw_parts(cmd,cmd_len)};
    match prepare_side(cold,cmd,false){
        Ok(h)=>{unsafe{out.write(h)};OK},Err(e)=>e
    }
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_stage(
    h:u64,seq:u32,data:*const u8,len:usize
)->i32{
    if data.is_null()||len==0||len>2048{return INVALID}
    let b=unsafe{std::slice::from_raw_parts(data,len)};
    stage(h,seq,b)
}
#[no_mangle]
pub extern "C" fn wbd_m0_embedded_go_commit(h:u64,n:u32,bytes:u32,tx:u32)->i32{
    commit(h,n,bytes,tx)
}
#[no_mangle]
pub extern "C" fn wbd_m0_embedded_go_abort(h:u64)->i32{abort(h)}
#[no_mangle]
pub extern "C" fn wbd_m0_embedded_go_stop(h:u64)->i32{stop(h)}
#[no_mangle]
pub extern "C" fn wbd_m0_embedded_go_release(h:u64)->i32{release(h)}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_state(h:u64,out:*mut u32)->i32{
    if out.is_null(){return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    unsafe{out.write(e.phase)};OK
}

//// Non-test public V4 original TLS owner counters. Only actual M4 copied
/// records and SAME original M3 authenticated reverse receipts may advance
/// these. No positive count from bootstrap ACK, queue acceptance, or Go caller.
#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_public_outer_counters(
    h:u64,out:*mut u64,n:usize
)->i32{
    if out.is_null()||n!=6{return INVALID}
    #[cfg(not(feature="fec2_product_record"))]
    {let _=h;BAD_STAGE}
    #[cfg(feature="fec2_product_record")]
    {
        let Ok(cell)=session(h)else{return UNKNOWN};
        let Ok(e)=cell.lock()else{return BAD_STAGE};
        if e.phase!=PH_ACTIVE{return BAD_STAGE}
        let Some(outer)=e.original_outer.as_ref()else{return BAD_STAGE};
        let Ok(v)=outer.lock()else{return BAD_STAGE};
        let vals=[v.sent_fresh,v.authentic_ack,v.repair_copied,
            v.repair_uncertain,v.repair_blocked,v.retired];
        unsafe{std::ptr::copy_nonoverlapping(vals.as_ptr(),out,6)}
        OK
    }
}
// Read-only slow-path recovery classifier, sampled once pre-Stop by the
// public CLI. No packet contents, identity, scheduler decision or mutation.
#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_public_outer_diagnostics(
    h:u64,out:*mut u64,n:usize
)->i32{
    if out.is_null()||n!=34{return INVALID}
    #[cfg(not(feature="fec2_product_record"))]
    {let _=h;BAD_STAGE}
    #[cfg(feature="fec2_product_record")]
    {
        let Ok(cell)=session(h)else{return UNKNOWN};
        let Ok(e)=cell.lock()else{return BAD_STAGE};
        if e.phase!=PH_ACTIVE{return BAD_STAGE}
        let Some(outer)=e.original_outer.as_ref()else{return BAD_STAGE};
        let Ok(v)=outer.lock()else{return BAD_STAGE};
        let d=v.shadow.diagnostic_snapshot();
        let Some(t)=v.shadow.timing_snapshot()else{return BAD_STAGE};
        let vals=[
            d.candidate_first,d.candidate_retry,
            d.acked_attempt0,d.acked_attempt1,d.acked_attempt2,
            d.expired_attempt0,d.expired_attempt1,d.expired_attempt2,
            d.late_positive_expired,
            t.samples,t.srtt_ns/1_000,t.rttvar_ns/1_000,t.recent_rtt_ns/1_000,
            t.reorder_window_ns/1_000,t.pto_ns/1_000,t.cache_ns/1_000,
            v.shadow.outstanding() as u64,
            v.block_reasons[0],v.block_reasons[1],v.block_reasons[2],
            v.block_reasons[3],v.block_reasons[4],v.block_reasons[5],
            v.block_reasons[6],v.block_reasons[7],v.block_reasons[8],
            v.block_reasons[9],
            d.repair_accepted_retired,d.repair_uncertain_retired,
            d.repair_abandoned_retired,d.max_queue_age_ns/1_000,
            v.shadow.policy_limits().0,v.shadow.policy_limits().1 as u64,
            v.shadow.policy_limits().2/1_000,
        ];
        unsafe{std::ptr::copy_nonoverlapping(vals.as_ptr(),out,34)}
        // A single read-only per-generation marker before Stop; counts are
        // RX-owner only, batched atomics, not an ACK or business qualification.
        let rx=&e.counters.rx_chain;
        let snapshot:Vec<u64>=rx.iter().map(|n|n.load(Ordering::Relaxed)).collect();
        let feedback=e.rx_feedback.as_ref()
            .and_then(|f|f.lock().ok().map(|g|(
                g.retained_pages() as u64,g.feedback_drop()
            ))).unwrap_or((0,0));
        eprintln!(
            "V4_PUBLIC_RX_CHAIN role={} raw_observed={} raw_tuple={} data_unique={} data_lagged32={} link_completed={} tun_delivered={} link_pending={} link_malformed={} link_discarded={} tun_failed={} replay_duplicate={} replay_retired={} open_invalid={} feedback_retained_pages={} feedback_dropped={} tun_udp={} tun_tcp={} tun_other={}",
            if e.server_side{"server"}else{"client"},
            snapshot[0],snapshot[1],snapshot[2],snapshot[3],
            snapshot[4],snapshot[5],snapshot[6],snapshot[7],
            snapshot[8],snapshot[9],snapshot[10],snapshot[11],snapshot[12],
            feedback.0,feedback.1,snapshot[13],snapshot[14],snapshot[15]);
        let tx=&e.counters.tx_chain;
        let t:Vec<u64>=tx.iter().map(|n|n.load(Ordering::Relaxed)).collect();
        eprintln!(
            "V4_PUBLIC_TX_CHAIN role={} tun_udp={} tun_tcp={} tun_other={} tun_rejected={} arena_failed={} staged_udp={} staged_tcp={} pre_read_deferred={}",
            if e.server_side{"server"}else{"client"},
            t[0],t[1],t[2],t[3],t[4],t[5],t[6],t[7]);
        eprintln!(
            "V4_PUBLIC_M1_POOL role={} slots={} peak_loaned={} charged_bytes={} normal_control_reserve={}",
            if e.server_side{"server"}else{"client"},
            e.arena.capacity(),e.arena.peak_loaned(),e.arena.charged_bytes(),
            if e.rx_feedback.is_some() && e.fixed_pending.is_none()
                && e.fixed_applied.is_none(){16}else{0});
        OK
    }
}
// Pure read-only original FixedStream owner snapshot, taken once pre-Stop.
// No per-packet observations, no cryptographic or queue authority.
// ABI: accepted,notready,full,partial,k1,k2..4,k5..12,k13..16,
// planned,confirmed,expired,pressure_jobs,pressure_sources,capacity_unknown.
#[cfg(all(feature="fec2_product_record",target_os="linux",
    any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn original_fec_tx_snapshot(r:crate::runtime::fec2_owner::OwnerReport)->[u64;14]{
    let mut v=[0u64;14];
    for st in &r.classes{
        v[0]+=st.accepted;v[1]+=st.source_not_ready;
        v[2]+=st.full;v[3]+=st.partial;
        v[4]+=st.k_hist[1];
        v[5]+=st.k_hist[2..=4].iter().sum::<u64>();
        v[6]+=st.k_hist[5..=12].iter().sum::<u64>();
        v[7]+=st.k_hist[13..=16].iter().sum::<u64>();
        v[8]+=st.r_planned;v[9]+=st.r_sent;
        v[10]+=st.expired_jobs;v[11]+=st.pressure_jobs;
        v[12]+=st.pressure_sources;v[13]+=st.unknown_capacity;
    }
    v
}
#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_public_fec2_tx_snapshot(
    h:u64,out:*mut u64,n:usize
)->i32{
    if out.is_null()||n!=14{return INVALID}
    #[cfg(not(feature="fec2_product_record"))]
    {let _=h;BAD_STAGE}
    #[cfg(feature="fec2_product_record")]
    {
        let Ok(cell)=session(h)else{return UNKNOWN};
        let Ok(e)=cell.lock()else{return BAD_STAGE};
        if e.phase!=PH_ACTIVE||e.workers.is_none(){return BAD_STAGE}
        let Some(stream)=e.fec2_live_tx.as_ref()else{return BAD_STAGE};
        let v=original_fec_tx_snapshot(stream.report());
        unsafe{std::ptr::copy_nonoverlapping(v.as_ptr(),out,14)}
        OK
    }
}
// Side-band read-only reason ledger; FEC source/repair failure paths only.
// Eight u64 are unambiguous and scoped to original active generation.
#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_public_fec2_tx_failures(
    h:u64,out:*mut u64,n:usize
)->i32{
    if out.is_null()||n!=8{return INVALID}
    #[cfg(not(feature="fec2_product_record"))]
    {let _=h;BAD_STAGE}
    #[cfg(feature="fec2_product_record")]
    {
        let Ok(cell)=session(h)else{return UNKNOWN};
        let Ok(e)=cell.lock()else{return BAD_STAGE};
        if e.phase!=PH_ACTIVE||e.workers.is_none(){return BAD_STAGE}
        if e.fec2_live_tx.is_none(){return BAD_STAGE}
        unsafe{std::ptr::copy_nonoverlapping(e.fec2_fail_reasons.as_ptr(),out,8)}
        OK
    }
}
// Bind genuine public original-Go V4 TLS session to the SAME original
/// Rust M1/M3/M4 kernel receive -> authenticated M2 feedback -> TX worker.
/// This is a mode authorization, NOT a separate data plane or self-attested
/// epoch: generation handle already required private protected Go Prepare,
/// actual FakeTCP Detach/Commit, and original TX/RX owner activation.
#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_arm_public_original_m2_feedback(
    h:u64,epoch_ptr:*const u8,epoch_len:usize
)->i32{
    #[cfg(not(feature="fec2_product_record"))]
    {let _=(h,epoch_ptr,epoch_len);BAD_STAGE}
    #[cfg(feature="fec2_product_record")]
    {
        let Ok(epoch)=verified_normal_off_epoch(epoch_ptr,epoch_len)else{return INVALID};
        let Ok(cell)=session(h)else{return UNKNOWN};
        let Ok(mut e)=cell.lock()else{return BAD_STAGE};
        if !verified_normal_off_owner(&e,&epoch)||
            e.workers.is_some()||e.original_public_feedback_armed||
            e.raw_rx.is_none()||e.tun_sink.is_none()||
            e.raw_ifname.is_none(){return BAD_STAGE}
        e.original_public_feedback_armed=true;
        OK
    }
}

// The same non-_test Go-verified owner now owns BOTH actual M4 device
// handles. No shadow/test engine, no alternate AEAD/PN or delivery route.
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn attach_raw(handle:u64,ifindex:u32,ifname:&str)->i32{
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.raw_rx.is_some(){return BAD_STAGE}
    let Ok(driver)=ScopedRawIpv4Rx::open(ifname,ifindex,(handle>>32) as u32)
    else{return INVALID};
    e.raw_rx=Some(Arc::new(driver));
    e.raw_ifname=Some(ifname.to_owned());OK
}
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn attach_tun(handle:u64,fd:i32,name:&str)->i32{
    if fd<3{return INVALID}
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.tun_sink.is_some(){return BAD_STAGE}
    // Borrow only for dup(): Rust owns its duplicate, Go owns original FD.
    let Ok(dup)=unsafe{BorrowedFd::borrow_raw(fd)}.try_clone_to_owned()
    else{return INVALID};
    let Ok(tun)=ScopedTunSink::from_owned_fd(dup,(handle>>32) as u32,name)
    else{return INVALID};
    e.tun_sink=Some(Arc::new(tun));OK
}
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn raw_to_tun(handle:u64)->Result<(u32,u32),i32>{
    let cell=session(handle)?;
    let mut guard=cell.lock().map_err(|_|BAD_STAGE)?;
    let e:&mut Entry=&mut guard;
    if e.phase!=PH_ACTIVE||e.workers.is_some(){return Err(BAD_STAGE)}
    let raw=e.raw_rx.as_ref().ok_or(BAD_STAGE)?;
    let tun=e.tun_sink.as_ref().ok_or(BAD_STAGE)?;
    let f=e.flow;
    let tuple=Ipv4Tuple{
        src_ip:&f.client_ip,dst_ip:&f.server_ip,
        src_port:f.client_port,dst_port:f.server_port,
    };
    let slab=e.arena.allocate().map_err(|_|FULL)?;
    e.owner.receive_scoped_raw_into_owner(
        raw,slab,tuple,PacketPersona::Legacy,
        u64::from(e.rx_boundary),MonoNs(0),
    ).map_err(|_|INVALID)?;
    let normal=e.normal.as_mut().ok_or(BAD_STAGE)?;
    let (returned,report,delivered,failed)=e.owner.drain_normal_off_to_tun(
        normal,tun,MonoNs(0),Vec::with_capacity(32),
    ).map_err(|_|BAD_STAGE)?;
    drop(returned);
    e.arena.drain_returns();
    // A valid authenticated fragment is deliberately NOT a business packet.
    // Keep the M3 reassembly slot for the next raw record; pending must never
    // write a partial IP datagram to TUN or be counted as a failed delivery.
    if report.authenticated.link_ready!=1 || failed!=0 || report.malformed!=0
        || report.discarded!=0{return Err(INVALID)}
    if report.completed==1 && delivered==1 && report.pending==0{
        return Ok((delivered,failed))
    }
    if report.pending==1 && report.completed==0 && delivered==0{
        return Ok((0,0))
    }
    Err(INVALID)
}
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub extern "C" fn wbd_m0_embedded_go_attach_raw_rx(h:u64,ifindex:u32)->i32{
    // Existing exact-source developer ABI retained unchanged.
    attach_raw(h,ifindex,"lo")
}
/// Real product interface is bound ONCE to the same credential-verified Go
/// generation. M4 opens the real kernel socket and checks ifname+ifindex.
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_attach_raw_rx_on_interface(
    h:u64,ifindex:u32,name:*const u8,len:usize
)->i32{
    if name.is_null()||len==0||len>15{return INVALID}
    let bytes=unsafe{std::slice::from_raw_parts(name,len)};
    let Ok(ifname)=std::str::from_utf8(bytes)else{return INVALID};
    attach_raw(h,ifindex,ifname)
}
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_attach_tun(
    h:u64,fd:i32,name:*const u8,len:usize
)->i32{
    if name.is_null()||len==0||len>15{return INVALID}
    let raw=unsafe{std::slice::from_raw_parts(name,len)};
    let Ok(name)=std::str::from_utf8(raw)else{return INVALID};
    attach_tun(h,fd,name)
}
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_raw_to_tun(
    h:u64,out_ok:*mut u32,out_failed:*mut u32
)->i32{
    if out_ok.is_null()||out_failed.is_null(){return INVALID}
    match raw_to_tun(h){
        Ok((ok,failed))=>{unsafe{out_ok.write(ok);out_failed.write(failed)};OK}
        Err(e)=>e,
    }
}


/// Reverse app path using SAME protected generation, non-_test normal Rust
/// LINK AEAD/PN, and real Linux M4 ScopedTunSink/ScopedRawIpv4Tx objects.
/// One trusted Go session tuple and original Tx boundary; never resynthesize
/// keys/seq/PN in the FFI or in Go. Driver is retained through Stop.
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn tun_to_raw(handle:u64,ifindex:u32)->Result<(u64,u32,u32,u32),i32>{
    let cell=session(handle)?;
    let mut guard=cell.lock().map_err(|_|BAD_STAGE)?;
    let e:&mut Entry=&mut guard;
    if e.phase!=PH_ACTIVE||e.workers.is_some(){return Err(BAD_STAGE)}
    let ifname=e.raw_ifname.clone().ok_or(BAD_STAGE)?;
    let tun=e.tun_sink.as_ref().ok_or(BAD_STAGE)?;
    let flow=e.flow;
    let server=e.server_side;
    if e.raw_tx.is_none(){
        let driver=ScopedRawIpv4Tx::open(&ifname,ifindex,(handle>>32) as u32)
            .map_err(|_|INVALID)?;
        let observed=wbd_platform::linux_packet_preflight::observe_interface_mtu(
            &ifname,ifindex).map_err(|_|INVALID)?;
        e.raw_tx_lease_mtu=observed.kernel_mtu;
        e.raw_tx=Some(Arc::new(driver));
    }
    let route=e.owner.observe_linux_normal_off_route_budget(
        &ifname,ifindex,Ipv4Addr::from(
            if server{flow.client_ip}else{flow.server_ip}
        )
    ).map_err(|_|INVALID)?;
    let slab=e.arena.allocate().map_err(|_|FULL)?;
    let (pn,seq,_wire_len,app_len)=e.owner.seal_tun_ipv4_normal_off(
        tun,slab,&route,15,MonoNs(0)
    ).map_err(|_|INVALID)?;
    let raw=e.raw_tx.as_ref().ok_or(BAD_STAGE)?;
    let tuple=if server{Ipv4Tuple{
        src_ip:&flow.server_ip,dst_ip:&flow.client_ip,
        src_port:flow.server_port,dst_port:flow.client_port,
    }}else{Ipv4Tuple{
        src_ip:&flow.client_ip,dst_ip:&flow.server_ip,
        src_port:flow.client_port,dst_port:flow.server_port,
    }};
    let presentation=Presentation{
        ack32:1,advertised_window:4096,ip_id:43,
        persona:PacketPersona::Legacy,
    };
    let full=e.owner.submit_scoped_raw_tx(raw,tuple,presentation,MonoNs(0))
        .map_err(|_|BAD_STAGE)?;
    e.arena.drain_returns();
    Ok((pn,seq,u32::try_from(full).map_err(|_|INVALID)?,
        u32::try_from(app_len).map_err(|_|INVALID)?))
}
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_tun_to_raw(
    handle:u64,ifindex:u32,pn:*mut u64,seq:*mut u32,
    packet_len:*mut u32,app_len:*mut u32,
)->i32{
    if pn.is_null()||seq.is_null()||packet_len.is_null()||
        app_len.is_null(){return INVALID}
    match tun_to_raw(handle,ifindex){
        Ok((p,s,wire,app))=>{
            unsafe{pn.write(p);seq.write(s);
                packet_len.write(wire);app_len.write(app)};
            OK
        }
        Err(e)=>e,
    }
}


// Development-only perpetual owner processing, never a parallel crypto
// implementation. Two independent Rust kernel-readiness threads; Go app
// sender and receiver do not call per-packet RX/TX helpers. The READY poll
// is outside the shared registry lock. Subsequent owner admission, AEAD/PN,
// Normal/off and kernel driver send use the exact existing Rust functions.
// Unrelated raw TCP is discarded by M4; RX's actual mutable opener/PN,
// reassembly and arena belong to RX alone after Go Detach, not Entry.
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[repr(C)]
struct PollFd {fd:c_int,events:i16,revents:i16}
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
unsafe extern "C" {fn poll(fds:*mut PollFd,count:usize,timeout:c_int)->c_int;}
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[derive(Default)]
struct LoopCounts {
    rx:AtomicU64,tx:AtomicU64,rx_error:AtomicU64,tx_error:AtomicU64,
    tx_dropped:AtomicU64,tx_uncertain:AtomicU64,tx_backpressure:AtomicU64,
    route_refresh:AtomicU64,
    rx_thread_cpu_ns:AtomicU64,tx_thread_cpu_ns:AtomicU64,
    #[cfg(feature="fec2_product_record")]
    fec_rx:[AtomicU64;11],
    #[cfg(feature="fec2_product_record")]
    fec_rx_ip:[AtomicU64;8],
    // Genuine M1 TUN intake: read IPv4, small owner loan, owner
    // NoCapacity, jumbo, rejected. No packet contents or endpoint logs.
    #[cfg(feature="fec2_product_record")]
    fec_m1_ingress:[AtomicU64;5],
    // Original feature7 post-TUN-loan Fixed stage outcomes: attempted,
    // first_copy_queued, owner_not_ready, stage_error, over_budget,
    // mode_skipped. Only per-session numeric counters, not packet data.
    #[cfg(feature="fec2_product_record")]
    fec_m1_stage:[AtomicU64;6],
    // RX chain aggregates (normal/off) updated per <=32-record kernel batch:
    // observed, tuple, unique, lagged_unique, LINK complete, TUN delivery,
    // pending, malformed, discarded, TUN failed, replay duplicate,
    // replay retired, AEAD/record invalid. No packet identifiers leave owner.
    #[cfg(feature="fec2_product_record")]
    rx_chain:[AtomicU64;16],
    // Real TUN IPv4 ingress classifications and successful immutable
    // Normal/off source staging, batched once per worker turn.
    // UDP,TCP,other,rejected,postread_arena_failed,staged_UDP,
    // staged_TCP,pre_read_deferred (NOT consumed or dropped).
    #[cfg(feature="fec2_product_record")]
    tx_chain:[AtomicU64;8],
    // M0 developer-only deterministic barrier between 32-slot real kernel
    // turns. Never compiled into ordinary FEC2-OFF production builds.
    debug_pause_jumbo:AtomicBool,debug_jumbo_paused:AtomicBool,
}
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
struct LoopWorkers{
    shutdown:Arc<AtomicBool>,
    rx:JoinHandle<()>,
    tx:JoinHandle<()>,
    route_events:Arc<wbd_platform::linux_route_events::RouteEvents>,
}
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[repr(C)]
struct ClockTimespec {seconds:i64,nanoseconds:i64}
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
unsafe extern "C" {
    fn clock_gettime(clock_id:c_int,raw:*mut ClockTimespec)->c_int;
}
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn owner_thread_cpu_ns()->u64{
    let mut sample=ClockTimespec{seconds:0,nanoseconds:0};
    // Linux CLOCK_THREAD_CPUTIME_ID=3, measures ONLY this original Rust
    // worker's CPU, excluding Go injector/receiver goroutines and sleeps.
    if unsafe{clock_gettime(3,&mut sample)}!=0{return 0}
    u64::try_from(sample.seconds).unwrap_or(0).saturating_mul(1_000_000_000)
        .saturating_add(u64::try_from(sample.nanoseconds).unwrap_or(0))
}
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn loop_now()->MonoNs{
    static START:OnceLock<Instant>=OnceLock::new();
    MonoNs(START.get_or_init(Instant::now).elapsed().as_nanos().min(u64::MAX as u128) as u64)
}
// Bounded M1 arena return servicing inside one authenticated DATA turn.
// Only Stop/report/quiescence/control paths may drain every outstanding item;
// an arbitrarily long backlog must not monopolize the per-session TX/RX lock.
// Arena::allocate already drains at most 64 before making a new loan.
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
const M0_DATA_RETURN_TURN_CAP:usize=64;
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn drain_data_turn_returns(arena:&mut Arena)->usize{
    arena.drain_returns_bounded(M0_DATA_RETURN_TURN_CAP)
}

// Do not hold global registry lock while M4 RX preflight ignores unrelated
// RST/ACK or polls for up to 750ms. M4 receives directly into the already
// allocated ORIGINAL M1 UniqueBuffer via recvmmsg and checks trusted tuple and
// TCP checksum. On reentry the ONLY decrypt/PN/LINK/TUN path is the original
// Rust ScopedOwner. Stop joins worker before owner/slab/driver retirement.
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
// Only a successfully authenticated (AEAD and unique PN) Normal/off LINK
// admission may advance the seq32 reference. A raw TCP tuple/checksum/seq
// is not proof: an attacker could otherwise jump the 64-bit high-water mark.
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn authenticated_rx_anchor(anchor:u64,absolute_seq:u64,wire_len:usize,
    admitted_link:u32)->Option<u64>{
    if admitted_link!=1{return Some(anchor)}
    let end=absolute_seq.checked_add(u64::try_from(wire_len).ok()?)?;
    Some(anchor.max(end))
}
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn background_raw_once(
    owner:&mut crate::v4_owner_crypto::ProtectedBackgroundRx,
    arena:&mut Arena,anchor:&mut u64,
    flow:crate::v4_protected_handoff::GoFlow,generation:u32,
    server_side:bool,
    raw:&ScopedRawIpv4Rx,tun:&ScopedTunSink,stop:&AtomicBool,
    rx_pending:&mut Vec<crate::memory::UniqueBuffer>,
    mature:&Arc<Mutex<NormalFirstSendM2>>,
    #[cfg(feature="fec2_product_record")]
    fec_stats:&LoopCounts,
    #[cfg(feature="fec2_product_record")]
    feedback:Option<&Arc<Mutex<wbd_recovery::RxFeedbackState>>>,
    #[cfg(feature="fec2_product_record")]
    outer:Option<&Arc<Mutex<OriginalOuterRepair>>>,
)->Result<u32,i32>{
    // The SAME original Go credential-derived AEAD+PN opener and M3 LINK
    // table are now owned by RX, not re-initialized or cloned. RX never
    // locks Entry / TX during normal packets, ready or Stop detection.
    while rx_pending.len()<32{
        match arena.allocate(){
            Ok(slab)=>rx_pending.push(slab),
            Err(_)=>break,
        }
    }
    if rx_pending.is_empty(){return Err(FULL)}
    let tuple=if server_side{Ipv4Tuple{
        src_ip:&flow.client_ip,dst_ip:&flow.server_ip,
        src_port:flow.client_port,dst_port:flow.server_port,
    }}else{Ipv4Tuple{
        src_ip:&flow.server_ip,dst_ip:&flow.client_ip,
        src_port:flow.server_port,dst_port:flow.client_port,
    }};
    let slot_count=rx_pending.len();
    let mut slots:[&mut [u8];32]=std::array::from_fn(|_|&mut [][..]);
    for (dst,slab) in slots.iter_mut().zip(rx_pending.iter_mut()){
        *dst=slab.writable();
    }
    let batch=raw.receive_kernel_multimsg(
        generation,&mut slots[..slot_count],tuple,PacketPersona::Legacy
    ).map_err(|_|INVALID)?;
    drop(slots);
    if stop.load(Ordering::Acquire){return Err(BAD_STAGE)}
    if batch.observed==0{return Err(INVALID)}
    let mut delivered_total=0u32;
    #[cfg(feature="fec2_product_record")]
    let mut rx_chain_batch=[0u64;16];
    #[cfg(feature="fec2_product_record")]
    {rx_chain_batch[0]=batch.observed as u64;}
    #[cfg(feature="fec2_product_record")]
    let mut fec_batch=[0u64;11];
    #[cfg(feature="fec2_product_record")]
    let mut fec_ip_batch=[0u64;8];
    let mut pending_valid=false;
    let mut invalid_seen=false;
    let mut authenticated_control=false;
    // Unused preposted original M1 slabs persist in this RX worker; used
    // ones return through the same bounded per-arena return path.
    for (i,slab) in rx_pending.drain(..batch.observed).enumerate(){
        let (len,seq)=match batch.entry(i){
            Some(wbd_platform::linux_raw_carrier::RawReadyEntry::Unauthenticated{
                cipher_len,seq32
            })=>(cipher_len,seq32),
            _=>{drop(slab);continue},
        };
        if stop.load(Ordering::Acquire){break}
        #[cfg(feature="fec2_product_record")]
        {rx_chain_batch[1]+=1;}
        let absolute=match extend_seq32(*anchor,seq){
            Ok(n)=>n,Err(_)=>{drop(slab);continue}
        };
        // Exactly one actual M3 opener and unique replay PN bitmap.
        let when=loop_now();
        let receipt=owner.consume_original(slab,len,tun,when);
        #[cfg(feature="fec2_product_record")]
        {
            let items=[
                0,0,receipt.normal_unique,receipt.normal_late_unique,
                receipt.normal_completed,receipt.delivered,receipt.pending,
                receipt.normal_malformed,receipt.normal_discarded,
                receipt.failed,receipt.open_duplicate,
                receipt.open_retired,receipt.open_invalid,
                receipt.normal_udp_delivered,
                receipt.normal_tcp_delivered,
                receipt.normal_other_delivered,
            ];
            for (v,n) in rx_chain_batch.iter_mut().zip(items){
                *v+=u64::from(n);
            }
        }
        #[cfg(feature="fec2_product_record")]
        for (dst,n) in fec_batch.iter_mut().zip(receipt.fec_rx.iter()){
            *dst=dst.saturating_add(u64::from(*n));
        }
        #[cfg(feature="fec2_product_record")]
        for (dst,n) in fec_ip_batch.iter_mut().zip(receipt.fec_rx_ip.iter()){
            *dst=dst.saturating_add(u64::from(*n));
        }
        let Some(next)=authenticated_rx_anchor(
            *anchor,absolute,len,receipt.authenticated_link
        )else{continue};
        *anchor=next;
        pending_valid |=receipt.pending>0;
        invalid_seen |=receipt.invalid>0 || receipt.failed>0;
        // The one unique authenticated M3 opener is the ONLY input to
        // first-delivery M2 feedback. Raw tuple/seq, FEC parity guess or
        // a replayed PN can never fabricate an ACK.
        #[cfg(feature="fec2_product_record")]
        if let (Some(feedback),Some(pn))=(feedback,receipt.authenticated_data_pn){
            if let Ok(mut state)=feedback.lock(){
                state.on_authenticated_data(wbd_types::RecordPn(pn),when);
            }else{invalid_seen=true}
        }
        if let Some(control)=receipt.reverse_kind1{
            // RX never locks Entry/TX and never holds a driver slab after
            // opener returns. Shared M2 state is one bounded mutex.
            if stop.load(Ordering::Acquire){break}
            match mature.lock(){
                Ok(mut first)=>{
                    if let Ok(scoped)=first.on_original_authenticated_reverse(control,when){
                        authenticated_control=true;
                        // The SAME original TLS-bound authenticated control
                        // retires frozen M2 shadows; TCP ACK is never trust.
                        #[cfg(feature="fec2_product_record")]
                        if let Some(shared)=outer {
                            match shared.lock(){
                                Ok(mut active)=>{
                                    let dir=active.direction;
                                    let result=original_process_repair_quota().lock()
                                        .map_err(|_|BAD_STAGE)
                                        .and_then(|mut global|
                                            global.observe_scoped_receipt(
                                                dir,&mut active.shadow,&scoped,when
                                            ).map_err(|_|BAD_STAGE)
                                        );
                                    match result{
                                        Ok(released)=>{
                                            active.authentic_ack=active.authentic_ack
                                                .saturating_add(released.len() as u64);
                                            active.retired=active.retired
                                                .saturating_add(released.len() as u64);
                                        },
                                        Err(_)=>invalid_seen=true,
                                    }
                                },
                                Err(_)=>invalid_seen=true,
                            }
                        }
                    }else{invalid_seen=true;}
                },
                Err(_)=>invalid_seen=true,
            }
        }
        if receipt.failed==0{
            delivered_total=delivered_total.saturating_add(receipt.delivered);
        }
    }
    #[cfg(feature="fec2_product_record")]
    for (dst,n) in fec_stats.rx_chain.iter().zip(rx_chain_batch){
        if n>0{dst.fetch_add(n,Ordering::Relaxed);}
    }
    #[cfg(feature="fec2_product_record")]
    for (dst,n) in fec_stats.fec_rx.iter().zip(fec_batch){
        if n>0{dst.fetch_add(n,Ordering::Relaxed);}
    }
    #[cfg(feature="fec2_product_record")]
    for (dst,n) in fec_stats.fec_rx_ip.iter().zip(fec_ip_batch){
        if n>0{dst.fetch_add(n,Ordering::Relaxed);}
    }
    arena.drain_returns_bounded(M0_DATA_RETURN_TURN_CAP);
    // A unique authenticated LINK shard with no completed datagram is
    // healthy progress, not a spurious RX error. A malformed/discarded shard
    // must still register an error even if another pending shard was valid.
    if invalid_seen || (delivered_total==0 && !pending_valid && !authenticated_control){
        return Err(INVALID)
    }
    Ok(delivered_total)
}
// The actual peer ACK is generated only from original M3 authenticated,
// unique RX PNs. Exactly the SAME original TX AEAD/PN, M1 frozen buffer queue
// and M4 sendmmsg dispatch carries this kind1 receipt, including idle time.
// The queued draft is terminally settled ONLY from actual kernel copied /
// uncertain / definitely-not-sent evidence. Never fabricate a peer ACK.
#[cfg(all(feature="fec2_product_record",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn stage_original_reverse_feedback(e:&mut Entry,now:MonoNs)->Result<bool,i32>{
    if e.feedback_queued.is_some(){return Ok(false)}
    let Some(feedback)=e.rx_feedback.as_ref().map(Arc::clone)
        else{return Ok(false)};
    let mut rx=feedback.lock().map_err(|_|BAD_STAGE)?;
    let Some(draft)=rx.on_due(now)else{return Ok(false)};
    let attempt=(||->Result<u64,i32>{
        let msg=wbd_codec::Receipt{
            largest_data_pn:draft.largest_data_pn().0,ack_delay_us:0,
            report_seq:draft.report_seq(),
            pages:draft.pages().iter().map(|p|wbd_codec::ReceiptPage{
                base_pn:p.base_pn.0,bitmap:p.bitmap,
            }).collect(),
        };
        let tlv=wbd_codec::encode_control(
            &[wbd_codec::ControlTlv::Receipt(msg)],512
        ).map_err(|_|INVALID)?;
        let budget=e.tx_route.as_ref().ok_or(BAD_STAGE)?.scoped.frame;
        let slab=e.arena.allocate().map_err(|_|FULL)?;
        let (pn,_,_)=e.owner.seal_original_authenticated_receipt(
            slab,&tlv,budget,15,now
        ).map_err(|_|BAD_STAGE)?;
        Ok(pn)
    })();
    match attempt{
        Ok(pn)=>{
            e.feedback_queued=Some((draft,pn));
            Ok(true)
        },
        Err(err)=>{
            let _=rx.on_send_result(
                &draft,wbd_recovery::FeedbackSendResult::NotSent,now
            );
            Err(err)
        }
    }
}
// Independently wait for the REAL TUN application RX OUTSIDE registry lock.
// Only original owner grants route-bound budget, seals AEAD/PN and submits
// original frozen M1 record through genuine scoped M4 raw TX.
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[derive(Debug,Default,Clone,Copy,Eq,PartialEq)]
struct TxTurnCompletion{
    copied:u32,definitely_unsent:u32,uncertain:u32,
    backpressure:bool,failed:bool,invalidate_route:bool,
}
// The only completion translation on the original authenticated TX path.
// Exactly the kernel-copied prefix counts, the untouched suffix is dropped
// by the existing bounded owner drain; an uncertain record is NEVER retried.
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn classify_tx_turn(report:Option<&wbd_platform::linux_batch::KernelSendReport>,
    ready:usize,seal_failed:bool)->TxTurnCompletion{
    use wbd_platform::linux_batch::KernelSendSignal as S;
    let sent=report.map_or(0,|r|r.outcome.accepted_prefix.min(ready));
    let uncertain=usize::from(report.is_some_and(|r|
        r.outcome.uncertain_index==Some(sent) && sent<ready));
    let failed=seal_failed || report.is_none_or(|r|
        r.outcome.error.is_some()||r.signal!=S::None||sent!=ready);
    TxTurnCompletion{
        copied:sent as u32,
        definitely_unsent:ready.saturating_sub(sent+uncertain) as u32,
        uncertain:uncertain as u32,
        backpressure:report.is_some_and(|r|r.signal==S::Backpressure),
        failed,
        // Path/device/actual MTU exception only. Ordinary EAGAIN, partial
        // errno-unavailable, or uncertain completion says nothing definite
        // about route change; per-record preflight rejects never invalidate.
        invalidate_route:report.is_some_and(|r|matches!(r.signal,
            S::RouteUnavailable|S::DeviceUnavailable|S::MtuExceeded)),
    }
}
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn raw_driver_reopen_on_route_change(
    has_cache:bool,previous_refresh_count:u64,observed_mtu:u32,lease_mtu:u32
)->bool{
    // A genuine 65536->1500 MTU shrink MUST continue to reject this
    // authenticated generation, even if the smaller packet would fit.
    // Only after M4 has actually failed and M0 invalidated its route cache,
    // and the trusted kernel observation has recovered to the original
    // lease capacity, may this owner install a fresh same-generation FD.
    !has_cache && previous_refresh_count!=0 && lease_mtu!=0
        && observed_mtu>=lease_mtu
}

#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
const M0_TUN_IPV4_MAX:usize=65_535;
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
const M0_SMALL_ARENA_PAYLOAD:usize=2048-14;
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
const M0_MAX_PENDING_JUMBO:usize=4;
#[cfg(all(feature="fec2_product_record",
    any(target_arch="x86_64",target_arch="aarch64"),
    any(target_env="gnu",target_env="musl")))]
const M0_NORMAL_FEEDBACK_SLAB_RESERVE:usize=16;

// The sole background TX worker owns this logical packet. No self-referential
// borrowed plan crosses worker calls: rehydrate M3's immutable planner and
// skip previously ISSUED indices without ever resealing or resending them.
// Every failed/uncertain turn discards the remaining source and reserves
// the old ID forever within this generation. Bound retained jumbo memory
// to four complete IPv4 datagrams plus one currently active plan.
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
struct PendingOriginalJumbo{
    source:Vec<u8>,packet_id:u32,frame_mtu:usize,
    issued:usize,total:usize,generation:u32,route_event_revision:u64,
}
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
impl PendingOriginalJumbo{
    fn new(source:Vec<u8>,packet_id:u32,frame_mtu:usize,
        generation:u32,route_event_revision:u64)->Result<Self,i32>{
        if source.len()<=M0_SMALL_ARENA_PAYLOAD
            || source.len()>M0_TUN_IPV4_MAX{return Err(INVALID)}
        let plan=LinkPacketPlan::new(&source,frame_mtu,LinkMode::FixedOff,packet_id)
            .map_err(|_|INVALID)?;
        let total=plan.total_frames();
        if total<=1{return Err(INVALID)}
        Ok(Self{source,packet_id,frame_mtu,issued:0,total,
            generation,route_event_revision})
    }
    fn done(&self)->bool{self.issued==self.total}
    // One authenticated generation and one original LINK stride own every
    // frame of this packet. A route revision, including MTU +1, is terminal:
    // never silently continue an old packet ID in a new route scope.
    fn valid_for(&self,generation:u32,route_event_revision:u64,
        frame_mtu:usize)->bool{
        self.generation==generation
            && self.route_event_revision==route_event_revision
            && self.frame_mtu==frame_mtu
    }
    // The original M4 kernel copies at most a definite prefix. After any
    // partial, ambiguous, Stop or route invalidation the remaining immutable
    // LINK tail MUST NOT acquire fresh PN or be sent under the same packet ID.
    fn retire_after_turn(&self,completion:TxTurnCompletion,stopping:bool)->bool{
        stopping || self.done() || completion.failed
            || completion.uncertain!=0 || completion.definitely_unsent!=0
            || completion.invalidate_route
    }
    fn stage_turn(&mut self,arena:&mut Arena,current_frame_mtu:usize,
        available:usize)->Result<Vec<(crate::memory::UniqueBuffer,usize)>,i32>{
        let mut plan=LinkPacketPlan::new(
            &self.source,self.frame_mtu,LinkMode::FixedOff,self.packet_id
        ).map_err(|_|INVALID)?;
        for _ in 0..self.issued{
            // Reconstituting the immutable cursor is not new network output.
            // Past frames are thrown away, NEVER granted a PN or M4 loan.
            plan.issue_next(self.frame_mtu).map_err(|_|INVALID)?
                .ok_or(INVALID)?;
        }
        let parts=stage_next_original_link_turn(
            arena,&mut plan,current_frame_mtu,available
        )?;
        self.issued=plan.issued();
        Ok(parts)
    }
}

// The original M1 arena holds ALL slabs for one LINK packet BEFORE the
// first original owner AEAD/PN/Seq and TX admission. On any bad stride,
// capacity shortage or invalid packet ID the local Vec drops every slab;
// no partial packet is ever queued due to fragment materialization failure.
// This remains a bounded 32-record SAME-turn staging step, NOT yet 64KiB
// cross-turn scheduling or atomic kernel sendmmsg completion.
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn stage_bounded_original_link(
    arena:&mut Arena, source:&[u8],frame_mtu:usize,
    packet_id:u32,available_records:usize
)->Result<Vec<(crate::memory::UniqueBuffer,usize)>,i32>{
    let mut plan=LinkPacketPlan::new(
        source,frame_mtu,LinkMode::FixedOff,packet_id
    ).map_err(|_|INVALID)?;
    let count=plan.total_frames();
    if count==0 || count>available_records || count>32{return Err(FULL)}
    let staged=stage_next_original_link_turn(
        arena,&mut plan,frame_mtu,available_records
    )?;
    if staged.len()!=count || plan.issued()!=count
        || plan.issue_next(frame_mtu).map_err(|_|INVALID)?.is_some(){
        return Err(INVALID)
    }
    Ok(staged)
}

// M0 incremental integration: original M1 arena/loan plus original M3
// LINK20 planner stage ONE bounded owner turn of a >32-frame packet.
// Production TUN worker cannot yet persist plan+source across turns.
// On ANY failure caller must retire the whole plan/packet ID, not retry
// after a partially issued cursor, to avoid mixed-stride logical packets.
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn stage_next_original_link_turn(
    arena:&mut Arena,plan:&mut LinkPacketPlan<'_>,
    current_frame_mtu:usize,available_records:usize
)->Result<Vec<(crate::memory::UniqueBuffer,usize)>,i32>{
    if available_records==0 || plan.is_abandoned(){return Err(FULL)}
    let remaining=plan.total_frames().checked_sub(plan.issued()).ok_or(INVALID)?;
    if remaining==0{return Ok(Vec::new())}
    let count=remaining.min(available_records).min(32);
    let mut staged=Vec::with_capacity(count);
    for _ in 0..count{
        let part=plan.issue_next(current_frame_mtu).map_err(|_|INVALID)?
            .ok_or(INVALID)?;
        let mut slot=arena.allocate().map_err(|_|FULL)?;
        let end=14usize.checked_add(part.len()).ok_or(INVALID)?;
        if end>slot.writable().len(){return Err(INVALID)}
        slot.writable()[14..end].copy_from_slice(&part);
        staged.push((slot,part.len()));
    }
    Ok(staged)
}
// The public product accepts the same 20 parity row IDs as the FEC2 codec.
// Strong uses rows 0..15; Maximum requires rows 0..19. Never truncate
// Maximum to 16 while calling the unchanged authenticated M3/M4 owner.
#[cfg(all(feature="fec2_product_record",target_os="linux",
    any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn original_public_fixed_row_allowed(row:u8)->bool{
    usize::from(row)<wbd_codec::fec_v2::MAX_R
}
// Genuine TLS-authorized Fixed/Normal product TX share original owner
// M1 immutable FrozenRecord, M3 authenticated PN and M4 driver. This runs
// ONLY after Go Fixed REQUESTED, not for a peer packet or a feature flag.
#[cfg(all(feature="fec2_product_record",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn original_fixed_stage_source(e:&mut Entry,
    slab:crate::memory::UniqueBuffer,n:usize,
    budget:wbd_codec::path_budget::FrameBudget,now:MonoNs)->Result<bool,i32>{
    use crate::v4_fixed_stream::FixedStream;
    use wbd_types::ConfigRevision;
    let (profile,rev)=e.fixed_pending.or(e.fixed_applied).ok_or(BAD_STAGE)?;
    if e.protected_features!=7||e.phase!=PH_ACTIVE{return Err(BAD_STAGE)}
    let (_,epoch)=e.owner.normal_firstsend_identity().ok_or(BAD_STAGE)?;
    if n==0||n>budget.record_payload_mtu.saturating_sub(14){return Err(INVALID)}
    let mut stream=match e.fec2_live_tx.take(){
        Some(old) if old.revision()==ConfigRevision(rev)=>old,
        Some(old)=>{
            // Never silently discard another revision's immutable sources.
            e.fec2_live_tx=Some(old);return Err(BAD_STAGE)
        }
        None=>FixedStream::new(profile,rev,budget.record_payload_mtu).ok_or(INVALID)?,
    };
    let mut callback_error=None;
    let offered=stream.offer_source(slab,14..14+n,now,|ticket,source|{
        let attempt=(||->Result<(),i32>{
            if ticket.revision!=ConfigRevision(rev){return Err(BAD_STAGE)}
            let payload=match wbd_codec::fec_v2::source_owned(
                ticket.block_id,ticket.index,source,budget.record_payload_mtu
            ){
                Ok(payload)=>payload,
                Err(_)=>{e.fec2_fail_reasons[0]+=1;return Err(INVALID)}
            };
            let mut sealed=match e.arena.allocate(){
                Ok(slot)=>slot,
                Err(_)=>{e.fec2_fail_reasons[1]+=1;return Err(FULL)}
            };
            let Some(end)=14usize.checked_add(payload.len())else{
                e.fec2_fail_reasons[0]+=1;return Err(INVALID)
            };
            if end>sealed.writable().len(){
                e.fec2_fail_reasons[0]+=1;return Err(FULL)
            }
            sealed.writable()[14..end].copy_from_slice(&payload);
            let (pn,_,_)=match e.owner.seal_fec2_product_one(
                sealed,payload.len(),2,budget,15,epoch,now
            ){
                Ok(x)=>x,
                Err(_)=>{e.fec2_fail_reasons[2]+=1;return Err(BAD_STAGE)}
            };
            e.fec2_staged_pns.push((pn,2));
            Ok(())
        })();
        if let Err(err)=attempt{callback_error=Some(err);false}else{true}
    });
    e.fec2_live_tx=Some(stream);
    let accepted=offered.map_err(|_|INVALID)?;
    if let Some(err)=callback_error{return Err(err)}
    Ok(accepted.source_enqueued)
}
#[cfg(all(feature="fec2_product_record",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn original_fixed_stage_due(e:&mut Entry,
    budget:wbd_codec::path_budget::FrameBudget,now:MonoNs)->Result<usize,i32>{
    use crate::v4_fixed_stream::DriverProof;
    let Some(mut stream)=e.fec2_live_tx.take()else{return Ok(0)};
    let (_,epoch)=e.owner.normal_firstsend_identity().ok_or(BAD_STAGE)?;
    let mut failed=None;
    let result=stream.poll_parity(now,|parity,_block,row,revision|{
        if e.fixed_pending.or(e.fixed_applied).is_none_or(|(_,r)|r!=revision.0)
            ||!original_public_fixed_row_allowed(row){
            e.fec2_fail_reasons[3]+=1;return DriverProof::NotSent
        }
        let attempt=(||->Result<(),i32>{
            let mut sealed=match e.arena.allocate(){
                Ok(slot)=>slot,
                Err(_)=>{e.fec2_fail_reasons[4]+=1;return Err(FULL)}
            };
            let Some(end)=14usize.checked_add(parity.len())else{
                e.fec2_fail_reasons[5]+=1;return Err(INVALID)
            };
            if end>sealed.writable().len(){
                e.fec2_fail_reasons[5]+=1;return Err(FULL)
            }
            sealed.writable()[14..end].copy_from_slice(parity);
            let (pn,_,_)=match e.owner.seal_fec2_product_one(
                sealed,parity.len(),3,budget,15,epoch,now
            ){
                Ok(x)=>x,
                Err(_)=>{e.fec2_fail_reasons[5]+=1;return Err(BAD_STAGE)}
            };
            e.fec2_staged_pns.push((pn,3));
            Ok(())
        })();
        match attempt{
            Ok(())=>DriverProof::Staged,
            Err(err)=>{failed=Some(err);DriverProof::NotSent},
        }
    });
    e.fec2_live_tx=Some(stream);
    if let Some(err)=failed{return Err(err)}
    Ok(result.map_err(|_|BAD_STAGE)?.0)
}
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn background_tun_once(cell:&Mutex<Entry>,tun:&ScopedTunSink,
    stop:&AtomicBool,ifindex:u32,ifname:&str,tx_storage:&mut Vec<TxDispatch>,
    pending:&mut Vec<(crate::memory::UniqueBuffer,usize)>,
    ready_records:&mut Vec<crate::memory::FrozenRecord>,
    presentations:&mut Vec<Presentation>,
    actual_firstsend:&mut Vec<(wbd_types::RecordPn,u64)>,
    events:&wbd_platform::linux_route_events::RouteEvents,
    jumbo_read:&mut [u8],jumbo_queue:&mut VecDeque<Vec<u8>>,
    active_jumbo:&mut Option<PendingOriginalJumbo>,
    #[cfg(feature="fec2_product_record")]
    ingress:&LoopCounts,
    #[cfg(feature="fec2_product_record")]
    fec_ingress_on:bool
)->Result<TxTurnCompletion,i32>{
    // The caller has ALREADY polled the first TUN packet. Never wait for
    // batch fill: one sparse packet is sealed/submitted immediately.
    // The stack-owned vectors are reserved once per worker (not per DATA).
    // Retain already-read but NOT admitted original M1 loaned small packets
    // across a route/coalescing abort. Never silently clear a kernel-consumed
    // packet on the next owner turn; it still belongs to this generation.
    let recovered_small=!pending.is_empty();
    ready_records.clear();
    presentations.clear();
    actual_firstsend.clear();
    let started=Instant::now();
    let observed_event=events.snapshot();
    let (generation,defer_route)={
        let e=cell.lock().map_err(|_|BAD_STAGE)?;
        if e.phase!=PH_ACTIVE{return Err(BAD_STAGE)}
        let defer_route=e.tx_route.as_ref().is_some_and(|cache|
            wbd_platform::linux_route_events::classify(
                cache.route_event_revision,observed_event.revision,
                cache.observed_at.elapsed()
            )==wbd_platform::linux_route_events::EventRefresh::Defer
        );
        (e.generation,defer_route)
    };
    if defer_route{
        // The source has not been read from TUN yet, so its first arrival
        // cannot be lost by the route's 100ms coalescing window. No busy
        // spin on an already-ready TUN fd or active jumbo plan.
        if !stop.load(Ordering::Acquire){
            thread::sleep(Duration::from_millis(1));
        }
        return Ok(TxTurnCompletion::default())
    }
    let mut ingress_error=false;
    let mut observed=0usize;
    // One stack-local numeric batch, no packet identity or per-packet atomic.
    #[cfg(feature="fec2_product_record")]
    let mut tx_trace=[0u64;8];
    if jumbo_read.len()<M0_TUN_IPV4_MAX{return Err(INVALID)}
    loop {
        if recovered_small{break}
        if stop.load(Ordering::Acquire){return Err(BAD_STAGE)}
        // A full-size, reusable TUN scratch is necessary: Linux TUN read()
        // truncates a packet irreversibly if called with the 2034B small slab.
        // Only jumbo copies are retained; ordinary traffic moves into the
        // original generation-scoped M1 arena immediately after kernel read.
        if jumbo_queue.len()>=M0_MAX_PENDING_JUMBO{break}
        // Linux TUN read is destructive. Reserve a real owner slab BEFORE
        // consuming a business datagram; deferred packets stay in kernel TUN.
        // The jumbo/rejected/no-data branch drops the unused reservation.
        let pre_read={
            let mut e=cell.lock().map_err(|_|BAD_STAGE)?;
            if e.phase!=PH_ACTIVE{return Err(BAD_STAGE)}
            // Normal/off DATA and authenticated reverse receipts use the
            // SAME M1 frozen arena. With all loans held by sender shadow,
            // reverse ACK staging cannot acquire a slab, so 2ms NotSent
            // retries and PTO duplicates amplify capacity exhaustion even
            // on a zero-loss wire. Reserve small, REAL owner slots for ACK.
            // Fixed/Auto data staging keeps its existing arena admission.
            #[cfg(feature="fec2_product_record")]
            let control_floor=if e.rx_feedback.is_some()
                && e.fixed_pending.is_none() && e.fixed_applied.is_none() {
                M0_NORMAL_FEEDBACK_SLAB_RESERVE
            }else{0};
            #[cfg(not(feature="fec2_product_record"))]
            let control_floor=0;
            e.arena.allocate_preserving(control_floor)
        };
        let mut reserved=match pre_read{
            Ok(slot)=>slot,
            Err(wbd_types::buffer_contract::BufferContractError::NoCapacity)=>{
                #[cfg(feature="fec2_product_record")]
                {tx_trace[7]+=1;}
                // An already-ready TUN fd is level-triggered. No-spin on
                // saturation, but do not delay other pending work this turn.
                if pending.is_empty() && jumbo_queue.is_empty()
                    && active_jumbo.is_none() && !stop.load(Ordering::Acquire){
                    thread::sleep(Duration::from_millis(1));
                }
                break
            },
            Err(_)=>{ingress_error=true;break}
        };
        let read={
            let mut slots=[&mut jumbo_read[..M0_TUN_IPV4_MAX]];
            tun.read_ready_batch(generation,&mut slots)
        };
        observed+=1;
        match read {
            Ok(batch)=>match batch.entry(0) {
                Some(TunReadyEntry::UntrustedIpv4{len})=>{
                    #[cfg(feature="fec2_product_record")]
                    match jumbo_read.get(9).copied(){
                        Some(17)=>tx_trace[0]+=1,
                        Some(6)=>tx_trace[1]+=1,
                        _=>tx_trace[2]+=1,
                    }
                    #[cfg(feature="fec2_product_record")]
                    if fec_ingress_on{
                        ingress.fec_m1_ingress[0].fetch_add(1,Ordering::Relaxed);
                    }
                    if len>M0_SMALL_ARENA_PAYLOAD {
                        #[cfg(feature="fec2_product_record")]
                        if fec_ingress_on{
                            ingress.fec_m1_ingress[3].fetch_add(1,Ordering::Relaxed);
                        }
                        jumbo_queue.push_back(jumbo_read[..len].to_vec());
                    }else{
                        // Small fresh packet always owns an M1 loan before
                        // kernel TUN consumption. No post-read slot failure.
                        reserved.writable()[14..14+len]
                            .copy_from_slice(&jumbo_read[..len]);
                        pending.push((reserved,len));
                        #[cfg(feature="fec2_product_record")]
                        if fec_ingress_on{
                            ingress.fec_m1_ingress[1].fetch_add(1,Ordering::Relaxed);
                        }
                    }
                }
                Some(TunReadyEntry::Rejected)=>{
                    #[cfg(feature="fec2_product_record")]
                    {tx_trace[3]+=1;}
                    #[cfg(feature="fec2_product_record")]
                    if fec_ingress_on{
                        ingress.fec_m1_ingress[4].fetch_add(1,Ordering::Relaxed);
                    }
                },
                _=>break, // EAGAIN, EINTR or readiness race: healthy idle
            },
            Err(TunError::Stopped)=>return Err(BAD_STAGE),
            Err(_)=>{ingress_error=true;break},
        }
        if observed>=32 || stop.load(Ordering::Acquire){break}
        if pending.len()%8==0 && started.elapsed()>=Duration::from_micros(100){break}
        if !loop_readiness(tun.readiness_fd(),stop,0){break}
    }
    if pending.is_empty() && jumbo_queue.is_empty() && active_jumbo.is_none(){
        #[cfg(feature="fec2_product_record")]
        let due={
            let e=cell.lock().map_err(|_|BAD_STAGE)?;
            let fec=e.fec2_live_tx.as_ref().is_some_and(|s|
                s.report().queued_jobs>0 ||
                s.next_deadline().is_some_and(|d|d.0<=loop_now().0));
            let reverse=e.feedback_queued.is_none() &&
                e.rx_feedback.as_ref().is_some_and(|f|
                    f.lock().ok().and_then(|rx|rx.next_deadline())
                    .is_some_and(|d|d.0<=loop_now().0));
            fec||reverse
        };
        #[cfg(not(feature="fec2_product_record"))]
        let due=false;
        if !due{
            return if ingress_error{Err(INVALID)}else{Ok(TxTurnCompletion::default())}
        }
    }
    // Route validation and original M1/M3 AEAD/PN/queue admission occur
    // under the current generation's owner. M4's real sendmmsg follows
    // OUTSIDE Entry lock with an immutable original LoanBatch.
    let (batch,raw,flow,server_side,generation,admitted,seal_failed,jumbo_staged)={
        let mut guard=cell.lock().map_err(|_|BAD_STAGE)?;
        let e:&mut Entry=&mut guard;
        if e.phase!=PH_ACTIVE||stop.load(Ordering::Acquire){return Err(BAD_STAGE)}
        let flow=e.flow;
        let destination=Ipv4Addr::from(
            if e.server_side{flow.client_ip}else{flow.server_ip}
        );
        let event=events.snapshot();
        if let Some(cache)=e.tx_route.as_ref(){
            if wbd_platform::linux_route_events::classify(
                cache.route_event_revision,event.revision,cache.observed_at.elapsed()
            )==wbd_platform::linux_route_events::EventRefresh::Defer{
                return Err(INVALID)
            }
        }
        let refresh=e.tx_route.as_ref().is_none_or(|cache|
            cache.observed_at.elapsed()>=Duration::from_secs(1)
            || cache.ifindex!=ifindex || cache.destination!=destination
            || cache.revision!=e.tx_route_revision
            || cache.route_event_revision!=event.revision
        );
        if refresh{
            // M0 owner snapshot refresh alone cannot resurrect M4's
            // deliberately invalidated ScopedRouteBudget, or change the
            // device MTU bound frozen when its raw FD was opened. Reopen the
            // SAME trusted M4 driver, generation and ifindex ONLY on actual
            // link/route revision change or prior invalidation; never on
            // ordinary 1s refresh or DATA. Exact one background TX worker
            // owns this handle, so no other TX batch can be in flight.
            let has_cache=e.tx_route.is_some();
            e.tx_route=None;
            let snapshot=e.owner.observe_linux_normal_off_route_budget(
                ifname,ifindex,destination
            ).map_err(|_|INVALID)?;
            let must_reopen=raw_driver_reopen_on_route_change(
                has_cache,e.tx_route_revision,snapshot.observed_interface_mtu,
                e.raw_tx_lease_mtu
            );
            if must_reopen{
                let fresh=ScopedRawIpv4Tx::open(ifname,ifindex,e.generation)
                    .map_err(|_|INVALID)?;
                let old=e.raw_tx.as_ref().ok_or(BAD_STAGE)?;
                // One unique active TX loop: no asynchronous kernel data
                // loan may remain when the old FD is retired. Failure keeps
                // the owner fail-closed, never drops a live borrowed slab.
                if old.outstanding()!=0{return Err(BAD_STAGE)}
                old.begin_stop();
                if old.stop_until(Instant::now())!=StopResult::Drained{
                    return Err(BAD_STAGE)
                }
                e.raw_tx=Some(Arc::new(fresh));
                e.raw_tx_lease_mtu=snapshot.observed_interface_mtu;
            }
            e.tx_route_revision=e.tx_route_revision.checked_add(1).ok_or(FULL)?;
            e.tx_route=Some(WorkerRouteBudget{
                scoped:snapshot,observed_at:Instant::now(),ifindex,destination,
                revision:e.tx_route_revision,route_event_revision:event.revision,
            });
            e.counters.route_refresh.fetch_add(1,Ordering::Relaxed);
        }
        let mut accepted=0usize;
        let mut failed=ingress_error;
        let mut jumbo_staged=false;
        #[cfg(feature="fec2_product_record")]
        {
            // The previous kernel send is synchronous and settled before a
            // new turn may allocate new encrypted FEC PNs.
            if !e.fec2_staged_pns.is_empty(){return Err(BAD_STAGE)}
        }
        for (mut slab,n) in pending.drain(..){
            if stop.load(Ordering::Acquire){failed=true;break}
            // The NORMAL small-packet path stays unchanged: no LINK20, no
            // packet copy and no extra timer. One oversized real TUN IPv4
            // packet is slow-path fragmented using M3's immutable single-
            // snapshot plan, then EACH frame follows the original M1 owner,
            // real AEAD/PN, scoped raw lease and kernel syscall. Never seal
            // a naked over-budget ordinary frame.
            let frame_mtu=e.tx_route.as_ref().ok_or(BAD_STAGE)?
                .scoped.frame.link_frame_mtu;
            #[cfg(feature="fec2_product_record")]
            if e.protected_features==7 &&
                (e.fixed_pending.is_some()||e.fixed_applied.is_some()){
                let budget=e.tx_route.as_ref().ok_or(BAD_STAGE)?.scoped.frame;
                // Real TUN input already has a bounded M1 slab. Record
                // EXACTLY where the first-source handoff fails, including
                // the pre-offer record-size guard not covered by source_payload.
                e.counters.fec_m1_stage[0].fetch_add(1,Ordering::Relaxed);
                if n>budget.record_payload_mtu.saturating_sub(14){
                    e.counters.fec_m1_stage[4].fetch_add(1,Ordering::Relaxed);
                }
                match original_fixed_stage_source(e,slab,n,budget,loop_now()){
                    Ok(true)=>{
                        accepted+=1;
                        e.counters.fec_m1_stage[1].fetch_add(1,Ordering::Relaxed);
                    }
                    Ok(false)=>{
                        e.counters.fec_m1_stage[2].fetch_add(1,Ordering::Relaxed);
                    }
                    Err(_)=>{
                        failed=true;
                        e.counters.fec_m1_stage[3].fetch_add(1,Ordering::Relaxed);
                    }
                }
                // An authenticated Fixed source must never silently escape
                // onto Normal/off kind1 when oversize or pressure occurs.
                continue
            }
            #[cfg(feature="fec2_product_record")]
            if fec_ingress_on{
                // Read while genuinely Fixed, but switched mode before the
                // owner processed the retained small packet. Do not infer
                // it entered the FEC source counter.
                e.counters.fec_m1_stage[5].fetch_add(1,Ordering::Relaxed);
            }
            if n<=frame_mtu {
                // Exact inner IPv4 protocol is in original owned M1 slab.
                // Stage-success does not claim a kernel copy or delivery.
                #[cfg(feature="fec2_product_record")]
                let proto=slab.writable().get(14+9).copied();
                let scoped=&e.tx_route.as_ref().ok_or(BAD_STAGE)?.scoped;
                let result=e.owner.seal_normal_off_with_worker_snapshot(
                    slab,n,scoped,ifindex,destination,15,loop_now()
                );
                if result.is_ok(){
                    accepted+=1;
                    #[cfg(feature="fec2_product_record")]
                    match proto{
                        Some(17)=>tx_trace[5]+=1,
                        Some(6)=>tx_trace[6]+=1,
                        _=>{},
                    }
                }else{failed=true}
                continue;
            }
            let id=e.next_link_packet_id;
            if id==0 || id==u32::MAX || n>65_535 {
                failed=true;continue;
            }
            let source=&slab.writable()[14..14+n];
            let staged=match stage_bounded_original_link(
                &mut e.arena,source,frame_mtu,id,32usize.saturating_sub(accepted)
            ){
                Ok(all)=>all,
                Err(_)=>{failed=true;continue}
            };
            // All pieces are now present in original generation-scoped M1
            // slots. No short arena or malformed LINK part can publish a
            // prefix before this point; reserve a never-reused logical ID.
            e.next_link_packet_id=id+1;
            for (fragment_slab,part_len) in staged{
                if stop.load(Ordering::Acquire){failed=true;break}
                let scoped=&e.tx_route.as_ref().ok_or(BAD_STAGE)?.scoped;
                let result=e.owner.seal_fragment_with_worker_snapshot(
                    fragment_slab,part_len,scoped,ifindex,destination,
                    15,loop_now()
                );
                if result.is_ok(){accepted+=1}else{failed=true;break}
            }
        }
        #[cfg(feature="fec2_product_record")]
        if e.protected_features==7 &&
            (e.fixed_pending.is_some()||e.fixed_applied.is_some()){
            // Current Fixed mode does not authorize LINK fragmentation as
            // plain Normal/off. Reject jumbo rather than emit mixed kinds.
            if !jumbo_queue.is_empty()||active_jumbo.is_some(){
                failed=true;jumbo_queue.clear();active_jumbo.take();
            }
            let budget=e.tx_route.as_ref().ok_or(BAD_STAGE)?.scoped.frame;
            let before=e.fec2_staged_pns.len();
            if original_fixed_stage_due(e,budget,loop_now()).is_err(){
                failed=true
            }
            accepted+=e.fec2_staged_pns.len().saturating_sub(before);
        }
        // A jumbo is eligible for a new <=32-frame turn even without new
        // TUN readiness. Preserve small packet priority within this turn,
        // so an unrelated fresh datagram is not held behind 48+ pieces.
        if active_jumbo.is_none(){
            if let Some(source)=jumbo_queue.pop_front(){
                let id=e.next_link_packet_id;
                let frame_mtu=e.tx_route.as_ref().ok_or(BAD_STAGE)?
                    .scoped.frame.link_frame_mtu.min(M0_SMALL_ARENA_PAYLOAD);
                if id==0 || id==u32::MAX{failed=true}
                else{
                    // Reserve exactly once, BEFORE first publish. Even a
                    // later route/Stop/error never reuses this packet ID.
                    e.next_link_packet_id=id+1;
                    match PendingOriginalJumbo::new(
                        source,id,frame_mtu,e.generation,event.revision
                    ){
                        Ok(plan)=>*active_jumbo=Some(plan),
                        Err(_)=>failed=true,
                    }
                }
            }
        }
        if accepted<32{
            if let Some(plan)=active_jumbo.as_mut(){
                // Route invalidation, generation change or MTU shrink is
                // terminal for an already-issued logical LINK packet.
                let frame_mtu=e.tx_route.as_ref().ok_or(BAD_STAGE)?
                    .scoped.frame.link_frame_mtu.min(M0_SMALL_ARENA_PAYLOAD);
                if !plan.valid_for(e.generation,event.revision,frame_mtu){
                    failed=true;active_jumbo.take();
                }else{
                    match plan.stage_turn(
                        &mut e.arena,frame_mtu,32usize.saturating_sub(accepted)
                    ){
                        Ok(staged)=>{
                            jumbo_staged=!staged.is_empty();
                            for (fragment_slab,part_len) in staged{
                                if stop.load(Ordering::Acquire){
                                    failed=true;break
                                }
                                let scoped=&e.tx_route.as_ref().ok_or(BAD_STAGE)?.scoped;
                                if e.owner.seal_fragment_with_worker_snapshot(
                                    fragment_slab,part_len,scoped,ifindex,destination,
                                    15,loop_now()
                                ).is_ok(){accepted+=1}else{failed=true;break}
                            }
                            if failed{active_jumbo.take();}
                        }
                        Err(_)=>{failed=true;active_jumbo.take();}
                    }
                }
            }
        }
        #[cfg(feature="fec2_product_record")]
        if accepted<32{
            match stage_original_reverse_feedback(e,loop_now()){
                Ok(true)=>accepted+=1,
                Ok(false)=>{},
                Err(_)=>failed=true,
            }
        }
        if accepted==0{
            #[cfg(feature="fec2_product_record")]
            for (slot,count) in ingress.tx_chain.iter().zip(tx_trace) {
                if count>0{slot.fetch_add(count,Ordering::Relaxed);}
            }
            drain_data_turn_returns(&mut e.arena);
            return if failed{Err(INVALID)}else{Ok(TxTurnCompletion::default())}
        }
        let raw=Arc::clone(e.raw_tx.as_ref().ok_or(BAD_STAGE)?);
        let available=std::mem::take(tx_storage);
        let batch=match e.owner.drain_tx(loop_now(),available){
            Ok(batch)=>batch,
            Err((_,storage))=>{
                *tx_storage=storage;e.tx_route=None;
                if jumbo_staged{active_jumbo.take();}
                drain_data_turn_returns(&mut e.arena);
                return Err(BAD_STAGE)
            }
        };
        let ready=e.owner.checked_tx_ready(&batch).map_err(|_|BAD_STAGE)?;
        if ready.is_empty() || ready.len()>32 || ready.iter().any(
            |x|x.kind!=crate::runtime::TxKind::Fresh){
            *tx_storage=batch.recycle();
            e.tx_route=None;
            if jumbo_staged{active_jumbo.take();}
            drain_data_turn_returns(&mut e.arena);
            return Err(INVALID)
        }
        // Clone only Arc handles into preallocated metadata, NEVER the
        // plaintext/ciphertext. Both vectors are recycled next turn.
        for x in ready{
            // Original M4 uses legacy IPv4+TCP fixed 40B scatter header,
            // options=None; count the complete outer bytes, not ciphertext
            // alone or an RX-derived estimate. Reuse fixed 32-slot metadata.
            actual_firstsend.push((x.record.metadata().pn,
                (x.record.bytes().len()+wbd_platform::ipv4_tcp::BASE_OVERHEAD) as u64));
            ready_records.push(x.record.clone());
            presentations.push(Presentation{
                ack32:1,advertised_window:4096,ip_id:43,
                persona:PacketPersona::Legacy,
            });
        }
        (batch,raw,flow,e.server_side,e.generation,ready_records.len(),failed,jumbo_staged)
    };
    let report=if stop.load(Ordering::Acquire){None}else{
        let tuple=if server_side{Ipv4Tuple{
            src_ip:&flow.server_ip,dst_ip:&flow.client_ip,
            src_port:flow.server_port,dst_port:flow.client_port,
        }}else{Ipv4Tuple{
            src_ip:&flow.client_ip,dst_ip:&flow.server_ip,
            src_port:flow.client_port,dst_port:flow.server_port,
        }};
        Some(raw.send_kernel_multimsg(
            generation,ready_records.as_slice(),tuple,presentations.as_slice()
        ))
    };
    // Hold only immutable Arc frozen records until the actual synchronous
    // M4 syscall returns. No reserve/ACK is inferred from queue acceptance.
    #[cfg(feature="fec2_product_record")]
    let frozen_for_outer=ready_records.clone();
    ready_records.clear();
    presentations.clear();
    *tx_storage=batch.recycle();
    let mut guard=cell.lock().map_err(|_|BAD_STAGE)?;
    let e:&mut Entry=&mut guard;
    if e.phase!=PH_ACTIVE||stop.load(Ordering::Acquire){
        drain_data_turn_returns(&mut e.arena);
        return Err(BAD_STAGE)
    }
    let finish=classify_tx_turn(report.as_ref(),admitted,seal_failed);
    #[cfg(feature="fec2_product_record")]
    if let Some(shared)=e.original_outer.as_ref(){
        let mut original=shared.lock().map_err(|_|BAD_STAGE)?;
        let mut global=original_process_repair_quota().lock()
            .map_err(|_|BAD_STAGE)?;
        let now=loop_now();
        let copied=(finish.copied as usize).min(frozen_for_outer.len());
        // Fresh ciphertext is registered only for the actual M4 definite
        // copied prefix; never register health-control kind1, driver-unknown,
        // or definitely-not-sent as missing data.
        let control_last=e.feedback_queued.is_some();
        let data_count=frozen_for_outer.len()-usize::from(control_last);
        for record in frozen_for_outer.iter().take(copied.min(data_count)){
            let frame_bytes=(record.bytes().len()+
                wbd_platform::ipv4_tcp::BASE_OVERHEAD) as u64;
            match global.on_fresh_accepted(
                original.direction,frame_bytes,now
            ){
                Ok(())=>{
                    if original.shadow.on_sent_adaptive(record.clone(),now).is_ok(){
                        original.sent_fresh=original.sent_fresh.saturating_add(1);
                    }else{
                        original.note_block(OriginalRepairBlockReason::FreshShadow);
                    }
                },
                Err(_)=>original.note_block(OriginalRepairBlockReason::FreshGlobal),
            }
        }
    }
    // Keep M2 original outbound DATA denominator separate from a native
    // receipt record. Control is appended last after all application
    // first-sends; failure to preserve this order censors the owner, never
    // counts an authenticated ACK as successful new business DATA.
    #[cfg(feature="fec2_product_record")]
    let feedback_last=if let Some((_,pn))=e.feedback_queued.as_ref(){
        if !actual_firstsend.last().is_some_and(|x|x.0.0==*pn){
            return Err(BAD_STAGE)
        }
        true
    }else{false};
    #[cfg(not(feature="fec2_product_record"))]
    let feedback_last=false;
    #[cfg(feature="fec2_product_record")]
    if let Some((draft,_))=e.feedback_queued.take(){
        let idx=actual_firstsend.len().checked_sub(1).ok_or(BAD_STAGE)?;
        let status=if idx<finish.copied as usize{
            wbd_recovery::FeedbackSendResult::Accepted
        }else if finish.uncertain==1&&idx==finish.copied as usize{
            wbd_recovery::FeedbackSendResult::Uncertain
        }else{
            wbd_recovery::FeedbackSendResult::NotSent
        };
        let feedback=e.rx_feedback.as_ref().ok_or(BAD_STAGE)?;
        feedback.lock().map_err(|_|BAD_STAGE)?
            .on_send_result(&draft,status,loop_now())
            .map_err(|_|BAD_STAGE)?;
    }
    #[cfg(feature="fec2_product_record")]
    {
        let mut parity_copied=0u8;
        let mut parity_not_sent=0u8;
        let mut parity_uncertain=0u8;
        let mut actual_fec_sources=Vec::new();
        let mut source_copied=0u32;
        let mut source_uncertain=0u32;
        for (pn,kind) in e.fec2_staged_pns.drain(..){
            let idx=actual_firstsend.iter().position(|x|x.0.0==pn);
            let copied=idx.is_some_and(|i|i<finish.copied as usize);
            let uncertain=idx.is_some_and(|i|
                finish.uncertain==1&&i==finish.copied as usize);
            if kind==2{
                if let Some(i)=idx{
                    actual_fec_sources.push(actual_firstsend[i]);
                    if copied{
                        source_copied=source_copied.saturating_add(1);
                        e.fec2_copied_source=e.fec2_copied_source.saturating_add(1);
                    }else if uncertain{
                        source_uncertain=source_uncertain.saturating_add(1);
                        e.fec2_fail_reasons[7]+=1;
                    }else{
                        e.fec2_fail_reasons[7]+=1;
                    }
                }
            }else{
                if copied{
                    parity_copied+=1;
                    e.fec2_copied_repair=e.fec2_copied_repair.saturating_add(1);
                }else if uncertain{
                    parity_uncertain+=1;
                    e.fec2_fail_reasons[6]+=1;
                }else{
                    parity_not_sent+=1;
                    e.fec2_fail_reasons[6]+=1;
                }
            }
        }
        // Only original M4 definitely-copied kind2 DATA becomes an M2
        // source denominator. Parity is excluded; uncopied or uncertain
        // DATA is censored. The RX worker later admits C2S receipts only
        // after the same original AEAD+unique replay bitmap.
        if !actual_fec_sources.is_empty(){
            if let Some(first)=e.normal_firstsend_m2.as_ref(){
                let observation=TxTurnCompletion{
                    copied:source_copied,uncertain:source_uncertain,
                    definitely_unsent:(actual_fec_sources.len() as u32)
                        .saturating_sub(source_copied)
                        .saturating_sub(source_uncertain),
                    backpressure:finish.backpressure,
                    failed:finish.failed,
                    invalidate_route:finish.invalidate_route,
                };
                match first.lock(){
                    Ok(mut observer)=>observer.on_real_kernel_turn(
                        &actual_fec_sources,observation,loop_now()),
                    Err(_)=>return Err(BAD_STAGE)
                }
            }
        }
        if parity_copied+parity_not_sent+parity_uncertain>0{
            let stream=e.fec2_live_tx.as_mut().ok_or(BAD_STAGE)?;
            stream.settle_staged(parity_copied,parity_not_sent,parity_uncertain)
                .map_err(|_|BAD_STAGE)?;
        }
        // A true kernel copy proves local transmission ONLY. No authentic
        // remote receipt and first TUN delivery has yet confirmed the
        // product. Keep Fixed REQUESTED/PENDING, never fabricate APPLIED.
    }
    if let Some(first)=e.normal_firstsend_m2.as_ref(){
        // Original M2 observes Normal/off first sends here. FEC source
        // DATA is separately accounted above with exact kind2 PNs; repair
        // kind3 is excluded from the source denominator.
        #[cfg(feature="fec2_product_record")]
        let has_fec=e.fixed_pending.is_some()||e.fixed_applied.is_some();
        #[cfg(not(feature="fec2_product_record"))]
        let has_fec=false;
        if !has_fec{
            let data_count=actual_firstsend.len()
                .saturating_sub(usize::from(feedback_last));
            let data=&actual_firstsend[..data_count];
            let copied=finish.copied.min(data_count as u32);
            let uncertain=if finish.uncertain==1 &&
                (finish.copied as usize)<data_count{1}else{0};
            let data_finish=TxTurnCompletion{
                copied,uncertain,
                definitely_unsent:(data_count as u32)
                    .saturating_sub(copied).saturating_sub(uncertain),
                ..finish
            };
            match first.lock(){
                Ok(mut observer)=>observer.on_real_kernel_turn(
                    data,data_finish,loop_now()),
                Err(_)=>return Err(BAD_STAGE)
            }
        }
    }
    actual_firstsend.clear();
    if finish.invalidate_route{e.tx_route=None}
    // The kernel's scoped prefix is the only positive send proof. Never
    // resume a mixed-stride/ambiguous/partially copied logical packet.
    if jumbo_staged && active_jumbo.as_ref().is_some_and(
        |x|x.retire_after_turn(finish,stop.load(Ordering::Acquire))
    ){
        active_jumbo.take();
    }
    drain_data_turn_returns(&mut e.arena);
    #[cfg(feature="fec2_product_record")]
    for (slot,count) in ingress.tx_chain.iter().zip(tx_trace){
        if count>0{slot.fetch_add(count,Ordering::Relaxed);}
    }
    // Even when the tail failed, the definite prefix remains copied and
    // accounted. Dropped/uncertain immutable records are only released
    // after synchronous M4 sendmmsg completes; never reseal/reuse PN.
    Ok(finish)
}
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn loop_readiness(fd:i32,stop:&AtomicBool,timeout_ms:c_int)->bool{
    if stop.load(Ordering::Acquire){return false}
    let mut p=PollFd{fd,events:1,revents:0};
    // Block only to discover the first ready packet. Further work in the
    // same bounded slice only drains immediately ready packets (timeout 0).
    // Never sleep to fill a batch, and never wait under registry.
    let got=unsafe{poll(&mut p,1,timeout_ms)};
    got>0 && p.revents&1!=0
}

// Accept only a single definitely kernel-copied original FrozenRecord.
// A partial, ambiguous, or backpressured M4 KernelSendReport is never a
// success just because a syscall returned a positive prefix elsewhere.
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn raw_ready_prefix_copied(report:&wbd_platform::linux_batch::KernelSendReport,
    expected:usize)->bool{
    report.outcome.accepted_prefix==expected
        && report.outcome.error.is_none()
        && report.outcome.uncertain_index.is_none()
        && report.signal==wbd_platform::linux_batch::KernelSendSignal::None
}
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn raw_one_packet_copied(report:&wbd_platform::linux_batch::KernelSendReport)->bool{
    raw_ready_prefix_copied(report,1)
}

// A single kernel readiness event can service multiple ALREADY ready packets.
// Bounded by both 32 packets and roughly 100us of actual work, so Stop,
// the opposite direction and later control work get regular opportunities.
// The caller owns the packet buffer/driver; no extra packet Vector is built.
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn ready_only_slice(
    stop:&AtomicBool,
    mut next_ready:impl FnMut()->bool,
    mut service:impl FnMut()->bool,
    mut within_budget:impl FnMut()->bool,
)->usize{
    let mut count=0;
    while count<32 && !stop.load(Ordering::Acquire){
        // The caller has already observed one ready packet; never wait
        // again for a first packet or for a larger batch.
        if count!=0 && !next_ready(){break}
        let ok=service();
        count+=1;
        // Sample the monotonic work-slice budget every eight packets, not
        // for every DATA. First-packet/low-rate arrival never waits to batch.
        if !ok || (count%8==0 && !within_budget()){break}
    }
    count
}
// REAL original TLS V4 public product outer retransmission, for either
// direction, using M2's EXISTING single-repair PTO/RACK immutable candidate producer,
// process-global sparse/10% byte grants and exact M4 raw syscall result.
// No simulated receipt, alternative encoder or fresh PN is used anywhere.
#[cfg(all(feature="fec2_product_record",target_os="linux",
    any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn background_original_repair_once(
    cell:&Mutex<Entry>,stop:&AtomicBool
)->Result<u32,i32>{
    use wbd_recovery::{
        reserve_frozen_submission,complete_driver_prefix,
        DriverPrefixObservation,BatchSuffixEvidence,RepairSendResult
    };
    if stop.load(Ordering::Acquire){return Ok(0)}
    let (shared,raw,flow,server,generation,mature)={
        let e=cell.lock().map_err(|_|BAD_STAGE)?;
        if e.phase!=PH_ACTIVE||e.workers.is_none(){return Ok(0)}
        let Some(shared)=e.original_outer.as_ref().map(Arc::clone)
            else{return Ok(0)};
        let Some(raw)=e.raw_tx.as_ref().map(Arc::clone)
            else{return Err(BAD_STAGE)};
        let Some(mature)=e.normal_firstsend_m2.as_ref().map(Arc::clone)
            else{return Err(BAD_STAGE)};
        if raw.is_stopping()||e.tx_route.is_none(){return Ok(0)}
        (shared,raw,e.flow,e.server_side,e.generation,mature)
    };
    let now=loop_now();
    let candidates={
        let mut own=shared.lock().map_err(|_|BAD_STAGE)?;
        let polled=own.shadow.on_timer(now);
        own.retired=own.retired.saturating_add(polled.releases.len() as u64);
        polled.candidates
    };
    let tuple=if server{Ipv4Tuple{
        src_ip:&flow.server_ip,dst_ip:&flow.client_ip,
        src_port:flow.server_port,dst_port:flow.client_port,
    }}else{Ipv4Tuple{
        src_ip:&flow.client_ip,dst_ip:&flow.server_ip,
        src_port:flow.client_port,dst_port:flow.server_port,
    }};
    let presentation=Presentation{
        ack32:1,advertised_window:4096,ip_id:43,
        persona:PacketPersona::Legacy,
    };
    let mut repaired=0;
    for candidate in candidates{
        if stop.load(Ordering::Acquire){break}
        let wire_bytes=(candidate.frozen().bytes().len()+
            wbd_platform::ipv4_tcp::BASE_OVERHEAD) as u64;
        let now=loop_now();
        // Lock order is uniform: this session shadow then ONE shared global
        // process budget. RX authentic receipts use exactly the same order.
        let reserved={
            let mut own=shared.lock().map_err(|_|BAD_STAGE)?;
            if !own.shadow.preflight(&candidate,now){continue}
            let dir=own.direction;
            let route=own.route;
            let mut global=original_process_repair_quota().lock()
                .map_err(|_|BAD_STAGE)?;
            match global.grant(dir,wire_bytes,40_000_000,now){
                Ok(lease)=>{
                    match reserve_frozen_submission(
                        &mut global,lease,route,&own.shadow,
                        &candidate,wire_bytes,now
                    ){
                        Ok(submission)=>{
                            // no mutation, cipher duplication, or new AEAD
                            if submission.driver.metadata!=candidate.frozen().metadata()
                                ||submission.driver.wire.as_ptr()!=
                                    candidate.frozen().bytes().as_ptr(){
                                own.note_block(OriginalRepairBlockReason::Invariant);
                                let _=global.revoke(lease,now);
                                if own.shadow.on_send_result(
                                    &candidate,RepairSendResult::NotSent,now).is_ok(){
                                    own.retired=own.retired.saturating_add(1);
                                }
                                continue
                            }
                            Some((lease,submission.reservation_id,route))
                        },
                        Err(err)=>{
                            let _=global.revoke(lease,now);
                            let reason=original_repair_reserve_block_reason(err);
                            own.note_block(reason);
                            if reason==OriginalRepairBlockReason::Quota{
                                if own.shadow.on_quota_exhausted(&candidate,now).is_ok(){
                                    own.retired=own.retired.saturating_add(1);
                                }
                            }else if own.shadow.on_send_result(
                                &candidate,RepairSendResult::NotSent,now).is_ok(){
                                own.retired=own.retired.saturating_add(1);
                            }
                            None
                        }
                    }
                },
                Err(_)=>{
                    own.note_block(OriginalRepairBlockReason::Grant);
                    if own.shadow.on_send_result(
                        &candidate,RepairSendResult::NotSent,now).is_ok(){
                        own.retired=own.retired.saturating_add(1);
                    }
                    None
                }
            }
        };
        let Some((lease,id,route))=reserved else{continue};
        // No owner, quota, or RX lock held across the genuine raw socket IO.
        let copied=raw.send_one(generation,candidate.frozen(),tuple,presentation)
            .ok().is_some_and(|n|n as u64==wire_bytes);
        let now=loop_now();
        let observation=DriverPrefixObservation::checked(
            1,usize::from(copied),if copied{None}else{Some(0)},
            BatchSuffixEvidence::Unproven
        ).map_err(|_|BAD_STAGE)?;
        // Complete quota/accounting under the established outer->global
        // lock order, then release both before touching maturity. RX uses
        // maturity->outer->global, so never invert that order here.
        let status={
            let mut own=shared.lock().map_err(|_|BAD_STAGE)?;
            let mut global=original_process_repair_quota().lock()
                .map_err(|_|BAD_STAGE)?;
            let results=complete_driver_prefix(
                &mut global,&[(id,route)],observation,now
            );
            let status=match results {
                Ok(s)=>s.shadow_result(0).unwrap_or(RepairSendResult::Uncertain),
                Err(_)=>RepairSendResult::Uncertain,
            };
            let _=global.revoke(lease,now);
            if copied && status==RepairSendResult::Accepted{
                repaired+=1;
                own.repair_copied=own.repair_copied.saturating_add(1);
            }else{
                own.repair_uncertain=own.repair_uncertain.saturating_add(1);
            }
            status
        };
        // Candidate clone keeps immutable payload alive across this metadata
        // update even if a concurrent authentic receipt already retired the
        // shadow. No owner/global lock is held here.
        if let Ok(mut m)=mature.lock(){
            m.on_possible_recovery(candidate.pn(),status,now);
        }
        // Re-acquire only the outer owner for idempotent payload retirement.
        // A racing receipt may have won; stale completion never resurrects.
        if let Ok(mut own)=shared.lock(){
            if own.shadow.on_send_result(&candidate,status,now).is_ok(){
                own.retired=own.retired.saturating_add(1);
            }
        }
    }
    Ok(repaired)
}
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn start_loop(handle:u64,ifindex:u32)->i32{
    // One shared Linux link/route listener for all live owner sessions.
    // This is only an invalidation signal; M4 still checks every raw send.
    let events=wbd_platform::linux_route_events::subscribe();
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.workers.is_some(){return BAD_STAGE}
    // Grouped Game2/4 consumes these TLS keys into a different SINGLE
    // GameAdapter. Starting a second Normal owner would duplicate PN/AEAD.
    #[cfg(feature="fec2_product_record")]
    if e.game_joined{return BAD_STAGE}
    let (Some(raw),Some(tun))=(e.raw_rx.as_ref(),e.tun_sink.as_ref())
    else{return BAD_STAGE};
    let Some(ifname)=e.raw_ifname.clone()else{return BAD_STAGE};
    let raw=Arc::clone(raw);
    let tun=Arc::clone(tun);
    let raw_fd=raw.readiness_fd();
    let tun_fd=tun.readiness_fd();
    if e.raw_tx.is_none(){
        let Ok(tx)=ScopedRawIpv4Tx::open(&ifname,ifindex,(handle>>32) as u32)
        else{return INVALID};
        let Ok(observed)=wbd_platform::linux_packet_preflight::observe_interface_mtu(
            &ifname,ifindex) else{return INVALID};
        e.raw_tx_lease_mtu=observed.kernel_mtu;
        e.raw_tx=Some(Arc::new(tx));
    }
    if e.raw_tx_lease_mtu==0{return BAD_STAGE}
    // Build the independent RX arena and move the exact protected opener
    // only after both original raw/TUN devices have been installed. Never
    // allocate a second crypto instance or credential authority.
    let rx_arena_id=e.generation ^ 0x8000_0000;
    if rx_arena_id==0{return FULL}
    let Ok(mut rx_arena)=Arena::new(rx_arena_id,64,2048,64,1_000_000)
    else{return FULL};
    // Preserve pre-Detach early RX bytes. Original M1 32-slot queue is
    // flushed through the SAME opener and LINK table before the move.
    if e.staged_count>0{
        let e:&mut Entry=&mut e;
        let normal=match e.normal.as_mut(){Some(n)=>n,None=>return BAD_STAGE};
        let returned=match e.owner.drain_normal_off_to_tun(
            normal,&tun,loop_now(),Vec::with_capacity(32)){
            Ok((returned,_,_,_))=>returned,
            Err((_,returned))=>{drop(returned);return BAD_STAGE}
        };
        drop(returned);
        drain_data_turn_returns(&mut e.arena);
    }
    // Bind M2 to the ORIGINAL authenticated Go TLS identity before moving
    // the sole AEAD/replay RX to its independent worker. No peer receipt is
    // manufactured; every uncovered mature observation stays UNKNOWN.
    let Some((lane,epoch))=e.owner.normal_firstsend_identity()else{return BAD_STAGE};
    let Ok(first)=NormalFirstSendM2::new(lane,epoch,e.server_side,loop_now())
        else{return INVALID};
    #[cfg(feature="fec2_product_record")]
    let original_outer_rx=if e.original_public_feedback_armed{
        let now=loop_now();
        let direction=wbd_recovery::BudgetDirection{
            tunnel:lane.tunnel,
            direction:first.route.outbound_direction(),
        };
        let route=first.route;
        let Ok(mut shadow)=wbd_recovery::ReceiptState::new(
            lane,wbd_recovery::ReceiptConfig{
                max_shadow_entries:131_072,pto_ns:810_000_000,
                reorder_window_ns:20_000_000,
            }
        )else{return INVALID};
        if shadow.enable_adaptive_timing(600_000_000,50_000_000).is_err(){
            return INVALID
        }
        let Ok(mut global)=original_process_repair_quota().lock()else{return BAD_STAGE};
        // RepairBudget independently enforces its finite local burst and
        // sparse/10% epoch ledger. The large configured ceiling remains only
        // an absolute safety cap; it is not extra repair credit or fresh HOL.
        if global.register(direction,wbd_recovery::RepairBudgetConfig{
            outer_mtu:u64::from(e.raw_tx_lease_mtu),
            max_repair_bytes_per_epoch:8*1024*1024,
            max_pending_reservations:128,max_pending_bytes:4*1024*1024,
            io_timeout_ns:100_000_000,
        },now).is_err(){return BAD_STAGE}
        if global.bind_receipt_route(direction,route,now).is_err(){return BAD_STAGE}
        let active=Arc::new(Mutex::new(OriginalOuterRepair{
            shadow,direction,route,sent_fresh:0,authentic_ack:0,
            repair_copied:0,repair_uncertain:0,repair_blocked:0,
            block_reasons:[0;ORIGINAL_REPAIR_BLOCK_REASON_COUNT],retired:0,
        }));
        e.original_outer=Some(Arc::clone(&active));
        Some(active)
    }else{None};
    let mature=Arc::new(Mutex::new(first));
    e.normal_firstsend_m2=Some(Arc::clone(&mature));
    // Only the REAL published original-Go product API explicitly arms the
    // native bidirectional M2 feedback worker under verified epoch. Existing
    // separate-sender scoped source proofs keep their independently
    // authenticated Go health sender; no duplicate two-sender race.
    #[cfg(feature="fec2_product_record")]
    let feedback_rx=if e.original_public_feedback_armed{
        let Ok(state)=wbd_recovery::RxFeedbackState::new(
            wbd_recovery::RxFeedbackConfig{
                max_retained_pages:512,max_pages_per_report:8,
                retention_ns:2_000_000_000,srtt_ns:600_000_000,
            }
        )else{return INVALID};
        let shared=Arc::new(Mutex::new(state));
        e.rx_feedback=Some(Arc::clone(&shared));
        Some(shared)
    }else{None};
    let normal=match e.normal.take(){Some(n)=>n,None=>return BAD_STAGE};
    let mut original_rx=match e.owner.detach_background_rx(normal){
        Ok(rx)=>rx,
        Err((_,normal))=>{e.normal=Some(normal);return BAD_STAGE},
    };
    #[cfg(all(feature="fec2_product_record",target_os="linux"))]
    if e.protected_features==7 {
        let verified=crate::v4_fec2_live_rx::VerifiedReceiveEpoch{
            generation:e.generation,epoch,
            negotiated_features:e.protected_features,
            // Original-Go TLS binding selects the reverse direction:
            // server opens C2S; client opens S2C, never same-direction keys.
            direction_s2c:!e.server_side,
        };
        if original_rx.arm_fec2_original_go_only(
            verified,Arc::clone(&e.fec2_rx_admit),
            usize::from(e.wire_limit)
        ).is_err(){return BAD_STAGE}
    }
    #[cfg(feature="fec2_product_record")]
    if e.original_public_feedback_armed && e.protected_features==7 &&
        e.fixed_pending.is_some(){
        // TLS feature7 + original Go operator's native FIXED/PENDING
        // authorizes inbound FEC source/repair *parsing*. Sender APPLIED
        // remains separate and requires actual kernel copies plus mature
        // authenticated reverse receipts, never a requested flag.
        e.fec2_rx_admit.store(true,Ordering::Release);
    }
    let mut rx_anchor=e.rx_seq_anchor;
    let rx_flow=e.flow;
    let rx_server_side=e.server_side;
    let generation=e.generation;
    let shutdown=Arc::new(AtomicBool::new(false));
    let stats=Arc::clone(&e.counters);
    #[cfg(feature="fec2_product_record")]
    let fec_ingress_on=e.protected_features==7 &&
        (e.fixed_pending.is_some()||e.fixed_applied.is_some());
    let stop_rx=Arc::clone(&shutdown);
    let stats_rx=Arc::clone(&stats);
    let raw_for_rx=Arc::clone(&raw);
    let tun_for_rx=Arc::clone(&tun);
    let Ok(rx)=thread::Builder::new().name("wbd-original-m4-rx".into())
        .spawn(move||{
            let cpu_origin=owner_thread_cpu_ns();
            let mut last_cpu_sample=Instant::now();
            let mut rx_pending=Vec::<crate::memory::UniqueBuffer>::with_capacity(32);
            while !stop_rx.load(Ordering::Acquire){
                if last_cpu_sample.elapsed()>=Duration::from_millis(100){
                    stats_rx.rx_thread_cpu_ns.store(
                        owner_thread_cpu_ns().saturating_sub(cpu_origin),Ordering::Relaxed);
                    last_cpu_sample=Instant::now();
                }
                if !loop_readiness(raw_fd,&stop_rx,10){continue}
                match background_raw_once(
                    &mut original_rx,&mut rx_arena,&mut rx_anchor,
                    rx_flow,generation,rx_server_side,&raw_for_rx,&tun_for_rx,
                    &stop_rx,&mut rx_pending,&mature,
                    #[cfg(feature="fec2_product_record")]
                    &stats_rx,
                    #[cfg(feature="fec2_product_record")]
                    feedback_rx.as_ref(),
                    #[cfg(feature="fec2_product_record")]
                    original_outer_rx.as_ref()
                ){
                    Ok(n)=>{stats_rx.rx.fetch_add(u64::from(n),Ordering::Relaxed);}
                    Err(_)=>{stats_rx.rx_error.fetch_add(1,Ordering::Relaxed);}
                }
            }
            // No outstanding kernel borrow after the synchronous call,
            // and STOP joins this thread before retiring original drivers.
            rx_pending.clear();
            rx_arena.drain_returns_bounded(M0_DATA_RETURN_TURN_CAP);
            stats_rx.rx_thread_cpu_ns.store(
                owner_thread_cpu_ns().saturating_sub(cpu_origin),Ordering::Relaxed);
        })
    else{
        // The original RX state was consumed by the attempted spawn; fail
        // closed and require normal Stop rather than resurrecting keys.
        e.phase=PH_STOPPING;
        return INVALID
    };
    let stop_tx=Arc::clone(&shutdown);
    let tx_events=Arc::clone(&events);
    let tx_cell=Arc::clone(&cell);
    let tx_ifname=ifname;
    let Ok(tx)=thread::Builder::new().name("wbd-original-m4-tx".into())
        .spawn(move||{
            let cpu_origin=owner_thread_cpu_ns();
            let mut last_cpu_sample=Instant::now();
            let mut tx_storage=Vec::<TxDispatch>::with_capacity(32);
            let mut tx_pending=Vec::<(crate::memory::UniqueBuffer,usize)>::with_capacity(32);
            let mut tx_records=Vec::<crate::memory::FrozenRecord>::with_capacity(32);
            let mut tx_presentations=Vec::<Presentation>::with_capacity(32);
            let mut tx_actual_firstsend=Vec::<(wbd_types::RecordPn,u64)>::with_capacity(32);
            // One reusable TUN read slot, not 128 enlarged M1 owner slabs.
            let mut jumbo_read=vec![0u8;M0_TUN_IPV4_MAX];
            let mut jumbo_queue=VecDeque::<Vec<u8>>::with_capacity(M0_MAX_PENDING_JUMBO);
            let mut active_jumbo=None::<PendingOriginalJumbo>;
            while !stop_tx.load(Ordering::Acquire){
                if last_cpu_sample.elapsed()>=Duration::from_millis(100){
                    stats.tx_thread_cpu_ns.store(
                        owner_thread_cpu_ns().saturating_sub(cpu_origin),Ordering::Relaxed);
                    last_cpu_sample=Instant::now();
                }
                let tun_ready=loop_readiness(tun_fd,&stop_tx,10);
                #[cfg(feature="fec2_product_record")]
                let (fec_due,feedback_due)=tx_cell.lock().ok().map_or(
                    (false,false),|e|{
                        let now=loop_now();
                        let fec=e.fec2_live_tx.as_ref().is_some_and(|s|
                            s.report().queued_jobs>0 ||
                            s.next_deadline().is_some_and(|d|d<=now));
                        // Authenticated feedback is independently due, even
                        // for strictly one-way data with an idle local TUN.
                        let fb=e.feedback_queued.is_none() &&
                            e.rx_feedback.as_ref().is_some_and(|f|
                                f.lock().ok().and_then(|rx|rx.next_deadline())
                                .is_some_and(|d|d<=now));
                        (fec,fb)
                    });
                #[cfg(not(feature="fec2_product_record"))]
                let (fec_due,feedback_due)=(false,false);
                if !tun_ready && active_jumbo.is_none() &&
                    jumbo_queue.is_empty()&&!fec_due&&!feedback_due{
                    #[cfg(feature="fec2_product_record")]
                    if background_original_repair_once(&tx_cell,&stop_tx).is_err(){
                        stats.tx_error.fetch_add(1,Ordering::Relaxed);
                    }
                    continue
                }
                let slice_start=Instant::now();
                match background_tun_once(
                    &tx_cell,&tun,&stop_tx,ifindex,&tx_ifname,&mut tx_storage,
                    &mut tx_pending,&mut tx_records,&mut tx_presentations,
                    &mut tx_actual_firstsend,&tx_events,&mut jumbo_read,&mut jumbo_queue,&mut active_jumbo,
                    #[cfg(feature="fec2_product_record")]
                    &stats,
                    #[cfg(feature="fec2_product_record")]
                    fec_ingress_on
                ){
                    Ok(done)=>{
                        stats.tx.fetch_add(u64::from(done.copied),Ordering::Relaxed);
                        stats.tx_dropped.fetch_add(u64::from(done.definitely_unsent),Ordering::Relaxed);
                        stats.tx_uncertain.fetch_add(u64::from(done.uncertain),Ordering::Relaxed);
                        if done.backpressure{stats.tx_backpressure.fetch_add(1,Ordering::Relaxed);}
                        if done.failed{stats.tx_error.fetch_add(1,Ordering::Relaxed);}
                    }
                    Err(_)=>{stats.tx_error.fetch_add(1,Ordering::Relaxed);}
                }
                #[cfg(feature="fec2_product_record")]
                if background_original_repair_once(&tx_cell,&stop_tx).is_err(){
                    stats.tx_error.fetch_add(1,Ordering::Relaxed);
                }
                // Deterministic developer probe: the first real kernel
                // sendmmsg has COMPLETED and loans returned, but the next
                // 65KiB LINK turn has not sealed any fresh AEAD/PN. Stop
                // always overrides the barrier; no lock is held here.
                if active_jumbo.as_ref().is_some_and(
                    |p|p.issued>0 && !p.done()
                ) && stats.debug_pause_jumbo.load(Ordering::Acquire){
                    stats.debug_jumbo_paused.store(true,Ordering::Release);
                    while stats.debug_pause_jumbo.load(Ordering::Acquire)
                        && !stop_tx.load(Ordering::Acquire){
                        thread::sleep(Duration::from_millis(1));
                    }
                    stats.debug_jumbo_paused.store(false,Ordering::Release);
                }
                let _=slice_start;
            }
            active_jumbo.take();
            jumbo_queue.clear();
            stats.tx_thread_cpu_ns.store(
                owner_thread_cpu_ns().saturating_sub(cpu_origin),Ordering::Relaxed);
        })
    else{
        shutdown.store(true,Ordering::Release);
        // No worker may still deliver after a failed second spawn.
        e.phase=PH_STOPPING;
        drop(e);
        let _=rx.join();
        return INVALID
    };
    e.workers=Some(LoopWorkers{shutdown,rx,tx,route_events:events});
    OK
}
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub extern "C" fn wbd_m0_embedded_go_loop_start(handle:u64,ifindex:u32)->i32{
    start_loop(handle,ifindex)
}
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_loop_stats(
    h:u64,rx:*mut u64,tx:*mut u64,rx_err:*mut u64,tx_err:*mut u64)->i32{
    if rx.is_null()||tx.is_null()||rx_err.is_null()||tx_err.is_null(){return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    unsafe{
        rx.write(e.counters.rx.load(Ordering::Relaxed));
        tx.write(e.counters.tx.load(Ordering::Relaxed));
        rx_err.write(e.counters.rx_error.load(Ordering::Relaxed));
        tx_err.write(e.counters.tx_error.load(Ordering::Relaxed));
    }
    OK
}

// Developer-only device netlink witness; event revision is NOT MTU authority.
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_loop_route_events(
    h:u64,out_revision:*mut u64,out_healthy:*mut u32)->i32{
    if out_revision.is_null()||out_healthy.is_null(){return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    let Some(w)=e.workers.as_ref()else{return BAD_STAGE};
    let snapshot=w.route_events.snapshot();
    unsafe{
        out_revision.write(snapshot.revision);
        out_healthy.write(u32::from(snapshot.healthy));
    }
    OK
}

// Read-only original TLS session first-send M2 observation. Real DATA
// denominator comes only from the original kernel-copied prefix; until an
// authenticated reverse kind1 is wired, mature windows are UNKNOWN, not
// loss=0. No Go per-packet callback, no control or FEC2 activation.
#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_loop_firstsend_m2(
    h:u64,accepted:*mut u64,not_sent:*mut u64,uncertain:*mut u64,
    unknown_2s:*mut u64,unknown_8s:*mut u64,censored:*mut u32
)->i32{
    if accepted.is_null()||not_sent.is_null()||uncertain.is_null()
        ||unknown_2s.is_null()||unknown_8s.is_null()||censored.is_null(){return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.workers.is_none(){return BAD_STAGE}
    let Some(first)=e.normal_firstsend_m2.as_ref()else{return BAD_STAGE};
    let Ok(mut first)=first.lock()else{return BAD_STAGE};
    first.poll(loop_now());
    let counts=first.state.counters();
    unsafe{
        accepted.write(first.accepted);
        not_sent.write(counts.definitely_not_sent);
        uncertain.write(counts.uncertain_originals);
        unknown_2s.write(first.unknown_2s);
        unknown_8s.write(first.unknown_8s);
        censored.write(u32::from(first.censored));
    }
    OK
}
// Exact original credential-bound Normal/OFF native mode acknowledgment.
// This does not stage any FEC2 fixed/auto sender, nor activate a policy
// from untrusted 248B cold metadata; actual Go TLS+Detach owns the handle.
#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn verified_normal_off_epoch(ptr:*const u8,len:usize)->Result<[u8;16],i32>{
    if ptr.is_null()||len!=16{return Err(INVALID)}
    let mut epoch=[0u8;16];
    epoch.copy_from_slice(unsafe{std::slice::from_raw_parts(ptr,16)});
    if epoch==[0u8;16]{return Err(INVALID)}
    Ok(epoch)
}
#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
fn verified_normal_off_owner(e:&Entry,epoch:&[u8;16])->bool{
    e.phase==PH_ACTIVE&&!e.joining&&
        e.owner.normal_firstsend_identity()
        .is_some_and(|(_,real_epoch)|&real_epoch==epoch)
}
#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_normal_off_stage(
    h:u64,epoch:*const u8,epoch_len:usize,revision:u64
)->i32{
    if revision==0{return INVALID}
    let Ok(epoch)=verified_normal_off_epoch(epoch,epoch_len)else{return INVALID};
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if !verified_normal_off_owner(&e,&epoch){return BAD_STAGE}
    // Reject an old OFF revision relative to either a pending or an
    // already kernel-copied original-Go Fixed policy. A stale operator
    // intent can never wipe more recent data-plane authority.
    let latest=e.normal_off_applied_revision
        .max(e.fixed_pending.map_or(0,|(_,r)|r))
        .max(e.fixed_applied.map_or(0,|(_,r)|r));
    if revision<=latest{return INVALID}
    #[cfg(feature="m0_fec2_owner_probe")]
    if e.fixed_applied.is_some() && e.fec2_receipt_sender.is_some(){
        // Real source/repair is copied, but until all immutable original
        // sender shadows are settled by genuine M2 acknowledgments, even
        // an authenticated OFF request is not quiescent. Never rewrite
        // the Go-facing ACK simply to silence the FEC scheduler.
        if e.arena.report().loaned!=0||
            e.fec2_receipt_sender.as_ref().is_some_and(
                |s|s.shadow.outstanding()!=0
            ){return BAD_STAGE}
        if e.owner.apply_fec2_probe_quiescent_off(epoch,revision).is_err(){
            return BAD_STAGE
        }
    }
    #[cfg(feature="fec2_product_record")]
    {
        // Fixed remains PENDING until a remote authenticated M2/product
        // receipt. Even an OFF request must not discard old FEC plaintext
        // or a staged ciphertext while an M1 job or real M4 kernel copy is
        // unsettled. No queue acceptance is a quiescent proof.
        if !e.fec2_staged_pns.is_empty()||
            e.fec2_live_tx.as_ref().is_some_and(|s|{
                let r=s.report();
                r.open_bytes!=0||r.charged_bytes!=0||
                    r.queued_jobs!=0||r.outstanding_jobs!=0
            }){
            return BAD_STAGE
        }
    }
    // Only an authenticated, quiescent original owner can publish OFF.
    e.normal_off_applied_revision=revision;
    e.fixed_pending=None;
    e.fixed_applied=None;
    #[cfg(feature="fec2_product_record")]
    {
        e.fec2_rx_admit.store(false,Ordering::Release);
        if let Some(stream)=e.fec2_live_tx.as_mut(){stream.stop()}
        e.fec2_live_tx=None;
        e.fec2_staged_pns.clear();
    }
    OK
}
#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_normal_off_readback(
    h:u64,epoch:*const u8,epoch_len:usize,out:*mut u64
)->i32{
    if out.is_null(){return INVALID}
    let Ok(epoch)=verified_normal_off_epoch(epoch,epoch_len)else{return INVALID};
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if !verified_normal_off_owner(&e,&epoch){return BAD_STAGE}
    unsafe{out.write(e.normal_off_applied_revision)};
    OK
}

// Original-Go authenticated mode intent boundary, independent of the
// m0_fec2_owner_probe test-only ABI. The ordinary Rust owner can accept
// Fixed REQUEST/PENDING only for a negotiated TLS feature7 epoch, but has
// NO authority to call this APPLIED until real source+parity kernel copies
// and authenticated RX recovery are connected. No synthetic readiness flag.
#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_fixed_stage_pending(
    h:u64,epoch:*const u8,len:usize,profile:u8,revision:u64
)->i32{
    if profile>6 || revision==0{return INVALID}
    let Ok(epoch)=verified_normal_off_epoch(epoch,len)else{return INVALID};
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if !verified_normal_off_owner(&e,&epoch)
        ||e.protected_features!=7{return BAD_STAGE}
    let current=e.fixed_pending.map_or(e.normal_off_applied_revision,|(_,r)|r);
    if revision<=current || revision<=e.normal_off_applied_revision{return INVALID}
    #[cfg(feature="fec2_product_record")]
    {
        // A new policy is NOT allowed to truncate or reprofile any older
        // unretired FEC source/parity block; preserve old authority until
        // a genuine application control quiescent transition.
        if e.fec2_live_tx.as_ref().is_some_and(|s|
            s.report().charged_bytes!=0 || s.report().outstanding_jobs!=0
            || s.report().open_bytes!=0) || !e.fec2_staged_pns.is_empty(){
            return BAD_STAGE
        }
        if let Some(old)=e.fec2_live_tx.as_mut(){old.stop()}
        e.fec2_live_tx=None;
        e.fec2_copied_source=0;
        e.fec2_copied_repair=0;
        e.fec2_rx_admit.store(false,Ordering::Release);
    }
    e.fixed_pending=Some((profile,revision));
    // Private legacy FEC probe must never leave a different pending policy
    // overriding an original-Go Fixed revision in a feature-enabled test.
    #[cfg(feature="m0_fec2_owner_probe")]
    {e.fec2_probe_pending_policy=None;}
    OK
}
#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_fixed_pending_readback(
    h:u64,epoch:*const u8,len:usize,profile:*mut u8,
    revision:*mut u64,applied:*mut u32
)->i32{
    if profile.is_null()||revision.is_null()||applied.is_null(){return INVALID}
    let Ok(epoch)=verified_normal_off_epoch(epoch,len)else{return INVALID};
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if !verified_normal_off_owner(&e,&epoch)
        ||e.protected_features!=7{return BAD_STAGE}
    let Some((p,r,published))=e.fixed_pending.map(|(p,r)|(p,r,false))
        .or_else(||e.fixed_applied.map(|(p,r)|(p,r,true)))
    else{return BAD_STAGE};
    unsafe{
        profile.write(p);
        revision.write(r);
        // Only the M0 opt-in original M1+M3+M4 native real kernel copy
        // path may commit this; ordinary builds never publish APPLIED.
        applied.write(u32::from(published));
    }
    OK
}

// One authenticated original-Go TLS revision may become APPLIED only when
// M4 definitely copied source+parity and the SAME moved C2S AEAD opener
// delivered M2, with a genuinely matured/covered first-send denominator.
// This is NOT an external client-supplied success boolean.
#[cfg(all(feature="fec2_product_record",target_os="linux",
    any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_fixed_commit_mature_m2(
    h:u64,epoch:*const u8,len:usize,revision:u64
)->i32{
    if revision==0{return INVALID}
    let Ok(epoch)=verified_normal_off_epoch(epoch,len)else{return INVALID};
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if !verified_normal_off_owner(&e,&epoch)||
        e.protected_features!=7||
        !e.fixed_pending.is_some_and(|(_,r)|r==revision)||
        e.fec2_copied_source==0||e.fec2_copied_repair==0||
        !e.fec2_staged_pns.is_empty(){return BAD_STAGE}
    // Under continuing business FEC open/queued jobs are bounded and
    // expected; a global all-jobs-zero gate is a startup timing race.
    if e.fec2_live_tx.is_none(){return BAD_STAGE}
    let Some(first)=e.normal_firstsend_m2.as_ref()else{return BAD_STAGE};
    let covered={
        let Ok(mut m2)=first.lock()else{return BAD_STAGE};
        m2.poll(loop_now());
        // A 2s-mature authentic clean cohort, NOT all-source epoch totals.
        // Identity/capacity censorship is still a hard failure.
        m2.has_clean_fixed_m2()
    };
    if !covered{return BAD_STAGE}
    let Some(policy)=e.fixed_pending.take()else{return BAD_STAGE};
    e.fixed_applied=Some(policy);
    e.fec2_rx_admit.store(true,Ordering::Release);
    OK
}
// Sole original Go TLS M3 FEC RX/M4 TUN low-cost numeric-only counters.
// No alternate opener, per-packet trace, payload, fake success or hot lock.
#[cfg(all(feature="fec2_product_record",target_os="linux",
    any(target_arch="x86_64",target_arch="aarch64"),
    any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_loop_fec_rx_proof(
    h:u64,out:*mut u64,len:usize
)->i32{
    if out.is_null()||len!=11{return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.workers.is_none()||e.protected_features!=7{
        return BAD_STAGE
    }
    for (i,counter) in e.counters.fec_rx.iter().enumerate(){
        unsafe{out.add(i).write(counter.load(Ordering::Relaxed))};
    }
    OK
}
// Real post-TUN-loan Fixed source staging outcomes, exact six counters.
// Private native feature7 owner. No alternate input or packet classification.
#[cfg(all(feature="fec2_product_record",target_os="linux",
    any(target_arch="x86_64",target_arch="aarch64"),
    any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_loop_fec_m1_stage(
    h:u64,out:*mut u64,len:usize
)->i32{
    if out.is_null()||len!=6{return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.workers.is_none()||e.protected_features!=7{
        return BAD_STAGE
    }
    for (i,counter) in e.counters.fec_m1_stage.iter().enumerate(){
        unsafe{out.add(i).write(counter.load(Ordering::Relaxed))};
    }
    OK
}

// Read-only original M1 TUN intake evidence. This observes packet ownership
// BEFORE FEC source staging and distinguishes genuine post-read NoCapacity.
// No second device reader, data sampling or changed forwarding semantics.
#[cfg(all(feature="fec2_product_record",target_os="linux",
    any(target_arch="x86_64",target_arch="aarch64"),
    any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_loop_fec_m1_ingress(
    h:u64,out:*mut u64,len:usize
)->i32{
    if out.is_null()||len!=5{return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.workers.is_none()||e.protected_features!=7{
        return BAD_STAGE
    }
    for (i,counter) in e.counters.fec_m1_ingress.iter().enumerate(){
        unsafe{out.add(i).write(counter.load(Ordering::Relaxed))};
    }
    OK
}

// Read-only FEC M3→M4 IP class numbers from original copied packets.
// Private feature7 owner, exact 8 fields. Does not alter admission or TUN.
#[cfg(all(feature="fec2_product_record",target_os="linux",
    any(target_arch="x86_64",target_arch="aarch64"),
    any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_loop_fec_rx_ip_classes(
    h:u64,out:*mut u64,len:usize
)->i32{
    if out.is_null()||len!=8{return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.workers.is_none()||e.protected_features!=7{
        return BAD_STAGE
    }
    for (i,value) in e.counters.fec_rx_ip.iter().enumerate(){
        unsafe{out.add(i).write(value.load(Ordering::Relaxed))};
    }
    OK
}

// Explicit coverage counters are separate from UNKNOWN and kernel copied.
// A positive number requires actual original C2S kind1 received, opened
// with the moved M3 replay state and pinned into M2, not an RX count.
#[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_loop_firstsend_m2_coverage(
    h:u64,covered_2s:*mut u64,covered_8s:*mut u64,
    reverse_reports:*mut u64,censored:*mut u32
)->i32{
    if covered_2s.is_null()||covered_8s.is_null()
        ||reverse_reports.is_null()||censored.is_null(){return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.workers.is_none(){return BAD_STAGE}
    let Some(first)=e.normal_firstsend_m2.as_ref()else{return BAD_STAGE};
    let Ok(mut first)=first.lock()else{return BAD_STAGE};
    first.poll(loop_now());
    unsafe{
        covered_2s.write(first.covered_2s);
        covered_8s.write(first.covered_8s);
        reverse_reports.write(first.authenticated_reverse_reports);
        censored.write(u32::from(first.censored));
    }
    OK
}
// M0 developer-only test rendezvous. A real original M4 sendmmsg prefix
// must finish before the concurrent Go netlink MTU mutation is permitted.
// Never blocks under the M0 registry or owner lock; no synthetic driver
// result or alternate packet sender exists.
#[cfg(all(feature="m0_v4_probe",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_loop_debug_pause_jumbo(
    handle:u64,enabled:u32,paused:*mut u32,loaned:*mut u32
)->i32{
    if paused.is_null()||loaned.is_null()||enabled>1{return INVALID}
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(mut e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.workers.is_none(){return BAD_STAGE}
    e.counters.debug_pause_jumbo.store(enabled!=0,Ordering::Release);
    unsafe{
        paused.write(u32::from(e.counters.debug_jumbo_paused.load(Ordering::Acquire)));
        loaned.write(e.arena.report().loaned as u32);
    }
    OK
}
// Developer-mode per-worker *actual Linux thread CPU time* for 10s+60s
// receipt. Combined process CPU includes Go sender/reader; independent
// exact user-vs-kernel attribution within that residual is NOT available.
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_loop_route_refresh(
    handle:u64,out:*mut u64)->i32{
    if out.is_null(){return INVALID}
    let Ok(cell)=session(handle)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    unsafe{out.write(e.counters.route_refresh.load(Ordering::Relaxed))}
    OK
}
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_loop_thread_cpu(
    h:u64,rx_ns:*mut u64,tx_ns:*mut u64)->i32{
    if rx_ns.is_null()||tx_ns.is_null(){return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    unsafe{
        rx_ns.write(e.counters.rx_thread_cpu_ns.load(Ordering::Relaxed));
        tx_ns.write(e.counters.tx_thread_cpu_ns.load(Ordering::Relaxed));
    }
    OK
}

// Query the real M1/M3 original Rust owner Route/PeerMSS budget after the
// credential-verified private Go control Commit and exact M4 interface bind.
// This value is NOT a cold-self-attested cap or a way to mutate the budget.
#[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_embedded_go_observed_tx_ipv4_mtu(
    h:u64,ifindex:u32,out:*mut u32)->i32{
    if out.is_null(){return INVALID}
    let Ok(cell)=session(h)else{return UNKNOWN};
    let Ok(e)=cell.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.tun_sink.is_none()||e.raw_rx.is_none(){
        return BAD_STAGE
    }
    let Some(ifname)=e.raw_ifname.as_deref()else{return BAD_STAGE};
    let route=e.owner.observe_linux_normal_off_route_budget(
        ifname,ifindex,Ipv4Addr::from(
            if e.server_side{e.flow.client_ip}else{e.flow.server_ip}
        ));
    let Ok(route)=route else{return INVALID};
    let Ok(limit)=u32::try_from(route.frame.single_business_payload_mtu)
    else{return INVALID};
    if limit<28{return INVALID}
    unsafe{out.write(limit)};
    OK
}
#[cfg(test)]
mod tests{
    use super::*;
    #[cfg(all(target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    #[test]
    fn m0_original_wbc4_authenticated_kind1_m2_covered_vs_uncovered_and_replay_boundary(){
        use wbd_types::{LaneKey,TunnelKey,RecordPn};
        use crate::v4_owner_crypto::AuthenticatedNormalKind1;
        let lane=LaneKey{tunnel:TunnelKey{slot:13,generation:5},slot:1,generation:5};
        let mut first=NormalFirstSendM2::new(lane,[7;16],true,MonoNs(0)).unwrap();
        let send=TxTurnCompletion{copied:2,..Default::default()};
        first.on_real_kernel_turn(
            &[(RecordPn(7),100),(RecordPn(8),100)],send,MonoNs(100));
        assert_eq!(first.accepted,2);
        let mut bitmap=[0u8;32];
        bitmap[0]=1u8<<7; // PN7 positive, PN8 explicitly missing
        let positive=AuthenticatedNormalKind1{
            reverse_record_pn:0,receipt:wbd_codec::Receipt{
                largest_data_pn:8,ack_delay_us:0,report_seq:1,
                pages:vec![wbd_codec::ReceiptPage{base_pn:0,bitmap}],
            }
        };
        let wire=wbd_codec::encode_control(
            &[wbd_codec::ControlTlv::Receipt(positive.receipt.clone())],512
        ).unwrap();
        assert_eq!(wbd_codec::decode_control(&wire,512).unwrap().len(),1);
        first.on_original_authenticated_reverse(positive,MonoNs(200)).unwrap();
        first.poll(MonoNs(2_000_000_200));
        assert_eq!(first.authenticated_reverse_reports,1);
        assert_eq!(first.covered_2s,2);
        assert_eq!(first.unknown_2s,0);
        first.poll(MonoNs(8_000_000_200));
        assert_eq!(first.covered_8s,2);
        assert_eq!(first.unknown_8s,0);
        assert!(!first.censored);
        // Plain wire, malformed WBC4, and forged kind are NEVER accepted
        // by this M2 bridge. Only the moved owner's AEAD opener constructs
        // AuthenticatedNormalKind1; these checks are pure post-open logic.
        assert!(wbd_codec::decode_control(b"garbage",512).is_err());
        assert!(wbd_codec::decode_control(&wire[..wire.len()-1],512).is_err());
        let wrong_kind=wbd_codec::encode_control(
            &[wbd_codec::ControlTlv::LegacyHealth(vec![1])],512
        ).unwrap();
        assert!(matches!(
            wbd_codec::decode_control(&wrong_kind,512).unwrap()[0],
            wbd_codec::ControlTlv::LegacyHealth(_)
        ));
    }

    #[cfg(all(feature="fec2_product_record",target_os="linux",
        any(target_arch="x86_64",target_arch="aarch64")))]
    #[test]
    fn m0_original_fixed_m2_continuous_clean_cohort_unknown_resets_without_forgery(){
        use wbd_types::{LaneKey,TunnelKey,RecordPn};
        use crate::v4_owner_crypto::AuthenticatedNormalKind1;
        let lane=LaneKey{tunnel:TunnelKey{slot:102,generation:3},slot:1,generation:3};
        let mut first=NormalFirstSendM2::new(lane,[9;16],false,MonoNs(0)).unwrap();
        assert!(!first.has_clean_fixed_m2());
        let copied=TxTurnCompletion{copied:1,..Default::default()};
        first.on_real_kernel_turn(&[(RecordPn(7),1200)],copied,MonoNs(100));
        first.poll(MonoNs(2_000_000_200));
        assert_eq!(first.unknown_2s,1);
        assert!(!first.has_clean_fixed_m2());
        first.on_real_kernel_turn(&[(RecordPn(8),1200)],copied,MonoNs(2_100_000_000));
        let mut bitmap=[0u8;32];
        bitmap[1]=1;
        first.on_original_authenticated_reverse(AuthenticatedNormalKind1{
            reverse_record_pn:3,receipt:wbd_codec::Receipt{
                largest_data_pn:8,ack_delay_us:0,report_seq:1,
                pages:vec![wbd_codec::ReceiptPage{base_pn:0,bitmap}],
            },
        },MonoNs(2_200_000_000)).unwrap();
        first.poll(MonoNs(4_100_000_100));
        assert_eq!(first.unknown_2s,1);
        assert_eq!((first.clean_2s,first.clean_positive_2s),(1,1));
        assert!(first.has_clean_fixed_m2());
        first.on_real_kernel_turn(&[(RecordPn(9),1200)],copied,MonoNs(4_200_000_000));
        first.poll(MonoNs(6_200_000_100));
        assert!(!first.has_clean_fixed_m2());
        first.censored=true;
        assert!(!first.has_clean_fixed_m2());
    }
    #[cfg(all(feature="fec2_product_record",target_os="linux",
        any(target_arch="x86_64",target_arch="aarch64")))]
    #[test]
    fn m0_original_repair_block_reason_classifier_is_stable(){
        use wbd_recovery::{BudgetError as B,GlobalRepairError as G};
        assert_eq!(original_repair_reserve_block_reason(G::Local(B::BurstPaced)),
            OriginalRepairBlockReason::Burst);
        assert_eq!(original_repair_reserve_block_reason(G::Local(B::QuotaExhausted)),
            OriginalRepairBlockReason::Quota);
        assert_eq!(original_repair_reserve_block_reason(G::Local(B::NoCapacity)),
            OriginalRepairBlockReason::Capacity);
        assert_eq!(original_repair_reserve_block_reason(G::PendingCapacity),
            OriginalRepairBlockReason::Capacity);
        assert_eq!(original_repair_reserve_block_reason(G::GlobalCap),
            OriginalRepairBlockReason::Capacity);
        assert_eq!(original_repair_reserve_block_reason(G::StaleCandidate),
            OriginalRepairBlockReason::Stale);
        assert_eq!(original_repair_reserve_block_reason(G::StaleGrant),
            OriginalRepairBlockReason::Stale);
        assert_eq!(original_repair_reserve_block_reason(G::Local(B::InvalidFrame)),
            OriginalRepairBlockReason::LocalOther);
        assert_eq!(original_repair_reserve_block_reason(G::WrongReceiptScope),
            OriginalRepairBlockReason::GlobalOther);
    }
    #[test]
    fn ready_only_batch_0_1_32_33_and_failure_do_not_wait(){
        use std::cell::Cell;
        let stop=AtomicBool::new(false);
        let count=Cell::new(0usize);
        let polls=Cell::new(0usize);
        // First packet never has to poll a second time. A solitary ready
        // packet terminates immediately at the nonblocking next probe.
        let n=ready_only_slice(&stop,||{polls.set(polls.get()+1);false},
            ||{count.set(count.get()+1);true},||true);
        assert_eq!((n,count.get(),polls.get()),(1,1,1));
        for offered in [1usize,32,33] {
            let complete=Cell::new(0usize);
            let n=ready_only_slice(&stop,
                ||complete.get()<offered,
                ||{complete.set(complete.get()+1);true},
                ||true);
            assert_eq!(n,offered.min(32));
            assert_eq!(complete.get(),offered.min(32));
        }
        let complete=Cell::new(0usize);
        let n=ready_only_slice(&stop,||true,||{
            complete.set(complete.get()+1);
            complete.get()!=3
        },||true);
        assert_eq!((n,complete.get()),(3,3)); // error ends burst
        let n=ready_only_slice(&stop,||true,||true,||false);
        assert_eq!(n,8); // budget is checked once per eight packets
        stop.store(true,Ordering::Release);
        let n=ready_only_slice(&stop,||panic!("unexpected poll"),
            ||panic!("unexpected packet"),||true);
        assert_eq!(n,0);
    }
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    #[test]
    fn r1_m0_live_authenticated_seq32_anchor_wrap_and_untrusted_no_advance(){
        // Same helper and wbd-platform::extend_seq32 used by background_raw_once:
        // Go bootstrap is near wrap and each accepted original LINK frame
        // advances the trusted reference without a real 2GiB allocation.
        let initial=0xffff_ff00u64;
        let first=extend_seq32(initial,0xffff_ff00).unwrap();
        let crossed=authenticated_rx_anchor(initial,first,0x200,1).unwrap();
        assert_eq!(crossed,0x1_0000_0100);
        assert_eq!(extend_seq32(crossed,0x100),Ok(crossed));
        let next=extend_seq32(crossed,0x100).unwrap();
        let ahead=authenticated_rx_anchor(crossed,next,0x180,1).unwrap();
        assert_eq!(ahead,0x1_0000_0280);
        // These exact same apparent seq32 bits must remain high-generation
        // candidates even after advancing >half-space beyond the old Go base.
        let far=0x1_8000_1000u64;
        assert!(far-initial>0x8000_0000);
        assert_ne!(extend_seq32(initial,far as u32),Ok(far));
        assert_eq!(extend_seq32(far,far as u32),Ok(far));
        // Untrusted and replay packets cannot poison the owner anchor.
        assert_eq!(authenticated_rx_anchor(ahead,far,512,0),Some(ahead));
        assert_eq!(authenticated_rx_anchor(ahead,far,512,2),Some(ahead));
        assert_eq!(authenticated_rx_anchor(ahead,ahead-128,64,1),Some(ahead));
        assert_eq!(authenticated_rx_anchor(ahead,u64::MAX,2,1),None);
        assert_eq!(extend_seq32(0,0x8000_0000),
            Err(wbd_platform::rx_ipv4_tcp::SeqExtendError::HalfSpaceAmbiguous));
    }
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    #[test]
    fn m0_link_65k_original_owner_cross_turn_48_fragment_gate_and_no_hol(){
        use wbd_codec::link_reassembly::{
            ReassemblyTable,ReassemblyScope,LinkDirection,LinkDelivery
        };
        // Maximum allowed inner logical LINK datagram, not a spoofed
        // shortened test record. Original M3 LINK20 uses 1400B budget.
        let original=(0..65_535usize)
            .map(|i|((i*19+7)%251) as u8).collect::<Vec<_>>();
        let scope=|id|ReassemblyScope{
            tunnel_epoch:81,direction:LinkDirection::ServerToClient,
            packet_id_ext:id
        };
        let mut producer=LinkPacketPlan::new(
            &original,1400,LinkMode::FixedOff,41
        ).expect("legally bounded original LINK message");
        assert_eq!(producer.total_frames(),48);
        let mut m3=ReassemblyTable::new(1400,1400,LinkMode::FixedOff)
            .expect("original bounded M3 reassembly table");
        for turn in 0u64..48{
            let wire=producer.issue_next(1400).unwrap()
                .expect("exactly one issued LINK frame per owner turn");
            assert!(wire.len()<=1400);
            // Authentication is a REQUIRED call-site precondition. The
            // isolated parser+reassembly here does not counterfeit M3
            // AEAD or claim protected Go TLS original kernel delivery.
            let observation=m3.push_after_record_auth(
                &wire,scope(41),turn*10
            ).unwrap();
            if turn<47{
                assert_eq!(observation,LinkDelivery::Pending);
                assert_eq!(
                    m3.push_after_record_auth(b"small-after-fragment",
                        scope(0),turn*10+1).unwrap(),
                    LinkDelivery::Ordinary(b"small-after-fragment"),
                    "incomplete 65KiB packet must not HOL ordinary DATA"
                );
            }else{
                assert_eq!(
                    observation,LinkDelivery::Reassembled(original.clone())
                );
            }
        }
        assert!(producer.issue_next(1400).unwrap().is_none());
        assert_eq!(m3.state().assemblies,0);

        // Stop/timeout mid-stream: retiring an incomplete 65KiB frame
        // scope must not replay a late tail or stop small complete data.
        let mut abandoned=LinkPacketPlan::new(
            &original,1400,LinkMode::FixedOff,42
        ).unwrap();
        for turn in 0u64..12{
            let frame=abandoned.issue_next(1400).unwrap().unwrap();
            assert_eq!(m3.push_after_record_auth(
                &frame,scope(42),1000+turn*10
            ),Ok(LinkDelivery::Pending));
        }
        assert_eq!(m3.state().assemblies,1);
        m3.expire(6200);
        assert_eq!(m3.state().assemblies,0);
        assert_eq!(
            m3.push_after_record_auth(
                &abandoned.issue_next(1400).unwrap().unwrap(),
                scope(42),6201
            ),
            Ok(LinkDelivery::Discarded)
        );
        assert_eq!(
            m3.push_after_record_auth(b"independent",scope(0),6202),
            Ok(LinkDelivery::Ordinary(b"independent"))
        );

        // Actual ORIGINAL M0 sending materializer is still capped by
        // one 32-entry owner turn. 48 > 32 MUST fail before any slab
        // acquisition, PN seal, M4 syscall or packet half-admission.
        // This is a detected PRE-PRODUCT BLOCKER, not a full 65KiB PASS.
        let mut owner=Arena::new(244,32,2048,32,96_000).unwrap();
        assert_eq!(
            stage_bounded_original_link(
                &mut owner,&original,1400,43,32
            ).err(),Some(FULL)
        );
        owner.drain_returns();
        assert_eq!(owner.report().loaned,0);
        let healthy=vec![0x4a;700];
        let one=stage_bounded_original_link(
            &mut owner,&healthy,1400,44,32
        ).unwrap();
        assert_eq!(one.len(),1);
        drop(one);
        owner.drain_returns();
        assert_eq!(owner.report().loaned,0);
        println!(
            "M0_LINK_65K_CROSS_TURN_48_CODED_FRAGMENTS_NOHOL_PASS \
             original_owner_32_slot_gate=BLOCKED_FAIL_CLOSED \
             staged_partial=0 loan_leak=0 real_tls_kernel=NOT_RUN"
        );
    }

    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    #[test]
    fn m0_link_original_m1_arena_two_turn_65k_32_plus_16_stop_mtu_nohol(){
        use wbd_codec::link_reassembly::{
            ReassemblyTable,ReassemblyScope,LinkDirection,LinkDelivery
        };
        let data=(0..65_535usize).map(|i|((i*23+5)%251) as u8)
            .collect::<Vec<_>>();
        let scope=|packet:u64|ReassemblyScope{
            tunnel_epoch:91,direction:LinkDirection::ServerToClient,
            packet_id_ext:packet
        };
        let mut original_m1=Arena::new(410,32,2048,32,128_000).unwrap();
        let mut plan=LinkPacketPlan::new(
            &data,1400,LinkMode::FixedOff,91
        ).unwrap();
        let mut original_m3=ReassemblyTable::new(
            1400,1400,LinkMode::FixedOff
        ).unwrap();
        assert_eq!(plan.total_frames(),48);
        for (turn,expected) in [(0usize,32usize),(1,16)]{
            let staged=stage_next_original_link_turn(
                &mut original_m1,&mut plan,1400,32
            ).unwrap();
            assert_eq!(staged.len(),expected);
            for (idx,(mut loan,len)) in staged.into_iter().enumerate(){
                let frame=&loan.writable()[14..14+len];
                let opened=original_m3.push_after_record_auth(
                    frame,scope(91),(turn*32+idx) as u64
                ).unwrap();
                if turn==1 && idx==15{
                    assert_eq!(opened,LinkDelivery::Reassembled(data.clone()));
                }else{
                    assert_eq!(opened,LinkDelivery::Pending);
                    assert_eq!(
                        original_m3.push_after_record_auth(
                            b"unrelated-small-packet",scope(0),
                            (turn*32+idx) as u64
                        ),
                        Ok(LinkDelivery::Ordinary(b"unrelated-small-packet"))
                    );
                }
            }
            original_m1.drain_returns();
            assert_eq!(original_m1.report().loaned,0);
            assert_eq!(plan.issued(),if turn==0{32}else{48});
        }
        assert!(stage_next_original_link_turn(
            &mut original_m1,&mut plan,1400,32
        ).unwrap().is_empty());
        assert_eq!(original_m3.state().assemblies,0);

        let mut abandoned=LinkPacketPlan::new(
            &data,1400,LinkMode::FixedOff,92
        ).unwrap();
        let prefix=stage_next_original_link_turn(
            &mut original_m1,&mut abandoned,1400,12
        ).unwrap();
        assert_eq!(prefix.len(),12);
        drop(prefix);
        original_m1.drain_returns();
        assert_eq!(original_m1.report().loaned,0);
        assert_eq!(
            stage_next_original_link_turn(
                &mut original_m1,&mut abandoned,1300,32
            ).err(),Some(INVALID)
        );
        assert!(abandoned.is_abandoned());
        assert_eq!(
            stage_next_original_link_turn(
                &mut original_m1,&mut abandoned,1400,32
            ).err(),Some(FULL)
        );
        assert_eq!(original_m1.report().loaned,0);
        let mut healthy=LinkPacketPlan::new(
            b"healthy-following-packet",1400,LinkMode::FixedOff,93
        ).unwrap();
        let loans=stage_next_original_link_turn(
            &mut original_m1,&mut healthy,1400,32
        ).unwrap();
        assert_eq!(loans.len(),1);
        drop(loans);
        original_m1.drain_returns();
        assert_eq!(original_m1.report().loaned,0);
        println!("M0_ORIGINAL_M1_65K_TWO_TURN_LOANS_32_PLUS_16_MTU_STOP_NOHOL_PASS production_tun_worker=WIRING_NOT_PROVEN_BY_THIS_TEST real_kernel=NOT_RUN");
    }


    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    #[test]
    fn m0_background_owned_jumbo_persists_65k_generation_32_16_nohol_mtu_stop(){
        use wbd_codec::link_reassembly::{
            ReassemblyTable,ReassemblyScope,LinkDirection,LinkDelivery
        };
        let input=(0..65_535usize).map(|i|((i*17+9)%251) as u8)
            .collect::<Vec<_>>();
        let mut owner=Arena::new(715,32,2048,32,128_000).unwrap();
        let mut pending=PendingOriginalJumbo::new(
            input.clone(),715,1400,715,22
        ).unwrap();
        assert_eq!((pending.generation,pending.route_event_revision),(715,22));
        assert_eq!(pending.total,48);
        let mut table=ReassemblyTable::new(1400,1400,LinkMode::FixedOff).unwrap();
        let scope=ReassemblyScope{
            tunnel_epoch:715,direction:LinkDirection::ServerToClient,
            packet_id_ext:715,
        };
        for (round,wanted) in [(0usize,32usize),(1,16)]{
            let parts=pending.stage_turn(&mut owner,1400,32).unwrap();
            assert_eq!(parts.len(),wanted);
            for (i,(mut slot,len)) in parts.into_iter().enumerate(){
                let received=table.push_after_record_auth(
                    &slot.writable()[14..14+len],scope,(round*32+i) as u64
                ).unwrap();
                if round==1 && i==15{
                    assert_eq!(received,LinkDelivery::Reassembled(input.clone()));
                }else{
                    assert_eq!(received,LinkDelivery::Pending);
                    assert_eq!(
                        table.push_after_record_auth(
                            b"small-unrelated",ReassemblyScope{
                                tunnel_epoch:715,
                                direction:LinkDirection::ServerToClient,
                                packet_id_ext:716
                            },(round*32+i) as u64
                        ),Ok(LinkDelivery::Ordinary(b"small-unrelated"))
                    );
                }
            }
            owner.drain_returns();
            assert_eq!(owner.report().loaned,0);
            assert_eq!(pending.issued,if round==0{32}else{48});
        }
        assert!(pending.done());
        assert!(pending.stage_turn(&mut owner,1400,32).unwrap().is_empty());
        let mut shrunk=PendingOriginalJumbo::new(input,716,1400,715,22).unwrap();
        let prefix=shrunk.stage_turn(&mut owner,1400,12).unwrap();
        assert_eq!(prefix.len(),12);
        drop(prefix);
        owner.drain_returns();
        assert_eq!(owner.report().loaned,0);
        assert_eq!(shrunk.stage_turn(&mut owner,1300,32).err(),Some(INVALID));
        // A failed/uncertain kernel turn or Stop drops the generation-bound
        // source, not an alternate-stride tail with the same packet ID.
        let mut active=Some(shrunk);
        active.take();
        assert!(active.is_none());
        assert_eq!(owner.report().loaned,0);
        println!("M0_BACKGROUND_OWNED_JUMBO_65K_32_PLUS_16_MTU_STOP_NOHOL_NATIVE_PASS real_tun_tls_m4_kernel=NOT_RUN");
    }

    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    #[test]
    fn m0_pending_jumbo_midflight_scope_stop_prefix_matrix(){
        use wbd_platform::linux_batch::{KernelSendReport,KernelSendSignal as S};
        use wbd_platform::{TxBatchOutcome,TxError};
        let payload=(0..65_535usize).map(|i|(i%251) as u8)
            .collect::<Vec<_>>();
        let mut arena=Arena::new(811,32,2048,32,128_000).unwrap();
        let mut tested=0usize;
        // Each independent source has one real original M1 slab turn issued
        // and then a typed original M4 completion outcome. This tests
        // deterministic owner retirement, not a synthetic network PASS.
        for prefix in 0..=32usize{
            for uncertain in [false,true]{
                if prefix==32 && uncertain{continue}
                let mut plan=PendingOriginalJumbo::new(
                    payload.clone(),811+tested as u32,1400,811,27
                ).unwrap();
                assert_eq!(plan.total,48);
                assert!(plan.valid_for(811,27,1400));
                // Changing either direction of frame MTU, generation or
                // route revision MUST never resume the same packet ID.
                assert!(!plan.valid_for(811,27,1399));
                assert!(!plan.valid_for(811,27,1401));
                assert!(!plan.valid_for(812,27,1400));
                assert!(!plan.valid_for(811,28,1400));
                let parts=plan.stage_turn(&mut arena,1400,32).unwrap();
                assert_eq!((parts.len(),plan.issued),(32,32));
                drop(parts);
                arena.drain_returns();
                assert_eq!(arena.report().loaned,0);
                // The only all-copied leg can continue; all partial,
                // uncertain, EAGAIN, and Stop legs permanently retire.
                let report=KernelSendReport{
                    outcome:TxBatchOutcome{
                        accepted_prefix:prefix,
                        uncertain_index:uncertain.then_some(prefix),
                        error:if prefix==32{None}else if uncertain{
                            Some(TxError::IoUncertain)
                        }else{Some(TxError::WouldBlock)},
                    },
                    signal:if prefix==32{S::None}else if uncertain{
                        S::AmbiguousCompletion
                    }else{S::Backpressure},
                };
                let result=classify_tx_turn(Some(&report),32,false);
                assert_eq!(result.copied,prefix as u32);
                assert_eq!(result.uncertain,u32::from(uncertain));
                assert_eq!(result.copied+result.uncertain+
                    result.definitely_unsent,32);
                assert_eq!(plan.retire_after_turn(result,false),prefix!=32);
                assert!(plan.retire_after_turn(result,true));
                // No same-ID late tail after Stop or any uncertain prefix.
                let mut active=Some(plan);
                if active.as_ref().unwrap().retire_after_turn(result,true){
                    active.take();
                }
                assert!(active.is_none());
                assert_eq!(arena.report().loaned,0);
                tested+=1;
            }
        }
        let mut accepted=PendingOriginalJumbo::new(
            payload,999,1400,811,27
        ).unwrap();
        drop(accepted.stage_turn(&mut arena,1400,32).unwrap());
        arena.drain_returns();
        assert_eq!(arena.report().loaned,0);
        let full=classify_tx_turn(Some(&KernelSendReport{
            outcome:TxBatchOutcome::copied_all(32),signal:S::None
        }),32,false);
        assert!(!accepted.retire_after_turn(full,false));
        assert_eq!(accepted.stage_turn(&mut arena,1400,32).unwrap().len(),16);
        arena.drain_returns();
        assert_eq!(arena.report().loaned,0);
        assert!(accepted.done());
        assert!(accepted.retire_after_turn(full,false));
        assert_eq!(tested,65);
        println!("M0_ORIGINAL_JUMBO_MIDFLIGHT_PREFIX_SCOPE_STOP_MATRIX_PASS tested=65 generation=1 mtu_plus_minus=1 route_revision=1 loans=0 real_kernel=NOT_RUN");
    }
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    #[test]
    fn m0_link_materialization_never_admits_half_packet_on_arena_failure(){
        // Actual M1 unique loans + original M3 LINK20 planner. A synthetic
        // 1500B logical input needs THREE fixed-600B framed slabs.
        let original=(0..1500usize).map(|i|(i%251) as u8).collect::<Vec<_>>();
        let mut small=Arena::new(141,2,2048,2,16_000).unwrap();
        assert_eq!(stage_bounded_original_link(
            &mut small,&original,600,41,32).err(),Some(FULL));
        // Both preallocated loans were returned; zero actual owner seals or
        // AEAD packet-number commits could have occurred.
        small.drain_returns();
        assert_eq!(small.report().loaned,0);
        assert_eq!(stage_bounded_original_link(
            &mut small,&original,600,41,2).err(),Some(FULL));
        small.drain_returns();
        assert_eq!(small.report().loaned,0);

        let mut full=Arena::new(142,4,2048,4,32_000).unwrap();
        let staged=stage_bounded_original_link(
            &mut full,&original,600,41,3).unwrap();
        assert_eq!(staged.len(),3);
        assert_eq!(full.report().loaned,3);
        let parts=staged.iter().map(|(slot,n)|slot.origin()).collect::<Vec<_>>();
        assert_eq!(parts.len(),3);
        let mut table=Vec::new();
        for (mut slot,n) in staged{
            let bytes=slot.writable()[14..14+n].to_vec();
            assert!(matches!(
                wbd_codec::link_fec_wire::inspect_link(
                    &bytes,600,LinkMode::FixedOff
                ),
                Ok(wbd_codec::link_fec_wire::LinkView::Fragment(_))
            ));
            table.push(bytes);
        }
        assert_eq!(table.len(),3);
        for (index,wire) in table.iter().enumerate(){
            let wbd_codec::link_fec_wire::LinkView::Fragment(frag)=
                wbd_codec::link_fec_wire::inspect_link(
                    wire,600,LinkMode::FixedOff
                ).unwrap() else{panic!("not a LINK fragment")};
            assert_eq!(usize::from(frag.index),index);
            assert_eq!(usize::from(frag.count),3);
            assert_eq!(frag.packet_id,41);
        }
        full.drain_returns();
        assert_eq!(full.report().loaned,0);
        assert_eq!(stage_bounded_original_link(
            &mut full,&original,600,0,3).err(),Some(INVALID));
        assert_eq!(stage_bounded_original_link(
            &mut full,&original,20,41,3).err(),Some(INVALID));
        assert_eq!(full.report().loaned,0);
    }
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    #[test]
    fn r1_m0_original_data_return_budget_yields_at_64_128_33(){
        // Exactly the M1 owner slab and ReturnPath used in authenticated
        // real Linux data, not a synthetic stand-in or another lock.
        let mut arena=Arena::new(31,128,256,32,256_000).unwrap();
        let loans=(0..128).map(|_|arena.allocate().unwrap()).collect::<Vec<_>>();
        drop(loans); // mpsc(32) + bounded fallback; 128 real unique loans.
        assert_eq!(drain_data_turn_returns(&mut arena),64);
        assert_eq!(drain_data_turn_returns(&mut arena),64);
        assert_eq!(drain_data_turn_returns(&mut arena),0);
        assert_eq!(arena.report().loaned,0);
        let loans=(0..33).map(|_|arena.allocate().unwrap()).collect::<Vec<_>>();
        drop(loans);
        assert_eq!(drain_data_turn_returns(&mut arena),33);
        assert_eq!(drain_data_turn_returns(&mut arena),0);
        assert_eq!(arena.report().loaned,0);
        // Control / Stop still uses the full drain and retirement fence.
        let stopped=arena.stop();
        assert_eq!(stopped.loaned,0);
    }
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    #[test]
    fn m0_route_refresh_rearms_real_m4_only_after_change_or_invalidation(){
        assert!(!raw_driver_reopen_on_route_change(false,0,65536,65536));
        assert!(!raw_driver_reopen_on_route_change(true,3,65536,65536));
        assert!(!raw_driver_reopen_on_route_change(false,3,1500,65536));
        assert!(raw_driver_reopen_on_route_change(false,3,65536,65536));
        assert!(raw_driver_reopen_on_route_change(false,3,65536,1500));
        assert!(!raw_driver_reopen_on_route_change(false,3,65536,0));
    }
    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    #[test]
    fn m0_tx_turn_completion_preserves_prefix_tail_and_typed_path(){
        use wbd_platform::linux_batch::{KernelSendSignal as S,KernelSendReport};
        use wbd_platform::{TxBatchOutcome,TxError};
        let full=KernelSendReport{outcome:TxBatchOutcome::copied_all(32),signal:S::None};
        assert_eq!(classify_tx_turn(Some(&full),32,false),
            TxTurnCompletion{copied:32,..Default::default()});
        assert_eq!(classify_tx_turn(Some(&KernelSendReport{outcome:TxBatchOutcome::copied_all(0),signal:S::None}),0,false),
            TxTurnCompletion::default());
        let examples=[
            (1,0,None,S::Backpressure,0,1,0,true,false),
            (32,5,None,S::PartialErrnoUnavailable,5,27,0,false,false),
            (33,32,None,S::Backpressure,32,1,0,true,false),
            (32,5,Some(5),S::AmbiguousCompletion,5,26,1,false,false),
            (32,7,None,S::MtuExceeded,7,25,0,false,true),
            (32,0,None,S::PreflightRejected,0,32,0,false,false),
            (32,0,None,S::DeviceUnavailable,0,32,0,false,true),
            (32,0,None,S::RouteUnavailable,0,32,0,false,true),
            (32,0,None,S::Stopping,0,32,0,false,false),
        ];
        for (total,prefix,unknown,signal,copied,dropped,uncertain,backpressure,invalidate) in examples {
            let report=KernelSendReport{
                outcome:TxBatchOutcome{accepted_prefix:prefix,
                    uncertain_index:unknown,error:Some(if unknown.is_some(){
                        TxError::IoUncertain
                    }else if backpressure{TxError::WouldBlock}else{TxError::IoFailed})},
                signal
            };
            let done=classify_tx_turn(Some(&report),total,false);
            assert_eq!((done.copied,done.definitely_unsent,done.uncertain,
                done.backpressure,done.invalidate_route),
                (copied,dropped,uncertain,backpressure,invalidate));
            assert!(done.failed);
            assert_eq!(done.copied+done.definitely_unsent+done.uncertain,total as u32);
        }
        assert!(classify_tx_turn(Some(&full),32,true).failed);
    }
    #[cfg(all(feature="m0_fec2_owner_probe",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    #[test]
    fn m0_fec2_original_m4_m2_batch_0_32_unknown_prefix_never_refunds(){
        use wbd_platform::linux_batch::{KernelSendReport,KernelSendSignal as S};
        use wbd_platform::{TxBatchOutcome,TxError};
        // Exhaust every legitimate size, accepted prefix, no-uncertain
        // and unknown-at-first-nonaccepted variations. NotSent is NEVER
        // derived merely from a native kernel return or elapsed timeout.
        let mut checked=0usize;
        for total in 0..=32{
            for copied in 0..=total{
                for unknown in [None,(copied<total).then_some(copied)]{
                    let report=KernelSendReport{
                        outcome:TxBatchOutcome{
                            accepted_prefix:copied,uncertain_index:unknown,
                            error:if copied==total&&unknown.is_none(){None}
                                  else{Some(TxError::IoUncertain)},
                        },
                        signal:if unknown.is_some(){S::Interrupted}
                               else if copied<total{S::PartialErrnoUnavailable}
                               else{S::None},
                    };
                    let obs=m0_fec2_observe_native_m4_repair_prefix(
                        &report,total
                    ).expect("all 0..32 typed M4 prefix shapes legal");
                    // The observer does not publish private M2 fields.
                    // Its Debug output must carry explicitly Unproven,
                    // never a fabricated ProvenNotAttempted refund.
                    let desc=format!("{obs:?}");
                    assert!(desc.contains("Unproven"));
                    assert!(!desc.contains("ProvenNotAttempted"));
                    checked+=1;
                }
            }
            for copied in [total+1,33,usize::MAX]{
                let report=KernelSendReport{
                    outcome:TxBatchOutcome{accepted_prefix:copied,
                        uncertain_index:None,error:Some(TxError::IoUncertain)},
                    signal:S::AmbiguousCompletion,
                };
                assert!(m0_fec2_observe_native_m4_repair_prefix(
                    &report,total
                ).is_err(),"out-of-range must fail BEFORE global debit");
            }
        }
        for (signal,err,unknown) in [
            (S::Backpressure,TxError::WouldBlock,None),
            (S::Interrupted,TxError::IoUncertain,Some(0)),
            (S::AmbiguousCompletion,TxError::IoUncertain,Some(0)),
            (S::PreflightRejected,TxError::IoFailed,None),
            (S::Stopping,TxError::Stopping,None),
            (S::MtuExceeded,TxError::IoFailed,None),
            (S::DeviceUnavailable,TxError::IoFailed,None),
            (S::RouteUnavailable,TxError::IoFailed,None),
        ]{
            let report=KernelSendReport{
                outcome:TxBatchOutcome{
                    accepted_prefix:0,uncertain_index:unknown,error:Some(err)
                },signal,
            };
            let observed=m0_fec2_observe_native_m4_repair_prefix(
                &report,32
            ).expect("typed conservative no-refund classification");
            let desc=format!("{observed:?}");
            assert!(desc.contains("Unproven"));
            assert!(!desc.contains("ProvenNotAttempted"));
        }
        let malformed=KernelSendReport{
            outcome:TxBatchOutcome{
                accepted_prefix:1,uncertain_index:Some(0),
                error:Some(TxError::IoUncertain)
            },signal:S::AmbiguousCompletion,
        };
        assert!(m0_fec2_observe_native_m4_repair_prefix(
            &malformed,32
        ).is_err());
        assert!(m0_fec2_observe_native_m4_repair_prefix(
            &KernelSendReport{
                outcome:TxBatchOutcome::copied_all(33),signal:S::None
            },33
        ).is_err());
        assert!(checked>=1000);
        println!("M0_FEC2_NATIVE_M4_M2_PREFIX_0_32_UNPROVEN_FAIL_CLOSED_PASS shapes={checked}");
    }

    #[cfg(all(any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    #[test]
    fn m0_raw_original_owner_kernel_prefix_and_uncertain_never_conflate(){
        use wbd_platform::linux_batch::{KernelSendSignal,KernelSendReport};
        use wbd_platform::{TxBatchOutcome,TxError};
        let full=KernelSendReport{
            outcome:TxBatchOutcome::copied_all(1),
            signal:KernelSendSignal::None,
        };
        assert!(raw_one_packet_copied(&full));
        for (outcome,signal) in [
            (TxBatchOutcome{accepted_prefix:0,uncertain_index:None,
                error:Some(TxError::WouldBlock)},KernelSendSignal::Backpressure),
            (TxBatchOutcome{accepted_prefix:0,uncertain_index:None,
                error:Some(TxError::IoFailed)},KernelSendSignal::MtuExceeded),
            (TxBatchOutcome{accepted_prefix:0,uncertain_index:None,
                error:Some(TxError::IoFailed)},KernelSendSignal::DeviceUnavailable),
            (TxBatchOutcome{accepted_prefix:0,uncertain_index:Some(0),
                error:Some(TxError::IoUncertain)},KernelSendSignal::AmbiguousCompletion),
            (TxBatchOutcome{accepted_prefix:1,uncertain_index:None,
                error:Some(TxError::WouldBlock)},KernelSendSignal::None),
        ]{
            assert!(!raw_one_packet_copied(&KernelSendReport{outcome,signal}));
        }
    }
    #[cfg(all(feature="fec2_product_record",target_os="linux",
        any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
    #[test]
    fn m0_public_fixed_maximum_all_20_rows_supported(){
        assert_eq!(wbd_codec::fec_v2::MAX_R,20);
        for row in 0..20u8{
            assert!(original_public_fixed_row_allowed(row),"maximum parity row {row}");
        }
        assert!(!original_public_fixed_row_allowed(20));
        assert!(!original_public_fixed_row_allowed(u8::MAX));
    }
    #[test]
    fn m0_embedded_go_private_control_rejects_unknown_and_null(){
        assert_eq!(unsafe{wbd_m0_embedded_go_prepare(
            std::ptr::null(),COLD_V4_LEN,std::ptr::null(),HANDOFF_V1_LEN,
            std::ptr::null_mut())},INVALID);
        assert_eq!(stage(0x5742,1,&[1]),UNKNOWN);
        assert_eq!(commit(0x5742,0,0,3),UNKNOWN);
        assert_eq!(stop(0x5742),UNKNOWN);
        assert_eq!(release(0x5742),UNKNOWN);
    }
}
