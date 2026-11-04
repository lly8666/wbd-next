# PLAN028 H1206 — x86 Normal strongest high30 generated measurement marker fix

[H1204 Action41933848259](https://github.com/lly8666/wbd-next/actions/runs/41933848259) SOURCE600864 native x86 compile succeeded; generator failed **before** executing netns/TLS/UDP because original x86 measurement text was converted `NETEM5→NETEM30`, while subsequent exact replacement still searched for `M0_PLAN028_H1184_X86_NETEM5...`, leaving required new receipt absent. Fix only that post-transformation marker to `...NETEM30...` and require exactly one final H1204 marker. Keep genuine second physical source4 under `tc netem loss 30% delay 250ms`, up to120s bounded original TLS retry, Game4 original sibling320 native UDP, Normal fixed6 200 no-app-retry kernel UDP p99 and qdisc cleanup. No Go/Rust product code changes; prior Action remains PRE_NATIVE_TEST_GENERATOR_FAIL, not network FAIL. Distinct H1205 ARM high30 true kernel original PASS retained.

```feature-impact
{"kind":"none","ids":[],"reason":"Fix source-locked test-only post-rename H1184 NETEM marker so original x86 Normal30 native test can execute; no product change."}
```
