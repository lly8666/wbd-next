# PLAN027 H614 — recover real matrix result, distinguish fixture failure from product capacity

H610 one frozen `80ee526cc7b466ec6ccbe3cc25caf2f3754996ef` binary build, 13 separate hosted Windows/WSL2 modes: **12 original native Actions success, 1 failure**. Failure [41192901095](https://github.com/lly8666/wbd-next/actions/runs/41192901095) is source-scoped Normal 100M/25ms/0% planned 300s with experimental TUN queue override 2048; actual client/server TLS and initial UDP/TCP reached but test fixture stopped immediately before full measurement with `H491_ORIGINAL_TUN_QUEUELEN_BASELINE_NOT_500`. Not a 300s throughput verdict, not a C100 product capacity failure. Preserve FAIL and no foreign queue reset.

Use already committed `plan027-c-normal-100m-product-tun2048-loss0-300s.json`, which **does not request** experimental `linux_tun_txqlen_packets`: new independent Action runs real product default queue for five minutes, no extra compiled binary. H610 Auto staged240s Action41192868015 succeeded real kernel phases/UDP/TCP/Stop but explicitly calls actual quality grade `NOT_PROVEN_UNTIL_NATIVE_QUALITY_AND_APPLIED_READBACK`; H614 therefore separately dispatches original `auto-adaptive` natural first sustained downshift and `auto-revision` genuine config revision Applied, each as an individual Action on a different VM. Reuse SOURCE80ee build run41190352345 and identical SHA/manifest; correct native script validates each result. Game2/4 off H610 genuine success; highest Game-FEC H612 pending. Additional lifecycle B idle H613 pending.

Full PLAN027 five-part task still not complete; B blackhole/rotation and remaining matrix criteria not waived.

```feature-impact
{"kind":"none","ids":[],"reason":"Three independent source-locked native verification Actions; no production code or defaults changed."}
```
