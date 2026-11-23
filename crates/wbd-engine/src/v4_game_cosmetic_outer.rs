//! Original Linux Game2/4 outer appearance repair, using Normal's existing
//! OuterAckIndex + opportunistic-v3 ReceiptState + 9% paced/10% quota ledger.
//! Only the original RAW driver accepts frozen PN/Seq/ciphertext. FEC, Health,
//! authenticated delivery and first-send credit are independent.
use std::collections::VecDeque;
use std::sync::Arc;
use wbd_recovery::outer_ack::{OuterAckIndex,OuterAckError,SackRange32};
use wbd_recovery::{
    ReceiptState,ReceiptConfig,RepairCandidate,RepairSendResult,
    RepairBudget,RepairBudgetConfig,BudgetDirection,WireDirection,BudgetError,ReservationId,
};
use wbd_types::{MonoNs,LaneKey,RecordPn,SeqOffset,BufferKey};
use wbd_types::buffer_contract::{BufferOrigin,FrozenMetadata,FrozenRecordHandle};

const MAX_WIRE:usize=1536;
const OUTER_HEADER_BYTES:u64=40; // Linux raw original IPv4+TCP, no options
const SHADOWS_PER_LANE:usize=6144;
const RETAIN_FLOOR_NS:u64=1_200_000_000; // same Normal Linux RTT step floor
const REORDER_GUARD_NS:u64=20_000_000;
const PACER_RETRY_NS:u64=5_000_000;

