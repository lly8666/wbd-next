//! M0 TEST-ONLY *inactive* native Go/Rust bridge. No production feature or
//! authenticated C ABI is published. A caller-supplied 248-byte bundle is
//! merely a candidate, even if structurally valid; ONLY the private Go
//! credential-checked callsite is a potential future positive authority.
//! This probe owns a NEW ScopedOwner generation in Rust and exercises stage,
//! commit and stop transitions, but it does NOT install business AEAD/FEC.
#![allow(clippy::missing_safety_doc)]

use std::collections::BTreeMap;
use std::sync::{Mutex, OnceLock};

use wbd_types::{LaneKey, TunnelKey, MonoNs};
use wbd_types::buffer_contract::UniqueSealable;
use crate::memory::Arena;
use crate::runtime::early_rx::{EarlyRxOwner,EarlyLimits,EarlyAccepted};
use crate::cold_v4::{ColdIdentity, ExpectedRustOwner, UntrustedColdV4, COLD_V4_LEN};
use crate::runtime::{QueueLimits, RxOwner, TxOwner};
use crate::runtime::generation::{ScopeToken, ScopedOwner};

const OK: i32 = 0;
const INVALID: i32 = 1;
const UNKNOWN: i32 = 2;
const BAD_STAGE: i32 = 3;
const FULL: i32 = 4;
const MAX_PROBES: usize = 16;
const MAX_EARLY: u32 = 64;
const PH_PREPARED: u32 = 1;
const PH_COMMITTED: u32 = 2;
const PH_STOPPED: u32 = 3;

struct Probe {
    owner: EarlyRxOwner,
    token: ScopeToken,
    arena: Arena,
    phase: u32,
    rx_boundary: u32,
    staged_count:u32,
    staged_bytes:u32,
    drained:bool,
    cold_identity: ColdIdentity,
}

struct Probes {
    next_generation: u32,
    slots: BTreeMap<u64, Probe>,
}

fn registry() -> &'static Mutex<Probes> {
    static INSTANCE: OnceLock<Mutex<Probes>> = OnceLock::new();
    INSTANCE.get_or_init(|| Mutex::new(Probes {
        next_generation: 1,
        slots: BTreeMap::new(),
    }))
}

