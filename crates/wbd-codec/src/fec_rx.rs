//! Authenticated-input FEC RX owner, bounded Heavy 3s / Compact 10s.
//! The caller MUST first verify record AEAD/replay and supply authenticated
//! epoch/direction/extended BlockID and monotonic milliseconds.
//! Scalar pinned-Go GF256 e×e recovery only; no timer thread or ISA-L.
#![forbid(unsafe_code)]
use std::collections::BTreeMap;
use crate::fec_math::{FecMathError,ReedSolomon20};
use crate::link_fec_wire::{inspect_fec_frame,FecHeader,FecShardPhase,WireError,FEC_DATA_SHARDS,FEC_HEADER};

pub const HEAVY_TTL_MS:u64=3_000;
pub const COMPACT_TTL_MS:u64=10_000;
pub const HARD_HEAVY_BLOCKS:usize=64;
pub const HARD_COMPACT_BLOCKS:usize=8192;
pub const HARD_HEAVY_BYTES:usize=64*20*65535;
#[derive(Debug,Clone,Copy,Eq,PartialEq)]
pub enum Direction{ClientToServer,ServerToClient}
#[derive(Debug,Clone,Copy)]
pub struct Scope{pub epoch:u64,pub direction:Direction,pub id_ext:u64}
#[derive(Debug,Clone,Copy)]
pub struct Config {
 pub epoch:u64,pub direction:Direction,pub max_wire:usize,
 pub max_heavy_bytes:usize,pub max_heavy_blocks:usize,
 pub max_compact_blocks:usize,pub first_id_ext:u64,
}
#[derive(Debug,Clone,Copy,Eq,PartialEq)]
pub enum RxError{Config,WrongScope,Retired,Wire(WireError),Metadata,Conflict,Math(FecMathError)}
#[derive(Default,Debug,Eq,PartialEq)]
pub struct Deliver{
 pub systematic:Vec<(u8,Vec<u8>)>,
 pub recovered:Vec<(u8,Vec<u8>)>,
}
#[derive(Default,Debug,Clone,Copy,Eq,PartialEq)]
pub struct Stats{
 pub heavy:usize,pub heavy_bytes:usize,pub compact:usize,
 pub floor:Option<u64>,pub systematic:u64,pub recovered:u64,
 pub compactions:u64,pub conflicts:u64,
}
#[derive(Clone,Copy,Eq,PartialEq)]
struct Meta{ k:u8,r:u8,len:u16,lens:[u16;FEC_DATA_SHARDS] }
impl Meta{
 fn read(h:&FecHeader)->Result<Self,RxError>{
  let k=usize::from(h.data_count);
  if k==0||k>20||h.lengths[..k].iter().any(|&n|n==0||n>h.shard_size)
    ||h.lengths[k..].iter().any(|&n|n!=0){return Err(RxError::Metadata);}
  Ok(Self{k:h.data_count,r:h.parity_count,len:h.shard_size,lens:h.lengths})
 }
 fn header(self)->FecHeader{
  FecHeader{block_id:1,shard_index:20,parity_count:self.r,
    data_count:self.k,shard_size:self.len,lengths:self.lens,
    phase:FecShardPhase::FinalParity}
 }
}
struct Heavy{
 id:u64,started:u64,profile:u8,meta:Option<Meta>,delivered:u32,
 sources:[Option<Vec<u8>>;20],parities:[Option<Vec<u8>>;20],bytes:usize,
}
impl Heavy{
 fn new(id:u64,started:u64,profile:u8)->Self{
  Self{id,started,profile,meta:None,delivered:0,
   sources:std::array::from_fn(|_|None),
   parities:std::array::from_fn(|_|None),bytes:0}
 }
}
struct Compact{
 profile:u8,meta:Option<Meta>,delivered:u32,
 lengths:[u16;20],started:u64,blocked:bool,
}
impl Compact{
 fn from_heavy(h:Heavy,now:u64)->Self{
  let mut lengths=[0u16;20];
  for (i,s) in h.sources.iter().enumerate(){if let Some(s)=s{lengths[i]=s.len() as u16;}}
  // Recovered-only sources have no retained systematic payload, but their
  // authenticated final lengths MUST survive Heavy→Compact. Otherwise a
  // late genuine source is falsely treated as a conflicting first delivery.
  if let Some(meta)=h.meta{
   for (i,length) in lengths.iter_mut().enumerate(){
    if h.delivered&(1u32<<i)!=0{*length=meta.lens[i];}
   }
  }
  Self{profile:h.profile,meta:h.meta,delivered:h.delivered,
   lengths,started:now,blocked:false}
 }
}
pub struct FecRxOwner{
 cfg:Config,math:ReedSolomon20,
 heavy:BTreeMap<u64,Heavy>,compact:BTreeMap<u64,Compact>,
 bytes:usize,clock:u64,floor:Option<u64>,stats:Stats,
}
impl FecRxOwner{
 pub fn new(cfg:Config)->Result<Self,RxError>{
  if cfg.first_id_ext==0||cfg.first_id_ext as u32==0||
   cfg.max_wire<=FEC_HEADER||cfg.max_wire>FEC_HEADER+65535||
   cfg.max_heavy_bytes==0||cfg.max_heavy_bytes>HARD_HEAVY_BYTES||
   cfg.max_heavy_blocks==0||cfg.max_heavy_blocks>HARD_HEAVY_BLOCKS||
   cfg.max_compact_blocks==0||cfg.max_compact_blocks>HARD_COMPACT_BLOCKS{
    return Err(RxError::Config);
  }
  Ok(Self{cfg,math:ReedSolomon20::new().map_err(RxError::Math)?,
   heavy:BTreeMap::new(),compact:BTreeMap::new(),
   bytes:0,clock:0,floor:Some(cfg.first_id_ext-1),stats:Stats::default()})
 }
 pub fn stats(&self)->Stats{Stats{heavy:self.heavy.len(),heavy_bytes:self.bytes,
  compact:self.compact.len(),floor:self.floor,..self.stats}}
 fn retire(&mut self,id:u64){
  let floor=self.floor.map_or(id,|x|x.max(id));self.floor=Some(floor);
  let gone=self.heavy.range(..=floor).map(|(&key,_)|key).collect::<Vec<_>>();
  for key in gone{self.bytes-=self.heavy.remove(&key).expect("exists").bytes;}
  self.compact.retain(|&key,_|key>floor);
 }
 fn compact_insert(&mut self,id:u64,c:Compact){
  if self.floor.is_some_and(|floor|id<=floor){return;}
  self.compact.insert(id,c);
  while self.compact.len()>self.cfg.max_compact_blocks{
   let oldest=*self.compact.keys().next().expect("nonempty");
   self.retire(oldest);
  }
 }
 fn compact_heavy_at(&mut self,id:u64,compact_started_ms:u64){
  if let Some(h)=self.heavy.remove(&id){
   self.bytes-=h.bytes;
   self.stats.compactions+=1;
   self.compact_insert(id,Compact::from_heavy(h,compact_started_ms));
  }
 }
 fn compact_heavy(&mut self,id:u64){
  // Actual completion/pressure transitions begin Compact at owner clock.
  self.compact_heavy_at(id,self.clock);
 }
 pub fn expire(&mut self,now:u64){
  self.clock=self.clock.max(now);
  // A delayed timer callback must preserve the first-source absolute
  // Heavy deadline, not start an extra ten seconds from callback time.
  // Thus one late expire() call can retire Heavy and Compact together.
  let old=self.heavy.iter().filter_map(|(&id,h)|{
   let deadline=h.started.saturating_add(HEAVY_TTL_MS);
   (self.clock>=deadline).then_some((id,deadline))
  }).collect::<Vec<_>>();
  for (id,deadline) in old{self.compact_heavy_at(id,deadline);}
  let expired=self.compact.iter().filter_map(|(&id,c)|
   (self.clock>=c.started.saturating_add(COMPACT_TTL_MS)).then_some(id))
   .collect::<Vec<_>>();
  for id in expired{self.retire(id);}
 }
 fn room(&mut self,extra:usize){
  while self.heavy.len()>=self.cfg.max_heavy_blocks||
   self.bytes.saturating_add(extra)>self.cfg.max_heavy_bytes{
   let Some(id)=self.heavy.iter().min_by_key(|(_,b)|(b.started,b.id))
    .map(|(&id,_)|id)else{break;};
   self.compact_heavy(id);
  }
 }
 fn check_scope(&self,s:Scope,h:&FecHeader)->Result<(),RxError>{
  if s.epoch!=self.cfg.epoch||s.direction!=self.cfg.direction||
   s.id_ext==0||s.id_ext as u32==0||s.id_ext as u32!=h.block_id{
   return Err(RxError::WrongScope);
  }
  if self.floor.is_some_and(|x|s.id_ext<=x){return Err(RxError::Retired);}
  Ok(())
 }
 fn source<'a>(h:&FecHeader,body:&'a [u8],meta:Option<Meta>)
  ->Result<&'a [u8],RxError>{
  let i=usize::from(h.shard_index);
  if i>=20{return Err(RxError::Metadata);}
  let m=match (h.phase,meta){
   (FecShardPhase::StreamingSource,m)=>m,
   (_,Some(m))=>{
    if Meta::read(h)?!=m{return Err(RxError::Metadata);}
    Some(m)
   },
   (_,None)=>Some(Meta::read(h)?),
  };
  if let Some(m)=m{
   if i>=usize::from(m.k)||h.parity_count!=m.r{return Err(RxError::Metadata);}
   let len=usize::from(m.lens[i]);
   if len>body.len()||(h.phase==FecShardPhase::StreamingSource&&len!=body.len())
    ||(h.phase==FecShardPhase::FinalSource&&body[len..].iter().any(|&b|b!=0)){
    return Err(RxError::Metadata);
   }
   Ok(&body[..len])
  }else{Ok(body)}
 }
 fn compact_push(c:&mut Compact,h:&FecHeader,body:&[u8])->Result<Deliver,RxError>{
  if c.blocked||c.profile!=h.parity_count{return Err(RxError::Metadata);}
  if h.phase!=FecShardPhase::StreamingSource{
   let next=Meta::read(h)?;
   if c.meta.is_some_and(|m|m!=next){return Err(RxError::Metadata);}
   for i in 0..20{
    if (c.delivered&(1<<i))!=0 &&
     (i>=usize::from(next.k)||c.lengths[i]!=next.lens[i]){
     return Err(RxError::Metadata);
    }
   }
   c.meta=Some(next);
  }
  if h.phase==FecShardPhase::FinalParity{return Ok(Deliver::default());}
  let src=Self::source(h,body,c.meta)?;
  let i=h.shard_index as usize;
  if c.delivered&(1<<i)!=0{
   if c.lengths[i]!=src.len() as u16{return Err(RxError::Conflict);}
   return Ok(Deliver::default());
  }
  c.lengths[i]=src.len() as u16;c.delivered|=1<<i;
  Ok(Deliver{systematic:vec![(h.shard_index,src.to_vec())],recovered:Vec::new()})
 }
 fn heavy_push(math:&ReedSolomon20,b:&mut Heavy,h:&FecHeader,body:&[u8])
  ->Result<(Deliver,bool),RxError>{
  if b.profile!=h.parity_count{return Err(RxError::Metadata);}
  if h.phase!=FecShardPhase::StreamingSource{
   let m=Meta::read(h)?;
   if b.meta.is_some_and(|old|old!=m){return Err(RxError::Metadata);}
   for i in 0..20{
    if let Some(ref s)=b.sources[i]{
     if i>=usize::from(m.k)||s.len()!=m.lens[i] as usize{
      return Err(RxError::Metadata);
     }
    }
   }
   b.meta=Some(m);
  }
  let mut out=Deliver::default();
  if h.phase==FecShardPhase::FinalParity{
   let i=usize::from(h.shard_index)-20;
   if let Some(ref old)=b.parities[i]{
    if old!=body{return Err(RxError::Conflict);}
   }else{b.parities[i]=Some(body.to_vec());b.bytes+=body.len();}
  }else{
   let body=Self::source(h,body,b.meta)?;
   let i=usize::from(h.shard_index);
   if let Some(ref old)=b.sources[i]{
    if old!=body{return Err(RxError::Conflict);}
   }else{
    b.sources[i]=Some(body.to_vec());b.bytes+=body.len();
    if b.delivered&(1<<i)==0{
     b.delivered|=1<<i;
     out.systematic.push((i as u8,body.to_vec()));
    }
   }
  }
  let done=if let Some(m)=b.meta{
   let k=usize::from(m.k);
   let missing=(0..k).filter(|&i|b.sources[i].is_none()).count();
   let available=b.parities.iter().filter(|x|x.is_some()).count();
   if missing==0{true}
   else if available<missing{false}
   else{
    let source=(0..k).map(|i|b.sources[i].as_deref()).collect::<Vec<_>>();
    let parity=b.parities.iter().enumerate().filter_map(|(i,b)|
      b.as_ref().map(|body|((i+20) as u8,body.as_slice()))).collect::<Vec<_>>();
    let decoded=math.recover_missing(&m.header(),&source,&parity)
     .map_err(RxError::Math)?;
    for (i,body) in decoded{
     if b.delivered&(1<<i)==0{
      b.delivered|=1<<i;out.recovered.push((i as u8,body));
     }
    }
    true
   }
  }else{b.sources.iter().all(Option::is_some)};
  Ok((out,done))
 }
 fn conflict(&mut self,id:u64){
  // Count distinct new fences, not every further frame hitting a tombstone.
  if self.compact.get(&id).is_some_and(|c|c.blocked){return;}
  self.stats.conflicts+=1;
  if let Some(h)=self.heavy.remove(&id){
   self.bytes-=h.bytes;
   let mut c=Compact::from_heavy(h,self.clock);c.blocked=true;
   self.compact_insert(id,c);
  }else if let Some(c)=self.compact.get_mut(&id){c.blocked=true;}
 }
 /// Only on already-authenticated record body; invalid input cannot allocate.
 pub fn push_after_auth(&mut self,wire:&[u8],scope:Scope,now:u64)
  ->Result<Deliver,RxError>{
  let view=inspect_fec_frame(wire,self.cfg.max_wire).map_err(RxError::Wire)?;
  self.check_scope(scope,&view.header)?;
  self.expire(now);
  self.check_scope(scope,&view.header)?;
  let id=scope.id_ext;
  // First source and parity might be too large for heavy: Compact still
  // allows systematic first delivery but never speculative parity recovery.
  let extra=match self.heavy.get(&id){
   Some(h) if view.header.phase==FecShardPhase::FinalParity=>
    if h.parities[view.header.shard_index as usize-20].is_some(){0}else{view.shard.len()},
   Some(h)=>if h.sources[view.header.shard_index as usize].is_some(){0}else{view.shard.len()},
   None=>view.shard.len(),
  };
  if self.heavy.contains_key(&id)&&
   self.bytes.saturating_add(extra)>self.cfg.max_heavy_bytes{
   self.compact_heavy(id);
  }
  // Capacity compaction may itself advance the monotone retired floor.
  // Recheck AFTER each such mutation: a late but previously admitted ID
  // must never reappear as a fresh Heavy block behind a new floor.
  if self.floor.is_some_and(|floor|id<=floor){return Err(RxError::Retired);}
  if !self.heavy.contains_key(&id)&&!self.compact.contains_key(&id){
   if extra<=self.cfg.max_heavy_bytes{self.room(extra);}
   if self.floor.is_some_and(|floor|id<=floor){return Err(RxError::Retired);}
   if extra<=self.cfg.max_heavy_bytes{
    self.heavy.insert(id,Heavy::new(id,self.clock,view.header.parity_count));
   }else{
    self.compact_insert(id,Compact{profile:view.header.parity_count,
     meta:None,delivered:0,lengths:[0;20],started:self.clock,blocked:false});
    if self.floor.is_some_and(|floor|id<=floor){return Err(RxError::Retired);}
   }
  }
  if let Some(c)=self.compact.get_mut(&id){
   let out=Self::compact_push(c,&view.header,view.shard);
   if out.is_err(){self.conflict(id);}
   if let Ok(ref x)=out{self.stats.systematic+=x.systematic.len() as u64;}
   return out;
  }
  let h=self.heavy.get_mut(&id).expect("fresh heavy");
  let old=h.bytes;
  let result=Self::heavy_push(&self.math,h,&view.header,view.shard);
  match result{
   Ok((out,done))=>{
    self.bytes+=self.heavy.get(&id).expect("heavy").bytes-old;
    self.stats.systematic+=out.systematic.len() as u64;
    self.stats.recovered+=out.recovered.len() as u64;
    if done{self.compact_heavy(id);}
    Ok(out)
   }
   Err(err)=>{self.conflict(id);Err(err)}
  }
 }
}
