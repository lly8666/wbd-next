# M3 workpack016: minimal native ISA-L shared dependency / native CI boundary

Current main task: `R1-M3-RECORD-LINK-FEC-WORKPACK-016`, M3 path whitelist exclusively codec and role files. Existing `fec_math.rs` is correct scalar GF(256)/0x11d and pinned old-Go Vandermonde-normalized 20×20 matrix, including missing-only e×e inverse; previous tests cover Go generator and parity/golden. **There is no ISA-L binding, FFI or pinned native linkage in the current Cargo workspace.** The root workspace Cargo.toml and Cargo.lock, shared CI, Go/engine and public ABI are M0-owned.

Please supply a single M0-reviewed minimal native ISA-L linking/binding interface and reproducible Actions build capability (Linux x86_64 baseline, explicit target CPU/ISA and compiler/link flags), including any required root Cargo/lock changes. Avoid granting M3 blanket shared-path edits. The safe M3 codec wrapper will receive the exact legacy 20×20 GF coefficients, use `ec_init_tables + ec_encode_data` (not default Cauchy matrix), avoid aliasing, handle L<64 scalar fallback, preserve 8B HP and parity count. The existing crate has forbid(unsafe_code); a reviewed narrow safe API is needed rather than allowing arbitrary unsafe calls. Keep native ISA-L vs scalar backend explicit and test-only unavailable => UNSUPPORTED/NOT_RUN, never silently claim acceleration.

M3 will own codec integration and native byte-for-byte oracle suite for k=1..20 × parity r=4/8/10/12/16/20 × short/unaligned/MTU, e×e missing rows, tests of profile/rate/parity; native platform probe must run on the actual ISA and verify real backend selection. Any material CPU delta needs same-host paired A/B Action after build-once, not cross-run ratios. No production ABI feature enablement, no 500Mbps claim.

Meanwhile M3 continues independent scalar/record/LINK/FEC work and this request is not permission to change root or shared CI.

## 2026-10-17 · Existing shared backend delivered; exact worker-native execution entrance still needed

