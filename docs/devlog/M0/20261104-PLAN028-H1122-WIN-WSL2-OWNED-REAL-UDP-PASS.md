# PLAN028 H1122 — Windows2025↔real Ubuntu WSL2 test-owned dual-source and UDP preproduct

[Action 41805849503](https://github.com/lly8666/wbd-next/actions/runs/41805849503) SUCCESS, verified original [artifact13309762906](https://github.com/lly8666/wbd-next/actions/runs/41805849503/artifacts/13309762906), ZIP SHA256 `e563eb89d6c4caee227a74f7878b44552a3fed7ed84edf3e1d49f2bae7e07505`; real Windows 2025/Ubuntu WSL2 native virtual NIC and guest eth0. Host **test-owned only** IPv4 `198.19.254.1→198.19.254.9`, guest owned `198.19.254.2`. Actual Windows `Find-NetRoute` chosen new source, genuine Windows UDP sockets from both owned sources received real Linux guest echo, original host/guest IPv4 preserved, runner default routes unchanged, test-owned alias/WSL firewall cleanup attempted. OS source mutation→selected source and real UDP echo 3395.54ms, includes Windows address state convergence; **not native 200/500ms callback budget, TLS handshake or first single tunnel packet latency**.

Strict **PREPRODUCT ONLY**: No original Go TLS, no Npcap/Wintun/Rust inner packet, no generation/old Stop/MTU apply, no hardware NIC change was exercised. This closes the reachable two-physical-source *test fixture* prerequisite, permitting the next signed original product Windows source4 switch test rather than another Linux matrix. [Exact evidence](../evidence/M0/PLAN028-H1122-WINDOWS-WSL2-OWNED-SOURCE4-REAL-UDP-20261104.json). H998 online shrink and historical Game4FEC ARM64 Action FAIL, ICMP remote, CPU/p99, Android remain as recorded.

```feature-impact
{"kind":"none","ids":[],"reason":"H1122 limited Windows WSL2 test-owned OS/UDP underlay proof, not a product behavior upgrade; no Go/Rust source changed."}
```
