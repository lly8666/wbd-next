# PLAN028 H1128 — evidence and bounded cursor

[Linux H1127 Action41811668300](https://github.com/lly8666/wbd-next/actions/runs/41811668300) downloaded artifact13311214984: genuine x86/x86 frozen original TLS/Rust SOURCE0e47, Normal Auto 64+128 UDP, physical source4 .2→.3 and MTU 1280, OS inner1195, old exact Stop PASS. Command→READY303.74ms, 128 new UDP RTT p99 0.333205ms, short client process CPU49.79%; observed path-log→TLS candidate10.15ms and second lease-log→first real UDP116.71ms with 10ms log observation resolution. NOT exact OS notification/TLS Finished phase timestamps, NOT old/new CPU causal proof.

[Windows H1126 Action41810476391](https://github.com/lly8666/wbd-next/actions/runs/41810476391) downloaded artifact13312891151: first actual Go TLS, signed Npcap/Wintun/Rust, duplex UDP and inner MTU1389 PASS, exact old Stop after real .1→.9 OS callback PASS. **Second TLS fails at repeated SYN timeout** because current test Linux server runs singleton manual-IP `runServer`: after Rust handoff the original Go reader ignores all further SYN. Not a new-key failure or second authentication success. Next minimal solution is server-side verified manual /32 for existing shared Rust TUN generation manager; do not restart server, duplicate Go pump or change stable wire.

Governance H1127 found cursor size exceeded 8192; trim history summary (all older evidence remains immutable). No product source change in this checkpoint.

```feature-impact
{"kind":"none","ids":[],"reason":"Record exact native H1127 PASS and H1126 scoped FAIL and bound cursor, no product semantic change."}
```
