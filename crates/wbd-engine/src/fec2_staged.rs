//! M0 integration boundary between accepted M1 bounded short-block owner and
//! accepted M3 RS16. Does not admit FEC2 capability/kind2/3 or Go policy.
//! The caller holds the authenticated generation/direction and the ParityJob;
//! production first-send and driver completion remain original owner duties.
//! Each call writes at most four final repair payloads from one cached block.
#![forbid(unsafe_code)]

use crate::runtime::fec2_owner::ParityJob;
use wbd_codec::fec_v2::{
    BackendChoice, BackendUsed, Error, PreparedBlock, Profile, Rs16,
    MAX_BATCH_ROWS, REPAIR_HEADER,
};

pub struct StagedParity {
    block_id: u64,
    profile: Profile,
    r: usize,
    next_row: usize,
    prepared: PreparedBlock,
}

impl StagedParity {
    /// Must use the same frozen profile/revision that issued this M1 job.
    /// A mismatch is rejected BEFORE consuming any parity row or driver PN.
    /// This owns exactly one set of zero-tail math symbols, never the M1
    /// source slab or a sealed record/borrowed driver send.
    pub fn from_owner_job(
        job: &mut ParityJob, authenticated_profile: Profile,
        record_payload_budget: usize,
    ) -> Result<Self, Error> {
        let k=job.source_count();
        if job.block_id==0 || k==0 || k!=usize::from(job.k)
            || authenticated_profile.parity_count(k)?!=usize::from(job.r)
        {
            return Err(Error::ConflictingMeta);
        }
        let prepared=job.with_sources(|refs|
            PreparedBlock::from_frames(refs,record_payload_budget))?;
        Ok(Self{block_id:job.block_id,profile:authenticated_profile,
                r:usize::from(job.r),next_row:0,prepared})
    }

    /// One bounded M3 codec quantum (<=4 output rows). The caller must
    /// separately original-AEAD-seal and submit each output, then attribute
    /// definite copied-prefix/uncertain outcomes through M1.finish_parity.
    /// A codec failure NEVER advances this row cursor.
    pub fn next_quantum(
        &mut self, rs:&Rs16, record_payload_budget:usize,
        backend:BackendChoice,
    )->Result<Option<(Vec<Vec<u8>>,BackendUsed)>,Error>{
        if self.next_row==self.r{return Ok(None)}
        let count=(self.r-self.next_row).min(MAX_BATCH_ROWS);
        let len=REPAIR_HEADER+self.prepared.symbol_len();
        if len>record_payload_budget{return Err(Error::BudgetExceeded)}
        let mut rows=vec![vec![0u8;len];count];
        let mut views=rows.iter_mut().map(Vec::as_mut_slice).collect::<Vec<_>>();
        let used=rs.encode_prepared_into(
            self.block_id,&mut self.prepared,self.profile,self.next_row,
            &mut views,record_payload_budget,backend
        )?;
        self.next_row+=count;
        Ok(Some((rows,used)))
    }

    /// Same bounded M3 encode and row cursor, but reuse the original
    /// FixedStream-owned four wire scratch slabs across ALL FEC blocks.
    /// No heap allocation per row or temporary Vec of borrowed row views.
    /// Scratch is never loaned to M4: original owner seals/copies each row
    /// synchronously before the next quantum may overwrite its plaintext.
    pub fn next_quantum_reuse(
        &mut self,rs:&Rs16,record_payload_budget:usize,
        backend:BackendChoice,rows:&mut [Vec<u8>;MAX_BATCH_ROWS]
    )->Result<Option<(usize,BackendUsed)>,Error>{
        if self.next_row==self.r{return Ok(None)}
        let count=(self.r-self.next_row).min(MAX_BATCH_ROWS);
        let len=REPAIR_HEADER+self.prepared.symbol_len();
        if len>record_payload_budget{return Err(Error::BudgetExceeded)}
        for row in rows.iter_mut().take(count){row.resize(len,0)}
        // Stack-only four-slice view. The codec sees EXACTLY count output
        // rows, never any stale unused scratch row from a previous block.
        let [a,b,c,d]=rows;
        let mut views=[a.as_mut_slice(),b.as_mut_slice(),
                       c.as_mut_slice(),d.as_mut_slice()];
        let used=rs.encode_prepared_into(
            self.block_id,&mut self.prepared,self.profile,self.next_row,
            &mut views[..count],record_payload_budget,backend
        )?;
        self.next_row+=count;
        Ok(Some((count,used)))
    }

