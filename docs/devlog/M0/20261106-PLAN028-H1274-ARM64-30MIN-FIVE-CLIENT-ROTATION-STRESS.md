# PLAN028 H1274 — five-client continuous lane rotation and cosmetic retransmission, 3×30min

2026-11-06 user explicitly authorized the 30-minute multi-client stress suite with multiple independent parallel scenarios. No earlier 120s/430s tests are repeated. Latest main H1273 governance Action42159049347 was SUCCESS.

Per 2026-11-04 Linux whole-task alternation, this new whole native Linux test is ARM64 client+ARM64 server, not ARM↔x86 and never QEMU. One hash-locked native ARM64 original Go TLS/Rust build; three matrix scenario Actions in parallel after build; one 443 protected listener and five separately authenticated /32 devices, with a single owned server Rust TUN. No new transport protocol, FEC, AEAD, PN, recovery policy or hot path scheduling.

## 1800-second independent scenes

Each scene runs 10s warmup + 240s first_wave (.6×) + 600s sustained (1×) + 300s overload (1.3×) + 650s recovery (1×), 10s drain. All clients are authenticated before true netem loss is installed, then automatically reauthenticate and rotate throughout the test. The client intervals differ 67–127s with ±5s jitter; for EACH client, require at least ten actual authenticated generation replacements and exact old-generation Stops, same /32 lease and no mere timer tick counted as success. Each scene includes NormalOff, NormalAuto, Game2Off, Game4Fixed6, NormalFixed6 with independent cipher, FEC, OS TUN, user, and both-direction TCP/UDP; Fixed6 outer1280, others default outer1460.

| scene | real underlay loss Alice/Bob/Carol/Dave/Erin | delays (ms one-way) | per-client Mbps each direction |
|---|---|---|---|
| baseline | 0/0/1/1/5% | 0/0/15/20/50 | 8/8/6/6/6 |
| heterogeneous | 0/1/5/15/30% | 0/15/50/100/125 | 12/12/10/9/8 |
| pressure | 0/1/5/15/30% | 0/15/50/100/125 | 22/22/18/18/16 |

## Exact telemetry and interpretation

Reuse original /proc 3-second CPU/RSS sampling, real OS TC qdisc counts, first-delivery/unique no-application-retry UDP, TCP framed app traffic, per-phase p99/delivery/generator errors, 30 × 60-second genuine offered/received windows per client/direction, and actual Stop receipts. H1271 true kernel raw-vs-delivered diagnostic is a separate opt-in feature, not a proxy for application delivery. Do not invent 30% packet loss performance success; full native time window is evidence, not a release guarantee.

Only additional production metric: the already-mature Game original frozen cosmetic copy completion increments accepted encrypted record wire byte count and first record wire bytes, preserving counts across lane rekey; Stop displays both. Normal uses existing first_wire_bytes, repair_accepted_wire_bytes, repair_uncertain_wire_bytes. Reporter computes exact accepted record R bytes, cumulative Mbps, R/(F+R) on same record scope, per-client and aggregate. Control C/outer full IPv4 TCP L2 and FEC parity are NOT in this denominator, therefore R/(F+R+C) is explicitly NOT_MEASURED and cannot be invented. Cosmetic repeats preserve original record/PN/Seq; they do not count as application delivery or FEC repair.

The original H1259 430s fixture remains default with no environment variable and stays manual-only. This new run is enabled only with the explicit WBD_PLAN028_30M_SCENE profile. Current-source build and all three 30-minute Actions are NOT_RUN until the new workflow produces SOURCE-locked artifacts; workflow success proves diagnostics completed, not all-platform/product performance qualification. H1259 old 7s S2C gap, H1268 1.007s RAW RX gap, H998 original same-socket online MTU shrink FAIL, remote ICMP NOT_MEASURED, Windows/Android/physical WAN unqualified remain unchanged.

```feature-impact
{"kind":"updated","ids":["game-lanes","outer-opportunistic-repair"],"reason":"Exact Game appearance-only frozen record accepted byte count at existing Stop and opt-in native 30m stress harness. No hot packet/crypto/protocol/recovery decisions changed."}
```

## H1274 initial CI receipt (source-specific)

SOURCE d04ace6c ARM64 original Go TLS/Rust native one-build completed; three 1800s native matrix scene jobs started, results still IN_PROGRESS/NOT_YET_QUALIFIED (Action 42162179000). First governance run found that appended text exceeded feature-card 16KiB UTF-8 bound; cards were compacted without dropping SOURCE-specific historical failures or feature-impact scope. This is governance-only metadata correction, **not another product SOURCE or rerun**.
