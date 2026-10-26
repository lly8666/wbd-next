## W51 2026-10-25 — Resume ORIGINAL FEC functional mainline from exact 3af257cd; genuine M2 positive confirmation latency

**User correction honored:** `experiment/fec-network-tuning` at exact `3af257cd1a353a47d424094a689fa5179b198a07` is the selected FEC functional mainline. W48–W50 special stepped-IID loss requests now CLOSED without rewriting or erasing their historical evidence. This W51 resumes that FEC branch, **no main branch merge/import, no network-matrix code, no change to native FEC math/priority/Rust packet engine or outer DATA restoration**.

Original Rust already exposes native full cumulative 8s-mature `positive_confirmation_lag_ns` and `positive_confirmation_samples` for actual original M4 first-copied DATA with unambiguous original M3 authenticated reverse kind1 M2 positive. Go Auto already consumes the same `rustOwnerFec2MatureQuality` array. W51 narrowly publishes `positive_lag_ns`, `positive_samples`, `positive_mean_us`, and `positive_mean_known` in original-Go CLI FEC M2 proof (client/server) through existing read-only bridge. No samples -> UNKNOWN, never fake 0ms or fallback `srtt_us=600000` (OFF outer shadow default); logs require actual original native proof. The reported latency measures first copied DATA to positive authenticated confirmation including feedback scheduling, **NOT one-way latency, TCP RTT, FEC age, or p99**. No new control/feedback packets, no per-packet Go work.

Exact new source [e446fa1cf09ebfb259da3d764abf8f8ed8d4211f](https://github.com/lly8666/wbd-next/commit/e446fa1cf09ebfb259da3d764abf8f8ed8d4211f); native ARM64 actual product [build40167423967](https://github.com/lly8666/wbd-next/actions/runs/40167423967) SUCCESS (original TLS, ISA-L native, M4 two quanta, deterministic missing source to TUN, Go Auto latency counter proven). Artifact12588789024 frozen SHA256 `3bac82b33642335ed3691c763d66c3c556c575f38f92fd635073fc9673ea1cb4`. New scoped network harness parser validates both native fields, arithmetic/false unknown, does NOT rewrite historical older artifacts; contracts [40167596889](https://github.com/lly8666/wbd-next/actions/runs/40167596889), [40167677632](https://github.com/lly8666/wbd-next/actions/runs/40167677632) SUCCESS.

True product [W51 Action40167733514](https://github.com/lly8666/wbd-next/actions/runs/40167733514) `PASS_SCOPED_OBSERVATION`, original 8Mbps each, Fixed3 (requested=applied1 both), 2%IID/75ms one-way, mixed UDP96% two real TCP sockets4%, small35% packet count, independent sparse64B20Hz, outer DATA repair0, owned TUN fq600, warmup15/measure30/drain15. Actual ZIP artifact12588149669 SHA256 `bec3f9384f16a52356a443aac2e4d30f60edd250bce0321a332596991dd25485`.

| Original native proof | Client | Server |
|---|---:|---:|
| 8s-mature original M2 positive DATA samples | 53,875 | 53,938 |
| Actual positive lag sum ns | 8,241,048,743,812 | 8,249,165,558,731 |
| Real positive confirmation mean us | **152,966** | **152,937** |
| Authentic reverse reports | 11,346 | 11,400 |
| 2s/8s uncovered UNKNOWN | 161/161 | 175/175 |
| First/coverage censored flags | 1/1 | 1/1 |
| Native parity planned/sent | 34,699/34,699 | 34,710/34,710 |
| Parity owner expired/capacity unknown | 0/0 | 0/0 |

Both actual 7.68Mbps UDP +0.32Mbps TCP each direction delivered with app record loss 0; small UDP loss0 first p99 C→S89.1ms S→C89.4ms; no original source TUN/root drops, no outer DATA retrans, original Stop cleanup success. **Native M2 censorship/UNKNOWN is retained and is NOT erased by these positive samples.** No claim that the entire 8s cohort is clean/valid or that this is standalone clock-based RTT. Actual FEC confirmation mean near 153ms is plausible for 150ms baseline RTT, not an inferred echo or shadow timing.

**Next FEC mainline:** confirm new exact source Auto asymmetric genuine authenticated stage and confirmation metric once, then finite original FEC product MTU boundary and Stop/generation as needed; no tier/peak throughput extension. Keep `capacity_stop=true`, `merge_ready=false` and do NOT merge into main or import its network recovery.
