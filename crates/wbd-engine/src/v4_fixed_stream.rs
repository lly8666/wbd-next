//! M0 original-owner *composition* for many FEC Fixed blocks. No credential
//! grant, AEAD, kernel-send, peer-delivery or product-mode authority lives here.
//! Only Go-verified original owner may call this after exact epoch policy.
//! Source-first callback is synchronous; deferred parity takes bounded turns.
//! Existing M1 Fec2Owner and M3 StagedParity remain the sole sources of truth.
#![forbid(unsafe_code)]
use std::ops::Range;
use crate::memory::UniqueBuffer;
use crate::runtime::fec2_owner::{
    Accepted,Fec2Owner,FecMode,FecError,Limits,ParityJob,Profile as OwnerProfile,
    OwnerReport,SourceTicket,
};
use crate::fec2_staged::StagedParity;
use wbd_codec::fec_v2::{
    BackendChoice,Profile as CodecProfile,Rs16,Error as CodecError,MAX_BATCH_ROWS
};
use wbd_types::{ConfigRevision,MonoNs};

/// This confirms an immutable ciphertext kernel-copy prefix, not delivery.
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub enum DriverProof { Copied, NotSent, Uncertain, Staged }
#[derive(Debug)]
pub enum StreamError { Stopped, StaleRevision, Busy, Invalid, Owner(FecError), Codec(CodecError) }
struct InFlight {
    job:ParityJob,
    prepared:StagedParity,
    copied:u8,
    staged:u8,
    capacity_known:bool,
}
#[derive(Clone,Copy,Debug,Default)]
pub struct InterleaveStats {
    pub paired_quanta:u64,pub alternating_rows:u64,
    pub single_quanta:u64,pub max_consecutive_same_group:u64,
    pub max_ready_age_ns:u64,
    last_block:u64,last_run:u64,
}
impl InterleaveStats {
    fn observe(&mut self,id:u64,age_ns:u64){
        self.last_run=if self.last_block==id{self.last_run+1}else{1};
        self.last_block=id;
        self.max_consecutive_same_group=self.max_consecutive_same_group.max(self.last_run);
        self.max_ready_age_ns=self.max_ready_age_ns.max(age_ns);
    }
}
// Call M4 ONLY in the post-interleave order: it allocates PN/seq and AEAD.
fn offer_repair<F>(flight:&mut InFlight,wire:&[u8],row:u8,group:u8,
    callback:&mut F,order:&mut [u8;32],length:&mut usize,
    stats:&mut InterleaveStats,now:MonoNs,copied:&mut u8)
