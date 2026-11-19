# H2180｜Linux双原生ISA真10/10源锁证据及预算防回归

H2177 [Action44258876671](https://github.com/lly8666/wbd-next/actions/runs/44258876671) 的真实原生Ubuntu x86_64与aarch64两个独立托管CPU环境，分别原Go TLS＋Rust M4 Linux客户端和Linux服务端各五短模式，真内核TCP/UDP双向业务、TUN/IPv6自有设备、1460MTU/FEC6 parity/双Stop均签名PASS_SCOPED。唯一**网络SOURCE `3cc095e38d98fd1a9b2a8f00835b113bc434c9e1`**，十场不因后续纯文档提交变成新网络源。

H2177归档触发主治理超32KiB，H2178缩减M0热读；H2179补证据顶层`source_sha`与同值`same_exact_source_sha`，[治理及功能卡 Action44261621654](https://github.com/lly8666/wbd-next/actions/runs/44261621654) **SUCCESS**。旧H2177/H2178红灯原样保留；H2179没有重触发全量maintenance回归。

为保有效交付，本提交只新增`tests/test_m0_plan029_h2180_linux_source_and_hot_budget.py`：严格10/10两个原ISA及每场双向真业务/原二进制源锁、游标唯一`source_sha`一致、各角色热读取仍按**原32,768B上限**计算。这个tests路径使既有governance-maintenance自动运行**一次**全量测试；不修改仓库治理配额、不绕过诊断、不碰产品Go/Rust/winGUI/FEC/网络。若真实维护回归FAIL要如实报告而非宣称成功。

当前完整PLAN029/029B技术出口仍OPEN；跨ISA互连、实际ARM板、Win专属分流及性能测试依然未跑，PLAN030 NOT_STARTED。

```feature-impact
{"kind":"none","ids":[],"reason":"Add cheap permanent static guard for exact H2177 dual native Linux 10/10 evidence, live cursor source schema and existing governance hot-read byte budget; no product behavior/feature change."}
```
