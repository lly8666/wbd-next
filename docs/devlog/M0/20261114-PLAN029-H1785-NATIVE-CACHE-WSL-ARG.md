# PLAN029 H1785 | signed real CN cache bridge first failure

Collected [H1783 43547631254](https://github.com/lly8666/wbd-next/actions/runs/43547631254) and [H1784 43548325696](https://github.com/lly8666/wbd-next/actions/runs/43548325696), both **FAILED** at the same actual Windows/WSL test fixture boundary. Real original Windows Wintun source-bound two DNS UDP clients obtained one durable FakeIP `198.18.0.1`, real Linux physical resolver saw target_dns_count=1, and the original Windows Direct UDP app received its physical echo. But Linux reported `cache_mode=false`: WSL did not inherit the Windows-only environment; the guest never ran its required post-Direct 2.5s duplicate-query watch. Do **not** credit full cache isolation, later Tunnel/Direct8 or owned Stop as PASS on either run. Owned fail-path WAL/guest drained in logs; expected normal-Stop result NOT_RUN. Evidence `docs/evidence/M0/PLAN029-H1785-H1783-NATIVE-WSL-CACHE-MODE-BRIDGE-20261114.json`.

H1785 exactly forwards `0/1` through `wsl.exe -- python3 ...` and validates it in guest, retaining true 2.5s watch, target DNS count 1, physical original source and normal owner Stop. Tests prevent reinstating implicit env. One signed combined Action auto-triggered by commit, not manually repeated. Independent D1 TCP53, D3 quota, lifecycle GUI/1460 and P1/P2 remain open.

```feature-impact
{"kind":"none","ids":[],"reason":"Signed test-only WSL argv correction; production behavior and config unchanged."}
```
