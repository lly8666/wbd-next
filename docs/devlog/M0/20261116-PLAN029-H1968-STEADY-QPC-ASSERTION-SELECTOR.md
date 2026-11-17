# PLAN029 H1968｜修正正例断言文字，保持严格字节/时间源验证

H1967 原 [廉价 Action43804163808](https://github.com/lly8666/wbd-next/actions/runs/43804163808) 进到`tests.test_m0_plan029_h1966_steady_qpc`：**7例中6例成功**，唯一正例已运行原合成2048条1KiB全部QPC分段/字节对齐、产出完整字典，随后因测试期望文字 `not TCP packet count equality`、分析器实际文字 `no TCP packet count equality` 而断言FAIL。H1968仅修改正例assert文案，**不修改Rust诊断、源锁、QPC算法、原应用/WSL2实测条件**。

H1967 治理/Feature PASS；Windows/Linux Rust pure component、独立原始DLL build按真实CI完整收集。H1968无原生P2触发词，不能把6条纯合成/1条断言修复称作任何真实 Windows 2048连接延迟。用户要求普通小包、已有连接的系统与Rust开销，不追极端同-IP CDN。正式新原生场景仍需在7/7/Win Rust纯编译绿后单独签名，普通产品提前物理建连仍OFF。

```feature-impact
{"kind":"none","ids":[],"reason":"Only align a positive synthetic parser assertion with the unchanged fail-closed analyzer wording; no product code, source-locked experimental QPC conditions or feature qualification changed."}
```
