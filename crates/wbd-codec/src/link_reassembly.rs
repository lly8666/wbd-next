//! Bounded LINK reassembly slow path; old Go 20B wire, stronger fail-closed
//! conflicting-fragment retirement per modules/06-LINK-MTU.md.
//! Input MUST have passed AEAD authentication outside this codec module.
//! Owner supplies extended packet ID, tunnel epoch, direction and mono ms.
#![forbid(unsafe_code)]
use std::collections::BTreeMap;
use crate::link_fec_wire::{inspect_link,Fragment,LinkMode,LinkView,WireError,LINK_HEADER,MAX_LOGICAL_DATAGRAM};

pub const MAX_ASSEMBLIES:usize=16;
pub const MAX_RETIRED:usize=64;
pub const MAX_BUFFERED_BYTES:usize=MAX_ASSEMBLIES*MAX_LOGICAL_DATAGRAM;
pub const MAX_BUFFERED_FRAGMENTS:usize=MAX_LOGICAL_DATAGRAM;
pub const MAX_METADATA_BYTES:usize=1024*1024;
pub const ASSEMBLY_TTL_MS:u64=5_000;
pub const RETIRED_TTL_MS:u64=10_000;
const ASSEMBLY_CHARGE:usize=256;
const PART_CHARGE:usize=128;

