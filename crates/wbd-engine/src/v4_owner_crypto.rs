//! M0 protected Go V4 crypto installation, compiled in normal engine.
//! This is NOT a public cold installer or a credential authenticator. Only
//! the private credential-checked Go V4 callsite may supply its frozen source.
//! Test probes use these exact production-compiled methods, not a duplicate
//! crypto or business delivery path.
#![forbid(unsafe_code)]

use crate::cold_v4::{ColdV4Error, ExpectedRustOwner, UntrustedColdV4};
use crate::memory::UniqueBuffer;
use crate::runtime::{QueueLimits, RxOwner, RxPacket, TxOwner,TxDispatch};
use crate::runtime::early_rx::{EarlyAccepted, EarlyError, EarlyLimits, EarlyRetirement, EarlyRxOwner};
use crate::runtime::generation::{LoanBatch, ScopedOwner, ScopeToken};
use std::ops::Range;
use wbd_types::{MonoNs,RecordPn,SeqOffset};
use wbd_types::buffer_contract::{FrozenMetadata,UniqueSealable};
use wbd_codec::record_crypto::{LaneTxCrypto, RecordSuite};
use wbd_codec::record_frame::{AUTHENTICATED_LINK_KIND,FIXED_WIRE_OVERHEAD};
use wbd_codec::link_fec_wire::{inspect_link,LinkMode,LinkView,LINK_HEADER,LINK_MAGIC};
use wbd_codec::path_budget::FrameBudget;
#[cfg(all(target_os="linux",target_arch="x86_64",target_env="gnu"))]
use wbd_codec::path_budget::{FrameBudgetInput,FecReservation,MAX_CONNECTION_MTU};
#[cfg(all(target_os="linux",target_arch="x86_64",target_env="gnu"))]
use wbd_platform::linux_packet_preflight::observe_interface_mtu;
use wbd_codec::link_reassembly::{
    LinkDelivery,LinkDirection,ReassemblyScope,ReassemblyTable,
};
use wbd_codec::record_replay::{
    ReplayConfigError, ReplayProtectedLaneRx, ReplayWindowConfig,
};

#[derive(Debug)]
pub(crate) enum ProtectedCryptoError {
    Scope(ColdV4Error),
    Suite,
    Tx,
    Rx(ReplayConfigError),
    Inactive,
    Owner,
    Early(EarlyError),
}

/// The scoped owner still owns dispatch, generation, driver leases and Stop.
/// This is the reusable AEAD/PN half of that owner; no payload is delivered.
pub(crate) struct ProtectedScopedCrypto {
    tx: LaneTxCrypto,
    rx: ReplayProtectedLaneRx,
    active: bool,
    generation: u32,
    go_lane: u8,
    epoch: [u8; 16],
    tx_boundary: Option<u32>,
}

impl ProtectedScopedCrypto {
    /// Private trusted-Go-call precondition; cannot infer trust from 248 bytes.
    /// Construct BOTH directions before either can be published.
    pub(crate) fn prepare_from_protected_go(
        cold: &UntrustedColdV4, expected: &ExpectedRustOwner,
    ) -> Result<Self, ProtectedCryptoError> {
        cold.preflight_untrusted_owner(expected).map_err(ProtectedCryptoError::Scope)?;
        if expected.owner_generation != expected.lane.generation
            || expected.owner_generation != expected.lane.tunnel.generation
            || expected.lane.slot != u32::from(expected.go_lane_id)
        {
            return Err(ProtectedCryptoError::Scope(ColdV4Error::ScopeMismatch));
        }
        let identity = cold.identity();
        let suite = RecordSuite::try_from(identity.cipher)
            .map_err(|_| ProtectedCryptoError::Suite)?;
        let (c2s, s2c) = cold.internal_direction_keys();
        let (tx_keys, rx_keys, tx_limit, rx_limit) = if identity.server {
            (s2c, c2s, identity.client_limit, identity.server_limit)
        } else {
            (c2s, s2c, identity.server_limit, identity.client_limit)
        };
        let tx = LaneTxCrypto::new_for_suite(tx_keys, usize::from(tx_limit), suite)
            .map_err(|_| ProtectedCryptoError::Tx)?;
        // Bounded preliminary replay parameters; NOT a production throughput
        // selection. Effective values must be recorded before qualification.
        let replay = ReplayWindowConfig {
            pn_per_second: 1000, cache_horizon_ms: 3000,
            fec_horizon_ms: 0, rtt_ms: 500, metadata_budget_bytes: 8192,
        };
        let rx = ReplayProtectedLaneRx::new_for_suite(
            rx_keys, usize::from(rx_limit), suite, replay,
        ).map_err(ProtectedCryptoError::Rx)?;
        Ok(Self {
            tx, rx, active:false, generation:expected.owner_generation,
            go_lane:expected.go_lane_id, epoch:identity.logical_epoch,
            tx_boundary:None,
        })
    }

