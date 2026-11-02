# PLAN027A H953｜Game补码后仅一次重编，十个原生场景复用新产物

H948原生程序 `adc63a8b...` 在H950/H951按单模式重用时，Normal 3Mbps、Auto 5→30→5、显式1500 Normal/Fixed/Auto 有 Windows 内层数值回执且实际原生 PASS；Game2/4 off/FEC在默认1460及显式1500共同暴露 Game 冷路径数值回执遗漏，失败记录一概保留。

H952 `54160ac88b9b41d10f4c3f885879dd68646466a0` 只补原始 Go Windows Game `Apply→LiveReceipt→RuntimeMTU CAS→READY` 以及所需单项manifest。新源已有廉价assembly及 Windows Go、Windows Rust、Linux Rust preflight PASS，当前一次完整 Linux 产品构建/实际原生仍执行中。H953只加一份监听前序H952成功的one-shot派发工作流，**不修改产品，也不启动第二次编译**：先要求H952工作流SUCCESS与两套产物真实存在，检查 product/ABI/Cargo 不变；再派发 Game2/Game4 off/FEC x1460/1500 共8个边界和 Game4FEC3Mbps loss0/loss30两个资源场景，每Action一场景，全部通过 `perf_reuse_run_id=41456643128`、`perf_binary_source_sha=54160ac88b9b41d10f4c3f885879dd68646466a0` 复用 Windows exe/DLL及Linux二进制，并在Windows runner上二次SHA256验证。

这批是补测，不做当前Game性能PASS或整个MTU计划完成声明；真DF/ICMP、Game staged与新源ARM64仍NOT_RUN，028未开始。若前序编译/native失败则**派发直接阻断**，不冒充已完成。

```feature-impact
{"kind":"none","ids":[],"reason":"H953 adds only an exact-previous-source Game prebuilt one-shot qualification workflow/evidence, no product changes or feature promotion."}
```
