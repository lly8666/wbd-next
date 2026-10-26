//! M1-013 owned shared Game/Normal scheduler, no wire or credential authority.
//! One logical pre-seal owned frame / epoch; lane queues contain only slot keys.
//! M0 must validate each lane and call the real per-lane codec/driver separately.
#![forbid(unsafe_code)]
use std::{collections::{BTreeMap,VecDeque},ops::Range};
use wbd_types::{BlockIdExt,LaneKey,LogicalPacketId,MonoNs,TunnelKey};
use wbd_types::buffer_contract::{UniqueSealable,checked_wire_range};
use crate::memory::UniqueBuffer;

const MAX_LANES:usize=8;
const MAX_SHARDS:usize=4;
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub enum Mode {Normal,Game}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub enum FlowDirection {Tx,Rx}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct GameScope {
    pub tunnel:TunnelKey,pub epoch:[u8;16],pub direction:FlowDirection,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct QualifiedLane {pub key:LaneKey,pub mss:usize}
/// External admission evidence is a precondition, NOT manufactured here.
/// No constructor grants Go credentials; M0 supplies and validates this list.
pub struct ActiveLaneSnapshot {pub scope:GameScope,lanes:Vec<QualifiedLane>}
impl ActiveLaneSnapshot {
    pub fn new(scope:GameScope,mut lanes:Vec<QualifiedLane>)->Option<Self>{
        if lanes.is_empty()||lanes.len()>MAX_LANES||scope.tunnel.generation==0||
            scope.epoch==[0;16]||lanes.iter().any(|x|
                x.key.tunnel!=scope.tunnel||x.key.generation==0||x.mss==0){
            return None;
        }
        lanes.sort_unstable_by_key(|x|(x.key.slot,x.key.generation));
        if lanes.windows(2).any(|w|w[0].key==w[1].key){return None;}
        Some(Self{scope,lanes})
    }
    pub fn lanes(&self)->&[QualifiedLane]{&self.lanes}
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct GameLimits{
    pub jobs:usize,pub logical_bytes:usize,
    pub lane_slots:usize,pub lane_bytes:usize,pub max_age_ns:u64,
}
impl GameLimits{
    pub fn valid(self)->bool{
        self.jobs>0&&self.jobs<=8192&&self.logical_bytes>0&&
        self.lane_slots>0&&self.lane_slots<=8192&&self.lane_bytes>0&&
        self.max_age_ns>0
    }
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub enum GameError{
    Scope,Unqualified,InvalidWindow,Capacity,ByteBudget,NoLane,
    TooLarge,Duplicate,Stale,Stopped,Overflow,WrongMode,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub enum DispatchOutcome {Accepted,PressureDrop}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct SendView<'a>{
    pub scope:GameScope,pub lane:LaneKey,pub mode:Mode,
    pub logical_id:Option<LogicalPacketId>,pub block:Option<BlockIdExt>,
    pub common_payload:&'a [u8],
}
#[derive(Clone,Copy,Debug,Default,Eq,PartialEq)]
pub struct GameCounters{
    pub logical_jobs:u64,pub common_bytes:u64,pub lane_copy_drop:u64,
    pub lane_dispatch:u64,pub stop_canceled:u64,
    pub scheduled:[u64;4],pub sent:[u64;4],pub abandoned:[u64;4],
    pub late_max_ns:[u64;4],pub late_total_ns:[u64;4],
}
struct Job{
    buffer:UniqueBuffer,wire:Range<usize>,mode:Mode,
    packet_id:Option<LogicalPacketId>,block:Option<BlockIdExt>,
    pending:usize,
}
#[derive(Clone,Copy)]
struct Pending {slot:usize,wire_bytes:usize,due:MonoNs,position:u8}
struct LaneReady{
    info:QualifiedLane,active:bool,
    q:VecDeque<Pending>,bytes:usize,
}
pub struct GameTx{
    scope:GameScope,limits:GameLimits,lanes:Vec<LaneReady>,
    slots:Vec<Option<Job>>,free:Vec<usize>,used:usize,
    cursor:usize,next_packet:u64,stopped:bool,
    copy_offsets_ns:[u64;4],staggered:bool,counters:GameCounters,
}
impl GameTx {
    pub fn new(snapshot:ActiveLaneSnapshot,limits:GameLimits)->Option<Self>{
        if !limits.valid() {return None;}
        let scope=snapshot.scope;
        let lanes=snapshot.lanes.into_iter().map(|info|LaneReady{
            info,active:true,q:VecDeque::with_capacity(limits.lane_slots),
            bytes:0
        }).collect::<Vec<_>>();
        let mut slots=Vec::with_capacity(limits.jobs);
        slots.resize_with(limits.jobs,||None);
        let free=(0..limits.jobs).rev().collect();
        Some(Self{scope,limits,lanes,slots,free,used:0,cursor:0,
            next_packet:0,stopped:false,copy_offsets_ns:[0;4],staggered:false,
            counters:GameCounters::default()})
    }
    pub fn counters(&self)->GameCounters{self.counters}
    pub fn staggered(&self)->bool{self.staggered}
    pub fn next_due_ns(&self)->Option<u64>{
        self.lanes.iter().filter_map(|l|l.q.front().map(|p|p.due.0)).min()
    }
    // 3Mbps worst-case 64B: ~5859pps *65ms =381 jobs.
    // 1024 has burst headroom; higher rates must pass capacity validation.
    pub fn configure_game4_stagger(&mut self)->Result<(),GameError>{
        if self.stopped||self.staggered||self.lanes.len()!=4||
           self.used!=0||self.free.len()!=self.limits.jobs||
           self.counters.logical_jobs!=0{return Err(GameError::WrongMode)}
        let old=self.limits.jobs;let jobs=1024;
        self.slots.resize_with(jobs,||None);
        self.free.extend((old..jobs).rev());
        self.limits.jobs=jobs;self.limits.logical_bytes=2*1024*1024;
        self.limits.lane_slots=1024;self.limits.lane_bytes=2*1024*1024;
        self.copy_offsets_ns=[0,4_000_000,20_000_000,60_000_000];
        self.staggered=true;Ok(())
    }
    /// Admit a new Game4 first copy when the finite work arena is full.
    /// Pressure is resolved by canceling the OLDEST queued logical job's
    /// outstanding refs, never by waiting for its 60ms due. The four FIFO
    /// heads identify that job; no unbounded queue walk or per-job timer.
    /// An older unsent first is droppable only on genuine saturation.
    /// All cancellations are PRODUCT abandonments, not carrier loss.
    pub fn reserve_game4_first(&mut self,new_bytes:usize,predicted_wire:usize){
        if !self.staggered||self.stopped{return}
        for _ in 0..4{
            let full=self.free.is_empty()||
                new_bytes>self.limits.logical_bytes.saturating_sub(self.used)||
                self.lanes.iter().any(|l|l.active &&
                    (l.q.len()>=self.limits.lane_slots||
                     predicted_wire>self.limits.lane_bytes.saturating_sub(l.bytes)));
            if !full{break}
            let oldest=self.lanes.iter().filter_map(|lane|{
                let p=lane.q.front()?;
                let id=self.slots[p.slot].as_ref()?.packet_id?.0;
                Some(id)
            }).min();
            let Some(oldest)=oldest else{break};
            let mut dropped=[usize::MAX;MAX_LANES];
            let mut count=0usize;
            for lane in &mut self.lanes{
                let old=lane.q.front().is_some_and(|p|
                    self.slots[p.slot].as_ref().and_then(|job|job.packet_id)
                    .is_some_and(|id|id.0==oldest));
                if old{
                    let p=lane.q.pop_front().expect("oldest queued");
                    lane.bytes-=p.wire_bytes;
                    dropped[count]=p.slot;
                    count+=1;
                    self.counters.lane_copy_drop+=1;
                    self.counters.abandoned[p.position as usize]+=1;
                }
            }
            if count==0{break}
            for &slot in &dropped[..count]{self.release(slot);}
        }
    }
    pub fn in_use(&self)->(usize,usize){
        (self.limits.jobs-self.free.len(),self.used)
    }
    pub fn lane_queued(&self,key:LaneKey)->Option<(usize,usize)>{
        self.lanes.iter().find(|l|l.info.key==key).map(|l|(l.q.len(),l.bytes))
    }
    pub fn scope(&self)->GameScope{self.scope}
    pub fn next_packet(&self)->Option<LogicalPacketId>{
        (!self.stopped).then_some(LogicalPacketId(self.next_packet))
    }
    /// Only NEW jobs use the updated snapshot. Old larger-MSS jobs remain
    /// on old draining lane queues; never hard-route them into smaller B.
    pub fn rotate(&mut self,next:ActiveLaneSnapshot)->Result<(),GameError>{
        if self.stopped{return Err(GameError::Stopped);}
        if next.scope!=self.scope{return Err(GameError::Scope);}
        let new_first=next.lanes.iter().find(|x|
            !self.lanes.iter().any(|l|l.info.key==x.key)).map(|x|x.key);
        let retained=self.lanes.iter().filter(|l|
            next.lanes.iter().any(|x|x.key==l.info.key)||!l.q.is_empty()).count();
        let new_count=next.lanes.iter().filter(|x|
            !self.lanes.iter().any(|l|l.info.key==x.key)).count();
        if retained+new_count>MAX_LANES{return Err(GameError::Capacity);}
        for lane in &mut self.lanes {lane.active=false;}
        for info in next.lanes {
            if let Some(lane)=self.lanes.iter_mut().find(|l|l.info.key==info.key){
                lane.info.mss=info.mss;lane.active=true;
            }else{
                self.lanes.push(LaneReady{info,active:true,
                    q:VecDeque::with_capacity(self.limits.lane_slots),bytes:0});
            }
        }
        self.compact_drained();
        if let Some(key)=new_first{
            self.cursor=self.lanes.iter().position(|l|l.info.key==key).unwrap_or(0);
        }else if self.cursor>=self.lanes.len(){self.cursor=0;}
        Ok(())
    }
    fn compact_drained(&mut self){
        self.lanes.retain(|l|l.active||!l.q.is_empty());
    }
    /// predicted_wire is the caller's conservative per-lane seal budget,
    /// not the logical payload length. No actual seal/packet-copy here.
    pub fn offer(&mut self,mut buffer:UniqueBuffer,wire:Range<usize>,
        mode:Mode,predicted_wire:usize,block:Option<BlockIdExt>,now:MonoNs)
        ->Result<Option<LogicalPacketId>,(GameError,UniqueBuffer)>{
        if self.stopped{return Err((GameError::Stopped,buffer));}
        let range=match checked_wire_range(buffer.writable().len(),wire){
            Ok(x)=>x,Err(_)=>return Err((GameError::InvalidWindow,buffer))
        };
        let bytes=range.len();
        if predicted_wire==0 {return Err((GameError::TooLarge,buffer));}
        if self.free.is_empty(){return Err((GameError::Capacity,buffer));}
        if bytes>self.limits.logical_bytes.saturating_sub(self.used){
            return Err((GameError::ByteBudget,buffer));
        }
        let mut choices=[usize::MAX;MAX_LANES];
        let mut count=0;
        // Stagger uses stable physical lane rank, not rotating first lane:
        // otherwise a later logical source could be due before an earlier
        // source on the SAME lane and violate FIFO/5ms after-due allowance.
        let first=if mode==Mode::Game&&self.staggered{0}else{self.cursor};
        for offset in 0..self.lanes.len(){
            let index=(first+offset)%self.lanes.len();
            let lane=&self.lanes[index];
            if !lane.active {continue;}
            if predicted_wire>lane.info.mss{
                self.counters.lane_copy_drop+=1;
                continue;
            }
            if lane.q.len()>=self.limits.lane_slots||
                predicted_wire>self.limits.lane_bytes.saturating_sub(lane.bytes){
                self.counters.lane_copy_drop+=1;continue;
            }
            choices[count]=index;count+=1;
            if mode==Mode::Normal{break;}
        }
        if count==0{return Err((GameError::NoLane,buffer));}
        if mode==Mode::Game&&self.next_packet==u64::MAX{
            return Err((GameError::Overflow,buffer));
        }
        let packet_id=if mode==Mode::Game{
            let id=LogicalPacketId(self.next_packet);
            self.next_packet+=1;Some(id)
        }else{None};
        let slot=self.free.pop().expect("free checked");
        self.used+=bytes;
        self.slots[slot]=Some(Job{
            buffer,wire:range,mode,packet_id,block,pending:count
        });
        for (position,&idx) in choices[..count].iter().enumerate(){
            let l=&mut self.lanes[idx];
            let delay=if mode==Mode::Game&&self.staggered{
                self.copy_offsets_ns[position]
            }else{0};
            l.q.push_back(Pending{slot,wire_bytes:predicted_wire,
                due:MonoNs(now.0.saturating_add(delay)),position:position as u8});
            l.bytes+=predicted_wire;
            if mode==Mode::Game&&self.staggered{
                self.counters.scheduled[position]+=1;
            }
        }
        // First qualified lane rotates per logical input, not per duplicated
        // Game copy; no lane is permanently the first during Normal overlap.
        if !self.staggered{
            self.cursor=(choices[0]+1)%self.lanes.len();
        }
        self.counters.logical_jobs+=1;
        self.counters.common_bytes+=bytes as u64;
        Ok(packet_id)
    }
    fn release(&mut self,slot:usize){
        let mut last=false;
        if let Some(job)=self.slots[slot].as_mut(){
            job.pending-=1;last=job.pending==0;
        }
        if last{
            let job=self.slots[slot].take().expect("pending points at job");
            self.used-=job.wire.len();
            self.free.push(slot);
        }
    }
    /// <=32 already-ready lane copies; the callback may immediately
    /// independently seal/dispatch this lane. No all-lane barrier.
    pub fn drain_ready<F:FnMut(SendView<'_>)->DispatchOutcome>(
        &mut self,now:MonoNs,budget:usize,mut dispatch:F)->usize{
        if self.stopped||self.lanes.is_empty(){return 0;}
        let mut processed=0;
        while processed<budget.min(32){
            let mut selected=None;
            for offset in 0..self.lanes.len(){
                let idx=(self.cursor+offset)%self.lanes.len();
                if self.lanes[idx].q.front().is_some_and(|p|p.due.0<=now.0){
                    selected=Some(idx);break;
                }
            }
            let Some(index)=selected else{break;};
            let entry=self.lanes[index].q.pop_front().expect("not empty");
            self.lanes[index].bytes-=entry.wire_bytes;
            self.cursor=(index+1)%self.lanes.len();
            let late=now.elapsed_since(entry.due);
            let expired=late>self.limits.max_age_ns;
            let pos=entry.position as usize;
            if expired{
                self.counters.lane_copy_drop+=1;
                if self.staggered{self.counters.abandoned[pos]+=1;}
            }else{
                let job=self.slots[entry.slot].as_mut().expect("queued job exists");
                let view=SendView{
                    scope:self.scope,lane:self.lanes[index].info.key,
                    mode:job.mode,logical_id:job.packet_id,block:job.block,
                    common_payload:&job.buffer.writable()[job.wire.clone()]
                };
                match dispatch(view){
                    DispatchOutcome::Accepted=>{
                        self.counters.lane_dispatch+=1;
                        if self.staggered{
                            self.counters.sent[pos]+=1;
                            self.counters.late_total_ns[pos]=
                                self.counters.late_total_ns[pos].saturating_add(late);
                            self.counters.late_max_ns[pos]=self.counters.late_max_ns[pos].max(late);
                        }
                    },
                    DispatchOutcome::PressureDrop=>{
                        self.counters.lane_copy_drop+=1;
                        if self.staggered{self.counters.abandoned[pos]+=1;}
                    },
                }
            }
            self.release(entry.slot);
            processed+=1;
        }
        self.compact_drained();
        if !self.lanes.is_empty(){self.cursor%=self.lanes.len();}
        processed
    }
    pub fn stop(&mut self)->usize{
        if self.stopped{return self.counters.stop_canceled as usize;}
        self.stopped=true;
        let mut canceled=0;
        for lane in &mut self.lanes{
            while let Some(p)=lane.q.pop_front(){
                let job=self.slots[p.slot].as_mut().expect("pending job");
                job.pending-=1;
                canceled+=1;
            }
            lane.bytes=0;
        }
        for i in 0..self.slots.len(){
            if let Some(job)=self.slots[i].take(){self.used-=job.wire.len();self.free.push(i);}
        }
        self.counters.stop_canceled=canceled as u64;
        canceled
    }
}
#[derive(Debug)]
pub struct ShardPiece{
    pub lane:LaneKey,pub wire:Range<usize>,pub buffer:UniqueBuffer,
}
pub struct CompletedBlock{
    pub scope:GameScope,pub block:BlockIdExt,
    pub packet:LogicalPacketId,pub pieces:[Option<ShardPiece>;MAX_SHARDS]
}
pub enum PieceProgress{Pending,Complete(CompletedBlock)}
struct OpenBlock{
    block:BlockIdExt,packet:LogicalPacketId,needed:u8,
    pieces:[Option<ShardPiece>;MAX_SHARDS],count:u8,bytes:usize,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct RxLimits{
    pub delivered_window:usize,pub open_blocks:usize,pub open_bytes:usize,
}
impl RxLimits{
    fn valid(self)->bool{
        self.delivered_window>0&&self.delivered_window<=65536&&
        self.open_blocks>0&&self.open_blocks<=8192&&self.open_bytes>0
    }
}
pub struct GameRx{
    scope:GameScope,admitted:Vec<LaneKey>,base:u64,
    // Physical bit positions are stable; head maps logical base to the ring.
    // A sequential new ID clears just the expired bit, not the entire window.
    delivered:Vec<u64>,head:usize,
    open:Vec<OpenBlock>,open_index:BTreeMap<BlockIdExt,usize>,
    used:usize,limit:RxLimits,stopped:bool,
    #[cfg(test)]
    dedup_clear_word_ops:u64,
}
impl GameRx{
    pub fn new(snapshot:ActiveLaneSnapshot,limits:RxLimits)->Option<Self>{
        if !limits.valid(){return None;}
        Some(Self{scope:snapshot.scope,admitted:snapshot.lanes.into_iter()
            .map(|l|l.key).collect(),base:0,
            delivered:vec![0;limits.delivered_window.div_ceil(64)],head:0,
            open:Vec::with_capacity(limits.open_blocks),open_index:BTreeMap::new(),
            used:0,limit:limits,stopped:false,
            #[cfg(test)]
            dedup_clear_word_ops:0})
    }
    pub fn widen_delivery_window_before_start(&mut self,width:usize)
        ->Result<(),GameError>{
        if self.stopped||self.base!=0||self.delivered.iter().any(|w|*w!=0)||
           width<=self.limit.delivered_window||width>65536{
            return Err(GameError::WrongMode)
        }
        self.delivered.resize(width.div_ceil(64),0);
        self.limit.delivered_window=width;Ok(())
    }
    pub fn add_lane(&mut self,scope:GameScope,lane:LaneKey)->Result<(),GameError>{
        if scope!=self.scope{return Err(GameError::Scope);}
        if self.stopped{return Err(GameError::Stopped);}
        if lane.tunnel!=self.scope.tunnel{return Err(GameError::Unqualified);}
        if !self.admitted.contains(&lane){
            if self.admitted.len()>=MAX_LANES{return Err(GameError::Capacity);}
            self.admitted.push(lane);
        }
        Ok(())
    }
    pub fn open_state(&self)->(usize,usize){(self.open.len(),self.used)}
    fn validate(&self,scope:GameScope,lane:LaneKey)->Result<(),GameError>{
        if self.stopped{return Err(GameError::Stopped);}
        if scope!=self.scope{return Err(GameError::Scope);}
        if !self.admitted.contains(&lane){return Err(GameError::Unqualified);}
        Ok(())
    }
    /// Retains owned authenticated *shards* across any qualified lane.
    /// A complete set is handed to M3 for decode/reassembly; never claims
    /// these pieces alone were authenticated as a Game business packet.
    pub fn offer_piece(&mut self,scope:GameScope,lane:LaneKey,
        block:BlockIdExt,packet:LogicalPacketId,index:u8,needed:u8,
        mut buffer:UniqueBuffer,wire:Range<usize>)
        ->Result<PieceProgress,(GameError,UniqueBuffer)>{
        if let Err(e)=self.validate(scope,lane){return Err((e,buffer));}
        if needed==0||needed as usize>MAX_SHARDS||index>=needed{
            return Err((GameError::InvalidWindow,buffer));
        }
        let range=match checked_wire_range(buffer.writable().len(),wire){
            Ok(r)=>r,Err(_)=>return Err((GameError::InvalidWindow,buffer))
        };
        let bytes=range.len();
        // Deterministic O(log open_blocks) lookup, not a linear scan over 8192.
        let found=self.open_index.get(&block).copied();
        if let Some(i)=found{
            if self.open[i].packet!=packet||self.open[i].needed!=needed{
                return Err((GameError::Scope,buffer));
            }
            if self.open[i].pieces[index as usize].is_some(){
                return Err((GameError::Duplicate,buffer));
            }
        }else if self.open.len()>=self.limit.open_blocks{
            return Err((GameError::Capacity,buffer));
        }
        if bytes>self.limit.open_bytes.saturating_sub(self.used){
            return Err((GameError::ByteBudget,buffer));
        }
        let at=if let Some(i)=found{i}else{
            let slot=self.open.len();
            self.open.push(OpenBlock{block,packet,needed,
                pieces:std::array::from_fn(|_|None),count:0,bytes:0});
            let previous=self.open_index.insert(block,slot);
            debug_assert!(previous.is_none());
            slot
        };
        self.open[at].pieces[index as usize]=Some(ShardPiece{lane,wire:range,buffer});
        self.open[at].count+=1;
        self.open[at].bytes+=bytes;self.used+=bytes;
        if self.open[at].count<needed {return Ok(PieceProgress::Pending);}
        let completed=self.open.swap_remove(at);
        self.open_index.remove(&block);
        // swap_remove moved the last open block into 'at', if any.
        if at<self.open.len(){
            self.open_index.insert(self.open[at].block,at);
        }
        self.used-=completed.bytes;
        Ok(PieceProgress::Complete(CompletedBlock{
            scope,block,packet,pieces:completed.pieces
        }))
    }
    /// Clear physical ring positions [from,to), bounded by words *actually*
    /// expired, with at most two partial words. No full-window rotation.
    fn clear_interval(&mut self,mut from:usize,to:usize){
        while from<to {
            let word=from/64;
            let until=to.min((word+1)*64);
            let width=until-from;
            let low=from%64;
            let mask=if width==64 {u64::MAX}
                else {((1u64<<width)-1)<<low};
            self.delivered[word]&=!mask;
            #[cfg(test)]
            {self.dedup_clear_word_ops+=1;}
            from=until;
        }
    }
    fn expire_head(&mut self,shift:usize,width:usize){
        if shift>=width {
            self.delivered.fill(0);
            self.head=0;
            #[cfg(test)]
            {self.dedup_clear_word_ops+=self.delivered.len() as u64;}
        }else {
            let first=(width-self.head).min(shift);
            self.clear_interval(self.head,self.head+first);
            if first<shift {self.clear_interval(0,shift-first);}
            self.head=(self.head+shift)%width;
        }
    }
    /// Read-only early duplicate/stale test AFTER per-lane AEAD and Game
    /// header decoding. Does NOT mark a packet as delivered; capacity failure
    /// must not evict the window or suppress another lane's valid first copy.
    pub fn first_delivery_candidate(&self,scope:GameScope,lane:LaneKey,
        id:LogicalPacketId)->Result<bool,GameError>{
        self.validate(scope,lane)?;
        if id.0<self.base{return Err(GameError::Stale)}
        let width=self.limit.delivered_window;
        let delta=id.0-self.base;
        if delta>=width as u64{return Ok(true)}
        let position=(self.head+delta as usize)%width;
        Ok(self.delivered[position/64]&(1u64<<(position%64))==0)
    }
    /// Consumes only M0/M3-authenticated and decoded/reassembled results.
    /// Shared logical PacketID dedup across lanes and recovered candidates.
    /// Older-than-window IDs are refused rather than accidentally redelivered.
    pub fn first_delivery(&mut self,scope:GameScope,lane:LaneKey,
        id:LogicalPacketId,buffer:UniqueBuffer)
        ->Result<UniqueBuffer,(GameError,UniqueBuffer)>{
        if let Err(e)=self.validate(scope,lane){return Err((e,buffer));}
        if id.0<self.base{return Err((GameError::Stale,buffer));}
        let width=self.limit.delivered_window;
        let delta=id.0-self.base;
        if delta>=width as u64 {
            // Subtract after delta>=width; supports IDs up to u64::MAX
            // without ever computing base+width (which could overflow).
            let shift=delta-(width as u64)+1;
            self.expire_head(shift.min(width as u64) as usize,width);
            self.base=id.0-(width as u64)+1;
        }
        let position=(self.head+(id.0-self.base) as usize)%width;
        let word=position/64;
        let mask=1u64<<(position%64);
        if self.delivered[word]&mask!=0 {
            return Err((GameError::Duplicate,buffer));
        }
        self.delivered[word]|=mask;
        Ok(buffer)
    }
    pub fn stop(&mut self)->usize{
        if self.stopped{return 0;}
        self.stopped=true;
        let n:usize=self.open.iter().map(|b|b.count as usize).sum();
        self.open.clear();self.open_index.clear();self.used=0;n
    }
}

#[cfg(test)]
#[path="game_shared_tests.rs"]
mod tests;
