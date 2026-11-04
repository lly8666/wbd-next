# PLAN028 H1124 — signed Windows Npcap/WSL2 owned-source route first fault

[H1123 native Action 41807321337](https://github.com/lly8666/wbd-next/actions/runs/41807321337) **FAIL before TLS READY**, not a Windows product cutover PASS. Original Windows Go/Rust compiled, genuine drivers and WSL2 were launched. Native OS selected test-owned `198.19.254.1` on ifindex25 to actual guest `198.19.254.2`; legacy GetIpForwardTable still returned unrelated original WSL gateway `172.26.128.1`. Existing Npcap guest MAC override denied as designed. Separate Restore script failed because ConvertFrom-Json PSCustomObject has no dynamic members.

This narrow source revision applies the already OS-confirmed guest IP/MAC neighbor only to `GITHUB_ACTIONS=true` plus explicit `WBD_PLAN028_WSL_OWNED_SWITCH=1` and exact isolated guest `.2` / original source `.1` / actual gen1 `.1` or gen2 `.9`, same live ifindex. Production next-hop/MAC checks are unchanged. Negative Go test rejects absent owner, stale generation/source, foreign peer/guest/interface; no TLS record or steady wire changes. PowerShell Switch/Restore now Add-Member the exact owned receipt fields without touching runner default routes.

One real Windows Normal original GoTLS/Npcap/Wintun/Rust Action is triggered by `[plan028-win-physical-owned]` on this source; full reauthentication, inner MTU readback, first real business and exact Stop still pending. H998 previous same-TCP hot-MTU FAIL, historical ARM64 Game4FEC Action FAIL, remote ICMP, Android and CPU/p99 remain their previous bounded statuses.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1124 correct CI-only verified Windows WSL2 route and owned alias receipt on H1123 product first fault; source native result pending."}
```
