# PLAN027 H587 — retire unsafe cross-scenario Action ID discovery

The previous H585 source-reuse workflow Action41178208351 ran Fixed50 Action41178599622 and Game4 highest FEC 10Mbps Action41178602168. It failed after matching the Fixed50 Action to its Game10 verification, a **harness identity bug**, not a product Game failure. Re-running Game10 would waste a full true Windows/WSL2 origin build. This one-shot replacement binds the prior actual Game10 ID at workflow creation, requires exact SOURCE frozen build41177831521 and unique scenario hash with true dual native UDP/TCP and owned Stop. Only then dispatch one Game4 maximum FEC 20Mbps/250ms/0%; only when that exact new ID and report pass dispatch Game4 maximum FEC 20Mbps/250ms/30%. A competitor dispatch in the same interval fails closed; never picks the first unrelated Action. Signed original source from cb475 reused; no new product compile, no repeat Game10, no Fixed50 rerun. `Game10` remains IN_PROGRESS as of gate creation. 1% outer repair objective was already genuinely met at Windows0.4576%, Linux0.4815% and does not need further tuning. Other PLAN027 Health/A5/C remain OPEN.

```feature-impact
{"kind":"none","ids":[],"reason":"Workflow-only exact source/run/scenario identity repair; no runtime product, security or contract changes."}
```
