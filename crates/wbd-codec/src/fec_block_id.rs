//! Bounded FEC wire BlockID32 -> u64 reconstruction from authenticated context.
//! MUST follow AEAD auth and PN replay. No handshake/exporter/driver is here.
//! trusted_generation MUST come from an independently authenticated owner.
//! Without that source, this helper does not make production FEC-on safe.
#![forbid(unsafe_code)]
use std::collections::BTreeMap;
use crate::fec_rx::{Direction,Scope};
use crate::link_fec_wire::{inspect_fec_frame,WireError};
pub const HALF_SPACE:u64=1u64<<31;
pub const HEAVY_MS:u64=3_000;
pub const COMPACT_MS:u64=10_000;
pub const MAX_HEAVY:usize=64;
pub const MAX_COMPACT:usize=8192;
pub const MAX_WINDOW:u32=65_535;
#[derive(Debug,Clone,Copy,Eq,PartialEq)]
pub enum IdError {
    InvalidConfig,Wire(WireError),ReservedZero,WrongEpoch,WrongDirection,
    WrongGeneration,HalfSpaceAmbiguous,OutOfWindow,Retired,Exhausted,
}
#[derive(Debug,Clone,Copy)]
pub struct AuthenticatedContext {
    pub epoch:u64,
    pub direction:Direction,
    /// This value is NOT in the old Go WF header. Caller MUST substantiate it.
    pub trusted_generation:u32,
}
#[derive(Debug,Clone,Copy)]
pub struct IdConfig {
    pub epoch:u64,pub direction:Direction,
    /// Last trusted u64 highwater anchor, zero on a freshly negotiated scope.
    pub anchor:u64,
    pub retired_floor:u64,
    pub max_forward:u32,pub max_reorder:u32,
    pub max_heavy:usize,pub max_compact:usize,
}
#[derive(Debug,Clone,Copy,Eq,PartialEq)]
pub enum TrackedPhase{Heavy,Compact}
#[derive(Debug,Clone,Copy,Eq,PartialEq)]
pub struct Observation{
    pub id_ext:u64,pub first_seen:bool,pub phase:TrackedPhase,
}
impl Observation{
    pub fn rx_scope(self,ctx:AuthenticatedContext)->Scope{
        Scope{epoch:ctx.epoch,direction:ctx.direction,id_ext:self.id_ext}
    }
}
#[derive(Debug,Clone,Copy,Eq,PartialEq)]
pub struct IdStats{
    pub highest:u64,pub retired_floor:u64,pub heavy:usize,pub compact:usize,
    pub distinct_accepted:u64,pub duplicates:u64,
    pub pressure_compactions:u64,pub retired_by_capacity:u64,
}
pub struct FecBlockIdOwner{
    cfg:IdConfig,highest:u64,floor:u64,
    heavy:BTreeMap<u64,u64>,compact:BTreeMap<u64,u64>,
    clock:u64,accepted:u64,duplicates:u64,
    pressure_compactions:u64,retired_by_capacity:u64,
}
impl FecBlockIdOwner{
    pub fn new(cfg:IdConfig)->Result<Self,IdError>{
        if cfg.epoch==0||cfg.retired_floor>cfg.anchor||
            cfg.max_forward==0||cfg.max_forward>MAX_WINDOW||
            cfg.max_reorder==0||cfg.max_reorder>MAX_WINDOW||
            cfg.max_heavy==0||cfg.max_heavy>MAX_HEAVY||
            cfg.max_compact==0||cfg.max_compact>MAX_COMPACT{
            return Err(IdError::InvalidConfig);
        }
        Ok(Self{highest:cfg.anchor,floor:cfg.retired_floor,cfg,
            heavy:BTreeMap::new(),compact:BTreeMap::new(),clock:0,
            accepted:0,duplicates:0,pressure_compactions:0,retired_by_capacity:0})
    }
    pub fn stats(&self)->IdStats{
        IdStats{highest:self.highest,retired_floor:self.floor,
            heavy:self.heavy.len(),compact:self.compact.len(),
            distinct_accepted:self.accepted,duplicates:self.duplicates,
            pressure_compactions:self.pressure_compactions,
            retired_by_capacity:self.retired_by_capacity}
    }
    fn check_context(&self,ctx:AuthenticatedContext)->Result<(),IdError>{
        if ctx.epoch!=self.cfg.epoch{return Err(IdError::WrongEpoch);}
        if ctx.direction!=self.cfg.direction{return Err(IdError::WrongDirection);}
        Ok(())
    }
    /// Read-only reconstruction; generation, window and floor all fail closed.
    pub fn preview(&self,wire:u32,ctx:AuthenticatedContext)->Result<u64,IdError>{
        self.check_context(ctx)?;
        if wire==0{return Err(IdError::ReservedZero);}
        let low=self.highest as u32;
        let ahead=u64::from(wire.wrapping_sub(low));
        let back=u64::from(low.wrapping_sub(wire));
        let candidate=if ahead==0 {
            self.highest
        }else if ahead==HALF_SPACE {
            return Err(IdError::HalfSpaceAmbiguous);
        }else if ahead<HALF_SPACE{
            if ahead>u64::from(self.cfg.max_forward){return Err(IdError::OutOfWindow);}
            self.highest.checked_add(ahead).ok_or(IdError::Exhausted)?
        }else{
            if back>u64::from(self.cfg.max_reorder){
                return Err(IdError::HalfSpaceAmbiguous);
            }
            self.highest.checked_sub(back).ok_or(IdError::Retired)?
        };
        if candidate<=self.floor{return Err(IdError::Retired);}
        if (candidate>>32)!=u64::from(ctx.trusted_generation){
            return Err(IdError::WrongGeneration);
        }
        Ok(candidate)
    }
    fn retire_to(&mut self,id:u64){
        if id<=self.floor{return;}
        self.floor=id;
        self.highest=self.highest.max(id);
        self.heavy.retain(|&key,_|key>id);
        self.compact.retain(|&key,_|key>id);
    }
    /// An external authenticated RX owner may advance its own retirement floor.
    pub fn advance_retired_floor(&mut self,id:u64){self.retire_to(id);}
    fn put_compact(&mut self,id:u64,started:u64){
        if id<=self.floor{return;}
        self.compact.entry(id).or_insert(started);
        while self.compact.len()>self.cfg.max_compact{
            let oldest=*self.compact.keys().next().expect("compact nonempty");
            self.retired_by_capacity+=1;
            self.retire_to(oldest);
        }
    }
    fn compact_one(&mut self,id:u64,started:u64,pressure:bool){
        if self.heavy.remove(&id).is_some(){
            if pressure{self.pressure_compactions+=1;}
            self.put_compact(id,started);
        }
    }
    /// Caller marks a completed/pressure-released decoder block Compact.
    /// Repeated transition does not renew existing compact deadline.
    pub fn mark_compact(&mut self,id:u64,now:u64){
        self.clock=self.clock.max(now);
        self.compact_one(id,self.clock,false);
    }
    /// No polling: caller schedules this callback. If called late, expiry
    /// is still absolute from first seen +3s then original deadline +10s.
    pub fn expire(&mut self,now:u64){
        self.clock=self.clock.max(now);
        let heavy_due=self.heavy.iter().filter_map(|(&id,&first)|{
            let due=first.saturating_add(HEAVY_MS);
            (self.clock>=due).then_some((id,due))
        }).collect::<Vec<_>>();
        for (id,due) in heavy_due{self.compact_one(id,due,false);}
        let done=self.compact.iter().filter_map(|(&id,&started)|
            (self.clock>=started.saturating_add(COMPACT_MS)).then_some(id)
        ).collect::<Vec<_>>();
        for id in done{self.retire_to(id);}
    }
    fn oldest_heavy(&self)->Option<u64>{
        self.heavy.iter().min_by_key(|(&id,&at)|(at,id)).map(|(&id,_)|id)
    }
    /// Call only after authentication/replay and strict wire header validation.
    /// Repeated shards do not renew first_seen, Compact or highwater.
    pub fn observe_id_after_auth(&mut self,wire:u32,ctx:AuthenticatedContext,now:u64)
        ->Result<Observation,IdError>{
        let initial=self.preview(wire,ctx)?;
        self.expire(now);
        let id=self.preview(wire,ctx)?;
        if id!=initial{return Err(IdError::OutOfWindow);}
        if self.heavy.contains_key(&id){
            self.duplicates+=1;
            return Ok(Observation{id_ext:id,first_seen:false,phase:TrackedPhase::Heavy});
        }
        if self.compact.contains_key(&id){
            self.duplicates+=1;
            return Ok(Observation{id_ext:id,first_seen:false,phase:TrackedPhase::Compact});
        }
        if self.heavy.len()>=self.cfg.max_heavy{
            if let Some(oldest)=self.oldest_heavy(){
                self.compact_one(oldest,self.clock,true);
            }
        }
        // A pressure compaction can raise the retired floor mid-admission.
        if id<=self.floor{return Err(IdError::Retired);}
        self.heavy.insert(id,self.clock);
        self.highest=self.highest.max(id);
        self.accepted+=1;
        Ok(Observation{id_ext:id,first_seen:true,phase:TrackedPhase::Heavy})
    }
    /// Validate the actual old-Go 56-byte layout before consuming an ID.
    /// Wire parsing alone is NOT authentication; the caller must already have
    /// a successful AEAD Open and PN replay admission and trusted generation.
    pub fn observe_wire_after_auth(&mut self,wire:&[u8],max_wire:usize,
        ctx:AuthenticatedContext,now:u64)->Result<Observation,IdError>{
        let view=inspect_fec_frame(wire,max_wire).map_err(IdError::Wire)?;
        self.observe_id_after_auth(view.header.block_id,ctx,now)
    }
}
