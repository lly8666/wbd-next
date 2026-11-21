# H2217 — H2216v2 physical Windows field FAIL, PktMon header-only

2026-11-19 M0 received user-supplied `wbd-all-components-20261119.zip` (archive SHA-256 `3a688065c19d61740121e2d29cd691310c3b5d0d557f314793563eb539a0083e`). Reported binary version H2216v2 SOURCE prefix `91b9d52`; installed executable SHA/hash **not supplied**. Raw packet captures, private source addresses, identity/credentials and ETL stay only in user attachment, not repo.

**Observed physical FAIL**: 18:14:57–18:15:23 Beijing local original Windows client; TLS authenticated, Rust workers 2; `TXCopied=32`, `RXDelivered=0`, `TXAfterRX=0`, `WorkerError=0`, `Rejected=23`, final `context deadline exceeded`. `PLAN029B_WINTUN_IPV6_SKIPPED_STOP packets=23`, so Rejected did not show an additional counted TCP parser or AEAD rejection. It does not prove NPF RX saw any DATA. The PktMon trace holds 80 component packet events (about 15 distinct header groups) and 30 TCPIP drop events; server inbound TTL=52, DF=0x4000, IP header checksum valid for captured heads; 54B snaplen truncates TCP payload and prevents full TCP checksum/AEAD validation. Physical NIC, WFP and Npcap **components** saw early server packets; this is not proof `pcap_next_ex` in handed-off Rust capture delivered them. TCPIP endpoint-not-found (20) and arbitration-unhandled (10) are separate stack events and not proven root cause.

Chronology: server SYN/ACK 18:14:57.648, initial 1200+708B server payload 18:14:57.901, other small server packets through 18:15:00, Windows outgoing at 18:15:03.058 / 18:15:16.570 / 18:15:21.958, client exit 18:15:23, and **late server-direction 87B payload at 18:15:29.912** (unknown retransmission vs control). Pcapng microsecond timestamps checked against PktMon UTF-16 ETL text; do not mistake the 32s elapsed range for 3.2s. `TXCopied` records native Npcap copied-prefix status, not independent physical evidence for *all* 32 frames.

Earlier [H2216 source-matched CI](https://github.com/lly8666/wbd-next/actions/runs/44495120323) Linux independent SNAT/DNAT/UDP/Stop and Windows build remain historical `PASS_SCOPED`, **not** the same physical WAN scene. This new physical trial is **FAIL**. No code-level fix has been proved by this attachment alone. First next scope: same-window Go→Rust NPF reader handoff, event vs `pcap_next_ex`, bounded IPv4/TCP/AEAD counters and server actual post-auth reverse send; capture full private test payload *only if required and sanitized*, no promiscuous broad logging or unrelated TTL/wire changes. Full PLAN029/029B exit remains OPEN.

See [structured evidence](../evidence/M0/PLAN029-H2217-H2216V2-WINDOWS-PHYSICAL-PKTMON-FIRST-REVERSE-FAIL-20261119.json).

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"Record actual Windows field regression FAIL and narrow first Go-to-Rust NPF/server reverse boundary, without reinterpreting earlier scoped NAT CI PASS or claiming new product source behavior."}
```
