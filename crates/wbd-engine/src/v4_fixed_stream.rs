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
use wbd_codec::fec_v2::{BackendChoice,Profile as CodecProfile,Rs16,Error as CodecError};
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
/// Exactly one original generation/direction owns one instance; no global queue.
pub struct FixedStream {
    owner:Fec2Owner,
    codec:Rs16,
    profile:CodecProfile,
    revision:ConfigRevision,
    record_payload_budget:usize,
    in_flight:Option<InFlight>,
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
            in_flight:None,stopped:false})
    }
    pub fn revision(&self)->ConfigRevision{self.revision}
    pub fn report(&self)->OwnerReport{self.owner.report()}
    pub fn next_deadline(&self)->Option<MonoNs>{
        if self.in_flight.as_ref().is_some_and(|j|
            j.staged==0&&j.prepared.remaining_rows()>0){
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
    /// Change to a newer Go-authenticated policy ONLY at a quiescent owner
    /// boundary; no old block may use a new matrix profile/revision.
    pub fn quiescent_change(&mut self,profile:u8,revision:u64,now:MonoNs)
        ->Result<(),StreamError>{
        if self.stopped{return Err(StreamError::Stopped)}
        if revision<=self.revision.0{return Err(StreamError::StaleRevision)}
        let r=self.owner.report();
        if self.in_flight.is_some()||r.open_bytes!=0||
            r.outstanding_jobs!=0||r.queued_jobs!=0{
            return Err(StreamError::Busy)
        }
        let next=Self::new(profile,revision,self.record_payload_budget)
            .ok_or(StreamError::Invalid)?;
        // No pending original slabs or cipher loans may exist in this
        // owned queue at a mode boundary; old M1 owner drains at Stop.
        self.owner.change_policy(FecMode::Normal,
            match profile{
                0=>OwnerProfile::Light,1=>OwnerProfile::Mild,
                2=>OwnerProfile::Medium,3=>OwnerProfile::Balanced,
                4=>OwnerProfile::High,5=>OwnerProfile::Strong,
                6=>OwnerProfile::Maximum,_=>return Err(StreamError::Invalid),
            },ConfigRevision(revision),
            self.record_payload_budget-14,now).map_err(StreamError::Owner)?;
        self.profile=next.profile;
        self.revision=ConfigRevision(revision);
        Ok(())
    }
    /// At most one four-row M3 encode quantum per call; never wait for more
    /// sources and never hold a fresh source behind parity or driver HOL.
    /// Every emitted row consumes the independent original owner's AEAD PN
    /// at callback time, even when kernel copy is uncertain; NO retry here.
    pub fn poll_parity<F>(&mut self,now:MonoNs,mut on_parity:F)
        ->Result<(usize,u8),StreamError>
    where F:FnMut(&[u8],u64,u8,ConfigRevision)->DriverProof {
        if self.stopped{return Err(StreamError::Stopped)}
        self.owner.on_due(now).map_err(StreamError::Owner)?;
        if self.in_flight.is_none(){
            let Some(mut job)=self.owner.take_parity(now)
                .map_err(StreamError::Owner)? else{return Ok((0,0))};
            let prepared=match StagedParity::from_owner_job(
                &mut job,self.profile,self.record_payload_budget
            ){
                Ok(x)=>x,
                Err(e)=>{
                    self.owner.finish_parity(job,0,false);
                    return Err(StreamError::Codec(e))
                }
            };
            self.in_flight=Some(InFlight{job,prepared,copied:0,staged:0,capacity_known:true});
        }
        let cur=self.in_flight.as_mut().ok_or(StreamError::Invalid)?;
        // The original kernel batch still borrows these immutable
        // ciphertexts. Never complete or encode another parity job until
        // actual M4 definite-prefix resolution is reported.
        if cur.staged>0{return Ok((0,0))}
        if now.0>cur.job.expire_at.0{
            let job=self.in_flight.take().ok_or(StreamError::Invalid)?;
            self.owner.finish_parity(job.job,job.copied,false);
            return Ok((0,0))
        }
        let row_start=cur.job.r as usize-cur.prepared.remaining_rows();
        let rows=match cur.prepared.next_quantum(
            &self.codec,self.record_payload_budget,BackendChoice::default()
        ){
            Ok(Some((rows,_)))=>rows,
            Ok(None)=>Vec::new(),
            Err(e)=>{
                let job=self.in_flight.take().ok_or(StreamError::Invalid)?;
                self.owner.finish_parity(job.job,job.copied,false);
                return Err(StreamError::Codec(e))
            }
        };
        let mut copied_now=0u8;
        for (i,wire) in rows.iter().enumerate(){
            let row=u8::try_from(row_start+i).map_err(|_|StreamError::Invalid)?;
            match on_parity(wire,cur.job.block_id,row,cur.job.revision){
                DriverProof::Copied=>{cur.copied=cur.copied.saturating_add(1);copied_now+=1;},
                DriverProof::NotSent=>{},
                DriverProof::Uncertain=>cur.capacity_known=false,
                DriverProof::Staged=>cur.staged=cur.staged.saturating_add(1),
            }
        }
        let emitted=rows.len();
        if cur.prepared.remaining_rows()==0 && cur.staged==0{
            let finished=self.in_flight.take().ok_or(StreamError::Invalid)?;
            self.owner.finish_parity(
                finished.job,finished.copied,finished.capacity_known
            );
        }
        Ok((emitted,copied_now))
    }
    /// The SAME original M4 kernel batch resolves staged immutable parity
    /// records only after its synchronous sendmmsg definite prefix. Neither
    /// a Rust queue acceptance nor an uncertain syscall counts copied.
    pub fn settle_staged(&mut self,copied:u8,not_sent:u8,uncertain:u8)
        ->Result<(),StreamError>{
        if self.stopped{return Err(StreamError::Stopped)}
        let cur=self.in_flight.as_mut().ok_or(StreamError::Invalid)?;
        if u16::from(copied)+u16::from(not_sent)+u16::from(uncertain)
            !=u16::from(cur.staged){return Err(StreamError::Invalid)}
        cur.copied=cur.copied.saturating_add(copied);
        cur.capacity_known &= uncertain==0;
        cur.staged=0;
        if cur.prepared.remaining_rows()==0{
            let done=self.in_flight.take().ok_or(StreamError::Invalid)?;
            self.owner.finish_parity(done.job,done.copied,done.capacity_known);
        }
        Ok(())
    }
    /// Stop cancels owned parity and prevents all subsequent source/cipher
    /// outputs. Outer original Go/Rust generation stops its driver separately.
    pub fn stop(&mut self){
        if self.stopped{return}
        self.stopped=true;
        if let Some(flight)=self.in_flight.take(){
            self.owner.finish_parity(flight.job,flight.copied,false);
        }
        self.owner.stop();
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
