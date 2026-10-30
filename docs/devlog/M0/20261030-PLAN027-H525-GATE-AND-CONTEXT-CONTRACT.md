# PLAN027 H525 — exact failed gate recovery, no duplicate tests

H524 one-shot gate [41064116585](https://github.com/lly8666/wbd-next/actions/runs/41064116585) failed **before any 1/5/10/30 dispatch**. Its live source7a H520 original Windows/Linux ZIP/Stop/0% and F/R verification printed `H521_REAL_ZERO_LOSS_SOURCE_AND_STOP_GATE_PASS` with Windows F=86402246, R=0, C=227836. The following scenario assertion indexed `cfg['public_mode']` but the existing canonical Normal `wl-outer-repair-50m-150ms-loss1-60s.json` omits that optional key; isolated `KeyError: 'public_mode'`. Correct only gate reader to `cfg.get('public_mode','normal')` matching other source-locked workflows. H525 is a **single new gate** with message-specific trigger and unchanged frozen source7a H520 artifact, not a second run of the previous 0% native scenario.

H523 governance [41063854364](https://github.com/lly8666/wbd-next/actions/runs/41063854364) failed existing bounded `cursor.context_refs` (extended from 7 to 9; H524 had 11), causing feature governance validate exit2 though feature_catalog structural artifact PASS. Restore exact bounded seven high-value legacy refs (new source H523 evidence is still registered via `evidence_refs`); no rule or product change. All PLAN027 stages remain unfinished.

```feature-impact
{"kind":"none","ids":[],"reason":"Repair failed Actions gate optional Normal scenario key and bounded cursor documentation only; production SOURCE7a unchanged."}
```
