# H305 — independent source-frozen ARM64 native functional + MTU result

M0 registry rev3 epoch1 task PLAN025 unchanged. User explicitly approved independent parallel functional/low-cost scenarios without sharing ownership or changing the Auto writer.

Exact ARM64 functional Action [40557336142](https://github.com/lly8666/wbd-next/actions/runs/40557336142), attempt1, native test branch `experiment/windows-wiring-arm64-native-parallel-20261028`, `f7ee097e116ab813f9ba23514df01a3f0f9d342a`, parent product source49f816375a9e69bd1cde41df2543b15b58066313 with no production code changed. Bundle artifact12757832935 ZIP sha256 `a6c2f17d6282e0d9817236357b62adb119a9d6d22143daa117458b789872ea45`; native netns artifact12756938404 sha256 `a9c2e338d9edc830774cfb01a5fa488d56fd8c822e9bb54733602c212147570d`; nine MTU cases artifact12757702892 sha256 `d97fd3144b77e542ad073ebc1d9c95620cef7151f6d168f048d752794d8174f7`; all **independently ZIP hash verified** and scoped source receipts include exact Go/ISA-L/Rust compiler manifest.

Native aarch64 `ubuntu-24.04-arm` original Go1.23.12/TLS credential session with Rust1.85.1 shared owner and real Linux raw/TUN, source-locked 2 netns + owned Stop, actual Normal bidirectional 3 ICMP/direction **PASS**, exact `PASS_SCOPED_TWO_ARM64_NETNS_GENUINE_GO_TLS_RUST_RAW_TUN`. Nine inexpensive functional MTU runs **ALL PASS**, actual budget readback from boundary report:
- Normal: 1280→IPv4 budget1209; 1500→1429.
- Fixed & Auto: 1280→1195; 1500→1415. Fixed asymmetric 1500/1280→1195.
- Game2 1500→1413; Game4 1280→1193.
- All directions actual boundary/DF+1 oversized packet rejected; Fixed/Auto/Game each 20 native ICMP/direction with both-owned Stop and netns cleanup.

These are **native Linux ARM64 functional scopes only**: FEC parity recovery NOT_PROVEN, sustained UDP/TCP/p99/N0/CPU NOT_RUN, genuine impaired network NOT_RUN, Windows platforms and physical/global GUI/WFP/DNS NOT_RUN. No extrapolation from these quick ICMP cases to 500Mbps/30% loss. Existing old PASS/FAIL statuses for Windows and Auto unchanged. Frozen S55 Windows natural Auto Action40556191100 and independent Normal N0 Action40557095692 still in-flight at H305, not settled by ARM64 evidence. S55 doc-only S57 Governance40558280033 passed the unchanged 16KiB feature card gate.

```feature-impact
{"kind":"updated","ids":["normal-off","fec-fixed","fec-auto","game-lanes","path-mtu-budget"],"reason":"Register nine exact-source real ARM64 original-Go TLS/Rust TUN + owned Stop and effective IPv4 MTU boundary functions as experimental native-scoped positives; no Windows/throughput/FEC loss/performance/physical promotion, no product code changes."}
```