    pub fn remaining_rows(&self)->usize {self.r-self.next_row}
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::memory::Arena;
    use crate::runtime::fec2_owner::{Fec2Owner,FecMode,Profile as OwnerProfile,Limits};
    use wbd_codec::fec_v2::parse_repair;
    use wbd_types::{ConfigRevision,MonoNs};
    use wbd_types::buffer_contract::UniqueSealable;

    #[test]
    fn r1_m0_fec2_true_m1_arena_to_m3_cauchy_recover_only_missing_source(){
        let mut arena=Arena::new(831,8,2048,8,100_000).unwrap();
        let mut owner=Fec2Owner::new(
            FecMode::Normal,OwnerProfile::Strong,ConfigRevision(1),
            Limits{pending_bytes:100_000,pending_jobs:8,max_frame:1400}
        ).unwrap();
        let a=(0..1200).map(|n|(n%251) as u8).collect::<Vec<_>>();
        let b=(0..1200).map(|n|((n*7+3)%251) as u8).collect::<Vec<_>>();
        let mut original_ready=Vec::new();
        for (i,packet) in [a.as_slice(),b.as_slice()].iter().enumerate(){
            let mut slab=arena.allocate().unwrap();
            slab.writable()[..packet.len()].copy_from_slice(packet);
            let accepted=owner.push_source(slab,0..packet.len(),MonoNs(i as u64),|first|{
                assert_eq!(first.frame,*packet);
                original_ready.push((first.ticket.unwrap().block_id,
                                     first.ticket.unwrap().index));
                true
            }).unwrap();
            assert!(accepted.source_enqueued);
            assert!(accepted.fec_retained);
            assert!(!accepted.closed_full);
        }
        assert_eq!(original_ready,vec![(1,0),(1,1)]);
        assert_eq!(owner.on_due(MonoNs(6_100_000)).unwrap(),1);
        let mut job=owner.take_parity(MonoNs(6_100_000)).unwrap().unwrap();
        assert_eq!((job.block_id,job.k,job.r),(1,2,2));

        // Capturing a mismatched applied profile cannot manufacture a
        // repair under the wrong owner policy/revision.
        assert!(matches!(
            StagedParity::from_owner_job(&mut job,Profile::Maximum,1400),
            Err(Error::ConflictingMeta)
        ));
        let mut staged=StagedParity::from_owner_job(&mut job,Profile::Strong,1400)
            .unwrap();
        let rs=Rs16::new();
        let (wire,backend)=staged.next_quantum(&rs,1400,BackendChoice::Scalar)
            .unwrap().unwrap();
        assert_eq!(backend,BackendUsed::Scalar);
        assert_eq!((wire.len(),staged.remaining_rows()),(2,0));
        assert!(staged.next_quantum(&rs,1400,BackendChoice::Scalar)
            .unwrap().is_none());
        let repairs=wire.iter().map(|w|parse_repair(w,1400).unwrap())
            .collect::<Vec<_>>();
        let mut decoder=Rs16::new();
        let (restored,used)=decoder.recover_missing(
            job.block_id,&[None,Some(b.as_slice())],&repairs,
            1400,BackendChoice::Scalar
        ).unwrap();
        assert_eq!(used,BackendUsed::Scalar);
        assert_eq!(restored.len(),1);
        assert_eq!(restored[0].0,0);
        assert_eq!(restored[0].1,a);
        // Processing parity bytes does not claim a definite driver send.
        assert_eq!(owner.report().classes[2].r_sent,0);
        owner.finish_parity(job,2,true);
        assert_eq!(owner.report().classes[2].r_sent,2);
        owner.stop();
        arena.stop();
        arena.drain_returns();
        assert_eq!(arena.report().loaned,0);
    }
}
