# M0 PLAN026 — Windows native Actions: close inner WSL PIPE ownership gap

2026-10-29; main-only CI process-boundary batch. This is not new product wiring, not a performance result, and does not alter signed drivers, TLS, Wintun, Game, FEC, M2, kernel delivery, MTU or owned Stop.

## Provenance / recovered facts
- H364 checkpoint SOURCE `a13bbdd2f0c4c229173c95d85cd1da2e603e0f10` and sole later cursor-only commit `6fd154e58307712dfcdd1006890f0e922eab82ec`; no pending product source after checkpoint.
- Same-SOURCE native Windows Action [40874802357](https://github.com/lly8666/wbd-next/actions/runs/40874802357), test SOURCE a13bbdd: Windows Go/Rust/Linux compile + unit gates PASS, true signed two-OS stage in progress when inspected; job logs unavailable during running (404), so real first error remains UNKNOWN and Game product PASS is NOT claimed.
- Completed historical [40847146468](https://github.com/lly8666/wbd-next/actions/runs/40847146468) SOURCE `4c6a7c03328033dff2534922de3ee6f45b06cca9` and [40848387586](https://github.com/lly8666/wbd-next/actions/runs/40848387586) SOURCE `adc586cd200c24eba717e07b9df6f1a0e0572dca`: Normal/Fixed/Auto functional modes passed, Game2/4 and Game-FEC failed, including a Game RX `npcap_read` EndOfStream and native worker exit rc=3. These older source failures remain separate; subsequent Game capture handoff fix has not yet been positively qualified on the current source.

## Single CI defect / minimal change
The existing outer `m0_wl_native_step_runner.py` removes PowerShell Tee/PIPE ownership, but the actual `m0_wl_public_normal_e2e.py::run` still called `subprocess.run(wsl.exe, capture_output=True, timeout=...)`. On TimeoutExpired a WSL/Linux descendant inheriting the write end may hold the parent `communicate()` PIPE open after the owning WSL command has exited or been killed; it can mask the actual first native error and stall cleanup. The exact live Action cause is unverified, so this is a source-proven process-ownership gap, **not** an asserted root cause for Action408748.

Route only the existing OS command helper `run()` through `tools/m0_wl_windows_bounded_cmd.py` (already a file-backed child-tree deadline used by workflow OS preflight). Preserve original argument vector, per-command deadline, stdout, original nonzero exit status, real WSL guest and signed-driver test. Add a regression with a completed parent and a descendant holding stdout, demonstrating the command exits with rc=7 without PIPE EOF. Existing cheap Actions test job already runs `tests.test_m0_wl_native_step_runner`; do not trigger full signed Windows business suite for this helper alone.

## Frozen-source qualification and unverified
- SOURCE is the commit containing this devlog, test and fixture, and exact build SHA is attached by the existing `windows-binary-manifest.json` and Linux manifest; no new product artifact or feature config changed.
- Cheap Windows/Linux checks: Actions PENDING for this commit. Current in-flight SOURCE a13bbdd must finish or be separately recorded; historical Game rc3 and real Stop remain UNEXPLAINED, not overwritten.
- CPU A/B, capacity, physical NIC qualification, newly requested Fixed/Game/Auto/Health settings and Dormant/Wake: NOT_RUN in this CI-only batch. Continue current PLAN026 implementation under registry.goal.

```feature-impact
{"kind":"none","ids":[],"reason":"Source-locked Windows CI WSL control-command PIPE ownership and process-exit propagation only; no product feature, effective mode, packet algorithm, driver or public configuration changed."}
```
