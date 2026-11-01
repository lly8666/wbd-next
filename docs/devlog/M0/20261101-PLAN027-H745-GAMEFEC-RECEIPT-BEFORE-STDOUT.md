# PLAN027 H745 — independent first-fault receipt must precede native console output

M0 GameFEC sole priority, all unrelated PLAN027 tasks paused. H742 true original SOURCE0264 signed Windows NPF/Wintun↔WSL2 Linux native run41286724011 watcher41286729417 still IN_FLIGHT; pretest through SUPERVISOR_LOOP_ENTER had independent proofs but no business/Stop. H744 native supervisor no longer requires synchronous GitHub stdout, its blocked-console pure synthetic fixture Action41287112254 passed 16 tests and governance green; product source unchanged.

During further first-fault audit, H744 GameFecProgress.poll still printed `WL_GAME_NATIVE_FIRST_FAULT` (and BOTH_READY stage) to the potentially blocked native job stdout BEFORE calling `snapshot("FIRST_ERROR")`/`snapshot("BOTH_READY")`, so even a working diagnostic daemon could lose the only robust independent receipt when job log is blocked/BlobNotFound. H745 orders independent snapshot first then bounded local human-readable stdout; pure new synthetic OSError console fixture requires the independent first-error relay to happen before the deliberate console failure, with sensitive token excluded from relay. No new watcher, test scenario, protocol, Rust worker or product change. H745 unit-only Actions, then one true Game2/FEC6 on unchanged SOURCE0264 after H742 finishes. 480s native hard-stop retained.

```feature-impact
{"kind":"none","ids":[],"reason":"GameFEC first-fault and Ready independent diagnostic event ordering only, no product logic or performance claims."}
```
