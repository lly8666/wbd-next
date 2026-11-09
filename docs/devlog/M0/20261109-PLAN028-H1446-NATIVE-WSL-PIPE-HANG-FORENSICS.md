# PLAN028 H1446 — Windows L3 360s stdout silent, unbounded inherited-PIPE timeout bug

Original source `deb2c693897a93a9884a40b1a6b74b32c5db6362` [Action 42540960361](https://github.com/lly8666/wbd-next/actions/runs/42540960361) reached user-observed 360s live Windows+Linux app but native step19 is still IN_PROGRESS at review; no original 1800s, no owned Stop or final app artifact. Three older Windows L3 runs last emitted at ~600/720/960s, step19 later remained in_progress after GitHub job ended failure with logs BlobNotFound. Do not infer VPN product FAIL or PASS.

**Definite code-level bug (causal role in this particular stall not yet proved)**: `tools/m0_plan028_h1412_wsl_cross_os_client_preflight.py::wsl` repeatedly called Windows `wsl.exe` with `subprocess.run(capture_output=True,timeout=N)`. L3 `resources` and `refresh_runner_management` called PowerShell the same way. CPython's Windows timeout path first kills the immediate process, then invokes `process.communicate()` without a new timeout. A WSL/PowerShell descendant retaining inherited stdout/stderr pipe handles prevents EOF and blocks the test forever. Existing `m0_wl_windows_bounded_cmd.py` documents exactly that failure mode but L3 hot periodic callers did not reuse it; escalating management /32 or watchdog delays cannot fix this Python pipe wait.

**Minimal fix**: reuse that tool with file-backed stdout/stderr `run_captured`, wait on only the owned OS child PID, use existing exact process-tree kill on timeout (124), preserve bounded diagnostic output. Change only the H1412 WSL and H1430 recurring PowerShell calls. Add L3-only supervisor heartbeat when the test child log is idle for 20s so a future silent real app with active GitHub log can be distinguished from full Runner transport loss. All original VPN product, TLS/FEC/MTU/wire, Windows Wintun, original 1800s/1500ms/TCP/RSS/owned Stop criteria remain unchanged. Offline local descendant-inherited-output fixture returned rc124 in ~1.02s instead of waiting for its 9s descendant; CI regression checks the same.

**No blind replay**: `[plan028-harness-offline-only]` excludes native job for this change while previous deb2 long Action is in-flight; collect its final metadata/logs first. Original historical H998 HOT MTU FAIL, Android/physical NOT_RUN, native ARM64 eef2 two 1800s PASS_SCOPED and Windows L1 e6aa PASS_SCOPED retained. PLAN028 IN_PROGRESS.

```feature-impact
{"kind":"none","ids":[],"reason":"PLAN028 Windows test-harness file-backed child-process bounded I/O and L3 diagnostics only; no shipping product or wire changes."}
```
