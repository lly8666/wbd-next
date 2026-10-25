# W30 diagnosis

## W30 (2026-10-25): 220Mbps frozen ARM64, narrow single-run PASS

Native W29 SOURCE 6246aa82, build40144596602 artifact12579619244 reused; original fixed Maximum6, real outer DATA repair OFF, authentic reverse M2 preserved. One standalone ARM64 job Action40145722367 artifact12581285466 ZIP SHA256 c2acba0adf8de8ae3cb7599e69930ba4e2582df0e4677f34632612010abd0e35. Real 30%IID actual client30.032/server30.002%, 300ms one-way, outer rate600Mbps, original TUN fq600, own static neighbor, each app rate220Mbps, 15s warmup/30s measure/30s drain.

C2S delivered218.145889Mbps, residual0.850472%, p99=312.0ms, missing5504. S2C delivered217.874079Mbps, residual0.977346%, p99=312ms, missing6325. Overall PASS_SCOPED_OBSERVATION but 0.02265 percentage points S2C margin to <=1% loss gate; no repeatability guarantee.

Native parity planned/sent client1216607/1186004 gap2.516%; server1216680/1182083 gap2.844%. Jobs expired1398/1588; unknown_capacity396/427 but pressure_jobs/sources=0 and parity_seal=0. Original TUN and root fq no drops; RX peak236/234 of640, bytes~8.9MB/48MB, pressure eviction/codec/capacity rejects0; no outer DATA retrans; genuine FEC recovered TUN 284121/285276, Stop cleaned.

CPU 30s client32.0/server32.11s; host CPU PSI mean45.53%, peak48.47%, >20% all samples. Each core nonidle79.16/80.22/80.36/80.93%, softirq CPU10.16/10.37/10.24/10.97%, NET_RX/TX balanced, steal0, cgroup CPU throttles0. Full-run original native TX thread21.6 CPU-s vs RX16.6 CPU-s EACH, not a 30-second counter. This is scheduling/CPU headroom, not memory exhaustion or one saturated IRQ.

Code-specific next candidate: StagedParity::next_quantum makes 4 new parity Vec + a Vec of mutable row views on each <=4-row ISA-L quantum, up to5 quanta per k16/r20 full block; W30 each end60k+ full blocks. Reuse four bounded row output buffers per stream for identical math, no change to AEAD, PN, deadline, first-send or copied prefix. Test against frozen W29 once, same VM old/new AB 220Mbps, after native function regression. Do not escalate >220, merge_ready=false.
