//! M0 protected Go V4 crypto installation, compiled in normal engine.
//! This is NOT a public cold installer or a credential authenticator. Only
//! the private credential-checked Go V4 callsite may supply its frozen source.
//! Test probes use these exact production-compiled methods, not a duplicate
//! crypto or business delivery path.
#![forbid(unsafe_code)]

use crate::cold_v4::{ColdV4Error, ExpectedRustOwner, UntrustedColdV4};
use crate::memory::UniqueBuffer;
use crate::runtime::{QueueLimits, RxOwner, RxPacket, TxOwner};
use crate::runtime::early_rx::{EarlyAccepted, EarlyError, EarlyLimits, EarlyRetirement, EarlyRxOwner};
use crate::runtime::generation::{LoanBatch, ScopedOwner, ScopeToken};
use std::ops::Range;
use wbd_types::MonoNs;
use wbd_codec::record_crypto::{LaneTxCrypto, RecordSuite};
use wbd_codec::record_replay::{
    ReplayConfigError, ReplayProtectedLaneRx, ReplayWindowConfig, UniqueOpenError,
};

#[derive(Debug)]
pub(crate) enum ProtectedCryptoError {
    Scope(ColdV4Error),
    Suite,
    Tx,
    Rx(ReplayConfigError),
    Inactive,
    Replay(UniqueOpenError),
    Owner,
    Early(EarlyError),
}

/// The scoped owner still owns dispatch, generation, driver leases and Stop.
/// This is the reusable AEAD/PN half of that owner; no payload is delivered.
pub(crate) struct ProtectedScopedCrypto {
    _tx: LaneTxCrypto,
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
            _tx:tx, rx, active:false, generation:expected.owner_generation,
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

    pub(crate) fn open_unique_after_active(&mut self,generation:u32,
        epoch:[u8;16],wire:&mut [u8],
    ) -> Result<(u64,u8,u64),ProtectedCryptoError> {
        if !self.active || self.tx_boundary.is_none()
            || generation!=self.generation || epoch!=self.epoch {
            return Err(ProtectedCryptoError::Inactive)
        }
        let opened=self.rx.open_unique_in_place(wire).map_err(ProtectedCryptoError::Replay)?;
        let digest=opened.payload.iter().fold(0xcbf29ce484222325u64,
            |v,byte|(v^u64::from(*byte)).wrapping_mul(0x100000001b3));
        Ok((opened.pn,opened.kind,digest))
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
}
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
enum OwnerPhase { Prepared, Active, Retired }

impl ProtectedScopedOwner {
    pub(crate) fn prepare_from_protected_go(
        cold:&UntrustedColdV4, expected:&ExpectedRustOwner,
        owner_id:u64, exact_rx_boundary:u32,
    )->Result<Self,ProtectedCryptoError>{
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
            epoch:expected.logical_epoch,
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
        self.state=OwnerPhase::Active;
        Ok(())
    }
    pub(crate) fn drain_rx(&mut self,now:MonoNs,storage:Vec<RxPacket>)
        ->Result<LoanBatch<RxPacket>,(EarlyError,Vec<RxPacket>)>{
        if self.state!=OwnerPhase::Active {
            return Err((EarlyError::NotPrepared,storage));
        }
        self.rx_tx.drain_rx(&self.token,now,storage)
    }
    pub(crate) fn open_unique_after_active(&mut self,wire:&mut[u8])
        ->Result<(u64,u8,u64),ProtectedCryptoError>{
        if self.state!=OwnerPhase::Active {
            return Err(ProtectedCryptoError::Inactive);
        }
        self.crypto.open_unique_after_active(self.generation,self.epoch,wire)
    }
    /// Stops BOTH actual owner queues and AEAD/PN admission. Retained loan
    /// batches still own their original generation; repeat Stop is safe.
    pub(crate) fn stop(&mut self)->Result<EarlyRetirement,EarlyError>{
        self.state=OwnerPhase::Retired;
        self.crypto.retire();
        self.rx_tx.stop(&self.token)
    }
}
