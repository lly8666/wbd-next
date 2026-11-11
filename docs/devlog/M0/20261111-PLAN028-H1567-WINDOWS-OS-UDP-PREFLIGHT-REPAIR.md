# PLAN028 H1567 | pure CI literal correction for H1566 original Windows first-reverse

[H1566 Action 42960126194](https://github.com/lly8666/wbd-next/actions/runs/42960126194) failed cheap Windows CI preflight before any original Go/Rust Windows/WSL2 network. Its one failed test searched the nonexistent literal `if($env:WBD_PLAN028_WIN_REAL_COLD_SEED`, but actual protected PowerShell branch uses `($env:WBD_PLAN028_WIN_REAL_COLD_SEED -eq '1' -and ...)` inside the existing `if`. Three H1565 and one H1566 genuine Linux OS sender source checks were PASS; only this assertion was FAIL. Do not count this as product failure. Changed one test literal and added that test path to the full Windows workflow's source change list. The actual H1566 condition remains a source-locked, genuine Linux native UDP socket sending after original credential TLS and never synthetic protocol READY; native trial **NOT_RUN** until next Action. Previous actual [H1565 Action42957807750](https://github.com/lly8666/wbd-next/actions/runs/42957807750) Windows alone 200ms/loss0 RXDelivered0 FAIL remains, original Windows+Linux4 full 600s and loss30 still NOT_RUN.

```feature-impact
{"kind":"none","ids":[],"reason":"Fix CI-only assertion against the existing PowerShell protection branch and watched paths. Product Go/TLS/Rust/NPF/OS untouched; no prior qualification widened."}
```

Evidence [H1567](../evidence/M0/PLAN028-H1567-WINDOWS-SERVER-OS-UDP-PREFLIGHT-20261111.json), PLAN028 IN_PROGRESS.