where F:FnMut(&[u8],u64,u8,ConfigRevision)->DriverProof{
    stats.observe(flight.job.block_id,now.0.saturating_sub(flight.job.closed_at.0));
    match callback(wire,flight.job.block_id,row,flight.job.revision){
        DriverProof::Copied=>{
            flight.copied=flight.copied.saturating_add(1);
            *copied=copied.saturating_add(1);
        },
        DriverProof::NotSent=>{},
        DriverProof::Uncertain=>flight.capacity_known=false,
        DriverProof::Staged=>{
            assert!(*length<order.len(),"M4 never stages >32 rows");
            order[*length]=group;*length+=1;
            flight.staged=flight.staged.saturating_add(1);
        },
    }
}
fn encode_rows(f:&mut InFlight,rs:&Rs16,budget:usize,
    scratch:&mut [Vec<u8>;MAX_BATCH_ROWS])->Result<(usize,usize),CodecError>{
    let start=usize::from(f.job.r)-f.prepared.remaining_rows();
    let count=f.prepared.next_quantum_reuse(
        rs,budget,BackendChoice::default(),scratch)?.map_or(0,|x|x.0);
    Ok((start,count))
}
/// Exactly one original generation/direction owns one instance; no global queue.
pub struct FixedStream {
    owner:Fec2Owner,
    codec:Rs16,
    profile:CodecProfile,
    revision:ConfigRevision,
    record_payload_budget:usize,
    in_flight:Option<InFlight>,
    peer:Option<InFlight>,
    stage_order:[u8;32],stage_len:usize,
    interleave:InterleaveStats,
    // At most one prior applied revision can have bounded old parity jobs
    // draining through the same original M4 / same monotone block-id owner.
    // The new source is first-sealed immediately; only old parity rows use
    // the prior profile's codec shape, never a newly selected matrix.
    prior_profile:Option<(ConfigRevision,CodecProfile)>,
    // Bounded 4-row plaintext parity scratch, reused for every block,
    // never exposed or borrowed across the synchronous original M4 seal.
    parity_scratch:[Vec<u8>;MAX_BATCH_ROWS],
    peer_scratch:[Vec<u8>;MAX_BATCH_ROWS],
    // One bounded MAX_K*symbol_len source workspace. Recovered ONLY after
    // original M4 finishes the previous job; zeroed on Stop.
    source_scratch:Vec<u8>,
    peer_source_scratch:Vec<u8>,
    stopped:bool,
}
impl FixedStream {
    /// Caller must have validated original Go TLS principal/epoch, feature7,
    /// direction and monotone requested revision. No permission is minted here.
    pub fn new(profile:u8,revision:u64,record_payload_budget:usize)->Option<Self>{
        if revision==0||record_payload_budget<=14||record_payload_budget>65535{
            return None;
        }
        let (m1,m3)=match profile {
            0=>(OwnerProfile::Light,CodecProfile::Light),
            1=>(OwnerProfile::Mild,CodecProfile::Mild),
            2=>(OwnerProfile::Medium,CodecProfile::Medium),
            3=>(OwnerProfile::Balanced,CodecProfile::Balanced),
            4=>(OwnerProfile::High,CodecProfile::High),
            5=>(OwnerProfile::Strong,CodecProfile::Strong),
            6=>(OwnerProfile::Maximum,CodecProfile::Maximum),
            _=>return None,
        };
        let owner=Fec2Owner::new(FecMode::Normal,m1,ConfigRevision(revision),
            Limits{
                pending_bytes:2*1024*1024,
                pending_jobs:64,
                max_frame:record_payload_budget-14,
            })?;
        Some(Self{owner,codec:Rs16::new(),profile:m3,
            revision:ConfigRevision(revision),record_payload_budget,
            in_flight:None,peer:None,stage_order:[0;32],stage_len:0,
            interleave:InterleaveStats::default(),prior_profile:None,
            parity_scratch:std::array::from_fn(|_|Vec::new()),
            peer_scratch:std::array::from_fn(|_|Vec::new()),
            source_scratch:Vec::new(),peer_source_scratch:Vec::new(),
            stopped:false})
    }
    pub fn revision(&self)->ConfigRevision{self.revision}
    pub fn report(&self)->OwnerReport{self.owner.report()}
    pub fn next_deadline(&self)->Option<MonoNs>{
        if [self.in_flight.as_ref(),self.peer.as_ref()].iter().any(|x|
            x.is_some_and(|j|j.staged==0&&j.prepared.remaining_rows()>0)){
            // No new kernel borrow outstanding: schedule the next <=4
            // rows immediately without waiting for another TUN packet.
            return Some(MonoNs(0))
        }
        self.owner.next_deadline()
    }
    /// One source is handed to the original owner's AEAD+driver IMMEDIATELY.
    /// A false/not-sent callback is never counted as an accepted send;
    /// FEC storage remains charged through its original M1 slab lifetime.
    pub fn offer_source<F>(&mut self,buffer:UniqueBuffer,wire:Range<usize>,
        now:MonoNs,mut on_source:F)->Result<Accepted,(FecError,UniqueBuffer)>
    where F:FnMut(SourceTicket,&[u8])->bool{
        if self.stopped{return Err((FecError::Stopped,buffer))}
        self.owner.push_source(buffer,wire,now,|first|
            first.ticket.is_some_and(|ticket|on_source(ticket,first.frame)))
    }
    // W71 real own-60Mbps small-PPS: waiting for all three continuously
    // populated open groups to be empty can leave a genuinely REQUESTED
    // downshift PENDING forever. The M4 batch is already synchronously
    // settled at this caller's boundary. Seal old open blocks under their
    // ORIGINAL profile, retain queued old parity and unique block IDs in
    // this same owner, and immediately stage the next fresh first-send with
    // the new profile. No fake APPLIED: kernel source+repair and authentic
    // reverse M2 still gate the revision.
    pub fn quiescent_change(&mut self,profile:u8,revision:u64,now:MonoNs)
        ->Result<(),StreamError>{
        if self.stopped{return Err(StreamError::Stopped)}
        if revision<=self.revision.0{return Err(StreamError::StaleRevision)}
        // A staged/part-encoded old parity job must first be settled by
        // original M4. No early release of its slab, row or seal authority.
        if self.in_flight.is_some()||self.peer.is_some()||self.stage_len>0{
            return Err(StreamError::Busy)
        }
        if let Some((old,_))=self.prior_profile {
            if self.owner.pending_revision(old){return Err(StreamError::Busy)}
            self.prior_profile=None;
        }
        let next=Self::new(profile,revision,self.record_payload_budget)
            .ok_or(StreamError::Invalid)?;
        self.owner.change_policy(FecMode::Normal,
            match profile{
                0=>OwnerProfile::Light,1=>OwnerProfile::Mild,
                2=>OwnerProfile::Medium,3=>OwnerProfile::Balanced,
                4=>OwnerProfile::High,5=>OwnerProfile::Strong,
                6=>OwnerProfile::Maximum,_=>return Err(StreamError::Invalid),
            },ConfigRevision(revision),
            self.record_payload_budget-14,now).map_err(StreamError::Owner)?;
        self.prior_profile=Some((self.revision,self.profile));
        self.profile=next.profile;
        self.revision=ConfigRevision(revision);
        Ok(())
    }
    pub fn prior_parity_revision(&self)->Option<ConfigRevision>{
        self.prior_profile.map(|(revision,_)|revision)
    }

