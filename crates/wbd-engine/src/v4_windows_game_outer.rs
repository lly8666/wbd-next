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

// H814: use Normal's full bounded first-copy ACK index and frozen-receipt
// cache, not the old 1/16 sparse window that never nominated a copied
// Windows GameFEC outer packet under genuine 10% loss. The Normal single
// adaptive PTO is a cosmetic fallback when the peer supplies no usable
// duplicate-ACK gap. Rate-limited repeats NEVER count as FEC recovery.
const FEC_SHADOW_SAMPLE_MASK:u64=0;
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
    // GameFEC uses Normal's full first-copy ACK/ReceiptState/M2 path
    // plus classic bounded PTO fallback; same original ciphertext/PN/seq.
    // Keep the single-repair hard expiry and per-lane rate cap.
    pub(super) repair_enabled:bool,
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
        // validated cumulative ACK/immutable shadow, Normal PTO and
        // global driver settlement. Performance tuning is deferred.
        let fec_sparse=cfg.fec==1;
        let repair_enabled=cfg.disable_outer_repair==0;
        let mut owner=Self{lanes:Vec::with_capacity(lanes.len()),
            epoch:cfg.first.epoch,repair_enabled,fec_sparse,
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
                max_shadow_entries:MAX_M2_FIXED_FROZEN,
                pto_ns:810_000_000,
                reorder_window_ns:20_000_000,
            }).map_err(|_|BAD_STAGE)?;
            shadow.enable_adaptive_timing(600_000_000,50_000_000)
                .map_err(|_|BAD_STAGE)?;
            // H813 genuine 10%-loss Windows GameFEC had 263 expired
            // shadows and ZERO candidates: sparse ACK-head matching with
            // v3 gap-only mode had no dependable retransmit wake. Use the
            // SAME Normal receipt/810ms adaptive PTO when FEC is enabled;
            // Game/off continues its existing v3 ACK-only path.
            if !fec_sparse{
                shadow.enable_opportunistic_v3().map_err(|_|BAD_STAGE)?;
            }
            let ack=OuterAckIndex::new(lane,cfg.first.epoch,
                u64::from(entry.tx_seq),MAX_M2_FIXED_FROZEN)
                .map_err(|_|BAD_STAGE)?;
            if repair_enabled {
                let now=m2_clock();
                let mut g=m2_global().lock().map_err(|_|BAD_STAGE)?;
                g.register(dir,RepairBudgetConfig{
                    outer_mtu:u64::from(cfg.first.path_mtu).saturating_add(54),
                    max_repair_bytes_per_epoch:7_000_000,
                    max_pending_reservations:256,
                    max_pending_bytes:524_288,
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
        // H814 uses Normal's full first-copy receipt ledger for FEC:
        // sparse 1/16 retained originals never matched the peer's precise
        // cumulative ACK head in real loss and all 263 expired without a
        // candidate. Deferring CPU optimization is explicitly intentional.
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
        if !self.repair_enabled{
            // Preserve exact FakeTCP sequence without M2 shadow/index,
            // optional global repair-credit lock or ciphertext Arc copy.
            return m.ack.advance_untracked(high,wire.len() as u32)
                .map_err(|_|BAD_STAGE)
        }
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
        // Normal's bounded optional receipt arena: a full cache never
        // blocks actual original FEC source/parity first sends.
        if m.shadow.outstanding()>=MAX_M2_FIXED_FROZEN ||
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
        if !self.repair_enabled||self.fec_sparse{
            return m.ack.advance_untracked(high,wire_len as u32)
                .map_err(|_|BAD_STAGE)
        }
        m.ack.on_definitely_sent(
            RecordPn(pn),high,wire_len as u32,m2_clock())
            .map(|_|()).map_err(|_|BAD_STAGE)
    }
    pub(super) fn on_hint(&mut self,index:usize,ack:u32,
        sacks:&[SackRange32])->bool{
        // Untrusted ACK can only nominate a Normal M2 shadow; an FEC
        // candidate must begin at the exact first missing TCP byte. Full
        // first-copy indexing makes such gaps observable. No FEC credit.
        if !self.repair_enabled{return false}
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
        if !self.repair_enabled{return Ok(None)}
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
        if !self.repair_enabled{return None}
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
        if !self.repair_enabled{
            eprintln!("WBD_GAME_NORMAL_SHARED_OUTER_STOP enabled=0 lanes={} copied_appearance=0 optional_shadow=0",self.lanes.len());
            return
        }
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
    fn plan027_game_cold_outer_off_preserves_original_seq_without_shadow_or_timer(){
        // Synthetic authenticated attachment values ONLY; this does not
        // claim OS/Wintun/NPF native business success.
        let generation=877;
        let lane=LaneKey{tunnel:TunnelKey{
            slot:0x474d_0001,generation},slot:1,generation};
        let dir=BudgetDirection{tunnel:lane.tunnel,
            direction:WireDirection::ClientToServer};
        let route=ReceiptRouteScope::checked(lane,lane,
            WireDirection::ClientToServer,[3;16],
            (RecordPn(0),RecordPn(u64::MAX)),
            (RecordPn(0),RecordPn(u64::MAX))).unwrap();
        let shadow=ReceiptState::<GameFrozen>::new(lane,ReceiptConfig{
            max_shadow_entries:MAX_M2_FIXED_FROZEN,
            pto_ns:810_000_000,reorder_window_ns:20_000_000,
        }).unwrap();
        let ack=OuterAckIndex::new(lane,[3;16],200,MAX_M2_FIXED_FROZEN).unwrap();
        let mut owner=GameOuter{lanes:vec![GameOuterLane{
            lane,direction:dir,route,ack,shadow,
            ready:VecDeque::new(),held:None,retry_after_ns:None,
        }],epoch:[3;16],repair_enabled:false,
        fec_sparse:false,fec_seen:vec![0],fec_copied:0};
        assert!(!owner.repair_enabled);
        assert_eq!(owner.on_firstsend(0,1,200,&[7u8;120]),Ok(()));
        assert_eq!(owner.lanes[0].ack.highest_sent_end(),320);
        assert_eq!(owner.lanes[0].shadow.outstanding(),0);
        assert_eq!(owner.on_health_copy(0,2,320,40),Ok(()));
        assert_eq!(owner.lanes[0].ack.highest_sent_end(),360);
        assert!(!owner.on_hint(0,360,&[]));
        assert!(owner.prepare(&[true]).unwrap().is_none());
        assert_eq!(owner.next_deadline(),None);
    }
    #[test]
    fn h811_fec_reuses_normal_cumulative_gap_without_flooding_every_record(){
        assert_eq!(FEC_SHADOW_SAMPLE_MASK+1,1);
        assert_eq!(1_000_000_000/FEC_OUTER_MIN_INTERVAL_NS,12);
        // All original FEC sends now have an exact Normal ACK entry.
        // No earlier untracked hole may suppress the only appearance retry.
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
        assert!(ack.tracks_cumulative_head(100));
        assert!(ack.tracks_cumulative_head(250)); // packet 16
        assert!(ack.tracks_cumulative_head(260)); // packet 17
        assert!(ack.tracks_cumulative_head(410)); // packet 32
        // No fake M4/FEC credit is awarded by the optional ACK index.
    }
    #[test]
    fn h814_normal_receipt_pto_fallback_nominates_real_fec_original_once(){
        // Exact production Normal receipt configuration; no artificial
        // crypto reseal, source FEC credit, new PN or fake NPF receipt.
        let lane=LaneKey{tunnel:TunnelKey{slot:0x474d0001,generation:9},
            slot:1,generation:9};
        let mut s=ReceiptState::<GameFrozen>::new(lane,ReceiptConfig{
            max_shadow_entries:MAX_M2_FIXED_FROZEN,
            pto_ns:810_000_000,reorder_window_ns:20_000_000,
        }).unwrap();
        s.enable_adaptive_timing(600_000_000,50_000_000).unwrap();
        // GameFEC intentionally DOES NOT enable gap-only opportunistic_v3.
        assert!(!s.is_opportunistic_v3());
        let frozen=GameFrozen{
            wire:Arc::from([0x5au8;120].as_slice()),
            meta:FrozenMetadata{lane,seq:SeqOffset(100),pn:RecordPn(7),
                carrier_snapshot:0},
            origin:BufferOrigin{owner_arena:lane.tunnel.slot,
                key:BufferKey{slot:7,generation:0}},
        };
        s.on_sent_adaptive_with_floor(
            frozen,MonoNs(0),WIN_NORMAL_M2_MIN_RETAIN_NS).unwrap();
        let due=s.next_deadline().expect("Normal PTO must schedule original");
        assert!(due.0>0&&due.0<WIN_NORMAL_M2_MIN_RETAIN_NS);
        assert!(s.on_timer(MonoNs(due.0-1)).candidates.is_empty());
        let result=s.on_timer(due);
        assert_eq!(result.candidates.len(),1);
        let candidate=&result.candidates[0];
        assert_eq!(candidate.pn(),RecordPn(7));
        assert_eq!(candidate.frozen().metadata().seq,SeqOffset(100));
        assert_eq!(candidate.frozen().bytes(),&[0x5au8;120]);
        s.on_send_result(candidate,RepairSendResult::Accepted,due).unwrap();
        assert_eq!(s.outstanding(),0);
        assert!(s.on_timer(MonoNs(2_000_000_000)).candidates.is_empty());
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
