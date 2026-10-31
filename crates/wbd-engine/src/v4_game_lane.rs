//! M0 original-owner Game2/4 lane adapter. Receives ONLY original Go TLS
//! validated epoch, generation, lane IDs and distinct exporter keys.
//! Reuses frozen M1 GameTx shared-buffer dispatch and GameRx dedup;
//! per-lane AEAD/PN/replay are independently allocated; no public Go grant.
#![forbid(unsafe_code)]
use crate::memory::{Arena,UniqueBuffer};
#[cfg(feature="fec2_product_record")]
use crate::v4_game_fec::{GameFecTx,GameFecRx,GameFecCounters};
#[cfg(feature="fec2_product_record")]
use crate::v4_fec2_live_rx::VerifiedReceiveEpoch;
use std::sync::{Arc,Mutex};
use std::time::Instant;
use crate::v4_native_health::{AuthenticatedActivity,parse_authenticated_control,encode_authenticated_health_live};
use crate::cold_v4::UntrustedColdV4;
use wbd_types::TunnelKey;
use crate::runtime::game_shared::{
    ActiveLaneSnapshot,DispatchOutcome,FlowDirection,GameCounters,GameError,
    GameLimits,GameRx,GameScope,GameTx,Mode,QualifiedLane,RxLimits
};
use wbd_types::{LaneKey,LogicalPacketId,MonoNs};
use wbd_types::buffer_contract::UniqueSealable;
use wbd_codec::record_crypto::{DirectionKeys,LaneTxCrypto,RecordSuite};
use wbd_codec::record_replay::{ReplayProtectedLaneRx,ReplayWindowConfig,UniqueOpenError};
use wbd_codec::record_crypto::CryptoError;
pub struct ScopedKeys{pub lane:QualifiedLane,pub tx:DirectionKeys,pub rx:DirectionKeys}
struct TxLane{key:LaneKey,tx:LaneTxCrypto}
struct RxLane{key:LaneKey,rx:ReplayProtectedLaneRx}
/// One original per-lane AEAD/replay owner, moved (not cloned) into its
/// sole authenticated Linux worker before any DATA can be delivered.
pub(crate) struct GameLaneOpener{
    lane:RxLane,inner_mtu:usize,health_origin:Instant,
    health:Arc<AuthenticatedActivity>,last_health_record_ns:u64,
}
impl GameLaneOpener{
    pub(crate) fn open<'a>(&mut self,wire:&'a mut [u8])
        ->Result<Option<(LogicalPacketId,&'a [u8])>,Error>{
        let opened=self.lane.rx.open_unique_in_place(wire).map_err(|e|match e{
            UniqueOpenError::InvalidRecord(CryptoError::Authentication)=>Error::Crypto,
            UniqueOpenError::InvalidRecord(_)=>Error::Invalid,
            UniqueOpenError::Duplicate=>Error::Duplicate,
            UniqueOpenError::Retired=>Error::Stale,
        })?;
        let now=self.health_origin.elapsed().as_nanos().min(u128::from(u64::MAX)) as u64;
        if opened.kind==0{
            read_game_health(opened.payload,now,&self.health)?;
            return Ok(None)
        }
        if opened.kind!=1{return Err(Error::Invalid)}
        let (id,payload)=wbd_codec::decode_game(opened.payload,self.inner_mtu+16)
            .map_err(|_|Error::Invalid)?;
        if payload.len()>self.inner_mtu{return Err(Error::Invalid)}
        if now.saturating_sub(self.last_health_record_ns)>=500_000_000{
            self.health.record_batch(now,0,None);
            self.last_health_record_ns=now;
        }
        Ok(Some((id,payload)))
    }
}
fn read_game_health(wire:&[u8],now:u64,evidence:&AuthenticatedActivity)
    ->Result<(),Error>{
    let value=parse_authenticated_control(wire).map_err(|_|Error::Invalid)?;
    let idle=value.peer_idle_ns.ok_or(Error::Invalid)?;
    if value.receipt.is_some()||value.quality{return Err(Error::Invalid)}
    evidence.record_batch(now,0,Some((now,idle)));
    Ok(())
}
#[derive(Debug,PartialEq,Eq)]
pub enum Error{Unauthorized,Invalid,Capacity,Stopped,Duplicate,Stale,Crypto,Game(GameError)}
/// One bounded RX owner for all authenticated Game lanes; independent of the
/// TX owner mutex even while TX is sealing or executing raw send syscalls.
/// Temporary authenticated, scope-bound source reserved against concurrent
/// lane duplicates, but NOT yet marked delivered in the shared Game window.
/// Its original slab remains frozen to this worker until the TUN result.
pub(crate) struct PreparedGameDelivery{
    id:LogicalPacketId,lane:LaneKey,len:usize,slab:UniqueBuffer,
}
impl PreparedGameDelivery{
    pub(crate) fn payload(&mut self)->&[u8]{
        &self.slab.writable()[14..14+self.len]
    }
}

