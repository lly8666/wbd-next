//! Game FEC *presentation only* outer TCP replay, shared by Windows NPF
//! and Linux raw M4. It is NOT a delivery retry, FEC source, ACK, or credit.
 //! One sparse frozen ciphertext per lane; no heap work on ordinary sends,
 //! no global M2 allocator, no background thread or per-packet wall clock.
use std::sync::Arc;
use wbd_types::{LaneKey,RecordPn,SeqOffset,BufferKey};
use wbd_types::buffer_contract::{BufferOrigin,FrozenMetadata,FrozenRecordHandle};

const SAMPLE_MASK:u64=255; // at most one optional copy per 256 copied records
const AFTER_FIRST_NS:u64=120_000_000; // same-payload TCP-looking copy
const MIN_INTERVAL_NS:u64=250_000_000; // at most four copies/second/lane
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
}
pub(crate) struct CosmeticOuter{
    lanes:Vec<Lane>,
}
impl CosmeticOuter{
    pub fn new(count:usize)->Self{
        Self{lanes:(0..count).map(|_|Lane{
            seen:0,not_before:0,pending:None,held:None,sent:0
        }).collect()}
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
        for i in 1..256{
            assert!(!c.should_sample(0),"no per-source duplicate allocation");
            assert!(c.next_due().is_none());
            let _=i;
        }
        assert!(c.should_sample(0));
        c.sample(0,77,10001,&wire,5_000_000);
        assert_eq!(c.next_due(),Some(125_000_000));
        assert!(c.take_due(124_999_999,&[]).is_none());
        let copy=c.take_due(125_000_000,&[]).unwrap();
        assert_eq!(copy.lane,0);assert_eq!(copy.pn,77);
        assert_eq!(copy.seq,10001);assert_eq!(&*copy.wire,&wire);
        let key=LaneKey{tunnel:wbd_types::TunnelKey{slot:1,generation:7},
            slot:1,generation:7};
        let f=copy.frozen(key);
        assert_eq!(f.metadata().pn,RecordPn(77));
        assert_eq!(f.metadata().seq,SeqOffset(10001));
        assert_eq!(f.bytes(),wire);
        assert!(c.take_due(125_000_001,&[]).is_none());
        assert!(!c.complete(0,78,true,125_000_000));
        assert!(c.complete(0,77,true,125_000_000));
        assert!(!c.complete(0,77,true,125_000_000));
        assert_eq!(c.sent(),1);
    }
    #[test]
    fn game_fec_cosmetic_cannot_resume_retired_lane_or_double_credit(){
        let mut c=CosmeticOuter::new(2);
        c.sample(1,4,120,b"immutable",50);
        assert!(c.take_due(120_000_051,&[true,false]).is_none());
        assert_eq!(c.sent(),0);
        c.sample(0,9,17,b"cipher",1);
        let row=c.take_due(120_000_002,&[true,true]).unwrap();
        assert_eq!(row.pn,9);
        assert!(c.complete(0,9,false,120_000_002));
        assert_eq!(c.sent(),0);
        assert!(c.next_due().is_none());
    }
}
