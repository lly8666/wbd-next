# PLAN027 H603 — retain only reusable Game native watchdog after exact rescue

Exact H602 rescue Ubuntu Action 41187706865 **SUCCESS**: source-checked force-cancel requested on original H601 Game2 FEC run41186157073. Original run ended **CANCELLED**, native step no original mode report/owned Stop (not PASS); frozen Windows and Linux compile+boot artifacts retained. H601 orchestrator41186143741 ended **FAILURE**, Game4 was not dispatched. These are one actual stuck product trial plus monitors, not three product trials.

H602 cheap main original workflow Action41187706880 failed only `tests.test_m0_wl_native_os_deadline` assertion asking for literal quote characters around 720 while current correct watchdog records `720` in regex and workflow dispatch expression. H603 fixes this exact assertion.

Prevent recurrence and preserve failure diagnostics: 720s Game external deadline now starts from actual `Launch actual WSL2...` step's GitHub job started_at (with job-start fallback), NOT minutes of earlier signed-driver/WSL2 boot, so the 510s bounded PowerShell native child and 600s Windows step can fail and upload partial original evidence before an external force-cancel. Normal/Fixed/Auto and C 300s retain 1200s external limit. Remove the consumed emergency H602 recovery job entirely; no stale one-off cancellation code remains on main. User A5 old Go benchmark remains WAIVED and not repaired.

```feature-impact
{"kind":"none","ids":[],"reason":"Workflow and test-only exact incident cleanup; retain H602 Game health/step fixes, no product behavior changed."}
```
