# PLAN027A H950｜复用H948签名原生程序，六场景独立并行

已收齐 H948 Windows/Linux 原生工作流 [41452689481](https://github.com/lly8666/wbd-next/actions/runs/41452689481) 成功（仅 legacy1400 七模式）、Windows WAL [41452689382](https://github.com/lly8666/wbd-next/actions/runs/41452689382) 成功，H949 治理 [41452968540](https://github.com/lly8666/wbd-next/actions/runs/41452968540) 成功。Windows exe/Rust DLL 与 Linux Go/Rust 原生程序源为 `adc63a8b8af209dbe589d072403b7bceae8e038b`，分别存于同 run 的签名artifact。

此次新增**只有独立Action派发器、四份测试场景和证据/cursor**，不改产品/ABI/汇编manifest。派发器先校验原始run为success、两套产物存在、商品源码目录与锁定文件没有差异、MTU parser unit PASS、每个场景合法；每个新原生测试均传 `perf_reuse_run_id=41452689481` 和 `perf_binary_source_sha=adc63a8b8af209dbe589d072403b7bceae8e038b`，真实工作流还执行 SHA256 校验。二套七模式默认1460/显式1500，Normal3Mbps、Game4FEC3Mbps loss0/loss30 与 Auto10Mbps 250ms 5→30→5 四个测量场景，每Action仅测一场景；全部仍需完整有签名的Npcap/Wintun和实际WSL2内核，不是缓存VM。

**所有新场景初始 NOT_RUN，** 不将派发视作PASS。真实 Windows numeric pre-READY、3Mbps CPU/RSS/p99、DF0/DF1、Game4 staged与新源ARM64仍按各自真实结果决定资格。Game4FEC旧10Mbps p99~1.3s仍是疑点，先看3Mbps容量可用性；不做新旧不同VM的CPU因果比较。未完成PLAN027A退出条件前不宣称PLAN028交付。

```feature-impact
{"kind":"none","ids":[],"reason":"H950 only adds prebuilt qualification workflow, four immutable test scenes and task evidence; no product code or feature card results until real native Actions."}
```
