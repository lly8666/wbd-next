# WL performance harness V2 (M0 Windows Go/Rust)

## Current entry
The real test is `.github/workflows/m0-wl-public-normal-full.yml`, signed Windows Npcap/Wintun, original authenticated Go TLS and WSL2 Linux real raw/TUN. V2 uses the existing `tools/m0_wl_public_rate_app.py`, `tools/m0_wl_netem.py`, `tools/m0_wl_public_normal_e2e.py` and the orchestration `tools/m0_wl_perf_v2_ab.py`. Normal/off alone has a same-process Go-steady test-selectable path vs Rust NativeOwner. No mocked carrier, no bypassing original Apply/Stop.

**One dedicated Actions run = one scenario + one measurement job**, B (Rust) then A (Go) on the same `windows-2025` runner, same source and signed drivers, same original Linux peer. No concurrent Go/Rust legs. A's Go steady state is the *still-present code compiled at the current SOURCE*, not a historical precompiled published Go executable. It uses the same DLL for legacy M1/M3; report both actual paths honestly. New binary artifact is separate from the diagnostic results.

## How to run
On a source with the V2 integration, trigger a workflow dispatch with `public_mode=normal`, `run_n0=false`, `perf_scenario_file=scenarios/wl-normal-150m-300ms-0loss-60s.json`, `perf_ab=true`. The workflow may also have a one-off source-tagged push entry `[plan026-ab-150]`. Do not use N0/P200 in the same invocation. The A/B runner handles two independent original TCP/TLS/OS/WAL/Stop sessions, not two simultaneous products. B runs first so a crashing Go baseline cannot prevent measuring Rust; it will still block the second leg if its own owned Stop is not verified.

`scenarios/*.json`: integer duration (10..240 s), warmup (0..30), drain (2..30), supported TUN MTU, seed; two directional sections each contain offered Mbps (0..350), delay ms (0..2000), loss percent (0..60), optional `tc_rate_mbps`, and packet mix array with `udp_payload_bytes` + `packets_weight` (weighted **per packet**, not per byte; sum <= 100). Source-lock full JSON by SHA. Input-to-generator offered Mbps and actual socket sent/first delivered Mbps are distinct. The original N0 and P200 names, thresholds and evidence remain untouched.

## Exact evidence to read
`result/wl-public/wl-ab-v2/leg-A/` and `leg-B/` contain independent Windows/Linux generator results, 1 Hz whole-EXE Windows CPU+RSS/threads, owner log, and pre/after genuine Linux tc qdiscs. `wl-ab-v2/report.json` contains per-leg offered/first delivered/CPU-seconds/GB and the classified A/B outcome. An invalid scenario, missing authenticated Stop, incomplete same-VM telemetry, insufficient offered rate (each direction >=95% of target) or lost counters -> INCONCLUSIVE/FAIL rather than an invented improvement. Per-process CPU includes Go+Rust and kernel charges; named Rust worker CPU excludes unnamed runtime/driver CPU. Approximate 1 Hz process windows are not per-packet or one-way p99.

Default production builds have no per-packet Rust lock timers. The existing opt-in `win_native_lock_profile` samples 1/64 lock attempts on diagnostic source; it does not establish who consumed all CPU. Separate unexplained TCP-like data loss from actual tc drop and generator capacity. Do not split the NativeOwner mutex or change ciphertext/PN without measured evidence.

## Qualification
Code installed != build PASS != real two-OS PASS != 150Mbps sustained offered != 150Mbps first-delivered, and none implies physical-machine PASS. If either leg fails, preserve first error and both independent reports; do not compare a surviving single leg. At capacity limits stop heavier scenes. Original Linux path and fixed/auto/game modes are not modified by this opt-in Normal-only benchmark.

## First 150Mbps attempt and failure provenance (2026-10-28)

