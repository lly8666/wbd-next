//! R0 native ABI sentinel, NOT a steady data engine.
//! Production dataplane features remain 0 until independently qualified.
//! C ABI is owned by engine alone; wbd-types stays pure Rust and no pointers
//! or arena BufferKeys ever cross this FFI boundary.

// M0-owned composition hooks. Worker M1 owns the implementations below.
#[path = "runtime/mod.rs"]
pub mod runtime;
/// Staged M0 M1→M3 FEC2 parity batches; wire kinds and capability remain disabled.
pub mod fec2_staged;
/// M0 continuous original-owner Fixed source-first/parity composition.
/// Independent Go TLS/M4 integration still gates all real product capability.
mod v4_fixed_stream;
/// M0 one-owner adapter around frozen M1 GameTx/Rx with per-lane AEAD/PN.
/// Not a public Go product grant until real lanes are bound.
mod v4_game_lane;
#[cfg(feature="fec2_product_record")]
mod v4_game_fec;
/// Linux-only privileged same-Actions original-Go TLS Game2/4 actual M4
/// raw/TUN/UDP application ingress. Never a public capability or default run.
#[cfg(all(test,target_os="linux"))]
mod v4_game_kernel_linux_tests;
/// One original-Go TLS shared Game2/4 AEAD owner → real independent M4
/// raw/TUN packet drivers with joined Stop. Opt-in, product gate pending.
#[cfg(all(feature="fec2_product_record",target_os="linux",any(target_arch="x86_64",target_arch="aarch64"),any(target_env="gnu",target_env="musl")))]
mod v4_game_public_kernel;
/// Release-option original-owner persistent multi-block authenticated FEC RX
/// component only: not a live Go/kernel product route or public enablement.
#[cfg(feature="fec2_product_record")]
mod v4_fec2_live_rx;
#[path = "memory/mod.rs"]
pub mod memory;
/// M0 bounded authentication/receipt assembly; no production V4 enablement.
pub mod recovery_ingress;
/// M0-only V4 copied byte candidate grammar; never an authenticated installer.
pub mod cold_v4;
/// Normal-build crypto composition reused by the private Go native probe.
mod v4_owner_crypto;
// Versioned actual owner Prepare is in ordinary builds; test FFI only routes
// the already authenticated private Go callback into this same code.
mod v4_protected_handoff;
#[cfg(all(feature = "m0_v4_embedded_go", target_os = "linux"))]
mod v4_embedded_go;
// M0-shared private original-Go Windows lifecycle ABI. No Windows M4 device
// lease, OS applied status or product activation is granted by this module.
#[cfg(all(feature = "m0_v4_embedded_go", target_os = "windows"))]
mod v4_windows_owner;
#[cfg(all(feature = "m0_v4_probe", target_os = "linux"))]
mod v4_probe_bridge;

use std::sync::{Mutex, OnceLock};
use wbd_types::next_generation;

const ABI_VERSION: u32 = 1;
const ENGINE_KIND: u32 = 0x1000_0000;
const LANE_KIND: u32 = 0x2000_0000;
const SLOT_MASK: u32 = 0x0fff_ffff;
const ENGINE_LIMIT: usize = 4;
const LANE_LIMIT: usize = 16;

const OK: i32 = 0;
const NULL_ARG: i32 = 1;
const BAD_SIZE: i32 = 2;
const BAD_VERSION: i32 = 3;
const UNSUPPORTED: i32 = 4;
const STALE: i32 = 5;
const NO_CAPACITY: i32 = 6;
const INTERNAL: i32 = 7;

#[repr(C)]
#[derive(Clone, Copy, Debug)]
pub struct WbdAbiInfoV1 {
    pub abi_version: u32,
    pub struct_size: u32,
    pub features: u64,
    pub reserved: u64,
}
#[repr(C)]
#[derive(Clone, Copy, Debug)]
pub struct WbdAbiConfigV1 {
    pub abi_version: u32,
    pub struct_size: u32,
    pub flags: u32,
    pub reserved: u32,
}
#[repr(transparent)]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct WbdEngineToken(pub u64);
#[repr(transparent)]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct WbdLaneToken(pub u64);

#[derive(Default)]
struct EngineSlot { generation: u32, alive: bool }
#[derive(Default)]
struct LaneSlot { generation: u32, owner: u64, alive: bool }
#[derive(Default)]
struct Registry { engines: Vec<EngineSlot>, lanes: Vec<LaneSlot> }
static REGISTRY: OnceLock<Mutex<Registry>> = OnceLock::new();

