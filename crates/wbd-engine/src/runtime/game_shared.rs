//! M1-013 owned shared Game/Normal scheduler, no wire or credential authority.
//! One logical pre-seal owned frame / epoch; lane queues contain only slot keys.
//! M0 must validate each lane and call the real per-lane codec/driver separately.
#![forbid(unsafe_code)]
use std::{collections::VecDeque,ops::Range};
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
}
struct Job{
    buffer:UniqueBuffer,wire:Range<usize>,mode:Mode,
    packet_id:Option<LogicalPacketId>,block:Option<BlockIdExt>,
    pending:usize,
}
#[derive(Clone,Copy)]
struct Pending {slot:usize,wire_bytes:usize,at:MonoNs}
struct LaneReady{
    info:QualifiedLane,active:bool,
    q:VecDeque<Pending>,bytes:usize,
}
pub struct GameTx{
    scope:GameScope,limits:GameLimits,lanes:Vec<LaneReady>,
    slots:Vec<Option<Job>>,free:Vec<usize>,used:usize,
    cursor:usize,next_packet:u64,stopped:bool,
    counters:GameCounters,
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
            next_packet:0,stopped:false,counters:GameCounters::default()})
    }
    pub fn counters(&self)->GameCounters{self.counters}
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
        for offset in 0..self.lanes.len(){
            let index=(self.cursor+offset)%self.lanes.len();
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
        for &idx in &choices[..count]{
            let l=&mut self.lanes[idx];
            l.q.push_back(Pending{slot,wire_bytes:predicted_wire,at:now});
            l.bytes+=predicted_wire;
        }
        // First qualified lane rotates per logical input, not per duplicated
        // Game copy; no lane is permanently the first during Normal overlap.
        self.cursor=(choices[0]+1)%self.lanes.len();
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
                if !self.lanes[idx].q.is_empty(){selected=Some(idx);break;}
            }
            let Some(index)=selected else{break;};
            let entry=self.lanes[index].q.pop_front().expect("not empty");
            self.lanes[index].bytes-=entry.wire_bytes;
            self.cursor=(index+1)%self.lanes.len();
            let expired=now.elapsed_since(entry.at)>self.limits.max_age_ns;
            if expired{
                self.counters.lane_copy_drop+=1;
            }else{
                let job=self.slots[entry.slot].as_mut().expect("queued job exists");
                let view=SendView{
                    scope:self.scope,lane:self.lanes[index].info.key,
                    mode:job.mode,logical_id:job.packet_id,block:job.block,
                    common_payload:&job.buffer.writable()[job.wire.clone()]
                };
                match dispatch(view){
                    DispatchOutcome::Accepted=>self.counters.lane_dispatch+=1,
                    DispatchOutcome::PressureDrop=>self.counters.lane_copy_drop+=1,
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
    scope:GameScope,admitted:Vec<LaneKey>,base:u64,delivered:Vec<bool>,
    open:Vec<OpenBlock>,used:usize,limit:RxLimits,stopped:bool,
}
impl GameRx{
    pub fn new(snapshot:ActiveLaneSnapshot,limits:RxLimits)->Option<Self>{
        if !limits.valid(){return None;}
        Some(Self{scope:snapshot.scope,admitted:snapshot.lanes.into_iter()
            .map(|l|l.key).collect(),base:0,
            delivered:vec![false;limits.delivered_window],
            open:Vec::with_capacity(limits.open_blocks),
            used:0,limit:limits,stopped:false})
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
        let found=self.open.iter().position(|b|b.block==block);
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
            self.open.push(OpenBlock{block,packet,needed,
                pieces:std::array::from_fn(|_|None),count:0,bytes:0});
            self.open.len()-1
        };
        self.open[at].pieces[index as usize]=Some(ShardPiece{lane,wire:range,buffer});
        self.open[at].count+=1;
        self.open[at].bytes+=bytes;self.used+=bytes;
        if self.open[at].count<needed {return Ok(PieceProgress::Pending);}
        let completed=self.open.swap_remove(at);
        self.used-=completed.bytes;
        Ok(PieceProgress::Complete(CompletedBlock{
            scope,block,packet,pieces:completed.pieces
        }))
    }
    /// Consumes only M0/M3-authenticated and decoded/reassembled results.
    /// Shared logical PacketID dedup across lanes and recovered candidates.
    /// Older-than-window IDs are refused rather than accidentally redelivered.
    pub fn first_delivery(&mut self,scope:GameScope,lane:LaneKey,
        id:LogicalPacketId,buffer:UniqueBuffer)
        ->Result<UniqueBuffer,(GameError,UniqueBuffer)>{
        if let Err(e)=self.validate(scope,lane){return Err((e,buffer));}
        if id.0<self.base{return Err((GameError::Stale,buffer));}
        let width=self.delivered.len() as u64;
        if id.0-self.base>=width{
            let delta=id.0-self.base;
            let shift=usize::try_from(delta-width+1).unwrap_or(usize::MAX);
            if shift>=self.delivered.len(){
                self.delivered.fill(false);
            }else{
                self.delivered.rotate_left(shift);
                let end=self.delivered.len();
                self.delivered[end-shift..].fill(false);
            }
            self.base=id.0-width+1;
        }
        let index=(id.0-self.base) as usize;
        if self.delivered[index]{return Err((GameError::Duplicate,buffer));}
        self.delivered[index]=true;
        Ok(buffer)
    }
    pub fn stop(&mut self)->usize{
        if self.stopped{return 0;}
        self.stopped=true;
        let n:usize=self.open.iter().map(|b|b.count as usize).sum();
        self.open.clear();self.used=0;n
    }
}

#[cfg(test)]
#[path="game_shared_tests.rs"]
mod tests;