    /// Only after protected reply, Go Detach, and both owner installations.
    /// Exact Go SenderNext after protected reply is mandatory, never guessed.
    pub(crate) fn commit_after_detach(&mut self, generation:u32,
        go_lane:u8, epoch:[u8;16], exact_tx_boundary:u32,
    ) -> Result<(),ProtectedCryptoError> {
        if self.active || generation!=self.generation
            || go_lane!=self.go_lane || epoch!=self.epoch {
            return Err(ProtectedCryptoError::Inactive)
        }
        self.tx_boundary=Some(exact_tx_boundary);
        self.active=true;
        Ok(())
    }

    /// Same real AEAD/PN function to be called by the eventual RX owner.
    /// Never a standalone business delivery or test-specific decryptor.
    fn retire(&mut self) {
        self.active = false;
        self.tx_boundary = None;
    }

}

/// M0 composition of the ACTUAL M1 RX/TX scoped owner with the authenticated
/// record state. Compiled into the ordinary engine, not behind test features.
/// Go's private credential-checked control callsite is the ONLY intended
/// caller; bytes alone still cannot prove TLS identity.
pub(crate) struct ProtectedScopedOwner {
    rx_tx: EarlyRxOwner,
    token: ScopeToken,
    crypto: ProtectedScopedCrypto,
    state: OwnerPhase,
    generation: u32,
    go_lane: u8,
    epoch: [u8;16],
    rx_wire_limit:usize,
    tx_wire_limit:usize,
    peer_mss:u16,
    peer_mss_advertised:bool,
    next_tx_seq:Option<u32>,
    server:bool,
}
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
enum OwnerPhase { Prepared, Active, Retired }

/// Counts verified records admitted to downstream LINK parsing, not
/// application first delivery. Invalid/replayed wires are never passed to
/// the caller; HEALTH remains a separate authenticated control kind.
#[derive(Clone,Copy,Debug,Default,PartialEq,Eq)]
pub(crate) struct AuthenticatedRxReport {
    pub(crate) link_ready:u32,
    pub(crate) control_ready:u32,
    pub(crate) rejected:u32,
}

