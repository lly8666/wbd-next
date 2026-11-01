# H781 first Windows Action failure and test-path repair

User priority: Actions transport/control first, then Game2/4 FEC. Other PLAN027 paused, overall PARTIAL, physical NOT_RUN.

New Windows2025 [H780 run41306817415](https://github.com/lly8666/wbd-next/actions/runs/41306817415) FAILED in job124848801198: 21 original native-step tests, 19 passed and 2 errors. Original Windows local probe step SKIPPED, upload FAILED no files. Exact product SOURCE `48ed7ffe82aafa17a125948068a2ca6ee6a1593e` still not run again.

1. `test_file_handle_tailer_reports_first_process_exit_not_descendants`: promptly returned parent rc3, but its deliberately inherited `real.log` remained locked by a test orphan; Windows TemporaryDirectory cleanup raised WinError32. Fix test-only: record exactly this grandchild's PID and terminate it in finally after asserting prompt parent exit, without changing transport/Stop code.
2. `test_h748_actual_unread_os_pipe_full_does_not_hold_game_deadline`: Windows observed child supervisor rc3221225477 (`0xC0000005`) instead of expected 124 with no stderr. This is genuine Windows native test-control failure, not FEC product error. After original main deadline has requested Stop/killed and reaped owned child, end only the *same supervisor* using Windows `TerminateProcess(GetCurrentProcess(),124)` instead of CRT `os._exit` with another thread blocked in stdout, retain non-Windows behavior. One Windows retest must verify; do not backfill success.
3. Existing fixture failed before new probe, so always-run upload also had no files. Workflow now initializes bounded test-only evidence before suite; runs unit then original-runner subprocess even if suite fails, always uploads local files and explicitly fails at end if either outcome failed. Adds `GH_TOKEN` to authenticated post-failure GitHub API read. No test cancellation or product PASS inferred.

Game2/FEC6 original H771 run41299653430 remains CANCELLED/BlobNotFound; watchdog/management artifacts H775/H776 are independent NOT product. Full five-stage route/WFP/DNS/MTU/lease crashed WAL still unqualified; do NOT start 480s original Game before safety proof.

```feature-impact
{"kind":"none","ids":[],"reason":"Windows Actions native runner termination, precise synthetic fixture process cleanup and always-upload error evidence, no GameFEC product behavior."}
```