fn probe_prepare(raw: &[u8], boundary: u32) -> Result<u64, i32> {
    let data = UntrustedColdV4::parse(raw).map_err(|_| INVALID)?;
    let identity = data.identity();
    if !identity.server { return Err(INVALID); }
    let mut state = registry().lock().map_err(|_| BAD_STAGE)?;
    if state.slots.len() >= MAX_PROBES { return Err(FULL); }
    let generation = state.next_generation;
    state.next_generation = generation.checked_add(1).ok_or(FULL)?;
    let lane = LaneKey {
        tunnel: TunnelKey {slot: 1, generation},
        slot: u32::from(identity.go_lane_id),
        generation,
    };
    let expected = ExpectedRustOwner {
        lane, owner_generation:generation, logical_epoch:identity.logical_epoch,
        tunnel_id:identity.tunnel_id, go_lane_id:identity.go_lane_id,
        server:true,
    };
    data.preflight_untrusted_owner(&expected).map_err(|_| INVALID)?;
    // Separate locally minted opaque token; Go's wire epoch/lane is NOT a
    // Rust owner generation and cannot select an existing owner.
    let handle = (u64::from(generation) << 32) | 0x5642;
    let max_wire = usize::from(identity.server_limit);
    let fresh = QueueLimits {
        slots: 32, bytes:max_wire.saturating_mul(32), max_age_ns:50_000_000,
    };
    let rx = QueueLimits {
        slots:64, bytes:max_wire.saturating_mul(64), max_age_ns:50_000_000,
    };
    let Some(tx_owner) = TxOwner::new(fresh, fresh) else {return Err(INVALID)};
    let Some(rx_owner) = RxOwner::new(rx) else {return Err(INVALID)};
    let Some(owner) = ScopedOwner::new(handle,generation,lane,tx_owner,rx_owner)
        else {return Err(INVALID)};
    // Bounded owner-local test-only arena; input Go []byte is copied into a
    // uniquely owned Rust slab before the cgo call returns. No Go pointer kept.
    let Some(mut owner)=EarlyRxOwner::new(owner,EarlyLimits {
        slots:32,bytes:max_wire.saturating_mul(32),
    }) else {return Err(INVALID)};
    let token=owner.token();
    if owner.prepare(&token,u64::from(boundary)).is_err(){return Err(BAD_STAGE)}
    let Ok(arena)=Arena::new(generation,32,2048,32,1_000_000) else {return Err(INVALID)};
    state.slots.insert(handle, Probe {
        owner,token,arena,phase:PH_PREPARED,rx_boundary:boundary,
        staged_count:0,staged_bytes:0,drained:false,cold_identity:identity,
    });
    // No caller byte pointer is retained, and no production AEAD opener,
    // receiver route, positive FecOrigin or ABI feature was activated.
    Ok(handle)
}
// This stages the ACTUAL Go-owned DetachTransition packet bytes, but remains
// a test-only inert RX queue: NOT AEAD authentication and NOT a production lane.
fn probe_stage(handle:u64,seq:u32,bytes:&[u8])->i32 {
    let Ok(mut state)=registry().lock() else {return BAD_STAGE};
    let Some(p)=state.slots.get_mut(&handle) else {return UNKNOWN};
    if p.phase!=PH_PREPARED || p.drained{return BAD_STAGE;}
    let len=bytes.len();
    if len==0 || len>usize::from(p.cold_identity.server_limit) ||
       p.staged_count>=32 || p.staged_bytes.checked_add(len as u32).is_none(){
        return INVALID;
    }
    // TCP sequence wraps; use bounded signed-ahead distance only. Never
    // reinterpret a pre-boundary or opposite-half serial as fresh early RX.
    let distance=seq.wrapping_sub(p.rx_boundary);
    if distance>u32::from(p.cold_identity.server_limit).saturating_mul(MAX_EARLY) {
        return INVALID;
    }
    let Ok(mut buffer)=p.arena.allocate() else {return FULL};
    buffer.writable()[..len].copy_from_slice(bytes);
    match p.owner.offer(&p.token,buffer,0..len,
        u64::from(p.rx_boundary)+u64::from(distance),MonoNs(0)) {
        Ok(EarlyAccepted::Staged)=>{
            p.staged_count+=1;p.staged_bytes+=len as u32;OK
        }
        Ok(EarlyAccepted::Ready)=>BAD_STAGE,
        Err(_)=>INVALID,
    }
}

// An independent test-only digest of the bytes physically received by
// Rust's owned RX slabs after Detach; this does not decrypt or deliver traffic.
fn probe_drain(handle:u64)->Result<(u32,u32,u64),i32> {
    let Ok(mut state)=registry().lock() else {return Err(BAD_STAGE)};
    let Some(p)=state.slots.get_mut(&handle) else {return Err(UNKNOWN)};
    if p.phase!=PH_COMMITTED||p.drained{return Err(BAD_STAGE)}
    let batch=p.owner.drain_rx(&p.token,MonoNs(0),Vec::with_capacity(32))
        .map_err(|_|BAD_STAGE)?;
    let mut count=0u32;
    let mut len=0u32;
    let mut digest=0xcbf29ce484222325u64; // FNV-1a, matches Go hash/fnv
    // LoanBatch::recycle() intentionally DROPS all packet contents, it is
    // NOT a bytes-view API. Inspect the generation-bound borrowed slice
    // before dropping the batch, then let its ledger/arena return once.
    for packet in batch.as_slice() {
        count+=1;
        let data=&packet.buffer.m0_inert_probe_bytes()[packet.wire.clone()];
        len+=data.len() as u32;
        for byte in data.iter() {
            digest=(digest^u64::from(*byte)).wrapping_mul(0x100000001b3);
        }
    }
    drop(batch);
    if count!=p.staged_count||len!=p.staged_bytes{return Err(BAD_STAGE)}
    p.drained=true;
    Ok((count,len,digest))
}