/// One *owner-bound* Normal/FEC-off LINK reassembly context. This is not a
/// second crypto or activation path; it can only receive data from the actual
/// ScopedOwner's authenticated RX batch. A new owner/generation creates a
/// new table, so retired packet IDs cannot cross sessions.
pub(crate) struct NormalOffReceive {
    table:ReassemblyTable,
    frame_mtu:usize,
    owner_id:u64,
    generation:u32,
    lane:u8,
    epoch:[u8;16],
    epoch_tag:u64,
    direction:LinkDirection,
    max_extended_id:Option<u64>,
}
#[derive(Clone,Copy,Debug,Default,PartialEq,Eq)]
pub(crate) struct NormalOffReport {
    pub(crate) authenticated:AuthenticatedRxReport,
    pub(crate) completed:u32,
    pub(crate) pending:u32,
    pub(crate) discarded:u32,
    pub(crate) malformed:u32,
}
impl NormalOffReceive {
    /// frame_mtu MUST be the effective negotiated M4/Go path budget once a
    /// live carrier is installed, NOT merely a requested record limit.
    /// Explicit configuration is required: do not quietly assume local MTU.
    pub(crate) fn new_for_owner(owner:&ProtectedScopedOwner,
        effective_link_frame_mtu:usize,minimum_link_frame_mtu:usize,
    )->Result<Self,ProtectedCryptoError>{
        if effective_link_frame_mtu<=LINK_HEADER
            || effective_link_frame_mtu>
                owner.rx_wire_limit.saturating_sub(FIXED_WIRE_OVERHEAD) {
            return Err(ProtectedCryptoError::Owner)
        }
        let table=ReassemblyTable::new(effective_link_frame_mtu,
            minimum_link_frame_mtu,LinkMode::FixedOff)
            .map_err(|_|ProtectedCryptoError::Owner)?;
        let mut first=[0u8;8];first.copy_from_slice(&owner.epoch[..8]);
        Ok(Self{
            table,frame_mtu:effective_link_frame_mtu,
            owner_id:owner.token.owner_id(),generation:owner.generation,
            lane:owner.go_lane,epoch:owner.epoch,
            epoch_tag:u64::from_be_bytes(first),
            direction:if owner.server {LinkDirection::ClientToServer}
                else {LinkDirection::ServerToClient},
            max_extended_id:None,
        })
    }
    fn accepts(&self,owner:&ProtectedScopedOwner)->bool{
        self.owner_id==owner.token.owner_id()
            && self.generation==owner.generation
            && self.lane==owner.go_lane && self.epoch==owner.epoch
    }
    /// Extend the authenticated LINK32 identifier near wrap using a
    /// half-range window; far-old ambiguous IDs are rejected, not guessed.
    /// No packet_id is read before record AEAD/PN validation.
    fn extend_packet_id(&mut self,raw:u32)->Option<u64>{
        if raw==0{return None}
        let mut value=u64::from(raw);
        if let Some(max)=self.max_extended_id{
            const FULL:u64=1u64<<32;
            const HALF:u64=1u64<<31;
            value=(max & !(FULL-1))|value;
            if value<max && max-value>HALF {
                value=value.checked_add(FULL)?;
            }else if value>max && value-max>HALF {
                value=value.checked_sub(FULL)?;
            }
            if value<max && max-value>HALF{return None}
            self.max_extended_id=Some(max.max(value));
        }else{
            self.max_extended_id=Some(value);
        }
        Some(value)
    }
}

/// Immutable owner-bound *kernel interface MTU*, not path PMTU, socket
/// capability, driver lease or peer authentication. Private fields prevent
/// a later caller from minting its own unrestricted FrameBudget.
#[cfg(all(target_os="linux",target_arch="x86_64",target_env="gnu"))]
pub(crate) struct ScopedLinuxBudget {
    pub(crate) frame:FrameBudget,
    owner_id:u64,
    generation:u32,
    epoch:[u8;16],
    pub(crate) observed_ifindex:u32,
    pub(crate) observed_interface_mtu:u32,
}