/// One logical Game FEC symbol may yield MULTIPLE distinct recovered IP
/// frames. Keep every candidate alive until all corresponding TUN writes
/// resolve; the logical symbol is committed only if ALL writes succeed.
#[cfg(feature="fec2_product_record")]
pub(crate) struct PreparedGameFecBatch{
    id:LogicalPacketId,lane:LaneKey,slab:UniqueBuffer,
    frames:Vec<Vec<u8>>,
}
#[cfg(feature="fec2_product_record")]
impl PreparedGameFecBatch{
    pub(crate) fn frames(&self)->&[Vec<u8>]{&self.frames}
}
pub(crate) struct GameReceiveOwner{
    rx:GameRx,rx_scope:GameScope,lanes:Vec<RxLane>,
    arena:Arena,stopped:bool,inner_mtu:usize,lane_count:usize,
    // At most one in-flight TUN write per RX lane, no per-packet HashSet.
    // A pending entry suppresses a concurrent duplicate but does not set
    // shared delivery bits until the genuine TUN write succeeds.
    pending:Vec<LogicalPacketId>,
    health_origin:Instant,health:Arc<AuthenticatedActivity>,
    last_health_record_ns:u64,
    #[cfg(feature="fec2_product_record")]
    fec:Option<GameFecRx>,
}
impl GameReceiveOwner{
    /// Remove exactly one replay owner; repeated handoff is unauthorized.
    /// Shared GameRx still validates lane key, generation and epoch.
    pub(crate) fn take_lane_for_worker(&mut self,lane_key:LaneKey)
        ->Result<GameLaneOpener,Error>{
        if self.stopped{return Err(Error::Stopped)}
        let at=self.lanes.iter().position(|l|l.key==lane_key)
            .ok_or(Error::Unauthorized)?;
        Ok(GameLaneOpener{
            lane:self.lanes.swap_remove(at),inner_mtu:self.inner_mtu,
            health_origin:self.health_origin,health:Arc::clone(&self.health),
            last_health_record_ns:0,
        })
    }
    pub(crate) fn prepare_receive(&mut self,lane_key:LaneKey,wire:&mut [u8])
        ->Result<Option<PreparedGameDelivery>,Error>{
        if self.stopped{return Err(Error::Stopped)}
        #[cfg(feature="fec2_product_record")]
        if self.fec.is_some(){return Err(Error::Invalid)}
        let lane=self.lanes.iter_mut().find(|l|l.key==lane_key)
            .ok_or(Error::Unauthorized)?;
        let opened=lane.rx.open_unique_in_place(wire).map_err(|e|match e{
            UniqueOpenError::InvalidRecord(CryptoError::Authentication)=>Error::Crypto,
            UniqueOpenError::InvalidRecord(_)=>Error::Invalid,
            UniqueOpenError::Duplicate=>Error::Duplicate,
            UniqueOpenError::Retired=>Error::Stale,
        })?;
        let observed=self.health_origin.elapsed().as_nanos().min(u128::from(u64::MAX)) as u64;
        if opened.kind==0{
            read_game_health(opened.payload,observed,&self.health)?;
            return Ok(None)
        }
        if opened.kind!=1{return Err(Error::Invalid)}
        let (id,payload)=wbd_codec::decode_game(opened.payload,self.inner_mtu+16)
            .map_err(|_|Error::Invalid)?;
        if payload.len()>self.inner_mtu{return Err(Error::Invalid)}
        if observed.saturating_sub(self.last_health_record_ns)>=500_000_000{
            self.health.record_batch(observed,0,None);
            self.last_health_record_ns=observed;
        }
        self.prepare_opened_receive(lane_key,id,payload)
    }
    /// Only callable after authentic original lane AEAD/replay open.
    pub(crate) fn prepare_opened_receive(&mut self,lane_key:LaneKey,
        id:LogicalPacketId,payload:&[u8])
        ->Result<Option<PreparedGameDelivery>,Error>{
        if self.stopped{return Err(Error::Stopped)}
        #[cfg(feature="fec2_product_record")]
        if self.fec.is_some(){return Err(Error::Invalid)}
        if payload.len()>self.inner_mtu{return Err(Error::Invalid)}
        // Duplicate/stale after AEAD, BEFORE allocating the owned frame.
        match self.rx.first_delivery_candidate(self.rx_scope,lane_key,id){
            Ok(true)=>{},
            Ok(false)=>return Ok(None),
            Err(e)=>return Err(Error::Game(e)),
        }
        if self.pending.contains(&id){return Ok(None)}
        if self.pending.len()>=self.lane_count{
            return Err(Error::Capacity)
        }
        let mut slab=self.arena.allocate().map_err(|_|Error::Capacity)?;
        slab.writable()[14..14+payload.len()].copy_from_slice(payload);
        self.pending.push(id);
        Ok(Some(PreparedGameDelivery{id,lane:lane_key,len:payload.len(),slab}))
    }
    /// The call site MUST invoke this only after the real kernel TUN write
    /// resolves; unsuccessful writes release reservation without touching the
    /// logical delivery window. A future authenticated lane copy may retry.
    pub(crate) fn finish_receive(&mut self,prepared:PreparedGameDelivery,
        tun_written:bool)->Result<(),Error>{
        let Some(at)=self.pending.iter().position(|id|*id==prepared.id)
            else{return Err(Error::Invalid)};
        self.pending.swap_remove(at);
        if !tun_written{return Ok(())}
        self.rx.first_delivery(self.rx_scope,prepared.lane,
            prepared.id,prepared.slab).map(|_|())
            .map_err(|(e,_)|Error::Game(e))
    }
    #[cfg(feature="fec2_product_record")]
    pub(crate) fn fec_active(&self)->bool{self.fec.is_some()}
    /// This is the Linux Game+FEC receive entry, distinct from Game OFF.
    /// All AEAD/replay and logical ID precheck happen before one shared FEC
    /// decoder; a bounded batch is handed to the M4 writer without a lock.
    #[cfg(feature="fec2_product_record")]
    pub(crate) fn prepare_fec_batch(&mut self,lane_key:LaneKey,
        wire:&mut [u8],now:MonoNs)->Result<Option<PreparedGameFecBatch>,Error>{
        if self.stopped||self.fec.is_none(){return Err(Error::Invalid)}
        let lane=self.lanes.iter_mut().find(|l|l.key==lane_key)
            .ok_or(Error::Unauthorized)?;
        let opened=lane.rx.open_unique_in_place(wire).map_err(|e|match e{
            UniqueOpenError::InvalidRecord(CryptoError::Authentication)=>Error::Crypto,
            UniqueOpenError::InvalidRecord(_)=>Error::Invalid,
            UniqueOpenError::Duplicate=>Error::Duplicate,
            UniqueOpenError::Retired=>Error::Stale,
        })?;
        let observed=self.health_origin.elapsed().as_nanos().min(u128::from(u64::MAX)) as u64;
        if opened.kind==0{
            read_game_health(opened.payload,observed,&self.health)?;
            return Ok(None)
        }
        if opened.kind!=1{return Err(Error::Invalid)}
        let (id,payload)=wbd_codec::decode_game(opened.payload,self.inner_mtu+16)
            .map_err(|_|Error::Invalid)?;
        if payload.len()>self.inner_mtu{return Err(Error::Invalid)}
        if observed.saturating_sub(self.last_health_record_ns)>=500_000_000{
            self.health.record_batch(observed,0,None);
            self.last_health_record_ns=observed;
        }
        self.prepare_opened_fec_batch(lane_key,id,payload,now)
    }
    /// Shared cross-lane GameRX and ONE FEC recovery owner. Only AEAD
    /// authenticated payloads are supplied by the unique RX worker.
    #[cfg(feature="fec2_product_record")]
    pub(crate) fn prepare_opened_fec_batch(&mut self,lane_key:LaneKey,
        id:LogicalPacketId,payload:&[u8],now:MonoNs)
        ->Result<Option<PreparedGameFecBatch>,Error>{
        if self.stopped||self.fec.is_none(){return Err(Error::Invalid)}
        if payload.len()>self.inner_mtu{return Err(Error::Invalid)}
        match self.rx.first_delivery_candidate(self.rx_scope,lane_key,id){
            Ok(true)=>{},
            Ok(false)=>return Ok(None),
            Err(e)=>return Err(Error::Game(e))
        }
        if self.pending.contains(&id){return Ok(None)}
        if self.pending.len()>=self.lane_count{return Err(Error::Capacity)}
        // Reserve GameRx commit slab BEFORE modifying inner FEC cache.
        let mut slab=self.arena.allocate().map_err(|_|Error::Capacity)?;
        slab.writable()[14..14+payload.len()].copy_from_slice(payload);
        let frames=self.fec.as_mut().unwrap().receive(payload,now)?;
        if frames.len()>16||frames.iter().any(|f|f.is_empty()||
                f.len()>self.inner_mtu.saturating_sub(15)){
            return Err(Error::Invalid)
        }
        self.pending.push(id);
        Ok(Some(PreparedGameFecBatch{id,lane:lane_key,slab,frames}))
    }
    #[cfg(feature="fec2_product_record")]
    pub(crate) fn finish_fec_batch(&mut self,batch:PreparedGameFecBatch,
        all_tun_writes_succeeded:bool)->Result<(),Error>{
        let Some(pos)=self.pending.iter().position(|id|*id==batch.id)
            else{return Err(Error::Invalid)};
        self.pending.swap_remove(pos);
        if !all_tun_writes_succeeded{return Ok(())}
        // Empty parity candidate also retires the authenticated Game symbol
        // after successful native decoder acceptance; no TUN write required.
        self.rx.first_delivery(self.rx_scope,batch.lane,
            batch.id,batch.slab).map(|_|())
            .map_err(|(e,_)|Error::Game(e))
    }
    /// Native/test stage of shared FEC RX after original lane AEAD/replay.
    /// Production TUN routing is added only with a bounded multi-delivery
    /// acknowledgment contract (not by calling ordinary prepare_receive).
    #[cfg(feature="fec2_product_record")]
    pub(crate) fn receive_fec_at(&mut self,lane_key:LaneKey,
        wire:&mut [u8],now:MonoNs)->Result<Vec<Vec<u8>>,Error>{
        if self.stopped||self.fec.is_none(){return Err(Error::Invalid)}
        let lane=self.lanes.iter_mut().find(|l|l.key==lane_key)
            .ok_or(Error::Unauthorized)?;
        let opened=lane.rx.open_unique_in_place(wire).map_err(|e|match e{
            UniqueOpenError::InvalidRecord(CryptoError::Authentication)=>Error::Crypto,
            UniqueOpenError::InvalidRecord(_)=>Error::Invalid,
            UniqueOpenError::Duplicate=>Error::Duplicate,
            UniqueOpenError::Retired=>Error::Stale
        })?;
        let observed=self.health_origin.elapsed().as_nanos().min(u128::from(u64::MAX)) as u64;
        if opened.kind==0{
            read_game_health(opened.payload,observed,&self.health)?;
            return Ok(Vec::new())
        }
        if opened.kind!=1{return Err(Error::Invalid)}
        let (id,payload)=wbd_codec::decode_game(opened.payload,self.inner_mtu+16)
            .map_err(|_|Error::Invalid)?;
        if payload.len()>self.inner_mtu{return Err(Error::Invalid)}
        if observed.saturating_sub(self.last_health_record_ns)>=500_000_000{
            self.health.record_batch(observed,0,None);
            self.last_health_record_ns=observed;
        }
        match self.rx.first_delivery_candidate(self.rx_scope,lane_key,id){
            Ok(true)=>{},
            Ok(false)=>return Ok(Vec::new()),
            Err(e)=>return Err(Error::Game(e)),
        }
        // Transactional admission: malformed FEC must not mark logical
        // Game ID as delivered. Before enabling real TUN writes, FEC symbol
        // and individual restored source commits need a shared owner fence.
        let restored=self.fec.as_mut().unwrap().receive(payload,now)?;
        let mut loan=self.arena.allocate().map_err(|_|Error::Capacity)?;
        loan.writable()[14..14+payload.len()].copy_from_slice(payload);
        match self.rx.first_delivery(self.rx_scope,lane_key,id,loan){
            Ok(_)=>Ok(restored),
            Err((GameError::Duplicate,_))=>Ok(Vec::new()),
            Err((e,_))=>Err(Error::Game(e))
        }
    }
    /// In-memory test/adapter path: the caller accepts the payload as the
    /// delivery boundary. The live Linux worker uses prepare + TUN + finish.
    pub(crate) fn receive(&mut self,lane_key:LaneKey,wire:&mut [u8])
        ->Result<Option<Vec<u8>>,Error>{
        let Some(mut prepared)=self.prepare_receive(lane_key,wire)?
            else{return Ok(None)};
        let result=prepared.payload().to_vec();
        self.finish_receive(prepared,true)?;
        Ok(Some(result))
    }
    fn stop(&mut self){
        if self.stopped{return}
        self.stopped=true;
        self.pending.clear();
        #[cfg(feature="fec2_product_record")]
        if let Some(f)=self.fec.as_mut(){f.stop()}
        self.rx.stop();self.arena.stop();self.arena.drain_returns();
    }
}
pub struct GameAdapter{
    tx:GameTx,rx_owner:Arc<Mutex<GameReceiveOwner>>,
    lanes:Vec<TxLane>,arena:Arena,stopped:bool,inner_mtu:usize,
    wire_scratch:[u8;2048],
    health_origin:Instant,health:Arc<AuthenticatedActivity>,
    #[cfg(feature="fec2_product_record")]
    fec:Option<GameFecTx>,
}
impl GameAdapter{
    /// Caller MUST independently check Go TLS feature, KDF, lane owner and
    /// epoch. This constructor does not authorize a public mode.
    pub fn new(tx_scope:GameScope,rx_scope:GameScope,
        materials:Vec<ScopedKeys>,suite:RecordSuite)->Result<Self,Error>{
        if !matches!(materials.len(),2|4)||tx_scope.direction!=FlowDirection::Tx||
            rx_scope.direction!=FlowDirection::Rx||
            tx_scope.tunnel!=rx_scope.tunnel||tx_scope.epoch!=rx_scope.epoch||
            tx_scope.epoch==[0;16]{return Err(Error::Unauthorized)}
        let mut infos=Vec::new();let mut lanes=Vec::new();
        let mut rx_lanes=Vec::new();
        let mut identities=Vec::new();
        let mut inner_mtu=2048usize;
        for m in materials {
            if m.lane.key.tunnel!=tx_scope.tunnel||
                m.lane.key.generation==0||
                m.lane.mss<64||m.lane.mss>2048||
                identities.iter().any(|(key,k,iv,hp):&(LaneKey,[u8;32],[u8;12],[u8;32])|
                    *key==m.lane.key||
                    (*k==m.tx.aead_key&&*iv==m.tx.iv&&*hp==m.tx.hp_key)){
                return Err(Error::Unauthorized)
            }
            identities.push((m.lane.key,m.tx.aead_key,m.tx.iv,m.tx.hp_key));
            // Record31 + logical Game16. This also keeps the 14B arena
            // prefix within the existing2048 slab; no larger hot allocation.
            inner_mtu=inner_mtu.min(m.lane.mss-31-16);
            let tx=LaneTxCrypto::new_for_suite(m.tx,m.lane.mss,suite)
                .map_err(|_|Error::Crypto)?;
            let rx=ReplayProtectedLaneRx::new_for_suite(m.rx,m.lane.mss,
                suite,ReplayWindowConfig{pn_per_second:2000,
                    cache_horizon_ms:200,fec_horizon_ms:200,rtt_ms:100,
                    metadata_budget_bytes:131072}).map_err(|_|Error::Crypto)?;
            infos.push(m.lane);
            lanes.push(TxLane{key:m.lane.key,tx});
            rx_lanes.push(RxLane{key:m.lane.key,rx});
        }
        let txsnap=ActiveLaneSnapshot::new(tx_scope,infos.clone())
            .ok_or(Error::Unauthorized)?;
        let rxsnap=ActiveLaneSnapshot::new(rx_scope,infos)
            .ok_or(Error::Unauthorized)?;
        let tx=GameTx::new(txsnap,GameLimits{jobs:128,
            logical_bytes:256*1024,lane_slots:64,lane_bytes:128*1024,
            max_age_ns:5_000_000}).ok_or(Error::Invalid)?;
        let rx=GameRx::new(rxsnap,RxLimits{
            delivered_window:4096,open_blocks:64,open_bytes:256*1024
        }).ok_or(Error::Invalid)?;
        // Independent bounded arenas avoid TX slab capacity making RX stall.
        // Generation and scope remain checked by the authenticated lane owner.
        let arena=Arena::new(905,256,2048,256,1024*1024)
            .map_err(|_|Error::Capacity)?;
        let rx_arena=Arena::new(906,256,2048,256,1024*1024)
            .map_err(|_|Error::Capacity)?;
        let lane_count=rx_lanes.len();
        let health_origin=Instant::now();
        let health=Arc::new(AuthenticatedActivity::default());
        let rx_owner=Arc::new(Mutex::new(GameReceiveOwner{
            rx,rx_scope,lanes:rx_lanes,arena:rx_arena,stopped:false,inner_mtu,lane_count,
            pending:Vec::with_capacity(lane_count),
            health_origin,health:Arc::clone(&health),last_health_record_ns:0,
            #[cfg(feature="fec2_product_record")]
            fec:None
        }));
        Ok(Self{tx,rx_owner,lanes,arena,stopped:false,inner_mtu,
            wire_scratch:[0u8;2048],
            health_origin,health,
            #[cfg(feature="fec2_product_record")]
            fec:None})
    }
    /// The only prospective Go TLS→Game adapter construction boundary.
    /// The Go caller MUST have run its private 2/4 original TLS ColdSnapshot
    /// verification on the same live sessions. Input bytes alone are NOT
    /// authentication; do not export this as a public installer or enable
    /// Game production using this scoped composition.
    pub(crate) fn from_private_original_go_tls(
        cold:Vec<UntrustedColdV4>,server:bool,owner_tunnel:TunnelKey,
        generation:u32,
    )->Result<Self,Error>{
        let n=cold.len();
        if !matches!(n,2|4)||owner_tunnel.slot==0||
            owner_tunnel.generation==0||generation==0 {
            return Err(Error::Unauthorized)
        }
        let first=cold[0].identity();
        if first.server!=server || first.logical_epoch==[0;16]{
            return Err(Error::Unauthorized)
        }
        let suite=RecordSuite::try_from(first.cipher)
            .map_err(|_|Error::Unauthorized)?;
        let mut indexed:Vec<Option<ScopedKeys>>=
            (0..n).map(|_|None).collect();
        let mut incarnations=Vec::new();
        let mut all_materials=Vec::new();
        for b in &cold {
            let id=b.identity();
            if id.server!=server||id.tunnel_id!=first.tunnel_id||
                id.logical_epoch!=first.logical_epoch||
                id.principal_hash!=first.principal_hash||
                id.cipher!=first.cipher||
                id.client_limit!=first.client_limit||
                id.server_limit!=first.server_limit||
                id.go_lane_id==0||usize::from(id.go_lane_id)>n||
                indexed[usize::from(id.go_lane_id)-1].is_some()||
                incarnations.contains(&id.incarnation){
                return Err(Error::Unauthorized)
            }
            let (c2s,s2c)=b.internal_direction_keys();
            // DirectionKeys intentionally does not implement PartialEq
            // (crypto material must not be casually compared). This private
            // TLS lane admission checks exact exporter bytes explicitly.
            let same=|a:&DirectionKeys,b:&DirectionKeys|
                a.aead_key==b.aead_key&&a.iv==b.iv&&a.hp_key==b.hp_key;
            if same(&c2s,&s2c) ||
               all_materials.iter().any(|old:&([u8;32],[u8;12],[u8;32])|{
                   let match_dir=|d:&DirectionKeys|
                       old.0==d.aead_key&&old.1==d.iv&&old.2==d.hp_key;
                   match_dir(&c2s)||match_dir(&s2c)
               }) {
                return Err(Error::Unauthorized)
            }
            // Retain immutable comparable bytes only, never move the
            // non-Copy key owners before constructing Tx/Rx AEAD sessions.
            all_materials.push((c2s.aead_key,c2s.iv,c2s.hp_key));
            all_materials.push((s2c.aead_key,s2c.iv,s2c.hp_key));
            incarnations.push(id.incarnation);
            let mss=id.client_limit.min(id.server_limit).min(2048);
            if mss<64{return Err(Error::Invalid)}
            let (tx,rx)=if server{(s2c,c2s)}else{(c2s,s2c)};
            indexed[usize::from(id.go_lane_id)-1]=Some(ScopedKeys{
                lane:QualifiedLane{key:LaneKey{tunnel:owner_tunnel,
                    slot:u32::from(id.go_lane_id),generation},mss:usize::from(mss)},
                tx,rx,
            });
        }
        let material=indexed.into_iter()
            .collect::<Option<Vec<_>>>().ok_or(Error::Unauthorized)?;
        let tx_scope=GameScope{
            tunnel:owner_tunnel,epoch:first.logical_epoch,
            direction:FlowDirection::Tx
        };
        let rx_scope=GameScope{direction:FlowDirection::Rx,..tx_scope};
        Self::new(tx_scope,rx_scope,material,suite)
    }
    pub fn counters(&self)->GameCounters{self.tx.counters()}
    pub(crate) fn inner_mtu(&self)->usize{self.inner_mtu}
    pub(crate) fn health_context(&self)->(Instant,Arc<AuthenticatedActivity>){
        (self.health_origin,Arc::clone(&self.health))
    }
    // Authenticated control kind0 shares per-lane AEAD/PN but never enters
    // Game logical source/FEC/TUN. This is a cold control packet at 15s.
    pub(crate) fn seal_native_health(&mut self,slot:u32,idle_ns:u64,
        wire:&mut [u8])->Result<(u64,usize),Error>{
        if self.stopped{return Err(Error::Stopped)}
        let idx=slot.checked_sub(1).and_then(|v|usize::try_from(v).ok())
            .filter(|&v|v<self.lanes.len()).ok_or(Error::Unauthorized)?;
        let body=encode_authenticated_health_live(idle_ns,None,None,
            wire.len().saturating_sub(31)).map_err(|_|Error::Invalid)?;
        if 14+body.len()>wire.len(){return Err(Error::Invalid)}
        wire[14..14+body.len()].copy_from_slice(&body);
        self.lanes[idx].tx.seal_in_place(0,wire,body.len(),0)
            .map_err(|_|Error::Crypto)
    }
    pub(crate) fn receiver_handle(&self)->Arc<Mutex<GameReceiveOwner>>{
        Arc::clone(&self.rx_owner)
    }
    pub(crate) fn has_game_fec(&self)->bool{
        #[cfg(feature="fec2_product_record")]
        {self.fec.is_some()}
        #[cfg(not(feature="fec2_product_record"))]
        {false}
    }
    /// Only the original Go TLS-protected BOTH-endpoint fixed profile may
    /// call this BEFORE the network workers start. Game Auto is excluded.
    /// TX and RX FEC remain independent owners, both use one logical FEC
    /// state per direction and still retain separate lane authentication.
    #[cfg(feature="fec2_product_record")]
    pub(crate) fn enable_game_fec(&mut self,profile:u8,server:bool)
        ->Result<(),Error>{
        if self.stopped||self.fec.is_some()||self.tx.in_use().0!=0{
            return Err(Error::Invalid)
        }
        let mut rx=self.rx_owner.lock().map_err(|_|Error::Stopped)?;
        if rx.stopped||rx.fec.is_some()||!rx.pending.is_empty(){
            return Err(Error::Invalid)
        }
        let scope=VerifiedReceiveEpoch{
            generation:rx.rx_scope.tunnel.generation,
            epoch:rx.rx_scope.epoch,negotiated_features:7,
            direction_s2c:!server,
        };
        let receiver=GameFecRx::new(profile,scope,self.inner_mtu)
            .ok_or(Error::Invalid)?;
        let sender=GameFecTx::new(profile,scope,self.inner_mtu,self.lanes.len())
            .ok_or(Error::Invalid)?;
        rx.fec=Some(receiver);
        self.fec=Some(sender);
        Ok(())
    }
    #[cfg(feature="fec2_product_record")]
    pub(crate) fn game_fec_counters(&self)
        ->Option<(GameFecCounters,crate::runtime::fec2_owner::OwnerReport)>{
        self.fec.as_ref().map(|f|(f.counters(),f.owner_report()))
    }
    #[cfg(feature="fec2_product_record")]
    pub(crate) fn game_fec_rx_counters(&self)->Option<GameFecCounters>{
        self.rx_owner.lock().ok()?.fec.as_ref().map(|f|f.counters())
    }
    /// Original single Game logical envelope (16B) contains either plaintext
    /// or one typed FEC source/parity symbol. All lane AEAD stays independent.
    fn enqueue(tx:&mut GameTx,arena:&mut Arena,bytes:&[u8],
        inner_mtu:usize,now:MonoNs)->Result<LogicalPacketId,Error>{
        if bytes.is_empty()||bytes.len()>inner_mtu{return Err(Error::Invalid)}
        let id=tx.next_packet().ok_or(Error::Stopped)?;
        let packet=wbd_codec::encode_game(id,bytes,inner_mtu+16)
            .map_err(|_|Error::Invalid)?;
        // Evict only overdue retained copies at the explicit Game4 capacity
        // boundary BEFORE borrowing a source slab. A fresh first cannot be
        // blocked simply because an old packet holds 60ms future duplicates.
        tx.reserve_game4_first(packet.len(),31+packet.len());
        let mut slab=arena.allocate().map_err(|_|Error::Capacity)?;
        let end=14+packet.len();
        slab.writable()[14..end].copy_from_slice(&packet);
        let offered=tx.offer(slab,14..end,Mode::Game,31+packet.len(),
            None,now).map_err(|(e,_)|Error::Game(e))?;
        if offered!=Some(id){return Err(Error::Invalid)}
        Ok(id)
    }
    #[cfg(feature="fec2_product_record")]
    pub(crate) fn poll_game_fec(&mut self,now:MonoNs)->Result<usize,Error>{
        if self.stopped{return Err(Error::Stopped)}
        let Some(fec)=self.fec.as_mut()else{return Ok(0)};
        let tx=&mut self.tx;
        let arena=&mut self.arena;
        let mtu=self.inner_mtu;
        let quiet=tx.in_use().0==0;
        fec.poll(now,quiet,|symbol|Self::enqueue(tx,arena,symbol,mtu,now))
    }
    pub fn configure_game4_stagger(&mut self)->Result<(),Error>{
        self.configure_game4_stagger_mode(1)
    }
    pub fn configure_game4_stagger_mode(&mut self,mode:u32)->Result<(),Error>{
        if mode!=1&&mode!=2{return Err(Error::Invalid)}
        if self.stopped||self.lanes.len()!=4{return Err(Error::Invalid)}
        #[cfg(feature="fec2_product_record")]
        // Game4 fixed FEC symbols are deep-copied into an independently
        // owned GameTx slab before the encoder can retire a block. Their
        // +60ms data-copy lifetime does NOT pin the encoder's source arena.
        let arena=Arena::new(905,4096,2048,4096,16*1024*1024)
            .map_err(|_|Error::Capacity)?;
        self.rx_owner.lock().map_err(|_|Error::Stopped)?.rx
            .widen_delivery_window_before_start(65536).map_err(Error::Game)?;
        let offsets=if mode==2{
            [0,4_000_000,50_000_000,140_000_000]
        }else{[0,4_000_000,20_000_000,60_000_000]};
        self.tx.configure_game4_stagger_offsets(offsets).map_err(Error::Game)?;
        #[cfg(feature="fec2_product_record")]
        {self.arena=arena;}
        Ok(())
    }
    pub fn game4_copy_schedule_mode(&self)->u32{self.tx.copy_schedule_mode()}
    pub fn game4_copy_schedule(&self)->Option<GameCounters>{
        self.tx.staggered().then_some(self.tx.counters())
    }
    pub fn game4_next_due_ns(&self)->Option<u64>{self.tx.next_due_ns()}
    pub(crate) fn game_fec_next_due_ns(&self,now:MonoNs)->Option<u64>{
        #[cfg(feature="fec2_product_record")]
        {self.fec.as_ref().and_then(|fec|fec.next_due_ns(now))}
        #[cfg(not(feature="fec2_product_record"))]
        {let _=now;None}
    }