    fn take_job(&mut self,now:MonoNs,peer:bool)->Result<bool,StreamError>{
        let Some(mut job)=self.owner.take_parity(now)
            .map_err(StreamError::Owner)? else{return Ok(false)};
        let profile=if job.revision==self.revision{self.profile}
            else if let Some((rev,old))=self.prior_profile {
                if job.revision!=rev{
                    self.owner.finish_parity(job,0,false);
                    return Err(StreamError::Invalid)
                }
                old
            }else{
                self.owner.finish_parity(job,0,false);
                return Err(StreamError::Invalid)
            };
        let workspace=if peer{std::mem::take(&mut self.peer_source_scratch)}
            else{std::mem::take(&mut self.source_scratch)};
        let prepared=match StagedParity::from_owner_job_with_workspace(
            &mut job,profile,self.record_payload_budget,workspace){
            Ok(x)=>x,Err(e)=>{
                self.owner.finish_parity(job,0,false);
                return Err(StreamError::Codec(e))
            }
        };
        let flight=InFlight{job,prepared,copied:0,staged:0,capacity_known:true};
        if peer{self.peer=Some(flight)}else{self.in_flight=Some(flight)}
        Ok(true)
    }
    fn complete_quiescent(&mut self){
        if self.in_flight.as_ref().is_some_and(|f|
            f.staged==0&&f.prepared.remaining_rows()==0){
            let f=self.in_flight.take().unwrap();
            self.source_scratch=f.prepared.into_workspace();
            self.owner.finish_parity(f.job,f.copied,f.capacity_known);
        }
        if self.peer.as_ref().is_some_and(|f|
            f.staged==0&&f.prepared.remaining_rows()==0){
            let f=self.peer.take().unwrap();
            self.peer_source_scratch=f.prepared.into_workspace();
            self.owner.finish_parity(f.job,f.copied,f.capacity_known);
        }
        if self.in_flight.is_none()&&self.peer.is_some(){
            self.in_flight=self.peer.take();
            std::mem::swap(&mut self.parity_scratch,&mut self.peer_scratch);
            std::mem::swap(&mut self.source_scratch,&mut self.peer_source_scratch);
        }
    }
    fn expire_quiescent(&mut self,now:MonoNs){
        if self.in_flight.as_ref().is_some_and(|f|
            f.staged==0&&now.0>f.job.expire_at.0){
            let f=self.in_flight.take().unwrap();
            self.source_scratch=f.prepared.into_workspace();
            self.owner.finish_parity(f.job,f.copied,false);
        }
        if self.peer.as_ref().is_some_and(|f|
            f.staged==0&&now.0>f.job.expire_at.0){
            let f=self.peer.take().unwrap();
            self.peer_source_scratch=f.prepared.into_workspace();
            self.owner.finish_parity(f.job,f.copied,false);
        }
        self.complete_quiescent();
    }
    pub fn interleave_stats(&self)->InterleaveStats{self.interleave}
    pub fn poll_parity<F>(&mut self,now:MonoNs,on_parity:F)
        ->Result<(usize,u8),StreamError>
    where F:FnMut(&[u8],u64,u8,ConfigRevision)->DriverProof {
        self.poll_parity_quanta(now,1,on_parity)
    }
    pub fn poll_parity_quanta<F>(&mut self,now:MonoNs,max_quanta:usize,
        mut on_parity:F)->Result<(usize,u8),StreamError>
    where F:FnMut(&[u8],u64,u8,ConfigRevision)->DriverProof {
        if self.stopped{return Err(StreamError::Stopped)}
        if max_quanta>5{return Err(StreamError::Invalid)}
        self.owner.on_due(now).map_err(StreamError::Owner)?;
        if max_quanta==0{return Ok((0,0))}
        // Never encode or seal another row until original M4 settled its
        // previous immutable batch and released every ciphertext borrow.
        if self.stage_len>0{return Ok((0,0))}
        self.expire_quiescent(now);
        if self.in_flight.is_none()&&!self.take_job(now,false)?{return Ok((0,0))}
        // No wait for a peer. Old single ready group path is unchanged.
        if max_quanta>=2&&self.peer.is_none()&&self.in_flight.as_ref()
            .is_some_and(|f|f.prepared.remaining_rows()>0){
            let _=self.take_job(now,true)?;
        }
        self.expire_quiescent(now);
        let mut remaining=max_quanta;
        let mut emitted=0usize;
        let mut copied=0u8;
        while remaining>0{
            let a=self.in_flight.as_ref().is_some_and(|f|f.prepared.remaining_rows()>0);
            let b=self.peer.as_ref().is_some_and(|f|f.prepared.remaining_rows()>0);
            if !a&&!b{break}
            let pair=a&&b&&remaining>=2;
            let (start_a,n_a)=if a{
                let f=self.in_flight.as_mut().unwrap();
                match encode_rows(f,&self.codec,self.record_payload_budget,
                    &mut self.parity_scratch){
                    Ok(x)=>x,Err(e)=>{
                        if emitted==0&&f.staged==0{
                            let retired=self.in_flight.take().unwrap();
                            self.source_scratch=retired.prepared.into_workspace();
                            self.owner.finish_parity(retired.job,retired.copied,false);
                        }
                        return Err(StreamError::Codec(e))
                    }
                }
            }else{(0,0)};
            let (start_b,n_b)=if pair||(!a&&b){
                let f=self.peer.as_mut().unwrap();
                match encode_rows(f,&self.codec,self.record_payload_budget,
                    &mut self.peer_scratch){
                    Ok(x)=>x,Err(e)=>{
                        // A is already prepared, not yet staged. Send A's
                        // quantum rather than silently skipping its cursor.
                        let retired=self.peer.take().unwrap();
                        self.peer_source_scratch=retired.prepared.into_workspace();
                        self.owner.finish_parity(retired.job,retired.copied,false);
                        if n_a==0{return Err(StreamError::Codec(e))}
                        (0,0)
                    }
                }
            }else{(0,0)};
            if n_a+n_b==0{break}
            if n_a>0&&n_b>0{
                self.interleave.paired_quanta+=1;
                self.interleave.alternating_rows+=(2*n_a.min(n_b)) as u64;
            }else{self.interleave.single_quanta+=1}
            for i in 0..n_a.max(n_b){
                if i<n_a{
                    let f=self.in_flight.as_mut().unwrap();
                    offer_repair(f,&self.parity_scratch[i],(start_a+i) as u8,0,
                        &mut on_parity,&mut self.stage_order,&mut self.stage_len,
                        &mut self.interleave,now,&mut copied);
                }
                if i<n_b{
                    let f=self.peer.as_mut().unwrap();
                    offer_repair(f,&self.peer_scratch[i],(start_b+i) as u8,1,
                        &mut on_parity,&mut self.stage_order,&mut self.stage_len,
                        &mut self.interleave,now,&mut copied);
                }
            }
            emitted+=n_a+n_b;
            remaining-=usize::from(n_a>0)+usize::from(n_b>0);
        }
        self.complete_quiescent();
        Ok((emitted,copied))
    }
    /// M4 provides its genuine copied-prefix, one uncertain item and
    /// not-sent suffix. Attribute each staged parity by original A/B order.
    pub fn settle_staged(&mut self,copied:u8,not_sent:u8,uncertain:u8)
        ->Result<(),StreamError>{
        if self.stopped{return Err(StreamError::Stopped)}
        if self.stage_len==0||uncertain>1||
            usize::from(copied)+usize::from(not_sent)+usize::from(uncertain)
                !=self.stage_len{return Err(StreamError::Invalid)}
        let mut owner_counts=[0u8;2];
        for &idx in &self.stage_order[..self.stage_len]{
            if idx>1{return Err(StreamError::Invalid)}
            owner_counts[usize::from(idx)]+=1;
        }
        if self.in_flight.as_ref().is_none_or(|f|f.staged!=owner_counts[0])||
            (owner_counts[1]>0&&self.peer.is_none())||
            self.peer.as_ref().is_some_and(|f|f.staged!=owner_counts[1]){
            return Err(StreamError::Invalid)
        }
        for i in 0..self.stage_len{
            let f=if self.stage_order[i]==0{self.in_flight.as_mut().unwrap()}
                else{self.peer.as_mut().unwrap()};
            if i<usize::from(copied){f.copied=f.copied.saturating_add(1)}
            else if i==usize::from(copied)&&uncertain==1{f.capacity_known=false}
        }
        if let Some(f)=self.in_flight.as_mut(){f.staged=0}
        if let Some(f)=self.peer.as_mut(){f.staged=0}
        self.stage_len=0;
        self.complete_quiescent();
        Ok(())
    }
    /// Stop cancels owned parity and prevents all subsequent source/cipher
    /// outputs. Outer original Go/Rust generation stops its driver separately.
    pub fn stop(&mut self){
        if self.stopped{return}
        self.stopped=true;
        if let Some(flight)=self.in_flight.take(){
            self.source_scratch=flight.prepared.into_workspace();
            self.owner.finish_parity(flight.job,flight.copied,false);
        }
        if let Some(f)=self.peer.take(){
            self.peer_source_scratch=f.prepared.into_workspace();
            self.owner.finish_parity(f.job,f.copied,false);
        }
        self.stage_len=0;
        self.owner.stop();
        self.prior_profile=None;
        // Retained parity scratch may contain plaintext-derived bytes;
        // scrub once on Stop and never reuse across the stopped generation.
        for row in &mut self.parity_scratch{row.fill(0);row.clear();}
        for row in &mut self.peer_scratch{row.fill(0);row.clear();}
        self.source_scratch.fill(0);self.source_scratch.clear();
        self.peer_source_scratch.fill(0);self.peer_source_scratch.clear();
    }
}

