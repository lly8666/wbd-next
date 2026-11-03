# H1029 | PLAN028 shared TUN pre-copy, age and byte bounded dispatch

Root cause after H1027: shared reader still allocated/copied a packet before discovering that A's deferred queue was full. Its eight deferred packets had unlimited residence and each silent A forced one timed 1ms wake indefinitely. This was residual cross-tenant CPU coupling despite the no-blocking-send fix.

Fix in original Rust shared reader: closure-based per-client admission rejects stopped owners and full FIFO 8-packet/64KiB deferred budget **before** Vec checkout and TUN-to-Vec copy. Each retained packet has an original timestamp and expires after 100ms; retries never refresh that timestamp. Fair one-try-per-client and exact generation fences/Stop preserved. After expiry reader returns to 10ms idle poll. Stable legacy `backpressure=N reader_joined=1` receipt unchanged; append packet/byte/age/retired drop counters after it. The 64-item session channel, original crypto/FEC/Go and wire format remain untouched.

Original same-SOURCE Linux Rust/Go native workflow adds 4096 dropped A with zero extra packet-builds, 256 interleaved B immediate deliveries, 8-head expiry without sleeping, and 40KiB+30KiB pre-copy byte rejection; H1027 A/B unit, actual 2/5-netns 70 UDP/443, path/MTU and 1%/Stop remain gates. Source remains IMPLEMENTED_NOT_TESTED pending native Action. CPU/p99 magnitude and real high-PPS multi-client overload unmeasured; no performance PASS claim. Historical f823 H1027 native PASS, H998 physical 3/3 FAIL, ARM64 Game4FEC and Win Game failures retained; PLAN028 ongoing.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient","idle-rotation-keepalive"],"reason":"H1029 original Rust TUN per-client bounded pre-copy drop, 64KiB/100ms FIFO and exact-source native unit regression; no protocol changes."}
```
