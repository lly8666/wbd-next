# PLAN027 H599 — Game2/4 authenticated Rust Health TX and 90s dead in existing workers

User explicitly retired A5 old-Go steady test; cleanup H593–H598 complete and cheap/governance restored. Game AEAD core H597 SOURCE2fa8 Rust native functional/ABI Actions success, but no native Game Health applied claim until real traffic and Stop.

H599 wires the existing v4_native_health HealthClock with default 15s±10% and 90s dead to BOTH real Game native Rust TX workers, with no new Go per-packet callback, thread, timer, or second Game owner. Windows Game native TX obtains shared GameAdapter receiver-authenticated activity, generates a canonical kind0 encrypted Health on an actual lane through the same AEAD/PN, wraps using existing TCP appearance original seq/ack, sends through Npcap and advances physical seq and Health deadline only on definite copied prefix. Error/uncertain do not pretend peer delivery. Pending Game DATA and FEC remain first; lost one NPF lane retired independently. The Game native WaitForMultipleObjects deadline is min(current stagger/FEC deadline, HealthClock 15s/dead90) not indefinite when idle.

Linux Game native TX obtains the same shared AuthenticatedActivity and HealthClock, sends a bounded kind0 ciphertext using unchanged original arena freeze + ScopedRawIpv4Tx original flow, updates seq/clock only on actual native copy and stops on 90s without authenticated inbound record. Health carries original local payload idle; TCP appearance ACK does not refresh peer liveness; an encrypted control is never entered into Game logical delivery/FEC/UDP TUN. RX already supported under H597 and atomics bound to same original GameAdapter generation.

This is a **new unverified SOURCE**. No 90s idle/rotation/reconnect/Stop/P99/CPU/actual Game4 60s network claim yet; original Game4 60s prior cancelled remains OPEN. Real Game2/4 native B tests, 15s Health cadence and 90s lost-peer + reincarnation must pass same-SOURCE Actions. Game4 highest FEC 20Mbps must not be dispatched without real 10Mbps capacity/Stop PASS. 1% outer-repair user goal already proved by old sourcecb475 original native, do not retune. Retired A5 does not come back.

```feature-impact
{"kind":"updated","ids":["idle-rotation-keepalive"],"reason":"Wire current Rust Game2/4 HealthClock 15s encrypted kind0/AEAD PN, driver credited control and verified 90s dead into existing Windows/Linux native TX workers; no new Go hot loop; new source unverified."}
```
