# PLAN027 H627 — restore native GitHub trigger before H626 network verification

H626 committed new product authenticated HealthDead rc6/Windows cold original TLS generation supervisor, but the newly inserted Windows Go classification test command in `m0-wl-public-normal-full.yml` was malformed: string replacement interpreted the literal `$'` regex anchor and duplicated the suffix into YAML (207KB vs valid 82KB). Consequently original native push Action [41199036955](https://github.com/lly8666/wbd-next/actions/runs/41199036955) rejected as a workflow configuration without a runnable job; H626 dispatcher [41199037747](https://github.com/lly8666/wbd-next/actions/runs/41199037747) failed at `gh workflow run` with HTTP422 `Workflow does not have 'workflow_dispatch' trigger`. No product compile/native test was performed. Not a product BUG/PASS, retain original real H625 dead90 counterexamples.

H627 restores the whole last valid native workflow from source `593da5494f8afbf2b75de6801e41d50f8d669723`, adds only the exact new source classification test without regex replacement corruption, retains native `workflow_dispatch` and all preexisting steps. Change H626 orchestration workflow path header to re-arm a single new frozen SOURCE build and independent Normal106/Fixed106 genuine tests; add cheap `tools/check_workflows.py` before dispatch. H626 product Rust/Go/assembly hashes untouched; original binary SOURCE now new commit. No blind GameFEC/C reruns. Any newly running Action is evidence ONLY after true native duplex and Stop.

```feature-impact
{"kind":"none","ids":[],"reason":"Repaired malformed GitHub Actions YAML and trigger only; no product wire/lifecycle change beyond still-unverified H626."}
```
