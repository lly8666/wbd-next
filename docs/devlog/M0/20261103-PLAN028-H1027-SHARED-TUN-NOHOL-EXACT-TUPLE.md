# H1027 | PLAN028 Rust shared TUN cross-client HOL and Normal raw CPU optimization

## Boundary and implemented code
At entry 61cc2d2, shared physical TUN reader waited indefinitely 100us on one full client inbox; Normal per-session raw open lacked the already available exact-tuple kernel prefilter. User prioritized these two before wider PLAN028 work.
Source b1d9545 changes only original Rust native owner: one full per-session 64-item channel may defer at most 8 more FIFO packets keyed by authenticated /32+generation; one nonblocking send per pending route per turn, and full capacity explicitly increments queue_full_drops. Old owner retire increments retired_drops and cannot erase successor; unrelated accounts still dispatch. Original Linux Normal uses the same exact 5-tuple SO_ATTACH_FILTER already used by Game; AEAD and PN remain unchanged.
Existing nonblocking TUN batch reads at most 8 already-ready frames per turn, reusing 8 kernel read slots. Small shared ingress Vec allocation is pooled through a bounded return channel after its copy into the original per-session M1 loan; Jumbo preserves the original owned Vec path. Split-ingress TX now waits on its own queue message or nearest original FEC/receipt/Health deadline, at most 10ms idle, instead of sleeping 250us every empty turn. No new wire, per-packet Go callback or repair protocol.

## Source truth and narrow repair
Initial source b1d9545 successfully compiled x86-64 native ABI, cross Windows GNU and ARM64; first 2-netns protected TLS+Rust real app 5 UDP each / shared reader routed5 and joined Stop were observed, but mandatory Action 41605334277 FAIL. The native fixture rejected only an incompatibly reordered V4_PUBLIC_SHARED_TUN_STOP log (AssertionError server []); see docs/evidence/M0/PLAN028-H1027-SOURCEB1D-INITIAL-HARNESS-FAIL-20261103.json. It MUST NOT be marked as native PASS.
The next source restores the original contiguous marker backpressure=N reader_joined=1, moves queue_full_drops/retired_drops after that token, avoids recycling empty moved-out Jumbo Vecs, and adds a targeted saturated-A/live-B/FIFO/stale-generation Rust unit to the same original combined native workflow. New SOURCE Action verification is pending.

## Qualification limits
CPU/p99 improvements are NOT_PROVEN without same-source OS workload and process+kernel sampling. This fix does not qualify seven-mode lane switch, Windows Npcap, Game4FEC ARM64, route-key first ClientHello or Android. Retain H998 physical online 1500->1280 small-packet FAIL (3/3), remote ICMP untested and CPU causality unproven. Default outer complete IPv4 limit stays 1460B, 1500B explicit max. Previous H1026 Linux OS switch Action41599359343 limited native PASS stays independent.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient","idle-rotation-keepalive"],"reason":"PLAN028 shared Rust TUN per-route bounded FIFO and no cross-client HOL; Normal exact kernel five-tuple filter; ready batch 8/recycle and deadline-driven original TX queue; source-specific failure retained."}
```
