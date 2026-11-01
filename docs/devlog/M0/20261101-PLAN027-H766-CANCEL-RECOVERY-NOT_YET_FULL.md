# PLAN027 H766 — H764 cancelled, real postTLS state unknown, full network crash restore NOT QUALIFIED

User scope GameFEC only, all other PLAN027 tasks PAUSED. Task PARTIAL, physical NOT_RUN.

## Genuine latest source state (no new dispatch)

Original Windows Go TLS/Rust NPF/Wintun ↔ WSL2 Linux Game2/FEC6, both offered 1Mbps/25ms/0% injected loss/10s trial, `SOURCE 48ed7ffe82aafa17a125948068a2ca6ee6a1593e`, [run41296364265](https://github.com/lly8666/wbd-next/actions/runs/41296364265) CANCELLED by watcher [41296372101](https://github.com/lly8666/wbd-next/actions/runs/41296372101); fresh SAME source Go/Rust windows+Linux signed builds available artifacts13080200535 and13080245081, compile and original contract suites all PASS. Original job logs cannot be recovered. Independent cross-Action stamps only through `COLD_READY_WAIT`, `CLIENT_LOG_STARTED`; **no postTLS Go entry/exit markers remotely received**. This is NOT proof that Windows Wintun or Rust did not execute: after host routing alters GH API connectivity, independent `gh` action dispatch can stop succeeding. Management underlay loss remains a hypothesis, NOT demonstrated as cause. Normal product Stop, full WAL Undo, real traffic all UNKNOWN.

## Crash recovery gap is real

`N4NativeRecoverState` in `r0/go_overlay/internal/windowsclient/native_product_entry_windows.go` delegates to `N4WindowsRecoverPersistedPreRouteWAL` in `native_orphan_persisted_preroute_windows.go`. This path checks only guard/lease/MTU/DNS **before routes**, and explicitly refuses `*.routes`. It is **not** a fully-qualified original production WAL five-stage crash recovery. Do NOT delete WAL/route sidecar, clear routing table, disarm global firewall, or promote the narrower PreRoute evidence. Actual Windows child-killed real signed Wintun config test `TestN4WindowsHostedRealPreRouteIPCrashWAL` [run41294981531](https://github.com/lly8666/wbd-next/actions/runs/41294981531) PASS ~21.6s but *fake WFP, no routes; MTU device removed not restored*, so FULL_NETWORK_RECOVERY=NOT_RUN.

## H765/H766 existing supervisor fail-close patch

[H765 ab25c46](https://github.com/lly8666/wbd-next/commit/ab25c46e92c33ad2ff1b4dc011182f21b479cbad) keeps single monotonic native PID loop, then when deadline hits locally records bounded timeout, issues a stop-request marker to existing mode and original E2E owner (ahead of taskkill), waits ≤12s in real scenario, only kills test-owned PID tree if it remains; records whether owned WAL and routes sidecar remain. No invocation of PreRoute-only path for actual routes and never infers an OS restore from child exit. This is a **liveness control patch**; no product/data-plane modification or real five-stage WAL restore qualification. [H766 455f130](https://github.com/lly8666/wbd-next/commit/455f13060121b0cdcdab73495e53e52bfea8fd13) adds focused synthetic live-owner cooperative stop and unverified sidecar-preservation tests. CI [41298466562](https://github.com/lly8666/wbd-next/actions/runs/41298466562) SUCCESS, 19 supervisor tests incl. these two and actual unread OS stdout pipe regression. This does NOT prove real Go/WFP/route recovery.

Do not dispatch another 480s Game before a real OS-mutating scoped Windows failure test verifies owner Stop vs abnormal exit, original five-stage route/WFP/DNS restoration or accurately reports unsupported, and before GitHub management egress isolation is demonstrably safe. Game4 after Game2 real PASS only.

```feature-impact
{"kind":"none","ids":[],"reason":"GameFEC one-loop owner-stop-before-kill and fail-closed crash evidence; no product stage, FEC, Windows WFP, route, DNS or protocol semantics changed."}
```
