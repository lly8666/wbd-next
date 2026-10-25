//! Authenticated Game2/4 fixed-FEC inner-symbol composition.
//! Original Game per-lane AEAD/PN and logical de-dup happen BEFORE M3 recovery.
//! Game+FEC is explicitly configured on both endpoints; no silent downgrade.
#![forbid(unsafe_code)]
use crate::memory::Arena;
use crate::runtime::fec2_owner::{
    Fec2Owner,FecMode,Profile as OwnerProfile,Limits,ParityJob,OwnerReport
};
use crate::fec2_staged::StagedParity;
use crate::v4_fec2_live_rx::{Fec2LiveRx,VerifiedReceiveEpoch};
use crate::v4_game_lane::Error as GameError;
use wbd_codec::fec_v2::{self,Profile as CodecProfile,Rs16,BackendChoice,MAX_BATCH_ROWS};
use wbd_types::{ConfigRevision,MonoNs,LogicalPacketId};
use wbd_types::buffer_contract::UniqueSealable;

#[derive(Clone,Copy,Debug,Default)]
pub(crate) struct GameFecCounters{
    pub source_offered:u64,pub parity_offered:u64,
    pub parity_kernel_copied:u64,pub recovered_candidate:u64,
    pub source_first_candidate:u64,pub expired:u64,pub failed:u64,
}
struct Flight{
    job:ParityJob,prepared:StagedParity,copied:u8,
    rows:Vec<(LogicalPacketId,bool)>,
}
pub(crate) struct GameFec{
    owner:Fec2Owner,rx:Fec2LiveRx,scope:VerifiedReceiveEpoch,
    rs:Rs16,profile:CodecProfile,math_scratch:Vec<u8>,
    repair_scratch:[Vec<u8>;MAX_BATCH_ROWS],
    source_arena:Arena,in_flight:Option<Flight>,
    budget:usize,lanes:usize,counters:GameFecCounters,
}
impl GameFec{
    pub(crate) fn new(profile:u8,scope:VerifiedReceiveEpoch,
        game_inner_mtu:usize,lanes:usize)->Option<Self>{
        if !matches!(lanes,2|4)||game_inner_mtu<=32 {return None}
        let (owner_profile,codec_profile)=match profile{
            0=>(OwnerProfile::Light,CodecProfile::Light),
            1=>(OwnerProfile::Mild,CodecProfile::Mild),
            2=>(OwnerProfile::Medium,CodecProfile::Medium),
            3=>(OwnerProfile::Balanced,CodecProfile::Balanced),
            4=>(OwnerProfile::High,CodecProfile::High),
            5=>(OwnerProfile::Strong,CodecProfile::Strong),
            6=>(OwnerProfile::Maximum,CodecProfile::Maximum),
            _=>return None,
        };
        // Game logical payload budget after a one-byte typed FEC symbol.
        // FEC M3 reserves its full 14 bytes for either source or parity.
        let budget=game_inner_mtu-1;
        let owner=Fec2Owner::new(FecMode::Game,owner_profile,
            ConfigRevision(1),Limits{
                pending_bytes:2*1024*1024,pending_jobs:64,
                max_frame:budget.checked_sub(14)?
            })?;
        // Existing RX requires wire_max-31 == FEC budget. It never
        // allocates a second AEAD opener: GameAdapter already authenticated.
        let rx=Fec2LiveRx::from_authenticated_scope(
            scope,budget+31).ok()?;
        let source_arena=Arena::new(
            scope.generation^0x4700_0000,128,2048,128,512*1024).ok()?;
        Some(Self{owner,rx,scope,rs:Rs16::new(),profile:codec_profile,
            math_scratch:Vec::new(),
            repair_scratch:std::array::from_fn(|_|Vec::new()),
            source_arena,in_flight:None,budget,lanes,
            counters:GameFecCounters::default()})
    }
    pub(crate) fn max_original(&self)->usize{
        self.budget.saturating_sub(14)
    }
    pub(crate) fn counters(&self)->GameFecCounters{self.counters}
    pub(crate) fn owner_report(&self)->OwnerReport{self.owner.report()}
    /// The callback submits a logical Game symbol to the existing GameTx.
    /// Caller immediately drains first source copies before any parity.
    pub(crate) fn offer<F>(&mut self,frame:&[u8],now:MonoNs,
        mut submit:F)->Result<LogicalPacketId,GameError>
    where F:FnMut(&[u8])->Result<LogicalPacketId,GameError>{
        if frame.is_empty()||frame.len()>self.max_original(){
            return Err(GameError::Invalid)
        }
        let mut slab=self.source_arena.allocate().map_err(|_|GameError::Capacity)?;
        slab.writable()[..frame.len()].copy_from_slice(frame);
        let mut ready=None;
        let mut bad=None;
        let budget=self.budget;
        let accepted=self.owner.push_source(slab,0..frame.len(),now,|first|{
            let Some(ticket)=first.ticket else{return false};
            let mut typed=[0u8;2048];
            typed[0]=2;
            let Ok(count)=fec_v2::source_into(ticket.block_id,
                ticket.index,first.frame,budget,&mut typed[1..])
                else{bad=Some(GameError::Invalid);return false};
            match submit(&typed[..count+1]){
                Ok(id)=>{ready=Some(id);true},
                Err(e)=>{bad=Some(e);false},
            }
        }).map_err(|(e,_)|{
            match e{
                crate::runtime::fec2_owner::FecError::Stopped=>GameError::Stopped,
                crate::runtime::fec2_owner::FecError::Exhausted=>GameError::Capacity,
                _=>GameError::Invalid
            }
        })?;
        if !accepted.source_enqueued {self.counters.failed+=1;}
        let Some(id)=ready else{return Err(bad.unwrap_or(GameError::Capacity))};
        self.counters.source_offered+=1;
        Ok(id)
    }
    /// At most one 4-row SIMD quantum per call; never wait for a second group,
    /// never allocate a separate timer or stall a fresh source.
    pub(crate) fn poll<F>(&mut self,now:MonoNs,
        mut submit:F)->Result<usize,GameError>
    where F:FnMut(&[u8])->Result<LogicalPacketId,GameError>{
        self.owner.on_due(now).map_err(|_|GameError::Invalid)?;
        if self.in_flight.is_none(){
            let Some(mut job)=self.owner.take_parity(now)
                .map_err(|_|GameError::Invalid)? else{return Ok(0)};
            let prepared=match StagedParity::from_owner_job_with_workspace(
                &mut job,self.profile,self.budget,
                std::mem::take(&mut self.math_scratch)){
                Ok(p)=>p,
                Err(_)=>{self.counters.failed+=1;
                    self.owner.finish_parity(job,0,false);
                    return Err(GameError::Invalid)}
            };
            self.in_flight=Some(Flight{
                job,prepared,copied:0,rows:Vec::with_capacity(20),
            });
        }
        let flight=self.in_flight.as_mut().unwrap();
        if now.0>flight.job.expire_at.0{
            let done=self.in_flight.take().unwrap();
            self.math_scratch=done.prepared.into_workspace();
            self.owner.finish_parity(done.job,done.copied,false);
            self.counters.expired+=1;
            return Ok(0)
        }
        let Some((count,_))=flight.prepared.next_quantum_reuse(
            &self.rs,self.budget,BackendChoice::default(),
            &mut self.repair_scratch
        ).map_err(|_|GameError::Invalid)? else{return Ok(0)};
        for row in self.repair_scratch.iter().take(count){
            let mut typed=[0u8;2048];
            typed[0]=3;typed[1..1+row.len()].copy_from_slice(row);
            match submit(&typed[..row.len()+1]){
                Ok(id)=>{
                    flight.rows.push((id,false));
                    self.counters.parity_offered+=1
                }
                Err(_)=>{self.counters.failed+=1}
            }
        }
        Ok(count)
    }
    pub(crate) fn copied(&mut self,id:LogicalPacketId){
        let Some(flight)=self.in_flight.as_mut()else{return};
        if let Some((_,credited))=flight.rows.iter_mut()
            .find(|(row,_)|*row==id){
            if !*credited{
                *credited=true;flight.copied=flight.copied.saturating_add(1);
                self.counters.parity_kernel_copied+=1;
            }
        }
    }
    pub(crate) fn settle_when_quiet(&mut self,game_tx_empty:bool){
        if !game_tx_empty{return}
        if self.in_flight.as_ref().is_some_and(|f|
            f.prepared.remaining_rows()==0){
            let f=self.in_flight.take().unwrap();
            self.math_scratch=f.prepared.into_workspace();
            self.owner.finish_parity(f.job,f.copied,true);
        }
    }
    /// Every byte is behind the ORIGINAL Game AEAD + per-lane replay
    /// and cross-lane logical-id de-dup, never an unauthenticated FEC opener.
    pub(crate) fn receive(&mut self,data:&[u8],now:MonoNs)
        ->Result<Vec<Vec<u8>>,GameError>{
        let Some((&kind,body))=data.split_first()else{
            return Err(GameError::Invalid)
        };
        let delivered=self.rx.accept_authenticated(
            self.scope,kind,body,now).map_err(|_|GameError::Invalid)?;
        let mut out=Vec::with_capacity(delivered.len());
        for v in delivered{
            if v.frame.is_empty()||v.frame.len()>self.max_original(){
                self.counters.failed+=1;return Err(GameError::Invalid)
            }
            if v.recovered{self.counters.recovered_candidate+=1}
            else{self.counters.source_first_candidate+=1}
            out.push(v.frame);
        }
        Ok(out)
    }
    pub(crate) fn stop(&mut self){
        if let Some(f)=self.in_flight.take(){
            self.math_scratch=f.prepared.into_workspace();
            self.owner.finish_parity(f.job,f.copied,false);
        }
        for row in &mut self.repair_scratch{row.fill(0);row.clear();}
        self.math_scratch.fill(0);self.math_scratch.clear();
        self.owner.stop();self.rx.stop();self.source_arena.stop();
        self.source_arena.drain_returns();
    }
}
