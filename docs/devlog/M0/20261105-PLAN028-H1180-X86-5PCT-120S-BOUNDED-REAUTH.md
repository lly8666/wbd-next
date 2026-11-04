# PLAN028 H1180 — genuine 5% Game4 TLS retry, longer bounded native x86 stage

[H1178 x86/x86 Action41886868283](https://github.com/lly8666/wbd-next/actions/runs/41886868283) original Go TLS/Rust SOURCE2ad artifact13352306776 SHA256 1a47059b8c4ba37833b622c1e8b23cbe3d7402b78f4b4eedf9a62b4baba923e8. Original 3 protected clients one443, first Game4 physical .3→.9 real new32, other Normal live48 and exact Stop PASS. During second .9→.3/physical1500 return, real kernel `tc netem loss 5%` on Bob's actual mxb0 verified by OS qdisc readback. Genuine Game4 gen3 and gen4 cold TLS each exceeded 15s, gen5 began as the 35s test-only window ended; old gen2 owner remained untouched and other Normal gen1 was not reauthenticated. No new-game business, UDP RTT p99 or final Stop from this second switch: **FAIL scoped, not 5% PASS**. Original 1–30s bounded retry can require more than a 35s old no-loss fixture.

H1180 modifies only this complete test scene: bound second original-TLS retry to 120s, maintain **320 real Normal Auto UDP replies at 0.4s cadence =128s** while the other Game4 changes path, allow any actually authenticated Game4 successor generation>=3 and require its READY before old gen2 exact Stop. After new M4, keep 5% real kernel qdisc while sending 200 no-application-retry native Game4 UDP at 10ms pacing, record receive-only RTT p99, 10ms send/arrival buckets, losses/max delivery gap, remove/OS-readback qdisc then final original Stop. Increase existing one echo server's bounded receive capacity to handle this same test, not a new packet format/pump. No seed, original Go FEC/AEAD/PN untouched, no legacy matrix rerun. One native x86/x86 Action for this distinct full window; next Linux ARM/ARM after completion. Separate Windows H1179 signed Game4 sourcea6 remains in flight.

H998 old same-connection online MTU shrink FAIL, old ARM Action FAIL, remote ICMP and CPU causality still not measured.

```feature-impact
{"kind":"none","ids":[],"reason":"Bound 5% network loss scenario retry window and acknowledge fail in evidence/cursor, no new product or wire change."}
```
