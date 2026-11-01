# PLAN027 H817 | Recover prebuild fixture validation without dispatch duplication

- Run [41342667546](https://github.com/lly8666/wbd-next/actions/runs/41342667546), SOURCE `df2f8cfe4510d0ec2e553f4c77a259efddb771ab`, completed FAIL at its **prebuild** `tests.test_m0_plan027_linux_repair_pair` (test one PASS, test config FAIL); build/manifest/native OFF/ON/Stop **NOT_RUN**, second job skipped.
- Exact original log: `ValueError: bundle sha256 must be exact full hex` at `configuration -> validate(config)`. In existing `m0_linux_dual_outer_repair.prepare` the strict validator receives ephemeral `run_id/artifact_id/attempt/sha256` placeholders, then replaces them with local SOURCE-checked manifest info before product execution. New fixture had inadvertently skipped that prevalidation stage.
- Correct that contract in one helper, preserving explicit product+bundle OFF/ON readback, scenario, binary hashes, cost accounting, cleanup and one-job-one-pair. Workflow-file touch triggers **one** replacement R Action on push with marker; no extra Game/FEC scenario, no product-code changes. New SOURCE native results not claimed until separately observed. H816 failure remains FAIL_FIXTURE and cannot be promoted into a product FAIL.
- Independently recovered prior no-scene Action `41341558605`: completed GitHub success; it is push assembly, not PLAN027 product/CPU PASS.

```feature-impact
{"kind":"none","ids":[],"reason":"Only validation-only Linux measurement fixture correction and exact pending R workflow retrigger; no native code, behavior or user defaults changed."}
```
