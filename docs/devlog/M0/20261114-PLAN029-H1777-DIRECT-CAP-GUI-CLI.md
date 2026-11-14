# PLAN029 H1777 | Direct quota CLI and GUI wiring

- Source-only implementation **NOT_YET_TESTED**: pinned original-Go `direct-flow-hard` 1–16384 (default 16384), one canonical CLI/config/WinForms field, `--check-config` effective readback, typed cold `m0NativeV4Options.DirectFlowHard` into existing Rust source; no Tunnel quota coupling. Real compiled WinForms harness saves `2`, rejects `16385`, and reloads default `16384`. Three exact generated overlay blob hashes source-locked against unchanged original Go.
- Full pressure and native network on this SOURCE are **NOT_RUN**; H1775 real D2 and Stop PASS only on previous SOURCE. Remaining D1 TCP53/D3–D5/P1–P2 and default1460/GUI live, IPv6 OPEN. No old WFP/028 matrix or 030.

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Direct-only hard capacity configurable in CLI/WinForms and cold owner, new physical pressure qualification pending."}
```