fn registry() -> &'static Mutex<Registry> {
    REGISTRY.get_or_init(|| Mutex::new(Registry::default()))
}
fn encode(kind: u32, index: usize, generation: u32) -> u64 {
    ((generation as u64) << 32) | u64::from(kind | (index as u32 + 1))
}
fn decode(token: u64, kind: u32) -> Result<(usize, u32), i32> {
    let low = token as u32;
    let generation = (token >> 32) as u32;
    if low & !SLOT_MASK != kind || low & SLOT_MASK == 0 || generation == 0 {
        return Err(STALE);
    }
    Ok(((low & SLOT_MASK) as usize - 1, generation))
}
fn active_engine(r: &Registry, token: u64) -> Result<usize, i32> {
    let (index, generation) = decode(token, ENGINE_KIND)?;
    match r.engines.get(index) {
        Some(s) if s.alive && s.generation == generation => Ok(index),
        _ => Err(STALE),
    }
}
fn active_lane(r: &Registry, token: u64) -> Result<usize, i32> {
    let (index, generation) = decode(token, LANE_KIND)?;
    match r.lanes.get(index) {
        Some(s) if s.alive && s.generation == generation => Ok(index),
        _ => Err(STALE),
    }
}
fn alloc_engine(r: &mut Registry) -> Result<u64, i32> {
    if let Some((i,s)) = r.engines.iter_mut().enumerate()
        .find(|(_,s)| !s.alive && s.generation != u32::MAX)
    {
        s.generation = if s.generation == 0 { 1 } else { s.generation };
        s.alive = true;
        return Ok(encode(ENGINE_KIND, i, s.generation));
    }
    if r.engines.len() >= ENGINE_LIMIT { return Err(NO_CAPACITY); }
    r.engines.push(EngineSlot { generation: 1, alive: true });
    Ok(encode(ENGINE_KIND, r.engines.len()-1, 1))
}
fn alloc_lane(r: &mut Registry, owner: u64) -> Result<u64, i32> {
    active_engine(r, owner)?;
    if let Some((i,s)) = r.lanes.iter_mut().enumerate()
        .find(|(_,s)| !s.alive && s.generation != u32::MAX)
    {
        s.generation = if s.generation == 0 { 1 } else { s.generation };
        s.alive = true;
        s.owner = owner;
        return Ok(encode(LANE_KIND, i, s.generation));
    }
    if r.lanes.len() >= LANE_LIMIT { return Err(NO_CAPACITY); }
    r.lanes.push(LaneSlot { generation: 1, owner, alive: true });
    Ok(encode(LANE_KIND, r.lanes.len()-1, 1))
}
fn retire_lane(s: &mut LaneSlot) {
    s.alive = false;
    s.owner = 0;
    s.generation = next_generation(s.generation).unwrap_or(u32::MAX);
}
fn close_engine(r: &mut Registry, token: u64) -> Result<(), i32> {
    let index = active_engine(r, token)?;
    r.engines[index].alive = false;
    r.engines[index].generation = next_generation(r.engines[index].generation).unwrap_or(u32::MAX);
    for lane in &mut r.lanes {
        if lane.alive && lane.owner == token { retire_lane(lane); }
    }
    Ok(())
}
fn close_lane(r: &mut Registry, token: u64) -> Result<(), i32> {
    let index = active_lane(r, token)?;
    retire_lane(&mut r.lanes[index]);
    Ok(())
}
fn locked<F: FnOnce(&mut Registry) -> i32>(f: F) -> i32 {
    match registry().lock() {
        Ok(mut r) => f(&mut r),
        Err(_) => INTERNAL,
    }
}

