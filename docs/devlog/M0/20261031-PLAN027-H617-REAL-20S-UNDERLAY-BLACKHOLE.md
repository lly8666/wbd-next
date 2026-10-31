# PLAN027 H617 — independent short full carrier blackout, no GameFEC wait

After H615/H616 original SRC `80ee526cc7b466ec6ccbe3cc25caf2f3754996ef` 12/13 independent A/B/C native successes, real Auto natural one-grade/Rev2, normal 105s idle and Normal 100M/300s Stop; Game2 highest FEC remains cancelled twice after >720s and must not be silently retried unchanged. Instead exercise one short B failure/recovery phase on standalone hosted WSL2 VM: after real UDP+TCP and actual native authenticated Ready, install only existing M0-owned eth0/IFB qdisc from committed Normal 10M/25ms/0% scene, change both directions to **100% real kernel tc loss for 20s**, restore real qdiscs and cleanup exact owned objects, then require fresh bilateral kernel UDP 24 sends/12 reads per side, 60s real throughput and both owned Stop. This is *not* 90s peer dead nor rotation/reconnect, which remain separately REQUIRED. No product code, wire or timers; one Action one scenario, same SOURCE80ee Win/Linux binaries from Action41190352345, no compile or seed refresh. Each failure reports real first cause, never green from fixture alone.

```feature-impact
{"kind":"none","ids":[],"reason":"Source-controlled real kernel 20s outage and recovery fixture only; no production change."}
```
