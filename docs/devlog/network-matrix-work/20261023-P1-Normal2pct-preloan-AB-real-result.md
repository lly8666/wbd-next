# 2026-10-23 Normal/off 2% loss: confirmed TUN preloan product repair in same-VM AB

Original TUN ingress logical error was measured, not theoretical. Baseline A=99042008e8f42f334ed635df92945e00e53c45dd (128 M1 slots, TUN read before arena allocation) and fixed B=de55a1322b4580c60e77322d2d38843caefeec79 (bounded 512 slots, reserve before consuming TUN). One automatic sequential same-VM Actions measurement [39913690718](https://github.com/lly8666/wbd-next/actions/runs/39913690718), request SOURCE 6f4acf937d8003ac6471ae6b690d018b46458ccd, attempt1, raw artifact12484331372 SHA256 5a689f6ebd0dde500585f56fc83381a108f9c65b9b5f2de0bfa6639795d2c241. Overall workflow FAILURE only because A FAIL; B is explicitly PASS_SCOPED_OBSERVATION. No repeated dispatch.

| True 60s measurement | A before | B after |
|---|---:|---:|
| UDP C->S missing /5884 |132 (2.24337%)|5 (0.08498%)|
| UDP S->C missing /5884 |147 (2.49830%)|4 (0.06798%)|
| TCP C->S p99 |4695.7ms|643.4ms|
| TCP S->C p99 |4954.4ms|898.0ms|
| Client consumed-postread arena_failed |219|0|
| Server consumed-postread arena_failed |248|0|
| RX feedback_drop client/server |266/296|0/0|
| Client CPU / Server CPU (same job) |1.71s /1.73s|1.93s /1.95s|
| Client / Server peak RSS |15.65MB /15.48MB|16.90MB /16.86MB|

B source protocol conservation: client read UDP9635/staged9635, TCP21622/staged21622; server UDP9632/staged9632, TCP21487/staged21487. Full-session counters include warmup/steady/drain; do not compare directly with steady 5884 offered. Receiver authenticated LINK malformed/discard 0/0, actual TUN write failures 0/0, original peer receipt readback true, Stop and namespace cleanup PASS. B loss meets v2 <=0.25% each way under real 2% independent netem (client1.94%, server2.09% observed). No kernel UDP send/receive errors, PSI some peak0 and steal0.

CPU tradeoff is real: B uses ~0.22s more per process in this 60s measured window (~13% rise), and ~1.2-1.4MiB more RSS, but B also advances substantially more true TCP/record work with far shorter tails. Do not call this an absolute CPU optimization; accepted correctness/latency repair under user-allowed bounded memory. 512 fixed M1 backing slots does not establish high-rate 500Mbps or endpoint-shared 512MiB qualification. One Action cannot prove independent modes, idle/blackhole, multi-client HOL.

Exact native B [39913063383](https://github.com/lly8666/wbd-next/actions/runs/39913063383) 75/75 recovery and nine MTU functional PASS, artifact12483243411 ZIP SHA256 8a6a8c240430b32f4270085c45569245f65476ba1fb6ff987942a2169a813479. A old native bundle artifact12482468452. Structured receipt P1-TUN-preloan-Normal2pct-sameVM-AB-result-20261023.json. No further identical seed reruns.