impl ProtectedScopedOwner {
    pub(crate) fn prepare_from_protected_go(
        cold:&UntrustedColdV4, expected:&ExpectedRustOwner,
        owner_id:u64, exact_rx_boundary:u32,
        peer_mss:u16,peer_mss_advertised:bool,
    )->Result<Self,ProtectedCryptoError>{
        // A peer's original SYN MSS is an untrusted cap, not TLS identity,
        // and MUST be bound once at the same private protected Go Prepare.
        // A later driver/CLI-provided FrameBudget must not enlarge it.
        if peer_mss<64 || (!peer_mss_advertised && peer_mss!=536){
            return Err(ProtectedCryptoError::Owner)
        }
        // Construct all resources locally; NONE is published on half failure.
        let crypto=ProtectedScopedCrypto::prepare_from_protected_go(cold,expected)?;
        let wire=usize::from(cold.identity().server_limit);
        let limits=QueueLimits {
            slots:32,bytes:wire.saturating_mul(32),max_age_ns:50_000_000,
        };
        let rx_limits=QueueLimits {
            slots:64,bytes:wire.saturating_mul(64),max_age_ns:50_000_000,
        };
        let tx=TxOwner::new(limits,limits).ok_or(ProtectedCryptoError::Owner)?;
        let rx=RxOwner::new(rx_limits).ok_or(ProtectedCryptoError::Owner)?;
        let inner=ScopedOwner::new(owner_id,expected.owner_generation,
            expected.lane,tx,rx).ok_or(ProtectedCryptoError::Owner)?;
        let mut rx_tx=EarlyRxOwner::new(inner,EarlyLimits{
            slots:32,bytes:wire.saturating_mul(32),
        }).ok_or(ProtectedCryptoError::Owner)?;
        let token=rx_tx.token();
        rx_tx.prepare(&token,u64::from(exact_rx_boundary))
            .map_err(ProtectedCryptoError::Early)?;
        Ok(Self {
            rx_tx,token,crypto,state:OwnerPhase::Prepared,
            generation:expected.owner_generation,go_lane:expected.go_lane_id,
            epoch:expected.logical_epoch,rx_wire_limit:wire,
            tx_wire_limit:usize::from(if expected.server {
                cold.identity().client_limit
            }else{cold.identity().server_limit}),
            peer_mss,peer_mss_advertised,
            next_tx_seq:None,server:expected.server,
        })
    }
    /// The same M1 owner stages before the protected reply/Detach; no
    /// application payload may be exposed while state is Prepared.
    pub(crate) fn offer_early(&mut self,buffer:UniqueBuffer,wire:Range<usize>,
        offset:u64,now:MonoNs,
    )->Result<EarlyAccepted,(EarlyError,UniqueBuffer)>{
        if self.state!=OwnerPhase::Prepared {
            return Err((EarlyError::NotPrepared,buffer));
        }
        self.rx_tx.offer(&self.token,buffer,wire,offset,now)
    }
    pub(crate) fn commit_after_detach(&mut self,
        exact_tx_boundary:u32,
    )->Result<(),ProtectedCryptoError>{
        if self.state!=OwnerPhase::Prepared {
            return Err(ProtectedCryptoError::Inactive);
        }
        // Ensure all possible crypto commit errors precede RX Detach.
        if self.crypto.active || self.generation!=self.crypto.generation
           || self.go_lane!=self.crypto.go_lane || self.epoch!=self.crypto.epoch {
            return Err(ProtectedCryptoError::Inactive);
        }
        self.rx_tx.detach(&self.token).map_err(ProtectedCryptoError::Early)?;
        self.crypto.commit_after_detach(
            self.generation,self.go_lane,self.epoch,exact_tx_boundary,
        )?;
        self.next_tx_seq=Some(exact_tx_boundary);
        self.state=OwnerPhase::Active;
        Ok(())
    }

