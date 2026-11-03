# H1031 PLAN028 | Linux route MTU and truthful native capacity

Minimal source: `106e5fd20fbf414b946723ba3c0ee3b5aca6819e`.
Linux kernel `ip -j -4 route get` may return a destination route MTU lower than the physical interface MTU; cold path now respects `min(interface MTU, explicit route MTU)` and rejects invalid explicit metrics before TLS/M1 config. Route metric changes reenter the existing native rtnetlink/coalesced OS route supervisor; no new wire, worker or per-packet fallback. A bounded Go unit covers route 1280 under interface 1500, cap 1500 if route1600, absent metric, invalid metrics.
Server startup no longer conflates Go's 32 FakeTCP *cold association slots* with Rust's actual 16 native `prepare_side` session limit. Native limit intentionally unchanged: raising it requires a separate real capacity test and does not unblock full-occupancy overlap by itself.
Run existing original PLAN028 native Go TLS path + Go unit on the exact new code SHA; this source is pending targeted completion. No new claim for p99, physical online 1500→1280 or Windows/Game readiness. PLAN028 IN_PROGRESS.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient","idle-rotation-keepalive"],"reason":"H1031 per-route Linux MTU cold readback and truthful 32 cold/16 native slot capacity label; one small source-native gate."}
```
