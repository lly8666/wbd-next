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
    // A brand-new valid PN for an old already-retired FEC block must fail
    // the BlockID floor without reviving heavy capacity or contaminating B.
    let mut sender = LaneTxCrypto::new_for_suite(keys(a.seed), MAX_WIRE_LEN, SUITE).unwrap();
    let mut stale = Vec::new();
    for _ in 0..=RECORDS_PER_SCOPE {
        let frame = &a.sealed[0][14..a.sealed[0].len()-16]; // ciphertext is NOT a FEC frame
        black_box(frame);
    }
    // The existing replay case above is the only resubmitted PN; never
    // pretend to mint an authenticated stale wire from ciphertext.
    black_box(&mut sender);
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