    /// Observe the actual Linux kernel's LOCAL interface MTU and bind the
    /// M3 frame budget to this owner's full epoch and generation. Uses the
    /// one protected-session SYN peer MSS already stored at Prepare; there
    /// is no caller MSS parameter and no operator-controlled cold authority.
    /// The caller must still independently verify OS routing / real peer
    /// path PMTU and own a driver lease before any product activation.
    #[cfg(all(target_os="linux",target_arch="x86_64",target_env="gnu"))]
    pub(crate) fn observe_linux_normal_off_budget(
        &self,ifname:&str,expected_ifindex:u32,
    )->Result<ScopedLinuxBudget,ProtectedCryptoError>{
        if self.state!=OwnerPhase::Active || !self.rx_tx.detached(){
            return Err(ProtectedCryptoError::Inactive)
        }
        let kernel=observe_interface_mtu(ifname,expected_ifindex)
            .map_err(|_|ProtectedCryptoError::Owner)?;
        let observed=usize::try_from(kernel.kernel_mtu)
            .map_err(|_|ProtectedCryptoError::Tx)?;
        let connection_mtu=observed.min(MAX_CONNECTION_MTU);
        let frame=FrameBudget::derive(FrameBudgetInput{
            connection_mtu,local_packet_mtu:observed,
            ipv4_header_len:20,tcp_header_len:20,
            peer_mss:if self.peer_mss_advertised{Some(self.peer_mss)}else{None},
            record_wire_limit:self.tx_wire_limit,
            fec:FecReservation::FixedOff,game:false,
        }).map_err(|_|ProtectedCryptoError::Tx)?;
        Ok(ScopedLinuxBudget{
            frame,owner_id:self.token.owner_id(),
            generation:self.generation,epoch:self.epoch,
            observed_ifindex:kernel.ifindex,
            observed_interface_mtu:kernel.kernel_mtu,
        })
    }
    /// No caller-invented budget can be substituted for this kernel-observed
    /// and original-owner-scoped constraint. This still does NOT submit any
    /// packet to a kernel device; M4 driver-held Stop remains unqualified.
    #[cfg(all(target_os="linux",target_arch="x86_64",target_env="gnu"))]
    pub(crate) fn seal_normal_off_with_linux_budget(
        &mut self,buffer:UniqueBuffer,payload_len:usize,
        scoped:&ScopedLinuxBudget,carrier_snapshot:u64,now:MonoNs,
    )->Result<(u64,u32,usize),ProtectedCryptoError>{
        if self.state!=OwnerPhase::Active || self.generation!=scoped.generation
            || self.epoch!=scoped.epoch
            || self.token.owner_id()!=scoped.owner_id {
            return Err(ProtectedCryptoError::Inactive)
        }
        self.seal_normal_off_one(buffer,payload_len,scoped.frame,carrier_snapshot,now)
    }

    /// The actual normal-build S2C/C2S TX: one application Normal/off
    /// packet, already placed by the caller in the SAME M1 UniqueBuffer at
    /// [14 .. 14+payload_len]. Only an explicitly supplied effective M4
    /// FrameBudget can grant the wire size; never infer MSS from cold bytes.
    ///
    /// A LINK packet needing magic escape/fragmentation is rejected here,
    /// never emitted as ambiguous raw ordinary bytes. It will use the same
    /// M3 fragmenter in a subsequent bounded TX path.
    /// AEAD/PN and TCP sequence are consumed BEFORE queue publication.
    pub(crate) fn seal_normal_off_one(
        &mut self,mut buffer:UniqueBuffer,payload_len:usize,
        budget:FrameBudget,carrier_snapshot:u64,now:MonoNs,
    )->Result<(u64,u32,usize),ProtectedCryptoError>{
        if self.state!=OwnerPhase::Active || !self.rx_tx.detached()
            || !self.crypto.active || self.crypto.tx_boundary.is_none(){
            return Err(ProtectedCryptoError::Inactive)
        }
        if budget.peer_mss != usize::from(self.peer_mss)
            || budget.peer_mss_advertised != self.peer_mss_advertised {
            return Err(ProtectedCryptoError::Tx)
        }
        if budget.fec_overhead!=0 || budget.game_overhead!=0
            || budget.record_wire_mtu>self.tx_wire_limit
            || budget.link_frame_mtu>budget.record_payload_mtu
            || payload_len==0 || payload_len>budget.single_business_payload_mtu {
            return Err(ProtectedCryptoError::Tx)
        }
        let used=payload_len.checked_add(FIXED_WIRE_OVERHEAD)
            .ok_or(ProtectedCryptoError::Tx)?;
        if used>budget.record_wire_mtu || buffer.writable().len()<used {
            return Err(ProtectedCryptoError::Tx)
        }
        let business=&buffer.writable()[14..14+payload_len];
        if business.starts_with(LINK_MAGIC){return Err(ProtectedCryptoError::Tx)}
        let seq=self.next_tx_seq.ok_or(ProtectedCryptoError::Inactive)?;
        let next=seq.checked_add(
            u32::try_from(used).map_err(|_|ProtectedCryptoError::Tx)?
        ).ok_or(ProtectedCryptoError::Tx)?;
        let (pn,sealed_len)=self.crypto.tx.seal_in_place(
            AUTHENTICATED_LINK_KIND,buffer.writable(),payload_len,0,
        ).map_err(|_|ProtectedCryptoError::Tx)?;
        // No sequence reuse even if freezing/queue admission fails.
        self.next_tx_seq=Some(next);
        let frozen=buffer.freeze(0..sealed_len,FrozenMetadata {
            lane:self.token.lane(),seq:SeqOffset(u64::from(seq)),
            pn:RecordPn(pn),carrier_snapshot,
        }).map_err(|_|ProtectedCryptoError::Tx)?;
        self.rx_tx.offer_tx_fresh(&self.token,frozen,now)
            .map_err(|_|ProtectedCryptoError::Owner)?;
        Ok((pn,seq,sealed_len))
    }

