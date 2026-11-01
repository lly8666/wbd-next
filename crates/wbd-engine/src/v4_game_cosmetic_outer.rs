//! Game FEC *presentation only* outer TCP replay, shared by Windows NPF
//! and Linux raw M4. It is NOT a delivery retry, FEC source, ACK, or credit.
 //! One sparse frozen ciphertext per lane; no heap work on ordinary sends,
 //! no global M2 allocator, no background thread or per-packet wall clock.
use std::sync::Arc;
use wbd_recovery::outer_ack::{OuterAckIndex,OuterAckError};
use wbd_types::MonoNs;
use wbd_types::{LaneKey,RecordPn,SeqOffset,BufferKey};
use wbd_types::buffer_contract::{BufferOrigin,FrozenMetadata,FrozenRecordHandle};

const SAMPLE_MASK:u64=15; // one optional original snapshot / 16 real raw copies
const AFTER_FIRST_NS:u64=250_000_000; // conservative timed fallback
const MIN_INTERVAL_NS:u64=80_000_000; // <=12.5 per second per lane
const REORDER_GUARD_NS:u64=20_000_000; // Normal ACK reordering guard
const MAX_WIRE:usize=1536;

#[derive(Clone)]
pub(crate) struct CosmeticCopy{
    pub lane:usize,pub pn:u64,pub seq:u64,pub wire:Arc<[u8]>,
}
impl CosmeticCopy{
    // Frozen original bytes and exact original PN/Seq; the raw driver uses
    // the same existing TCP framing/checksum/route path as first send.
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
    seen:u64,not_before:u64,pending:Option<(u64,CosmeticCopy)>,
    held:Option<u64>,sent:u64,
    key:Option<LaneKey>,epoch:[u8;16],ack:Option<OuterAckIndex>,
}
pub(crate) struct CosmeticOuter{
    lanes:Vec<Lane>,
}
impl CosmeticOuter{
    pub fn new(count:usize)->Self{
        Self{lanes:(0..count).map(|_|Lane{
            seen:0,not_before:0,pending:None,held:None,sent:0,
            key:None,epoch:[0;16],ack:None
        }).collect()}
    }
    /// Original Normal ACK interval index, bounded to 128 sampled entries
    /// per lane. No new kernel reader, thread or separate FEC authority.
    pub fn with_normal_feedback(keys:&[LaneKey],seqs:&[u64],epoch:[u8;16])
        ->Result<Self,OuterAckError>{
        if keys.is_empty()||keys.len()!=seqs.len()||keys.len()>4{
            return Err(OuterAckError::InvalidConfig)
        }
        let mut result=Self::new(keys.len());
        for (i,key) in keys.iter().enumerate(){
            result.lanes[i].key=Some(*key);
            result.lanes[i].epoch=epoch;
            result.lanes[i].ack=Some(OuterAckIndex::new(*key,epoch,seqs[i],128)?);
        }
        Ok(result)
    }
    /// Always advance actual copied TCP byte bounds; 15/16 use Normal's
    /// untracked constant-time path. Track every 16th as positive later
    /// send evidence; freeze at most ONE original PN/Seq per lane.
    pub fn on_firstsend(&mut self,index:usize,pn:u64,seq:u64,
        wire:&[u8],now_ns:u64)->Result<(),OuterAckError>{
        let Some(l)=self.lanes.get_mut(index)else{
            return Err(OuterAckError::WrongScope)
        };
        let Some(ack)=l.ack.as_mut()else{
            return Err(OuterAckError::WrongScope)
        };
        l.seen=l.seen.wrapping_add(1);
        let sampled=l.seen&SAMPLE_MASK==0;
        if sampled{
            ack.on_definitely_sent(RecordPn(pn),seq,wire.len() as u32,
                MonoNs(now_ns))?;
        }else{
            ack.advance_untracked(seq,wire.len() as u32)?;
        }
        if sampled && l.pending.is_none() && l.held.is_none() &&
            now_ns>=l.not_before&&!wire.is_empty()&&wire.len()<=MAX_WIRE{
            l.pending=Some((now_ns.saturating_add(AFTER_FIRST_NS),
                CosmeticCopy{lane:index,pn,seq,wire:Arc::from(wire)}));
        }
        Ok(())
    }
    /// Original authenticated Health advances the outer TCP stream but
    /// creates no DATA/FEC repair candidate, first credit or feedback.
    pub fn on_health_copy(&mut self,index:usize,seq:u64,wire_len:usize)
        ->Result<(),OuterAckError>{
        let Some(l)=self.lanes.get_mut(index)else{
            return Err(OuterAckError::WrongScope)
        };
        let Some(ack)=l.ack.as_mut()else{
            return Err(OuterAckError::WrongScope)
        };
        let n=u32::try_from(wire_len).map_err(|_|OuterAckError::InvalidSend)?;
        ack.advance_untracked(seq,n)
    }

