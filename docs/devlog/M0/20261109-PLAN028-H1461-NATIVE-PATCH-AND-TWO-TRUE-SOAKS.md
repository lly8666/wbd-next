# PLAN028 H1461 — genuine five-client 600s and 1800s in parallel with real bounded queue repair

Historical SOURCE548 native x86 Normal75 true 0-loss peak 30s dropped Alice uplink25 and downlink3 UDP packets; original server per-lease pending queue cap8 overflowed 5 times. It remains FAIL_SCOPED. The source data did not establish a product-only versus host scheduling first cause.

Production Rust original shared TUN code now attempts a bounded urgent FIFO drain when a per-lease queue approaches full (at least 6 of 8): at most 8 original oldest packets are offered to the recovered M1 inbox before the new packet is admitted. The existing 8-packet, 64KiB, 100ms caps, ownership, sibling isolation and original cryptography/wire are unchanged. Rust unit regression covers a recovered receiver releasing 8 slots, strict FIFO, sibling and legacy saturation. This is a candidate fix, not a proven 75Mbps product PASS.

New workflow builds one full exact source Go TLS443 and native Rust ISA-L package, then two separate Ubuntu x86 native 6-netns jobs on the same immutable package. One tests exactly 600s five clients with Alice Normal phased 25-50-75-50 Mbps, four simultaneous 2Mbps siblings, 0% configured physical loss and deliberately no rotations; it hard-fails real zero-loss missing UDP, server lease pending overflow, active gap >=750ms, generated actual rate below 95%, missing original server M4 or six owned Stops. The other uses original H1274 genuine 1800s mixed 0/1/5/15/30% physical netem and rotations, source-locked real UDP/TCP and all owned Stops. No old 430s renamed to 600; no separate hosted Windows 1800. Rust, Python fixture, original Go and exact ISA-L source all pinned.

Statuses at authoring: neither new patched-source build nor native 600/1800 results are yet observed, both NOT_RUN. Windows L3 original 1800 remains NOT_QUALIFIED. Prior ARM64 two 1800 and Windows 600 PASS_SCOPED remain; H998 old hot MTU FAIL and Android/physical NOT_RUN remain. PLAN028 IN_PROGRESS. No PLAN029/030.

```feature-impact
{"kind":"updated","ids":["linux-raw-tun"],"reason":"Bounded original Rust shared TUN urgent FIFO drain scheduling under real per-lease 8-slot M1 backlog; exact source-locked five-client native 600s/1800s stress, no capacity or wire change."}
```
