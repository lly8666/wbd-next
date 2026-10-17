# M1 PACK-006 · R1-M1-OWNER-MEMORY-READY-WORKPACK-011

## Authority, baseline, and owner boundary

Main `.governance/registry.json` revision2, epoch1, role M1 active, `assigned_task` 011. M0 `docs/decisions/M0-full-module-workpackages-2026-10-17.md`; allowed M1 runtime/memory/tests/devlog/evidence/cursor/requests only. Previous worker H `35fdcf07b44bba2ffde249ac085902385b16eb3c` (cursor sequence12) vs checkpoint `c821f57413d112f57a083dee67ff824afde36407` had **only cursor delta**; H Governance38712396892 attempt2 SUCCESS. Previous M1 CODE `2ce58427f84a777bce6242f6803a5c82413b5fe2` native 88/88 scoped `r1_` PASS. Main merged previous M1 code separately; do not cherry-pick live M0 owner or ABI edits to worker, or modify M0 activity. Source-specific production readiness flags remain FALSE.

### Existing proof reused rather than recreated

- `runtime/generation`, `early_rx`, `batch` and `rx_batch` implement same-owner borrowed immutable/unique handle, exact scope, 0/1/32/33 immediate ready bounded 32, no old→new or untrusted ingress authority. Previous 88 cases stay mandatory.
- `runtime/wake` implements std-only bounded producer queue, `armed:SeqCst` double-check, stop versus in-flight producer, fake MonoNs deadline and one-slot return notification. It is not a qualified OS eventfd/rtrb/loom execution; no dependency/wire/CI permission here.
- `memory` uses fixed allocation slabs, generation slots, single owner drain, `sync_channel` + preallocated Mutex fallback backlog for multiple concurrent *last-droppers*, including Stop with outstanding frozen Arc clones. Driver/kernel real loan NOT_RUN. `ARENA_READY=false`.
- Existing M1 `parity::ParityReady` stores bounded first-send records but old `TxOwner` scheduler treated parity as the same secondary 10%-share class as repair. This is a real always-fresh FEC regression.

## This package: bounded service and lifetime changes

1. `runtime::ready_turn::ReadyTurn`: one reusable owner-only budgeted turn, preallocated caller `Vec` TX+RX outputs, at most 32 already-ready of each direction; no waiting for a full batch, no socket/driver or dynamic buffer allocation. Uses cooperative ~100µs fake `MonoNs` budget between TX/RX classes; alternates which class starts so a continually busy one cannot starve the other. `TurnStats` snapshot requested only by slow caller (not a per-record global mutex/counter). It is not hard preemption, actual loop thread orchestration or M0 authenticated Go I/O.
2. `memory::Arena::drain_returns_bounded(max)`: fixed-budget (e.g.64) return completion loop with alternating channel/backlog service and no key loss. `allocate` reaps at most64 so bursts cannot consume arbitrary owner CPU in one allocation; explicit `drain_returns()` remains full control-path drain for Stop/report compatibility. All old clone/lifetime tests retained; saturated backlog from independent producers stays bounded by preallocated count.
3. `runtime::wake::WakeGate::notify` retains armed state if notification could not be delivered; a test-only one-shot notification failure lets the *next* publication awaken a consumer even if the first item left the queue already nonempty. Stop still linearizes and caller owns returned buffers. Platform OS wake callback and real SPSC/rtrb not implemented here.
4. `TxOwner`: parity bytes are **FIRST send**, not 10% repair. `with_parity_share(...,k,r)` lets M0-supplied eligible parity scheduler express 1..20 systematic/parity ratio with `0<r<=k<=20`; default `with_parity` selects 20:20. Bounded signed deficit yields initial systematic immediately then parity service under continuous ready source, independent of 10-first-send repair share. A due parity-only batch never waits for source; control path explicitly still owns AEAD, parity production, true wire byte budgets and production ratios. Strict `r/k` in bytes for variable sized payloads **requires actual wire-byte-aware lane scheduling** at M0 integration; these handle-count component proofs cannot qualify that part. No full FEC implementation in M1.

## Functional test plan in existing compiled-once native action