    /// The actual M1 generation-fenced FrozenRecord ready batch. It keeps
    /// cipher bytes immutable until its TX loan is recycled or dropped, and
    /// MUST be submitted to M4 only while this current owner is Active.
    pub(crate) fn drain_tx(&mut self,now:MonoNs,
        storage:Vec<TxDispatch>,
    )->Result<LoanBatch<TxDispatch>,(ProtectedCryptoError,Vec<TxDispatch>)>{
        if self.state!=OwnerPhase::Active {
            return Err((ProtectedCryptoError::Inactive,storage))
        }
        self.rx_tx.drain_tx(&self.token,now,storage)
            .map_err(|(_,s)|(ProtectedCryptoError::Owner,s))
    }
    pub(crate) fn checked_tx_ready<'a>(
        &self,batch:&'a LoanBatch<TxDispatch>,
    )->Result<&'a [TxDispatch],ProtectedCryptoError>{
        if self.state!=OwnerPhase::Active {
            return Err(ProtectedCryptoError::Inactive)
        }
        self.rx_tx.checked_tx_ready(&self.token,batch)
            .map_err(|_|ProtectedCryptoError::Owner)
    }

    /// Accept an existing owned ingress slab ONLY after Go's trusted Detach
    /// and commit. The exact sequence hint enforces the bootstrap/record
    /// boundary; record PN+payload remain untrusted until AEAD validates.
    pub(crate) fn offer_after_active(&mut self,buffer:UniqueBuffer,
        wire:Range<usize>,absolute_seq:u64,now:MonoNs,
    )->Result<(),(EarlyError,UniqueBuffer)>{
        if self.state!=OwnerPhase::Active || !self.rx_tx.detached() {
            return Err((EarlyError::NotPrepared,buffer))
        }
        self.rx_tx.offer(&self.token,buffer,wire,absolute_seq,now)
            .map(|accepted| {
                // The only allowed post-Detach result is Ready.
                debug_assert_eq!(accepted,EarlyAccepted::Ready);
            })
    }

    /// The production-compiled RX path uses the REAL M1 owner queue and
    /// generation-fenced borrowed batch. Decrypt IN PLACE inside that owned
    /// slab; publish LINK data only after both AEAD and unique PN admission.
    /// The caller owns onward LINK parsing/reassembly and application
    /// delivery. No untrusted bytes, HEALTH or replay reach this callback.
    ///
    /// Supply a caller-preallocated Vec: the batch returns the same storage
    /// after its original generation ledger has been released, with no
    /// second copy or per-packet allocation.
    pub(crate) fn drain_authenticated<F>(&mut self,now:MonoNs,
        storage:Vec<RxPacket>,mut accept_link:F,
    )->Result<(Vec<RxPacket>,AuthenticatedRxReport),(ProtectedCryptoError,Vec<RxPacket>)>
    where F:FnMut(u64,&[u8]){
        if self.state!=OwnerPhase::Active {
            return Err((ProtectedCryptoError::Inactive,storage))
        }
        let mut borrowed=self.rx_tx.drain_rx(&self.token,now,storage)
            .map_err(|(err,st)|(ProtectedCryptoError::Early(err),st))?;
        let mut report=AuthenticatedRxReport::default();
        for packet in borrowed.as_mut_slice(){
            match self.crypto.rx.open_unique_in_place(packet.wire_mut()){
                Ok(record) if record.kind==AUTHENTICATED_LINK_KIND=>{
                    // The payload reference is tied to this mutable owner
                    // batch and cannot outlive this synchronous callback.
                    accept_link(record.pn,record.payload);
                    report.link_ready+=1;
                }
                Ok(_)=>report.control_ready+=1,
                Err(_)=>report.rejected+=1,
            }
        }
        Ok((borrowed.recycle(),report))
    }

    /// Single normal-build ingress: owner LoanBatch -> AEAD & PN unique ->
    /// M3 LINK wire inspection / bounded reassembly -> complete packet sink.
    /// Incomplete, conflicting, stale and malformed fragments never call
    /// the sink; one new ordinary packet does not wait for any old hole.
    pub(crate) fn drain_normal_off<F>(&mut self,receiver:&mut NormalOffReceive,
        now:MonoNs,storage:Vec<RxPacket>,mut accept_packet:F,
    )->Result<(Vec<RxPacket>,NormalOffReport),(ProtectedCryptoError,Vec<RxPacket>)>
    where F:FnMut(u64,&[u8]){
        if self.state!=OwnerPhase::Active || !receiver.accepts(self){
            return Err((ProtectedCryptoError::Inactive,storage))
        }
        let ms=now.0/1_000_000;
        let mut out=NormalOffReport::default();
        let (returned,authenticated)=self.drain_authenticated(
            now,storage,|pn,link|{
                let id=match inspect_link(link,receiver.frame_mtu,LinkMode::FixedOff){
                    Ok(LinkView::Ordinary(_))=>Some(0),
                    Ok(LinkView::Fragment(f))=>receiver.extend_packet_id(f.packet_id),
                    Err(_)=>{out.malformed+=1;return}
                };
                let Some(id)=id else {out.malformed+=1;return};
                let scope=ReassemblyScope{
                    tunnel_epoch:receiver.epoch_tag,
                    direction:receiver.direction,packet_id_ext:id,
                };
                match receiver.table.push_after_record_auth(link,scope,ms){
                    Ok(LinkDelivery::Ordinary(bytes))=>{accept_packet(pn,bytes);out.completed+=1;},
                    Ok(LinkDelivery::Reassembled(bytes))=>{accept_packet(pn,&bytes);out.completed+=1;},
                    Ok(LinkDelivery::Pending)=>out.pending+=1,
                    Ok(LinkDelivery::Discarded)=>out.discarded+=1,
                    Err(_)=>out.malformed+=1,
                }
            })?;
        out.authenticated=authenticated;
        Ok((returned,out))
    }

    pub(crate) fn drain_rx(&mut self,now:MonoNs,storage:Vec<RxPacket>)
        ->Result<LoanBatch<RxPacket>,(EarlyError,Vec<RxPacket>)>{
        if self.state!=OwnerPhase::Active {
            return Err((EarlyError::NotPrepared,storage));
        }
        self.rx_tx.drain_rx(&self.token,now,storage)
    }
    /// Stops BOTH actual owner queues and AEAD/PN admission. Retained loan
    /// batches still own their original generation; repeat Stop is safe.
    pub(crate) fn stop(&mut self)->Result<EarlyRetirement,EarlyError>{
        self.state=OwnerPhase::Retired;
        self.crypto.retire();
        self.next_tx_seq=None;
        self.rx_tx.stop(&self.token)
    }
}
