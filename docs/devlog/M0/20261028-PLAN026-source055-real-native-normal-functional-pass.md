# M0 PLAN026 S2｜Normal/off 原生 Rust worker 双端功能实证登记（2026-10-28）

源锁：**Windows/Rust候选 SOURCE `055026fda1cf6ef31e1a8d81b7e04badeb617c34`**、原Go固定 `a7a82db31fe736ffedee330795a3234d358f1984`，Actions <https://github.com/lly8666/wbd-next/actions/runs/40646957672> 的 `native-public-two-os` job 最终 **success**；真实签名Npcap/Wintun安装、WSL2 Linux raw/TUN、Normal双向kernel UDP/TCP及两端Stop均由工作流 PASS 标记报告。其它6模式也在同job成功，但**旧Go业务包泵**仍负责Fixed/Auto/Game，不能冒称Rust模式已经迁移。

精确收据 [PLAN026-S2-source055-Windows-Rust-Normal-real-native-functional-20261028.json](../../evidence/M0/PLAN026-S2-source055-Windows-Rust-Normal-real-native-functional-20261028.json)；两张功能卡只对该SRC补 `FUNCTIONAL_PASS`，明确后来 `f93f7fe7` 批量锁优化、`e5752611` NPF已发送ACK快照和 N0触发源码 `a1238c4d` 仍需本身的精确SOURCE测试，不允许继承此正例。

用户要求先Normal/off真跑通并测资源。完整签名两端功能现在有一源锁正例；真正N0 10Mbps/300ms/240s 单场景已由 `a1238c4d` commit message `[plan025-n0-240s]` 触发 Workflow `m0-wl-public-normal-full.yml`，运行是否/何时 PASS 需看 Action 40648269441 的**终态**；同一VM A/B CPU-seconds/GB、Go steady CPU、Rust idle wake、RSS、P99还没有新源收据。旧PLAN025 `produced=0 ready=4` 原首错独立保留，不能因Go旧接口不再调用就删掉回归。

```feature-impact
{"kind":"updated","ids":["normal-off","windows-native-transport"],"reason":"将PLAN026 SOURCE055真实签名Wintun/Npcap+Linux双向UDP/TCP/owned Stop成功精确登记；未升级最新SOURCE/N0/CPU/Fixed/Game资格。"}
```
