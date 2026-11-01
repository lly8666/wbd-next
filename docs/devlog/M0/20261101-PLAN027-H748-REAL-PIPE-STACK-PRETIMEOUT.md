# M0 PLAN027 H748 — Real output PIPE and independent Python thread stacks

User instruction: GameFEC only, all other PLAN027 work paused, overall PARTIAL. Prior original SOURCE0264 Windows NPF/Wintun Go TLS Rust ↔ WSL2 Linux Game2FEC 1M25ms/0%/10s run41287639141 CANCELLED at independent 480s native-step gate (real timeout 507s due polling); watcher41287646432 confirmed cancel BEFORE log REST/CLI. Native job log BlobNotFound. Separate rescue receipts PRE_NATIVE_STEP/STEP_ENTER/STEP_PREFLIGHT_COMPLETE/MODE_STARTED/SUPERVISOR_LOOP_ENTER all SUCCESS, no SUPERVISOR_POLL_OK, 20s, first-error, business or Stop. These are test-control observations, never product PASS.

H748 corrects authority: single native PID owner only polls child PID, monotonic time, process-tree kill, enqueues bounded stage events in memory. All file reads/parse, stdout and `gh workflow run` are in optional daemon diagnostics; blocked console cannot disable the 250s test deadline. Game wrapper on native 124 after completed kill uses `os._exit(124)` to bypass interpreter global stdout shutdown deadlock from a wedged optional daemon, only after preserving stack file and killing process tree. Other modes retain file-backed output and original child rc.

One-shot Python `faulthandler.dump_traceback_later` pretimeout dumps with pre-opened retained fd, no locals/keys/packets: supervisor at limit-12s, mode controller after145s (185s minimal limit), actual E2E after105s. Distinct bounded files `gamefec-supervisor-stack.txt`, `gamefec-mode-stack.txt`, `gamefec-e2e-stack.txt` added to existing native artifact. These can distinguish Python stdout/Win32 WSL/Stop stage when artifacts survive; cancelled job blobs and abrupt runner loss remain external limitations. Any stack filenames/source hashes are evidence, not log PASS.

H748 synthetic one 1s PID deadline creates real OS stdout pipe and deliberately DOES NOT READ it while native diagnostics continuously format thousands of bounded Game results; asserts 124 child-tree kill, pipe >=8192B, and faulthandler real thread stack file. No signed Game product run until this and cheap workflow/governance pass. Frozen SOURCE0264 binaries from build41280564979 remain reusable. No new timers/watchdog or product data-plane change.

```feature-impact
{"kind":"none","ids":[],"reason":"GameFEC-only original native harness PID authority, true blocked OS stdout PIPE regression and one-shot Python pretimeout stack evidence; no real Go/Rust product data-plane change."}
```
