# W39 actual receipts

## W39 2026-10-25: 100Mbps same mixed packet distribution safe diagnostic with real sparse 64B first-arrival

After W38 mixed200 A/B both failed with source TUN drops/CPU PSI peak60% and TCP heavy backpressure, W39 intentionally de-escalates to single low-load 100Mbps each so it does not re-stress the capacity_stop host. This is not an attempt to replace or erase user's 200Mbps requirement.

Exact native W36 product source861f0396264734f97658243156060f13e6a2f74f build Action40150749260 artifact12582379708; original true Fixed Maximum6, outer DATA retrans OFF with genuine0, real M2 reverse, 30%IID netem actual,300ms one-way, outer600Mbps, source fq600, static owned veth, 15s warmup30s measure30s drain. Packet weights by count 64:6 96:8 160:10 256:11 512:15 900:20 1287:30 (35% <=256B). UDP96%=96Mbps, two actual Linux TCP socket flows share4%=4Mbps, separate20Hz64B probes.

[W39 action40151444036](https://github.com/lly8666/wbd-next/actions/runs/40151444036) SUCCESS true PASS_SCOPED_OBSERVATION, artifact12582309090 zipSHA256 80fa6550e58c62bdd884d22c816cf7a2f1ec6c5bd45fbe133d5f7723f62f80e0.

| Original business metric | C2S | S2C |

|---|---:|---:|

| UDP delivered / residual |95.958Mbps /0.0464%|95.978Mbps /0.0309%|

| 64–256B UDP sent / delivered |180355 /180240|180355 /180236|

| small UDP residual / p99 |0.06376% /308.6ms|0.06598% /308.7ms|

| netem-aligned longest offered small UDP 10ms zero-delivery gap |0ms|0ms|

| TCP 4Mbps offered / actual |3.9997Mbps, backpressure0|3.9998Mbps, backpressure0|

| TCP framed-record first arrival p99 |943.3ms|925.9ms|

| 64B 20Hz sparse probes sent/peer-real-first-arrivals |595/593|595/593|

| sparse probe one-way p99 / separate reverse RTT p99 |307.1ms /610ms|306.7ms /610ms|

| native Parity planned→sent / expiry |client1019107→1019107 /0|server1020072→1020072 /0|

Both source TUN warmup+steady drops=0, original fq root drops=0, RX capacity rejects0, outer DATA reTX0, Stop drained. Host CPU PSI mean37.65/peak40.43% still high; shared VM cannot establish physical/Windows capacity. Sparse probe first-arrival records receipt before reverse echo and is not inferred from the RTT; 2/595 real missing each side explicitly retained.

**Interpretation:** 100Mbps genuine mixed UDP+TCP and 64B sparse does recover correctly; previously W38 at200Mbps with same packet weights FAIL even though older mostly1287B250Mbps benchmark passed. Small packet count/second and kernel TUN throughput /20-row Parity encode scheduling (not a fundamental 64B header or decoder defect) are primary next questions. 200Mbps mixed is NOT qualified. Do not rerun overloaded 200 or increase rates without CPU headroom. Keep capacity_stop=true merge_ready=false.
