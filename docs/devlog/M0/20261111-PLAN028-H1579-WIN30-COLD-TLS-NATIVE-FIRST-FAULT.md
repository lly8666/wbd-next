# PLAN028 H1579 — Windows2025 original 30% physical weak-net cold TLS/M4 first-fault

Prior [SOURCE620 H1548 real Windows+Linux4 loss30 Action42942358907](https://github.com/lly8666/wbd-next/actions/runs/42942358907) proved genuine SYN/SYNACK MSS1420 with physical 30% loss and 200ms each direction, but Windows original FakeTCP TLS bootstrap timed out before signed Npcap/Wintun native M4 READY. This remains a different confirmed first fault from the later 0%-loss multi-client data-plane issue already fixed and source-locked H1575 150s validated.

**H1579 one minimal real cross-OS test instead of blindly repeating 600s**: original compiled Go TLS443 and Rust M4 Linux WSL2 server, one genuine Windows2025 signed Npcap+Wintun original client, exact original credentials and server source. Same 30% independent physical damage each direction and 200ms one-way propagation; outer complete IPv4 MTU1460. Read original Windows `WBD_WINDOWS_CLIENT_READY` and server `V4_PUBLIC_MIXED_NORMAL_READY role=server` after real protected TLS, inspect actual Windows Wintun IPv4 `10.66.0.2/32`, require owned Windows Wintun/Rust/WAL Stop and canonical Linux Rust server TUN generation1 reader join/Go authenticated session drain. Clean Npcap, WSL bridge and netem; never invent TLS ACK or synthetic M4. 160s is a **bounded test readiness window**, not a 200/500ms handshake SLA. No business traffic recovery is claimed by TLS/M4 success. If it fails, the earliest actual TLS/FakeTCP stage remains first problem; do not launch 600s full five-client 30% before that resolves. No app expects 4/4 successful zero-loss UDP under genuine 30% packet loss. Original current L2 0loss 1.15x separate Windows runner Action42983815178 continues concurrently; never reuse the same VM in parallel.

The new marker `[plan028-h1579-win30-cold-auth]` selects exactly one real Windows2025 original `mixed-loss30` network job on main and a scoped offline source test, not previous two-scene H1548 600s. Source Go/Rust data path, FEC, Game, shared owner, true Stop, 1460 outer and user configuration remain unchanged.

```feature-impact
{"kind":"none","ids":[],"reason":"One source-locked 30% physical loss Windows2025/WSL2 original TLS443/M4 cold readiness and owned Stop diagnostic. No product, feature, wire or throughput changes."}
```

Evidence [H1579](../evidence/M0/PLAN028-H1579-WIN2025-LOSS30-ORIGINAL-COLD-TLS-M4-20261111.json). PLAN028 IN_PROGRESS; real 30% five-client business, 600s and L3 NOT_RUN.
