//! M0-only, **in-process** authenticated receipt/retransmit composition.
 //! The trusted Go V4 admission has NOT been connected to this Rust API;
 //! caller must supply the verified direction-separated RX crypto key,
 //! nonzero logical tunnel epoch and lane mapping from authenticated admission.
 //! Never accept raw receipt bytes, unauthenticated TCP ACK or peer-supplied
 //! lane/epoch to release a shadow entry. Uses M3's AEAD-first RX PN replay
 //! window; no product or live Go admission qualification.
 #![forbid(unsafe_code)]

 use wbd_codec::{decode_control, CodecError, ControlTlv};
 use wbd_codec::record_crypto::CryptoError;
 use wbd_codec::record_replay::{ReplayProtectedLaneRx, ReplayWindowInfo, ReplayStats,
                                UniqueOpenError};
 use wbd_codec::record_frame::AUTHENTICATED_HEALTH_KIND;
 use wbd_platform::r1::ReadyPacketSink;
 use wbd_platform::ipv4_tcp::{self,Ipv4Tuple,Presentation,PacketError};
 use std::io::ErrorKind;
 use wbd_recovery::{AuthenticatedReceipt, ReceiptPage, ReceiptState,
                    Release, RepairCandidate, RepairSendResult,
                    RepairBudget, BudgetError, GlobalRepairAllocator, GlobalRepairError, GrantLease};
 use wbd_types::{DataError, LaneKey, MonoNs, RecordPn};
 use wbd_types::buffer_contract::FrozenRecordHandle;

 #[derive(Debug)]
 pub enum ReceiptIngressError {
     UnboundLaneEpoch, Crypto(CryptoError), Control(CodecError),
     Replay(UniqueOpenError), NotHealth, MissingReceipt, Recovery(DataError),
     StaleCandidate, Budget(BudgetError), GlobalBudget(GlobalRepairError), Packet(PacketError), DriverOutcome,
 }

 /// A one-direction RX capability. Construct ONLY from trusted engine session
 /// state: feedback direction crypto and logical lane/epoch must already have
 /// been bound by authenticated Go V4 admission (not by feedback packet data).
 pub struct BoundReceiptIngress {
     reverse_rx: ReplayProtectedLaneRx,
     data_lane: LaneKey,
     logical_epoch: [u8; 16],
     control_budget: usize,
 }

 impl BoundReceiptIngress {
     /// Does *not* authenticate a Go V4 session or derive keys. It verifies
     /// the explicit already-authenticated lane and epoch inputs agree.
     pub fn from_verified_session(
         reverse_rx: ReplayProtectedLaneRx,
         data_lane: LaneKey, authenticated_feedback_lane: LaneKey,
         data_epoch: [u8; 16], authenticated_feedback_epoch: [u8; 16],
         control_budget: usize,
     ) -> Result<Self, ReceiptIngressError> {
         if data_lane != authenticated_feedback_lane
             || data_epoch == [0; 16]
             || data_epoch != authenticated_feedback_epoch
             || control_budget < 8 || control_budget > 16_645
         { return Err(ReceiptIngressError::UnboundLaneEpoch); }
         Ok(Self { reverse_rx, data_lane, logical_epoch:data_epoch,
                   control_budget })
     }

     pub fn lane(&self) -> LaneKey { self.data_lane }
     pub fn logical_epoch(&self) -> [u8; 16] { self.logical_epoch }
     /// Effective epoch-lane RX replay horizon/budget; source config comes
     /// from the authenticated owner, never the untrusted Health payload.
     pub fn replay_info(&self) -> ReplayWindowInfo { self.reverse_rx.info() }
     pub fn replay_stats(&self) -> ReplayStats { self.reverse_rx.stats() }
     pub fn replay_max_seen(&self) -> Option<u64> { self.reverse_rx.max_seen() }

     /// Open and authenticate exactly one reverse-direction Health record;
     /// only then parse bounded WBC4 control and construct M2 receipt evidence.
     /// Authentic PN uniqueness is checked BEFORE parsing Health/Receipt.
     /// Duplicate, retired and failed AEAD never call state.on_receipt.
     pub fn accept_one<H: FrozenRecordHandle>(
         &mut self, encrypted_wire: &mut [u8],
         state: &mut ReceiptState<H>, now: MonoNs,
     ) -> Result<Vec<Release<H>>, ReceiptIngressError> {
         let opened = self.reverse_rx.open_unique_in_place(encrypted_wire)
             .map_err(|err|match err {
                 UniqueOpenError::InvalidRecord(crypto) => ReceiptIngressError::Crypto(crypto),
                 other => ReceiptIngressError::Replay(other),
             })?;
         if opened.kind != AUTHENTICATED_HEALTH_KIND {
             return Err(ReceiptIngressError::NotHealth);
         }
         let controls=decode_control(opened.payload,self.control_budget)
             .map_err(ReceiptIngressError::Control)?;
         let receipt = controls.into_iter().find_map(|tlv|match tlv {
             ControlTlv::Receipt(r) => Some(r),
             ControlTlv::LegacyHealth(_) | ControlTlv::LegacyQuality(_) => None,
         }).ok_or(ReceiptIngressError::MissingReceipt)?;
         let pages=receipt.pages.into_iter().map(|p|ReceiptPage {
             base_pn:RecordPn(p.base_pn), bitmap:p.bitmap,
         }).collect();
         let authenticated=AuthenticatedReceipt::after_authenticated_open(
             self.data_lane,RecordPn(receipt.largest_data_pn),
             receipt.report_seq,pages,
         ).map_err(ReceiptIngressError::Recovery)?;
         state.on_receipt(&authenticated,now)
             .map_err(ReceiptIngressError::Recovery)
     }
 }

 /// Actual M4 IPv4+TCP DATA envelope of the original M1 frozen ciphertext.
 /// Trusted cold tuple/options/persona are provided by the caller; their live
 /// Go V4 admission binding is NOT implemented here. MTU and scratch are
 /// verified before budget or any driver call. Caller owns bounded scratch.
 ///
 /// The old unbudgeted/record-only repair sender has no public overload.
 /// This handler never re-seals the record or creates a new PN/Seq, and sends
 /// exactly the same full bytes it charges to the M2 ledger.
 pub fn submit_repair_once<S: ReadyPacketSink,H: FrozenRecordHandle>(
     state: &mut ReceiptState<H>, budget: &mut RepairBudget,
     candidate: &RepairCandidate<H>, sink: &mut S,
     tuple: Ipv4Tuple<'_>, presentation: Presentation,
     authenticated_options: Option<&[u8]>, outer_mtu: usize,
     scratch: &mut [u8], now: MonoNs,
 ) -> Result<RepairSendResult, ReceiptIngressError> {
     if !state.preflight(candidate,now) {
         return Err(ReceiptIngressError::StaleCandidate);
     }
     let packet=ipv4_tcp::build(
         tuple,presentation,candidate.frozen(),authenticated_options,
         outer_mtu,scratch).map_err(ReceiptIngressError::Packet)?;
     let wire_bytes=u64::try_from(packet.len())
         .map_err(|_|ReceiptIngressError::Budget(BudgetError::InvalidFrame))?;
     let reservation=budget.reserve(candidate,wire_bytes,now)
         .map_err(ReceiptIngressError::Budget)?;
     // M4 ReadyPacketSink::try_send is nonblocking and borrows exact full
     // IPv4/TCP bytes. As in M4 submit_ready: only EAGAIN means definite
     // NotSent; short send and every other I/O error are Uncertain.
     let disposition=match sink.try_send(packet) {
         Ok(n) if n==packet.len() => RepairSendResult::Accepted,
         Err(ref err) if err.kind()==ErrorKind::WouldBlock => RepairSendResult::NotSent,
         Ok(_) | Err(_) => RepairSendResult::Uncertain,
     };
     // A state failure retains the bounded reservation, which M2 timers
     // eventually charge as Uncertain, never mistaken for a refund.
     state.on_send_result(candidate,disposition,now)
         .map_err(ReceiptIngressError::Recovery)?;
     budget.on_send_result(reservation,disposition,now)
         .map_err(ReceiptIngressError::Budget)?;
     Ok(disposition)
 }

