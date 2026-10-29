# PLAN027 H405｜S404 strict Quality START/CLOSE 原生回归

2026-10-30。精确 SOURCE `9a2af725ab0dd498dd7960e4e91d1ca23a0683cb` [native40953849123](https://github.com/lly8666/wbd-next/actions/runs/40953849123) SUCCESS：engine 135 passed /0 failed /1 existing optional ignored，新反例 `r1_plan027_authenticated_quality_start_close_canonical_and_fail_closed` PASS；receipt11、kernel6、fec3、normal3 均成功。构建 artifact12932083994，manifest `b356905e9d2c43d74902b0c565c8d36e6323037fad4f90e2a7719960e15c1c04`，五组二进制/log hash、job ID 见 [H405 evidence](../../evidence/M0/PLAN027-H405-QUALITY-BOUNDARY-SOURCE-NATIVE-RESULTS-20261030.json)。governance40953849032、static40953849199、g2 40953849056、crossABI40953849131 也成功。Windows ABI、Linux Auto/Health、Windows owner专项仍在途，不能提前判定。

**限定**：这是编码/解析的源码级正反例，不是生产 Auto/Quality 接线；线上逐 record M2 仍未退役，A/B/C/长测仍未跑。旧源码 preflight 成功单独在 H404 evidence，不合并为新 SOURCE 业务证明。下一步先回收在途，然后继续双端接线与 PLAN027 五项。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Attach exact S404 native Quality START/CLOSE regression and hashes, while retaining live product and PLAN027 A/B/C NOT_RUN."}
```
