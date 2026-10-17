//! Bounded genuine FEC TX owner: systematic on admission, parity separately.
//! Original Go 20:R wire and 32ms first-source deadline. No fake parity,
//! background tasks, SIMD claim, or guarantee of driver-send success.
#![forbid(unsafe_code)]
use std::collections::VecDeque;
use crate::fec_math::{FecMathError,ReedSolomon20,FecBackendChoice,FecBackendUsed};
use crate::link_fec_wire::{FEC_DATA_SHARDS,FEC_HEADER,FEC_PARITY_PROFILES};

pub const FLUSH_MS:u64=32;
pub const MAX_CLASSES:usize=3;
pub const MAX_RETAINED:usize=MAX_CLASSES*FEC_DATA_SHARDS*65535;
/// Independent metadata ceiling even when closed blocks contain 1-byte shards.
pub const MAX_COOPERATIVE_PARITY_JOBS:usize=64;
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub enum TxError {InvalidBudget,InvalidSource,UnsupportedProfile,IdExhausted,Backpressure,Math(FecMathError)}
impl From<FecMathError> for TxError {fn from(e:FecMathError)->Self{Self::Math(e)}}
#[derive(Default,Debug,PartialEq,Eq)]
pub struct TxBatch {pub systematic:Vec<Vec<u8>>,pub parity:Vec<Vec<u8>>}
/// Maximum first-send parity frames a scheduler may take from this batch
/// without another fresh-systematic/driver servicing opportunity. This is
/// only a ready-output API: encoding CPU time remains separate and UNMEASURED.
pub const MAX_PARITY_FIRST_SEND_ROWS_PER_TURN:usize=4;
impl TxBatch{
    /// Drain one bounded unit of parity that has NOT been sent before.
    /// Its caller must put these frames in the fresh-FEC lane, never charge
    /// them to the outer repair 10% retransmission allowance. The caller
    /// owns scheduling/bytes/queue-age; no timer/thread is started here.
    pub fn take_ready_parity_chunk(&mut self)->Vec<Vec<u8>>{
        let n=self.parity.len().min(MAX_PARITY_FIRST_SEND_ROWS_PER_TURN);
        self.parity.drain(..n).collect()
    }
    pub fn parity_pending(&self)->usize{self.parity.len()}
}
/// An owned, self-contained closed-block parity job. Sources are moved into
/// this job once (no extra 64KiB copy); a caller MUST keep its total pending
/// jobs within its shared payload budget. One call computes <=4 REAL RS rows,
/// not merely drains a previously encoded batch. Completion is monotone and
/// exactly-once. The owner still must dispatch output as FRESH parity.
pub struct FecParityJob{
    block_id:u32,profile:u8,wire_limit:usize,
    parts:Vec<Vec<u8>>,next_row:usize,rows:usize,held_bytes:usize,
}
impl FecParityJob{
    pub fn new(block_id:u32,parts:Vec<Vec<u8>>,profile:u8,
        wire_limit:usize)->Result<Self,TxError>{
        if block_id==0{return Err(TxError::IdExhausted);}
        if !FEC_PARITY_PROFILES.contains(&profile){return Err(TxError::UnsupportedProfile);}
        if wire_limit<=FEC_HEADER||wire_limit>FEC_HEADER+65535{
            return Err(TxError::InvalidBudget);
        }
        if parts.is_empty()||parts.len()>FEC_DATA_SHARDS||
            parts.iter().any(|p|p.is_empty()||p.len()>wire_limit-FEC_HEADER){
            return Err(TxError::InvalidSource);
        }
        let rows=parts.len().min(usize::from(profile));
        let held_bytes=parts.iter().map(Vec::len).sum();
        Ok(Self{block_id,profile,wire_limit,parts,next_row:0,rows,held_bytes})
    }
    pub fn pending_rows(&self)->usize{self.rows-self.next_row}
    pub fn retained_bytes(&self)->usize{self.held_bytes}
    pub fn is_done(&self)->bool{self.next_row==self.rows}
    pub fn first_parity_index(&self)->u8{(FEC_DATA_SHARDS+self.next_row) as u8}
    /// No timeout, block or thread creation; caller owns fairness.
    /// On error, progress is unchanged and no partially issued rows escape.
    pub fn take_next_rows(&mut self,codec:&ReedSolomon20)
        ->Result<Vec<Vec<u8>>,TxError>{
        Ok(self.take_next_rows_selected(codec,FecBackendChoice::Scalar)?.0)
    }
    /// Opt-in native GF rows: an error does not consume this job or publish
    /// incomplete parity; the Used value is based on an actual backend call.
    pub fn take_next_rows_selected(&mut self,codec:&ReedSolomon20,
        choice:FecBackendChoice)->Result<(Vec<Vec<u8>>,FecBackendUsed),TxError>{
        let count=self.pending_rows().min(MAX_PARITY_FIRST_SEND_ROWS_PER_TURN);
        if count==0{return Ok((Vec::new(),FecBackendUsed::Scalar));}
        let inputs=self.parts.iter().map(Vec::as_slice).collect::<Vec<_>>();
        let (wires,used)=codec.final_parity_wires_range_selected(self.block_id,&inputs,
            self.profile,self.wire_limit,self.next_row,count,choice)?;
        self.next_row+=wires.len();
        if self.is_done(){
            self.parts.clear();
            self.held_bytes=0;
        }
        Ok((wires,used))
    }
}

