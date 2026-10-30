# PLAN027 H524 — single real SOURCE7a gated follow-up loss tier launch

H520 [41060763175](https://github.com/lly8666/wbd-next/actions/runs/41060763175) completed success, with artifact [12979407518](https://github.com/lly8666/wbd-next/actions/runs/41060763175) proving 60s signed original Windows/Linux true UDP/TCP business and both owned Stop. At H524 recovery the previous H521 `workflow_run` hook had not appeared in repository Actions run listing after the completed source action, so it was **replaced**, not added as a second parallel trigger, with a single explicit push gate `[plan027-h524-loss-launch]`.

The unchanged gate first fetches source7a's real H520 artifacts and enforces original binary source SHA, Windows first F/R and zero-loss threshold, true kernel tc no drop, bilateral first delivery >=99.9%, original product/Stop and 4 legitimate 60s 50Mbps/150ms each-side loss 1/5/10/30 scenarios. Only then it dispatches **one measurement Action per loss scenario**, reuse_run_id=41060763175 and exact binary source SHA `7a5d7e83823e96539d2a904a8193a85ec18df30d`. No recompile, no new SOURCE, no synthetic repair. Do not trigger this gate again for a skipped/queued existing action; collect actual run/artifact before any correction.

A2 10Mbps/250ms both 0/30, Auto sustained A, B full lifecycles/GameFEC, C breadth/long and A5 CPU are **not** closed by a launch; preserve previous scoped PASS/FAIL and capacity decisions.

```feature-impact
{"kind":"none","ids":[],"reason":"Actions source-locked test orchestration and recovery cursor only; no product behavior, configuration or feature catalog change."}
```
