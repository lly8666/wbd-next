# PLAN028 H1165 — recover queued Actions, correct exact ARM fixture assertion

Checked new results instead of dispatching duplicates. H1162 ARM Action [41863838024](https://github.com/lly8666/wbd-next/actions/runs/41863838024) failed before UDP from escaped literal \`${6:-0}\` (fixture-only). H1164 ARM Action [41864678877](https://github.com/lly8666/wbd-next/actions/runs/41864678877) built native ARM ELF183 and ran baseline 12+12+12 UDP plus OS source 10.25.0.3→.9 / physical 1280 readback; failed after new path in embedded Python line 15, because the assertion rejected even Carol's *initial* generation=1 READY. The existing supervisor records generation1 READY at initial startup; this is not evidence of Carol reauthentication. Fix exactly that negative check to require only generation1; on failure expose `alice/bob/carol.log` instead of nonexistent `A/B/C.log`. No Go/Rust/wire changes. Full ARM physical new32/Normal live48 and Stop remain unqualified until replacement current-source run.

Windows independent signed original native Normal [41864386204](https://github.com/lly8666/wbd-next/actions/runs/41864386204) **PASS** SOURCE `a27178d2`: owned source IPv4 198.19.254.1→.9, original Go TLS, Npcap/Wintun↔WSL2, Rust, both directions real kernel UDP+TCP, generation2 ready, generation1 WAL-owned Stop, OS inner 1389/1389 and MSS1420 on outer default1460. Observed mutation→ready 13,110ms; notifier→TLS, auth→first packet and CPU/p99 NOT_MEASURED, not a 200/500ms end-to-end SLA. Windows not counted for Linux alternation.

Preserve PLAN027A H998 same-connection online shrink FAIL, ARM Game4 Action FAIL, remote ICMP NOT_MEASURED, old/new CPU causality unproven. No 027/027A matrix rerun; next native Linux is still ARM64/ARM64 for this incomplete scene, then x86_64/x86_64. Evidence [H1165](../evidence/M0/PLAN028-H1165-COLLECT-H1162-H1164-ARM-H1163-WINDOWS-20261104.json).

```feature-impact
{"kind":"none","ids":[],"reason":"Only test-only fixture assertion/diagnostics and scoped evidence/cursor; original product runtime unchanged."}
```
