# PLAN026 M0 | source-locked A rollback native retest: 150M not qualified

After same-runner [ABBA decision](20261028-PLAN026-WIN-NPF-ABBA-ROLLBACK.md) rejected borrowed NPF RX variant B (+1.6323% CPU seconds/first-delivered GB), main `b1bc9315be23a78b2af65c52c2d6f53bbf858aa2` restored **only** the two A Rust NPF blobs. This check used **new binaries freshly compiled from main**, not historical ABBA A artifacts. Verification [Actions 40710227335](https://github.com/lly8666/wbd-next/actions/runs/40710227335), job 122895718517, ZIP artifact 12827165857, SHA256 `c4b778be432f484f8a75bc99be9b53cc20e4749771544d84a41f4b8431bda9dd`; [scoped evidence](../../evidence/M0/PLAN026-WIN-NPF-ABBA-ROLLBACK-NEW-SOURCE150M-FAIL-20261028.json).

## Observed product versus performance

Original Go TLS cold control, Rust Normal/off Wintun/NPF NativeOwner, signed driver, Linux WSL2 raw/TUN, real bidirectional UDP/TCP and **both owned Stop PASS**, no source-batch failure. Preflight, Windows Go and Rust, Linux Rust and original Go/Rust peer builds all PASS for compiled source `b1bc9315be23a78b2af65c52c2d6f53bbf858aa2`. This is functional evidence, not a 150M performance PASS.

One 60s original workload, 300ms one-way each, real netem0%, target150Mbps offered each; strict offered>=142.5Mbps, first-unique>=99.9% both:
- Offered Windows **149.9618**, Linux **140.9482** Mbps (Linux floor FAIL); first unique received Windows **98.2784% /138.5259Mbps**, Linux **99.9160% /149.8273Mbps** (Windows floor FAIL).
- Linux actual tc ifb/eth0 drop **0**; real Linux raw-socket drop **0**; Linux UDP fixture receiver `SO_RXQ_OVFL`/global `RcvbufErrors` delta **81**. Windows NPF local sampled drop0. Windows missing within observed sequence span 19,982 packets, distributed beyond the terminal window; cannot dismiss as only drain-tail.
- Whole Windows Go+Rust EXE **50.90625s CPU/75.921s**, 41.140625s process kernel charged, RSS peak42,033,152B. Real Rust TX TID5668 top6 sample >=**43.71875s** (kernel >=38.01562), RX TID7768 >=6.73438s; Rust 32-verified RX batch readback 36,357 SetEvent attempts/1,141,893 RX records. Business UDP RTT p99 Windows782/Linux811.691ms, NOT one-way calibrated. Driver ISR/DPC and causal stage stack not measured.
- Mode functional status `PASS_ACTUAL_WINDOWS_LINUX_NATIVE_normal`, performance `CAPACITY_LIMITED_GENERATOR_OFFER` with independent first-delivery failure; aggregate Action **FAIL**. Host scheduling/UDP fixture receiver and Rust TX/NPF kernel work are distinct unresolved contributors. **Do not assert purely host capacity, purely product defect or performance PASS.**

Decision remains **ROLL_BACK_B** per controlled A-B-B-A, but newest main 150M performance status **FAIL/NOT_QUALIFIED**. Don't rerun a heavier member of this capacity-limited family or change M2/FEC, NPF driver lifetime, ACK or memory buffers on suspicion. Preserve product integrity/owned Stop. Next when authorized: a minimal distinguishing same-host lower-load sample plus TX kernel/NPF driver outcome/ETW attribution if closing 150M, not a seed refresh. Other PLAN026 modes and physical qualification remain open; this ABBA package is closed with a negative 150M retest.

```feature-impact
{"kind":"updated","ids":["normal-off","windows-native-transport"],"reason":"Register exact compiled main rollback SOURCE b1bc native Normal/off functional PASS/owned Stop but genuine 150Mbps scoped FAIL with Linux offered shortfall, Linux socket drops and Windows first-delivery/CPU hotspot; retain source-scoped ABBA rollback and existing user-visible experimental defaults."}
```
