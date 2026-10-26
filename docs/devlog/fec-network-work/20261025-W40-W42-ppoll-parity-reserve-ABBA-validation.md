## 2026-10-25 W40–W42: exact Linux nanosecond TUN/FEC wait and source-first bounded M4 fairness; AB/BA genuine 100Mbps mixed evidence

**Verified bug:** W35 original_fec_tun_wait_ms rounded future FEC/M2 due within 1ms down to `poll(fd,0)`. Linux poll(2) immediately returns when timeout=0, so idle sessions might spin until the deadline. W40 source 23da99f0de04afe17756542f5176f2759e318747 replaces it with Linux `ppoll` exact bounded nanosecond timespec, still waking immediately for genuinely ready TUN or due owner and never holding locks across sleep. Existing Normal/off/non-FEC 10ms behavior preserved. Unit asserts future900us creates real900us wait, future4.5ms creates4.5ms, queued/overdue=0.

**First simple scheduler not arbitrary QoS:** original Fixed/Auto original TUN/M4 32-record source-first batch. Read budget is 31 new DATA when no queued/near due FEC, preserving one genuine authenticated M2 opportunity. When queued Parity or native FEC deadline <=1ms, read at most23 new DATA, reserving up to 8 Parity rows across two unchanged <=4 ISA-L quanta plus one actual M2 entry. DATA remains 23/32 minimum, all source/TCP order and identical AEAD/PN remain, no new packet allocations/threads/scans, no modification to math/r or original DATA retransmission (still true OFF). On idle non-FEC nothing gets priority; no indiscriminate small/TCP tail reordering or application DPI. This is per-turn opportunity, not a guarantee of 200Mbps capacity.

**ARM64 correctness:** W40 native build [40153525640](https://github.com/lly8666/wbd-next/actions/runs/40153525640) SUCCESS Fixed/Auto original authenticated missing-source recovery to TUN, original M4 staged two quantum prefix, codec ISA-L native cross-block and Max20 row contract [40153525653](https://github.com/lly8666/wbd-next/actions/runs/40153525653) PASS. Artifact12583149711 ZIP sha256 d297411d00a312aeac2557fab6af21d70de88d13ac8a96244f8430081a227ff2.

**Both ordering controls pass** original 100Mbps each real 96Mbps UDP + 4Mbps true TCP two sockets, count 35% UDP application payloads <=256B among 64/96/160/256/512/900/1287B, separate 20Hz 64B sparse peers, one-way300ms /30%IID, original outer600Mbps fq600, FEC Fixed Maximum applied, outer DATA repair true OFF, 15s warmup30s measure30s drain. [W41 A->B Action40153771977](https://github.com/lly8666/wbd-next/actions/runs/40153771977) SUCCESS artifact12584120637 sha256 17e4fd8dfe1c872ed6ca6ecdc7ba84207ff4c2c4eff5a15f785c72442b5ea459; [W42 B->A Action40154125275](https://github.com/lly8666/wbd-next/actions/runs/40154125275) SUCCESS artifact12583383213 sha256 89a4b0014e590b0a66d8492efd817efe354909f875121a54e425065f94b2fa49. Both legs in each same VM, order reversed independent fresh runner to rule out always faster second leg.

| 100Mbps real mixed | W41 old A | W41 new B | W42 new B FIRST | W42 old A LAST |

|---|---:|---:|---:|---:|

| C2S true UDP residual% |0.04269|0.03338|0.02891|0.02950|

| S2C true UDP residual% |0.04463|0.03435|0.04657|0.03842|

| C2S small <=256B residual% |0.07707|0.05434|0.05600|0.05101|

| S2C small <=256B residual% |0.06820|0.05378|0.05877|0.06210|

| C2S small first p99 ms |308.7|307.7|307.7|308.2|

| S2C small first p99 ms |308.7|307.8|307.7|308.3|

| True CPU-s combined client+server, source analyzer `measurement_cost` |61.44|48.42|47.97|61.20|

| Host CPU PSI mean % |37.93|29.36|29.10|36.69|

| Sparse 64B 20Hz C2S missing |1/596|0/597|1/596|0/596|

| Sparse 64B 20Hz S2C missing |3/595|0/596|2/596|2/596|

| Native Parity copied vs planned |exact/equal both directions|exact/equal both directions|exact/equal both directions|exact/equal both directions|

| All Original Source TUN drops and test-owned root qdisc drops |0|0|0|0|

Real per-direction TCP application rate ~4Mbps all legs, no TCP backpressure, no outer DATA retransmission, native parity expiry0, authentic M2 and Stop cleanup. W41 CPU observation B -13.02s /61.44s = -21.19%, W42 inverse order B -13.23s /61.20s = -21.62%; stable in TWO independent A/B orderings, strong evidence the combined ppoll+bounded M4 change can lower CPU load in this 100Mbps mixed load. **Do not promise exactly 21% causal gain**: each leg also differs in CPU PSI on shared 4core Actions host (~8 percentage points), not controlled CPU core quotas or fixed physical host occupancy; nor is the contribution of ppoll vs parity reserve separately isolated. Small C2S W42 A happened to lose slightly less than B, so no unconditional improvement claim.

**Limit**: W38 200Mbps mixed on same underlying older W36 source A/B both FAIL 1% and source TUN drops + TCP injected <0.4/8Mbps under PSI mean 56.6%, not rerun high-load W40 and NOT qualified 200Mbps. This low-load result supports bounded scheduler and stops chasing trivial heap allocations; before a real congestion/QoS classifier profile original TUN read stalls, per-class original M4 actual bytes/age/feedback and ISA-L stages, then evaluate 200Mbps only on demonstrably sufficient CPU headroom. Do NOT reorder inner same-flow TCP payloads or add an extra thread by assumption. `capacity_stop=true`, `merge_ready=false`, main/upstream network branch untouched.