#[derive(Clone,Copy,Debug,Eq,PartialEq,Ord,PartialOrd)]
pub enum LinkDirection { ClientToServer,ServerToClient }
#[derive(Clone,Copy,Debug,Eq,PartialEq,Ord,PartialOrd)]
pub struct ReassemblyScope {
    pub tunnel_epoch:u64,
    pub direction:LinkDirection,
    pub packet_id_ext:u64,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub enum ReassemblyError {
    Wire(WireError),InvalidScope,InvalidBudget,InvalidLayout,
    ConflictingFragment,NoCapacity
}
#[derive(Debug,Eq,PartialEq)]
pub enum LinkDelivery<'a>{
    Ordinary(&'a [u8]),
    Reassembled(Vec<u8>),
    Pending,
    Discarded,
}
#[derive(Clone,Copy,Debug,Default,Eq,PartialEq)]
pub struct ReassemblyState{
    pub assemblies:usize,
    pub buffered_fragments:usize,
    pub buffered_bytes:usize,
    pub metadata_charged_bytes:usize,
    pub retired_packet_ids:usize,
}
struct Assembly {
    count:u16,total:usize,created_at_ms:u64,
    stride:Option<usize>,parts:BTreeMap<u16,Vec<u8>>,bytes:usize,
}
pub struct ReassemblyTable {
    frame_mtu:usize,min_frame_mtu:usize,mode:LinkMode,
    assemblies:BTreeMap<ReassemblyScope,Assembly>,
    retired:BTreeMap<ReassemblyScope,u64>,
    last_now_ms:u64,
}
impl ReassemblyTable{
    pub fn new(frame_mtu:usize,min_frame_mtu:usize,mode:LinkMode)->Result<Self,ReassemblyError>{
        if !(LINK_HEADER+1..=MAX_LOGICAL_DATAGRAM).contains(&frame_mtu)
            || !(LINK_HEADER+1..=frame_mtu).contains(&min_frame_mtu)
        {return Err(ReassemblyError::InvalidBudget);}
        Ok(Self{frame_mtu,min_frame_mtu,mode,
            assemblies:BTreeMap::new(),retired:BTreeMap::new(),last_now_ms:0})
    }
    /// Owner-authorized MTU transition, not guessed from unauthenticated
    /// traffic. Preserve existing packet assemblies and their immutable
    /// per-packet stride across both MTU downshifts and upshifts.
    ///
    /// The RX envelope accepts the largest *previously authorized* frame
    /// while old in-flight packets are draining; new frame production must
    /// use the current TX FrameBudget, never this permissive RX highwater.
    /// Keeping the smallest approved frame size retains a bounded declared
    /// fragment-count test for packets created during any of these epochs.
    pub fn update_authorized_frame_mtu(&mut self,current_frame_mtu:usize)
        ->Result<(),ReassemblyError>{
        if !(LINK_HEADER+1..=MAX_LOGICAL_DATAGRAM).contains(&current_frame_mtu){
            return Err(ReassemblyError::InvalidBudget);
        }
        self.frame_mtu=self.frame_mtu.max(current_frame_mtu);
        self.min_frame_mtu=self.min_frame_mtu.min(current_frame_mtu);
        Ok(())
    }
    /// Receive-only bounds, not a transmitter budget.
    pub fn accepted_frame_range(&self)->(usize,usize){
        (self.min_frame_mtu,self.frame_mtu)
    }
    pub fn state(&self)->ReassemblyState{
        let mut s=ReassemblyState{assemblies:self.assemblies.len(),
            retired_packet_ids:self.retired.len(),..ReassemblyState::default()};
        for a in self.assemblies.values(){
            s.buffered_fragments+=a.parts.len();
            s.buffered_bytes+=a.bytes;
            s.metadata_charged_bytes+=ASSEMBLY_CHARGE+a.parts.len()*PART_CHARGE;
        }
        s.metadata_charged_bytes+=self.retired.len()*core::mem::size_of::<(ReassemblyScope,u64)>();
        s
    }
    pub fn expire(&mut self,now_ms:u64){
        let now=now_ms.max(self.last_now_ms);self.last_now_ms=now;
        let dead=self.assemblies.iter().filter_map(|(k,a)|
            (now>=a.created_at_ms.saturating_add(ASSEMBLY_TTL_MS)).then_some(*k)
        ).collect::<Vec<_>>();
        for k in dead {self.assemblies.remove(&k);self.retire(k,now);}
        self.retired.retain(|_,at|now<at.saturating_add(RETIRED_TTL_MS));
    }
    fn retire(&mut self,k:ReassemblyScope,now:u64){
        if !self.retired.contains_key(&k) && self.retired.len()>=MAX_RETIRED{
            if let Some(old)=self.retired.iter().min_by_key(|(key,t)|(**t,**key))
                .map(|(key,_)|*key){self.retired.remove(&old);}
        }
        self.retired.insert(k,now);
    }
    fn drop_retire(&mut self,k:ReassemblyScope,now:u64){
        self.assemblies.remove(&k);self.retire(k,now);
    }
    fn evict_oldest(&mut self,now:u64)->Option<ReassemblyScope>{
        let k=self.assemblies.iter().min_by_key(|(k,a)|(a.created_at_ms,**k))
            .map(|(k,_)|*k)?;
        self.drop_retire(k,now);Some(k)
    }
    /// Return room for a separate completed output while keeping the target
    /// packet's owned parts alive. These two copies coexist until the caller
    /// has completed the contiguous business buffer.
    fn evict_oldest_except(&mut self,exempt:ReassemblyScope,now:u64)->Option<ReassemblyScope>{
        let k=self.assemblies.iter().filter(|(key,_)|**key!=exempt)
            .min_by_key(|(key,a)|(a.created_at_ms,**key))
            .map(|(key,_)|*key)?;
        self.drop_retire(k,now);Some(k)
    }
    /// Only after record authentication. Ordinary packet is a borrowed,
    /// zero-copy fast path: no state lookup or timer scan or added LINK20.
    pub fn push_after_record_auth<'a>(&mut self,wire:&'a [u8],scope:ReassemblyScope,now_ms:u64)
        ->Result<LinkDelivery<'a>,ReassemblyError>{
        let fragment=match inspect_link(wire,self.frame_mtu,self.mode)
            .map_err(ReassemblyError::Wire)?{
            LinkView::Ordinary(data)=>return Ok(LinkDelivery::Ordinary(data)),
            LinkView::Fragment(f)=>f,
        };
        if scope.packet_id_ext==0 || scope.packet_id_ext as u32 !=fragment.packet_id{
            return Err(ReassemblyError::InvalidScope);
        }
        self.expire(now_ms);let now=self.last_now_ms;
        if self.retired.contains_key(&scope){return Ok(LinkDelivery::Discarded);}
        self.push_fragment(fragment,scope,now)
    }
    fn push_fragment<'a>(&mut self,f:Fragment<'a>,k:ReassemblyScope,now:u64)
        ->Result<LinkDelivery<'a>,ReassemblyError>{
        let count=usize::from(f.count);let total=usize::from(f.total_len);
        let min_chunk=self.min_frame_mtu-LINK_HEADER;
        // Additional deliberate security guard vs permissive old-Go count.
        // Never allocate an attacker-controlled declared parts[count] array.
        if count>total.div_ceil(min_chunk){
            self.drop_retire(k,now);return Err(ReassemblyError::InvalidLayout);
        }
        if count==1{
            if self.assemblies.contains_key(&k){
                self.drop_retire(k,now);return Err(ReassemblyError::ConflictingFragment);
            }
            let mut out=Vec::new();
            out.try_reserve_exact(f.payload.len()).map_err(|_|ReassemblyError::NoCapacity)?;
            out.extend_from_slice(f.payload);
            self.retire(k,now);
            return Ok(LinkDelivery::Reassembled(out));
        }
        if let Some(a)=self.assemblies.get(&k){
            if a.count!=f.count || a.total!=total{
                self.drop_retire(k,now);return Err(ReassemblyError::ConflictingFragment);
            }
        }else{
            while self.assemblies.len()>=MAX_ASSEMBLIES{self.evict_oldest(now);}
            self.assemblies.insert(k,Assembly{count:f.count,total,
                created_at_ms:now,stride:None,parts:BTreeMap::new(),bytes:0});
        }
        let a=self.assemblies.get(&k).expect("just inserted");
        if let Some(old)=a.parts.get(&f.index){
            if old.as_slice()==f.payload{return Ok(LinkDelivery::Pending);}
            self.drop_retire(k,now);return Err(ReassemblyError::ConflictingFragment);
        }
        let last=usize::from(f.index)==count-1;
        let stride=if last{a.stride}else{Some(f.payload.len())};
        let shape=if let Some(s)=stride{
            let prefix=(count-1).checked_mul(s);
            if let Some(prefix)=prefix{
                if prefix>=total{false}else{
                    let tail=total-prefix;
                    s>0 && tail>0 && tail<=s &&
                    (if last{f.payload.len()==tail}
                     else{a.stride.is_none_or(|prior|prior==s)
                        && a.parts.get(&(f.count-1)).is_none_or(|p|p.len()==tail)})
                }
            }else{false}
        }else{true};
        if !shape{
            self.drop_retire(k,now);return Err(ReassemblyError::ConflictingFragment);
        }
        if a.bytes+f.payload.len()>total{
            self.drop_retire(k,now);return Err(ReassemblyError::InvalidLayout);
        }
        loop{
            let s=self.state();
            if s.buffered_bytes+f.payload.len()<=MAX_BUFFERED_BYTES
                && s.buffered_fragments<MAX_BUFFERED_FRAGMENTS
                && s.metadata_charged_bytes+PART_CHARGE<=MAX_METADATA_BYTES{break;}
            let evicted=self.evict_oldest(now).ok_or(ReassemblyError::NoCapacity)?;
            if evicted==k{return Ok(LinkDelivery::Discarded);}
        }
        let mut part=Vec::new();
        part.try_reserve_exact(f.payload.len()).map_err(|_|ReassemblyError::NoCapacity)?;
        part.extend_from_slice(f.payload);
        let a=self.assemblies.get_mut(&k).expect("preserved by capacity");
        a.bytes+=f.payload.len();if !last{a.stride=stride;}
        a.parts.insert(f.index,part);
        if a.parts.len()!=count{return Ok(LinkDelivery::Pending);}
        if a.bytes!=total{
            self.drop_retire(k,now);return Err(ReassemblyError::InvalidLayout);
        }
        // The old parts and contiguous output are simultaneously live here.
        // A completed packet must not bypass the ~1MiB RX payload budget by
        // allocating a second copy on top of sixteen near-complete assemblies.
        // Evict only OTHER incomplete packets: never silently discard a ready
        // packet when capacity can be recovered without touching its data.
        while self.state().buffered_bytes.checked_add(total)
            .is_none_or(|peak|peak>MAX_BUFFERED_BYTES) {
            if self.evict_oldest_except(k,now).is_none(){
                self.drop_retire(k,now);
                return Err(ReassemblyError::NoCapacity);
            }
        }
        let mut out=Vec::new();
        if out.try_reserve_exact(total).is_err(){
            self.drop_retire(k,now);
            return Err(ReassemblyError::NoCapacity);
        }
        {
            let a=self.assemblies.get(&k).expect("completed");
            for i in 0..f.count{
                let piece=a.parts.get(&i).ok_or(ReassemblyError::InvalidLayout)?;
                out.extend_from_slice(piece);
            }
        }
        if out.len()!=total{
            self.drop_retire(k,now);return Err(ReassemblyError::InvalidLayout);
        }
        self.drop_retire(k,now);
        Ok(LinkDelivery::Reassembled(out))
    }
}