fn probe_commit(handle:u64,early_count:u32,early_bytes:u32) -> i32 {
    let Ok(mut state)=registry().lock() else {return BAD_STAGE};
    let Some(probe)=state.slots.get_mut(&handle) else {return UNKNOWN};
    if probe.phase!=PH_PREPARED {return BAD_STAGE}
    let max_wire=u32::from(probe.cold_identity.server_limit);
    if early_count>32 || early_count!=probe.staged_count ||
       early_bytes!=probe.staged_bytes ||
       early_bytes>max_wire.saturating_mul(32) ||
       (early_count==0 && early_bytes!=0) ||
       (early_count>0 && early_bytes<early_count) {
        return INVALID;
    }
    // The Go protected reply and FakeTCP Detach were completed by the
    // private Go caller. Rust now moves all already-copied early bytes from
    // its staged, bounded owner into its inert RX, atomically.
    if probe.owner.detach(&probe.token).is_err(){return BAD_STAGE}
    probe.phase=PH_COMMITTED;
    OK
}
fn probe_abort(handle:u64)->i32 {
    let Ok(mut state)=registry().lock() else {return BAD_STAGE};
    let Some(p)=state.slots.get(&handle) else {return UNKNOWN};
    if p.phase==PH_COMMITTED {return OK} // Go defer abort after commit is benign
    if p.phase!=PH_PREPARED {return BAD_STAGE}
    if let Some(mut p)=state.slots.remove(&handle) {
        let _=p.owner.stop(&p.token);
        return OK;
    }
    UNKNOWN
}
fn probe_stop(handle:u64)->i32 {
    let Ok(mut state)=registry().lock() else {return BAD_STAGE};
    let Some(p)=state.slots.get_mut(&handle) else {return UNKNOWN};
    if p.phase==PH_STOPPED {return OK}
    if p.phase!=PH_COMMITTED {return BAD_STAGE}
    let Ok(retired)=p.owner.stop(&p.token) else {return BAD_STAGE};
    if !retired.ready.batch_handles_released(){return BAD_STAGE}
    p.phase=PH_STOPPED;
    OK
}
fn probe_release(handle:u64)->i32 {
    let Ok(mut state)=registry().lock() else {return BAD_STAGE};
    match state.slots.get(&handle) {
        None=>UNKNOWN,
        Some(p) if p.phase!=PH_STOPPED=>BAD_STAGE,
        Some(_)=>{state.slots.remove(&handle);OK},
    }
}
// All these C symbols are compiled ONLY under m0_v4_probe Linux feature.
// They intentionally do not authenticate caller bytes; production links do
// not contain them and capability reporting always remains features=0.
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_test_probe_prepare(
    bytes:*const u8,len:usize,boundary:u32,out:*mut u64
)->i32 {
    if bytes.is_null()||out.is_null()||len!=COLD_V4_LEN {return INVALID}
    // SAFETY: input is borrowed strictly for this synchronous call, C Go
    // wrapper supplies a valid length/pointer and holds the backing array.
    let data=unsafe{std::slice::from_raw_parts(bytes,len)};
    match probe_prepare(data,boundary) {
        Ok(handle)=>{
            // SAFETY: out was validated and the C caller owns a u64 slot.
            unsafe{out.write(handle)};
            OK
        },
        Err(e)=>e,
    }
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_test_probe_stage(
    handle:u64,seq:u32,data:*const u8,len:usize
)->i32 {
    if data.is_null()||len==0||len>2048{return INVALID}
    // SAFETY: cgo keeps one Go-owned nonempty []byte alive for this strictly
    // synchronous call; copy occurs before returning to Go.
    let bytes=unsafe{std::slice::from_raw_parts(data,len)};
    probe_stage(handle,seq,bytes)
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_test_probe_drain(
    handle:u64,count:*mut u32,bytes:*mut u32,digest:*mut u64
)->i32 {
    if count.is_null()||bytes.is_null()||digest.is_null(){return INVALID}
    match probe_drain(handle) {
        Ok((n,len,hash))=>{
            // SAFETY: caller supplied valid owned integer output slots.
            unsafe{count.write(n);bytes.write(len);digest.write(hash)};
            OK
        }
        Err(e)=>e,
    }
}
#[no_mangle]
pub extern "C" fn wbd_m0_test_probe_commit(handle:u64,n:u32,bytes:u32)->i32{
    probe_commit(handle,n,bytes)
}
#[no_mangle]
pub extern "C" fn wbd_m0_test_probe_abort(handle:u64)->i32{
    probe_abort(handle)
}
#[no_mangle]
pub extern "C" fn wbd_m0_test_probe_stop(handle:u64)->i32{
    probe_stop(handle)
}
#[no_mangle]
pub extern "C" fn wbd_m0_test_probe_release(handle:u64)->i32{
    probe_release(handle)
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_test_probe_state(handle:u64,out:*mut u32)->i32 {
    if out.is_null(){return INVALID}
    let Ok(state)=registry().lock() else {return BAD_STAGE};
    let Some(p)=state.slots.get(&handle) else {return UNKNOWN};
    // SAFETY: output pointer checked and owned by the C caller.
    unsafe{out.write(p.phase)};
    OK
}

#[cfg(test)]
mod tests {
    use super::*;
    fn candidate()->[u8;COLD_V4_LEN]{
        let mut b=[0u8;COLD_V4_LEN];
        b[..4].copy_from_slice(b"WBCO");
        b[4..6].copy_from_slice(&1u16.to_be_bytes());
        b[6..8].copy_from_slice(&(COLD_V4_LEN as u16).to_be_bytes());
        b[8]=1;b[9]=1;b[10]=1;
        b[12..28].fill(1);b[28..44].fill(2);b[44..60].fill(3);
        b[60..62].copy_from_slice(&1400u16.to_be_bytes());
        b[62..64].copy_from_slice(&1400u16.to_be_bytes());
        b[64..96].fill(4);b[96..172].fill(5);b[172..].fill(6);
        b
    }
    #[test]
    fn r0_m0_native_probe_local_fresh_generation_and_bounded_phases(){
        let a=candidate();
        let first=probe_prepare(&a,0).unwrap();
        assert_eq!(probe_commit(first,65,65),INVALID);
        assert_eq!(probe_commit(first,1,1401*64),INVALID);
        assert_eq!(probe_stop(first),BAD_STAGE);
        assert_eq!(probe_commit(first,0,0),OK);
        assert_eq!(probe_commit(first,0,0),BAD_STAGE);
        assert_eq!(probe_abort(first),OK);
        assert_eq!(probe_stop(first),OK);
        assert_eq!(probe_release(first),OK);
        let second=probe_prepare(&a,100).unwrap();
        assert_ne!(first,second);
        assert_eq!(probe_stage(second,99,&[1]),INVALID);
        assert_eq!(probe_stage(second,100,&[11,22,33]),OK);
        assert_eq!(probe_stage(second,103,&[44,55]),OK);
        assert_eq!(probe_commit(second,1,5),INVALID); // metadata can't lie
        assert_eq!(probe_commit(second,2,5),OK);
        let (n,bytes,digest)=probe_drain(second).unwrap();
        let expected=[11u8,22,33,44,55].iter().fold(0xcbf29ce484222325u64,
            |v,b|(v^u64::from(*b)).wrapping_mul(0x100000001b3));
        assert_eq!((n,bytes,digest),(2,5,expected));
        assert_eq!(probe_drain(second).err(),Some(BAD_STAGE));
        assert_eq!(probe_stop(second),OK);
        assert_eq!(probe_release(second),OK);
        let third=probe_prepare(&a,100).unwrap();
        assert_ne!(third,second);
        assert_eq!(probe_abort(third),OK);
        assert_eq!(probe_commit(second,0,0),UNKNOWN);
        let mut corrupt=a;corrupt[0]=0;
        assert_eq!(probe_prepare(&corrupt,0).err(),Some(INVALID));
        let mut forged_client=a;forged_client[8]=0;
        assert_eq!(probe_prepare(&forged_client,0).err(),Some(INVALID));
    }
}
