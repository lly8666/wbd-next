# Linux ARM64 client/server — same-source native progress checkpoint
Date: 2026-10-22. Feature branch: `feature/arm64-linux-android-openwrt-autoaccel`.
Source of tested actual public Go/Rust binaries: `9194e20f2f53cd4ac0b85d3e7f5aa136f164d2c3`
Original Go: `a7a82db31fe736ffedee330795a3234d358f1984`
ISA-L: `c387163fcbca62701d646149564c550c78a4f985`.
This is **NOT** a release/product-wide certification.

| Gate | Exact test/action | Verdict and boundary |
| --- | --- | --- |
| Rust platform, AEAD, FEC2/native | [39751199746](https://github.com/lly8666/wbd-next/actions/runs/39751199746) | SUCCESS, ARM64 component only, actual NEON direct equality; product dispatch ratio not measured |
| Frozen ARM64 public CLI + Rust | [39751199619](https://github.com/lly8666/wbd-next/actions/runs/39751199619) | SUCCESS, original-Go client/server + Rust/ISA-L same-source build |
| Normal/off genuine two-sided Linux network | [39753488583](https://github.com/lly8666/wbd-next/actions/runs/39753488583) | SUCCESS, 3/3 ICMP both ways, 2 OS namespaces, real Go TLS/Rust AF_PACKET/TUN, two Stop drained |
| Fixed FEC2 policy application | [39754527848](https://github.com/lly8666/wbd-next/actions/runs/39754527848) | SUCCESS, 20/20 ICMP both ways, both applied=1, pending=false after authentic maturity |
| Auto FEC2 policy application | [39755143674](https://github.com/lly8666/wbd-next/actions/runs/39755143674) | SUCCESS, 20/20 ICMP each direction, both applied=1, pending=false |
| 60-second Normal UDP 10 Mbps each direction | [39755860617](https://github.com/lly8666/wbd-next/actions/runs/39755860617) | SUCCESS, 74,999 received packets / 74,999,000 B forward; same reverse receive 74,999 packets / 74,999,000 B, no iperf receive loss; bounded **capacity discovery**, NOT first-arrival p99/PHY/optimization |
| Game2 two-lane | [39757506578](https://github.com/lly8666/wbd-next/actions/runs/39757506578), [artifact 12416352561](https://github.com/lly8666/wbd-next/actions/runs/39757506578/artifacts/12416352561) | Overall workflow **FAIL** because final harness incorrectly checked Normal FEC2 readback. Independent actual logs show both role READY lanes=2, 20/20 actual ICMP each way, copied=80, delivered=40 each role, rejected=0, authentic reject=0, both Stop drained. Do not relabel original workflow success |
| Game4 four-lane | [39757760559](https://github.com/lly8666/wbd-next/actions/runs/39757760559), [artifact 12416531665](https://github.com/lly8666/wbd-next/actions/runs/39757760559/artifacts/12416531665) | **SUCCESS**, frozen product SOURCE, harness SOURCE `9750e97ffc980a1822724830e57a5349cf29abad`, 20/20 actual ICMP each direction, copied=160, delivered=40 per side, rejected=0, authentic reject=0, real 4-lane TLS/Go/Rust M4, Stop drained + namespace cleanup |

## Prior FAIL retained
- [39749868638](https://github.com/lly8666/wbd-next/actions/runs/39749868638) overall FAILED from nondeterministic Stop fixture, native ISA-L job SUCCESS; repaired by later [39751199746](https://github.com/lly8666/wbd-next/actions/runs/39751199746) SUCCESS.
- [39753912460](https://github.com/lly8666/wbd-next/actions/runs/39753912460) and [39754276465](https://github.com/lly8666/wbd-next/actions/runs/39754276465) FEC Fixed FAIL: 3 packets did not mature applied revision. 20 each direction and two-second maturity was required; never count requested=1 applied=0 as applied.
- [39757506578](https://github.com/lly8666/wbd-next/actions/runs/39757506578) overall Game2 FAIL preserved, despite its independent complete application/network/Stop logs.

## Remaining Linux-only work
1. Demonstrate selected native acceleration at product component/owner boundary, with CPU-safe scalar fallback under missing accelerator. The bundle compiles `native_fec_acceleration`, which does **not** prove actual product Native vs Scalar calls. Explicit NEON C call proves SIMD implementation but not automatic dispatch.
2. Real deliberately impaired link with exact dropped encrypted source and **verified** authenticated repaired application output vs fresh/Stop; must not infer recovery from Fixed/Auto policy applied or ICMP no-loss successes.
3. One qualified same-job paired A/B for ARM64 native ISA-L FEC2 vs scalar with CPU quotas, actual clocks and bounded workload, separately record startup latency/p99 where measurable. No reuse of x86 measured speedups.
4. Real physical ARM64 Linux client/server and crash/stop/reconnect/generation under device conditions; runner netns evidence is scoped virtual OS qualification.

**Deferred**: Android and OpenWrt clients. Do not update them or run their CI automatically during this phase.
**Next discrete action**: real ARM64 native/scalar same-host FEC2 component cost/selection evidence (one existing C k16/r16/1200 e4 ABBA scenario), or if the host has insufficient CPU budget stop rather than repeating. No repeat of the successful Normal/Fixed/Auto/Game4 samples.
