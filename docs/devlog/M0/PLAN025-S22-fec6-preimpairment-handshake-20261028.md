# M0 S22 — original FEC6 pre-impairment Go FakeTCP handshake failure and discriminating trace

Original S21 exact-source run40613090176 FAILED after binary SHA and Python/shell preflight PASS, but **before** any 30%-loss/200ms kernel impairment, while Go FakeTCP authentication starts. Client context deadline20s, server never ready, raw veth only ~10 client TX/9 server TX packets; actual stress offered ZERO, 150Mbps/30%/200ms product result NOT_RUN. Artifact12782939907 digest SHA256 c48830b189dde2f2dbbfe034022932edf599961c77c247f45637b2de3301a106. This same 10/9 preauth failure recurred earlier across Fixed4,Fixed5,Auto,Fixed3 with identical original ARM64 product binary, later source-locked tests passed when authentic handshake completed; no argument for host CPU 150Mbps bottleneck.

Targeted repair-before-test review: read exact original Go runClient WaitEstablished 20s and server SYN/association/AcceptAuthenticatedPeer, shell ready loop, recent S9 verified trace, and current NETWORK_TRIAGE. S22 is one **read-only diagnostic retry** with already-built original Go/Rust SOURCE f7ee, no product/build/policy/ABI/timeout/profile change; copy only S9 5 scheduled kernel veth and FakeTCP exact tuple counters at readiness loop iterations1/15/35/65/95. On startup success execute unchanged original 30%/200ms netem genuine damaged FEC6 60s bidirectional business; on failure retain earliest counters, original FAIL. Game4 separate running Action unaffected.

```feature-impact
{"kind":"none","ids":[],"reason":"Add exact pre-TLS Go fake-TCP veth/tuple progress snapshots to a single source-pinned targeted FEC6 test; no production code or spec changes."}
```
