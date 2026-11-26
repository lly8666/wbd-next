# M0 client TX cost and Rust compiler experiment intent

Measured exact H2453 ABBA run 45810506381. See docs/evidence/M0/20261126-DUAL-RUST-TCP-CLEAN-ABBA.json. A/B mean 570.134/571.421 Mbps, origin fq600; CPU-s/GiB client 13.114/16.930 (+29.1%), server 14.656/14.669 (+0.09%), host 31.702/35.622 (+12.4%). Native client RX 10.81 -> 7.66 CPU-s, TX 7.80 -> 17.48 CPU-s, TUN reverse packet count +54.9%. One B leg had 39 middle queue admission failures and 11 shared TUN full drops; no blanket no-drop claim. All four complete and Stop. No uncapped or physical performance claim.

User explicitly delegated toolchain decision 2026-11-26. Current stable Rust 1.100.0 published 2026-11-12 (https://blog.rust-lang.org/2026/11/12/Rust-1.100.0/). Keep default toolchain and workspace MSRV 1.85.1; add optional explicit build override and actual rustc version manifest. No Cargo.lock, profile, protocol, dependency or product hot path changes. One clean x86 ABBA run compares both paired dual Rust builds from exact same event SOURCE, A=1.85.1 B=1.100.0; glibc 2.31 unchanged. Separate native build jobs, one measurement VM. Candidate not promoted based on version or build alone. Linux ARM, Windows and other existing target compatibility remain to qualify before repository-wide switch. No blanket MSRV increase unless needed.

Separate diagnostic Action uses previously measured exact B build artifact 15113365713 (run 45810506381) on x86 with software cpu-clock stack profiling of the original client process, same clean download fixture, no A/B performance claim; retain unsupported perf status if runner denies event. Investigate actual ACK packet rate, copies/allocations, deadline indexing, TUN/queue/wake and inner TCP work according to measured samples. No speculative buffer enlargement or new worker. The 600M cap remains for this anchor. ARM baseline and other network conditions follow with independent qualification.

No change to product hot path; build tooling and fixture changes only. 

```feature-impact
{"kind":"updated","ids":["dual-rust-tcp"],"reason":"Record measured clean throughput parity and unresolved CPU gap, no product change or performance promotion."}
```
