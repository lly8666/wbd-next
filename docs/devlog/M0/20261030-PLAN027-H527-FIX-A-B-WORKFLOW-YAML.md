# PLAN027 H527 — recover H526 invalid YAML before dispatch

New H526 workflow [41064754971](https://github.com/lly8666/wbd-next/actions/runs/41064754971) failed parsing because template-generated Python scene rows and bash heredoc lines were dedented outside `run: |`. Main governance [41064757207](https://github.com/lly8666/wbd-next/actions/runs/41064757207) also failed syntax, not a source/product regression. H526 dispatched **zero** of its seven measurement Actions. Repair YAML scalar indentation only and trigger once with `[plan027-h527-a-b-once]`, retaining exact SOURCE7a original build 41060763175, no recompile, and seven scenarios same as H526. H525 loss1/5/10/30 children remain in progress and are not repeated.

```feature-impact
{"kind":"none","ids":[],"reason":"Correct source-locked Actions YAML/heredoc syntax and cursor only, source7a runtime unaffected."}
```