// Caller must provide aligned, writable memory; pointer validity except NULL
// cannot be checked at C ABI. Check sizes before touching output memory.
#[no_mangle]
pub extern "C" fn wbd_r0_abi_query(out: *mut WbdAbiInfoV1, out_size: u32) -> i32 {
    if out.is_null() { return NULL_ARG; }
    if out_size != std::mem::size_of::<WbdAbiInfoV1>() as u32 { return BAD_SIZE; }
    unsafe {
        out.write(WbdAbiInfoV1 {
            abi_version: ABI_VERSION, struct_size: out_size,
            features: 0, reserved: 0,
        });
    }
    OK
}
#[no_mangle]
pub extern "C" fn wbd_r0_engine_open(config: *const WbdAbiConfigV1, input_size: u32, out: *mut WbdEngineToken) -> i32 {
    if config.is_null() || out.is_null() { return NULL_ARG; }
    // Reject an older/shorter descriptor before reading any config bytes.
    if input_size != std::mem::size_of::<WbdAbiConfigV1>() as u32 { return BAD_SIZE; }
    // ABI v1 callers guarantee config points to input_size aligned bytes.
    let cfg = unsafe { config.read() };
    if cfg.struct_size != std::mem::size_of::<WbdAbiConfigV1>() as u32 { return BAD_SIZE; }
    if cfg.abi_version != ABI_VERSION { return BAD_VERSION; }
    if cfg.flags != 0 || cfg.reserved != 0 { return UNSUPPORTED; }
    locked(|r| match alloc_engine(r) {
        Ok(token) => {unsafe {out.write(WbdEngineToken(token))}; OK}
        Err(e) => e,
    })
}
#[no_mangle]
pub extern "C" fn wbd_r0_engine_close(token: WbdEngineToken) -> i32 {
    locked(|r| match close_engine(r, token.0) { Ok(()) => OK, Err(e) => e })
}
#[no_mangle]
pub extern "C" fn wbd_r0_lane_open(engine: WbdEngineToken, out: *mut WbdLaneToken) -> i32 {
    if out.is_null() { return NULL_ARG; }
    locked(|r| match alloc_lane(r, engine.0) {
        Ok(token) => {unsafe {out.write(WbdLaneToken(token))}; OK}
        Err(e) => e,
    })
}
#[no_mangle]
pub extern "C" fn wbd_r0_lane_close(token: WbdLaneToken) -> i32 {
    locked(|r| match close_lane(r, token.0) { Ok(()) => OK, Err(e) => e })
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn r0_abi_token_domains_and_generation() {
        let mut r = Registry::default();
        let engine = alloc_engine(&mut r).unwrap();
        let lane = alloc_lane(&mut r, engine).unwrap();
        assert_eq!(active_engine(&r, lane), Err(STALE));
        assert_eq!(active_lane(&r, engine), Err(STALE));
        close_lane(&mut r, lane).unwrap();
        assert_eq!(active_lane(&r,lane),Err(STALE));
        let new_lane = alloc_lane(&mut r, engine).unwrap();
        assert_ne!(lane,new_lane);
        close_engine(&mut r,engine).unwrap();
        assert_eq!(active_lane(&r,new_lane),Err(STALE));
        let new_engine = alloc_engine(&mut r).unwrap();
        assert_ne!(engine,new_engine);
    }
    #[test]
    fn r0_abi_never_wraps_generations() {
        let mut r=Registry::default();
        r.engines.push(EngineSlot {generation: u32::MAX, alive: true});
        let token=encode(ENGINE_KIND,0,u32::MAX);
        close_engine(&mut r,token).unwrap();
        let next=alloc_engine(&mut r).unwrap();
        assert_ne!(token,next);
        assert_eq!(decode(next,ENGINE_KIND).unwrap().0,1);
        r.lanes.push(LaneSlot {generation: u32::MAX,owner:next,alive:true});
        let lane=encode(LANE_KIND,0,u32::MAX);
        close_lane(&mut r,lane).unwrap();
        let next_lane=alloc_lane(&mut r,next).unwrap();
        assert_ne!(lane,next_lane);
        assert_eq!(decode(next_lane,LANE_KIND).unwrap().0,1);
    }
    #[test]
    fn r0_abi_capacity_rejects_without_stealing_live_tokens() {
        let mut r=Registry::default();
        let e:Vec<u64>=(0..ENGINE_LIMIT).map(|_|alloc_engine(&mut r).unwrap()).collect();
        assert_eq!(alloc_engine(&mut r),Err(NO_CAPACITY));
        for token in &e {assert!(active_engine(&r,*token).is_ok());}
        let lane_tokens:Vec<u64>=(0..LANE_LIMIT).map(|_|alloc_lane(&mut r,e[0]).unwrap()).collect();
        assert_eq!(alloc_lane(&mut r,e[0]),Err(NO_CAPACITY));
        for token in lane_tokens {assert!(active_lane(&r,token).is_ok());}
    }
}