    pub fn game4_stagger_enabled(&self)->bool{self.tx.staggered()}
    pub fn offer(&mut self,data:&[u8],now:MonoNs)->Result<LogicalPacketId,Error>{
        if self.stopped{return Err(Error::Stopped)}
        #[cfg(feature="fec2_product_record")]
        if let Some(fec)=self.fec.as_mut(){
            let tx=&mut self.tx;
            let arena=&mut self.arena;
            let mtu=self.inner_mtu;
            return fec.offer(data,now,|symbol|Self::enqueue(tx,arena,symbol,mtu,now))
        }
        Self::enqueue(&mut self.tx,&mut self.arena,data,self.inner_mtu,now)
    }
    /// Each ready lane gets a distinct AEAD nonce/PN and cipher buffer;
    /// network copy acknowledgement is supplied by the M0 kernel driver.
    /// Real Linux M4 kernel copy reports directly through drain().
    /// Windows original Go must FIRST stage immutable ciphertext, then
    /// report the actual Npcap syscall result by scoped Game logical ID.
    pub fn drain<F>(&mut self,now:MonoNs,kernel_copy:F)->usize
    where F:FnMut(LaneKey,LogicalPacketId,u64,&[u8])->bool{
        self.drain_dispatch(now,true,kernel_copy)
    }
    #[cfg(feature="fec2_product_record")]
    pub(crate) fn stage_for_windows_native<F>(&mut self,now:MonoNs,stage:F)->usize
    where F:FnMut(LaneKey,LogicalPacketId,u64,&[u8])->bool{
        self.drain_dispatch(now,false,stage)
    }
    fn drain_dispatch<F>(&mut self,now:MonoNs,
        copied_by_native_kernel:bool,mut kernel_copy:F)->usize
    where F:FnMut(LaneKey,LogicalPacketId,u64,&[u8])->bool{
        if self.stopped{return 0}
        let lanes=&mut self.lanes;
        let scratch=&mut self.wire_scratch;
        #[cfg(feature="fec2_product_record")]
        let fec=&mut self.fec;
        let processed=self.tx.drain_ready(now,32,|view|{
            let Some(id)=view.logical_id else{return DispatchOutcome::PressureDrop};
            let Some(lane)=lanes.iter_mut().find(|l|l.key==view.lane)
            else{return DispatchOutcome::PressureDrop};
            let len=view.common_payload.len();
            let Some(end)=31usize.checked_add(len)else{
                return DispatchOutcome::PressureDrop
            };
            if end>scratch.len(){return DispatchOutcome::PressureDrop}
            let wire=&mut scratch[..end];
            wire[14..14+len].copy_from_slice(view.common_payload);
            let Ok((pn,n))=lane.tx.seal_in_place(1,wire,len,0)
            else{return DispatchOutcome::PressureDrop};
            if kernel_copy(view.lane,id,pn,&wire[..n]){
                #[cfg(feature="fec2_product_record")]
                if copied_by_native_kernel {
                    if let Some(f)=fec.as_mut(){f.copied(id);}
                }
                DispatchOutcome::Accepted
            }else{DispatchOutcome::PressureDrop}
        });
        #[cfg(feature="fec2_product_record")]
        if copied_by_native_kernel {
            if let Some(f)=self.fec.as_mut(){
                f.settle_when_quiet(self.tx.in_use().0==0);
            }
        }
        #[cfg(not(feature="fec2_product_record"))]
        let _=copied_by_native_kernel;
        processed
    }
    #[cfg(feature="fec2_product_record")]
    pub(crate) fn note_windows_native_m4_copy(&mut self,id:LogicalPacketId){
        if let Some(f)=self.fec.as_mut(){f.copied(id);}
    }
    #[cfg(feature="fec2_product_record")]
    pub(crate) fn settle_windows_native_m4_batch(&mut self){
        if let Some(f)=self.fec.as_mut(){
            f.settle_when_quiet(self.tx.in_use().0==0);
        }
    }
    /// Synchronous adapter callers preserve the original API. The Linux
    /// worker instead keeps the RX handle once and NEVER takes TX mutex.
    pub fn receive(&mut self,lane_key:LaneKey,mut wire:Vec<u8>)
        ->Result<Option<Vec<u8>>,Error>{
        if self.stopped{return Err(Error::Stopped)}
        self.rx_owner.lock().map_err(|_|Error::Stopped)?
            .receive(lane_key,wire.as_mut_slice())
    }
    pub fn stop(&mut self){
        if self.stopped{return}
        self.stopped=true;
        #[cfg(feature="fec2_product_record")]
        if let Some(f)=self.fec.as_mut(){f.stop()}
        self.tx.stop();self.arena.stop();self.arena.drain_returns();
        if let Ok(mut receiver)=self.rx_owner.lock(){receiver.stop();}
    }
}
#[cfg(test)]
mod tests{
    use super::*;
    use wbd_types::TunnelKey;
    fn keys(n:u8)->DirectionKeys{DirectionKeys{
        aead_key:[n;32],iv:[n.wrapping_add(11);12],hp_key:[n.wrapping_add(21);32]}}
    fn build(n:usize)->GameAdapter{
        let tx=GameScope{tunnel:TunnelKey{slot:4,generation:7},
            epoch:[7;16],direction:FlowDirection::Tx};
        let rx=GameScope{direction:FlowDirection::Rx,..tx};
        GameAdapter::new(tx,rx,(0..n).map(|i|ScopedKeys{
            lane:QualifiedLane{key:LaneKey{tunnel:tx.tunnel,slot:(i+1) as u32,
                generation:7},mss:1400},
            tx:keys((i+1) as u8),rx:keys((i+1) as u8)
        }).collect(),RecordSuite::ChaCha20Poly1305).unwrap()
    }
    #[test]
    fn game_health_kind0_has_authenticated_PN_but_no_game_delivery(){
        let mut sender=build(2);
        let (origin,activity)=sender.health_context();
        let mut wire=[0u8;512];
        let (_,size)=sender.seal_native_health(1,20_000_000_000,&mut wire).unwrap();
        let receiver=sender.receiver_handle();
        let mut guard=receiver.lock().unwrap();
        let lane=LaneKey{tunnel:TunnelKey{slot:4,generation:7},slot:1,generation:7};
        assert!(guard.prepare_receive(lane,&mut wire[..size]).unwrap().is_none());
        let mut clock=crate::v4_native_health::HealthClock::new(
            crate::v4_native_health::HealthPolicy::default_connected(),0);
        activity.absorb(&mut clock);
        assert!(!clock.unhealthy(origin.elapsed().as_nanos() as u64));
        assert!(guard.pending.is_empty());
    }
    #[test]
    fn game4_stagger_due_fifo_source_immediate_and_tail_not_5ms_expired(){
        let mut game=build(4);
        game.configure_game4_stagger().unwrap();
        assert!(game.game4_stagger_enabled());
        assert_eq!(game.game4_next_due_ns(),None);
        let start=1_000_000u64;
        let first=game.offer(&[0x42;128],MonoNs(start)).unwrap();
        assert_eq!(first.0,0);
        let mut observed=Vec::new();
        assert_eq!(game.drain(MonoNs(start),|lane,id,_,_|{
            observed.push((lane.slot,id.0));true
        }),1); // T0 first copy: zero intentional wait
        assert_eq!(game.drain(MonoNs(start+3_999_999),|_,_,_,_|true),0);
        assert_eq!(game.drain(MonoNs(start+4_000_000),|lane,id,_,_|{
            observed.push((lane.slot,id.0));true
        }),1);
        assert_eq!(game.drain(MonoNs(start+19_999_999),|_,_,_,_|true),0);
        assert_eq!(game.drain(MonoNs(start+20_000_000),|lane,id,_,_|{
            observed.push((lane.slot,id.0));true
        }),1);
        assert_eq!(game.drain(MonoNs(start+59_999_999),|_,_,_,_|true),0);
        assert_eq!(game.drain(MonoNs(start+60_000_000),|lane,id,_,_|{
            observed.push((lane.slot,id.0));true
        }),1);
        assert_eq!(observed.len(),4);
        let proof=game.game4_copy_schedule().unwrap();
        assert_eq!(proof.scheduled,[1;4]);
        assert_eq!(proof.sent,[1;4]);
        assert_eq!(proof.abandoned,[0;4]);
        assert_eq!(game.game4_next_due_ns(),None);
        game.stop();
    }
    #[test]
    fn game4_stagger_wide_50_140_preserves_immediate_source_and_bounded_tail(){
        let mut game=build(4);
        game.configure_game4_stagger_mode(2).unwrap();
        assert_eq!(game.game4_copy_schedule_mode(),2);
        let t=1_000_000u64;
        let id=game.offer(&[0x41;128],MonoNs(t)).unwrap();
        let mut got=Vec::new();
        assert_eq!(game.drain(MonoNs(t),|lane,copy,_,_|{
            got.push((lane.slot,copy.0));true
        }),1);
        for (before,due) in [(3_999_999,4_000_000),
                             (49_999_999,50_000_000),
                             (139_999_999,140_000_000)]{
            assert_eq!(game.drain(MonoNs(t+before),|_,_,_,_|true),0);
            assert_eq!(game.drain(MonoNs(t+due),|lane,copy,_,_|{
                got.push((lane.slot,copy.0));true
            }),1);
        }
        assert_eq!(got,vec![(1,id.0),(2,id.0),(3,id.0),(4,id.0)]);
        let proof=game.game4_copy_schedule().unwrap();
        assert_eq!(proof.scheduled,[1;4]);
        assert_eq!(proof.sent,[1;4]);
        assert_eq!(proof.abandoned,[0;4]);
        assert_eq!(game.game4_next_due_ns(),None);
        game.stop();
        assert_eq!(game.tx.in_use().0,0);
    }
    #[test]
    fn game4_stagger_lanes_fifo_burst_capacity_and_stop(){
        let mut game=build(4);
        game.configure_game4_stagger().unwrap();
        // Multiple overlapping jobs share ONE arena source apiece.
        for i in 0..32u8{
            game.offer(&[i;128],MonoNs(1_000_000+u64::from(i)*1000)).unwrap();
        }
        let mut last=[None;4];
        for now in [1_031_000,5_031_000,21_031_000,61_031_000]{
            game.drain(MonoNs(now),|lane,id,_,_|{
                let pos=(lane.slot-1) as usize;
                if let Some(prev)=last[pos]{assert!(id.0>prev);}
                last[pos]=Some(id.0);true
            });
        }
        assert_eq!(game.game4_copy_schedule().unwrap().abandoned,[0;4]);
        // Stop cancels a pending future copy; it must never outlive generation.
        game.offer(&[0x55;128],MonoNs(70_000_000)).unwrap();
        game.drain(MonoNs(70_000_000),|_,_,_,_|true);
        game.stop();
        assert_eq!(game.drain(MonoNs(150_000_000),|_,_,_,_|true),0);
    }
    #[test]
    fn game4_stagger_capacity_evicts_old_refs_to_admit_new_first(){
        let mut game=build(4);
        game.configure_game4_stagger().unwrap();
        // No draining: fill the exact 4096-job and backing slab cap.
        // Only queued older refs can be canceled to admit the new first.
        for i in 0..4096u32{
            let id=game.offer(&[(i&255) as u8;64],MonoNs(1_000_000)).unwrap();
            assert_eq!(id.0,i as u64);
        }
        assert_eq!(game.tx.in_use().0,4096);
        let id=game.offer(&[0x91;64],MonoNs(1_000_000)).unwrap();
        assert_eq!(id.0,4096);
        let c=game.game4_copy_schedule().unwrap();
        assert_eq!(c.scheduled,[4097;4]);
        assert!(c.abandoned.iter().sum::<u64>()>=4);
        assert_eq!(game.tx.in_use().0,4096);
        let mut fresh_first=false;
        // Fair bounded turns progress all lane1 first copies; keep now=T0
        // to isolate capacity vs due scheduling, no wall clock sleeps.
        for _ in 0..129{
            game.drain(MonoNs(1_000_000),|lane,pid,_,_|{
                if pid.0==4096&&lane.slot==1{fresh_first=true;}
                true
            });
        }
        assert!(fresh_first);
        game.stop();
        assert_eq!(game.tx.in_use().0,0);
    }
    #[cfg(feature="fec2_product_record")]
    #[test]
    fn game4_stagger_fixed6_parity_credit_ignores_unrelated_source_ids(){
        let mut tx=build(4);
        tx.enable_game_fec(6,false).unwrap();
        tx.configure_game4_stagger().unwrap();
        for i in 0..16u8{
            let t=MonoNs(1_000+u64::from(i));
            tx.offer(&[i;128],t).unwrap();
            tx.drain(t,|lane,_,_,_|lane.slot==1);
        }
        assert!(tx.poll_game_fec(MonoNs(1_030)).unwrap()>0);
        // Parity M4 receipts are still outstanding. The scheduler must
        // wait for the bounded flight expiry or an actual kernel-copy wake,
        // NOT spin on an already matured source block deadline.
        let waiting=tx.game_fec_next_due_ns(MonoNs(1_031)).unwrap();
        assert!(waiting>1_031,"uncredited parity flight must not spin");
        tx.drain(MonoNs(1_031),|_,_,_,_|true);
        let credited=tx.game_fec_counters().unwrap().0.parity_kernel_copied;
        assert!(credited>0);
        // Source IDs later than the active parity quantum must not
        // inflate the parity credit, nor prevent the next real quantum.
        for i in 0..4u8{
            tx.offer(&[i;128],MonoNs(1_032+u64::from(i))).unwrap();
        }
        tx.drain(MonoNs(1_036),|_,_,_,_|true);
        assert_eq!(tx.game_fec_counters().unwrap().0.parity_kernel_copied,credited);
        assert!(tx.poll_game_fec(MonoNs(1_037)).unwrap()>0);
        tx.stop();
        assert_eq!(tx.game_fec_counters().unwrap().1.charged_bytes,0);
    }
    #[cfg(feature="fec2_product_record")]
    #[test]
    fn w137_sparse_fixed6_fec_close_preempts_game4_20ms_copy(){
        let mut game=build(4);
        game.enable_game_fec(6,false).unwrap();
        game.configure_game4_stagger().unwrap();
        let start=1_000_000_000u64;
        let original=game.offer(&[0x31;128],MonoNs(start)).unwrap();
        // Genuine first business copy goes immediately, second at 4ms.
        assert_eq!(game.drain(MonoNs(start),|lane,_,_,_|{
            assert_eq!(lane.slot,1);true
        }),1);
        assert_eq!(game.drain(MonoNs(start+4_000_000),|lane,_,_,_|{
            assert_eq!(lane.slot,2);true
        }),1);
        let next_copy=game.game4_next_due_ns().unwrap();
        assert_eq!(next_copy,start+20_000_000);
        let fec_due=game.game_fec_next_due_ns(MonoNs(start+4_000_000))
            .expect("one sparse source must retain FEC close deadline");
        assert!(fec_due>start && fec_due<next_copy,
            "sparse FEC must close before Game4 20ms copy");
        let before=game.game_fec_counters().unwrap().0.parity_offered;
        assert_eq!(game.poll_game_fec(MonoNs(fec_due-1)).unwrap(),0);
        assert!(game.poll_game_fec(MonoNs(fec_due)).unwrap()>0,
            "one source group must close at its original owner deadline");
        assert!(game.game_fec_counters().unwrap().0.parity_offered>before);
        // No copy schedule reconfiguration: later 20/60ms positions remain.
        game.drain(MonoNs(fec_due),|_,_,_,_|true);
        let mut original_third=false;
        for _ in 0..4{
            game.drain(MonoNs(start+20_000_000),|lane,id,_,_|{
                if id==original&&lane.slot==3{original_third=true;}
                true
            });
        }
        assert!(original_third,
            "repair parity must not steal or reschedule the original 20ms copy");
        game.stop();
        assert_eq!(game.game_fec_counters().unwrap().1.charged_bytes,0);
    }
    #[cfg(feature="fec2_product_record")]
    #[test]
    fn game4_fixed6_stagger_parity_does_not_wait_for_all_60ms_copies(){
        let mut game=build(4);
        // Original public config order: authenticated fixed6 first, then
        // apply default 0/4/20/60ms copies before the M4 kernel starts.
        game.enable_game_fec(6,false).unwrap();
        game.configure_game4_stagger().unwrap();
        for i in 0..16u8{
            let now=MonoNs(100+u64::from(i));
            game.offer(&[i;128],now).unwrap();
            // Only immediate physical lane1 should dispatch so far.
            assert_eq!(game.drain(now,|lane,_,_,_|{
                assert_eq!(lane.slot,1);true
            }),1);
        }
        // The other three ranks still hold their own GameTx source slabs,
        // so the global GameTx queue CANNOT be empty under steady load.
        assert!(game.tx.in_use().0>=16);
        let first=game.poll_game_fec(MonoNs(120)).unwrap();
        assert!(first>0,"fixed6 first quantum must issue");
        let dispatched=game.drain(MonoNs(121),|lane,_,_,_|{
            assert_eq!(lane.slot,1);true
        });
        assert!(dispatched>0);
        let proof=game.game_fec_counters().unwrap().0;
        assert!(proof.parity_kernel_copied>0);
        assert!(game.tx.in_use().0>=16);
        // This is the previously blocked case: a second parity quantum
        // must progress although the 60ms GameTx copy tails remain queued.
        let second=game.poll_game_fec(MonoNs(122)).unwrap();
        assert!(second>0,"parity blocked by unrelated delayed GameTx refs");
        game.drain(MonoNs(123),|_,_,_,_|true);
        // T+60ms is not misinterpreted as a 5ms-old source deadline.
        game.drain(MonoNs(60_000_200),|_,_,_,_|true);
        assert!(game.game4_copy_schedule().unwrap().sent[3]>0);
        game.stop();
        assert_eq!(game.tx.in_use().0,0);
        assert_eq!(game.game_fec_counters().unwrap().1.charged_bytes,0);
    }
    #[cfg(feature="fec2_product_record")]
    #[test]
    fn w98_shared_fixed_native_m4_batch_commits_all_restored_after_success(){
        for n in [2,4]{
            let mut tx=build(n);
            let mut rx=build(n);
            tx.enable_game_fec(6,false).unwrap();
            rx.enable_game_fec(6,true).unwrap();
            let mut delivered=Vec::new();
            for i in 0..16u8{
                let msg=vec![i;128];
                let now=MonoNs(100+u64::from(i));
                tx.offer(&msg,now).unwrap();
                tx.drain(now,|lane,id,_,wire|{
                    if id.0>=2&&lane.slot==1{
                        let mut packet=wire.to_vec();
                        let recv=rx.receiver_handle();
                        let mut owner=recv.lock().unwrap();
                        let batch=owner.prepare_fec_batch(lane,&mut packet,now)
                            .unwrap().unwrap();
                        delivered.extend(batch.frames().iter().cloned());
                        owner.finish_fec_batch(batch,true).unwrap();
                    }
                    true
                });
            }
            assert_eq!(delivered.len(),14);
            assert_eq!(tx.poll_game_fec(MonoNs(120)).unwrap(),4);
            tx.drain(MonoNs(121),|lane,_,_,wire|{
                if lane.slot==1{
                    let mut packet=wire.to_vec();
                    let recv=rx.receiver_handle();
                    let mut owner=recv.lock().unwrap();
                    if let Some(batch)=owner.prepare_fec_batch(lane,&mut packet,MonoNs(121))
                        .unwrap(){
                        delivered.extend(batch.frames().iter().cloned());
                        owner.finish_fec_batch(batch,true).unwrap();
                    }
                }
                true
            });
            assert_eq!(delivered.len(),16);
            assert_eq!(delivered.iter().filter(|f|*f==&vec![0;128]).count(),1);
            assert_eq!(delivered.iter().filter(|f|*f==&vec![1;128]).count(),1);
            tx.stop();rx.stop();
        }
    }
    #[cfg(feature="fec2_product_record")]
    #[test]
    fn w98_game_fixed_split_tx_rx_shared_recovery_native_only(){
        for n in [2,4]{
            let mut tx=build(n);
            let mut rx=build(n);
            tx.enable_game_fec(6,false).unwrap();
            rx.enable_game_fec(6,true).unwrap();
            let mut delivered=Vec::new();
            for i in 0..16u8{
                let msg=vec![i;128];
                let now=MonoNs(100+u64::from(i));
                assert_eq!(tx.offer(&msg,now).unwrap().0,u64::from(i));
                tx.drain(now,|lane,id,_,wire|{
                    if id.0!=0&&lane.slot==1{
                        let mut packet=wire.to_vec();
                        let recv=rx.receiver_handle();
                        delivered.extend(recv.lock().unwrap()
                            .receive_fec_at(lane,&mut packet,now).unwrap());
                    }
                    true
                });
            }
            assert_eq!(delivered.len(),15);
            assert_eq!(tx.poll_game_fec(MonoNs(120)).unwrap(),4);
            tx.drain(MonoNs(121),|lane,_,_,wire|{
                if lane.slot==1{
                    let mut packet=wire.to_vec();
                    let recv=rx.receiver_handle();
                    delivered.extend(recv.lock().unwrap()
                        .receive_fec_at(lane,&mut packet,MonoNs(121)).unwrap());
                }
                true
            });
            assert_eq!(delivered.len(),16);
            assert_eq!(delivered.iter().filter(|v|*v==&vec![0;128]).count(),1);
            let stats=rx.game_fec_rx_counters().unwrap();
            assert_eq!(stats.recovered_candidate,1);
            assert_eq!(stats.source_first_candidate,15);
            assert!(tx.game_fec_counters().unwrap().0.parity_kernel_copied>0);
            tx.stop();rx.stop();
            assert_eq!(tx.game_fec_counters().unwrap().1.charged_bytes,0);
        }
    }
    #[cfg(feature="fec2_product_record")]
    #[test]
    fn w98_fec_pending_source_keeps_first_delivery_before_parity(){
        let mut tx=build(2);
        tx.enable_game_fec(6,false).unwrap();
        let frame=vec![1u8;128];
        assert_eq!(tx.offer(&frame,MonoNs(10)).unwrap().0,0);
        assert_eq!(tx.drain(MonoNs(11),|_,_,_,_|true),2);
        assert_eq!(tx.poll_game_fec(MonoNs(15)).unwrap(),0);
        tx.stop();
        assert!(matches!(tx.poll_game_fec(MonoNs(16)),Err(Error::Stopped)));
    }
    #[test]
    fn game_tun_write_failure_does_not_commit_logical_delivery(){
        for n in [2,4]{
            let mut game=build(n);
            game.offer(b"deliver-only-after-tun",MonoNs(1)).unwrap();
            let mut copies=Vec::new();
            game.drain(MonoNs(2),|lane,_,_,wire|{
                copies.push((lane,wire.to_vec()));true
            });
            let rx=game.receiver_handle();
            let mut receiver=rx.lock().unwrap();
            let (first_lane,mut first_wire)=copies.remove(0);
            let failed=receiver.prepare_receive(first_lane,&mut first_wire)
                .unwrap().unwrap();
            // Kernel write fails: the payload is NOT in the delivered bitmap.
            assert_eq!(receiver.pending.len(),1);
            receiver.finish_receive(failed,false).unwrap();
            assert!(receiver.pending.is_empty());
            let (other_lane,mut other_wire)=copies.remove(0);
            let mut alternate=receiver.prepare_receive(other_lane,&mut other_wire)
                .unwrap().expect("another independently authenticated lane may deliver");
            assert_eq!(alternate.payload(),b"deliver-only-after-tun");
            receiver.finish_receive(alternate,true).unwrap();
            assert!(receiver.pending.is_empty());
            // An additional authenticated lane is a true duplicate only
            // AFTER a successful write; every per-lane AEAD remains unique.
            if n==4{
                let (lane,mut wire)=copies.remove(0);
                assert!(receiver.prepare_receive(lane,&mut wire).unwrap().is_none());
            }
            drop(receiver);
            game.stop();
        }
    }
    #[test]
    fn w143_lane_opener_single_replay_owner_before_shared_tun_commit(){
        for n in [2,4]{
            let mut tx=build(n);
            let mut rx=build(n);
            let key=tx.offer(b"w143-lane-owned",MonoNs(1)).unwrap();
            let mut copies=Vec::new();
            assert_eq!(tx.drain(MonoNs(2),|lane,_,_,wire|{
                copies.push((lane,wire.to_vec()));true
            }),n);
            let owner=rx.receiver_handle();
            let (lane0,mut wire0)=copies.remove(0);
            let (lane1,mut wire1)=copies.remove(0);
            let mut opener0=owner.lock().unwrap().take_lane_for_worker(lane0)
                .unwrap();
            let mut opener1=owner.lock().unwrap().take_lane_for_worker(lane1)
                .unwrap();
            assert!(matches!(owner.lock().unwrap().take_lane_for_worker(lane0),
                Err(Error::Unauthorized)),"same replay state cannot be detached twice");
            let mut broken=wire0.clone();
            *broken.last_mut().unwrap()^=1;
            assert!(matches!(opener0.open(&mut broken),Err(Error::Crypto)));
            let mut sealed_replay=wire0.clone();
            let (id,payload)=opener0.open(&mut wire0).unwrap().unwrap();
            assert_eq!(id,key);
            let mut candidate=owner.lock().unwrap()
                .prepare_opened_receive(lane0,id,payload).unwrap().unwrap();
            assert_eq!(candidate.payload(),b"w143-lane-owned");
            assert!(matches!(opener0.open(&mut sealed_replay),Err(Error::Duplicate)),
                "replay MUST present unchanged sealed ciphertext");
            let (other_id,other_payload)=opener1.open(&mut wire1).unwrap().unwrap();
            assert_eq!(other_id,key);
            assert!(owner.lock().unwrap().prepare_opened_receive(
                lane1,other_id,other_payload).unwrap().is_none(),
                "pending source suppresses parallel cross-lane delivery");
            owner.lock().unwrap().finish_receive(candidate,false).unwrap();
            if n==4 {
                let (lane2,mut wire2)=copies.remove(0);
                let mut opener2=owner.lock().unwrap().take_lane_for_worker(lane2)
                    .unwrap();
                let (third_id,third_payload)=opener2.open(&mut wire2).unwrap().unwrap();
                let received=owner.lock().unwrap().prepare_opened_receive(
                    lane2,third_id,third_payload).unwrap().unwrap();
                owner.lock().unwrap().finish_receive(received,true).unwrap();
                let (lane3,mut wire3)=copies.remove(0);
                let mut opener3=owner.lock().unwrap().take_lane_for_worker(lane3)
                    .unwrap();
                let (id3,payload3)=opener3.open(&mut wire3).unwrap().unwrap();
                assert!(owner.lock().unwrap().prepare_opened_receive(
                    lane3,id3,payload3).unwrap().is_none(),
                    "after TUN-success commit another fully authenticated copy must be deduped");
            }
            tx.stop();rx.stop();
        }
    }
    #[cfg(feature="fec2_product_record")]
    #[test]
    fn w143_lane_opener_fixed6_shared_decoder_partial_tun_failure_recovery(){
        let mut tx=build(4);
        let mut rx=build(4);
        tx.enable_game_fec(6,false).unwrap();
        rx.enable_game_fec(6,true).unwrap();
        tx.offer(&[0x65;128],MonoNs(10)).unwrap();
        let mut copies=Vec::new();
        tx.drain(MonoNs(11),|lane,_,_,wire|{
            copies.push((lane,wire.to_vec()));true
        });
        assert_eq!(copies.len(),4);
        let owner=rx.receiver_handle();
        let (lane0,mut wire0)=copies.remove(0);
        let (lane1,_wire1)=copies.remove(0);
        let mut opener0=owner.lock().unwrap().take_lane_for_worker(lane0).unwrap();
        let mut opener1=owner.lock().unwrap().take_lane_for_worker(lane1).unwrap();
        let (id,payload)=opener0.open(&mut wire0).unwrap().unwrap();
        let batch=owner.lock().unwrap().prepare_opened_fec_batch(
            lane0,id,payload,MonoNs(11)).unwrap().unwrap();
        assert!(!batch.frames().is_empty());
        owner.lock().unwrap().finish_fec_batch(batch,false).unwrap();
        // Failed TUN write MUST NOT mark the logical Game symbol
        // delivered; that does not imply an already-mutated FEC decoder
        // must accept the exact same source symbol a second time.
        {
            let shared=owner.lock().unwrap();
            assert!(shared.rx.first_delivery_candidate(
                shared.rx_scope,lane0,id).unwrap());
        }
        // A fresh unique symbol on lane1 still enters one shared FEC owner.
        tx.offer(&[0x66;128],MonoNs(13)).unwrap();
        let mut fresh=None;
        tx.drain(MonoNs(14),|lane,_,_,wire|{
            if lane==lane1 {fresh=Some(wire.to_vec());}
            true
        });
        let mut sealed=fresh.expect("fresh source on second physical lane");
        let (fresh_id,fresh_payload)=opener1.open(&mut sealed).unwrap().unwrap();
        assert_ne!(fresh_id,id);
        let batch=owner.lock().unwrap().prepare_opened_fec_batch(
            lane1,fresh_id,fresh_payload,MonoNs(14)).unwrap().unwrap();
        assert!(!batch.frames().is_empty());
        owner.lock().unwrap().finish_fec_batch(batch,true).unwrap();
        tx.stop();rx.stop();
    }
    #[test]
    fn game_pending_tun_write_suppresses_concurrent_duplicate_without_early_commit(){
        let mut game=build(4);
        game.offer(b"inflight",MonoNs(1)).unwrap();
        let mut copies=Vec::new();
        game.drain(MonoNs(2),|lane,_,_,wire|{
            copies.push((lane,wire.to_vec()));true
        });
        let rx=game.receiver_handle();
        let mut receiver=rx.lock().unwrap();
        let (lane0,mut wire0)=copies.remove(0);
        let first=receiver.prepare_receive(lane0,&mut wire0).unwrap().unwrap();
        let (lane1,mut wire1)=copies.remove(0);
        assert!(receiver.prepare_receive(lane1,&mut wire1).unwrap().is_none());
        receiver.finish_receive(first,false).unwrap();
        let (lane2,mut wire2)=copies.remove(0);
        let mut next=receiver.prepare_receive(lane2,&mut wire2)
            .unwrap().expect("failed TUN write did not poison shared dedup");
        assert_eq!(next.payload(),b"inflight");
        receiver.finish_receive(next,true).unwrap();
        drop(receiver);
        game.stop();
    }
    #[test]
    fn game_reused_tx_scratch_mixed_lengths_across_lanes_and_rx_duplicate_precheck(){
        let mut sender=build(4);
        let mut receiver=build(4);
        for (step,len) in [128usize,1260,77,1200,60,1300].iter().enumerate(){
            let payload=vec![(step+11) as u8;*len];
            let now=MonoNs((step as u64)*20);
            sender.offer(&payload,now).unwrap();
            let mut wires=Vec::new();
            let written=sender.drain(MonoNs(now.0+1),|lane,_,_,wire|{
                wires.push((lane,wire.to_vec()));true
            });
            assert_eq!(written,4);
            let mut delivered=Vec::new();
            for (lane,wire) in wires{
                if let Some(data)=receiver.receive(lane,wire).unwrap(){delivered.push(data)}
            }
            assert_eq!(delivered,vec![payload]);
        }
        sender.stop();receiver.stop();
    }
    #[test]
    fn game_receive_owner_progress_while_tx_adapter_lock_held(){
        use std::sync::mpsc;
        use std::time::Duration;
        let mut game=build(2);
        game.offer(b"no-tx-lock-hol",MonoNs(0)).unwrap();
        let mut copies=Vec::new();
        game.drain(MonoNs(1),|lane,_,_,wire|{
            copies.push((lane,wire.to_vec()));true
        });
        let (lane,mut wire)=copies.remove(0);
        let rx=game.receiver_handle();
        let game=Arc::new(Mutex::new(game));
        let hold_tx=game.lock().unwrap();
        let (tx,ch)=mpsc::channel();
        let worker=std::thread::spawn(move||{
            let result=rx.lock().unwrap().receive(lane,wire.as_mut_slice());
            tx.send(result).unwrap();
        });
        // Receive while TX lock is STILL held: do not create a deadlock
        // by allowing RX to access the legacy combined GameAdapter mutex.
        let outcome=ch.recv_timeout(Duration::from_millis(750));
        drop(hold_tx);
        worker.join().unwrap();
        assert_eq!(outcome.unwrap().unwrap(),Some(b"no-tx-lock-hol".to_vec()));
        game.lock().unwrap().stop();
    }
    #[test]
    fn game_rx_aeAD_tag_failure_not_replay_or_malformed(){
        let mut game=build(2);
        game.offer(b"first",MonoNs(0)).unwrap();
        let mut wires=Vec::new();
        game.drain(MonoNs(1),|lane,_,_,wire|{
            wires.push((lane,wire.to_vec()));true
        });
        let (lane,wire)=wires.remove(0);
        let mut tampered=wire.clone();
        *tampered.last_mut().unwrap()^=1;
        assert!(matches!(game.receive(lane,tampered),Err(Error::Crypto)));
        assert_eq!(game.receive(lane,wire.clone()).unwrap(),Some(b"first".to_vec()));
        assert!(matches!(game.receive(lane,wire),Err(Error::Duplicate)));
        assert!(matches!(game.receive(lane,vec![0;3]),Err(Error::Invalid)));
        game.stop();
    }
    #[test]
    fn game_mtu_uses_negotiated_record_budget_above_old1200(){
        let mut game=build(2);
        assert_eq!(game.inner_mtu(),1353); // authenticated record1400 -31 -16
        assert!(matches!(game.offer(&vec![7;1354],MonoNs(0)),Err(Error::Invalid)));
        let data=vec![7;1353];
        game.offer(&data,MonoNs(1)).unwrap();
        let mut copies=Vec::new();
        assert_eq!(game.drain(MonoNs(2),|lane,_,_,wire|{
            assert_eq!(wire.len(),1400);copies.push((lane,wire.to_vec()));true
        }),2);
        let (lane,wire)=copies.pop().unwrap();
        assert_eq!(game.receive(lane,wire).unwrap(),Some(data));
        game.stop();
    }
    #[test]
    fn m0_game_2_4_independent_record_pn_and_cross_lane_first_delivery(){
        for n in [2,4] {
            let mut game=build(n);
            assert_eq!(game.offer(b"business",MonoNs(0)).unwrap(),LogicalPacketId(0));
            let mut sends=Vec::new();
            assert_eq!(game.drain(MonoNs(1),|lane,id,pn,wire|{
                sends.push((lane,id,pn,wire.to_vec()));true
            }),n);
            assert_eq!(sends.len(),n);
            assert!(sends.iter().all(|x|x.1==LogicalPacketId(0)&&x.2==0));
            assert!(sends.iter().any(|x|x.3!=sends[0].3));
            sends.reverse();let mut accepted=Vec::new();
            for (lane,_,_,wire) in sends{
                if let Some(bytes)=game.receive(lane,wire).unwrap(){accepted.push(bytes);}
            }
            assert_eq!(accepted,vec![b"business".to_vec()]);
            game.stop();
            assert!(matches!(game.offer(b"retry",MonoNs(2)),Err(Error::Stopped)));
        }
    }
    #[test]
    fn m0_game_four_lane_stalled_copy_never_hol_other_lanes(){
        let mut game=build(4);
        game.offer(b"one",MonoNs(0)).unwrap();
        let mut sent=Vec::new();
        game.drain(MonoNs(1),|lane,_,_,wire|{
            if lane.slot==1{return false}
            sent.push((lane,wire.to_vec()));true
        });
        assert_eq!(game.counters().lane_copy_drop,1);
        assert_eq!(sent.len(),3);
        let (lane,wire)=sent.pop().unwrap();
        assert_eq!(game.receive(lane,wire).unwrap(),Some(b"one".to_vec()));
        game.offer(b"two",MonoNs(2)).unwrap();
        let mut newer=Vec::new();
        game.drain(MonoNs(3),|lane,_,_,wire|{
            newer.push((lane,wire.to_vec()));true
        });
        assert_eq!(newer.len(),4);
        let (lane,wire)=newer.pop().unwrap();
        assert_eq!(game.receive(lane,wire).unwrap(),Some(b"two".to_vec()));
        game.stop();
    }    #[test]
    fn m0_private_go_game_2_4_real_tls_independent_native_first_delivery(){
        use std::path::Path;
        let Ok(dir)=std::env::var("WBD_GAME_TLS_FIXTURE_DIR") else {
            // Real TLS fixture is required by the combined GitHub Actions
            // harness. Ordinary local native suite cannot claim this proof.
            return
        };
        let mut cases=0;
        for n in [2,4] {
            let mut read=|side:&str|->Vec<UntrustedColdV4>{
                (1..=n).map(|i|{
                    let path=Path::new(&dir).join(format!("game{n}-{side}-{i}.cold"));
                    let bytes=std::fs::read(path).expect("actual original Go TLS cold fixture");
                    UntrustedColdV4::parse(&bytes).expect("real original Go TLS cold grammar")
                }).collect()
            };
            let tunnel=TunnelKey{slot:14,generation:n as u32};
            let mut client=GameAdapter::from_private_original_go_tls(
                read("client"),false,tunnel,7).expect("client real Go TLS");
            let mut server=GameAdapter::from_private_original_go_tls(
                read("server"),true,tunnel,7).expect("server real Go TLS");
            assert_eq!(client.offer(b"actual-original-Go-TLS",MonoNs(0)).unwrap(),LogicalPacketId(0));
            let mut wires=Vec::new();
            assert_eq!(client.drain(MonoNs(1),|lane,id,pn,wire|{
                wires.push((lane,id,pn,wire.to_vec()));true
            }),n);
            assert_eq!(wires.len(),n);
            let mut seen=Vec::new();
            for (lane,id,pn,wire) in wires.into_iter().rev(){
                assert_eq!(id,LogicalPacketId(0));assert_eq!(pn,0);
                if let Some(payload)=server.receive(lane,wire).unwrap(){
                    seen.push(payload)
                }
            }
            assert_eq!(seen,vec![b"actual-original-Go-TLS".to_vec()]);
            server.offer(b"server-back",MonoNs(2)).unwrap();
            let mut back=Vec::new();
            assert_eq!(server.drain(MonoNs(3),|lane,_,_,wire|{
                back.push((lane,wire.to_vec()));true
            }),n);
            let mut received=Vec::new();
            for (lane,wire) in back.into_iter().rev(){
                if let Some(msg)=client.receive(lane,wire).unwrap(){received.push(msg)}
            }
            assert_eq!(received,vec![b"server-back".to_vec()]);
            let mut forged=read("client");
            forged[1]=UntrustedColdV4::parse(&std::fs::read(
                Path::new(&dir).join(format!("game{n}-client-1.cold"))
            ).unwrap()).unwrap();
            assert!(matches!(
                GameAdapter::from_private_original_go_tls(forged,false,tunnel,7),
                Err(Error::Unauthorized)));
            assert!(matches!(
                GameAdapter::from_private_original_go_tls(read("client"),true,tunnel,7),
                Err(Error::Unauthorized)));
            client.stop();server.stop();
            assert!(matches!(client.offer(b"stale",MonoNs(4)),Err(Error::Stopped)));
            println!("M0_ORIGINAL_GO_TLS_GAME_NATIVE_AEAD_PN_FIRST_DELIVERY_PASS lanes={n} independent_exporters=1 original_tls_fixture=1 REAL_M4_RAW_TUN_FIRST_APP_NOT_RUN=1");
            cases+=1;
        }
        assert_eq!(cases,2);
    }

}