New `r1_workpack_` cases: 0/1/32/33 caller-preallocated TX/RX handle batches, alternate starting class when artificial 100µs elapsed, slow-lane RX eligibility bypass, first-failed-wake followed by second publication, 96 multi-producer last returns through one-slot channel and saturated fixed backlog in 64+32 reap turns, last held frozen Arc during Stop and slot-generation advance, ready parity 20:20 continuous source, ratio 4:20 continuous source plus independent repair. Prior 88/88 R1 tests must remain PASS. New fairness semantics change two prior unit-test *expectations* (parity was previously counted as repair); maintain their function/coverage while asserting parity first-share rather than false 10% scheduling.

B01-B04/real Go V4 to Rust caller boundary, true driver lease, OS TUN/raw, syscalls, kernel-completion, 100us cycle CPU profile, platform native rtrb/loom, full timer wheel/10k jump, multiclient DRR actual wire bytes, Game FEC/AEAD/duplicate logical delivery, end-to-end 500Mbps/p99 and physical are NOT_RUN at this M1-owned standalone source. List concrete interface remaining issues for M0; do not enable `OWNER_RUNTIME_READY`/`ARENA_READY`/C ABI. No root Cargo/workflow/config dependency changes permitted. Only exact SOURCE Actions success + downloaded binary/result artifact, evidence S and cursor-only H Governance can attest scoped completion.

## Observed exact-source verification

Source S `0ec99ed0bd5706c9df54649c0b20e1b157ffd363` branch `work/m1-r1-runtime`. [Worker-native38997851983](https://github.com/lly8666/wbd-next/actions/runs/38997851983) compiled-once Linux x64 Rust native binary and consumed in same-source build/consume jobs, **96/96 `r1_` PASS** (prior88 + new8), 3 unrelated R0 tests filtered. Downloaded result artifact12088015978, independently opened exact ZIP:
- ZIP SHA256 `9ec9b83947cb794e50b07342b8323e9bfde59e47678c8920a998780e3d28109e`
- result.json SHA256 `df1ca337bb0f9c60debaef1f8c47614f5a9ccaa6e8a016c1b22fba407ed7d8ba`
- test.log SHA256 `362f588ff5af59867f380d5aa158b042b5c132566a88a66098ec63ef39178d84`
- outer executable SHA256 `24f80e64660212e9c2970cfce03497807dd67f8a9507766cc63ecd73a730b609`

All eight workpack cases appeared uniquely PASS in `test.log`. Existing Release component P0 also built precisely one executable SHA256 `1e331c079f2050a12c5c483c8335a3282e71416bfedf527a9bb6f37a84646ccd`, ran three 1.10s observations (TX32 ready p50 541 ns / p99 551 ns; RX32 ready p50 2214 ns / p99 2244 ns), but its process CPU-s includes allocation/freeze/offers and is unisolated. No A/B performance gain claimed.

Same CODE SOURCE Governance38997851974, G2 bootstrap38997851957, R0 qualification audit38997852000 and R0 cross ABI38997851994 **SUCCESS**. Root M0-owned old worker-branch [R0 native ABI38997852003](https://github.com/lly8666/wbd-next/actions/runs/38997852003) **FAIL** even though unit binary returned rc0, 98 passed+1 ignored; old shared `tools/r0_abi_bundle.py` expects `"3 passed"` from unfiltered output. No all-CI PASS.

## Stable integration interface and rollback / NOT_RUN

M0 may integrate `ReadyTurn::run` with preallocated TX/RX Vec, cooperative 100µs bounded class turns and low-frequency snapshot. Existing `drain_ready_batch`/stop remain fallback. M0 may select `TxOwner::with_parity_share(k,r)` when the authenticated codec/control profile supplies ratio; current tests use equal one-byte records only, **actual unequal wire-byte 10:1 repair budget and parity volume remain NOT_RUN**. Return consumption can use owner-local `Arena::drain_returns_bounded(64)`, while legacy `drain_returns()` stays complete control drain. Event retry uses existing bounded std-only WakeGate; real OS eventfd/rtrb/wheel/Go auth/driver/native Windows/ARM remain explicitly NOT_RUN. Previous owner loan/early RX boundary guarantees and first ready/no-copy remain covered by all original 88/88 tests. No product feature enablement.
