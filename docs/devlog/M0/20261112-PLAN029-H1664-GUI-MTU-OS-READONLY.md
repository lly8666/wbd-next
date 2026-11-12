# PLAN029 H1664: native GUI read-only outer/inner OS receipts and physical domain status

- Retains one editable outer `mtu` 1460 default/1500 explicit. Adds a read-only native status line on existing WinForms transport tab; it is only updated by the existing original-Go physical/Rust cold budget and owned Wintun OS MTU receipt; no user inner edit, no writeback on save/mode switch/restart. Initial state remains UNKNOWN, not false 0, not OS Applied. Full native Applied still gates connected status.
- Domain cold start explicitly says resolving original physical DNS; successful Npcap A selection shows sanitized IPv4 but not verified TLS/OS Applied. `server-name` and pre-shared route-key remain separate, no private pre-TLS exchange.
- Actual UI/CLI H1663 SOURCE `2622e9aedd486676d03853b89efaafb4da4207d0` Action `43184887622` SUCCESS before this UI status patch; new SOURCE must independently compile to claim updated GUI read-only behavior. No physical WFP/DNS real-network qualification.
- Mandatory native Rust post-Wintun CN/LAN/custom direct TCP/UDP §2A still NOT_IMPLEMENTED; keep no thousand OS/WFP rules, DNS53 capture priority, signed OS proof pending.

```feature-impact
{"kind":"updated","ids":["gui-config-feedback"],"reason":"PLAN029 added native read-only outer/inner OS MTU status presentation and domain resolution progress to actual WinForms source; guard no inner writeback and do not claim signed network."}
```
