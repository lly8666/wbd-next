# PLAN028 H1213 — original Game2 already idle past dead90 in 128s unrelated highloss fixture

[Action41939187804](https://github.com/lly8666/wbd-next/actions/runs/41939187804) SOURCE7eee original Linux x86/x86 Go TLS/Rust, fixed6 3 protected server rows initial data, but 128s Game4 witness left unrelated Game2 unused beyond **original 90s dead**. The test-side one-packet Game2 heartbeat did not extend that original owner; real kernel attempted binding its expired auto /32 returned Errno99. This is a FAIL, not a highloss PASS. Keep existing healthy mode semantics and solve at the scene level: complete Game2's real twelve UDP, execute its **existing** exact Stop BEFORE the 128s Game4/Normal high30 observation, then require original Game4 UDP320, Normal new authenticated generation and real 200 UDP RTT p99, qdisc restore and final Rust shared TUN owned Stop. One native Action on new exact SOURCE, no new keepalive logic, no FEC/AEAD/data changes. Source0510 true highloss measurement193/200 p99 550.038ms but Action FAIL remains separately documented. Windows Fixed6/Auto/Game4off underway in independent Actions.

```feature-impact
{"kind":"none","ids":[],"reason":"Move completed Game2 fixture exact Stop before 128s highloss observation so unrelated idle90 cannot spoil Normal/Game4 test; no product edits."}
```
