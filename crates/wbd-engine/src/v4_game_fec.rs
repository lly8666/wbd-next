//! Authenticated Game2/4 fixed-FEC inner-symbol composition.
//! Original Game per-lane AEAD/PN and logical de-dup happen BEFORE M3 recovery.
//! Game+FEC is explicitly configured on both endpoints; no silent downgrade.
#![forbid(unsafe_code)]
use crate::memory::Arena;
use crate::runtime::fec2_owner::{
    Fec2Owner,FecMode,Profile as OwnerProfile,Limits,ParityJob,OwnerReport
};
use crate::fec2_staged::StagedParity;
use crate::v4_fec2_live_rx::{Fec2LiveRx,VerifiedReceiveEpoch,ReceiveError};
use crate::v4_game_lane::Error as GameError;
use wbd_codec::fec_v2::{self,Profile as CodecProfile,Rs16,BackendChoice,MAX_BATCH_ROWS};
use wbd_types::{ConfigRevision,MonoNs,LogicalPacketId};
use wbd_types::buffer_contract::UniqueSealable;

#[derive(Clone,Copy,Debug,Default)]
pub(crate) struct GameFecCounters{
    pub source_offered:u64,pub parity_offered:u64,
    pub parity_kernel_copied:u64,pub recovered_candidate:u64,
    pub source_first_candidate:u64,pub expired:u64,pub failed:u64,
    // RX FEC decoder error classes are AFTER original lane AEAD/PN and
    // MUST NOT be conflated with a cryptographic tag failure.
    pub rx_invalid:u64,pub rx_conflict:u64,pub rx_capacity:u64,
    pub rx_codec:u64,pub rx_state:u64,pub rx_frame:u64,
}
struct Flight{
    job:ParityJob,prepared:StagedParity,copied:u8,
    rows:Vec<(LogicalPacketId,bool)>,
}
pub(crate) struct GameFecTx{
    owner:Fec2Owner,
    rs:Rs16,profile:CodecProfile,math_scratch:Vec<u8>,
    repair_scratch:[Vec<u8>;MAX_BATCH_ROWS],
    source_arena:Arena,in_flight:Option<Flight>,
    budget:usize,lanes:usize,counters:GameFecCounters,
}
impl GameFecTx{
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
        let source_arena=Arena::new(
            scope.generation^0x4700_0000,128,2048,128,512*1024).ok()?;
        Some(Self{owner,rs:Rs16::new(),profile:codec_profile,
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
    /// Earliest work that can wake the existing Game M4 TX owner. Sparse
    /// source groups close on the REAL FEC deadline, not the later Game4
    /// 20/60ms copy due. Ready queued parity or the next settled SIMD quantum
    /// must not sleep; an uncredited in-flight row waits only until expiry.
    /// No per-packet timer or new source-group ownership is created.
    pub(crate) fn next_due_ns(&self,now:MonoNs)->Option<u64>{
        if self.in_flight.is_none() && self.owner.has_ready_parity(){
            return Some(now.0)
        }
        let mut earliest=self.owner.next_deadline().map(|at|at.0);
        if let Some(f)=self.in_flight.as_ref(){
            if f.prepared.remaining_rows()>0 &&
                (f.rows.is_empty() || f.rows.iter().all(|(_,ok)|*ok)){
                return Some(now.0)
            }
            let expiry=f.job.expire_at.0.saturating_add(1);
            earliest=Some(earliest.map_or(expiry,|at|at.min(expiry)));
        }
        earliest
    }

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
        _game_tx_empty:bool,mut submit:F)->Result<usize,GameError>
    where F:FnMut(&[u8])->Result<LogicalPacketId,GameError>{
        self.owner.on_due(now).map_err(|_|GameError::Invalid)?;
        // GameTx owns its immutable encrypted-symbol input after submit()
        // (unique slab, never borrowing the FEC encoding workspace). Waiting
        // for the entire 60ms stagger queue to go empty would starve parity
        // production under constant business load. Only the actual native
        // acknowledgement of THIS parity quantum matters for advancing it.
        // Uncredited rows have a strict owner expiry; never wait forever.
        if let Some(f)=self.in_flight.as_ref(){
            if !f.rows.is_empty(){
                if f.rows.iter().all(|(_,credited)|*credited){
                    self.in_flight.as_mut().unwrap().rows.clear();
                }else if now.0<=f.job.expire_at.0{
                    return Ok(0)
                }
            }
        }
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
        // Every source/future-copy calls copied() after a genuine M4
        // send. Parity rows are assigned monotonically increasing logical
        // IDs; most source packets belong OUTSIDE the tiny in-flight parity
        // interval. Reject them in O(1), rather than scanning up to 20 rows
        // on each of four physical Game4 lane copies.
        let Some((low,_))=flight.rows.first()else{return};
        let Some((high,_))=flight.rows.last()else{return};
        if id.0<low.0||id.0>high.0{return}
        if let Some((_,credited))=flight.rows.iter_mut()
            .find(|(row,_)|*row==id){
            if !*credited{
                *credited=true;flight.copied=flight.copied.saturating_add(1);
                self.counters.parity_kernel_copied+=1;
            }
        }
    }
    pub(crate) fn settle_when_quiet(&mut self,game_tx_empty:bool){
        if let Some(f)=self.in_flight.as_mut(){
            // Delayed GameTx copies own independent slabs: the FEC encoder
            // can complete when each parity row was credited by >=1 lane.
            // If the whole TX is empty with uncredited rows, those copies
            // have been locally dropped and the owner must still retire.
            if f.rows.iter().all(|(_,credited)|*credited)||game_tx_empty{
                f.rows.clear();
            }
        }
        if self.in_flight.as_ref().is_some_and(|f|
            f.rows.is_empty()&&f.prepared.remaining_rows()==0){
            let f=self.in_flight.take().unwrap();
            self.math_scratch=f.prepared.into_workspace();
            self.owner.finish_parity(f.job,f.copied,true);
        }
    }
    pub(crate) fn stop(&mut self){
        if let Some(f)=self.in_flight.take(){
            self.math_scratch=f.prepared.into_workspace();
            self.owner.finish_parity(f.job,f.copied,false);
        }
        for row in &mut self.repair_scratch{row.fill(0);row.clear();}
        self.math_scratch.fill(0);self.math_scratch.clear();
        self.owner.stop();self.source_arena.stop();
        self.source_arena.drain_returns();
    }
}

/// Original per-lane authenticators are owned by GameReceiveOwner. The
/// decoder is ONE shared logical RX for all lanes, never an extra key opener.
pub(crate) struct GameFecRx{
    rx:Fec2LiveRx,scope:VerifiedReceiveEpoch,budget:usize,
    counters:GameFecCounters,
}
impl GameFecRx{
    pub(crate) fn new(profile:u8,scope:VerifiedReceiveEpoch,inner_mtu:usize)
        ->Option<Self>{
        if profile>6||inner_mtu<=32{return None}
        let budget=inner_mtu.checked_sub(1)?;
        let rx=Fec2LiveRx::from_authenticated_scope(scope,budget+31).ok()?;
        Some(Self{rx,scope,budget,counters:GameFecCounters::default()})
    }
    pub(crate) fn counters(&self)->GameFecCounters{self.counters}
    pub(crate) fn receive(&mut self,data:&[u8],now:MonoNs)
        ->Result<Vec<Vec<u8>>,GameError>{
        let Some((&kind,body))=data.split_first() else{
            self.counters.failed+=1;
            self.counters.rx_frame+=1;
            return Err(GameError::Invalid)
        };
        // FEC source(2)/parity(3) is already behind lane-specific AEAD+replay
        // and one shared authenticated cross-lane Game logical ID precheck.
        let delivered=self.rx.accept_authenticated(self.scope,kind,body,now)
            .map_err(|reason|{
                self.counters.failed+=1;
                match reason{
                    ReceiveError::Invalid=>self.counters.rx_invalid+=1,
                    ReceiveError::ConflictingBlock=>self.counters.rx_conflict+=1,
                    ReceiveError::Capacity=>self.counters.rx_capacity+=1,
                    ReceiveError::Codec=>self.counters.rx_codec+=1,
                    ReceiveError::Authorization|ReceiveError::Stopped|
                    ReceiveError::ReplayOrAuthentication=>self.counters.rx_state+=1,
                }
                GameError::Invalid
            })?;
        let mut out=Vec::with_capacity(delivered.len());
        for value in delivered{
            if value.frame.is_empty()||value.frame.len()>self.budget-14{
                self.counters.failed+=1;
                self.counters.rx_frame+=1;
                return Err(GameError::Invalid)
            }
            if value.recovered{
                self.counters.recovered_candidate+=1
            }else{
                self.counters.source_first_candidate+=1
            }
            out.push(value.frame)
        }
        Ok(out)
    }
    #[cfg(test)]
    fn w101_original_game_fec_decoder_rejections_have_separate_causes(){
        let epoch=VerifiedReceiveEpoch{
            generation:7,epoch:[7;16],negotiated_features:7,
            direction_s2c:true
        };
        let mut fec=GameFecRx::new(6,epoch,1353).unwrap();
        assert!(fec.receive(&[],MonoNs(0)).is_err());
        assert!(fec.receive(&[0xff,1,2],MonoNs(1)).is_err());
        let c=fec.counters();
        assert_eq!(c.failed,2);
        assert_eq!(c.rx_frame,1);
        assert_eq!(c.rx_invalid,1);
        assert_eq!(c.rx_conflict,0);
        assert_eq!(c.rx_capacity,0);
        assert_eq!(c.rx_codec,0);
        assert_eq!(c.rx_state,0);
        fec.stop();
    }
    pub(crate) fn stop(&mut self){self.rx.stop();}
}

#[cfg(test)]
#[test]
fn w101_original_game_fec_decoder_rejections_have_separate_causes(){
    // Rust #[test] must be free-standing, never an associated impl fn.
    GameFecRx::w101_original_game_fec_decoder_rejections_have_separate_causes();
}