#[derive(Clone)]
pub(crate) struct CosmeticCopy{
    pub lane:usize,pub pn:u64,pub seq:u64,pub wire:Arc<[u8]>,
}
impl CosmeticCopy{
    pub fn frozen(&self,key:LaneKey)->CosmeticFrozen{
        CosmeticFrozen{
            wire:Arc::clone(&self.wire),
            meta:FrozenMetadata{lane:key,seq:SeqOffset(self.seq),
                pn:RecordPn(self.pn),carrier_snapshot:1},
            origin:BufferOrigin{owner_arena:key.tunnel.slot,
                key:BufferKey{slot:self.pn as u32,
                    generation:(self.pn>>32) as u32}},
        }
    }
}
#[derive(Clone)]
pub(crate) struct CosmeticFrozen{
    wire:Arc<[u8]>,meta:FrozenMetadata,origin:BufferOrigin,
}
impl FrozenRecordHandle for CosmeticFrozen{
    fn origin(&self)->BufferOrigin{self.origin}
    fn metadata(&self)->FrozenMetadata{self.meta}
    fn bytes(&self)->&[u8]{&self.wire}
}
struct Lane{
    seen:u64,
    key:LaneKey,epoch:[u8;16],
    ack:OuterAckIndex,shadow:ReceiptState<CosmeticFrozen>,
    ready:VecDeque<RepairCandidate<CosmeticFrozen>>,
    held:Option<(RepairCandidate<CosmeticFrozen>,ReservationId)>,
    retry_after_ns:Option<u64>,
    sent:u64,
}
pub(crate) struct CosmeticOuter{
    lanes:Vec<Lane>,
    // All physical lanes share one real first-send F denominator and one
    // Normal local epoch/pacing budget; never multiply sparse credit by N.
    budget:RepairBudget,
    first_record_wire_bytes:u64,
    copied_record_wire_bytes:u64,
}
fn admit_shadow(pn:u64,lane:LaneKey)->bool{
    // Normal's deterministic mixed-PN/lane 1/2 sampling, no RNG or heap.
    let key=pn^((lane.tunnel.slot as u64)<<48)
        ^((lane.tunnel.generation as u64)<<32)
        ^((lane.slot as u64)<<16)^(lane.generation as u64);
    let mut x=key.wrapping_add(0x9e3779b97f4a7c15);
    x=(x^(x>>30)).wrapping_mul(0xbf58476d1ce4e5b9);
    x=(x^(x>>27)).wrapping_mul(0x94d049bb133111eb);
    (x^(x>>31))&1==0
}
fn new_lane(key:LaneKey,seq:u64,epoch:[u8;16])->Result<Lane,OuterAckError>{
    let ack=OuterAckIndex::new(key,epoch,seq,SHADOWS_PER_LANE)?;
    let mut shadow=ReceiptState::new(key,ReceiptConfig{
        max_shadow_entries:SHADOWS_PER_LANE,
        pto_ns:810_000_000,reorder_window_ns:REORDER_GUARD_NS,
    }).map_err(|_|OuterAckError::InvalidConfig)?;
    shadow.enable_adaptive_timing(600_000_000,50_000_000)
        .map_err(|_|OuterAckError::InvalidConfig)?;
    shadow.enable_opportunistic_v3().map_err(|_|OuterAckError::InvalidConfig)?;
    Ok(Lane{seen:0,key,epoch,ack,shadow,ready:VecDeque::with_capacity(32),
        held:None,retry_after_ns:None,sent:0})
}
impl CosmeticOuter{
    pub fn with_normal_feedback(keys:&[LaneKey],seqs:&[u64],epoch:[u8;16])
        ->Result<Self,OuterAckError>{
        if keys.is_empty()||keys.len()!=seqs.len()||keys.len()>4||
            keys.iter().any(|k|k.tunnel!=keys[0].tunnel){
            return Err(OuterAckError::InvalidConfig)
        }
        let mut lanes=Vec::with_capacity(keys.len());
        for (key,seq) in keys.iter().zip(seqs){
            lanes.push(new_lane(*key,*seq,epoch)?);
        }
        let mut budget=RepairBudget::new(BudgetDirection{
            tunnel:keys[0].tunnel,direction:WireDirection::ClientToServer,
        },RepairBudgetConfig{
            outer_mtu:1600,max_repair_bytes_per_epoch:8*1024*1024,
            max_pending_reservations:128,max_pending_bytes:4*1024*1024,
            io_timeout_ns:100_000_000,
        },MonoNs(0)).map_err(|_|OuterAckError::InvalidConfig)?;
        budget.enable_opportunistic_v3();
        Ok(Self{lanes,budget,first_record_wire_bytes:0,
            copied_record_wire_bytes:0})
    }
    pub(crate) fn rekey_one_lane(
        &mut self,index:usize,key:LaneKey,seq:u64,epoch:[u8;16],
    )->Result<(),OuterAckError>{
        let Some(old)=self.lanes.get(index)else{return Err(OuterAckError::WrongScope)};
        if key.tunnel!=old.key.tunnel||old.held.is_some(){
            return Err(OuterAckError::WrongScope)
        }
        let mut fresh=new_lane(key,seq,epoch)?;
        fresh.sent=old.sent;
        self.lanes[index]=fresh;
        Ok(())
    }
    // The caller invokes this ONLY after a successful original RAW send.
    // All first copies enter F; only one selected half pins a shadow+ACK node.
    pub fn on_firstsend(&mut self,index:usize,pn:u64,seq:u64,
        wire:&[u8],now_ns:u64)->Result<(),OuterAckError>{
        let Some(l)=self.lanes.get_mut(index)else{return Err(OuterAckError::WrongScope)};
        let now=MonoNs(now_ns);
        l.seen=l.seen.wrapping_add(1);
        let selected=admit_shadow(pn,l.key) &&
            l.shadow.outstanding()<SHADOWS_PER_LANE &&
            !wire.is_empty()&&wire.len()<=MAX_WIRE;
        let tracked=if selected{
            l.ack.on_definitely_sent(RecordPn(pn),seq,wire.len() as u32,now)?
        }else{
            l.ack.advance_untracked(seq,wire.len() as u32)?;
            false
        };
        let bytes=wire.len() as u64+OUTER_HEADER_BYTES;
        self.first_record_wire_bytes=self.first_record_wire_bytes.saturating_add(bytes);
        // Matching Normal's definite-firstsend budget, not Game's lifetime
        // ratio counter. No attempt to send DATA is made in this path.
        let _=self.budget.on_fresh_accepted(bytes,now);
        if tracked{
            let frozen=CosmeticCopy{
                lane:index,pn,seq,wire:Arc::from(wire)
            }.frozen(l.key);
            let _=l.shadow.on_sent_adaptive_with_floor(frozen,now,RETAIN_FLOOR_NS);
        }
        Ok(())
    }
    pub fn on_health_copy(&mut self,index:usize,seq:u64,wire_len:usize)
        ->Result<(),OuterAckError>{
        let Some(l)=self.lanes.get_mut(index)else{return Err(OuterAckError::WrongScope)};
        let n=u32::try_from(wire_len).map_err(|_|OuterAckError::InvalidSend)?;
        l.ack.advance_untracked(seq,n)
    }
    // Same Normal ACK/SACK algorithm: retire optionally frozen positive spans,
    // nominate only existing missing original spans, never a blind DATA PTO.
    pub fn on_feedback(&mut self,index:usize,ack32:u32,
        sacks:&[SackRange32],now_ns:u64)->bool{
        let Some(l)=self.lanes.get_mut(index)else{return false};
        let now=MonoNs(now_ns);
        let Ok(update)=l.ack.on_feedback(l.key,l.epoch,ack32,sacks,
            now,REORDER_GUARD_NS)else{return false};
        for pn in update.retired{let _=l.shadow.discard_outer_ack_hint(pn);}
        let mut found=false;
        for pn in update.gap_candidates{
            found|=l.shadow.on_outer_gap_hint(pn,now);
        }
        found
    }
    pub fn next_due(&self)->Option<u64>{
        self.lanes.iter().filter_map(|l|{
            if !l.ready.is_empty(){return Some(l.retry_after_ns.unwrap_or(0));}
            l.shadow.next_deadline().map(|d|d.0)
                .map(|d|d.max(l.retry_after_ns.unwrap_or(0)))
        }).min()
    }
    // Same Normal v3 candidate generation, preflight, one-shot budget,
    // and burst-pacing deferral. No separate Game ACK-epoch or lane cooldown.
    pub fn take_due(&mut self,now_ns:u64,active:&[bool])->Option<CosmeticCopy>{
        let now=MonoNs(now_ns);
        for (i,l) in self.lanes.iter_mut().enumerate(){
            if (!active.is_empty()&&!active.get(i).copied().unwrap_or(false))||
                l.held.is_some()||l.retry_after_ns.is_some_and(|v|v>now_ns){
                continue
            }
            l.retry_after_ns=None;
            if l.ready.is_empty() && l.shadow.next_deadline()
                .is_some_and(|deadline|deadline.0<=now_ns){
                // Normal ReceiptState::on_timer reserves two candidate Vecs;
                // do not run it in every Game TX batch when no wake/expiry
                // is due. Indexed next_deadline() is O(1) and preserves
                // original expiry/ACK-gap scheduling exactly.
                l.ready.extend(l.shadow.on_timer(now).candidates);
            }
            while let Some(candidate)=l.ready.pop_front(){
                if !l.shadow.preflight(&candidate,now){continue}
                let frozen=candidate.frozen();
                let n=frozen.bytes().len();
                if n==0||n>MAX_WIRE{
                    let _=l.shadow.on_send_result(
                        &candidate,RepairSendResult::NotSent,now);
                    continue
                }
                let wire_bytes=n as u64+OUTER_HEADER_BYTES;
                match self.budget.reserve(&candidate,wire_bytes,now){
                    Ok(reservation)=>{
                        let meta=frozen.metadata();
                        let copy=CosmeticCopy{lane:i,pn:meta.pn.0,
                            seq:meta.seq.0,wire:Arc::clone(&frozen.wire)};
                        l.held=Some((candidate,reservation));
                        return Some(copy)
                    },
                    Err(BudgetError::BurstPaced)=>{
                        l.retry_after_ns=Some(now_ns.saturating_add(PACER_RETRY_NS));
                        l.ready.push_front(candidate);
                        return None
                    },
                    Err(BudgetError::QuotaExhausted)=>{
                        let _=l.shadow.on_quota_exhausted(&candidate,now);
                    },
                    Err(_)=>{
                        let _=l.shadow.on_send_result(
                            &candidate,RepairSendResult::NotSent,now);
                    }
                }
            }
        }
        None
    }
    pub fn complete(&mut self,index:usize,pn:u64,copied:bool,now_ns:u64)->bool{
        let Some(l)=self.lanes.get_mut(index)else{return false};
        let Some((candidate,reservation))=l.held.take()else{return false};
        if candidate.pn()!=RecordPn(pn){
            l.held=Some((candidate,reservation));
            return false
        }
        // RAW send_one's error is not proof that the kernel copied nothing.
        // Mirror Normal: uncertain consumes the sole frozen opportunity.
        let result=if copied{RepairSendResult::Accepted}
            else{RepairSendResult::Uncertain};
        let now=MonoNs(now_ns);
        let _=self.budget.on_send_result(reservation,result,now);
        let _=l.shadow.on_send_result(&candidate,result,now);
        if copied{
            l.sent=l.sent.saturating_add(1);
            self.copied_record_wire_bytes=self.copied_record_wire_bytes
                .saturating_add(candidate.frozen().bytes().len() as u64+
                    OUTER_HEADER_BYTES);
        }
        true
    }
    pub fn sent(&self)->u64{self.lanes.iter().map(|l|l.sent).sum()}
    pub fn copied_record_wire_bytes(&self)->u64{self.copied_record_wire_bytes}
    pub fn first_record_wire_bytes(&self)->u64{self.first_record_wire_bytes}
}
#[cfg(test)]
mod tests{
    use super::*;
    fn keys(n:usize)->Vec<LaneKey>{
        (1..=n).map(|slot|LaneKey{
            tunnel:wbd_types::TunnelKey{slot:14,generation:7},
            slot:slot as u32,generation:7,
        }).collect()
    }
    #[test]
    fn lossless_real_cumulative_ack_does_not_emit_cosmetic_copy(){
        let k=keys(2);
        let mut c=CosmeticOuter::with_normal_feedback(&k,&[100,100],[7;16]).unwrap();
        for i in 0..64u64{
            c.on_firstsend(0,i+1,100+100*i,&[9;100],(i+1)*1_000_000).unwrap();
        }
        assert!(!c.on_feedback(0,6500,&[],300_000_000));
        assert!(c.take_due(400_000_000,&[]).is_none());
        assert_eq!(c.sent(),0);
        assert_eq!(c.first_record_wire_bytes(),64*140);
    }
    #[test]
    fn normal_v3_gap_can_repair_more_than_one_candidate_per_lane(){
        let k=keys(2);
        let mut c=CosmeticOuter::with_normal_feedback(&k,&[100,100],[7;16]).unwrap();
        let mut heads=Vec::new();
        for i in 1..=96u64{
            let seq=100+(i-1)*100;
            c.on_firstsend(0,i,seq,&[9;100],i*1_000_000).unwrap();
            if admit_shadow(i,k[0]){heads.push((i,seq));}
        }
        assert!(heads.len()>30);
        // At least the first indexed head has a genuine later indexed send.
        let (pn,seq)=heads[0];
        for t in [200_000_000,210_000_000,220_000_000]{
            let _=c.on_feedback(0,seq as u32,&[],t);
        }
        let first=c.take_due(260_000_000,&[true,true]).unwrap();
        assert_eq!((first.pn,first.seq),(pn,seq));
        assert!(c.complete(0,pn,true,260_000_000));
        assert_eq!(c.sent(),1);
        // A new advancing cumulative ACK allows a different frozen candidate,
        // unlike the former single-shadow/per-lane 1s stall implementation.
        let (pn2,seq2)=heads[1];
        for t in [350_000_000,360_000_000,370_000_000,380_000_000]{
            let _=c.on_feedback(0,seq2 as u32,&[],t);
        }
        let second=c.take_due(410_000_000,&[true,true]).unwrap();
        assert_eq!(second.pn,pn2);
        assert!(c.complete(0,pn2,true,410_000_000));
    }
    #[test]
    fn one_original_pn_is_never_repaired_twice(){
        let k=keys(2);
        let mut c=CosmeticOuter::with_normal_feedback(&k,&[100,100],[7;16]).unwrap();
        let mut target=None;
        for i in 1..=64u64{
            let seq=100+(i-1)*100;
            c.on_firstsend(0,i,seq,&[1;100],i*1_000_000).unwrap();
            if target.is_none()&&admit_shadow(i,k[0]){target=Some((i,seq));}
        }
        let (pn,seq)=target.unwrap();
        for t in [180_000_000,190_000_000,200_000_000]{
            let _=c.on_feedback(0,seq as u32,&[],t);
        }
        let first=c.take_due(250_000_000,&[true,true]).unwrap();
        assert_eq!(first.pn,pn);
        assert!(c.complete(0,pn,true,250_000_000));
        for t in [260_000_000,270_000_000,280_000_000]{
            let _=c.on_feedback(0,seq as u32,&[],t);
        }
        assert!(c.take_due(300_000_000,&[true,true]).is_none());
    }
}
