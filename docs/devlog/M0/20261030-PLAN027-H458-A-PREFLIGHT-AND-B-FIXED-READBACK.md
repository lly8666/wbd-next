# PLAN027 H458｜A真场景的精确CI阻塞与真实Fixed本地Applied

H457 SOURCEbaa7 A push dispatcher40995309062 TRUE success，三条独立真实Windows↔Linux A2 normal 0%、normal30%、A3 Fixed30% Actions40995322925/25145/27742在启动前均FAIL。精确原因是 `tests.test_delivery_ci.test_preflight_has_no_native_runtime_or_driver_effects` 仍要求旧 `if: inputs.perf_reuse_run_id == '' && !(...)`，而H456有意在coding-only快照跳过重复编译，生产workflow为 `&& !contains('[plan026-coding]') && !(...)`。单测调整至实际有界预检，无任何网络检查删除；没有A业务通过。

H455 B Fixed 40994441580 evidence zip artifact12950647138中 report 双端真实 kernel UDP25/25、双端TCP echo、owned Stop均PASS，Linux原Rust FixedStream `V4_PUBLIC_FEC2_READBACK role=server mode=fixed requested=1 applied=1 profile=6 pending=false` 真读回。旧脚本仍要求 Windows M2 Mature 标记，虚假FAIL；改只确认真实Linux installed profile6，Windows本地运行读回明确NOT_INSTRUMENTED，质量NOT_MEASURED。冻结原产品二进制在同一H458动作里单独再跑Fixed一次（不混A场景）。

H455 Auto `40994443303` 真失败原封记录：Windows outbound385 received0，Linux outbound100 received27，Linux TX 41.8 CPU秒/41秒墙钟，FEC parity planned7 sent0；不能称UNKNOWN而掩盖业务缺口，后续基于真实日志回读worker。

H458无业务代码变更、不重编译，只修受影响测试/夹具并受控重派三条先前未进入物理的A和一条实机B Fixed。A4/A5/B生命周期/C 5分钟未完，继续。

```feature-impact
{"kind":"none","ids":[],"reason":"Update exact preflight test guard and source-verified Linux Fixed installed readback; no live product behavior changed; retain Auto regression."}
```
