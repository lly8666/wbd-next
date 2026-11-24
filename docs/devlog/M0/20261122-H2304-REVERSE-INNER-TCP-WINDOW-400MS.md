# H2304 · real inner kernel TCP reverse-window 400ms, 0/1/5% (2026-11-22)

Source commits: `ac03b42143357059995bd51291c109ffb6d66641` adds six workflows, `5a29cd2934ff4066ba48e1f56ba1a6892e1cf30c` isolates historical static H2293 FEC tests for 0% trials. This is **test-only** and **not a current-main or current-branch Go/Rust product binary performance result**. The CLI and Rust binary hashes remain frozen from the archived H2286/H2292 source builds, and the workflows record the compiled-source diff instead of silently saying it matches current source. Main, runtime defaults, fake TCP retransmission, FEC implementations, and OS-wide production settings are untouched.

## Exact experiment grid

| Real two-end inner TCP socket trial | 0% loss | 1% loss | 5% loss |
|---|---|---|---|
| 8MiB → 2MiB → 8MiB | [44984376649](https://github.com/lly8666/wbd-next/actions/runs/44984376649) | [44984321085](https://github.com/lly8666/wbd-next/actions/runs/44984321085) | [44984321166](https://github.com/lly8666/wbd-next/actions/runs/44984321166) |
| 16MiB → 8MiB → 16MiB | [44984376588](https://github.com/lly8666/wbd-next/actions/runs/44984376588) | [44984321079](https://github.com/lly8666/wbd-next/actions/runs/44984321079) | [44984321196](https://github.com/lly8666/wbd-next/actions/runs/44984321196) |

Each runs 2 independent 3-runner Windows2025 original signed Npcap/Wintun+GoTLS/Rust ↔ native ARM relay netem ↔ native original ARM GoTLS/Rust TUN, true Windows and ARM kernel TCP socket setsockopt (not WBD FakeTCP outer), 4 bulk streams +160 sparse echo, **200ms per kernel-netem direction / 400ms RTT**, FEC OFF and opportunistic presentation repair OFF for all A/B/A'. Direct Tailscale before WSL/driver, real TX16/NPF64KiB archived Rust DLL, stage source-bound, actual recv byte count/latency, CPU, kernel qdisc packet/drop readback, Windows and ARM socket readback, per-leg owned Windows/WAL/WSL and ARM netns Stop. 0% netem must show the two directions and zero actual netem drops, 1%/5% require positive drops per direction. Never infer any 0% result is no-delay.

B stage deliberately shrinks the socket buffer; A and A' are same larger buffer. This tests whether **less** in-flight buffer can protect sparse TCP P99 without killing bulk throughput; B vs A/A' is not a product-default improvement without real receipt. `SO_RCVBUF/SO_SNDBUF` readback confirms allocation request but is not actual `cwnd`, `rwnd`, or window scaling proof.

## Source facts, failure and qualification

Prior H2303 [44982126475](https://github.com/lly8666/wbd-next/actions/runs/44982126475) had correctly qualified DIRECT underlay and original drivers, but **both A=8MiB 5%-loss client streams hit `H2271_REAL_TCP_CLIENT_INCOMPLETE` with `TimeoutError`** before B=16MiB; ARM servers timed out awaiting completion. It provides **NO 16MiB-vs-8MiB goodput or P99 result**. Prior H2302 [44978797691](https://github.com/lly8666/wbd-next/actions/runs/44978797691) stopped on DERP preflight, so it provides no 8MiB-vs-2MiB result. Preserve these FAIL/NOT_RUN, never promote.

H2304 original launch `ac03b42`: 1%/5% four static CI gates PASS; two 0% workflows were initially blocked by unrelated historical H2293 unit imports that require 1%/5% even with FEC OFF. Exactly two 0%-loss workflow **static** jobs now run H2293 old unit tests with FEC_ABA=0, while actual runtime retains FEC_ABA=1, WINDOW_ABA=1, FEC OFF and symmetric loss=0. The other four static tests and product gates remain unchanged. The **six real 3-stage goodput/P99 qualifications remain OPEN until completed artifacts, not PASS**; real network or kernel TCP timeout is not a signal of counterfactual window improvement.

Criterion: compare within runner A/B/A' real ARM received bytes / client measured elapsed, 160/160 echoed with missing/late kept, p50/p95/p99, Windows CPU seconds per real GiB, qdisc egress/drops, exact actual socket buffers, original Stop. Reject survivorship P99 or a claim that a bare TCP or UDP test validates product. Concurrent Actions share infrastructure and may drift; do not compare across six Actions as if one perfectly locked underlay. Any desired promotion must independently validate **current main source** and separately cover Linux x86/ARM and Windows OS scope, and must not mutate global system TCP settings without reversible owned isolation.
