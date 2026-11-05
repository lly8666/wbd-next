# PLAN028 H1238 — independent native Windows cold TLS races and owned OS IPv4 notifier

Current user directs remaining PLAN028 test coverage beyond H1221 scoped closeout. Parent SOURCE ac8b869aa7353d08249db8374930990470434acd. Two original Windows test jobs:
1. Windows2022 Go original pinned assembly & 6 tests for native IPv4 callback coalescing, physical source NIC, in-flight TLS cancellation on path change, user Stop never restarts, authenticated rejection non-overridable, timeout retry cannot revive Stop/reject. This is native Windows **Go unit**, not an Npcap+Rust end-to-end product test.
2. Windows2025 owned Hyper-V internal NIC and Windows API NotifyRouteChange2 / NotifyUnicastIpAddressChange, OS selected IPv4 .1→.9 and actual native callbacks, isolated 198.18.246.0/24, no management NIC modification, explicit NOT_RUN if HyperV/admin missing; no false product-TLS PASS.

H1237 exact previous source x86 original Go TLS/Rust Game4 dual physical netem5 run is independent and not changed by this test-only workflow. H1221 Windows seven physical mode shifts mostly NOT_RUN; Android/WiFi radio and remote ICMP not inferred. Historical PLAN027A H998 live same-socket physical MTU shrink FAIL unchanged.

```feature-impact
{"kind":"none","ids":[],"reason":"Current-source tests for Windows cold path and real OS IPv4 notification, without new product qualification yet."}
```
