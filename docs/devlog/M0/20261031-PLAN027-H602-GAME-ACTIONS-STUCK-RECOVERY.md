# PLAN027 H602 — Game2 Action hung: source-verified recovery and actual nested deadline fix

User reported ACTIONS AGAIN HUNG. Refreshed exact main 511c7dd21af7611ce97f75c0660a089dc359f500 and cursor601, read AGENTS/START_HERE/M0/PROJECT_CHARTER/PLAN027. Original Action 41186157073 completed original Windows + Linux source build/tests and WSL2 Ubuntu boot with PASS; job `native-public-two-os` blocked in step `Launch actual WSL2 Linux and direct full public two-OS product` for many minutes. **Neither UDP/TCP, 15s Health nor real Stop is proven**. H601 Action 41186143741 merely waits on this run; watchdog 41186163300 is a separate monitoring Action. Three green or in-progress statuses are not three product measurements. One real Game2-FEC scene only, Game4 not dispatched; no duplicate testing.

Fixed wrong deadline composition at root, rather than retrying unchanged:
* Scoped Game Windows step cannot exceed 600s (previous 1020), and the actual PowerShell native Python invocation is ALSO guarded by the existing file-backed bounded-OS process runner at 510s, breaking a stalled native PowerShell command wait even if nested Python children are blocked. The genuine original child writes a regular `direct-full.log`; timeout=124 remains FAIL. Existing nested V2 Game 360s mode / 440s child remain, other 300s Normal/Fixed/Auto paths retain 1020s. User's old Go A5 remains retired.
* The independent Ubuntu monitor now accepts an exact input `target_job_limit` of 720s for `game*` (1200s other modes), strictly source/runs/branch checked, performs cancel then force-cancel if Windows runner truly cannot exit; eliminates the prior ≈20m frozen native wait. Cancellation is explicitly not PASS.
* Exact-only emergency H602 push action verifies old run 41186157073 is a workflow_dispatch original at SOURCE511c, path m0-wl-public-normal-full.yml, native-public-two-os genuinely in_progress before requesting force-cancel. No other Action or users' sessions touched, no product redispatch.
* Game HealthClock 15s/90s is anchored at real native worker startup, not the earlier GameAdapter construction during cold TLS, so slow initial handshake cannot spuriously claim an unresponsive peer before the driver is even attached. Existing per-lane authenticated Activity remains; no Go hot loops.

New H602 SOURCE has to pass cheap CI and Windows+Linux Rust core compilation; prior H601 source Game2 original remains NOT_PASS until actual report exists. Independent 90s idle/loss/rotation, Game4 60s Stop and C/300s still OPEN. Existing outer 1% sourcecb475 R/F Windows0.4576 Linux0.4815 historical PASS not transferred. No A5 old Go comparison, no invented native success.

```feature-impact
{"kind":"updated","ids":["idle-rotation-keepalive"],"reason":"Rebase Game Health deadline to genuine native attach and bind stuck Game's real Windows/WSL2 Action to finite shell/whole-step/independent watchdog, preserving prior SRC failure; no A5."}
```
