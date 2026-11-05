# PLAN028 H1209 — one pinned Windows assembly blob SHA

H1208 changed the original Windows CLI source to carry authenticated Fixed6 profile+1 (the pre-existing V4 protected extension byte22) while retaining Auto0. This source code is intentionally pinned by `manifest-plan020-m0.json`, which still expected old cli blob `f41f8248...`; [Windows source Action41938690410](https://github.com/lly8666/wbd-next/actions/runs/41938690410) cheap `prepare_windows_wiring.py --check-only` failed before actual build; parallel x86 [Action41938690662](https://github.com/lly8666/wbd-next/actions/runs/41938690662) assembler failed before real network. Update exactly that single create operation `result_blob` to new real CLI SHA. Do not count either as product regression or native PASS. No new FEC, routing, wire or recovery module. Existing H998 live hot MTU and old ARM Game4 FAIL, remote ICMP, Android and CPU causal unqualified.

```feature-impact
{"kind":"none","ids":[],"reason":"Synchronize exact source-locked assembly manifest CLI blob SHA with H1208 deliberate Fixed6 authenticated profile product source change; no further runtime edit."}
```