Source `113b2e50` Action [40666215474](https://github.com/lly8666/wbd-next/actions/runs/40666215474) completed all compile/unit and Linux product builds, but Go-steady A exited during the 60s real kernel load after 13.359s of sender uptime; genuine original TLS and OS/WAL, real bidirectional UDP/TCP initial smoke passed. Windows Go original owner last observed `npcap_ingress_local_drops=210265`, `pending_original_rust_frozen_or_unacked_legacy_carrier_records=1489`, generator `WinError 10051` after loss of route. 250181160 Windows payload bytes emitted in 13.359s (~149.82Mbps over elapsed time); the old reported 33.3575Mbps divides by planned 60s and is NOT sustained-run throughput. B did not run because Go Stop was unverified. Root first owner failure subtype was not retained; new first-exit signature extraction and B-first order protect future independent evidence. Neither A/B CPU nor 150Mbps whole-run qualified. A legacy Go steady cannot be silently promoted to product PASS, even if Rust B succeeds.

## Rust-only root-cause diagnostics (preferred after 2026-10-28)

Use `perf_ab=false` and one `perf_scenario_file`. Do not re-test or maintain the retained Go steady-state path unless a separate user request explicitly requires it. Do not construe an exploratory 60-second Rust throughput result as lossless if first-delivery fraction <0.999 when 0% netem loss was configured.

The 2026-10-28 source `0543b805`, Action [40668581343](https://github.com/lly8666/wbd-next/actions/runs/40668581343), is the immutable baseline: actual Rust Normal 60s both-OS offered ~149/150Mbps, delivered ~147.0/148.94Mbps, app first-delivery ratios ~98.84% /99.30%, real netem drops=0, true owned Stop PASS. The 10ms **loop-tick** arrival histogram, NOT a kernel packet timestamp, has simultaneous-looking windows of no observed application arrivals: Windows 5.01–5.51s (500ms) and Linux 5.30–5.81s (510ms), offset around one 300ms impairment delay. Windows generator's 60-second offered budget was short ~0.491s of 150Mbps, while Linux generator had no material overall shortfall. This supports a temporary Windows-side pause/backpressure hypothesis but DOES NOT yet establish if the Python generator, Windows scheduler, Wintun consumer, Rust NativeOwner or kernel receive buffer caused the gap. `warmup_s=5` in the JSON was previously informational only; it did not schedule an intentional pause at second five.

Before changing the native product, compare `send_10ms_bucket_counts` and `arrival_10ms_bucket_counts` for BOTH generator processes, `max_generator_loop_gap_ms`, bounded long-pause events, `received_sequence_gap_summary` and real kernel `tc` deltas. New V2 generator output names explicitly distinguish userspace loop observation from OS packet arrival. With an existing artifact downloaded and unpacked, run:
`python tools/m0_wl_v2_gap_audit.py <unpacked-root>/wl-ab-v2/leg-B`.
For a new Rust-only run, locate the independent `wl-n0-{linux,windows}-app.json` and `wl-n0-netem-{before,after}.json`, unpack into a single folder and run this same reader. Never use differing userspace clocks as one-way p99.

### Faster Windows real measurement — reuse compiled SOURCE, not OS ownership

A normal 2026-10-28 run [40668581343](https://github.com/lly8666/wbd-next/actions/runs/40668581343) spent approximately **135s** on the longest parallel preflight, **100s** building a Linux product, and **340s** in the native Windows job (including **41s** Go rebuild and **88s** Rust DLL release build, plus **142s** signed-driver/WSL/product launch and measurements). Repeating compilation on every harness-only change is unnecessary.

The main full workflow supports dispatch inputs `public_mode=normal`, `perf_ab=false`, `perf_scenario_file=scenarios/wl-normal-150m-300ms-0loss-60s.json`, `perf_reuse_run_id=40668581343`, and `perf_binary_source_sha=0543b805ca25d804ccd131be6686b0b99f61f80f`. Example:

```bash
gh workflow run m0-wl-public-normal-full.yml --ref main \
  -f public_mode=normal -f run_n0=false \
  -f perf_scenario_file=scenarios/wl-normal-150m-300ms-0loss-60s.json \
  -f perf_ab=false -f perf_reuse_run_id=40668581343 \
  -f perf_binary_source_sha=0543b805ca25d804ccd131be6686b0b99f61f80f
```

The fast lane skips three source-unchanged compile preflights and the Linux/Windows native rebuild. It still runs cheap schema/assembly tests, verifies the exact artifact's GitHub run repository and source, checks *all* compiled product/ABI and Cargo.lock files are identical between binary SHA and harness HEAD, verifies manifest and binary SHA-256, installs signed Npcap/Wintun and real Ubuntu WSL2, and exercises true original Go TLS **cold control**, Rust Normal/off NativeOwner and owned Stop. This is **not** a cached VM or a bypass of kernel/driver checks. GitHub-hosted Windows VMs are ephemeral, so signed-driver setup and WSL guest bootstrap are still required; long-term repeat-speed needs a securely maintained self-hosted runner with per-job snapshot/revert and driver/WAL ownership checks. Old build artifacts expire after 30 days; choose a new known good binary run and hash, never silently select a latest tag or recycle artifacts after product code changes. One measurement scene per job remains the contract.

### Linux history worth reusing, and what was NOT proved

- [Linux Normal20 no-loss source896f](../evidence/M0/PLAN011-NORMAL20-CONTINUOUS-NETNS-LOSS0-20261019.json): real Rust Linux raw/TUN, 20Mbps each direction, 10s warmup +60s sample, 0 missing; this is not a 150Mbps/300ms Windows result.
- [Linux D10 traced-capacity](../devlog/M0/M0-024-D10-traced-capacity-2026-10-17.md): intrusive `strace -f` run produced 8.92–8.98Mbps C2S at a 10Mbps offer with thousands of missing packets; untraced original P10 passed. Historic interpretation is tracing overhead **plausible**, not an established single cause. Keep Windows diagnostics constant-time/bounded, opt-in and aggregate rather than each-packet tracing.
- [Linux high-loss P200 fixture](../devlog/M0/20261028-PLAN026-H327-stress-recv-slab-and-artifact-hash.md): Python receiver `recvfrom_into` replaced per-packet allocations, but generator CPU and capacity still limited the test. Borrow its fixture bottleneck separation, not a claim that 250Mbps was fully qualified.
- [Linux loss1 genuine delivery](../evidence/M0/PLAN025-H312-source33ed-linux-loss1-512-genuine-20261028.json): stopped using stop-and-wait all-echo validation because a real dropped packet prevented continued offer; switched to independent counted offers/receipts and genuine `tc` drops. It did **not** prove that this Windows 500ms stall was fixed on Linux.

Do not enlarge NativeOwner queues, split mutex ownership, or rewrite M2 deadlines until sender/receiver time histograms plus OS queue/driver error counters identify the failing stage.
