# PLAN028 H1173 — Windows signed Game4FEC6 real owned-source route test

Previously signed Windows↔WSL2 [H1163](https://github.com/lly8666/wbd-next/actions/runs/41864386204) PASS is **Normal only**. Windows native NotifyRouteChange2/NotifyUnicastIpAddressChange and same Go cold source-IP supervisor already support all native Normal/FEC/Game, but H1163 harness intentionally stopped at Normal. A **single test-only mode** of existing `.github/workflows/m0-wl-public-normal-full.yml` is selected via `[plan028-win-physical-game4fec]`: original signed Game4FEC6, authenticated source4 alias `198.19.254.1→.9`, default outer IPv4 **1460** (not 1500), identical owned WSL2 alias preparation and cleanup, same independent real Windows/Wintun+Npcap and Linux/WSL2 original TLS/Rust. Existing `[plan028-win-physical-owned]` Normal branch stays unchanged.

The native fixture now distinguishes Game4-specific original server READY and old Game owner Stop receipts, requiring **two** real original TLS generations, fresh Windows packet app UDP, OS applied MTU readback and original owned Stop. No mock READY, changing steady packet wire or new product recovery controller. This is **not** a Windows Game4 or seven-mode PASS until the new signed workflow and artifacts prove it. Concurrent independent Linux ARM64/ARM64 first-disconnected replacement [Action41877326739](https://github.com/lly8666/wbd-next/actions/runs/41877326739) remains in flight on its own frozen SOURCE; Windows does not count Linux rotation.

Keep H998 original online same-connection hot-shrink FAIL, old ARM Action FAIL, remote ICMP and CPU causal unknown, exact notifier→TLS/auth→first and CPU/p99 unmeasured. 

```feature-impact
{"kind":"none","ids":[],"reason":"Test-only signed Windows one-mode selector/markers, no Go/Rust product or wire modification."}
```
