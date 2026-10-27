# W53 original Auto A/B: scoped business PASS, C2S downshift NOT OBSERVED

Action [40169675377](https://github.com/lly8666/wbd-next/actions/runs/40169675377) success, precise source request `a944d1c0`, artifact 12590008550 SHA256 `3e0c4270b9066f5161754118b92e640f60982caee9de4d20e7d03e83780e6f8e`. One 8 Mbps/dir Auto scenario ran **A old** `e446fa1` then **B revised** `946346b` sequentially on the same ARM64 VM. Both used frozen built binaries (no in-measurement compilation). Real original TLS, kernel TUN, ISA-L parity, authenticated M2, true 75ms lane delay with C2S 2%→20%→1% and S2C 0%→1%→0% netem. Per-epoch netem RNG unseeded and recorded, so do not attribute stochastic 30-vs-9 high-loss UDP residual difference to source.

Both A/B scoped business PASS; both original owners read `repair_enabled=0`, `original_frozen_retransmitted=0`, zero outer DATA accepted, true parity positive, RX recovered→TUN >0, zero TUN failures and source TUN drops, positive reverse authentic M2 samples, Stop drained and owned namespaces deleted. **Not all-C2S Auto PASS**: A C2S briefly 5→4 during pre-low then 4→6 high, remains 6 on 1% recovery; B C2S 5→6 high and remains 6 through 60s 1% recovery. B S2C independently stepped 5→4→3→2→1. `PASS_SCOPED_OBSERVATION` Action code alone must not mask missing B recovery stage.

B C2S's actual log records *five distinct authentic VALID* 2s cohorts at 06:42:53, :55, :57, :59 and 06:43:01Z, then consecutive `actual-k observation incomplete` UNKNOWN through :10Z, so the bounded 6s retained proof was cleared; no false down action. A's C2S run likewise never returned down in recovery. The frozen design `docs/architecture/FEC_V2_BALANCED.md` section 7 says >=20s/4096 genuine down hold per level and recommends **180s** steady at test end; 60s low-recovery + real M2 8s age may not furnish enough continuous valid coverage. This is **an uncovered observation/convergence gate**, not grounds to lower loss-estimate quality or fabricate an ACK. W54 tests exactly this by extending only the low phase; no load increase.

| Metric | A old | B revised |
|---|---:|---:|
| Measured client process CPU s | 16.49 | 16.65 |
| Server process CPU s | 16.69 | 16.96 |
| Peak client RSS bytes | 22278144 | 21483520 |
| Peak server RSS bytes | 21266432 | 21270528 |
| C2S UDP high loss/missing | 30 / 47068 | 9 / 47066 |
| C2S UDP recovery missing | 0 | 0 |
| C2S recovery first p99 ms | 79.2 | 79.3 |
| S2C recovery first p99 ms | 77.1 | 76.5 |
| native outer DATA retransmitted | 0 both ends | 0 both ends |
| C2S Auto recovery down | NOT_OBSERVED | NOT_OBSERVED |

These same-VM CPU/RSS measurements show no demonstrated CPU improvement and no meaningful leak at 8 Mbps. They do **not** qualify mixed TCP, high rate, physical platforms or the omitted original FEC MTU/Stop-generation exact product matrix. Retain `capacity_stop=true`, `merge_ready=false`.
