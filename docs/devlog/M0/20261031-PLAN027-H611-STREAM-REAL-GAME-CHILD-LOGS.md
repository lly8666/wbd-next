# PLAN027 H611 — recover native Game failure logs without more timeout layers

H609 genuine Game2-FEC SOURCE80ee Action41190352345 remained running through independent +727s force cancel; original artifacts lacked a native product report. Root may be a Windows/WSL OS step, handshake or Stop; the source evidence cannot choose one. H602 added a 510s `m0_wl_windows_bounded_cmd.py` wrapper *around* the existing `m0_wl_native_step_runner.py`, hiding all stdout/heartbeats in an unstreamed temporary file until the wrapper finished. That made the long Action appear frozen and, on independent cancel, lost the original error.

H611 deletes only that redundant Game outer Python wrapper, not any driver, control semantics or safety timeout. The direct native step runner uses a regular file for the one real E2E test child's stdout, streams by byte offset while its PID is alive, reports errors and 20s heartbeats, and enforces the existing Game **360s mode / 440s batch**. The Windows full-step **600s** watchdog and independent Ubuntu **720s** action force-cancel remain, with owned cleaning/reporting still required. No raw inherited pipe and no new process controller. Offline contract assertion updated. This is observability/fail-fast work, not a claim that Game-FEC handshake or Stop is fixed; source-locked network retry only after cheap CI.

H610 has dispatched **13 separate A/B/C/Game-off** Actions from one immutable SOURCE80ee product build (run41190352345, hashes in original artifact). No duplicate dispatch; wait for exact outcomes and follow the five PLAN027 obligations. A5 remains WAIVED.

```feature-impact
{"kind":"none","ids":[],"reason":"Remove duplicate test subprocess wrapper hiding Game native progress; keep original PID-bound run guard and independent Windows/Ubuntu deadlines. No product change."}
```
