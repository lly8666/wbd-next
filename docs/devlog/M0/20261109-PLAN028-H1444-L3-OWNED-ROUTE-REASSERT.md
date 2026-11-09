# PLAN028 H1444 — First Refresh reveals original lease /32 missing

[Action 42538681178](https://github.com/lly8666/wbd-next/actions/runs/42538681178) ended failure at first L3 management Refresh (about eight seconds after app began), before 1800-second long test or normal signed Windows/Linux Stop. Its [20-file raw artifact](https://github.com/lly8666/wbd-next/actions/runs/42538681178/artifacts/13640797852) was inspected: two authenticated original TLS443 clients and actual Windows/Linux kernel UDP/TCP PASS; Windows RX/sent 118/118, Linux 95/96, max echo gaps 141/108.44ms. First infrastructure exception `OWNED_MANAGEMENT_ROUTE_LOST`; source product did not fail a UDP/TCP gate. Exact original host default 14:10.1.0.1 persisted before/after cleanup, DNS RESOLVED_A, owner management lease Restore, guest neighbor, Npcap and owned L2 recovery PASS. Evidence `docs/evidence/M0/PLAN028-H1444-87BC-FIRST-REFRESH-OWNED-ROUTE-LOSS-20261109.json`.

Initial Arm created four exact Runner.Worker/Listener management host /32 routes before product startup. First Refresh found at least one no longer matching the lease. Scope-only diagnostic: if and only if a **previously leased and now wholly missing** /32 has no foreign route, original physical default remains exact, owner/source match and OS readback after reassert is exact, reinstall **that same management /32**. Foreign/ambiguous or changed physical default rejects without rewrite. Count `repaired` separately from new `added` Runner destinations. Refresh remains PLAN028 crossOS1800 only, original GameFEC/Normal105 Arm and Restore unchanged; no product TLS/FEC/MTU/wire changes or relaxed long-run/Stop gate.

Original L3 NOT_QUALIFIED, PLAN028 IN_PROGRESS. Historic H998 MTU failure retained, physical/Android NOT_RUN, ARM64 eef2 existing two 1800s PASS_SCOPED unchanged.

```feature-impact
{"kind":"none","ids":[],"reason":"Only source-locked PLAN028 Windows native L3 management /32 owned route restoration and diagnostic counters; no product or wire changes."}
```