#[cfg(test)]
mod tests{
    use super::*;
    use crate::memory::Arena;
    use wbd_types::buffer_contract::UniqueSealable;
    use wbd_codec::fec_v2::{parse_repair,Rs16};

    fn push(owner:&mut FixedStream,arena:&mut Arena,bytes:&[u8],at:u64,
        ready:&mut Vec<(u64,u8,Vec<u8>)>){
        let mut slab=arena.allocate().unwrap();
        slab.writable()[14..14+bytes.len()].copy_from_slice(bytes);
        let r=owner.offer_source(slab,14..14+bytes.len(),MonoNs(at),
            |ticket,view|{
                ready.push((ticket.block_id,ticket.index,view.to_vec()));
                true
            }).unwrap();
        assert!(r.fec_retained&&r.source_enqueued);
    }

    // Two already CLOSED classes, 4-row M3 encode per class and a single
    // original M4 copied-prefix split A/B. No fake per-job acknowledgement.
    #[test]
    fn fec_interleave_two_ready_maximum_blocks_and_m4_partial_prefix(){
        let mut arena=Arena::new(619,128,2048,128,1_000_000).unwrap();
        let mut stream=FixedStream::new(6,51,1400).unwrap();
        let mut fresh=Vec::new();
        for i in 0..16{
            push(&mut stream,&mut arena,&[i as u8;128],i,&mut fresh);
        }
        for i in 0..16{
            push(&mut stream,&mut arena,&[i as u8;440],16+i,&mut fresh);
        }
        assert_eq!(fresh.len(),32);
        assert!(fresh.iter().take(16).all(|x|x.0==1));
        assert!(fresh.iter().skip(16).all(|x|x.0==2));
        let mut order=Vec::new();
        let (n,copied)=stream.poll_parity_quanta(MonoNs(6_100_000),2,
            |wire,id,row,rev|{
                assert_eq!(rev,ConfigRevision(51));
                assert_eq!(parse_repair(wire,1400).unwrap().parity_row,row);
                order.push((id,row));
                DriverProof::Staged
            }).unwrap();
        assert_eq!((n,copied),(8,0));
        assert_eq!(order,vec![(1,0),(2,0),(1,1),(2,1),
                              (1,2),(2,2),(1,3),(2,3)]);
        let stats=stream.interleave_stats();
        assert_eq!((stats.paired_quanta,stats.alternating_rows,
            stats.max_consecutive_same_group),(1,8,1));
        assert_eq!(stream.report().classes[0].r_sent,0);
        assert_eq!(stream.report().classes[1].r_sent,0);
        assert_eq!(stream.poll_parity_quanta(MonoNs(6_100_001),2,
            |_,_,_,_|panic!("no seal while M4 borrows previous row")).unwrap(),(0,0));
        // A0,B0,A1 definitely copied; B1 outcome unknown, A2,B2,A3,B3 unsent.
        assert!(matches!(stream.settle_staged(4,1,1),Err(StreamError::Invalid)));
        stream.settle_staged(3,4,1).unwrap();
        assert_eq!(stream.report().classes[0].r_sent,0); // A still has 16 rows
        assert_eq!(stream.report().classes[1].r_sent,0);
        // New sources never wait for old parity or the next paired quantum.
        push(&mut stream,&mut arena,&[7u8;130],12_000_000,&mut fresh);
        assert_eq!(fresh.last().unwrap().0,3);
        // At the old close+10ms TTL, the remaining A/B rows must NOT be
        // emitted. Only original M4 definite prefix counts each class.
        assert_eq!(stream.poll_parity_quanta(MonoNs(16_100_001),2,
            |_,_,_,_|panic!("expired parity must never reach M4")).unwrap(),(0,0));
        assert_eq!(stream.report().classes[0].r_sent,2);
        assert_eq!(stream.report().classes[1].r_sent,1);
        stream.stop();
        assert_eq!(stream.report().charged_bytes,0);
        arena.stop();arena.drain_returns();
        assert_eq!(arena.report().loaned,0);
    }
    #[test]
    fn fec_interleave_single_fallback_stop_and_revision_busy(){
        let mut arena=Arena::new(620,96,2048,96,1_000_000).unwrap();
        let mut stream=FixedStream::new(6,60,1400).unwrap();
        let mut first=Vec::new();
        for i in 0..16{
            push(&mut stream,&mut arena,&[i as u8;128],i,&mut first);
        }
        let mut rows=Vec::new();
        let (n,copy)=stream.poll_parity_quanta(MonoNs(6_100_000),2,
            |wire,id,row,rev|{
                assert_eq!((id,rev),(1,ConfigRevision(60)));
                assert_eq!(parse_repair(wire,1400).unwrap().parity_row,row);
                rows.push(row);
                DriverProof::Staged
            }).unwrap();
        assert_eq!((n,copy),(8,0));
        assert_eq!(rows,(0..8).collect::<Vec<u8>>());
        assert_eq!(stream.interleave_stats().paired_quanta,0);
        assert!(matches!(stream.quiescent_change(5,61,MonoNs(6_100_001)),
            Err(StreamError::Busy)));
        // Stop with M4 unsettled must not claim any copied row, and must
        // release both owned source workspaces; no parity is ever retried.
        stream.stop();
        assert_eq!(stream.report().classes[0].r_sent,0);
        assert_eq!(stream.report().charged_bytes,0);
        assert!(matches!(stream.settle_staged(8,0,0),Err(StreamError::Stopped)));
        arena.stop();arena.drain_returns();
        assert_eq!(arena.report().loaned,0);
    }

