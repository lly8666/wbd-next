# PLAN027 H529 — fix staged Auto false clean oracle only, one necessary test

SOURCE7a existing A4 240s [41065120516](https://github.com/lly8666/wbd-next/actions/runs/41065120516) real original Windows↔Linux single test **workflow FAIL** despite report `PASS_ACTUAL_WINDOWS_LINUX_NATIVE_auto`, owned Stop both PASS, actual tc 0→5/15/30→0 stages at scheduled20/40/65/95s, first Windows99.9977%, Linux99.7252%; terminal PowerShell error **"clean V2 native first delivery below existing 99.9 percent gate"**. Harness classified staged scenario with only initial top-level loss0, ignoring committed impairment_stages with intentional loss. Under this profile aggregate99.9% clean gate is inapplicable. Keep existing clean threshold for all-0 scenarios, strict actual kernel+Stop+positive first for intentionally damaged profiles. No product semantics change.

New H529 single exact SOURCE7a prebuilt Auto240 recheck only after verifying failed H527 report actually measured/Stop/positive first, same scene and stage hashes. Must still evaluate actual Mature+120s grade (source7a Linux Auto quality logs show revision2→profile4 then fast_first=0 while slow samples exist; UNKNOWN cannot be promoted as 120s PASS). Linux `WL_REAL_LINUX_OWNED_STOP_REQUEST_FAILED code=1` is a best-effort repeated kill after process already stopped—report Stop markers genuine; no masking other failures.

A5 [41065131823](https://github.com/lly8666/wbd-next/actions/runs/41065131823): one VM B then A, Rust native B 10Mbps/25ms/0% first100% both, owned Stop PASS, 3.2031s whole-EXE CPU/60s; old Go steady A actual early Windows rc=1 ~15.6s, Stop NOT_RUN, `WL_V2_AB.status=INCONCLUSIVE_OR_FAILED`. Preserve as real open product/fixture issue, no CPU winner claim. Game2/4-FEC pending.

```feature-impact
{"kind":"none","ids":[],"reason":"Correct mandatory network Actions test oracle for intentionally staged damage and add source-locked one-scene recheck; runtime/config/feature semantics unaffected."}
```
