# PLAN027 H568 — four source525 original scenarios actually dispatched, external Actions watchdog present

Recovered H566 original source525 first/Stop and completed H567 one-time gate [41170790470](https://github.com/lly8666/wbd-next/actions/runs/41170790470) SUCCESS, based strictly on original C50 business result41167357685 plus build41166008870 SHA, not a second product build. Four independent `m0-wl-public-normal-full.yml` Actions, all with preflight exact `perf_reuse_run_id=41166008870`, `perf_binary_source_sha=52566af216edf9dee4068f0bb8bfd0fb8d18dfcb` and matched source-committed scenario hashes:

- [41170803766](https://github.com/lly8666/wbd-next/actions/runs/41170803766): Normal/off 100Mbps both/25ms/0%/60s, scenario hash `737eaf5b2b2da784a0cd740ab41ed9525e00e30c7a46d224d47b81d30f110f15`.
- [41170805473](https://github.com/lly8666/wbd-next/actions/runs/41170805473): Normal/off 50Mbps both/25ms/0%/300s, hash `be41ab76080cef05dd098949fb1e2389452fb668983af8763ee0e8d2b27a3ec7`.
- [41170807537](https://github.com/lly8666/wbd-next/actions/runs/41170807537): Game2 highestFEC 10Mbps/75ms/15%/20s, hash `367a942d9fabbc1dc51e36a9ab311a4125d4022a0c7c71ef9192521115979de2`.
- [41170809210](https://github.com/lly8666/wbd-next/actions/runs/41170809210): Game4 highestFEC 10Mbps/75ms/30%/20s, hash `9ecedf8a69fc7f2675abbb398d28195a1d7533240b08a163dcb91d11f3592411`.

Each workflow has exactly one Windows/Linux native measurement job plus **one separate non-measurement Linux-hosted 20-minute Action hard-cancel watchdog**. The two original source525 Game FEC Actions41167362490/63904 remain CANCELLED with no owned Stop. These **four new Actions are in flight, not PASS**; do not duplicate. C100 outcome determines C200 gate, 300s stable checks independent. All available Stage preflights/source check PASS, full native outcome pending.

Governance recovery: H566 cursor mistakenly had nine context_refs, exceeding existing limit8, corrected in H567 by retiring a stale context-ref (not deleting its file). Then H566 evidence JSON lacked required `source_sha` even though `binary_source_sha` was present; governance failed with exact `evidence is for a different SOURCE`; added `source_sha=52566af216edf9dee4068f0bb8bfd0fb8d18dfcb` without changing data. Main governance Action41171016585 then **SUCCESS**, earlier failures retained. This is schema compliance, not product result.

Windows Game native Health/idle/90s/dead/rotation, A5 Go A product exit, DNS/MTU and remaining C weaknet/mixed/burst still OPEN. Never infer physical PASS.

```feature-impact
{"kind":"none","ids":[],"reason":"Precise source-locked four new Action identities, inherited source-only build and bounded Windows runner stop evidence; governance schema recovery, no user-facing product or data-plane change."}
```
