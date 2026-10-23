# Network matrix work — scoped P1 Normal/off recovery report (2026-10-23)

**Scope:** isolated Linux ARM64 public original-Go + Rust V4 Normal/off, 60-second steady 2 Mbps per direction, 50/50 UDP/TCP, 99% 1287-byte UDP payloads, 1% 64-byte probes, 2% IID netem, one-way 200ms, one outer repair, v2 0.25% UDP acceptance. This is NOT the final qualification of the entire product or H500 envelope.

## Root cause and fix

Prior source's 128-slot M1 arena retained FrozenRecord payload while awaiting ~400ms authenticated receipt/one repair. Linux TUN read consumed a valid business IPv4 datagram before attempting arena allocate; under moderate burst/load it discarded hundreds of unencoded UDP/TCP with no PN and no possibility of recovery. Receiver LINK/TUN counters separately proved no receiver-side malformed/write losses. Source de55a132 moves owner reservation before TUN read and uses bounded existing feature7 512-slot pool (~1.1MiB/session), making freshness preferred and avoiding consumed-first failure. No on-wire or retry quota semantic change.

## Actions evidence

| Test / precise source | Action | Result |
|---|---|---|
| B ARM64 product + 75/75 recovery, 9 MTU Normal/Fixed/Auto/Game functional boundaries, de55a132 | 39913063383 | PASS |
| Harness contract, request 6f4acf93 | 39913690811 | PASS |
| Same VM A=99042008 vs B=de55a132 two-way real Normal2pct | 39913690718 | A FAIL, B PASS_SCOPED_OBSERVATION, overall job FAIL by A |

Measured UDP final miss A 2.243%/2.498%, B **0.08498% / 0.06798%** <=0.25%. Both B directions 0 TCP packet final loss; surviving TCP p99 about 643/898ms vs A 4696/4954ms. A original owner post-TUN-read arena failure 219/248; B both zero, and both UDP/TCP read/staged full-session counts exactly equal. B receiver genuine feedback_drop 0/0 vs A 266/296; no malformed LINK, original TUN sink errors, UDP kernel socket errors, owned namespace residue or Stop failure.

## Cost and important limits

On SAME VM within measured 60s, client CPU A1.71s -> B1.93s; server1.73s ->1.95s (absolute +0.22s each, approx13%). B peak RSS ~16.90MB/16.86MB vs A15.65MB/15.48MB, roughly +1.2-1.4MiB/session. This is a correctness and TCP-tail win at a bounded CPU/RSS cost, not a CPU optimization. B handles more actual TCP/record work. Netem random choices were unseeded but recorded; corresponding observed ~2% loss, no exact per-packet AB pairing.

Policy and qualification remain source-scoped: runtime outer-single-repair-v2, limit1, shadow logical131072, retain cap1.5s; authentication and Stop remain mandatory. No 500Mbps/RTT600 capacity, endpoint 512MiB aggregate, multi-tenant no-cross-HOL, sustained Fixed/Auto/Game loss, physical/Windows or 50Mbps/30% claims. Historical quota failure and P1 two-repair attempts remain in existing evidence, not silently overwritten.

Full raw measurement: [Actions 39913690718](https://github.com/lly8666/wbd-next/actions/runs/39913690718), artifact12484331372 SHA256 5a689f6ebd0dde500585f56fc83381a108f9c65b9b5f2de0bfa6639795d2c241. Structured precise counters: P1-TUN-preloan-Normal2pct-sameVM-AB-result-20261023.json. No open request for repeating this same scenario.

## P2 Normal/off capacity exploration (no FEC tests; separate from P1)

- [6Mbps/dir 2% loss Actions 39916201119](https://github.com/lly8666/wbd-next/actions/runs/39916201119), exact product de55a132, 60s steady: **PASS_SCOPED**. UDP C→S 5/17650=0.0283% final missing; S→C 9/17650=0.0510%, both <=0.25%. Actual app injector 3.000 Mbps UDP each direction; TCP C→S 2.958/3 target Mbps (243 sender backpressure events), S→C 3.000/3. Both original M1 TUN UDP/TCP ingress exactly matched successful staging, arena_failed=0, pre_read_deferred=0, genuine RX LINK/TUN errors=0, feedback dropped=0, STOP/cleanup PASS. Netem approx1.933%/2.028% observed; host CPU PSI/steal zero.
- **Steady 60s product CPU:** client4.84s, server4.95s (8.1%/8.25% of one core). **Product peak RSS:** 17,645,568B and 17,985,536B (~16.83/17.15MiB). Injectors consumed4.49s and4.20s including setup/warmup/drain, with 24,076,288B and24,334,336B RSS; these CPU durations are not steady 60s like product measurement. Outer veth TX steady 55,797,337B/55,324,575B per direction (~7.44/7.38 Mbps over 60s), including control/repair and TCP ACKs, not a physical L1 NIC claim. Product CPU per received app GiB 115.52/118.95s.
- **Latency warning:** UDP survivors p99 615.8/616.1ms; TCP survivors p99 **5868.8/3067.2ms**. This precludes a no-HOL/low-tail claim even though scoped v2 UDP loss/Stop passes. Possible TCP congestion/backpressure; cannot assign cause without lossless high-rate contrast. No CPU improvement claim relative to older 2Mbps or different VM.
- Prior [10Mbps/dir 2% run 39915315299](https://github.com/lly8666/wbd-next/actions/runs/39915315299) reported INCONCLUSIVE; artifact12484209330 ZIP sha256 e25b87fde2066af6026c7d38f76d80a4c2b37c9a888827267732529488096f8d could not be fetched due repeated tool internal errors. No product/host root inferred. Bounded Actions stdout digest added in bec53e28 to preserve future factual results. Run a distinct **10Mbps no-loss 200ms** capacity isolation next. Product 512 fixed owner M1 slabs, model predicts near capacity at 10M; theoretical only, not empirical failure.

Structured current 6M result: docs/evidence/network-matrix-work/P2-Normaloff-6Mbps-capacity-result-20261023.json. The 500Mbps H500 target, cross-business HOL, endpoint aggregate cap and high-rate loss qualification remain NOT_TESTED, no FEC work this turn.
