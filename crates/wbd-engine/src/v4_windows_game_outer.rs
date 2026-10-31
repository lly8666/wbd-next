//! Original Game2/4 lanes use the SAME Normal outer-repair primitives:
//! original frozen ciphertext, OuterAckIndex, ReceiptState, process-global
//! v3 repair grant, preflight and exact NPF M4 settlement. Never reseal a PN.
use super::*;
use std::collections::VecDeque;
use wbd_types::{LaneKey,TunnelKey,SeqOffset,BufferKey};
use wbd_types::buffer_contract::{BufferOrigin,FrozenMetadata,FrozenRecordHandle};
use wbd_recovery::outer_ack::SackRange32;
use wbd_recovery::{ReceiptState,ReceiptConfig,OuterAckIndex,RepairCandidate,
    RepairSendResult,ReceiptRouteScope,BudgetDirection,WireDirection,
    RepairBudgetConfig,GrantLease,GlobalReservationId,reserve_frozen_submission,
    complete_driver_prefix,DriverPrefixObservation,BatchSuffixEvidence};
use wbd_recovery::{GlobalRepairError,BudgetError};
use wbd_types::{MonoNs,RecordPn};
use std::sync::Arc;

/// GameAdapter owns the distinct original-Go-TLS-derived AEAD/PN, not Normal
/// M1's key. After real NPF firstsend, this bounded immutable snapshot
/// satisfies Normal's exact FrozenRecordHandle interface without re-sealing.
#[derive(Clone)]
struct GameFrozen{
    wire:Arc<[u8]>,meta:FrozenMetadata,origin:BufferOrigin,
}
impl FrozenRecordHandle for GameFrozen{
    fn origin(&self)->BufferOrigin{self.origin}
    fn metadata(&self)->FrozenMetadata{self.meta}
    fn bytes(&self)->&[u8]{&self.wire}
}
struct RepairHold{
    candidate:RepairCandidate<GameFrozen>,
    lease:GrantLease,reservation:GlobalReservationId,
}
struct GameOuterLane{
    lane:LaneKey,direction:BudgetDirection,route:ReceiptRouteScope,
    ack:OuterAckIndex,shadow:ReceiptState<GameFrozen>,
    ready:VecDeque<RepairCandidate<GameFrozen>>,
    held:Option<RepairHold>,retry_after_ns:Option<u64>,
}
pub(super) struct GameRepair{
    pub index:usize,pub seq:u32,pub pn:u64,pub wire:Arc<[u8]>,
}
pub(super) struct GameOuter{
    lanes:Vec<GameOuterLane>,epoch:[u8;16],
}
impl GameOuter{
    pub(super) fn new(cfg:&WbdWinGameNativeAttachV3,
        lanes:&[LaneConfig])->Result<Self,i32>{
        // ONLY AFTER native_game_group has checked every original cold
        // TLS lane, owner handle, epoch, Wintun lease and kernel capture.
        let generation=(cfg.group>>32) as u32;
        if generation==0{return Err(INVALID)}
        let mut owner=Self{lanes:Vec::with_capacity(lanes.len()),epoch:cfg.first.epoch};
        for (index,entry) in lanes.iter().enumerate(){
            // Each independent Game TCP sequence stream needs its OWN
            // Normal budget direction. No collision with the group crypto
            // tunnel or other Normal/Fixed account; global hard cap SHARED.
            let tunnel=TunnelKey{
                slot:0x474d_0000|(index as u32+1),generation
            };
            let lane=LaneKey{tunnel,slot:index as u32+1,generation};
            let dir=BudgetDirection{tunnel,direction:WireDirection::ClientToServer};
            let all=(RecordPn(0),RecordPn(u64::MAX));
            let route=ReceiptRouteScope::checked(lane,lane,
                WireDirection::ClientToServer,cfg.first.epoch,all,all)
                .map_err(|_|BAD_STAGE)?;
            let mut shadow=ReceiptState::new(lane,ReceiptConfig{
                max_shadow_entries:MAX_M2_FIXED_FROZEN,pto_ns:810_000_000,
                reorder_window_ns:20_000_000,
            }).map_err(|_|BAD_STAGE)?;
            shadow.enable_adaptive_timing(600_000_000,50_000_000)
                .map_err(|_|BAD_STAGE)?;
            shadow.enable_opportunistic_v3().map_err(|_|BAD_STAGE)?;
            let ack=OuterAckIndex::new(lane,cfg.first.epoch,
                u64::from(entry.tx_seq),MAX_M2_FIXED_FROZEN)
                .map_err(|_|BAD_STAGE)?;
            let now=m2_clock();
            {
                let mut g=m2_global().lock().map_err(|_|BAD_STAGE)?;
                g.register(dir,RepairBudgetConfig{
                    outer_mtu:u64::from(cfg.first.path_mtu).saturating_add(54),
                    max_repair_bytes_per_epoch:7_000_000,
                    max_pending_reservations:256,max_pending_bytes:524_288,
                    io_timeout_ns:100_000_000,
                },now).map_err(|_|BAD_STAGE)?;
                if g.enable_opportunistic_v3(dir).is_err()||
                    g.bind_receipt_route(dir,route,now).is_err(){
                    let _=g.retire_tunnel(tunnel,now);
                    return Err(BAD_STAGE)
                }
            }
            owner.lanes.push(GameOuterLane{
                lane,direction:dir,route,ack,shadow,
                ready:VecDeque::new(),held:None,retry_after_ns:None,
            });
        }
        Ok(owner)
    }
    pub(super) fn on_firstsend(&mut self,index:usize,pn:u64,seq:u32,
        wire:&[u8])->Result<(),i32>{
        let m=self.lanes.get_mut(index).ok_or(INVALID)?;
        let now=m2_clock();
        let high=m.ack.highest_sent_end();
        let delta=seq.wrapping_sub(high as u32) as i32;
        // Only the exact next original TCP sequence. An old/overlapped
        // carrier cannot become repair-eligible or spend new first credit.
        if delta!=0{return Err(BAD_STAGE)}
        let bytes=wire.len().checked_add(54).ok_or(INVALID)? as u64;
        m2_global().lock().map_err(|_|BAD_STAGE)?
            .on_fresh_accepted(m.direction,bytes,now).map_err(|_|BAD_STAGE)?;
        let _=m.ack.on_definitely_sent(RecordPn(pn),high,wire.len() as u32,now);
        // Optional, sampled snapshots may be denied without delaying any
        // genuine source or parity firstsend.
        if m.shadow.outstanding()>=MAX_M2_FIXED_FROZEN ||
            !win_v3_admit_shadow(pn,m.lane,now){return Ok(())}
        let frozen=GameFrozen{
            wire:Arc::from(wire),
            meta:FrozenMetadata{
                lane:m.lane,seq:SeqOffset(high),pn:RecordPn(pn),
                carrier_snapshot:0,
            },
            origin:BufferOrigin{
                owner_arena:m.lane.tunnel.slot,
                key:BufferKey{slot:pn as u32,generation:(pn>>32) as u32},
            },
        };
        let _=m.shadow.on_sent_adaptive_with_floor(
            frozen,now,WIN_NORMAL_M2_MIN_RETAIN_NS);
        Ok(())
    }
    // Game Health is an original authenticated kind0 record with its OWN
    // PN and TCP sequence bytes. It advances the exact outbound sequence
    // ledger but NEVER enters the DATA repair shadow or first-send F.
    pub(super) fn on_health_copy(&mut self,index:usize,pn:u64,
        seq:u32,wire_len:usize)->Result<(),i32>{
        let m=self.lanes.get_mut(index).ok_or(INVALID)?;
        let high=m.ack.highest_sent_end();
        if seq!=high as u32 || wire_len==0{return Err(BAD_STAGE)}
        let _=m.ack.on_definitely_sent(
            RecordPn(pn),high,wire_len as u32,m2_clock());
        Ok(())
    }
    pub(super) fn on_hint(&mut self,index:usize,ack:u32,
        sacks:&[SackRange32])->bool{
        let Some(m)=self.lanes.get_mut(index)else{return false};
        let now=m2_clock();
        let Ok(update)=m.ack.on_feedback(
            m.lane,self.epoch,ack,sacks,now,20_000_000)else{return false};
        for pn in update.retired{let _=m.shadow.discard_outer_ack_hint(pn);}
        let mut work=false;
        for pn in update.gap_candidates{
            work|=m.shadow.on_outer_gap_hint(pn,now);
        }
        work
    }
    pub(super) fn prepare(&mut self,active:&[bool])
        ->Result<Option<GameRepair>,i32>{
        let now=m2_clock();
        for (index,m) in self.lanes.iter_mut().enumerate(){
            if !active[index]||m.held.is_some()||
                m.retry_after_ns.is_some_and(|at|at>now.0){continue}
            m.retry_after_ns=None;
            if m.ready.is_empty(){m.ready.extend(m.shadow.on_timer(now).candidates);}
            while let Some(candidate)=m.ready.pop_front(){
                if !m.shadow.preflight(&candidate,now){continue}
                if !win_v3_send_pps_permit(now){
                    let _=m.shadow.on_send_result(&candidate,RepairSendResult::NotSent,now);
                    continue
                }
                let wire=candidate.frozen().bytes();
                if wire.is_empty()||wire.len()>1536{
                    let _=m.shadow.on_send_result(&candidate,RepairSendResult::NotSent,now);
                    continue
                }
                let bytes=wire.len() as u64+54;
                let mut g=m2_global().lock().map_err(|_|BAD_STAGE)?;
                let lease=match g.grant(m.direction,bytes,40_000_000,now){
                    Ok(v)=>v,Err(_)=>{
                        let _=m.shadow.on_send_result(&candidate,RepairSendResult::NotSent,now);
                        continue
                    }
                };
                let submission=reserve_frozen_submission(
                    &mut g,lease,m.route,&m.shadow,&candidate,bytes,now);
                let reservation=match submission{
                    Ok(v) if v.driver.metadata==candidate.frozen().metadata()
                        && v.driver.wire.as_ptr()==wire.as_ptr()=>v.reservation_id,
                    Err(GlobalRepairError::Local(BudgetError::BurstPaced))=>{
                        let _=g.revoke(lease,now);
                        m.retry_after_ns=Some(now.0.saturating_add(5_000_000));
                        m.ready.push_front(candidate);
                        return Ok(None)
                    },
                    _=>{
                        let _=g.revoke(lease,now);
                        let _=m.shadow.on_send_result(&candidate,RepairSendResult::NotSent,now);
                        continue
                    }
                };
                let result=GameRepair{
                    index,seq:candidate.frozen().metadata().seq.0 as u32,
                    pn:candidate.pn().0,wire:Arc::clone(&candidate.frozen().wire),
                };
                m.held=Some(RepairHold{candidate,lease,reservation});
                return Ok(Some(result))
            }
        }
        Ok(None)
    }
    pub(super) fn complete(&mut self,index:usize,pn:u64,sent:u32)
        ->Result<(),i32>{
        if sent>2{return Err(INVALID)}
        let m=self.lanes.get_mut(index).ok_or(INVALID)?;
        let held=m.held.take().ok_or(BAD_STAGE)?;
        if held.candidate.pn()!=RecordPn(pn){
            m.held=Some(held);return Err(INVALID)
        }
        let now=m2_clock();
        let observation=DriverPrefixObservation::checked(
            1,usize::from(sent==1),if sent==1{None}else{Some(0)},
            BatchSuffixEvidence::Unproven
        ).map_err(|_|BAD_STAGE)?;
        let mut g=m2_global().lock().map_err(|_|BAD_STAGE)?;
        let settled=complete_driver_prefix(
            &mut g,&[(held.reservation,m.route)],observation,now
        );
        let status=match settled{
            Ok(v)=>v.shadow_result(0).unwrap_or(RepairSendResult::Uncertain),
            Err(_)=>RepairSendResult::Uncertain,
        };
        let _=m.shadow.on_send_result(&held.candidate,status,now);
        let _=g.revoke(held.lease,now);
        Ok(())
    }
    pub(super) fn next_deadline(&self)->Option<u64>{
        self.lanes.iter().flat_map(|m|{
            m.shadow.next_deadline().map(|x|x.0)
                .into_iter().chain(m.retry_after_ns)
        }).min()
    }
}
impl Drop for GameOuter{
    fn drop(&mut self){
        if let Ok(mut g)=m2_global().lock(){
            let now=m2_clock();
            for lane in &self.lanes{
                let d=lane.shadow.diagnostic_snapshot();
                eprintln!("WBD_GAME_NORMAL_SHARED_OUTER_STOP lane={} candidates={} repair_accepted={} expiry={} shadows={} ACK_examined={}",
                    lane.lane.slot,d.cosmetic_candidates,
                    d.repair_accepted_retired,d.expired_attempt0,
                    lane.shadow.outstanding(),lane.ack.gap_scanned_once());
                let _=g.retire_tunnel(lane.lane.tunnel,now);
            }
        }
    }
}
#[cfg(test)]
mod tests{
    use super::*;
    #[test]
    fn game_outer_budget_lanes_have_distinct_real_scope(){
        let generation=17u32;
        let x=LaneKey{tunnel:TunnelKey{slot:0x474d0001,generation},slot:1,generation};
        let y=LaneKey{tunnel:TunnelKey{slot:0x474d0002,generation},slot:2,generation};
        assert_ne!(x.tunnel,y.tunnel);
        assert!(ReceiptRouteScope::checked(x,x,WireDirection::ClientToServer,
            [9;16],(RecordPn(0),RecordPn(u64::MAX)),
            (RecordPn(0),RecordPn(u64::MAX))).is_ok());
    }
}
