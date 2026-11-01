# PLAN027 H823 | Next discriminating one-lane Fixed6 FEC OFF at matched Game2 mix

- H822 evidence recovered `41343702310` real original Game2FEC6 outer DATA-OFF: unique first 100% each at 10Mbps/250ms/true30pct/60s, parity120539/120572, 8.2k recovery candidates, p99 258.7ms, 8.24 CPU seconds each, Stop/clean PASS. Product SOURCE `f5e8f30fa4a5052c9797bbd15b385ec5cfc5d2c3`; different native mode and packet mix from Normal OFF prevents causal CPU/recovery attribution.
- H822 governance Action `41344218807` **PASS**, including feature catalog and repo structural validations after fixing H820/H821 `feature-impact.updated`, bounded card, exact `last_tested_source`/evidence_refs synchronization. No product code changed.
- Next most informative test: NORMAL single-lane Fixed6 outer repair OFF using the **identical Game2FEC6 packet mix 96/288/1060/1200B weights10/15/30/45** (910.8B weighted average, ~1372pps/dir), 10Mbps each/250ms each/30pct true netem/60s. Game2/Fixed source code is the same exact original Go TLS/Rust M4 binaries (3 SHA256 reused from run41342800664), no new build. The single-lane authenticated FEC readback, independent repair OFF+R=0, true tc drops, first delivery/p99, CPU/RSS, Go handoff and owned Stop must all be observed.
- Preserve that `scenarios/plan027-c-game2-fec-10m-250ms-loss30-60s.json` specifies the shared network+traffic scene while the new **effective test product** is `mode=fec-fixed, fec_profile=6, game_fec=off`; static explicit validator asserts this. No Game2 mode spoofing, no fixture treated as product implementation; SOURCE vs fixture commit separate.
- Decision still deferred until actual Fixed6 evidence; if Fix6 matches Game2 business at lower CPU, investigate lane overhead rather than speculative repair tree tweaks; if it fails, preserve product-vs-VM distinction and inspect exact FEC M2/M3/native receipts.

```feature-impact
{"kind":"none","ids":[],"reason":"Only one additional source-frozen scoped measurement fixture/workflow and short evidence-based worklog; no native product/config/UI/feature entry modified."}
```
