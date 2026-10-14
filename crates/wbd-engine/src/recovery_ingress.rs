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
 use wbd_platform::r1::{submit_ready, ReadyPacketSink};
 use wbd_recovery::{AuthenticatedReceipt, ReceiptPage, ReceiptState,
                    Release, RepairCandidate, RepairSendResult};
 use wbd_types::{DataError, LaneKey, MonoNs, RecordPn};
 use wbd_types::buffer_contract::FrozenRecordHandle;

 #[derive(Debug)]
 pub enum ReceiptIngressError {
     UnboundLaneEpoch, Crypto(CryptoError), Control(CodecError),
     Replay(UniqueOpenError), NotHealth, MissingReceipt, Recovery(DataError),
     StaleCandidate, DriverOutcome,
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

 /// Driver syscall result is NOT peer receipt: M2 records accepted/uncertain
 /// attempt cost, while true shadow release only occurs via accept_one().
 /// Uses original candidate frozen bytes; no new Seal/PN and no payload copy.
 pub fn submit_repair_once<S: ReadyPacketSink,H: FrozenRecordHandle>(
     state: &mut ReceiptState<H>, candidate: &RepairCandidate<H>,
     sink: &mut S, now: MonoNs,
 ) -> Result<RepairSendResult, ReceiptIngressError> {
     if !state.preflight(candidate,now) {
         return Err(ReceiptIngressError::StaleCandidate);
     }
     let outcome=submit_ready(sink,std::slice::from_ref(candidate.frozen()));
     let disposition=match (outcome.accepted_prefix,outcome.uncertain_index,outcome.error) {
         (1,None,None) => RepairSendResult::Accepted,
         (0,Some(0),Some(_)) => RepairSendResult::Uncertain,
         (0,None,Some(_)) => RepairSendResult::NotSent,
         _ => return Err(ReceiptIngressError::DriverOutcome),
     };
     state.on_send_result(candidate,disposition,now)
         .map_err(ReceiptIngressError::Recovery)?;
     Ok(disposition)
 }
