# PLAN028 H1123 — original Windows cold source IPv4 rebind product candidate

The real Windows2025↔WSL2 test-owned alias+UDP [Action41805849503](https://github.com/lly8666/wbd-next/actions/runs/41805849503) PASS proved distinct OS selected `198.19.254.1→.9` and genuine guest L2/UDP reachability without touching the runner default route. That is **not** Npcap/TLS product proof.

This is ONE complete original-Go/Windows Rust/WSL2 product assembly SOURCE candidate, not a new recovery controller. Review showed `m0_native_v4_windows.go` original WSL host MAC override unconditionally required the *first* local source IP on every later generation, so valid network change would fail after true native IP notification. Retain cert/SNI/route-key/credential, guest IP/MAC, protected ifindex, first-generation source, current physical route and OS source readback; permit later generation only when actual `DiscoverPhysicalUnderlay` matches a new OS-selected source on the already verified ifindex, and add pure negative tests for generation1/stale/foreign route. No each-packet routing/wire/crypto/FEC changes.

A single test-only `-Action Prepare/Switch/Restore` Windows/WSL alias owner script makes the original Windows client start on host-owned `.1` to guest-owned `.2`, then changes only owned source to `.9` during live signed Wintun/Rust Normal/off business. The actual native Windows notifier must prompt exact old Go/Rust Stop, new original TLS & Npcap/driver rebind, OS MTU readback and fresh two-way inner UDP. WSL2 original server port443 and fixed default outer1460 unchanged. Reuse original Linux build from same frozen SOURCE, one Windows normal scenario (not seven-mode matrix); route/neighbor/firewall test ownership is exact and restored independently after Stop. Until native Action and artifact PASS, **IMPLEMENTED_NOT_TESTED**, not Windows product PASS. CPU/p99 and precise notification→TLS/auth→single packet separately NOT_MEASURED.

Historical H998 same-connection hot MTU shrink FAIL, old ARM64 Game4FEC Action FAIL, remote ICMP, Android remain historical/out of scope.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1123 original Windows same-ifindex OS-selected source4 cold reauthorization and signed one-port Npcap/WSL2 native candidate; product PASS pending."}
```
