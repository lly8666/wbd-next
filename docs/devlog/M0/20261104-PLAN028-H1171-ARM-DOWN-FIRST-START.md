# PLAN028 H1171 — bounded checkpoint and native ARM link-down-before-reconnect

Previous source-specific [H1170 x86 double switch](../evidence/M0/PLAN028-H1170-SOURCECB4C-X86-GAME4-TWO-PHYSICAL-GEN-MIXED443-20261104.json) remains PASS. H1170 mandatory governance [run41873612574](https://github.com/lly8666/wbd-next/actions/runs/41873612574) feature catalog itself PASS but structure FAIL only `cursor too large`: accumulated `partial_summary` bloated to 6.4 KiB and cursor to 8,944 UTF-8 bytes over 8,192. Replace repetitive summary with a bounded 3683-byte checkpoint. All old evidence files/devlogs preserved; current source-specific reference remains H1170 cb4. This is not a runtime regression.

Next Linux full task switches **x86/x86→ARM64/ARM64**. One distinct native Game4FEC6 physical outage before new TLS: OS link `mxb0` DOWN, kernel JSON readback, hold 1.3s (not artificial event), add real new source4 .9, new physical MTU1280 and restore UP, then original Go TLS/Rust M4 generation2 and exact old generation1 Stop; healthy other Normal Auto 48 time-spanning real UDP replies, new Game4 32 real UDP. Outer user IPv4 1460; inner OS1358→1178. Separate original physical-disconnect gap from old gone permanently; original .3 remains installed, so do **not** overstate hard-dead case. Event→TLS & authenticated→first and CPU/p99 remain NOT_MEASURED; physical down→Ready is not notification 200/500ms coalescing SLA.

One SOURCE/workflow, one native Action, unchanged Rust/Go/wire, no 027/027A replay. H998 hot-shrink FAIL, prior ARM Action FAIL, remote ICMP and CPU causal open. If old owner genuinely terminates early, only proof of actual first-disconnected (not forced overlap assertions) will qualify separately.

```feature-impact
{"kind":"none","ids":[],"reason":"Shorten existing cursor under 8KiB and add narrow native ARM test-only physical outage fixture/workflow; no product interfaces or wire changed."}
```