/// One process-owner grant, a caller-trusted tuple, and a true M4 ready-only
/// syscall result settle the SAME full IPv4/TCP bytes globally and locally.
/// The caller MUST obtain the lease from independently authenticated
/// TunnelKey/direction routing. No production driver/admission is enabled.
/// Preflight and packet validation happen BEFORE spending the global grant.
pub fn submit_global_repair_once<S: ReadyPacketSink,H: FrozenRecordHandle>(
    state:&mut ReceiptState<H>, global:&mut GlobalRepairAllocator,
    grant:GrantLease, candidate:&RepairCandidate<H>, sink:&mut S,
    tuple:Ipv4Tuple<'_>, presentation:Presentation,
    authenticated_options:Option<&[u8]>, outer_mtu:usize,
    scratch:&mut [u8], now:MonoNs
) -> Result<RepairSendResult,ReceiptIngressError>{
    if !state.preflight(candidate,now){
        return Err(ReceiptIngressError::StaleCandidate);
    }
    // The grant is a trusted process-owner capability and must not be
    // reassigned across the original frozen record's TunnelKey.
    if grant.direction().tunnel != candidate.frozen().metadata().lane.tunnel {
        return Err(ReceiptIngressError::GlobalBudget(GlobalRepairError::StaleGrant));
    }
    let packet=ipv4_tcp::build(tuple,presentation,candidate.frozen(),
        authenticated_options,outer_mtu,scratch)
        .map_err(ReceiptIngressError::Packet)?;
    let wire_bytes=u64::try_from(packet.len())
        .map_err(|_|ReceiptIngressError::GlobalBudget(GlobalRepairError::InvalidGrant))?;
    let reservation=global.reserve(grant,candidate,wire_bytes,now)
        .map_err(ReceiptIngressError::GlobalBudget)?;
    let result=match sink.try_send(packet) {
        Ok(n) if n==packet.len()=>RepairSendResult::Accepted,
        Err(ref err) if err.kind()==ErrorKind::WouldBlock=>RepairSendResult::NotSent,
        Ok(_)|Err(_)=>RepairSendResult::Uncertain,
    };
    // On failure in the shadow, leave reservation alive: owner timer must
    // retain the conservative (possibly sent) debit.
    state.on_send_result(candidate,result,now)
        .map_err(ReceiptIngressError::Recovery)?;
    global.complete(reservation,result,now)
        .map_err(ReceiptIngressError::GlobalBudget)?;
    Ok(result)
}
