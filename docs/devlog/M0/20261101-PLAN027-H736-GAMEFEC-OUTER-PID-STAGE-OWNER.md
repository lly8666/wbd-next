# PLAN027 H736 — move GameFEC first-fault stage ownership to the actual PID supervisor

User GameFEC-only priority, other PLAN027 tasks PAUSED not closed. Original product source `0264c2cfc91e05c7c4b8d518fa0efc6707a2ff6b` unchanged.

H735 authentic Game2FEC6 1Mbps/25ms/zero-loss/10s run41282739002 original TLS, signed Windows NPF/Wintun and Linux WSL2 raw/TUN. Its independent separate Actions receipts all SUCCESS: PRE_NATIVE_STEP 41282847590, STEP_ENTER 41282851089, STEP_PREFLIGHT_COMPLETE 41282875508, MODE_STARTED 41282877118. This EXCLUDES preflight/Action-permission/driver/WSL as the immediate hang, but **BOTH_READY/FIRST_ERROR/Stop and actual delivery remain UNKNOWN**; native in progress at this checkpoint, do not double dispatch.

H736 observation: current `m0_wl_public_modes_e2e.py` (inside the test tree itself) owned the 2s client/server file sampler and its nested `child.wait()`. If that mode parent gets stuck in Win32/WSL cleanup or filesystem/CLI, the tracer can also cease. The outer `m0_wl_native_step_runner.py` already owns the one file-backed native batch child, PID tree kill and hard deadline, so move `GameFecProgress` polling to **that single existing supervising process**; remove duplicate nested observer, no extra watchdog/timer/control protocol/Go hot loop. It emits the same bounded independent stage/first-error + MODE_TIMEOUT/EXIT even if child is hung. Keep unchanged mode 240s and batch 310s, and existing Windows/independent 600/720 ultimate protection. This is fixture-only; no new GameFEC product PASS or old SOURCE promotion.

First test assembly Action41283288111 FAILED because native runner was imported via `from tools import ...` by existing H708 fixture, while new direct script import only resolved top-level `m0_wl_gamefec_progress`; H736 commit4ecbf809 uses explicit `__package__` split for Python module vs direct script. Followup exact cheap Action41283314659 **SUCCESS**, tests.test_m0_wl_native_step_runner and assembly; native two-OS job skipped on ordinary coding push. No new GameFEC product binary was compiled.

Next: collect existing H735 full native + watcher and independent stage first. If still stuck/BlobNotFound, one new same SOURCE original signed Game2FEC after source-locked H736 harness only (no redundant builds). Determine exact last worker stage and Stop; fix product minimally based on evidence.

```feature-impact
{"kind":"none","ids":[],"reason":"Move actual GameFEC log/first fault collection from a potentially hung test child into existing one PID supervisor, test-only; no product or public ABI changes."}
```
