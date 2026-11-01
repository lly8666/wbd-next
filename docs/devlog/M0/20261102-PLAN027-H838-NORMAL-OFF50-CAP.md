# PLAN027 H838 | One Normal 50Mbps clean capacity, conditional 100Mbps next

- Same immutable original Go TLS/Rust M4 product SOURCE `f5e8f30fa4a5052c9797bbd15b385ec5cfc5d2c3` used in earlier N/R. At full-size 1200B application payload and 50Mbps each direction: ~5208 first packets/s per direction, 10,417 bidirectional PPS; RTT50ms at25ms one-way ⇒ business BDP 312,500B each direction, **not** ciphertext/FEC/control/driver wire occupancy. Bound native memory+queue/CPU before considering next 100Mbps, do not blindly jump to 200M. Original Normal outer DATA repair OFF, FEC off, one real 60s zero-loss dual-direction scene, 5s warmup10s drain. Native required 50Mbps injection, >=99.9% authentic unique first, p99, real tc0 drops, CPU/RSS/host PSI+steal, real M4 F and zero R, Stop/netns clean. If source rejects/saturates, stop harder same-family; product single lock/thread not blamed on VM.
- Independent original diagnostic [H837 blackhole Action 41352697856](https://github.com/lly8666/wbd-next/actions/runs/41352697856) is already running to classify previous true dual 105s blackhole native Client exit1, no duplicate. Windows d0 signed Normal ON 10Mbps250ms30pct source-d0 original full native PASS scoped but lacks bilateral repair grade/Windows OFF paired and physical timing. Both one-lane Fixed6/Auto ON source-f5 native PASS with R/F8.3–8.4%; no causal CPU gain attributed.
- Source/manifest/3 hashes reused, one independent Action/one near-MTU clean case; no code/default/feature changes. A later 100Mbps or higher remains conditional on actual this 50M result and present workload theory, NOT_RUN now.

```feature-impact
{"kind":"none","ids":[],"reason":"One missing bounded Normal 50Mbps clean capacity scenario/test/workflow; all native product source/config/UI unchanged."}
```
