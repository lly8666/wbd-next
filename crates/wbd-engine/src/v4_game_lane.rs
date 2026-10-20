//! M0 original-owner Game2/4 lane adapter. Receives ONLY original Go TLS
//! validated epoch, generation, lane IDs and distinct exporter keys.
//! Reuses frozen M1 GameTx shared-buffer dispatch and GameRx dedup;
//! per-lane AEAD/PN/replay are independently allocated; no public Go grant.
#![forbid(unsafe_code)]
use crate::memory::Arena;
use crate::cold_v4::UntrustedColdV4;
use wbd_types::TunnelKey;
use crate::runtime::game_shared::{
    ActiveLaneSnapshot,DispatchOutcome,FlowDirection,GameCounters,GameError,
    GameLimits,GameRx,GameScope,GameTx,Mode,QualifiedLane,RxLimits
};
use wbd_types::{LaneKey,LogicalPacketId,MonoNs};
use wbd_types::buffer_contract::UniqueSealable;
use wbd_codec::record_crypto::{DirectionKeys,LaneTxCrypto,RecordSuite};
use wbd_codec::record_replay::{ReplayProtectedLaneRx,ReplayWindowConfig};
pub struct ScopedKeys{pub lane:QualifiedLane,pub tx:DirectionKeys,pub rx:DirectionKeys}
struct Lane{key:LaneKey,tx:LaneTxCrypto,rx:ReplayProtectedLaneRx}
#[derive(Debug,PartialEq,Eq)]
pub enum Error{Unauthorized,Invalid,Capacity,Stopped,Duplicate,Crypto,Game(GameError)}
pub struct GameAdapter{
    tx:GameTx,rx:GameRx,rx_scope:GameScope,
    lanes:Vec<Lane>,arena:Arena,stopped:bool
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
        let mut identities=Vec::new();
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
            let tx=LaneTxCrypto::new_for_suite(m.tx,m.lane.mss,suite)
                .map_err(|_|Error::Crypto)?;
            let rx=ReplayProtectedLaneRx::new_for_suite(m.rx,m.lane.mss,
                suite,ReplayWindowConfig{pn_per_second:2000,
                    cache_horizon_ms:200,fec_horizon_ms:200,rtt_ms:100,
                    metadata_budget_bytes:131072}).map_err(|_|Error::Crypto)?;
            infos.push(m.lane);lanes.push(Lane{key:m.lane.key,tx,rx});
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
        let arena=Arena::new(905,256,2048,256,1024*1024)
            .map_err(|_|Error::Capacity)?;
        Ok(Self{tx,rx,rx_scope,lanes,arena,stopped:false})
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
            if c2s==s2c || all_materials.contains(&c2s) ||
                all_materials.contains(&s2c) {
                return Err(Error::Unauthorized)
            }
            // Duplicate keys across any direction or lane violate distinct
            // exporter ownership. Native AEAD never rekeys or reuses a PN.
            all_materials.push(c2s);all_materials.push(s2c);
            incarnations.push(id.incarnation);
            let mss=id.client_limit.min(id.server_limit).min(2048);
            if mss<64{return Err(Error::Invalid)}
            indexed[usize::from(id.go_lane_id)-1]=Some(ScopedKeys{
                lane:QualifiedLane{key:LaneKey{tunnel:owner_tunnel,
                    slot:u32::from(id.go_lane_id),generation},mss},
                tx:if server{s2c}else{c2s},
                rx:if server{c2s}else{s2c},
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
    pub fn offer(&mut self,data:&[u8],now:MonoNs)->Result<LogicalPacketId,Error>{
        if self.stopped{return Err(Error::Stopped)}
        if data.is_empty()||data.len()>1200{return Err(Error::Invalid)}
        let id=self.tx.next_packet().ok_or(Error::Stopped)?;
        let packet=wbd_codec::encode_game(id,data,1216).map_err(|_|Error::Invalid)?;
        let mut slab=self.arena.allocate().map_err(|_|Error::Capacity)?;
        let end=14+packet.len();
        slab.writable()[14..end].copy_from_slice(&packet);
        let offered=self.tx.offer(slab,14..end,Mode::Game,31+packet.len(),
            None,now).map_err(|(e,_)|Error::Game(e))?;
        if offered!=Some(id){return Err(Error::Invalid)}
        Ok(id)
    }
    /// Each ready lane gets a distinct AEAD nonce/PN and cipher buffer;
    /// network copy acknowledgement is supplied by the M0 kernel driver.
    pub fn drain<F>(&mut self,now:MonoNs,mut kernel_copy:F)->usize
    where F:FnMut(LaneKey,LogicalPacketId,u64,&[u8])->bool{
        if self.stopped{return 0}
        let lanes=&mut self.lanes;
        self.tx.drain_ready(now,32,|view|{
            let Some(id)=view.logical_id else{return DispatchOutcome::PressureDrop};
            let Some(lane)=lanes.iter_mut().find(|l|l.key==view.lane)
            else{return DispatchOutcome::PressureDrop};
            let len=view.common_payload.len();
            let mut wire=vec![0u8;31+len];
            wire[14..14+len].copy_from_slice(view.common_payload);
            let Ok((pn,n))=lane.tx.seal_in_place(1,&mut wire,len,0)
            else{return DispatchOutcome::PressureDrop};
            if kernel_copy(view.lane,id,pn,&wire[..n]){
                DispatchOutcome::Accepted
            }else{DispatchOutcome::PressureDrop}
        })
    }
    /// This is a peer-facing authenticated receiver. Original Go's
    /// source, peer directions and actual kernel ingress still gate its use.
    pub fn receive(&mut self,lane_key:LaneKey,mut wire:Vec<u8>)
        ->Result<Option<Vec<u8>>,Error>{
        if self.stopped{return Err(Error::Stopped)}
        let lane=self.lanes.iter_mut().find(|l|l.key==lane_key)
            .ok_or(Error::Unauthorized)?;
        let opened=lane.rx.open_unique_in_place(&mut wire)
            .map_err(|_|Error::Crypto)?;
        if opened.kind!=1{return Err(Error::Invalid)}
        let (id,payload)=wbd_codec::decode_game(opened.payload,1216)
            .map_err(|_|Error::Invalid)?;
        if payload.len()>1200{return Err(Error::Invalid)}
        let mut owned=self.arena.allocate().map_err(|_|Error::Capacity)?;
        owned.writable()[14..14+payload.len()].copy_from_slice(payload);
        match self.rx.first_delivery(self.rx_scope,lane_key,id,owned){
            Ok(mut b)=>Ok(Some(b.writable()[14..14+payload.len()].to_vec())),
            Err((GameError::Duplicate,_))=>Ok(None),
            Err((e,_))=>Err(Error::Game(e)),
        }
    }
    pub fn stop(&mut self){
        if self.stopped{return}self.stopped=true;
        self.tx.stop();self.rx.stop();self.arena.stop();self.arena.drain_returns();
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
