//! M0 TEST-ONLY *inactive* native Go/Rust bridge. No production feature or
//! authenticated C ABI is published. A caller-supplied 248-byte bundle is
//! merely a candidate, even if structurally valid; ONLY the private Go
//! credential-checked callsite is a potential future positive authority.
//! This probe owns a NEW ScopedOwner generation in Rust and exercises stage,
//! commit and stop transitions, but it does NOT install business AEAD/FEC.
#![allow(clippy::missing_safety_doc)]

use std::collections::BTreeMap;
use std::sync::{Mutex, OnceLock};

use wbd_types::{LaneKey, TunnelKey};
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
    owner: ScopedOwner,
    token: ScopeToken,
    phase: u32,
    _rx_boundary: u32,
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
    let token = owner.token();
    state.slots.insert(handle, Probe {
        owner,token,phase:PH_PREPARED,_rx_boundary:boundary,
        cold_identity:identity,
    });
    // No caller byte pointer is retained, and no production AEAD opener,
    // receiver route, positive FecOrigin or ABI feature was activated.
    Ok(handle)
}
fn probe_commit(handle:u64,early_count:u32,early_bytes:u32) -> i32 {
    let Ok(mut state)=registry().lock() else {return BAD_STAGE};
    let Some(probe)=state.slots.get_mut(&handle) else {return UNKNOWN};
    if probe.phase!=PH_PREPARED {return BAD_STAGE}
    let max_wire=u32::from(probe.cold_identity.server_limit);
    if early_count>MAX_EARLY ||
       early_bytes>max_wire.saturating_mul(MAX_EARLY) ||
       (early_count==0 && early_bytes!=0) ||
       (early_count>0 && early_bytes<early_count) {
        return INVALID;
    }
    // Metadata-only receipt of Go Detach evidence, not yet early payload RX
    // or positive packet delivery. Keeping it inert is intentional.
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
    if !retired.batch_handles_released(){return BAD_STAGE}
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
        let second=probe_prepare(&a,0).unwrap();
        assert_ne!(first,second);
        assert_eq!(probe_abort(second),OK);
        assert_eq!(probe_commit(second,0,0),UNKNOWN);
        let mut corrupt=a;corrupt[0]=0;
        assert_eq!(probe_prepare(&corrupt,0).err(),Some(INVALID));
        let mut forged_client=a;forged_client[8]=0;
        assert_eq!(probe_prepare(&forged_client,0).err(),Some(INVALID));
    }
}
