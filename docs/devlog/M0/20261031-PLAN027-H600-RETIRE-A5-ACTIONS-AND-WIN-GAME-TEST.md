# PLAN027 H600 — remove dead A5 orchestration across full PLAN027 and correct Win Game unit

Latest user specifically retired A5 old-Go A/B and requested dead code cleanup. H593 removed the A5 public workflow input and runner, but historic one-shot PLAN027 Actions still passed `-f perf_ab=false` (now invalid) or `true` (risk of silently transforming old A5 into a new Normal product run). Audited **64** `.github/workflows/m0-plan027-*.yml` files and removed all literal and dynamic `perf_ab` args from their existing one-scene dispatches. Removed actual old-Go A5 extra Action branches from H469/H499/H514/H526/H545/H553/H557, including A5-only trailing scenario rows. Preserve C200, Game2/4, Fixed, Auto and appropriate staged gates. Retired A5 never becomes a fake Normal PASS. Added a source-level delivery CI assertion scanning all current PLAN027 workflows for any `-f perf_ab=` or deleted script.

H599 source47833 original Windows Rust owner ABI Action41185542729 failed **compile only** `E0308` at `v4_game_lane.rs:1173`: one GameLaneOpener test was still destructuring the new `Result<Option<(id,payload)>>` as if it returned a tuple. H600 updates that single test `.unwrap().unwrap()`; shared authentically opened Game kind0 Health and Rust TX implementations unchanged. The Linux G2 and native-functional H599 Actions completed SUCCESS, but new Windows ABI and **real signed two-OS Game 15s/90s** are NOT yet qualified on H600 SOURCE.

A5 historical invalid CPU evidence remains immutable, latest user WAIVED not PASS. Previously tested SOURCEcb475 1% outer repair R/F Win0.4576%, Linux0.4815% stays old-source evidence, not claimed for H600. Do not retrigger old A5 Action, rerun 1% tuning or dispatch Game4 20M until a true 10M60s first/Stop. Still require Game 90s dead/idle/rotation, native Stop, C representative 300s, docs/feature delivery.

```feature-impact
{"kind":"none","ids":[],"reason":"Remove obsolete legacy A5 workflow flags and dispatch-only branches and fix new shared Game Health unit test Option handling. No new product behavior beyond H599."}
```
