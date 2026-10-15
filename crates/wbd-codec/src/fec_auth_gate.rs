//! Fail-closed typed post-record FEC admission. FecOrigin intentionally
//! has NO public constructor: old WF wire and codec alone cannot attest a
//! V4 tunnel/epoch/direction/generation or derive the Go exporter.
//! Without a reviewed M0 authenticated session origin, an unbound gate
//! rejects every packet before AEAD and replay state mutation.
//!
//! Owns the real ReplayProtectedLaneRx. No raw FEC data are handed to
//! FecBlockIdOwner/FecRxOwner before authentic AEAD and PN uniqueness.
#![forbid(unsafe_code)]
use crate::fec_block_id::{
    AuthenticatedContext,FecBlockIdOwner,IdConfig,IdError,IdStats,
};
use crate::fec_rx::{
    Config as FecRxConfig,Deliver,Direction,FecRxOwner,RxError,Stats as FecStats,
};
use crate::record_crypto::{DirectionKeys,RecordSuite};
use crate::record_frame::AUTHENTICATED_LINK_KIND;
use crate::record_replay::{
    ReplayConfigError,ReplayProtectedLaneRx,ReplayWindowConfig,UniqueOpenError,
};

/// Sealed origin from a reviewed external authenticated V4 session manager.
/// No production constructor or Go exporter is added by this M3 atom.
pub struct FecOrigin {
    lane_id:u64,
    tunnel_id:u64,
    epoch:u64,
    direction:Direction,
    generation:u32,
}
impl FecOrigin {
    /// Explicit TEST-ONLY origin, NOT a product-session attestation.
    #[cfg(test)]
    pub(crate) fn test_only(lane_id:u64,tunnel_id:u64,epoch:u64,direction:Direction,generation:u32)->Self{
        Self{lane_id,tunnel_id,epoch,direction,generation}
    }
    fn context(&self)->AuthenticatedContext {
        AuthenticatedContext{
            epoch:self.epoch,direction:self.direction,
            trusted_generation:self.generation,
        }
    }
}
#[derive(Debug,Clone,Copy,PartialEq,Eq)]
pub enum AdmissionError {
    AbsentOrigin,WrongLane,WrongTunnel,NotLinkRecord,
    Replay(UniqueOpenError),BlockId(IdError),Fec(RxError),
}
#[derive(Debug,Clone,Copy,Default,PartialEq,Eq)]
pub struct AdmissionStats{
    pub denied_before_open:u64,pub replay_rejected:u64,
    pub rejected_after_open:u64,pub delivered_systematic:u64,
    pub delivered_recovered:u64,
}
#[derive(Debug,Clone,Copy,PartialEq,Eq)]
pub enum GateConfigError{
    MismatchedOwners,
    OriginLaneMismatch,OriginTunnelMismatch,OriginEpochMismatch,OriginDirectionMismatch,
    OriginGenerationMismatch,
    Replay(ReplayConfigError),BlockId(IdError),Fec(RxError),
}
/// One immutable record lane, epoch, direction and trusted generation.
/// Does not expose decrypted payloads through a bypass method.
pub struct AuthFecScopeGate{
    origin:Option<FecOrigin>,
    lane_id:u64,
    tunnel_id:u64,
    decoder:ReplayProtectedLaneRx,
    block_ids:FecBlockIdOwner,
    fec:FecRxOwner,
    stats:AdmissionStats,
}
impl AuthFecScopeGate{
    pub fn new(
        keys:DirectionKeys,record_suite:RecordSuite,record_max_wire:usize,
        replay_config:ReplayWindowConfig,
        id_config:IdConfig,fec_config:FecRxConfig,
        lane_id:u64,tunnel_id:u64,origin:Option<FecOrigin>,
    )->Result<Self,GateConfigError>{
        if lane_id==0||tunnel_id==0||id_config.epoch==0||
            id_config.epoch!=fec_config.epoch||
            id_config.direction!=fec_config.direction||
            id_config.retired_floor>=fec_config.first_id_ext||
            fec_config.first_id_ext==0{
            return Err(GateConfigError::MismatchedOwners);
        }
        if let Some(ref o)=origin{
            if o.lane_id!=lane_id{return Err(GateConfigError::OriginLaneMismatch);}
            if o.tunnel_id!=tunnel_id{return Err(GateConfigError::OriginTunnelMismatch);}
            if o.epoch!=id_config.epoch{return Err(GateConfigError::OriginEpochMismatch);}
            if o.direction!=id_config.direction{
                return Err(GateConfigError::OriginDirectionMismatch);
            }
            if u64::from(o.generation)!=id_config.anchor>>32 {
                return Err(GateConfigError::OriginGenerationMismatch);
            }
        }
        let decoder=ReplayProtectedLaneRx::new_for_suite(
            keys,record_max_wire,record_suite,replay_config
        ).map_err(GateConfigError::Replay)?;
        let block_ids=FecBlockIdOwner::new(id_config).map_err(GateConfigError::BlockId)?;
        let fec=FecRxOwner::new(fec_config).map_err(GateConfigError::Fec)?;
        Ok(Self{origin,lane_id,tunnel_id,decoder,block_ids,fec,stats:AdmissionStats::default()})
    }
    pub fn stats(&self)->AdmissionStats{self.stats}
    pub fn block_id_stats(&self)->IdStats{self.block_ids.stats()}
    pub fn fec_stats(&self)->FecStats{self.fec.stats()}

