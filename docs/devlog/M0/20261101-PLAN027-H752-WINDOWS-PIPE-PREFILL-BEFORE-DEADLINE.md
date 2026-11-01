# PLAN027 H752 Windows unread pipe guaranteed before native PID deadline

Task remains PARTIAL; only GameFEC allowed.

H751 Windows2025 fixture Action41289673986 **FAIL**, genuine native supervisor rc124 without blocking, but synthetic one 64KiB `os.write` yielded stdout bytes0 at exit (Windows CRT may wait to commit the full request). Cannot call it a saturated pipe proof. No product FAIL. Previously H750 run41289517226 stdout3770 vs 4096 also FAIL. Preserve negatives.

H752 fixture-only change: start one daemon writing committed **512B** chunks to actual unread Windows stdout pipe BEFORE test owner begins; sleep .4s for deterministic saturation, then run same native PID owner 1s deadline (second diagnostic thread may block independently). Assert returned124, >=4096 bytes written, and pre-cancel faulthandler stack includes `block_actual_output`. Windows CreatePipe, taskkill and os._exit genuine, no WSL, no Npcap, no product or additional watchdog. One test in one Windows Action, no new product binary or Game native dispatch.

H749 real original SOURCE0264 same authenticated Windows/Linux Game2FEC run41289375904 & watcher41289383815 remains IN_FLIGHT; separate stage receipt `SUPERVISOR_POLL_OK` [41289524827](https://github.com/lly8666/wbd-next/actions/runs/41289524827) PASS, no business/Stop proof yet. No other PLAN027 dispatch.

```feature-impact
{"kind":"none","ids":[],"reason":"Synthetic Windows stdout fixture now guarantees committed small writes before PID loop; product untouched, historical fixture failures retained."}
```
