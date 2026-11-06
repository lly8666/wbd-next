# PLAN028 H1260 — retain real H1259 430s, fix reporter Stop fence, replay original artifact offline

## Source and original native workload

H1258 SOURCE `62373ee910b4d43e4660e22a6ababe863d8bc5e4` Action42135894183 previously proved Game4 bounded **up to four** original shared-TUN ingress sources per owned Rust TX turn in genuine same-VM 90s scalar/native Game4Fixed6 + NormalOff A/B (native Game4 overloaded downlink ~98.99% unique delivery, compared with prior non-batched native ~73.79%). No new FEC profile, retransmission, crypto or unbounded queue.

H1259 SOURCE `af2dc107fb9edce01db8a143295b678af6c91bcf` Action [42137210217](https://github.com/lly8666/wbd-next/actions/runs/42137210217) built an exact same-source original Go TLS/Rust x86_64 native ISA-L product and **all ten app endpoints (five users, both sides) completed 430 seconds true coordinated load +10 seconds drain**: 10s warmup, 60s first wave, 240s sustained, 60s 1.3× overload, 60s return to the same 1.0× sustained offered rate. Client tiers: A NormalOff 0%; B NormalAuto 1%; C Game2Off 5%; D Game4Fixed6 15%; E NormalFixed6 30%, each unique authenticated lease, distinct tunnel budget/cipher/OS original TUN, one real TLS server443 and one Rust shared TUN, physical bidirectional tc delay 0/15/50/100/125ms. All qdiscs limit10000 and actual loss near exactly configured.

**Do not falsify original Action status:** it is **FAIL** because its reporter raced Dave's STOP. After the traffic had completed, orchestrator asked all clients and server to Stop, awaited only SERVER `V4_PUBLIC_SHARED_TUN_STOP`, copied Dave's still-writing log and immediately asserted `M0_GAME_M4_FEC_BACKEND_READBACK`. The archived final Dave log **does** contain the genuine native proof (`tx_native_quanta=386420`, `rx_native_decodes=61758`, `extra_accepted=548206`) and all five clients' final Stop. ZIP artifact13465309614 SHA256 `c59939e82baee616ab18bdd643bb83aeb01c70fa0554f02a7ac8d9e7bf6af33f` **55 entries, CRC PASS**, exact SHA/manifest validated. Hence the failure is report receipt ordering, not an incomplete network workload. The original unsuccessful Action remains linked and unchanged.

### Measured results from original ZIP, independently recomputed, no traffic rerun

| Phase | Actual app TX, both directions | Actual app RX, both directions | Unique UDP delivery |
|---|---:|---:|---:|
| 240s steady | 192.0001 Mbps | 191.8173 Mbps | 99.8948% |
| 60s overload | 249.5994 Mbps | 249.4738 Mbps | 99.9449% |
| 60s rate-down recovery | 191.9999 Mbps | 189.9330 Mbps | 98.8124% |

- **Game4 at 15% verified physical qdisc loss**: full real UDP business delivery **100%** in steady, overload (downlink actual23.4→23.4 Mbps), and rate-down recovery (downlink18→18 Mbps), on both directions. Server **all five authenticated per-lease shared TUN pending overflows=0**, total `queue_full_drops=0`, `backpressure=0`. Game4 real native FEC TX386420 calls/RX61758 and bounded extra source reads548206. These are exact same-SOURCE observations only, not all-platform performance PASS or cross-VM strict causal CPU gain.
- **Residual honest FAIL/warning:** NormalFixed6 **30% physical loss+125ms one-way**, recovery downlink **87.644%** unique app UDP despite full16Mbps app TX and zero server shared-TUN queue drops. Last recovery six 10s windows RX Mbps: 16.06,16.00,16.00,16.00,**8.17**,**11.99**. This is a genuine late-run delivery downturn, not proof of Game4 TUN regression or automatic success for all five.
- Average sampled original server one-core CPU73.314% and peakRSS96968KiB across about492s including setup; **not** a product CPU causal gain. Normal/Game2 siblings retained high scoped delivery. Historical H998 original same-connection MTU-shrink FAIL remains.

### H1260 minimal repair / verification

1. Add **product-specific Stop fence** for all five native client logs, plus the Game4 FEC backend marker, *before* copying original Go/Rust Stop receipts into evidence and running the unchanged current-source product report. No change to Rust, Go, TLS, FEC, TUN owner or packet budgets.
2. Restore an explicit `POST_OVERLOAD_RECOVERY_DELIVERY_UNDER_95PCT` diagnostic for **every** configured client, rather than suppressing the 30% peer; this retains the exact 87.644% residual and does **not** convert diagnostic collection success to product quality PASS.
3. Make the H1259 **long** workflow manually dispatched only. Add one **quick, zero-network** H1260 Action which downloads immutable H1259 artifact13465309614 by exact run and checks its SHA256 metadata, SOURCE and manifest; asserts all ten 430s endpoints and all five final Stops; invokes the real updated reporter against these final logs. Expect success of the offline *evidence replay*, not retroactive Action success. Do not run a second 430s matrix.

## H1261 validation closeout (original SOURCE unchanged)

The zero-network offline replay [Action42141025302](https://github.com/lly8666/wbd-next/actions/runs/42141025302) **PASS** downloaded the original immutable 430-second native Action artifact13465309614, validated its source+binary manifest, all ten real native application endpoint durations and all five original-Go/Rust product Stops, then re-ran the corrected original report on the final fully flushed logs. The resulting report emitted **two genuine diagnostic alerts**, including the 30%-loss NormalFixed6 recovery downlink at 87.6436% unique application UDP, and otherwise confirmed five independent per-lease TUN overflow counts of0 and Game4 15%-loss 100% unique business delivery in steady/overload/rate-down recovery. Replay artifact13467007746 SHA256 `2f55d1319bdeea65c6e10a9f71526d24653a50718a6d27e99b79e2e39e7a5fd0` stores the full report. This PASS is the **offline report replay only**. Historical original Action42137210217 remains **FAIL** due to Stop race; it is not rewritten as green. No new 430-second network job was dispatched.

```feature-impact
{"kind":"none","ids":[],"reason":"Native measurement postmortem, race-free per-client original Stop log capture and an offline immutable artifact reporter replay only. No new product or feature behavior."}
```
