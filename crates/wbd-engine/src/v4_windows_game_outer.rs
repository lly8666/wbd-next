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

// Optional GameFEC presentation: 1/16 original first copies retained,
// bounded to at most 12.5 real outer repeats/sec/lane. These limits do
// NOT influence FEC source/parity or Health and are not TCP delivery RTT.
const FEC_SHADOW_SAMPLE_MASK:u64=15;
const FEC_OUTER_MIN_INTERVAL_NS:u64=80_000_000;

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
    // GameFEC uses Normal's real ACK/ReceiptState/M2 candidate path.
    // Keep only a sparse OPTIONAL set of shadows (one original / 16 first
    // NPF copies), with a strict per-lane repair rate cap.
    fec_sparse:bool,fec_seen:Vec<u64>,fec_copied:u64,
}
impl GameOuter{
    pub(super) fn new(cfg:&WbdWinGameNativeAttachV3,
        lanes:&[LaneConfig])->Result<Self,i32>{
        // ONLY AFTER native_game_group has checked every original cold
        // TLS lane, owner handle, epoch, Wintun lease and kernel capture.
        let generation=(cfg.group>>32) as u32;
        if generation==0{return Err(INVALID)}
        // FEC presentation retransmission is NOT a second logical DATA,
        // a decode retry, nor authenticated feedback. It uses Normal's
        // validated cumulative ACK/immutable shadow and global driver
        // settlement, sampled to avoid a BTree/Arc/allocation per FEC symbol.
        let fec_sparse=cfg.fec==1;
        let mut owner=Self{lanes:Vec::with_capacity(lanes.len()),
            epoch:cfg.first.epoch,fec_sparse,
            fec_seen:vec![0;lanes.len()],fec_copied:0};
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
                max_shadow_entries:if fec_sparse{256}else{MAX_M2_FIXED_FROZEN},
                pto_ns:810_000_000,
                reorder_window_ns:20_000_000,
            }).map_err(|_|BAD_STAGE)?;
            shadow.enable_adaptive_timing(600_000_000,50_000_000)
                .map_err(|_|BAD_STAGE)?;
            shadow.enable_opportunistic_v3().map_err(|_|BAD_STAGE)?;
            let ack=OuterAckIndex::new(lane,cfg.first.epoch,
                u64::from(entry.tx_seq),if fec_sparse{256}else{MAX_M2_FIXED_FROZEN})
                .map_err(|_|BAD_STAGE)?;
            let now=m2_clock();
            {
                let mut g=m2_global().lock().map_err(|_|BAD_STAGE)?;
                g.register(dir,RepairBudgetConfig{
                    outer_mtu:u64::from(cfg.first.path_mtu).saturating_add(54),
                    max_repair_bytes_per_epoch:if fec_sparse{1_000_000}else{7_000_000},
                    max_pending_reservations:if fec_sparse{32}else{256},
                    max_pending_bytes:if fec_sparse{65_536}else{524_288},
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
        // A single integer/mask for 15/16 source/parity copies; no clock,
        // per-packet Normal global lock, BTree insert or heap ciphertext.
        let retain=if self.fec_sparse{
            let seen=self.fec_seen.get_mut(index).ok_or(INVALID)?;
            *seen=seen.wrapping_add(1);
            (*seen&FEC_SHADOW_SAMPLE_MASK)==0
        }else{true};
        let m=self.lanes.get_mut(index).ok_or(INVALID)?;
        let high=m.ack.highest_sent_end();
        let delta=seq.wrapping_sub(high as u32) as i32;
        // Only the exact next original TCP sequence. An old/overlapped
        // carrier cannot become repair-eligible or spend new first credit.
        if delta!=0{return Err(BAD_STAGE)}
        if !retain{
            // Normal ACK still bounds all actual copied TCP bytes; gaps
            // at unsampled spans MUST NOT nominate the next held record.
            m.ack.advance_untracked(high,wire.len() as u32)
                .map_err(|_|BAD_STAGE)?;
            return Ok(())
        }
        let now=m2_clock();
        let bytes=wire.len().checked_add(54).ok_or(INVALID)? as u64;
        m2_global().lock().map_err(|_|BAD_STAGE)?
            .on_fresh_accepted(m.direction,bytes,now).map_err(|_|BAD_STAGE)?;
        m.ack.on_definitely_sent(RecordPn(pn),high,wire.len() as u32,now)
            .map_err(|_|BAD_STAGE)?;
        // Optional, sampled snapshots may be denied without delaying any
        // genuine source or parity firstsend.
        if m.shadow.outstanding()>=(if self.fec_sparse{256}else{MAX_M2_FIXED_FROZEN}) ||
            (!self.fec_sparse&&!win_v3_admit_shadow(pn,m.lane,now)){return Ok(())}
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
        if self.fec_sparse{
            return m.ack.advance_untracked(high,wire_len as u32)
                .map_err(|_|BAD_STAGE)
        }
        m.ack.on_definitely_sent(
            RecordPn(pn),high,wire_len as u32,m2_clock())
            .map(|_|()).map_err(|_|BAD_STAGE)
    }
    pub(super) fn on_hint(&mut self,index:usize,ack:u32,
        sacks:&[SackRange32])->bool{
        // Untrusted presentation ACK can only nominate a Normal M2 shadow;
        // a sparse FEC candidate MUST start at the cumulative ACK's exact
        // first missing TCP byte. Otherwise an unsampled hole would falsely
        // nominate a newer packet. Never creates Game/FEC business credit.
        let Some(m)=self.lanes.get_mut(index)else{return false};
        let exact=!self.fec_sparse||m.ack.tracks_cumulative_head(ack);
        let now=m2_clock();
        let Ok(update)=m.ack.on_feedback(
            m.lane,self.epoch,ack,sacks,now,20_000_000)else{return false};
        for pn in update.retired{let _=m.shadow.discard_outer_ack_hint(pn);}
        let mut work=false;
        if exact{
            for pn in update.gap_candidates{
                work|=m.shadow.on_outer_gap_hint(pn,now);
            }
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
        if self.fec_sparse{
            // At most 12.5 optional outer repeats per second per lane.
            // No additional FEC symbol/PN, real first credit or Health.
            m.retry_after_ns=Some(now.0.saturating_add(FEC_OUTER_MIN_INTERVAL_NS));
            if sent==1{self.fec_copied=self.fec_copied.saturating_add(1)}
        }
        Ok(())
    }
    pub(super) fn next_deadline(&self)->Option<u64>{
        self.lanes.iter().filter_map(|m|{
            let shadow=m.shadow.next_deadline().map(|x|x.0);
            // A past-due shadow under the FEC per-lane rate cap must
            // not force a busy-spin until the next permitted attempt.
            match (shadow,m.retry_after_ns){
                (Some(s),Some(r))=>Some(s.max(r)),
                (Some(s),None)=>Some(s),
                (None,Some(r))=>Some(r),
                (None,None)=>None,
            }
        }).min()
    }
}
impl Drop for GameOuter{
    fn drop(&mut self){
        if self.fec_sparse{
            eprintln!("WBD_GAME_FEC_NORMAL_OUTER_STOP copied_appearance={} sampled_original={:?} exact_ack_head_only=1 same_original_pn_seq=1 no_fec_recovery_credit=1",
                self.fec_copied,self.fec_seen.iter().map(|n|n/(FEC_SHADOW_SAMPLE_MASK+1)).collect::<Vec<_>>());
        }
        if let Ok(mut g)=m2_global().lock(){
            let now=m2_clock();
            for lane in &self.lanes{
                let d=lane.shadow.diagnostic_snapshot();
                eprintln!("WBD_GAME_NORMAL_SHARED_OUTER_STOP lane={} fec_sparse={} candidates={} repair_accepted={} expiry={} shadows={} ACK_examined={}",
                    lane.lane.slot,self.fec_sparse,d.cosmetic_candidates,
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
    fn h811_fec_reuses_normal_cumulative_gap_without_flooding_every_record(){
        assert_eq!(FEC_SHADOW_SAMPLE_MASK+1,16);
        assert_eq!(1_000_000_000/FEC_OUTER_MIN_INTERVAL_NS,12);
        // Normal's exact ACK index MUST NOT misidentify unsampled earlier
        // TCP bytes as evidence that a later sampled FEC frame was lost.
        let lane=LaneKey{tunnel:TunnelKey{slot:29,generation:7},slot:1,generation:7};
        let mut ack=OuterAckIndex::new(lane,[7;16],100,128).unwrap();
        for i in 1..=32u64{
            let seq=ack.highest_sent_end();
            if i&FEC_SHADOW_SAMPLE_MASK==0{
                ack.on_definitely_sent(RecordPn(i),seq,10,
                    MonoNs(i*1_000_000)).unwrap();
            }else{
                ack.advance_untracked(seq,10).unwrap();
            }
        }
        assert_eq!(ack.highest_sent_end(),420);
        assert!(!ack.tracks_cumulative_head(100));
        assert!(ack.tracks_cumulative_head(250)); // packet 16
        assert!(!ack.tracks_cumulative_head(260));
        assert!(ack.tracks_cumulative_head(410)); // packet 32
        // No fake M4/FEC credit is awarded by the optional ACK index.
    }
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
