//! M3-013: P0 component cost ONLY, NOT product throughput or authenticated V4 provenance.
//! No production origin constructor, timers, networking, or crypto stand-in.
//! AEAD-only and FEC-enabled both Open actual independently keyed ChaCha records
//! with unique PNs; absent-origin intentionally does NOT decrypt (fail-closed).
#![allow(clippy::too_many_lines)]
use crate::fec_auth_gate::{AdmissionError, AuthFecScopeGate, FecOrigin};
use crate::fec_block_id::{IdConfig, IdError};
use crate::fec_rx::{Config as RxConfig, Direction};
use crate::fec_tx::FecTxOwner;
use crate::record_crypto::{CryptoError, DirectionKeys, LaneTxCrypto, RecordSuite};
use crate::record_frame::{FIXED_WIRE_OVERHEAD, MAX_WIRE_LEN};
use crate::record_replay::{ReplayProtectedLaneRx, ReplayWindowConfig, UniqueOpenError};
use std::hint::black_box;
use std::time::{Duration, Instant};

const LANE: u64 = 51;
const EPOCH: u64 = 9;
const RECORDS_PER_SCOPE: usize = 16;
const SCOPE_COUNT: usize = 4;
const RECORDS_PER_BATCH: usize = RECORDS_PER_SCOPE * SCOPE_COUNT;
const SUITE: RecordSuite = RecordSuite::ChaCha20Poly1305;
// Two tunnels, both directions, separate real AEAD/HP keys and PN=0 per scope.
const SCOPES: [(u64, Direction, u8); SCOPE_COUNT] = [
    (101, Direction::ClientToServer, 0x21),
    (101, Direction::ServerToClient, 0x31),
    (202, Direction::ClientToServer, 0x41),
    (202, Direction::ServerToClient, 0x51),
];
fn keys(seed: u8) -> DirectionKeys {
    DirectionKeys {
        aead_key: [seed; 32],
        iv: [seed.wrapping_add(1); 12],
        hp_key: [seed.wrapping_add(2); 32],
    }
}
fn replay() -> ReplayWindowConfig {
    ReplayWindowConfig {
        pn_per_second: 1000,
        cache_horizon_ms: 100,
        fec_horizon_ms: 100,
        rtt_ms: 0,
        metadata_budget_bytes: 80,
    }
}
fn gate(tunnel: u64, direction: Direction, seed: u8, bound: bool) -> AuthFecScopeGate {
    AuthFecScopeGate::new(
        keys(seed), SUITE, MAX_WIRE_LEN, replay(),
        IdConfig {
            epoch: EPOCH, direction, anchor: 0, retired_floor: 0,
            max_forward: 1024, max_reorder: 1024,
            max_heavy: 4, max_compact: 4,
        },
        RxConfig {
            epoch: EPOCH, direction, max_wire: 1500,
            max_heavy_bytes: 4096, max_heavy_blocks: 4,
            max_compact_blocks: 4, first_id_ext: 1,
        },
        LANE, tunnel,
        bound.then(|| FecOrigin::test_only(LANE, tunnel, EPOCH, direction, 0)),
    ).unwrap()
}
struct Case {
    tunnel: u64,
    direction: Direction,
    seed: u8,
    sealed: Vec<Vec<u8>>,
}
struct Corpus {
    cases: Vec<Case>,
    wire_bytes_per_batch: usize,
    shard_bytes_per_batch: usize,
}
fn corpus(shard_len: usize) -> Corpus {
    assert!(matches!(shard_len, 192 | 896));
    let mut cases = Vec::new();
    let mut wire_bytes = 0;
    let mut shard_bytes = 0;
    for &(tunnel, direction, seed) in &SCOPES {
        let mut sealer = LaneTxCrypto::new_for_suite(keys(seed), MAX_WIRE_LEN, SUITE).unwrap();
        let mut sealed = Vec::new();
        let shard = vec![seed; shard_len];
        for block in 1..=RECORDS_PER_SCOPE as u64 {
            // A distinct live BlockID on each record exercises bounded pressure,
            // not the trivial same-block fast path. Only a systematic shard is sent.
            let mut tx = FecTxOwner::new(block, 10_000).unwrap();
            let out = tx.submit(&shard, 0, 4, 1500, false).unwrap();
            assert_eq!(out.systematic.len(), 1);
            let frame = &out.systematic[0];
            let mut record = vec![0u8; FIXED_WIRE_OVERHEAD + frame.len()];
            record[14..14 + frame.len()].copy_from_slice(frame);
            sealer.seal_in_place(0, &mut record, frame.len(), 0).unwrap();
            shard_bytes += frame.len();
            wire_bytes += record.len();
            sealed.push(record);
        }
        cases.push(Case { tunnel, direction, seed, sealed });
    }
    Corpus {
        cases,
        wire_bytes_per_batch: wire_bytes,
        shard_bytes_per_batch: shard_bytes,
    }
}
#[derive(Clone, Copy, Debug)]
enum Mode { AeadOnly, AuthFec, AbsentOrigin }
impl Mode {
    fn name(self) -> &'static str {
        match self {
            Self::AeadOnly => "aead_unique_pn",
            Self::AuthFec => "postauth_fec",
            Self::AbsentOrigin => "absent_origin_deny_before_aead",
        }
    }
}
// The wire corpus is pre-sealed OUTSIDE the timer. Each batch creates fresh
// owner state so every PN is unique within its authenticated lane; it never
// replays old ciphertext as a fake successful measurement. Same wire bytes,
// same scratch copy, and same per-scope keys across compared paths.
fn batch(mode: Mode, input: &Corpus, scratch: &mut Vec<u8>) {
    let mut accepted = 0usize;
    for c in &input.cases {
        match mode {
            Mode::AeadOnly => {
                let mut rx = ReplayProtectedLaneRx::new_for_suite(
                    keys(c.seed), MAX_WIRE_LEN, SUITE, replay(),
                ).unwrap();
                for frame in &c.sealed {
                    scratch.resize(frame.len(), 0);
                    scratch.copy_from_slice(frame);
                    let opened = rx.open_unique_in_place(scratch).unwrap();
                    assert_eq!(opened.kind, 0);
                    accepted += usize::from(opened.payload.len() > 0);
                    black_box(opened.payload.len());
                }
                assert_eq!(rx.stats().delivered, RECORDS_PER_SCOPE as u64);
            }
            Mode::AuthFec | Mode::AbsentOrigin => {
                let mut rx = gate(c.tunnel, c.direction, c.seed, matches!(mode, Mode::AuthFec));
                for frame in &c.sealed {
                    scratch.resize(frame.len(), 0);
                    scratch.copy_from_slice(frame);
                    if matches!(mode, Mode::AuthFec) {
                        let out = rx.accept_record_on_lane(scratch, LANE, c.tunnel, 100).unwrap();
                        assert!(out.recovered.is_empty());
                        accepted += out.systematic.len();
                        black_box(out);
                    } else {
                        assert_eq!(
                            rx.accept_record_on_lane(scratch, LANE, c.tunnel, 100),
                            Err(AdmissionError::AbsentOrigin)
                        );
                    }
                }
                if matches!(mode, Mode::AuthFec) {
                    let stats = rx.block_id_stats();
                    assert_eq!(rx.stats().delivered_systematic, RECORDS_PER_SCOPE as u64);
                    assert!(stats.heavy <= 4 && stats.compact <= 4);
                    assert!(rx.fec_stats().heavy <= 4 && rx.fec_stats().compact <= 4);
                    assert!(stats.pressure_compactions > 0);
                    rx.expire(14_000);
                    assert_eq!(rx.fec_stats().heavy, 0);
                    assert_eq!(rx.fec_stats().compact, 0);
                } else {
                    assert_eq!(rx.stats().denied_before_open, RECORDS_PER_SCOPE as u64);
                    assert_eq!(rx.stats().replay_rejected, 0);
                    assert_eq!(rx.block_id_stats().distinct_accepted, 0);
                }
            }
        }
    }
    let expected = if matches!(mode, Mode::AbsentOrigin) { 0 } else { RECORDS_PER_BATCH };
    assert_eq!(accepted, expected);
    black_box(accepted);
}
#[test]
fn r1_p0_postauth_multiscope_adversarial_bounded_retirement_isolation() {
    let input = corpus(192);
    let a = &input.cases[0];
    let b = &input.cases[2];
    let mut ga = gate(a.tunnel, a.direction, a.seed, true);
    let mut gb = gate(b.tunnel, b.direction, b.seed, true);
    let first_a = a.sealed[0].clone();
    let first_b = b.sealed[0].clone();
    assert_eq!(
        gb.accept_record_on_lane(&mut first_a.clone(), LANE, a.tunnel, 100),
        Err(AdmissionError::WrongTunnel)
    );
    assert!(matches!(
        gb.accept_record_on_lane(&mut first_a.clone(), LANE, b.tunnel, 100),
        Err(AdmissionError::Replay(UniqueOpenError::InvalidRecord(CryptoError::Authentication)))
    ));
    assert_eq!(gb.stats().delivered_systematic, 0);
    assert_eq!(gb.block_id_stats().distinct_accepted, 0);
    assert_eq!(
        gb.accept_record_on_lane(&mut first_b.clone(), LANE, b.tunnel, 101)
            .unwrap().systematic.len(), 1
    );
    assert_eq!(
        ga.accept_record_on_lane(&mut first_a.clone(), LANE, a.tunnel, 101)
            .unwrap().systematic.len(), 1
    );
    assert_eq!(
        ga.accept_record_on_lane(&mut first_a.clone(), LANE, a.tunnel, 102),
        Err(AdmissionError::Replay(UniqueOpenError::Duplicate))
    );
    for frame in &a.sealed[1..] {
        assert_eq!(
            ga.accept_record_on_lane(&mut frame.clone(), LANE, a.tunnel, 200)
                .unwrap().systematic.len(), 1
        );
        assert!(ga.block_id_stats().heavy <= 4);
        assert!(ga.block_id_stats().compact <= 4);
        assert!(ga.fec_stats().heavy <= 4);
        assert!(ga.fec_stats().compact <= 4);
    }
    assert!(ga.block_id_stats().retired_floor > 0);
    assert_eq!(gb.block_id_stats().retired_floor, 0);
    ga.expire(14_000);
    assert_eq!(ga.fec_stats().heavy, 0);
    assert_eq!(ga.fec_stats().compact, 0);
    assert_eq!(gb.fec_stats().heavy, 1);
    assert_eq!(gb.stats().delivered_systematic, 1);
    // A fresh authenticated PN=16 carrying retired BlockID=1 must be
    // rejected AFTER actual AEAD and replay, not merely as an old PN replay.
    let mut sender = LaneTxCrypto::new_for_suite(keys(a.seed), MAX_WIRE_LEN, SUITE).unwrap();
    let mut old_block = FecTxOwner::new(1, 10_000).unwrap();
    let old_frame = old_block.submit(&vec![a.seed; 192], 0, 4, 1500, false)
        .unwrap().systematic.remove(0);
    for _ in 0..RECORDS_PER_SCOPE {
        let mut burn = vec![0; FIXED_WIRE_OVERHEAD + old_frame.len()];
        burn[14..14 + old_frame.len()].copy_from_slice(&old_frame);
        sender.seal_in_place(0, &mut burn, old_frame.len(), 0).unwrap();
    }
    let mut late = vec![0; FIXED_WIRE_OVERHEAD + old_frame.len()];
    late[14..14 + old_frame.len()].copy_from_slice(&old_frame);
    sender.seal_in_place(0, &mut late, old_frame.len(), 0).unwrap();
    assert_eq!(
        ga.accept_record_on_lane(&mut late, LANE, a.tunnel, 14_001),
        Err(AdmissionError::BlockId(IdError::Retired))
    );
    assert_eq!(gb.stats().delivered_systematic, 1);
}
#[cfg(target_os = "linux")]
fn thread_cpu_ticks() -> u64 {
    // Field 14+15 of /proc/thread-self/stat; after the final ')' field3 is index0.
    // Thread-local CPU avoids concurrent unrelated Rust tests affecting CPU-s.
    let text = std::fs::read_to_string("/proc/thread-self/stat").expect("Linux thread CPU");
    let tail = text.rsplit_once(')').expect("stat comm").1;
    let fields: Vec<&str> = tail.split_whitespace().collect();
    fields[11].parse::<u64>().unwrap() + fields[12].parse::<u64>().unwrap()
}
#[cfg(target_os = "linux")]
fn cpu_hz() -> f64 {
    let output = std::process::Command::new("getconf")
        .arg("CLK_TCK").output().expect("Linux getconf CLK_TCK");
    assert!(output.status.success());
    String::from_utf8(output.stdout).unwrap().trim().parse::<f64>().unwrap()
}
#[cfg(target_os = "linux")]
fn percentile(values: &mut [u64], percent: usize) -> u64 {
    values.sort_unstable();
    values[(values.len() - 1) * percent / 100]
}
#[cfg(target_os = "linux")]
#[test]
fn r1_p0_postauth_real_aead_cpu_seconds_bytes_and_percentiles() {
    const SAMPLE_CAP: usize = 1024;
    const MEASURE_MS: u64 = 1125;
    const WARMUP_MS: u64 = 150;
    let ticks_per_second = cpu_hz();
    for shard_len in [192, 896] {
        let c = corpus(shard_len);
        assert_eq!(c.cases.len(), SCOPE_COUNT);
        assert_eq!(c.cases.iter().map(|s| s.sealed.len()).sum::<usize>(), RECORDS_PER_BATCH);
        let mut scratch = Vec::with_capacity(FIXED_WIRE_OVERHEAD + 56 + shard_len);
        // Reversing the order prevents one always-cold/always-warm mode.
        for (repeat, order) in [
            [Mode::AeadOnly, Mode::AuthFec, Mode::AbsentOrigin],
            [Mode::AbsentOrigin, Mode::AuthFec, Mode::AeadOnly],
            [Mode::AeadOnly, Mode::AuthFec, Mode::AbsentOrigin],
        ].into_iter().enumerate() {
            for mode in order {
                let warmup = Instant::now();
                while warmup.elapsed() < Duration::from_millis(WARMUP_MS) {
                    batch(mode, &c, &mut scratch);
                }
                let start_cpu = thread_cpu_ticks();
                let start = Instant::now();
                let mut batches = 0u64;
                let mut samples = Vec::with_capacity(SAMPLE_CAP);
                while start.elapsed() < Duration::from_millis(MEASURE_MS) {
                    let began = Instant::now();
                    batch(mode, &c, &mut scratch);
                    let per_record_ns = (began.elapsed().as_nanos()
                        / RECORDS_PER_BATCH as u128) as u64;
                    if samples.len() < SAMPLE_CAP {
                        samples.push(per_record_ns);
                    } else {
                        samples[(batches as usize) % SAMPLE_CAP] = per_record_ns;
                    }
                    batches += 1;
                }
                let wall_s = start.elapsed().as_secs_f64();
                let cpu_s = (thread_cpu_ticks() - start_cpu) as f64 / ticks_per_second;
                assert!(wall_s >= 1.0 && cpu_s >= 0.0 && batches > 0);
                assert!(!samples.is_empty());
                let records = batches * RECORDS_PER_BATCH as u64;
                let wire_bytes = batches as usize * c.wire_bytes_per_batch;
                let shard_bytes = batches as usize * c.shard_bytes_per_batch;
                // Percentiles are BATCH-AVERAGE elapsed ns/record, not packet latency.
                let (p50, p95, p99) = (
                    percentile(&mut samples.clone(), 50),
                    percentile(&mut samples.clone(), 95),
                    percentile(&mut samples, 99),
                );
                println!(
                    "M3_P0_COST component_only=true origin=test_only suite=chacha20poly1305 \
                     mode={} shard_len={} scopes=4 records_per_batch={} repeat={} \
                     wall_s={:.6} thread_cpu_s={:.6} records={} wire_bytes={} \
                     fec_frame_bytes={} ns_per_record_batch_p50={} \
                     ns_per_record_batch_p95={} ns_per_record_batch_p99={} \
                     cold_start_excluded=false transport=NOT_RUN throughput=NOT_QUALIFIED",
                    mode.name(), shard_len, RECORDS_PER_BATCH, repeat,
                    wall_s, cpu_s, records, wire_bytes, shard_bytes, p50, p95, p99
                );
            }
        }
    }
}


