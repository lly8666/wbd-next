# PLAN027 H534 — recover H533 feature-impact inventory exact missing cards

H533 source [08069b1513a9cba61d0b315dde03505f97ef796c](https://github.com/lly8666/wbd-next/commit/08069b1513a9cba61d0b315dde03505f97ef796c) is the frozen candidate for original signed Windows/Wintun/Npcap and Linux raw/TUN **partial-reliability cosmetic ACK gap abandon**. New source build Action [41072984387](https://github.com/lly8666/wbd-next/actions/runs/41072984387) in progress; no new-source live claim yet. H533 governance [41072962781](https://github.com/lly8666/wbd-next/actions/runs/41072962781) FAIL: `feature-impact` explicitly listed linux-raw-tun and windows-native-transport but their cards remained unchanged. H534 changes only those two existing feature cards to record actual runtime semantic impact and source-scoped NOT_RUN; Windows card compacted below 16KiB with all prior verified rows/FAIL and references intact. No gate change, no code or test re-dispatch. Source remains `08069b...` until tested.

Prior H532 C200 fail, A5 original Go baseline fail, Windows B lifecycle and C outstanding unchanged. User's no-repair-percentage-floor §0.2 remains authoritative, full PLAN027 scope remains OPEN.

```feature-impact
{"kind":"updated","ids":["linux-raw-tun","windows-native-transport"],"reason":"Correct prior H533 source-linked feature-impact omissions: actual Linux/Windows original Rust RX partial cosmetic ACK gap abandonment; no new product behavior in this docs-only batch."}
```