    #[test]
    fn m0_fixed_stream_multiple_live_blocks_first_send_no_hol_codec_recover_stop(){
        let mut arena=Arena::new(604,24,2048,24,1_000_000).unwrap();
        let mut stream=FixedStream::new(1,9,1400).unwrap();
        let mut sources=Vec::new();
        let mut repairs:Vec<(u64,Vec<u8>)>=Vec::new();
        let a=(0..127).map(|i|i as u8).collect::<Vec<_>>();
        let b=(0..127).map(|i|(i*7%251) as u8).collect::<Vec<_>>();
        for block in 0..3 {
            let start=block*7_000_000;
            push(&mut stream,&mut arena,&a,start,&mut sources);
            push(&mut stream,&mut arena,&b,start+1,&mut sources);
            let (rows,copied)=stream.poll_parity(MonoNs(start+6_100_000),
                |row,id,index,revision|{
                    assert_eq!(revision,ConfigRevision(9));
                    assert_eq!(index,0);
                    repairs.push((id,row.to_vec()));
                    DriverProof::Copied
                }).unwrap();
            assert_eq!((rows,copied),(1,1));
            assert_eq!(stream.report().outstanding_jobs,0);
        }
        assert_eq!(sources.len(),6);
        assert_eq!(repairs.len(),3);
        for (i,(id,wire)) in repairs.iter().enumerate(){
            assert_eq!(*id,(i+1) as u64);
            assert_eq!(&sources[i*2].0,id);
            assert_eq!(sources[i*2].1,0);
            assert_eq!(sources[i*2+1].1,1);
            let reparsed=parse_repair(wire,1400).unwrap();
            let (restored,_)=Rs16::new().recover_missing(
                *id,&[Some(a.as_slice()),None],&[reparsed],1400,
                BackendChoice::Scalar
            ).unwrap();
            assert_eq!(restored[0].0,1);
            assert_eq!(restored[0].1,b);
        }
        assert_eq!(stream.report().classes[0].r_sent,3);
        assert!(matches!(stream.quiescent_change(1,9,MonoNs(22_000_000)),
            Err(StreamError::StaleRevision)));
        stream.quiescent_change(4,10,MonoNs(22_000_001)).unwrap();
        stream.stop();stream.stop();
        assert!(matches!(stream.poll_parity(MonoNs(22_100_000),|_,_,_,_|DriverProof::Copied),
            Err(StreamError::Stopped)));
        arena.stop();arena.drain_returns();
        assert_eq!(arena.report().loaned,0);
    }
    #[test]
    fn m0_fixed_stream_staged_parity_requires_genuine_m4_prefix_ack(){
        let mut arena=Arena::new(606,24,2048,24,1_000_000).unwrap();
        let mut stream=FixedStream::new(1,11,1400).unwrap();
        let mut sends=Vec::new();
        push(&mut stream,&mut arena,&[1u8;96],1,&mut sends);
        push(&mut stream,&mut arena,&[2u8;96],2,&mut sends);
        let (emitted,copied)=stream.poll_parity(MonoNs(6_100_001),
            |_,_,_,_|DriverProof::Staged).unwrap();
        assert_eq!((emitted,copied),(1,0));
        assert_eq!(stream.report().classes[0].r_sent,0);
        assert_eq!(stream.poll_parity(MonoNs(6_100_002),
            |_,_,_,_|panic!("cannot repeat staged job")).unwrap(),(0,0));
        assert!(matches!(stream.settle_staged(0,0,0),
            Err(StreamError::Invalid)));
        stream.settle_staged(1,0,0).unwrap();
        assert_eq!(stream.report().classes[0].r_sent,1);
        stream.stop();arena.stop();arena.drain_returns();
    }
    #[test]
    fn m0_fixed_stream_two_quanta_one_m4_settlement_no_reseal_no_data_hol(){
        let mut arena=Arena::new(607,48,2048,48,1_000_000).unwrap();
        let mut stream=FixedStream::new(6,21,1400).unwrap(); // Maximum k8 r10
        let mut fresh=Vec::new();
        for i in 0..8 {
            push(&mut stream,&mut arena,&[i as u8;125],i,&mut fresh);
        }
        assert_eq!(fresh.len(),8);
        let mut staged=Vec::new();
        assert!(matches!(stream.poll_parity_quanta(
            MonoNs(6_100_000),6,|_,_,_,_|DriverProof::Staged
        ),Err(StreamError::Invalid)));
        let (n,c)=stream.poll_parity_quanta(MonoNs(6_100_000),2,
            |wire,id,row,rev|{
                assert_eq!(rev,ConfigRevision(21));
                assert_eq!(id,1);
                assert_eq!(parse_repair(wire,1400).unwrap().parity_row,row);
                staged.push(row);
                DriverProof::Staged
            }).unwrap();
        assert_eq!((n,c),(8,0));
        assert_eq!(staged,(0..8).collect::<Vec<u8>>());
        assert_eq!(stream.report().classes[0].r_sent,0);
        assert_eq!(stream.poll_parity_quanta(MonoNs(6_100_001),2,
            |_,_,_,_|panic!("cannot generate rows while M4 unsettled")
        ).unwrap(),(0,0));
        // A fresh source from the next block is admitted without waiting
        // for parity kernel copy or an artificial FEC ACK.
        push(&mut stream,&mut arena,&[99u8;125],6_100_002,&mut fresh);
        assert_eq!(fresh.last().unwrap().0,2);
        assert!(matches!(stream.settle_staged(7,0,0),Err(StreamError::Invalid)));
        stream.settle_staged(8,0,0).unwrap();
        assert_eq!(stream.report().classes[0].r_sent,0); // remaining 2 rows
        let (n,c)=stream.poll_parity_quanta(MonoNs(6_100_003),2,
            |_,_,row,_|{
                assert!(row>=8 && row<10);
                DriverProof::Copied
            }).unwrap();
        assert_eq!((n,c),(2,2));
        assert_eq!(stream.report().classes[0].r_sent,10);
        assert_eq!(stream.report().outstanding_jobs,0);
        stream.stop();arena.stop();arena.drain_returns();
        assert_eq!(arena.report().loaned,0);
    }

