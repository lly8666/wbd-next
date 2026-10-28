//! PLAN026 generation-safe Make-Before-Break lane lifecycle.
//!
//! No network reads, no TLS handshakes, no Go callback, no packet locks.
//! The SAME long-lived tunnel/Wintun epoch survives lane replacement.
//! This table only publishes a candidate after RX+TX native attachments are
//! both ready; the owning Rust worker must still quiesce old driver loans
//! before calling retire. Caller supplies only sessions already authenticated
//! via the original protected Go credential/TLS handoff.
#![deny(unsafe_code)]

const MAX_LANES: usize = 4;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct LaneRef {
    pub logical_id: u8,
    pub generation: u64,
    pub incarnation: u64,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum LaneSide { Rx, Tx }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum LanePhase { Active, Candidate, Retiring }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum LaneTransitionError {
    BadEpoch,
    BadLane,
    Busy,
    DuplicateGeneration,
    MissingLane,
    StaleReference,
    NotReady,
    NotRetiring,
    IncarnationExhausted,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct Candidate {
    id: LaneRef,
    rx_ready: bool,
    tx_ready: bool,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct Slot {
    active: LaneRef,
    retiring: Option<LaneRef>,
    candidate: Option<Candidate>,
}
pub struct TunnelLanes {
    epoch: [u8; 16],
    slots: [Option<Slot>; MAX_LANES],
    // Only one uncommitted replacement across the entire tunnel.
    in_transition: Option<u8>,
    next_incarnation: [u64; MAX_LANES],
}
impl TunnelLanes {
    pub fn new(epoch: [u8; 16]) -> Result<Self, LaneTransitionError> {
        if epoch == [0u8;16] {return Err(LaneTransitionError::BadEpoch);}
        Ok(Self {
            epoch, slots: [None;MAX_LANES], in_transition:None,
            next_incarnation:[1;MAX_LANES],
        })
    }
    pub fn epoch(&self)->[u8;16]{self.epoch}
    fn index(id:u8)->Result<usize,LaneTransitionError>{
        if !(1..=MAX_LANES as u8).contains(&id) {
            return Err(LaneTransitionError::BadLane)
        }
        Ok(usize::from(id-1))
    }
    pub fn attach_initial(
        &mut self, logical_id:u8, generation:u64, epoch:[u8;16],
    )->Result<LaneRef,LaneTransitionError>{
        if self.epoch!=epoch {return Err(LaneTransitionError::BadEpoch)}
        let i=Self::index(logical_id)?;
        if self.slots[i].is_some()||generation==0{
            return Err(LaneTransitionError::Busy)
        }
        let id=LaneRef{logical_id,generation,incarnation:1};
        self.slots[i]=Some(Slot{active:id,retiring:None,candidate:None});
        self.next_incarnation[i]=2;
        Ok(id)
    }
    /// Register a truly authenticated and OS-epoch-matched candidate.
    /// Neither device configuration nor Wintun session is changed.
    pub fn prepare(
        &mut self, old:LaneRef, new_generation:u64, epoch:[u8;16],
    )->Result<LaneRef,LaneTransitionError>{
        if self.epoch!=epoch{return Err(LaneTransitionError::BadEpoch)}
        let i=Self::index(old.logical_id)?;
        let slot=self.slots[i].as_ref().ok_or(LaneTransitionError::MissingLane)?;
        if slot.active!=old{return Err(LaneTransitionError::StaleReference)}
        if self.in_transition.is_some()||slot.retiring.is_some()||
           slot.candidate.is_some(){return Err(LaneTransitionError::Busy)}
        if new_generation==0||new_generation==old.generation{
            return Err(LaneTransitionError::DuplicateGeneration)
        }
        let incarnation=self.next_incarnation[i];
        self.next_incarnation[i]=incarnation.checked_add(1)
            .ok_or(LaneTransitionError::IncarnationExhausted)?;
        let fresh=LaneRef{logical_id:old.logical_id,
            generation:new_generation,incarnation};
        self.slots[i].as_mut().unwrap().candidate=
            Some(Candidate{id:fresh,rx_ready:false,tx_ready:false});
        self.in_transition=Some(old.logical_id);
        Ok(fresh)
    }
    /// Native RX/TX attachment code calls this AFTER the real capture
    /// reader and sender for this candidate are installed and ready.
    pub fn mark_ready(
        &mut self, candidate:LaneRef, side:LaneSide,
    )->Result<(),LaneTransitionError>{
        let i=Self::index(candidate.logical_id)?;
        let slot=self.slots[i].as_mut().ok_or(LaneTransitionError::MissingLane)?;
        let pending=slot.candidate.as_mut().ok_or(LaneTransitionError::MissingLane)?;
        if pending.id!=candidate{return Err(LaneTransitionError::StaleReference)}
        match side {
            LaneSide::Rx=>pending.rx_ready=true,
            LaneSide::Tx=>pending.tx_ready=true,
        }
        Ok(())
    }
    /// One publication of the new active TX route. The old route retains its
    /// exact key/seq/replay and borrowed RX handle until retired by the driver.
    pub fn promote(
        &mut self, old:LaneRef, candidate:LaneRef,
    )->Result<LaneRef,LaneTransitionError>{
        let i=Self::index(old.logical_id)?;
        let slot=self.slots[i].as_mut().ok_or(LaneTransitionError::MissingLane)?;
        if slot.active!=old{return Err(LaneTransitionError::StaleReference)}
        if self.in_transition!=Some(old.logical_id) {
            return Err(LaneTransitionError::Busy)
        }
        let pending=slot.candidate.ok_or(LaneTransitionError::MissingLane)?;
        if pending.id!=candidate{return Err(LaneTransitionError::StaleReference)}
        if !pending.rx_ready||!pending.tx_ready {
            return Err(LaneTransitionError::NotReady)
        }
        slot.retiring=Some(old);
        slot.active=candidate;
        slot.candidate=None;
        self.in_transition=None;
        Ok(candidate)
    }
    /// TLS/OS candidate setup failure may never interrupt the valid old lane.
    pub fn abort(&mut self, old:LaneRef, candidate:LaneRef)
        ->Result<(),LaneTransitionError>{
        let i=Self::index(old.logical_id)?;
        let slot=self.slots[i].as_mut().ok_or(LaneTransitionError::MissingLane)?;
        if slot.active!=old{return Err(LaneTransitionError::StaleReference)}
        if slot.candidate.map(|p|p.id)!=Some(candidate) {
            return Err(LaneTransitionError::StaleReference)
        }
        slot.candidate=None;
        self.in_transition=None;
        Ok(())
    }
    /// Caller has already joined native IO for this old incarnation and
    /// released all Npcap/Wintun frame loans. Never retire based on a timer
    /// alone without the driver quiescence acknowledgment.
    pub fn retire_quiesced(&mut self, old:LaneRef)
        ->Result<(),LaneTransitionError>{
        let i=Self::index(old.logical_id)?;
        let slot=self.slots[i].as_mut().ok_or(LaneTransitionError::MissingLane)?;
        if slot.retiring!=Some(old) {
            return Err(LaneTransitionError::NotRetiring)
        }
        slot.retiring=None;
        Ok(())
    }
    pub fn active(&self, logical_id:u8)->Option<LaneRef>{
        let i=Self::index(logical_id).ok()?;
        self.slots[i].map(|slot|slot.active)
    }
    pub fn retiring(&self, logical_id:u8)->Option<LaneRef>{
        let i=Self::index(logical_id).ok()?;
        self.slots[i].and_then(|slot|slot.retiring)
    }
    pub fn phase(&self, id:LaneRef)->Option<LanePhase>{
        let i=Self::index(id.logical_id).ok()?;
        let slot=self.slots[i]?;
        if slot.active==id {Some(LanePhase::Active)}
        else if slot.retiring==Some(id){Some(LanePhase::Retiring)}
        else if slot.candidate.map(|c|c.id)==Some(id){Some(LanePhase::Candidate)}
        else {None}
    }
}
#[cfg(test)]
mod tests{
    use super::*;
    #[test]
    fn one_tunnel_epoch_two_generations_and_exact_retire(){
        let epoch=[9;16];
        let mut t=TunnelLanes::new(epoch).unwrap();
        let old=t.attach_initial(1,11,epoch).unwrap();
        let game_peer=t.attach_initial(2,12,epoch).unwrap();
        let next=t.prepare(old,13,epoch).unwrap();
        assert_eq!(next.incarnation,2);
        assert_eq!(t.phase(next),Some(LanePhase::Candidate));
        assert_eq!(t.promote(old,next),Err(LaneTransitionError::NotReady));
        t.mark_ready(next,LaneSide::Rx).unwrap();
        assert_eq!(t.promote(old,next),Err(LaneTransitionError::NotReady));
        t.mark_ready(next,LaneSide::Tx).unwrap();
        assert_eq!(t.promote(old,next),Ok(next));
        assert_eq!(t.active(1),Some(next));
        assert_eq!(t.retiring(1),Some(old));
        assert_eq!(t.active(2),Some(game_peer));
        assert_eq!(t.phase(old),Some(LanePhase::Retiring));
        assert_eq!(t.retire_quiesced(old),Ok(()));
        assert_eq!(t.phase(old),None);
        assert_eq!(t.epoch(),epoch);
    }
    #[test]
    fn abort_keeps_active_and_stale_callback_cannot_publish(){
        let epoch=[7;16];
        let mut t=TunnelLanes::new(epoch).unwrap();
        let old=t.attach_initial(3,10,epoch).unwrap();
        let pending=t.prepare(old,12,epoch).unwrap();
        assert_eq!(t.prepare(old,13,epoch),Err(LaneTransitionError::Busy));
        assert_eq!(t.abort(old,pending),Ok(()));
        assert_eq!(t.active(3),Some(old));
        let next=t.prepare(old,14,epoch).unwrap();
        assert_ne!(pending.incarnation,next.incarnation);
        assert_eq!(t.mark_ready(pending,LaneSide::Rx),Err(LaneTransitionError::StaleReference));
        t.mark_ready(next,LaneSide::Rx).unwrap();
        t.mark_ready(next,LaneSide::Tx).unwrap();
        assert_eq!(t.promote(old,pending),Err(LaneTransitionError::StaleReference));
        assert_eq!(t.promote(old,next),Ok(next));
    }
    #[test]
    fn mismatched_os_epoch_and_cross_lane_transition_denied(){
        let mut t=TunnelLanes::new([2;16]).unwrap();
        let lane1=t.attach_initial(1,1,[2;16]).unwrap();
        let lane2=t.attach_initial(2,2,[2;16]).unwrap();
        assert_eq!(t.prepare(lane1,3,[8;16]),Err(LaneTransitionError::BadEpoch));
        let next=t.prepare(lane1,3,[2;16]).unwrap();
        assert_eq!(t.prepare(lane2,4,[2;16]),Err(LaneTransitionError::Busy));
        assert_eq!(t.promote(lane2,next),Err(LaneTransitionError::Busy));
        assert_eq!(t.abort(lane1,next),Ok(()));
        assert_eq!(t.active(2),Some(lane2));
        assert_eq!(t.retire_quiesced(lane1),Err(LaneTransitionError::NotRetiring));
    }
}