    /// Strict admission order:
    /// 1. Sealed session origin and authenticated external route lane.
    /// 2. Actual record AEAD, marker/kind and unique PN via protected RX.
    /// 3. Old-Go WF56 wire validation and trusted generation extension.
    /// 4. FEC Heavy/Compact first-delivery / missing-only recovery.
    /// A failed step 1 does not consume PN, mutate origin or parse FEC.
    pub fn accept_record_on_lane(
        &mut self,record_wire:&mut [u8],incoming_lane_id:u64,incoming_tunnel_id:u64,now_ms:u64,
    )->Result<Deliver,AdmissionError>{
        let origin=match self.origin.as_ref(){
            Some(x)=>x,
            None=>{
                self.stats.denied_before_open+=1;
                return Err(AdmissionError::AbsentOrigin);
            }
        };
        if incoming_lane_id!=self.lane_id||origin.lane_id!=self.lane_id{
            self.stats.denied_before_open+=1;
            return Err(AdmissionError::WrongLane);
        }
        if incoming_tunnel_id!=self.tunnel_id||origin.tunnel_id!=self.tunnel_id{
            self.stats.denied_before_open+=1;
            return Err(AdmissionError::WrongTunnel);
        }
        let context=origin.context();
        let opened=self.decoder.open_unique_in_place(record_wire).map_err(|err|{
            self.stats.replay_rejected+=1;
            AdmissionError::Replay(err)
        })?;
        if opened.kind!=AUTHENTICATED_LINK_KIND{
            self.stats.rejected_after_open+=1;
            return Err(AdmissionError::NotLinkRecord);
        }
        let observed=self.block_ids.observe_wire_after_auth(
            opened.payload,self.fec.max_wire(),context,now_ms
        ).map_err(|err|{
            self.stats.rejected_after_open+=1;
            AdmissionError::BlockId(err)
        })?;
        let result=self.fec.push_after_auth(
            opened.payload,observed.rx_scope(context),now_ms
        ).map_err(|err|{
            self.stats.rejected_after_open+=1;
            AdmissionError::Fec(err)
        });
        self.block_ids.advance_retired_floor(self.fec.stats().floor.unwrap_or(0));
        self.fec.advance_retired_floor(self.block_ids.stats().retired_floor);
        let delivered=result?;
        self.stats.delivered_systematic+=delivered.systematic.len() as u64;
        self.stats.delivered_recovered+=delivered.recovered.len() as u64;
        Ok(delivered)
    }
    /// Explicit owner timer, never a new thread or OS clock.
    pub fn expire(&mut self,now_ms:u64){
        self.fec.expire(now_ms);
        self.block_ids.expire(now_ms);
        self.block_ids.advance_retired_floor(self.fec.stats().floor.unwrap_or(0));
        self.fec.advance_retired_floor(self.block_ids.stats().retired_floor);
    }
}
