# PLAN029 H1684｜真实Win32无WFP lease单阶段（源码先接，不越级声称OS通过）

- H1683 SOURCE `20c9d13da2d468a975008aacd0b3da8912c3f741` governance [43235392559](https://github.com/lly8666/wbd-next/actions/runs/43235392559) and maintenance [43235391683](https://github.com/lly8666/wbd-next/actions/runs/43235391683) SUCCESS. Frozen old M4 hashes remain unchanged; only explicit current MAIN adapters can differ.
- Reuse **original** `N4NativeUnifiedTxn` v2 four-stage WAL and original `N4WindowsAddressSnapshot`, `N4WindowsLeaseReader`, native `CreateUnicastIpAddressEntry` / `DeleteUnicastIpAddressEntry` / DAD readback. Add one Windows-only `n4WindowsNoWFPLeaseStage` (not shadowing the old guard-backed stage). It verifies held creator Wintun installation/generation/index/LUID/GUID+live PnP SHA, /32 intent, zero foreign addresses and exact WAL v2 `applying/intent` before **real** Win32 create; requires `cleaning/owned` before exact CAS delete. No old WFP Guard, no fake/no-op Guard, no firewall edits.
- New software-only journal permission tests reject changing baseline, wrong generation/state/phase, old v1 WFP WAL and tampered disk. No fake Wintun is opened; this cannot be used to claim real Win32 Apply/Stop. Source/manifest hash and native Windows compilation must return before marking BUILD_PASS.
- **Important:** only lease stage exists for v2; real no-WFP MTU/DNS/routes stages, authenticated product Ready/Stop, old exact-owned WFP retirement, Rust single ingress and Direct TCP/UDP/DNS/FakeIP plus startup-padding are OPEN. Do not wire product `Apply` to an incomplete v2 assembler or claim D1–D5/P1–P2. H1672 signed Wintun TCP listener no-SYNACK FAIL preserved.

```feature-impact
{"kind":"updated","ids":["windows-network-wal"],"reason":"PLAN029 first true Win32 Wintun /32 lease writer under exact v2 no-WFP durable-intent proof, with source-only permission negative tests; no product OS success implied."}
```