// M3-014: same-source RELEASE candidate, only M3-owned cfg(test) fixture.
// Authenticated RX state remains alive across all chunks, all warmups, and all
// 3 repetitions. Fresh PNs are minted on each scope's persistent true AEAD TX.
// Compared fresh-owner fixture uses the original M3-013 batch() on the SAME
// record size, same 2 tunnel x 2 direction keys, and same release runner.
// Preseal for steady mode occurs OUTSIDE measured CPU/wall spans.
#[cfg(target_os = "linux")]
const STEADY_CHUNK_PER_SCOPE: usize = RECORDS_PER_SCOPE;
#[cfg(target_os = "linux")]
enum ReusedRx {
    Unique(ReplayProtectedLaneRx),
    Fec(AuthFecScopeGate),
}
#[cfg(target_os = "linux")]
struct ReusedScope {
    tunnel: u64,
    seed: u8,
    tx: LaneTxCrypto,
    rx: ReusedRx,
    next_block: u64,
    delivered: u64,
}
#[cfg(target_os = "linux")]
fn reused_scopes(with_fec: bool) -> Vec<ReusedScope> {
    SCOPES.iter().map(|&(tunnel, direction, seed)| {
        let tx = LaneTxCrypto::new_for_suite(keys(seed), MAX_WIRE_LEN, SUITE).unwrap();
        let rx = if with_fec {
            ReusedRx::Fec(gate(tunnel, direction, seed, true))
        } else {
            ReusedRx::Unique(ReplayProtectedLaneRx::new_for_suite(
                keys(seed), MAX_WIRE_LEN, SUITE, replay()
            ).unwrap())
        };
        ReusedScope { tunnel, seed, tx, rx, next_block: 1, delivered: 0 }
    }).collect()
}
#[cfg(target_os = "linux")]
fn prepare_reused(scopes: &mut [ReusedScope], shard_len: usize)
    -> Vec<Vec<Vec<u8>>> {
    let mut batches = Vec::with_capacity(scopes.len());
    for s in scopes {
        let source = vec![s.seed; shard_len];
        let mut group = Vec::with_capacity(STEADY_CHUNK_PER_SCOPE);
        for _ in 0..STEADY_CHUNK_PER_SCOPE {
            let mut tx_fec = FecTxOwner::new(s.next_block, 10_000).unwrap();
            s.next_block = s.next_block.checked_add(1).unwrap();
            let emitted = tx_fec.submit(&source, 0, 4, 1500, false).unwrap();
            assert_eq!(emitted.systematic.len(), 1);
            let frame = &emitted.systematic[0];
            let mut wire = vec![0; FIXED_WIRE_OVERHEAD + frame.len()];
            wire[14..14+frame.len()].copy_from_slice(frame);
            s.tx.seal_in_place(0, &mut wire, frame.len(), 0).unwrap();
            group.push(wire);
        }
        batches.push(group);
    }
    batches
}
#[cfg(target_os = "linux")]
fn consume_reused(
    scopes: &mut [ReusedScope], wires: &[Vec<Vec<u8>>], scratch: &mut Vec<u8>,
) {
    let mut accepted = 0u64;
    for (s, group) in scopes.iter_mut().zip(wires) {
        for record in group {
            scratch.resize(record.len(), 0);
            scratch.copy_from_slice(record);
            match &mut s.rx {
                ReusedRx::Unique(rx) => {
                    let opened = rx.open_unique_in_place(scratch).unwrap();
                    assert_eq!(opened.kind, 0);
                    black_box(opened.payload.len());
                }
                ReusedRx::Fec(g) => {
                    let result = g.accept_record_on_lane(scratch, LANE, s.tunnel, 100).unwrap();
                    assert_eq!(result.systematic.len(), 1);
                    assert!(result.recovered.is_empty());
                    black_box(result);
                }
            }
            s.delivered += 1;
            accepted += 1;
        }
    }
    assert_eq!(accepted as usize, RECORDS_PER_BATCH);
    black_box(accepted);
}
#[cfg(target_os = "linux")]
fn check_reused(scopes: &[ReusedScope]) {
    for s in scopes {
        match &s.rx {
            ReusedRx::Unique(rx) => {
                assert_eq!(rx.stats().delivered, s.delivered);
                assert_eq!(rx.stats().duplicates, 0);
            }
            ReusedRx::Fec(g) => {
                assert_eq!(g.stats().delivered_systematic, s.delivered);
                assert_eq!(g.stats().replay_rejected, 0);
                let id = g.block_id_stats();
                let fec = g.fec_stats();
                assert!(id.heavy <= 4 && id.compact <= 4);
                assert!(fec.heavy <= 4 && fec.compact <= 4);
                assert!(id.retired_floor <= id.highest);
                assert_eq!(id.distinct_accepted, s.delivered);
                assert_eq!(id.highest, s.delivered);
            }
        }
    }
}
#[cfg(target_os = "linux")]
#[derive(Clone, Copy)]
enum ReuseCostLeg { FreshAead, SteadyAead, FreshFec, SteadyFec }
#[cfg(target_os = "linux")]
impl ReuseCostLeg {
    fn name(self) -> &'static str {
        match self {
            Self::FreshAead => "fresh_aead",
            Self::SteadyAead => "steady_aead",
            Self::FreshFec => "fresh_fec",
            Self::SteadyFec => "steady_fec",
        }
    }
}
// M3-015: same-window high-resolution Linux thread CPU clock, no unsafe FFI.
// schedstat field 1 is nanoseconds; when schedstats are disabled, sched
// se.sum_exec_runtime supplies decimal milliseconds at microsecond precision.
#[cfg(target_os = "linux")]
fn thread_runtime_ns() -> Option<(&'static str,u64)> {
    if let Ok(raw) = std::fs::read_to_string("/proc/thread-self/schedstat") {
        if let Some(ns) = raw.split_whitespace().next()
            .and_then(|v| v.parse::<u64>().ok()) {
            if ns>0 {return Some(("schedstat_ns",ns));}
        }
    }
    let raw=std::fs::read_to_string("/proc/thread-self/sched").ok()?;
    let t=raw.lines().find(|line|line.trim_start()
        .starts_with("se.sum_exec_runtime"))?.split_once(':')?.1.trim();
    let (whole,fraction)=t.split_once('.')?;
    if fraction.len()!=6 || !fraction.bytes().all(|ch|ch.is_ascii_digit()){
        return None;
    }
    let ns=whole.parse::<u64>().ok()?.checked_mul(1_000_000)?
        .checked_add(fraction.parse::<u64>().ok()?)?;
    (ns>0).then_some(("sched_runtime_us",ns))
}
#[cfg(target_os = "linux")]
#[derive(Debug,Clone,Copy,PartialEq,Eq)]
enum ClockError { ZeroWall, BackwardCpu, CpuOverWall }
#[cfg(target_os = "linux")]
fn validate_cpu_wall(wall:u128,start:Option<u64>,end:Option<u64>)
    ->Result<Option<u64>,ClockError>{
    if wall==0 {return Err(ClockError::ZeroWall);}
    let (Some(start),Some(end))=(start,end) else{return Ok(None)};
    if end<start {return Err(ClockError::BackwardCpu);}
    let cpu=end-start;
    if u128::from(cpu)*100>wall*102 {return Err(ClockError::CpuOverWall);}
    Ok(Some(cpu))
}
#[cfg(target_os = "linux")]
struct PairedClock {wall:Instant,cpu_start:Option<(&'static str,u64)>}
#[cfg(target_os = "linux")]
impl PairedClock {
    fn begin()->Self {
        // Wall begins BEFORE the first CPU probe, not after it.
        let wall=Instant::now();
        let cpu_start=thread_runtime_ns();
        Self{wall,cpu_start}
    }
    fn end(self)->(u128,Option<u64>,&'static str){
        // Wall ends AFTER the second CPU probe, not before it.
        let cpu_end=thread_runtime_ns();
        let wall=self.wall.elapsed().as_nanos();
        let backend=match (self.cpu_start,cpu_end) {
            (Some((a,_)),Some((b,_))) if a==b=>a,
            _=>"CPU_INCONCLUSIVE",
        };
        if backend=="CPU_INCONCLUSIVE" {return (wall,None,backend);}
        let cpu=validate_cpu_wall(wall,self.cpu_start.map(|(_,v)|v),
            cpu_end.map(|(_,v)|v)).unwrap_or_else(|e|
                panic!("M3_CLOCK_INVALID {e:?} wall_ns={wall} start={:?} end={cpu_end:?}",
                    self.cpu_start));
        (wall,cpu,backend)
    }
}
#[cfg(target_os = "linux")]
#[test]
fn r1_cpu_probe_same_window_valid_and_invalid_accounting() {
    assert_eq!(validate_cpu_wall(1000,Some(100),Some(1019)),Ok(Some(919)));
    assert_eq!(validate_cpu_wall(1000,Some(100),Some(1120)),Ok(Some(1020)));
    assert_eq!(validate_cpu_wall(1000,Some(100),Some(1121)),Err(ClockError::CpuOverWall));
    assert_eq!(validate_cpu_wall(1000,Some(100),Some(99)),Err(ClockError::BackwardCpu));
    assert_eq!(validate_cpu_wall(0,Some(100),Some(101)),Err(ClockError::ZeroWall));
    assert_eq!(validate_cpu_wall(1000,None,Some(100)),Ok(None));
    assert_eq!(validate_cpu_wall(1000,Some(100),None),Ok(None));
    let clock=PairedClock::begin();
    black_box((0..1024u32).fold(0u32,u32::wrapping_add));
    let (wall,cpu,backend)=clock.end();
    assert!(wall>0 && (cpu.is_some() || backend=="CPU_INCONCLUSIVE"));
}
#[cfg(target_os = "linux")]
struct ReuseCostResult {
    active_wall_ns:u128,
    cpu_ns:Option<u128>,
    backend:&'static str,
    clock_windows:u64,
    records:u64,
    p50_batch_avg_ns:u64,
    p99_batch_avg_ns:u64,
    samples:usize,
    raw_windows:Vec<(u128,Option<u64>,&'static str)>,
    raw_batch_samples:Vec<u64>,
}
#[cfg(target_os = "linux")]
fn measure_reuse_leg(
    leg: ReuseCostLeg, source:&Corpus, shard_len:usize,
    aead:&mut [ReusedScope], fec:&mut [ReusedScope],
    scratch:&mut Vec<u8>, target:Duration,
)->ReuseCostResult{
    // Batch 128 consecutive groups of 64 per clock window, so we do NOT
    // charge high-resolution CPU probes once for every 64 records.
    // Produce all unique-PN AEAD ciphertext before starting that window;
    // a persistent RX context consumes each ciphertext exactly once.
    const BATCHES_PER_WINDOW:usize=128;
    let mut active_ns=0u128;
    let mut cpu_total=0u128;
    let mut cpu_valid=true;
    let mut backend="CPU_INCONCLUSIVE";
    let mut windows=0u64;
    let mut count=0u64;
    let mut samples=Vec::with_capacity(2048);
    let mut raw_windows=Vec::new();
    while active_ns<target.as_nanos() || count==0{
        let staged=match leg{
            ReuseCostLeg::SteadyAead=>Some(
                (0..BATCHES_PER_WINDOW).map(|_|prepare_reused(aead,shard_len))
                    .collect::<Vec<_>>()),
            ReuseCostLeg::SteadyFec=>Some(
                (0..BATCHES_PER_WINDOW).map(|_|prepare_reused(fec,shard_len))
                    .collect::<Vec<_>>()),
            _=>None,
        };
        let clock=PairedClock::begin();
        for i in 0..BATCHES_PER_WINDOW{
            let started=Instant::now();
            match leg{
                ReuseCostLeg::FreshAead=>batch(Mode::AeadOnly,source,scratch),
                ReuseCostLeg::FreshFec=>batch(Mode::AuthFec,source,scratch),
                ReuseCostLeg::SteadyAead=>
                    consume_reused(aead,&staged.as_ref().unwrap()[i],scratch),
                ReuseCostLeg::SteadyFec=>
                    consume_reused(fec,&staged.as_ref().unwrap()[i],scratch),
            }
            let per_record=(started.elapsed().as_nanos()/RECORDS_PER_BATCH as u128) as u64;
            if samples.len()<samples.capacity(){
                samples.push(per_record);
            }else{
                samples[(count/RECORDS_PER_BATCH as u64) as usize%2048]=per_record;
            }
            count+=RECORDS_PER_BATCH as u64;
        }
        let (elapsed,cpu,kind)=clock.end();
        active_ns+=elapsed;
        raw_windows.push((elapsed,cpu,kind));
        windows+=1;
        if backend=="CPU_INCONCLUSIVE" {backend=kind;}
        if cpu.is_none() || kind!=backend {cpu_valid=false;}
        if let Some(cpu)=cpu {cpu_total+=u128::from(cpu);}
    }
    check_reused(aead);
    check_reused(fec);
    let p50=percentile(&mut samples.clone(),50);
    let p99=percentile(&mut samples.clone(),99);
    if cpu_valid {
        assert!(cpu_total*100<=active_ns*102,
            "M3_CLOCK_INVALID sum_cpu_ns={cpu_total} sum_wall_ns={active_ns}");
    }
    ReuseCostResult{
        active_wall_ns:active_ns,cpu_ns:cpu_valid.then_some(cpu_total),
        backend:if cpu_valid{backend}else{"CPU_INCONCLUSIVE"},
        clock_windows:windows,records:count,p50_batch_avg_ns:p50,
        p99_batch_avg_ns:p99,samples:samples.len(),
        raw_windows,raw_batch_samples:samples,
    }
}
#[cfg(target_os = "linux")]
#[test]
fn r1_steady_four_scope_auth_replay_pressure_and_independent_expiry() {
    let mut lanes = reused_scopes(true);
    let mut scratch = Vec::new();
    let staged = prepare_reused(&mut lanes, 192);
    let copy_a = staged[0][0].clone();
    let copy_b = staged[2][0].clone();
    let (left, right) = lanes.split_at_mut(2);
    let ReusedRx::Fec(ga) = &mut left[0].rx else { panic!("no FEC gate") };
    let ReusedRx::Fec(gb) = &mut right[0].rx else { panic!("no FEC gate") };
    assert_eq!(gb.accept_record_on_lane(&mut copy_a.clone(), LANE, left[0].tunnel, 1),
        Err(AdmissionError::WrongTunnel));
    assert!(matches!(
        gb.accept_record_on_lane(&mut copy_a.clone(), LANE, right[0].tunnel, 1),
        Err(AdmissionError::Replay(UniqueOpenError::InvalidRecord(CryptoError::Authentication)))
    ));
    assert_eq!(ga.accept_record_on_lane(&mut copy_a.clone(), LANE, left[0].tunnel, 2)
        .unwrap().systematic.len(), 1);
    assert_eq!(gb.accept_record_on_lane(&mut copy_b.clone(), LANE, right[0].tunnel, 2)
        .unwrap().systematic.len(), 1);
    assert_eq!(ga.accept_record_on_lane(&mut copy_a.clone(), LANE, left[0].tunnel, 3),
        Err(AdmissionError::Replay(UniqueOpenError::Duplicate)));
    ga.expire(14_000);
    assert_eq!(ga.fec_stats().heavy, 0);
    assert_eq!(ga.fec_stats().compact, 0);
    assert_eq!(gb.fec_stats().heavy, 1);
    assert_eq!(gb.block_id_stats().retired_floor, 0);
    // The other two independent direction contexts are still untouched and
    // each can accept a real fresh PN0 and BlockID1.
    for index in [1usize, 3] {
        let tunnel = lanes[index].tunnel;
        let ReusedRx::Fec(g) = &mut lanes[index].rx else { panic!("not a gate") };
        scratch.clear();
        scratch.extend_from_slice(&staged[index][0]);
        assert_eq!(g.accept_record_on_lane(&mut scratch, LANE, tunnel, 2)
            .unwrap().systematic.len(), 1);
    }
}
#[cfg(target_os = "linux")]
#[test]
fn r1_steady_release_same_source_fresh_vs_reused_owner_cost() {
    let release = !cfg!(debug_assertions);
    // Debug worker workflow verifies the exact harness and 98/98 correctness.
    // ONLY a separately compiled, SOURCE-locked RELEASE Actions job can
    // qualify M3_STEADY_RELEASE cost rows. Debug prints no release numbers.
    for shard_len in [192usize, 896] {
        let fixed = corpus(shard_len);
        let mut aead = reused_scopes(false);
        let mut fec = reused_scopes(true);
        let mut scratch = Vec::with_capacity(FIXED_WIRE_OVERHEAD+56+shard_len);
        if !release {
            let _ = measure_reuse_leg(ReuseCostLeg::SteadyAead, &fixed,
                shard_len, &mut aead, &mut fec, &mut scratch, Duration::ZERO);
            let _ = measure_reuse_leg(ReuseCostLeg::SteadyFec, &fixed,
                shard_len, &mut aead, &mut fec, &mut scratch, Duration::ZERO);
            println!("M3_STEADY_RELEASE profile=DEBUG state=NOT_RUN shard_len={shard_len}");
            continue;
        }
        let warmup = Duration::from_millis(1_050);
        let measure = Duration::from_millis(1_125);
        // Four >=1s active warmups per size; not included in measurements.
        for mode in [ReuseCostLeg::FreshAead, ReuseCostLeg::SteadyAead,
                     ReuseCostLeg::FreshFec, ReuseCostLeg::SteadyFec] {
            let w = measure_reuse_leg(mode, &fixed, shard_len,
                &mut aead, &mut fec, &mut scratch, warmup);
            assert!(w.active_wall_ns>=warmup.as_nanos());
            println!("M3_CLOCK_WARMUP profile=RELEASE mode={} shard_len={} active_wall_ns={} windows={} clock_backend={} cpu_valid={}",
                mode.name(),shard_len,w.active_wall_ns,w.clock_windows,w.backend,w.cpu_ns.is_some());
        }
        for (round, modes) in [
            [ReuseCostLeg::FreshAead,ReuseCostLeg::SteadyAead,
             ReuseCostLeg::FreshFec,ReuseCostLeg::SteadyFec],
            [ReuseCostLeg::SteadyFec,ReuseCostLeg::FreshFec,
             ReuseCostLeg::SteadyAead,ReuseCostLeg::FreshAead],
            [ReuseCostLeg::FreshAead,ReuseCostLeg::SteadyAead,
             ReuseCostLeg::FreshFec,ReuseCostLeg::SteadyFec],
        ].into_iter().enumerate() {
            for mode in modes {
                let m = measure_reuse_leg(mode, &fixed, shard_len,
                    &mut aead, &mut fec, &mut scratch, measure);
                assert!(m.active_wall_ns >= 1_000_000_000);
                assert!(m.records>0 && m.clock_windows>0);
                assert!(m.p50_batch_avg_ns<=m.p99_batch_avg_ns);
                let cpu_s=m.cpu_ns.map(|ns|ns as f64/1e9);
                let clock_status=if cpu_s.is_some(){"OK"}else{"CPU_INCONCLUSIVE"};
                println!(
                    "M3_STEADY_RELEASE profile=RELEASE source=ACTION_SHA_REQUIRED \
                     origin=cfg_test_only backend=real_chacha_aead_hp8 \
                     mode={} shard_len={} tunnels=2 directions=2 \
                     scope_count=4 records_per_batch=64 repeat={} \
                     warmup_active_s=1.05 active_wall_s={:.9} thread_cpu_s={:.9} \
                     cpu_us_per_record={:.9} records={} wire_bytes={} \
                     p50_batch_avg_ns_per_record={} p99_batch_avg_ns_per_record={} \
                     sample_count={} includes_new_rx_owner={} \
                     clock_status={} clock_backend={} clock_windows={} \
                     same_window_wall_ns={} same_window_cpu_ns={} \
                     cpu_ratio_valid={} preseal_excluded=true transport=NOT_RUN \
                     steady_product_p99=NOT_QUALIFIED throughput=NOT_QUALIFIED",
                    mode.name(), shard_len, round,
                    m.active_wall_ns as f64/1e9,cpu_s.unwrap_or(0.0),
                    cpu_s.map(|s|s*1e6/m.records as f64).unwrap_or(0.0),
                    m.records,m.records*(shard_len+56+FIXED_WIRE_OVERHEAD) as u64,
                    m.p50_batch_avg_ns,m.p99_batch_avg_ns,m.samples,
                    matches!(mode,ReuseCostLeg::FreshAead|ReuseCostLeg::FreshFec),
                    clock_status,m.backend,m.clock_windows,m.active_wall_ns,
                    m.cpu_ns.unwrap_or(0),cpu_s.is_some()
                );
                // Full paired CPU/Wall observations, emitted AFTER timing;
                // consumer may independently check every boundary.
                for (index,(wall,cpu,kind)) in m.raw_windows.iter().enumerate(){
                    println!("M3_CLOCK_WINDOW profile=RELEASE mode={} shard_len={} repeat={} index={} wall_ns={} cpu_ns={} clock_backend={} cpu_valid={}",
                        mode.name(),shard_len,round,index,wall,cpu.unwrap_or(0),kind,cpu.is_some());
                }
                println!("M3_BATCH_SAMPLE profile=RELEASE mode={} shard_len={} repeat={} batch_avg_ns_per_record={}",
                    mode.name(),shard_len,round,
                    m.raw_batch_samples.iter().map(u64::to_string).collect::<Vec<_>>().join(","));
            }
        }
    }
}