Verified main SOURCE `2dee6315f3c92a7b913f215b18354a4fe0f88711` / `21ef432683db99d122875a1ce534be59ed0eaca9` and [native run39011616037](https://github.com/lly8666/wbd-next/actions/runs/39011616037): M0 has delivered `native/isal-safe`, optional codec feature, pinned Intel ISA-L v2.31.1 static `c387163fcbca62701d646149564c550c78a4f985`, Rust1.85.1/Linux-x86_64 and real C `ec_encode_data` XOR fixture. **This prior request's missing backend/API root dependency is now RESOLVED; do not recreate or repin it.** M0 decision `docs/decisions/M0-024-unblock-M1-M3-M4-source-evidence-2026-10-17.md` explicitly authorizes M3 safe adapter only in codec/src.

M3 work branch CODE SOURCE `422a26127496560c0a52e6745ecc8f354e3f4f18` now contains:
- `fec_native.rs`: explicit Scalar/PreferNative/RequireNative; call `Tables::new/encode` with pinned Go 20x20 active coefficients; 64B+ native success marked only AFTER actual C encode; short/unsupported scalar or fail-closed; unequal active source tails padded zero, e×e direct-output coefficient decode; existing scalar reference untouched.
- `fec_tx.rs`: opt-in cooperative owner native four-row job, backend Used recorded only after rows produced; no scheduler thread, wire/PN change or default production enable.
- `fec_native_tests.rs`: three focused Go-vs-native/scalar suites across k1..20, all six parity profiles, short/unaligned/MTU, exact 56B original wire, k partial and e erasures including full k20; default native run39014384925 on SOURCE `2a373c0f49ddb60c30e71e74ab918bf41c66f026` **113 PASS/0 FAIL/1 ignored** but `native-isal` DISABLED, hence not a native PASS. New CODE includes a deliberately ignored **feature-gated Linux Release** AB/BA same-worker CPU/wall + recovered logical-frame component diagnostic. Its CPU result has not run.

**Remaining precise M0-owned test/CI gap, one change not repeated per assertion:** `.github/workflows/m0-native-isal-safe.yml` currently triggers only main dependency changes and only `cargo test -p wbd-codec --features native-isal --no-run`. It cannot execute M3 worker CODE with the main-pinned C crate because worker branch Cargo/lock/native directory is older. Add one opt-in manual `workflow_dispatch` with exact M3 code SHA and approved pinned main harness SHA parameters, no floating worker HEAD at consumption. In its throwaway checkout use reviewed M0 main `Cargo.toml`, `Cargo.lock`, `crates/wbd-codec/Cargo.toml` and `native/isal-safe/` only while copying M3-owned `crates/wbd-codec/src/` at exact CODE SOURCE; never commit those overlays to worker. Verify all copied blob SHA and actual lock/feature/ISA-L upstream SHA. Build native package once for Rust1.85.1 with pinned libisal.a and `WBD_ISAL_PREFIX`, then run the SAME verified binary:

```bash
cargo test --locked -p wbd-codec --features native-isal --lib r1_fec_selected_backend -- --nocapture --test-threads=1
cargo test --locked -p wbd-codec --release --features native-isal --lib r1_fec_native_release_same_vm_scalar_isal_paired_cpu -- --ignored --nocapture --test-threads=1
```

Prefer `cargo test --no-run` compile once per profile, record test executable sha256, then execute directly from artifact without recompiling in the measurement job. One performance Action = 20:20 1200B, fixed deterministic source, one seed, one measurement job/VM; A/B order declared `WBD_FEC_ORDER=AB` and optional separate later B/A run. Preserve >=250ms CPU/wall raw windows, per-leg output counts (20 systematic/20 real parity/4 recovered per block), true native `FecBackendUsed::NativeIsaL` witnesses, p99 **codec operation wall** only. Record `lscpu`/CPUID and native symbols/disassembly or actual dispatch witness separately: mere AVX2 host flag or native C invocation is **not** proof of a specific SIMD instruction path. No driver/NIC data-packet delivery or application packet p99 is measured here; those remain NOT_RUN until M0 real owner integration. Observe capacity, stop escalation on CPU or runner constraints. For cross-build Linux ARM/Windows, native unsupported under current `build.rs` (do not fake portable acceleration). Do not silently broaden M3 commit rights to Cargo/lock/workflows.

This is a missing **test entrypoint**, not permission to change shared CI. M3 can continue independent codec work; component native qualification waits only for this one M0-shared Actions implementation, not step-by-step integration approvals. All prior 016 and 015 results remain source-scoped.

## 2026-10-17 · Native source-qualified PASS — only one existing Actions performance step remains

**Resolved**: M0 already supplied the safe ISA-L API, pinned dependency, throwaway worker/Main Cargo overlay AND exact worker-source native execution. Formal [M0 native run39016665239](https://github.com/lly8666/wbd-next/actions/runs/39016665239), harness SOURCE `5f1fbb387308da67962efbec95ad194782b6e10e`, M3 CODE SOURCE `422a26127496560c0a52e6745ecc8f354e3f4f18`, Linux x86_64/Rust1.85.1/upstream ISA-L v2.31.1: static `ec_encode_data` executed, 3/3 Go/scalar/native parity/wire/e×e and cooperative owner differential tests PASS, 0 fail, artifact IDs 12094996653/12094524936 with digests in the new M3 SOURCE-specific evidence. Earlier nested-workspace and stdout-parser red runs remain historical failed workflow checks, not ISA-L parity failures. The earlier paragraphs requesting *native execution itself* are **satisfied**, do NOT add a second native wrapper or full regression matrix.

**Only unresolved M0-owned CI entry**: existing `.github/workflows/m0-m3-isal-native.yml` build stage already compiles **one Release test executable** from the exact M3 source with `--release --features native-isal --lib ... --no-run`; the consume stage already validates its source/manifests/sha256 and runs all 3 focused native correctness tests. In that *same existing consume job on its same VM*, add one step following successful checks (no new crate/lock/native source edit, no second compilation):

```bash
set -euo pipefail
lscpu | sed -n '1,25p' | tee m3-native-result/host-isa.log
WBD_FEC_ORDER=AB m3-native-build/isal-codec.test \
  r1_fec_native_release_same_vm_scalar_isal_paired_cpu \
  --ignored --test-threads=1 --nocapture \
  | tee m3-native-result/paired-AB.log
grep -F 'M3_FEC_CPU_RESULT order=AB leg=0 mode=scalar' m3-native-result/paired-AB.log
grep -F 'M3_FEC_CPU_RESULT order=AB leg=1 mode=native-isal' m3-native-result/paired-AB.log
```

The existing precompiled test executes equal k20/R20/1200B sources, five real 4-row parity quanta, 4 exact erasure recovery outputs on each leg, same generator/Go profile; warmup excluded, >=250ms raw thread CPU+wall windows, per-op codec wall p99, same seed. Preserve raw `M3_FEC_CPU_RAW` and `M3_FEC_CPU_RESULT`, binary SHA/host ISA, and capacity indicators. Treat `CPU_INCONCLUSIVE` as inconclusive, not PASS/speedup; observe actual `NativeIsaL` status from existing tests. `AVX2=true` is a CPU capability, **not** disassembly proof of which SIMD variant executed. A later reverse B/A is optional if interpreting small gains/noise, as a separate comparable Action—not a new test matrix.

This modification is strictly in **M0-owned shared workflow**. M3 has neither permission to edit it nor a GitHub connector action to issue `workflow_dispatch`; no new worker code is needed for this existing diagnostic. Until Action executes, M3 remains `partial` rather than fabricating CPU/real delivery/p99. This request is one bounded interface unblock, not a new coding architecture or requirement for multiple approvals.
