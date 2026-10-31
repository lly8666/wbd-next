# PLAN027 H564 — execute already verified SOURCE525 zero gate once, no duplicate product run

Original [41166008870](https://github.com/lly8666/wbd-next/actions/runs/41166008870) source525 signed Windows ↔ Linux 0% genuine 60s first100% each, F86398905/85005869, R0 both, owned Stop PASS; exact hashes/evidence in H562. The previously registered H557 `workflow_run` fanout did not appear in the workflow list after 41166008870 success; no children were dispatched. No claim about why GitHub did not emit/route that event. Replace H557 workflow trigger with **a single tagged main push** [plan027-h564-source525-once], reusing the unchanged strict gate on run41166008870 source525 and actual report, original Win/Linux build artifacts and zero real first/Stop/R. This same push is its only invocation; remove the old workflow_run trigger to prevent double dispatch. If the gate passes, enqueue 12 independent per-scenario Actions (Normal p1/5/15/30, Fixed30, Auto240, Normal C50, Game2/4 off/FEC) and one independent same-VM sequential A5; all reuse source525 binaries, no new build. Later capacity C100/300s and full B lifecycle still open. No source/config behavior changes.

```feature-impact
{"kind":"none","ids":[],"reason":"Replace an unobserved one-shot workflow_run with one tagged push, preserving exact original report/source gate and avoiding duplicate source/test builds."}
```
