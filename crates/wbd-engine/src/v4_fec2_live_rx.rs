//! M0 original-Go-authorized, generation-local FEC2 **receive** composition.
//! Not a credential grant, product enable switch, socket or TUN writer.
//! One AEAD/PN replay owner protects all interleaved blocks, then M3 RS16
//! emits first-delivery candidates. M4 must validate/submit each candidate.
#![forbid(unsafe_code)]
use std::collections::{BTreeMap,BTreeSet};
use wbd_codec::fec_v2::{self,BackendChoice,Rs16};
// The authenticated original-owner RX opener is MOVED here; never minted
// separately from keys, or duplicate normal/FEC PN windows could exist.
use wbd_codec::record_replay::{ReplayProtectedLaneRx,ReplayWindowConfig};
use wbd_types::MonoNs;

// Frozen W15 100Mbps: 96/96 active, 29,425 pressure retirements/side,
// 3.61MiB stored (well below 8MiB); 75Mbps: 83 blocks, no pressure.
// Extrapolate <=~(100Mbps equivalent 110 live)*3.5=385 blocks at
// 350Mbps, then reserve ~1.66x for actual-k/feedback/reordering bursts.
// The cache is on-demand, not a preallocated 48MiB slab. Keep the same
// 150ms age and never reclaim completed groups early (W11 regression).
// Retire with a monotonic touched-time index rather than O(live blocks)
// scans on every authenticated source/parity symbol.
const MAX_ACTIVE:usize=640;
const MAX_STORED_BYTES:usize=48*1024*1024;
const MAX_BLOCK_AGE_NS:u64=150_000_000;
const BLOCK_REORDER_SPAN:u64=1024;
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) struct VerifiedReceiveEpoch {
    pub generation:u32,pub epoch:[u8;16],
    pub negotiated_features:u16,pub direction_s2c:bool,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) enum ReceiveError {
    Authorization,Stopped,Invalid,Capacity,ReplayOrAuthentication,
    ConflictingBlock,Codec
}
#[derive(Debug,PartialEq,Eq)]
pub(crate) struct FirstDelivery {
    pub block_id:u64,pub index:u8,pub recovered:bool,pub frame:Vec<u8>,
}
#[derive(Clone,Copy,Debug,Default,PartialEq,Eq)]
pub(crate) struct Fec2RxCapacityReport {
    pub peak_active:u64,
    pub peak_stored_bytes:u64,
    pub evicted_age:u64,
    pub evicted_reorder:u64,
    pub evicted_pressure:u64,
    pub invalid_retired:u64,
    pub refused_bytes:u64,
    pub rejected_invalid:u64,
    pub rejected_capacity:u64,
    pub rejected_conflict:u64,
    pub rejected_codec:u64,
}
struct LiveBlock {
    touched:MonoNs,
    sources:Vec<Option<Vec<u8>>>,
    repairs:BTreeMap<u8,Vec<u8>>,
    actual_k:Option<u8>,
    delivered:u16,
    bytes:usize,
}
impl LiveBlock {
    fn new(now:MonoNs)->Self{
        Self{touched:now,sources:vec![None;fec_v2::MAX_K],
            repairs:BTreeMap::new(),actual_k:None,delivered:0,bytes:0}
    }
}
pub(crate) struct Fec2LiveRx {
    credential:VerifiedReceiveEpoch,
    // Optional only for standalone native tests. Background original Go
    // owner keeps the *one* moved opener and supplies AEAD-admitted frames.
    opener:Option<ReplayProtectedLaneRx>,
    rs:Rs16,budget:usize,stopped:bool,
    highest_block:u64,
    blocks:BTreeMap<u64,LiveBlock>,retired:BTreeSet<u64>,
    // One (last genuine receive ns, block id) entry per live block.
    // O(log n) update / amortized oldest-only expiration at 350Mbps.
    touched_order:BTreeSet<(u64,u64)>,
    stored:usize,evicted:u64,
    capacity_report:Fec2RxCapacityReport,
}
impl Fec2LiveRx{
    // This evidence must be supplied by the same Rust Go TLS owner that
    // verified the original exporter's principal, epoch and feature bit2.
    // A raw packet, peer request or config file is NEVER an admission fact.
    pub(crate) fn from_original_owner(
        verified:VerifiedReceiveEpoch,opener:ReplayProtectedLaneRx,
        wire_max:usize)->Result<Self,ReceiveError>{
        let mut rx=Self::from_authenticated_scope(verified,wire_max)?;
        rx.opener=Some(opener);
        Ok(rx)
    }
    /// M0 original-Go background owner already moved the only replay opener
    /// to its RX worker. This bounded FEC cache MUST NOT clone its keys.
    pub(crate) fn from_authenticated_scope(
        verified:VerifiedReceiveEpoch,wire_max:usize)->Result<Self,ReceiveError>{
        if verified.generation==0||verified.epoch==[0;16]||
           verified.negotiated_features!=7{
            return Err(ReceiveError::Authorization)
        }
        // Direction is authenticated by the original Go owner and carried
        // in this immutable scope. Both C2S and S2C are legitimate V2
        // directions; never infer one from an unauthenticated wire header.
        let budget=wire_max.checked_sub(wbd_codec::record_frame::FIXED_WIRE_OVERHEAD)
            .ok_or(ReceiveError::Invalid)?;
        if budget<32||budget>2048{return Err(ReceiveError::Invalid)}
        Ok(Self{credential:verified,opener:None,rs:Rs16::new(),budget,
            stopped:false,highest_block:0,blocks:BTreeMap::new(),retired:BTreeSet::new(),
            touched_order:BTreeSet::new(),stored:0,evicted:0,
            capacity_report:Fec2RxCapacityReport::default()})
    }
    pub(crate) fn active_blocks(&self)->usize{self.blocks.len()}
    pub(crate) fn stored_bytes(&self)->usize{self.stored}
    /// Lost/expired old blocks are never counted as delivered or credited.
    pub(crate) fn evicted_blocks(&self)->u64{self.evicted}
    pub(crate) fn capacity_report(&self)->Fec2RxCapacityReport{self.capacity_report}
    pub(crate) fn record_rejection(&mut self,error:ReceiveError){
        match error{
            ReceiveError::Invalid=>self.capacity_report.rejected_invalid+=1,
            ReceiveError::Capacity=>self.capacity_report.rejected_capacity+=1,
            ReceiveError::ConflictingBlock=>self.capacity_report.rejected_conflict+=1,
            ReceiveError::Codec=>self.capacity_report.rejected_codec+=1,
            _=>{}
        }
    }
    pub(crate) fn stop(&mut self){
        self.stopped=true;self.blocks.clear();self.retired.clear();
        self.touched_order.clear();self.stored=0;
    }
    fn retire_one(&mut self,id:u64,reason:u8){
        if let Some(block)=self.blocks.remove(&id){
            self.touched_order.remove(&(block.touched.0,id));
            self.stored=self.stored.saturating_sub(block.bytes);
            self.retired.insert(id);
            self.evicted=self.evicted.saturating_add(1);
            match reason{
                0=>self.capacity_report.evicted_age+=1,
                1=>self.capacity_report.evicted_reorder+=1,
                _=>self.capacity_report.evicted_pressure+=1,
            }
        }
    }
    fn retire(&mut self,now:MonoNs){
        let floor=self.highest_block.saturating_sub(BLOCK_REORDER_SPAN);
        // Both indices are ordered. Work proportional to actually expired
        // blocks, not to all cached blocks per one received packet.
        while let Some(&id)=self.retired.first(){
            if id>=floor{break}
            self.retired.pop_first();
        }
        while let Some((&id,_))=self.blocks.first_key_value(){
            if id>=floor{break}
            self.retire_one(id,1);
        }
        while let Some(&(touched,id))=self.touched_order.first(){
            if now.elapsed_since(MonoNs(touched))<=MAX_BLOCK_AGE_NS{break}
            self.retire_one(id,0);
        }
    }
    /// First delivery can occur from a systematic source before ANY prior
    /// block completes. An independent AEAD/replay bitmap is forbidden.
    pub(crate) fn consume(&mut self,scope:VerifiedReceiveEpoch,
        wire:&mut [u8],now:MonoNs)->Result<Vec<FirstDelivery>,ReceiveError>{
        self.consume_with_pn(scope,wire,now).map(|(_,deliveries)|deliveries)
    }
    /// The exact M3 AEAD+unique replay PN consumed for this DATA record.
    /// Only after this return may M2 native RX count it as received.
    /// Never infer record PN from untrusted outer header or application ID.
    pub(crate) fn consume_with_pn(&mut self,scope:VerifiedReceiveEpoch,
        wire:&mut [u8],now:MonoNs)
        ->Result<(u64,Vec<FirstDelivery>),ReceiveError>{
        if self.stopped{return Err(ReceiveError::Stopped)}
        if scope!=self.credential{return Err(ReceiveError::Authorization)}
        let rec=self.opener.as_mut().ok_or(ReceiveError::Authorization)?
            .open_unique_with_fec2_after_admission_in_place(wire)
            .map_err(|_|ReceiveError::ReplayOrAuthentication)?;
        let pn=rec.pn;
        let deliveries=self.accept_authenticated(scope,rec.kind,rec.payload,now)?;
        Ok((pn,deliveries))
    }
    /// Only callable from the original worker AFTER its single moved
    /// ReplayProtectedLaneRx has admitted AEAD and a unique PN. There is
    /// no independent decryptor, seq/PN acceptance or peer grant here.
    pub(crate) fn accept_authenticated(&mut self,scope:VerifiedReceiveEpoch,
        kind:u8,payload:&[u8],now:MonoNs)
        ->Result<Vec<FirstDelivery>,ReceiveError>{
        if self.stopped{return Err(ReceiveError::Stopped)}
        if scope!=self.credential{return Err(ReceiveError::Authorization)}
        let (id,index,kind,body,k)=match kind{
            2=>{
                let src=fec_v2::parse_source(payload,self.budget)
                    .map_err(|_|ReceiveError::Invalid)?;
                (src.block_id,src.source_index,2,src.frame.to_vec(),None)
            }
            3=>{
                let repair=fec_v2::parse_repair(payload,self.budget)
                    .map_err(|_|ReceiveError::Invalid)?;
                (repair.block_id,repair.parity_row,3,payload.to_vec(),
                    Some(repair.actual_k))
            }
            _=>return Err(ReceiveError::Invalid)
        };
        if id==0||id<self.highest_block.saturating_sub(BLOCK_REORDER_SPAN){
            return Err(ReceiveError::Invalid)
        }
        if self.retired.contains(&id){
            self.capacity_report.invalid_retired+=1;
            return Err(ReceiveError::Invalid)
        }
        self.highest_block=self.highest_block.max(id);
        self.retire(now);
        // The current unique authenticated symbol can itself advance the
        // monotonic clock beyond the previous block's absolute lifetime.
        // retire() may have JUST evicted this same identity above. Never
        // recreate it as a fresh FEC block and redeliver a source from a
        // delayed parity (or a separately authenticated late source).
        if self.retired.contains(&id){
            self.capacity_report.invalid_retired+=1;
            return Err(ReceiveError::Invalid)
        }
        if !self.blocks.contains_key(&id)&&self.blocks.len()>=MAX_ACTIVE{
            // Never allow old incomplete parity/source work to block a
            // freshly authenticated source. Evict ONE oldest incomplete
            // block; this is a censored drop, not successful recovery.
            let oldest=self.touched_order.first().map(|(_,id)|*id)
                .ok_or(ReceiveError::Capacity)?;
            self.retire_one(oldest,2);
        }
        let old=self.blocks.get(&id);
        if old.is_some_and(|b|b.touched.0>now.0){return Err(ReceiveError::Invalid)}
        if body.len()>MAX_STORED_BYTES.saturating_sub(self.stored){
            self.capacity_report.refused_bytes+=1;
            return Err(ReceiveError::Capacity)
        }
        // Mirror the last-touch semantics even if this authenticated
        // unique-PN symbol later proves to conflict with an already
        // delivered source; no stale expiry-index entries are left behind.
        if let Some(old)=self.blocks.get(&id){
            self.touched_order.remove(&(old.touched.0,id));
        }
        let b=self.blocks.entry(id).or_insert_with(||LiveBlock::new(now));
        b.touched=now;
        self.touched_order.insert((now.0,id));
        let mut output=Vec::new();
        if kind==2{
            let index=index as usize;
            if b.sources[index].is_some()||(b.delivered & (1u16<<index))!=0||
                b.actual_k.is_some_and(|k|index>=usize::from(k)){
                return Err(ReceiveError::ConflictingBlock)
            }
            // An authenticated source can be immediately returned to the
            // original LINK or IP candidate validator, without waiting for
            // parity or a previous block (first-arrival, no cross-block HOL).
            b.delivered|=1u16<<index;
            output.push(FirstDelivery{block_id:id,index:index as u8,
                recovered:false,frame:body.clone()});
            b.sources[index]=Some(body);
        }else{
            let Some(actual_k)=k else{return Err(ReceiveError::Invalid)};
            if b.actual_k.is_some_and(|old|old!=actual_k)||
                b.sources.iter().enumerate().any(|(i,s)|i>=actual_k as usize&&s.is_some())||
                b.repairs.contains_key(&index){
                return Err(ReceiveError::ConflictingBlock)
            }
            b.actual_k=Some(actual_k);
            b.repairs.insert(index,body);
        }
        let charge=if kind==2{b.sources[index as usize].as_ref().map_or(0,Vec::len)}
            else{b.repairs.get(&index).map_or(0,Vec::len)};
        self.stored=self.stored.saturating_add(charge);
        b.bytes=b.bytes.saturating_add(charge);
        if let Some(k)=b.actual_k {
            let live=b.sources.iter().take(k as usize)
                .map(Option::as_deref).collect::<Vec<_>>();
            let missing=live.iter().filter(|v|v.is_none()).count();
            if missing>0&&b.repairs.len()>=missing{
                // Owned parity remains bound to this exact authenticated
                // block+generation; reparsing keeps the M3 wire invariants.
                let repairs=b.repairs.values().map(|bytes|
                    fec_v2::parse_repair(bytes,self.budget)
                ).collect::<Result<Vec<_>,_>>().map_err(|_|ReceiveError::Codec)?;
                let recovered=self.rs.recover_missing(id,&live,&repairs,
                    self.budget,BackendChoice::default())
                    .map_err(|_|ReceiveError::Codec)?.0;
                let recovered_bytes=recovered.iter()
                    .try_fold(0usize,|total,(_,frame)|total.checked_add(frame.len()))
                    .ok_or(ReceiveError::Capacity)?;
                if recovered_bytes>MAX_STORED_BYTES.saturating_sub(self.stored){
                    self.capacity_report.refused_bytes+=1;
                    return Err(ReceiveError::Capacity)
                }
                for (i,frame) in recovered {
                    let bit=1u16<<i;
                    if b.delivered&bit!=0{return Err(ReceiveError::ConflictingBlock)}
                    b.delivered|=bit;
                    self.stored+=frame.len();
                    b.bytes+=frame.len();
                    b.sources[i as usize]=Some(frame.clone());
                    output.push(FirstDelivery{block_id:id,index:i,
                        recovered:true,frame});
                }
            }
        }
        self.capacity_report.peak_active=self.capacity_report.peak_active
            .max(self.blocks.len() as u64);
        self.capacity_report.peak_stored_bytes=self.capacity_report.peak_stored_bytes
            .max(self.stored as u64);
        Ok(output)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use wbd_codec::record_crypto::{LaneTxCrypto,DirectionKeys,RecordSuite};
    fn opened(suite:RecordSuite)->ReplayProtectedLaneRx{
        ReplayProtectedLaneRx::new_for_suite(keys(),1400,suite,
            ReplayWindowConfig{
                pn_per_second:20000,cache_horizon_ms:200,
                fec_horizon_ms:150,rtt_ms:100,
                metadata_budget_bytes:256*1024
            }).unwrap()
    }
    fn keys()->DirectionKeys{DirectionKeys{
        aead_key:[39;32],iv:[40;12],hp_key:[41;32]}}
    fn epoch()->VerifiedReceiveEpoch{VerifiedReceiveEpoch{
        generation:2,epoch:[10;16],negotiated_features:7,direction_s2c:true}}
    fn seal(tx:&mut LaneTxCrypto,kind:u8,payload:&[u8])->Vec<u8>{
        let mut wire=vec![0u8;1400];
        wire[14..14+payload.len()].copy_from_slice(payload);
        let (_,n)=tx.seal_fec2_after_admission_in_place(
            kind,&mut wire,payload.len(),0).unwrap();
        wire.truncate(n);wire
    }
    #[test]
    fn m0_fec2_live_rx_background_receiver_cannot_admit_without_original_opener(){
        let suite=RecordSuite::ChaCha20Poly1305;
        let mut tx=LaneTxCrypto::new_for_suite(keys(),1400,suite).unwrap();
        let mut blocks=Fec2LiveRx::from_authenticated_scope(epoch(),1400).unwrap();
        let payload=fec_v2::source_owned(7,0,b"source",1369).unwrap();
        let mut wire=seal(&mut tx,2,&payload);
        assert_eq!(blocks.consume(epoch(),&mut wire,MonoNs(1)),
            Err(ReceiveError::Authorization));
        assert_eq!(blocks.accept_authenticated(
            VerifiedReceiveEpoch{epoch:[99;16],..epoch()},2,
            &payload,MonoNs(1)),Err(ReceiveError::Authorization));
        // This packet has NOT been AEAD opened: only an authentic worker
        // may call accept_authenticated; native API is module-private.
        let mut admitted=opened(suite);
        let actual=admitted.open_unique_with_fec2_after_admission_in_place(
            &mut wire).unwrap();
        let result=blocks.accept_authenticated(epoch(),actual.kind,
            actual.payload,MonoNs(2)).unwrap();
        assert_eq!(result.len(),1);
        assert_eq!(result[0].frame,b"source");
        blocks.stop();
        assert_eq!(blocks.accept_authenticated(epoch(),2,&payload,MonoNs(3)),
            Err(ReceiveError::Stopped));
    }
    #[test]
    fn m0_fec2_live_rx_same_turn_age_retirement_cannot_redeliver_k1(){
        // Actual M3 AEAD accepts two DISTINCT legitimate record PNs.
        // The first systematic source is delivered at time 1; an old k1
        // parity arriving after the 150ms block lifetime MUST NOT revive
        // this already-delivered block, even if retirement occurs inside
        // the SAME accept_authenticated call, not on a prior packet.
        let suite=RecordSuite::ChaCha20Poly1305;
        let mut tx=LaneTxCrypto::new_for_suite(keys(),1400,suite).unwrap();
        let mut rx=Fec2LiveRx::from_original_owner(
            epoch(),opened(suite),1400).unwrap();
        let frame=vec![0x63u8;120];
        let source=fec_v2::source_owned(7,0,&frame,1369).unwrap();
        let repair=Rs16::new().encode_owned(
            7,&[frame.as_slice()],fec_v2::Profile::Maximum,
            0,1,1369,BackendChoice::Scalar
        ).unwrap().0.remove(0);
        let mut systematic=seal(&mut tx,2,&source);
        assert_eq!(rx.consume(epoch(),&mut systematic,MonoNs(1)).unwrap(),
            vec![FirstDelivery{block_id:7,index:0,recovered:false,
                frame:frame.clone()}]);
        let mut late_parity=seal(&mut tx,3,&repair);
        assert_eq!(rx.consume(epoch(),&mut late_parity,
            MonoNs(MAX_BLOCK_AGE_NS+3)),Err(ReceiveError::Invalid));
        assert_eq!(rx.evicted_blocks(),1);
        assert_eq!(rx.active_blocks(),0);
        // A later independent verified block remains free to deliver.
        let later=fec_v2::source_owned(8,0,&[0x42u8;120],1369).unwrap();
        let mut fresh=seal(&mut tx,2,&later);
        assert_eq!(rx.consume(epoch(),&mut fresh,
            MonoNs(MAX_BLOCK_AGE_NS+4)).unwrap().len(),1);
        rx.stop();
        assert_eq!(rx.stored_bytes(),0);
    }
    #[test]
    fn m0_fec2_350mbps_bounded_touch_index_retirement_no_full_scan(){
        // Capacity derived from W15 100Mbps 96/96 pressure at 150ms:
        // 640 live blocks admit the >=~385 extrapolated 350Mbps window.
        // All 450 independent distinct blocks are incomplete, so there
        // is no premature complete-block retirement, no pressure or HOL.
        let mut rx=Fec2LiveRx::from_authenticated_scope(epoch(),1400).unwrap();
        for id in 1..=450u64{
            let frame=fec_v2::source_owned(id,0,&[id as u8;1287],1369).unwrap();
            let r=rx.accept_authenticated(epoch(),2,&frame,MonoNs(id*1000)).unwrap();
            assert_eq!(r.len(),1);
            assert!(!r[0].recovered);
        }
        assert_eq!(rx.active_blocks(),450);
        assert_eq!(rx.touched_order.len(),450);
        assert_eq!(rx.capacity_report().evicted_pressure,0);
        assert_eq!(rx.capacity_report().evicted_reorder,0);
        assert_eq!(rx.capacity_report().evicted_age,0);
        assert!(rx.stored_bytes()<=MAX_STORED_BYTES);
        // Refresh a block without copying the entire metadata table.
        let more=fec_v2::source_owned(1,1,&[0x42;1287],1369).unwrap();
        assert_eq!(rx.accept_authenticated(epoch(),2,&more,MonoNs(1_000_000))
            .unwrap().len(),1);
        assert_eq!(rx.touched_order.len(),rx.blocks.len());
        // Expire all OTHER blocks; the last refreshed record stays live.
        let recent=fec_v2::source_owned(451,0,&[0x31;1287],1369).unwrap();
        let now=MonoNs(MAX_BLOCK_AGE_NS+600_000);
        assert_eq!(rx.accept_authenticated(epoch(),2,&recent,now).unwrap().len(),1);
        assert_eq!(rx.capacity_report().evicted_age,449);
        assert_eq!(rx.active_blocks(),2);
        assert_eq!(rx.touched_order.len(),2);
        assert_eq!(rx.blocks.len(),2);
        rx.stop();
        assert_eq!(rx.stored_bytes(),0);
        assert!(rx.touched_order.is_empty());
    }
    #[test]
    fn m0_fec2_live_rx_old_incomplete_blocks_cannot_head_of_line_fresh(){
        let suite=RecordSuite::ChaCha20Poly1305;
        let mut tx=LaneTxCrypto::new_for_suite(keys(),1400,suite).unwrap();
        let mut rx=Fec2LiveRx::from_original_owner(
            epoch(),opened(suite),1400).unwrap();
        for id in 1..=MAX_ACTIVE as u64+1{
            // Every block is deliberately incomplete. A busy old block
            // cannot force an authenticated new source to wait.
            let src=fec_v2::source_owned(id,0,&[id as u8;32],1369).unwrap();
            let mut wire=seal(&mut tx,2,&src);
            let out=rx.consume(epoch(),&mut wire,MonoNs(id)).unwrap();
            assert_eq!(out.len(),1);
            assert_eq!(out[0].block_id,id);
        }
        assert_eq!(rx.active_blocks(),MAX_ACTIVE);
        assert_eq!(rx.capacity_report().evicted_pressure,1);
        assert_eq!(rx.evicted_blocks(),1);
        assert!(rx.stored_bytes()<=MAX_STORED_BYTES);
        // Even a distinct authenticated PN with the same retired block
        // identity MUST NOT redeliver the evicted source.
        let prior=fec_v2::source_owned(1,0,&[99u8;32],1369).unwrap();
        let mut late=seal(&mut tx,2,&prior);
        assert_eq!(rx.consume(epoch(),&mut late,MonoNs(34)),
            Err(ReceiveError::Invalid));
        rx.stop();assert_eq!(rx.stored_bytes(),0);
    }
    #[test]
    fn m0_fec2_highrate_maximum_iid_missing_sources_recover_and_reclaim(){
        // ~56 full k16 groups at 50Mbps/150ms used to exceed MAX_ACTIVE=32.
        // Deliver eleven real first sources and five timely independent
        // Maximum parity rows; all five missing must be recovered. This
        // tests live RX cardinality, memory and late duplicate suppression,
        // not an invented sender or a simulated TUN-success receipt.
        let mut rx=Fec2LiveRx::from_authenticated_scope(epoch(),1400).unwrap();
        let codec=Rs16::new();
        let mut delivered=0usize;
        let mut recovered=0usize;
        for block_id in 1..=56u64 {
            let frames=(0..16usize).map(|i|vec![(i as u8)^block_id as u8;1287])
                .collect::<Vec<_>>();
            let refs=frames.iter().map(Vec::as_slice).collect::<Vec<_>>();
            for i in 0..16usize {
                if [0,3,6,9,12].contains(&i){continue}
                let source=fec_v2::source_owned(block_id,i as u8,&frames[i],1369).unwrap();
                let out=rx.accept_authenticated(epoch(),2,&source,
                    MonoNs(block_id*1_000_000)).unwrap();
                delivered+=out.len();
            }
            // Live M4 parity policy batches at most MAX_BATCH_ROWS=4.
            // Five genuine rows therefore require two bounded polls.
            let mut parity=codec.encode_owned(block_id,&refs,
                fec_v2::Profile::Maximum,0,4,1369,BackendChoice::Scalar)
                .unwrap().0;
            parity.extend(codec.encode_owned(block_id,&refs,
                fec_v2::Profile::Maximum,4,1,1369,BackendChoice::Scalar)
                .unwrap().0);
            assert_eq!(parity.len(),5);
            for row in &parity{
                let out=rx.accept_authenticated(epoch(),3,row,
                    MonoNs(block_id*1_000_000+400)).unwrap();
                for recovered_source in &out{
                    assert!(recovered_source.recovered);
                    assert_eq!(recovered_source.frame,
                        frames[recovered_source.index as usize]);
                }
                recovered+=out.len();
            }
            assert!(rx.active_blocks()<=MAX_ACTIVE);
            assert!(rx.stored_bytes()<=MAX_STORED_BYTES);
        }
        assert_eq!(delivered,56*11);
        assert_eq!(recovered,56*5);
        assert_eq!(rx.active_blocks(),56);
        assert!(rx.stored_bytes()>0);
        assert_eq!(rx.capacity_report().evicted_pressure,0);
        assert_eq!(rx.capacity_report().refused_bytes,0);
        let duplicate=fec_v2::source_owned(56,0,&frames_for_late(),1369).unwrap();
        assert_eq!(rx.accept_authenticated(epoch(),2,&duplicate,MonoNs(57_000_000)),
            Err(ReceiveError::ConflictingBlock));
        rx.stop();
    }
    fn frames_for_late()->Vec<u8>{vec![0u8;1287]}
    #[test]
    fn m0_fec2_live_rx_interleaved_four_blocks_3_ciphers_no_hol_and_stop(){
        for suite in [RecordSuite::ChaCha20Poly1305,
                RecordSuite::Aes128Gcm,RecordSuite::Aes256Gcm]{
            let mut tx=LaneTxCrypto::new_for_suite(keys(),1400,suite).unwrap();
            let mut rx=Fec2LiveRx::from_original_owner(epoch(),opened(suite),1400).unwrap();
            assert_eq!(Fec2LiveRx::from_original_owner(VerifiedReceiveEpoch{
                negotiated_features:3,..epoch()},opened(suite),1400)
                .err(),Some(ReceiveError::Authorization));
            let codec=Rs16::new();
            let mut queued=Vec::new();
            for id in 1..=4u64{
                let first=vec![id as u8;100];
                let second=vec![(id as u8)+9;100];
                let src=fec_v2::source_owned(id,0,&first,1369).unwrap();
                let repaired=codec.encode_owned(id,&[&first,&second],
                    fec_v2::Profile::Mild,0,1,1369,BackendChoice::Scalar)
                    .unwrap().0.remove(0);
                let mut ciphertext=seal(&mut tx,2,&src);
                let original=ciphertext.clone();
                let delivery=rx.consume(epoch(),&mut ciphertext,MonoNs(id*1_000)).unwrap();
                assert_eq!(delivery,vec![FirstDelivery{block_id:id,index:0,
                    recovered:false,frame:first}]);
                let mut again=original;
                assert_eq!(rx.consume(epoch(),&mut again,MonoNs(id*1_001)),
                    Err(ReceiveError::ReplayOrAuthentication));
                queued.push((id,second,seal(&mut tx,3,&repaired)));
            }
            assert_eq!(rx.active_blocks(),4);
            let mut recovered=0;
            for (id,second,mut parity) in queued.into_iter().rev(){
                let out=rx.consume(epoch(),&mut parity,MonoNs(20_000+id)).unwrap();
                assert_eq!(out,vec![FirstDelivery{block_id:id,index:1,
                    recovered:true,frame:second}]);
                recovered+=1;
            }
            assert_eq!(recovered,4);
            assert!(rx.stored_bytes()>0);
            assert_eq!(rx.active_blocks(),4);
            rx.stop();assert_eq!(rx.active_blocks(),0);
            assert_eq!(rx.stored_bytes(),0);
            assert_eq!(rx.consume(epoch(),&mut vec![0u8;40],MonoNs(30_000)),
                Err(ReceiveError::Stopped));
        }
    }
}
