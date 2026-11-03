# H996 — one source-protected Native performance gate; no full product build

One frozen Windows/Npcap/Wintun + WSL2/Linux original Go TLS/Rust binary from SOURCE 1e8325f16e2975a9da3497ab97ac570771a97238 / build Action41546652567. H996 dispatches exactly two independent measurement Actions with 1460-byte complete outer IPv4 MTU, identical packet_mix, seed, bidirectional 3Mbps offered, 25ms tc delay, 0% loss, 60s source-controlled workloads. Original build artifact names and product path non-drift checked once before dispatch. Previously accepted H987 5→30→5 staged weaknet never repeated.

Normal mode Action uses existing `tools/m0_wl_outer_pair.py`: same ORIGINAL Windows/Linux VM, source and binary hashes, 60s actual native repair OFF then owned Stop, next 60s native repair ON and owned Stop, with netem and process/RSS/FRC counters. New allowlisted scenario is derived from the same Game4FEC source-controlled packet family, not a deliberately smaller or different packet baseline. The Game4FEC separate Action uses original kernel/native 3Mbps loss0 60s. Each Action requires real Go credential TLS, Rust owner, signed driver, OS readback, true UDP/TCP business and Stop.

Compare normal ON versus OFF on SAME binary and SAME VM; do not misrepresent this as a measured before/after MTU implementation algorithm delta, or compare different VMs and declare a causal CPU optimization. Report requested payload rate vs actual delivered, CPU seconds per GiB when reliably measurable, RSS, UDP RTT p99 and long gaps, and dropped/unknown/FRC. An Action success alone cannot prove strict performance advantage; keep old/new CPU-s, same-VM algorithmic A/B `NOT_PROVEN` until a true paired control exists.

ARM64 H995 current-source one-build five native jobs is already underway and not repeated. No user-facing 028 may start until 027A exit gates are checked. H996 committed with old `[plan026-coding]` marker solely to skip auto-started redundant original Windows/Linux source rebuild; exact H996 dispatcher is the sole owner of its two native measurements.

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"H996 starts source-locked original Windows Wintun/WSL2 Normal same-run sequential outer repair OFF/ON measurement and separate Game4FEC 3Mbps loss0 baseline with identical packet mix; results start NOT_RUN and causal old/new CPU change is not falsely claimed."}
```