    /// Only a real original AEAD-opened reverse Game DATA frame can carry
    /// this packet's raw outer ACK hint. No Game FEC firstsend, Health,
    /// delivery or crypto credit may arise from an untrusted TCP ACK.
    pub fn on_feedback(&mut self,index:usize,ack32:u32,now_ns:u64)->bool{
        let Some(l)=self.lanes.get_mut(index)else{return false};
        let (Some(key),Some(indexer))=(l.key,l.ack.as_mut())else{return false};
        let exact=indexer.tracks_cumulative_head(ack32);
        let Ok(result)=indexer.on_feedback(key,l.epoch,ack32,&[],
            MonoNs(now_ns),REORDER_GUARD_NS)else{return false};
        let Some((due,copy))=l.pending.as_mut()else{return false};
        if result.retired.contains(&RecordPn(copy.pn)){
            l.pending=None;
            return false
        }
        if exact && result.gap_candidates.contains(&RecordPn(copy.pn)){
            *due=(*due).min(now_ns);
            return true
        }
        false
    }
    // Called only AFTER a real signed-NPF/raw first-copy succeeded. Ordinary
    // DATA/FEC input pays a single counter+mask, no allocation or clock.
    pub fn should_sample(&mut self,index:usize)->bool{
        let Some(l)=self.lanes.get_mut(index)else{return false};
        l.seen=l.seen.wrapping_add(1);
        l.seen&SAMPLE_MASK==0 && l.pending.is_none()&&l.held.is_none()
    }
    pub fn sample(&mut self,index:usize,pn:u64,seq:u64,
        wire:&[u8],now_ns:u64){
        let Some(l)=self.lanes.get_mut(index)else{return};
        if l.pending.is_some()||l.held.is_some()||now_ns<l.not_before||
            wire.is_empty()||wire.len()>MAX_WIRE{return}
        l.pending=Some((now_ns.saturating_add(AFTER_FIRST_NS),
            CosmeticCopy{lane:index,pn,seq,wire:Arc::from(wire)}));
    }
    pub fn next_due(&self)->Option<u64>{
        self.lanes.iter().filter_map(|l|l.pending.as_ref().map(|x|x.0)).min()
    }
    pub fn take_due(&mut self,now_ns:u64,active:&[bool])->Option<CosmeticCopy>{
        for l in &mut self.lanes{
            let Some((due,row))=l.pending.as_ref()else{continue};
            if *due>now_ns||l.held.is_some(){continue}
            if !active.is_empty()&&!active.get(row.lane).copied().unwrap_or(false){
                l.pending=None;continue
            }
            let (_,row)=l.pending.take()?;
            l.held=Some(row.pn);
            return Some(row)
        }
        None
    }
    pub fn complete(&mut self,index:usize,pn:u64,copied:bool,now_ns:u64)->bool{
        let Some(l)=self.lanes.get_mut(index)else{return false};
        if l.held!=Some(pn){return false}
        l.held=None;
        l.not_before=now_ns.saturating_add(MIN_INTERVAL_NS);
        if copied{l.sent=l.sent.saturating_add(1)}
        true
    }
    pub fn sent(&self)->u64{self.lanes.iter().map(|l|l.sent).sum()}
}
#[cfg(test)]
mod tests{
    use super::*;
    #[test]
    fn game_fec_outer_is_sparse_one_shot_frozen_and_does_not_mutate_source(){
        let mut c=CosmeticOuter::new(2);
        let wire=vec![9u8;1290];
        for i in 1..16{
            assert!(!c.should_sample(0),"no per-source duplicate allocation");
            assert!(c.next_due().is_none());
            let _=i;
        }
        assert!(c.should_sample(0));
        c.sample(0,77,10001,&wire,5_000_000);
        assert_eq!(c.next_due(),Some(255_000_000));
        assert!(c.take_due(254_999_999,&[]).is_none());
        let copy=c.take_due(255_000_000,&[]).unwrap();
        assert_eq!(copy.lane,0);assert_eq!(copy.pn,77);
        assert_eq!(copy.seq,10001);assert_eq!(&*copy.wire,&wire);
        let key=LaneKey{tunnel:wbd_types::TunnelKey{slot:1,generation:7},
            slot:1,generation:7};
        let f=copy.frozen(key);
        assert_eq!(f.metadata().pn,RecordPn(77));
        assert_eq!(f.metadata().seq,SeqOffset(10001));
        assert_eq!(f.bytes(),wire);
        assert!(c.take_due(255_000_001,&[]).is_none());
        assert!(!c.complete(0,78,true,255_000_000));
        assert!(c.complete(0,77,true,255_000_000));
        assert!(!c.complete(0,77,true,125_000_000));
        assert_eq!(c.sent(),1);
    }
    #[test]
    fn h812_normal_ack_targets_missing_original_not_later_sample(){
        let key=LaneKey{tunnel:wbd_types::TunnelKey{slot:14,generation:11},
            slot:1,generation:11};
        let mut c=CosmeticOuter::with_normal_feedback(
            &[key],&[100],[7;16]).unwrap();
        for i in 1..=32u64{
            c.on_firstsend(0,i,100+(i-1)*10,b"0123456789",
                i*1_000_000).unwrap();
        }
        assert_eq!(c.next_due(),Some(266_000_000)); // original PN16 only
        for t in [40_000_000,50_000_000,60_000_000]{
            assert!(!c.on_feedback(0,100,t))
        }
        assert!(c.take_due(80_000_000,&[]).is_none());
        for t in [85_000_000,86_000_000,87_000_000]{
            assert!(!c.on_feedback(0,250,t))
        }
        assert!(c.on_feedback(0,250,88_000_000));
        let row=c.take_due(88_000_000,&[]).unwrap();
        assert_eq!((row.pn,row.seq),(16,250));
        assert!(c.complete(0,16,true,88_000_000));
        assert_eq!(c.sent(),1);
        for i in 33..=48u64{
            c.on_firstsend(0,i,100+(i-1)*10,b"0123456789",
                i*1_000_000).unwrap();
        }
        assert!(c.next_due().is_none()); // bounded 80ms cooldown
    }
    #[test]
    fn h812_original_health_advances_outer_seq_without_repair_candidate(){
        let key=LaneKey{tunnel:wbd_types::TunnelKey{slot:14,generation:13},
            slot:1,generation:13};
        let mut c=CosmeticOuter::with_normal_feedback(
            &[key],&[100],[7;16]).unwrap();
        c.on_health_copy(0,100,42).unwrap();
        assert!(c.on_health_copy(0,100,42).is_err());
        c.on_firstsend(0,1,142,b"0123456789",1_000_000).unwrap();
        assert_eq!(c.next_due(),None);
        assert_eq!(c.sent(),0);
    }
    #[test]
    fn h812_ack_retirement_cancels_pending_original_raw_copy(){
        let key=LaneKey{tunnel:wbd_types::TunnelKey{slot:14,generation:12},
            slot:2,generation:12};
        let mut c=CosmeticOuter::with_normal_feedback(
            &[key],&[100],[7;16]).unwrap();
        for i in 1..=16u64{
            c.on_firstsend(0,i,100+(i-1)*10,b"0123456789",
                i*1_000_000).unwrap();
        }
        assert_eq!(c.next_due(),Some(266_000_000));
        assert!(!c.on_feedback(0,260,100_000_000));
        assert!(c.next_due().is_none());
        assert_eq!(c.sent(),0);
    }
    #[test]
    fn game_fec_cosmetic_cannot_resume_retired_lane_or_double_credit(){
        let mut c=CosmeticOuter::new(2);
        c.sample(1,4,120,b"immutable",50);
        assert!(c.take_due(250_000_051,&[true,false]).is_none());
        assert_eq!(c.sent(),0);
        c.sample(0,9,17,b"cipher",1);
        let row=c.take_due(250_000_002,&[true,true]).unwrap();
        assert_eq!(row.pn,9);
        assert!(c.complete(0,9,false,250_000_002));
        assert_eq!(c.sent(),0);
        assert!(c.next_due().is_none());
    }
}