    #[test]
    fn m0_fixed_stream_full_maximum_five_quanta_one_genuine_m4_prefix(){
        let mut arena=Arena::new(608,80,2048,80,1_000_000).unwrap();
        let mut stream=FixedStream::new(6,33,1400).unwrap();
        let mut fresh=Vec::new();
        for i in 0..16 {
            push(&mut stream,&mut arena,&[i as u8;135],i,&mut fresh);
        }
        assert_eq!(fresh.len(),16);
        let original=(0..16).map(|i|vec![i as u8;135]).collect::<Vec<_>>();
        let refs=original.iter().map(Vec::as_slice).collect::<Vec<_>>();
        let mut oracle=Vec::new();
        for first in (0..20).step_by(4){
            let (mut batch,_)=Rs16::new().encode_owned(
                1,&refs,CodecProfile::Maximum,first,4,1400,
                BackendChoice::Scalar
            ).unwrap();
            oracle.append(&mut batch);
        }
        assert_eq!(oracle.len(),20);
        // At an exhausted M4 kernel budget, time/expiry advances but no PN
        // can be allocated to unsendable parity.
        assert_eq!(stream.poll_parity_quanta(MonoNs(6_100_000),0,
            |_,_,_,_|panic!("zero slots cannot seal PN")).unwrap(),(0,0));
        let mut rows=Vec::new();
        assert_eq!(stream.poll_parity_quanta(MonoNs(6_100_001),5,
            |wire,id,row,rev|{
                assert_eq!(id,1);
                assert_eq!(rev,ConfigRevision(33));
                assert_eq!(parse_repair(wire,1400).unwrap().parity_row,row);
                assert_eq!(wire,oracle[usize::from(row)].as_slice());
                rows.push(row);
                DriverProof::Staged
            }).unwrap(),(20,0));
        assert_eq!(rows,(0u8..20u8).collect::<Vec<_>>());
        assert_eq!(stream.report().classes[0].r_sent,0);
        assert_eq!(stream.poll_parity_quanta(MonoNs(6_100_002),5,
            |_,_,_,_|panic!("must wait for M4 definite prefix")).unwrap(),(0,0));
        push(&mut stream,&mut arena,&[1u8;135],6_100_003,&mut fresh);
        assert_eq!(fresh.last().unwrap().0,2); // new M1 DATA unaffected
        assert!(matches!(stream.settle_staged(19,0,0),Err(StreamError::Invalid)));
        stream.settle_staged(20,0,0).unwrap();
        assert_eq!(stream.report().classes[0].r_sent,20);
        assert_eq!(stream.report().outstanding_jobs,0);
        assert_eq!(stream.source_scratch.len(),16*(135+2));
        let ptr=stream.source_scratch.as_ptr();
        // Second DIFFERENT full block MUST reuse the same continuous
        // source symbol allocation with exact per-block zero-tail bytes.
        let mut second=Vec::new();
        // The previous one-source open group is block 2 index0. Supply only
        // 15 more sources; the old 16-source test accidentally formed an
        // additional k1 block3, legitimately eligible as a ready peer.
        for i in 0..15{push(&mut stream,&mut arena,&[i as u8;77],7_000_000+i as u64,&mut second);}
        assert_eq!(stream.poll_parity_quanta(MonoNs(13_100_000),5,
            |wire,id,row,_|{
                assert_eq!(id,2);
                assert_eq!(parse_repair(wire,1400).unwrap().parity_row,row);
                DriverProof::Staged
            }).unwrap(),(20,0));
        stream.settle_staged(20,0,0).unwrap();
        assert_eq!(stream.source_scratch.as_ptr(),ptr);
        // Block 2 begins with the preserved 135B first-send DATA; the
        // other 15 symbols are only 77B, so its maximum remains 137B.
        assert_eq!(stream.source_scratch.len(),16*(135+2));
        stream.stop();arena.stop();arena.drain_returns();
        assert_eq!(arena.report().loaned,0);
    }

