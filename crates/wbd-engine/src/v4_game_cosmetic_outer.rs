//! Game FEC and Game OFF *presentation only* outer TCP replay, shared
//! by Windows NPF and Linux raw M4. It is NOT a delivery retry,
//! FEC source, authenticated ACK, or delivery credit.
 //! One sparse frozen ciphertext per lane; no heap work on ordinary sends,
 //! no global M2 allocator, no background thread or per-packet wall clock.
use std::sync::Arc;
use wbd_recovery::outer_ack::{OuterAckIndex,OuterAckError};
use wbd_types::MonoNs;
use wbd_types::{LaneKey,RecordPn,SeqOffset,BufferKey};
use wbd_types::buffer_contract::{BufferOrigin,FrozenMetadata,FrozenRecordHandle};

const SAMPLE_MASK:u64=1; // Normal-matching 1/2 eligibility, at most one live shadow per lane
const AFTER_FIRST_NS:u64=250_000_000; // test-only old sample() fixture, NOT a production PTO
const MIN_INTERVAL_NS:u64=80_000_000; // <=12.5 per second per lane
const REORDER_GUARD_NS:u64=20_000_000; // Normal ACK reordering guard
const INITIAL_ACK_STALL_NS:u64=1_000_000_000; // >=2 true 250ms RTT legs; no empty startup replay
const COSMETIC_MAX_AGE_NS:u64=2_000_000_000; // never replay ancient original DATA
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
    held:Option<(u64,usize)>,sent:u64,
    first_record_wire_bytes:u64,copied_record_wire_bytes:u64,
    key:Option<LaneKey>,epoch:[u8;16],ack:Option<OuterAckIndex>,
    initial_ack:Option<u32>,last_ack:Option<u32>,dup_acks:u8,
    ack_ever_progressed:bool,first_at_ns:u64,pending_at_ns:u64,
}
pub(crate) struct CosmeticOuter{
    lanes:Vec<Lane>,
}
impl CosmeticOuter{
    pub fn new(count:usize)->Self{
        Self{lanes:(0..count).map(|_|Lane{
            seen:0,not_before:0,pending:None,held:None,sent:0,
            first_record_wire_bytes:0,copied_record_wire_bytes:0,
            key:None,epoch:[0;16],ack:None,
            initial_ack:None,last_ack:None,dup_acks:0,
            ack_ever_progressed:false,first_at_ns:u64::MAX,pending_at_ns:0
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
            result.lanes[i].initial_ack=Some(seqs[i] as u32);
        }
        Ok(result)
    }
    /// Always advance actual copied TCP byte bounds; 1/2 use Normal's
    /// untracked constant-time path. Track every second as positive later
    /// send evidence; freeze at most ONE original PN/Seq per lane.
    /// A fresh protected original TLS lane must not reuse the previous
    /// TCP sequence/ACK gap index or a frozen ciphertext on a new 4-tuple.
    /// Other three physical lanes retain their exact cosmetic state.
    pub(crate) fn rekey_one_lane(
        &mut self,index:usize,key:LaneKey,seq:u64,epoch:[u8;16],
    )->Result<(),OuterAckError>{
        let Some(l)=self.lanes.get_mut(index)else{
            return Err(OuterAckError::WrongScope)
        };
        *l=Lane{
            seen:0,not_before:0,pending:None,held:None,sent:l.sent,
            first_record_wire_bytes:l.first_record_wire_bytes,
            copied_record_wire_bytes:l.copied_record_wire_bytes,
            key:Some(key),epoch,
            ack:Some(OuterAckIndex::new(key,epoch,seq,128)?),
            initial_ack:Some(seq as u32),last_ack:None,dup_acks:0,
            ack_ever_progressed:false,first_at_ns:u64::MAX,pending_at_ns:0,
        };
        Ok(())
    }
    pub fn on_firstsend(&mut self,index:usize,pn:u64,seq:u64,
        wire:&[u8],now_ns:u64)->Result<(),OuterAckError>{
        let Some(l)=self.lanes.get_mut(index)else{
            return Err(OuterAckError::WrongScope)
        };
        let Some(ack)=l.ack.as_mut()else{
            return Err(OuterAckError::WrongScope)
        };
        if l.first_at_ns==u64::MAX{l.first_at_ns=now_ns}
        l.seen=l.seen.wrapping_add(1);
        let sampled=l.seen&SAMPLE_MASK==0;
        if sampled{
            ack.on_definitely_sent(RecordPn(pn),seq,wire.len() as u32,
                MonoNs(now_ns))?;
        }else{
            ack.advance_untracked(seq,wire.len() as u32)?;
        }
        // Exact protected-record bytes of successfully copied first sends.
        l.first_record_wire_bytes=l.first_record_wire_bytes.saturating_add(wire.len() as u64);
        if sampled && l.pending.is_none() && l.held.is_none() &&
            now_ns>=l.not_before&&!wire.is_empty()&&wire.len()<=MAX_WIRE{
            // Unlike the old 250ms healthy timer, a real ACK gap alone
            // may arm this frozen original ciphertext. No fake DATA PTO.
            l.pending_at_ns=now_ns;
            l.pending=Some((u64::MAX,
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
        if l.last_ack==Some(ack32){
            l.dup_acks=l.dup_acks.saturating_add(1);
        }else{
            l.last_ack=Some(ack32);
            l.dup_acks=0;
        }
        if l.initial_ack.is_some_and(|initial|ack32!=initial){
            l.ack_ever_progressed=true;
        }
        let Some((due,copy))=l.pending.as_mut()else{return false};
        // Original Game copy is a TCP-looking appearance, NOT a
        // reliability recovery. A frozen record can be selected from the
        // genuinely unacknowledged window after three independently
        // AEAD-opened reverse DATA hints, even if the exact missing head
        // was never sampled. Never replay a cumulatively ACKed record.
        let offset=(copy.seq as u32).wrapping_sub(ack32) as i32;
        let acked=offset<0||result.retired.contains(&RecordPn(copy.pn));
        let age=now_ns.saturating_sub(l.pending_at_ns);
        if acked||age>COSMETIC_MAX_AGE_NS{
            l.pending=None;
            return false
        }
        let later_actual_copy=indexer.highest_sent_end()>
            copy.seq.saturating_add(copy.wire.len() as u64);
        let true_stall=l.dup_acks>=3 && later_actual_copy &&
            age>=REORDER_GUARD_NS &&
            (l.ack_ever_progressed||
                now_ns.saturating_sub(l.first_at_ns)>=INITIAL_ACK_STALL_NS);
        let exact_gap=exact&&result.gap_candidates.contains(&RecordPn(copy.pn));
        let next_bytes=l.copied_record_wire_bytes
            .saturating_add(copy.wire.len() as u64);
        // The original firstsend ledger is all actually copied original
        // bytes. Forbid attempts that could exceed sustained R/F<=10%.
        if (exact_gap||true_stall) &&
            next_bytes.saturating_mul(10)<=l.first_record_wire_bytes{
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
        self.lanes.iter().filter_map(|l|l.pending.as_ref()
            .and_then(|x|(x.0!=u64::MAX).then_some(x.0))).min()
    }
    pub fn take_due(&mut self,now_ns:u64,active:&[bool])->Option<CosmeticCopy>{
        for l in &mut self.lanes{
            let Some((due,row))=l.pending.as_ref()else{continue};
            if *due==u64::MAX||*due>now_ns||l.held.is_some(){continue}
            if !active.is_empty()&&!active.get(row.lane).copied().unwrap_or(false){
                l.pending=None;continue
            }
            let (_,row)=l.pending.take()?;
            l.held=Some((row.pn,row.wire.len()));
            return Some(row)
        }
        None
    }
    pub fn complete(&mut self,index:usize,pn:u64,copied:bool,now_ns:u64)->bool{
        let Some(l)=self.lanes.get_mut(index)else{return false};
        let Some((held_pn,record_bytes))=l.held else{return false};
        if held_pn!=pn{return false}
        l.held=None;
        l.not_before=now_ns.saturating_add(MIN_INTERVAL_NS);
        if copied{
            l.sent=l.sent.saturating_add(1);
            l.copied_record_wire_bytes=l.copied_record_wire_bytes.saturating_add(record_bytes as u64);
        }
        true
    }
    pub fn sent(&self)->u64{self.lanes.iter().map(|l|l.sent).sum()}
    pub fn copied_record_wire_bytes(&self)->u64{
        self.lanes.iter().map(|l|l.copied_record_wire_bytes).sum()
    }
    pub fn first_record_wire_bytes(&self)->u64{
        self.lanes.iter().map(|l|l.first_record_wire_bytes).sum()
    }
}
#[cfg(test)]
mod tests{
    use super::*;
    #[test]
    fn game_fec_outer_is_sparse_one_shot_frozen_and_does_not_mutate_source(){
        let mut c=CosmeticOuter::new(2);
        let wire=vec![9u8;1290];
        for i in 1..2{
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
        assert_eq!(c.copied_record_wire_bytes(),1290);
        assert_eq!(c.first_record_wire_bytes(),0); // should_sample path
    }
    #[test]
    fn r1_game_lossless_cumulative_ack_has_no_outer_copy(){
        let key=LaneKey{tunnel:wbd_types::TunnelKey{slot:18,generation:2},
            slot:1,generation:2};
        let mut c=CosmeticOuter::with_normal_feedback(&[key],&[100],[9;16]).unwrap();
        for i in 0..32u64{
            c.on_firstsend(0,i+1,100+10*i,b"0123456789",
                (i+1)*1_000_000).unwrap();
        }
        assert!(c.take_due(500_000_000,&[]).is_none());
        assert!(!c.on_feedback(0,420,600_000_000));
        assert!(c.next_due().is_none());
        assert_eq!(c.sent(),0);
    }
    #[test]
    fn r1_game_stalled_real_ack_allows_unacked_sample_not_exact_head(){
        let key=LaneKey{tunnel:wbd_types::TunnelKey{slot:44,generation:7},
            slot:1,generation:7};
        let mut c=CosmeticOuter::with_normal_feedback(
            &[key],&[100],[6;16]).unwrap();
        for i in 1..=32u64{
            c.on_firstsend(0,i,100+(i-1)*10,b"0123456789",
                i*1_000_000).unwrap();
        }
        assert!(c.next_due().is_none());
        // The first actual original seq100 was not sampled; PN2 is
        // unacknowledged but not the real hole. This is cosmetics ONLY.
        for t in [80_000_000,90_000_000,100_000_000,110_000_000]{
            assert!(!c.on_feedback(0,100,t)); // initial RTT quiet
        }
        assert!(c.take_due(990_000_000,&[true]).is_none());
        // Four separate authentically opened later Game records carry
        // one genuinely stalled cumulative ACK after the initial RTT.
        assert!(c.on_feedback(0,100,1_010_000_000));
        assert!(c.on_feedback(0,100,1_020_000_000)); // one due only
        assert!(c.on_feedback(0,100,1_030_000_000));
        assert_eq!(c.next_due(),Some(1_010_000_000));
        let copy=c.take_due(1_040_000_000,&[true]).unwrap();
        assert_eq!((copy.pn,copy.seq),(2,110));
        assert_eq!(copy.frozen(key).bytes(),b"0123456789");
        assert!(c.complete(0,2,true,1_040_000_000));
        assert!(c.take_due(1_041_000_000,&[true]).is_none());
        assert_eq!(c.sent(),1);
        assert!(c.copied_record_wire_bytes()*10<=c.first_record_wire_bytes());
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
        assert_eq!(c.next_due(),None); // no unsolicited Game DATA PTO
        for t in [40_000_000,50_000_000,60_000_000]{
            assert!(!c.on_feedback(0,100,t))
        }
        assert!(c.take_due(80_000_000,&[]).is_none());
        for t in [85_000_000,86_000_000,87_000_000]{
            assert!(!c.on_feedback(0,110,t))
        }
        assert!(c.on_feedback(0,110,88_000_000));
        let row=c.take_due(88_000_000,&[]).unwrap();
        assert_eq!((row.pn,row.seq),(2,110));
        assert!(c.complete(0,2,true,88_000_000));
        assert_eq!(c.sent(),1);
        assert_eq!(c.first_record_wire_bytes(),320);
        assert_eq!(c.copied_record_wire_bytes(),10);
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
        assert_eq!(c.next_due(),None);
        assert!(!c.on_feedback(0,260,100_000_000));
        assert!(c.next_due().is_none());
        assert_eq!(c.sent(),0);
    }
    #[test]
    fn r1_game_original_ciphertext_requires_real_gap_and_replays_once(){
        let key=LaneKey{tunnel:wbd_types::TunnelKey{slot:17,generation:9},
            slot:1,generation:9};
        let mut outer=CosmeticOuter::with_normal_feedback(&[key],&[100],[5;16]).unwrap();
        let wire=b"real-original-ciphertext";
        // PN2 is the exact sampled head; PN4 is an actual later copy.
        for i in 0..32u64{
            outer.on_firstsend(0,i+1,100+i*wire.len() as u64,
                wire,(i+1)*1_000_000).unwrap();
        }
        assert_eq!(outer.next_due(),None);
        assert!(outer.take_due(1_000_000_000,&[true]).is_none());
        let head=(100+wire.len()) as u32;
        for t in [80_000_000,90_000_000,100_000_000]{
            assert!(!outer.on_feedback(0,head,t));
        }
        assert!(outer.on_feedback(0,head,110_000_000));
        let copy=outer.take_due(110_000_000,&[true]).unwrap();
        assert_eq!((copy.pn,copy.seq),(2,u64::from(head)));
        let frozen=copy.frozen(key);
        assert_eq!(frozen.bytes(),wire);
        assert_eq!(frozen.metadata().pn,RecordPn(2));
        assert!(outer.take_due(110_000_001,&[true]).is_none());
        assert!(outer.complete(0,2,true,110_000_000));
        assert!(!outer.complete(0,2,true,110_000_001));
        assert_eq!(outer.sent(),1);
        assert_eq!(outer.first_record_wire_bytes(),32*wire.len() as u64);
        assert_eq!(outer.copied_record_wire_bytes(),wire.len() as u64);
        for i in 32..48u64{
            outer.on_firstsend(0,i+1,100+i*wire.len() as u64,
                wire,(i+1)*1_000_000).unwrap();
        }
        assert!(outer.next_due().is_none()); // bounded cooldown
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
        assert_eq!(c.copied_record_wire_bytes(),0);
        assert!(c.next_due().is_none());
    }
}
