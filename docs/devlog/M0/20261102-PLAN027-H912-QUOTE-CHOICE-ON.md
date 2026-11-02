# PLAN027 H912｜GH workflow_dispatch ON 值 YAML 解释失败，未进入原生测量

- H911 [Action41418761998](https://github.com/lly8666/wbd-next/actions/runs/41418761998) cheap dispatcher **FAIL**; first error `HTTP 422 Provided value 'on' for input 'outer_repair' not in list of allowed values`. No `PLAN027_ON_BATCH1_QUEUED` and no genuine ON child Action, all compiled jobs SKIPPED because parent [plan026-coding]. **This is workflow choice schema failure, not Windows/Linux product FAIL.**
- Original workflow `workflow_dispatch.inputs.outer_repair.options: [on, off]` and `default: on` were not quoted. H912 sets choice to string literals `['on','off']` and default `'on'`; no changes to public product parameter, Rust option, CLI UI or measurement fixture. Replay exactly once via new SOURCE marker `[plan027-on-batch1]`; GitHub valid choice must accept string on.
- Batch scenarios remain H911 three source-committed fixtures (Game4-FEC6 ON 250ms30%, Normal ON 100Mbps 25ms0%, Fixed ON 250ms30%), each native Action one scene; reuse exactly H908 SIGNED product run41415722303 SOURCE6693910 and verify manifest, no rebuild per mode.
- H908 real 105s post-recovery PASS is stored independently; H911 dispatch FAIL remains history, not overwritten. Results pending for H912 children. Physical NOT_RUN.

```feature-impact
{"kind":"none","ids":[],"reason":"Quote existing workflow_dispatch choice input values so GitHub receives literal ON/OFF strings; no product/default/mode change."}
```