#[derive(Clone,Copy,Default,Debug,Eq,PartialEq)]
pub struct TxStats {
    pub source_shards:u64,pub parity_shards:u64,pub full_blocks:u64,pub partial_blocks:u64,
    pub pressure_closes:u64,pub reconfig_closes:u64,
    pub pending_blocks:usize,pub pending_sources:usize,pub retained_bytes:usize,
    pub class_count:usize,pub pending_parity_jobs:usize,pub pending_parity_rows:usize,
    pub pending_parity_source_bytes:usize,pub backpressure_rejections:u64,
    pub closed_by_k:[u64;21],pub closed_by_r:[u64;21],
    pub closed_by_class_k:[[u64;21];MAX_CLASSES],
}
struct Block {id:u64,first_ms:u64,profile:u8,wire_limit:usize,parts:Vec<Vec<u8>>,bytes:usize}
pub struct FecTxOwner {
    codec:ReedSolomon20,next_id:u64,groups:[Option<Block>;MAX_CLASSES],
    profile:Option<u8>,wire_limit:Option<usize>,
    budget:usize,held:usize,clock_ms:u64,stats:TxStats,
    cooperative:bool,pending_jobs:VecDeque<FecParityJob>,pending_bytes:usize,
    backend:FecBackendChoice,last_backend:Option<FecBackendUsed>,
}
impl FecTxOwner {
    pub fn new(first_id:u64,budget:usize)->Result<Self,TxError>{
        if first_id==0||first_id as u32==0||budget==0||budget>MAX_RETAINED{
            return Err(TxError::InvalidBudget);
        }
        Ok(Self{codec:ReedSolomon20::new()?,next_id:first_id,
            groups:std::array::from_fn(|_|None),profile:None,wire_limit:None,
            budget,held:0,clock_ms:0,stats:TxStats::default(),
            cooperative:false,pending_jobs:VecDeque::new(),pending_bytes:0,
            backend:FecBackendChoice::Scalar,last_backend:None})
    }
    /// Opt-in owner mode. Closed blocks become bounded owned parity jobs;
    /// existing new()/submit()/flush behaviour remains synchronous.
    /// The caller must poll and dispatch parity before retrying Backpressure.
    pub fn new_cooperative(first_id:u64,budget:usize)->Result<Self,TxError>{
        let mut owner=Self::new(first_id,budget)?;
        owner.cooperative=true;
        Ok(owner)
    }
    /// Explicit opt-in backend for the existing bounded cooperative owner.
    /// Default new()/new_cooperative() remain scalar and wire-compatible.
    pub fn new_cooperative_with_backend(first_id:u64,budget:usize,
        backend:FecBackendChoice)->Result<Self,TxError>{
        let mut owner=Self::new_cooperative(first_id,budget)?;
        owner.backend=backend;
        Ok(owner)
    }
    pub fn last_parity_backend(&self)->Option<FecBackendUsed>{self.last_backend}
    /// Run one real-GF cooperative parity quantum (at most four rows).
    /// Returned wires belong to the fresh-FEC send lane, NOT repair/RTX.
    /// Their downstream ownership and send-queue memory are external.
    pub fn poll_cooperative_parity(&mut self)->Result<TxBatch,TxError>{
        if !self.cooperative{return Err(TxError::InvalidBudget);}
        let Some(front)=self.pending_jobs.front_mut()else{return Ok(TxBatch::default());};
        let held=front.retained_bytes();
        let (parity,used)=front.take_next_rows_selected(&self.codec,self.backend)?;
        let done=front.is_done();
        self.last_backend=Some(used);
        self.stats.parity_shards+=parity.len() as u64;
        if done{
            self.pending_bytes-=held;
            self.pending_jobs.pop_front();
        }
        Ok(TxBatch{systematic:Vec::new(),parity})
    }
    fn clock(&mut self,now:u64)->u64{self.clock_ms=self.clock_ms.max(now);self.clock_ms}
    pub fn next_block_id_ext(&self)->u64{self.next_id}
    pub fn next_deadline_ms(&self)->Option<u64>{
        self.groups.iter().flatten().map(|b|b.first_ms.saturating_add(FLUSH_MS)).min()
    }
    pub fn stats(&self)->TxStats{
        let mut s=self.stats;
        s.pending_blocks=self.groups.iter().flatten().count();
        s.pending_sources=self.groups.iter().flatten().map(|b|b.parts.len()).sum();
        s.retained_bytes=self.held+self.pending_bytes;
        s.pending_parity_jobs=self.pending_jobs.len();
        s.pending_parity_rows=self.pending_jobs.iter().map(FecParityJob::pending_rows).sum();
        s.pending_parity_source_bytes=self.pending_bytes;
        s.class_count=self.profile.zip(self.wire_limit)
            .map(|(p,w)|Self::classes(p,w)).unwrap_or(0);
        s
    }
    fn classes(profile:u8,limit:usize)->usize{
        let size=limit-FEC_HEADER;
        if profile!=20||size<=256{1}else if size<=512{2}else{3}
    }
    fn class(profile:u8,limit:usize,len:usize,large_fragment:bool)->usize{
        let n=Self::classes(profile,limit);
        if large_fragment{return n-1;}
        if n==1||len<=256{0}else if len<=512&&n==3{1}else{n-1}
    }
    fn preflight(source:&[u8],profile:u8,limit:usize,budget:usize)->Result<(),TxError>{
        if !FEC_PARITY_PROFILES.contains(&profile){return Err(TxError::UnsupportedProfile);}
        if limit<=FEC_HEADER||limit>FEC_HEADER+65535{return Err(TxError::InvalidBudget);}
        if source.is_empty()||source.len()>limit-FEC_HEADER||source.len()>budget{
            return Err(TxError::InvalidSource);
        }
        Ok(())
    }
    // At the terminal u64 boundary even an otherwise legal wire ID cannot
    // be reserved: reserve_id must be able to advance past it. Predict this
    // BEFORE closing old blocks, since a later Err would discard the parity
    // already collected in submit's local TxBatch.
    fn can_reserve_id(&self)->bool{
        let id=self.next_id;
        id!=0 && id as u32!=0 && id.checked_add(1).is_some_and(|next|
            next as u32!=0 || next.checked_add(1).is_some())
    }
    fn reserve_id(&mut self)->Result<u64,TxError>{
        let id=self.next_id;
        if id==0||id as u32==0{return Err(TxError::IdExhausted);}
        let next=id.checked_add(1).ok_or(TxError::IdExhausted)?;
        self.next_id=if next as u32==0{
            next.checked_add(1).ok_or(TxError::IdExhausted)?
        }else{next};
        Ok(id)
    }
    fn close(&mut self,i:usize,batch:&mut TxBatch)->Result<(),TxError>{
        let Some(block)=self.groups[i].as_ref()else{return Ok(());};
        if self.cooperative && self.pending_jobs.len()>=MAX_COOPERATIVE_PARITY_JOBS{
            return Err(TxError::Backpressure);
        }
        let (k,r,bytes);
        if self.cooperative{
            // Transfer the source Vecs without copying or doing GF encoding.
            // An error cannot occur after this point: each admitted shard
            // has already passed FEC profile/wire/source validation.
            let block=self.groups[i].take().expect("present");
            k=block.parts.len();r=k.min(usize::from(block.profile));bytes=block.bytes;
            let job=FecParityJob::new(block.id as u32,block.parts,block.profile,block.wire_limit)
                .expect("admitted FEC block meets cooperative job invariants");
            self.held-=bytes;self.pending_bytes+=bytes;
            self.pending_jobs.push_back(job);
        }else{
            let shards=block.parts.iter().map(Vec::as_slice).collect::<Vec<_>>();
            let parity=self.codec.final_parity_wires(
                block.id as u32,&shards,block.profile,block.wire_limit)?;
            (k,r,bytes)=(block.parts.len(),parity.len(),block.bytes);
            batch.parity.extend(parity);
            self.groups[i]=None;
            self.held-=bytes;
            self.stats.parity_shards+=r as u64;
        }
        self.stats.closed_by_k[k]+=1;
        self.stats.closed_by_r[r]+=1;
        self.stats.closed_by_class_k[i][k]+=1;
        if k==FEC_DATA_SHARDS{self.stats.full_blocks+=1;}
        else{self.stats.partial_blocks+=1;}
        Ok(())
    }
    fn oldest(&self)->Option<usize>{
        self.groups.iter().enumerate().filter_map(|(i,b)|b.as_ref()
            .map(|b|((b.first_ms,b.id),i))).min_by_key(|(order,_)|*order)
            .map(|(_,i)|i)
    }
    pub fn flush_due(&mut self,now_ms:u64)->Result<TxBatch,TxError>{
        let now=self.clock(now_ms);
        let mut due=self.groups.iter().enumerate().filter_map(|(i,b)|{
            let b=b.as_ref()?;
            (now>=b.first_ms.saturating_add(FLUSH_MS))
                .then_some(((b.first_ms,b.id),i))
        }).collect::<Vec<_>>();
        due.sort_by_key(|(order,_)|*order);
        let mut out=TxBatch::default();
        for (_,i) in due{self.close(i,&mut out)?;}
        Ok(out)
    }
    pub fn flush_all(&mut self,now_ms:u64)->Result<TxBatch,TxError>{
        self.clock(now_ms);
        let mut out=TxBatch::default();
        while let Some(i)=self.oldest(){self.close(i,&mut out)?;}
        Ok(out)
    }
    /// All already-ready systematic go to the separate source queue.
    /// Caller must schedule systematic before this batch's parity jobs.
    pub fn submit(&mut self,source:&[u8],now_ms:u64,profile:u8,
        wire_limit:usize,large_fragment_hint:bool)->Result<TxBatch,TxError>{
        Self::preflight(source,profile,wire_limit,self.budget)?;
        if self.cooperative {
            // All unencoded closed blocks remain charged until their final
            // parity row has been computed; never discard parity silently.
            // On pressure, close one old open block (if possible) so the
            // scheduler can poll a job. The rejected source was NOT admitted
            // and must be retried by the caller after servicing parity.
            if self.held.saturating_add(self.pending_bytes)
                .saturating_add(source.len())>self.budget{
                if let Some(i)=self.oldest(){
                    self.close(i,&mut TxBatch::default())?;
                    self.stats.pressure_closes+=1;
                }
                self.stats.backpressure_rejections+=1;
                return Err(TxError::Backpressure);
            }
            // Do not accept the final 20th source if a full job queue would
            // make its mandatory close return an error *after* accepting it.
            let class=Self::class(profile,wire_limit,source.len(),large_fragment_hint);
            if self.pending_jobs.len()>=MAX_COOPERATIVE_PARITY_JOBS
                && self.groups[class].as_ref().is_some_and(|b|
                    b.profile==profile&&b.wire_limit==wire_limit
                    && b.parts.len()==FEC_DATA_SHARDS-1) {
                self.stats.backpressure_rejections+=1;
                return Err(TxError::Backpressure);
            }
        }
        // Reject terminal BlockID exhaustion before flush_due/reconfiguration
        // can generate parity that would otherwise be lost with this Err.
        // A still-open compatible block may accept more sources without a new
        // ID. At the terminal boundary, fail closed on synchronous pressure:
        // it might close that block before the next admission.
        let now=self.clock_ms.max(now_ms);
        let class=Self::class(profile,wire_limit,source.len(),large_fragment_hint);
        let open_compatible=self.groups[class].as_ref().is_some_and(|b|
            b.profile==profile && b.wire_limit==wire_limit &&
            now<b.first_ms.saturating_add(FLUSH_MS));
        let pressure_may_close=!self.cooperative &&
            self.held.saturating_add(self.pending_bytes)
                .saturating_add(source.len())>self.budget;
        if !self.can_reserve_id() && (!open_compatible || pressure_may_close){
            return Err(TxError::IdExhausted);
        }
        let now=self.clock(now_ms);
        let mut out=self.flush_due(now)?;
        if self.profile!=Some(profile)||self.wire_limit!=Some(wire_limit){
            while let Some(i)=self.oldest(){
                self.close(i,&mut out)?;
                self.stats.reconfig_closes+=1;
            }
            self.profile=Some(profile);self.wire_limit=Some(wire_limit);
        }
        let class=Self::class(profile,wire_limit,source.len(),large_fragment_hint);
        while self.held+self.pending_bytes+source.len()>self.budget{
            let i=self.oldest().ok_or(TxError::InvalidBudget)?;
            self.close(i,&mut out)?;self.stats.pressure_closes+=1;
        }
        if self.groups[class].is_none(){
            let id=self.reserve_id()?;
            self.groups[class]=Some(Block{id,first_ms:now,profile,wire_limit,
                parts:Vec::with_capacity(FEC_DATA_SHARDS),bytes:0});
        }
        let block=self.groups[class].as_ref().expect("reserved");
        let wire=self.codec.streaming_wire(
            block.id as u32,block.parts.len(),source,profile,wire_limit)?;
        let block=self.groups[class].as_mut().expect("reserved");
        block.parts.push(source.to_vec());
        block.bytes+=source.len();
        self.held+=source.len();self.stats.source_shards+=1;
        out.systematic.push(wire);
        if block.parts.len()==FEC_DATA_SHARDS{
            self.close(class,&mut out)?;
        }
        Ok(out)
    }
}
