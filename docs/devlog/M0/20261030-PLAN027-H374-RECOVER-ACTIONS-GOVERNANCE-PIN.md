# M0 PLAN027 H374 — interrupted-session recovery and exact live-M0 Npcap pin

2026-10-30. Resume from cursor H373 checkpoint `009d7cfc` through main `5d449bcb354e17d0c0aac48a4ac3f6d2a3d5157d`; PLAN027/registry supersede H373 PLAN026 next action. No new product test/dispatch/build in this change.

## Recovered SOURCE-scoped Actions

- `009d7cfc2182b5b5ea80f479664e7298f4d08326` [Windows↔WSL2 Action40903498445](https://github.com/lly8666/wbd-next/actions/runs/40903498445) SUCCESS: actual original Go TLS/Rust native signed Npcap/Wintun modes `normal, fixed, auto, game2, game4, game2-fec, game4-fec` each `WL_PUBLIC_REAL_MODE_RESULT ... PASS`, duplex UDP/TCP and owned Stop. These are short functional modes, **not** PLAN027 impaired matrix or new-SOURCE PASS.
- Same SOURCE [Linux Auto natural40903498710](https://github.com/lly8666/wbd-next/actions/runs/40903498710) SUCCESS: real 26000-first/4096 mature one-step-down; [dead106s new-flow reauth40903498603](https://github.com/lly8666/wbd-next/actions/runs/40903498603) SUCCESS. [Health40903498544](https://github.com/lly8666/wbd-next/actions/runs/40903498544) CANCELED by reusable workflow concurrency; core job passed, separate netns job canceled; neither a full PASS nor product FAIL.
- Newer `de892bb3c80273b298d0fb7fdcb2be9bed128fd9` [Game2-only signed Action40915929519](https://github.com/lly8666/wbd-next/actions/runs/40915929519) SUCCESS real original two-OS Game2; [Windows WAL40915929426](https://github.com/lly8666/wbd-next/actions/runs/40915929426) FAIL in distinct long native OS gate, not converted to PASS.
- Latest `5d449bcb` [governance40922861021](https://github.com/lly8666/wbd-next/actions/runs/40922861021) SUCCESS; [governance-maintenance40922861001](https://github.com/lly8666/wbd-next/actions/runs/40922861001) FAIL exactly two assertions: historical `manifest.json` M4 blobs `6fcb0e18`/`d0d880b1` vs legitimately updated current M0 Npcap files `2901f245`/`53d06d45`. Live `manifest-plan020-m0.json` already pins both current blobs exactly. No queued/in-progress Actions in current repo query.

## This commit / next

Fix only the maintenance test's `M0_AUTHORIZED_CURRENT` for the two already-source-pinned live M0 Npcap files; preserve original M4 `PINNED_FILES` and `manifest.json` unchanged. Cursor H374 records recovered runs and PLAN027 next work. This is **metadata/test fixture only**; no production behavior change, no compilation, no new dispatch, no PASS inferred until automatic CI completes.

PLAN027 remains **partial**: online per-record M2 Receipt/bitmap still exists; replacement mature low-frequency directional quality and outer ACK/SACK one-shot repair not yet implemented, so A/B/C are NOT_RUN. Next batch must implement both directions/callers/config/cards/fixtures before frozen SOURCE and A checks, rather than repeat old M2/7-mode runs. Physical qualification NOT_RUN.

```feature-impact
{"kind":"none","ids":[],"reason":"Interrupted-session source/run recovery, exact current M0 Npcap governance test fixture correction and cursor update only; no product functionality or config change."}
```
