# PLAN027 H612 — one original Game2 FEC diagnosis independently of 13 parallel A/B/C

Product SOURCE `80ee526cc7b466ec6ccbe3cc25caf2f3754996ef` artifacts built once by Action `41190352345` and independently checked. H611 removed only the second temp-file wrapper; native test now emits genuine 20s source-log heartbeat and real errors to Actions with 360s mode, 440s batch, 600s Windows step, 720s independent cancel. There was no genuine FEC result in H609 cancelled Action. H612 dispatches one new original `game2-fec` 10Mbps both directions / 75ms / 15% / 20s Action, reuses the exact Windows+Linux binaries and hash, no full rebuild. Game4-FEC waits for actual Game2-FEC source-bound UDP/TCP/Stop evidence; cannot treat deployment or Action banner as PASS. Concurrent H610 thirteen other modes/C/long measurements are independent and continue. Fix only the observed failure stage, not layered new timeouts.

```feature-impact
{"kind":"none","ids":[],"reason":"One source-verified Game2-FEC diagnostic Actions dispatch; immutable product binary and wire unchanged."}
```