    #[test]
    fn m0_auto_w71_continuous_small_sources_quiescent_reprofile_keeps_old_parity(){
        let mut arena=Arena::new(606,64,2048,64,1_000_000).unwrap();
        let mut stream=FixedStream::new(5,1,1400).unwrap();
        let mut ready=Vec::new();
        for i in 0..6 {
            push(&mut stream,&mut arena,&[i as u8;64],i,&mut ready);
        }
        // Original M4 has settled every first-source borrow. These open
        // groups have not emptied naturally; the new request must NOT stall.
        stream.quiescent_change(0,2,MonoNs(7)).unwrap();
        assert_eq!(stream.prior_parity_revision(),Some(ConfigRevision(1)));
        push(&mut stream,&mut arena,&[99u8;64],8,&mut ready);
        assert_eq!(ready.last().unwrap().0,2); // block IDs never reset
        let mut actual=Vec::new();
        let (n,c)=stream.poll_parity_quanta(MonoNs(10),5,|wire,id,row,rev|{
            let r=parse_repair(wire,1400).unwrap();
            actual.push((id,row,rev,r.actual_k));
            DriverProof::Copied
        }).unwrap();
        assert_eq!((n,c),(6,6)); // old Strong k6 -> SIX old rows, not new Light1
        assert_eq!(actual.len(),6);
        assert!(actual.iter().all(|(id,_,rev,k)|
            *id==1 && *rev==ConfigRevision(1) && *k==6));
        let st=stream.report().classes[0];
        assert_eq!(st.accepted,7);
        assert_eq!(st.r_sent,6);
        // Once old M4 proof has drained, the next revision is again legal;
        // no stale matrices or old block identity can cross into rev3.
        stream.quiescent_change(1,3,MonoNs(11)).unwrap();
        stream.stop();arena.stop();arena.drain_returns();
        assert_eq!(arena.report().loaned,0);
    }
    #[test]
    fn m0_auto_prior_three_classes_sealed_same_owner_no_cross_revision_parity(){
        // The W75 native seamless transition must preserve ALL three source
        // classes and reject an overlapping second revision until original
        // old-parity M4 proof has settled. No extra sender, synthetic ACK
        // or block-id reset is permitted.
        let mut arena=Arena::new(607,96,2048,96,1_000_000).unwrap();
        let mut stream=FixedStream::new(5,10,1400).unwrap();
        let mut sources=Vec::new();
        for (i,n) in [65usize,300,1100].into_iter().enumerate(){
            push(&mut stream,&mut arena,&vec![i as u8;n],i as u64,&mut sources);
        }
        assert_eq!(sources.iter().map(|v|v.0).collect::<Vec<_>>(),vec![1,2,3]);
        // Genuine M4 kernel batches for old sources have settled, but
        // nonempty open groups remain at the control revision boundary.
        stream.quiescent_change(2,11,MonoNs(4)).unwrap();
        assert_eq!(stream.prior_parity_revision(),Some(ConfigRevision(10)));
        assert!(matches!(stream.quiescent_change(1,12,MonoNs(5)),
            Err(StreamError::Busy)));
        push(&mut stream,&mut arena,&[99u8;65],6,&mut sources);
        assert_eq!(sources.last().unwrap().0,4);
        // Each old class keeps STRONG original matrix and actual-k, even
        // though new systematic source id4 already uses rev11 Medium.
        let mut old=Vec::new();
        for now in 7..10u64{
            let (rows,copied)=stream.poll_parity(MonoNs(now),
                |wire,id,row,revision|{
                    let parsed=parse_repair(wire,1400).unwrap();
                    old.push((id,row,revision,parsed.actual_k));
                    DriverProof::Copied
                }).unwrap();
            assert_eq!((rows,copied),(1,1));
        }
        assert_eq!(old.len(),3);
        assert_eq!(old.iter().map(|v|v.0).collect::<Vec<_>>(),vec![1,2,3]);
        assert!(old.iter().all(|(_,row,rev,k)|
            *row==0&&*rev==ConfigRevision(10)&&*k==1));
        // Once old same-owner parity drained, another revision may seal
        // the newly open class; no prior job can cross the revision fence.
        stream.quiescent_change(1,12,MonoNs(10)).unwrap();
        let mut new_parity=Vec::new();
        assert_eq!(stream.poll_parity(MonoNs(11),|wire,id,row,rev|{
            let parsed=parse_repair(wire,1400).unwrap();
            new_parity.push((id,row,rev,parsed.actual_k));
            DriverProof::Copied
        }).unwrap(),(1,1));
        assert_eq!(new_parity,vec![(4,0,ConfigRevision(11),1)]);
        push(&mut stream,&mut arena,&[77u8;65],12,&mut sources);
        assert_eq!(sources.last().unwrap().0,5);
        stream.stop();stream.stop();
        arena.stop();arena.drain_returns();
        assert_eq!(arena.report().loaned,0);
    }
    #[test]
    fn m0_fixed_stream_eight_repair_rows_bounded_quantum_and_pressure_no_hol(){
        let mut arena=Arena::new(605,32,2048,32,1_000_000).unwrap();
        let mut stream=FixedStream::new(5,1,1400).unwrap(); // Strong k8 r8
        let mut ready=Vec::new();
        for i in 0..8{
            push(&mut stream,&mut arena,&[i as u8;120],i,&mut ready);
        }
        assert_eq!(ready.len(),8);
        let mut rows=Vec::new();
        let (n,c)=stream.poll_parity(MonoNs(6_100_000),|_,id,row,revision|{
            assert_eq!(id,1);assert_eq!(revision,ConfigRevision(1));
            rows.push(row);
            if row==1{DriverProof::Uncertain}else{DriverProof::Copied}
        }).unwrap();
        assert_eq!((n,c),(4,3));
        // Old parity job cannot block fresh M1 source callback.
        push(&mut stream,&mut arena,&[55u8;100],6_100_010,&mut ready);
        assert_eq!(ready.last().unwrap().0,2);
        assert!(matches!(stream.quiescent_change(4,2,MonoNs(6_100_011)),
            Err(StreamError::Busy)));
        let (n,c)=stream.poll_parity(MonoNs(6_100_020),|_,id,row,_|{
            assert_eq!(id,1);
            rows.push(row);
            DriverProof::Copied
        }).unwrap();
        assert_eq!((n,c),(4,4));
        assert_eq!(rows,(0u8..8u8).collect::<Vec<_>>());
        assert_eq!(stream.report().classes[0].r_sent,7);
        stream.stop();
        assert_eq!(stream.report().charged_bytes,0);
        arena.stop();arena.drain_returns();
        assert_eq!(arena.report().loaned,0);
    }
}
