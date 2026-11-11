# PLAN028 H1565 — Windows multi-client first/reverse differential (2026-11-11)

Resumed main SOURCE `b14e5aecf066b138ce4342987cfb78582aa20033`. Prior [H1548 Windows+Linux4 original Action 42942358907](https://github.com/lly8666/wbd-next/actions/runs/42942358907) under 200ms physical delay has **two preserved real first faults**: loss0 Windows credential TLS established, original Rust native TXCopied42/RXDelivered0, no app or 600s; Npcap actual observer saw 49 bidirectional WSL guest/Windows TCP443 frames. Loss30 Windows SYN/SYNACK and MSS1420 observed but original FakeTCP bootstrap stream deadline exceeded before Windows M4 ready. Linux four original TLS/M4 reached only their logged ready subset; not a mixed five-client PASS.

Compare [source0a Windows/Linux legacy native baseline Action42952219446](https://github.com/lly8666/wbd-next/actions/runs/42952219446): normal original client Windows app genuine 25/26 UDP received and Linux server true M4 RX/TX chain, therefore independent Windows native receive can function and failure needs more exact conditions.

**New one distinct H1565 auto-triggered test, no old seed replay**: on one Windows2025 runner/real WSL2, original Go/Rust source-locked Windows signed Wintun + Linux shared TUN server, loss0 and real 200ms each direction only. Start Windows **before** four Linux clients. Its original TLS, Npcap/Rust first+reverse, OS Wintun Ready and four real Windows UDP echoes must complete in that order; failure before any sibling proves the native cold/delay path independently. Only then attach 4 Linux namespaces (Normal Auto, Game2Off, Game4Fixed6, Normal Fixed6) under same protected server port443. H1560 authenticated auto clients receive server-chosen **actual** leases in disjoint `10.66.0.128/25`; each OS TUN readback is unique, no older hardcoded `10.66.0.3-.6` as client authority. Five simultaneous true kernel UDP app sockets must echo 40, Windows owned Stop must leave Bob doing four more real UDP, all Linux/native/server Rust reader Stop and WAL+netem+WSL L2 cleanup checked. The 4+40+4 receipts are short first-fault scope only, **NOT** the requested 600s 250–300Mbps capacity or L3 qualification. No synthetic packet success and no production Go/TLS/Rust code changed.

The old H1548 0/30 600s source contract and fail-closed workflow remain; new marker `[plan028-h1565-winfirst-five-native]` enables exactly one loss0 differential job, scoped preflight + one Windows2025 runner; no manual dispatch or duplicate loss30. If it fails, preserve Action and stop at the real first fault.

```feature-impact
{"kind":"none","ids":[],"reason":"Only bounded original Windows/WSL2 real-OS diagnostic harness and separate source-locked Action; production features, TLS, leases, data owner and existing 600s qualification unchanged."}
```

Evidence [H1565](../evidence/M0/PLAN028-H1565-WINDOWS1-LINUX4-FIRST-REVERSE-SHORT-20261111.json); PLAN028 IN_PROGRESS.
