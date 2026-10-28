# 历史检索地图：M0 主线收尾

2026-10-28 用户要求 M0 后续在 main 开发；FEC 历史工位任务完成。本页是定位地图，不发布 next_action。

| 问题 | 先查哪里 |
|---|---|
| 产品主旨、不能回退的约束 | PROJECT_CHARTER.md；docs/architecture/README.md |
| 现在能用哪些模式/参数/平台 | docs/features/README.md、entries 对应卡，缺项保留而非凭旧日志补 PASS |
| Rust 模块/ABI/所有权 | docs/architecture/modules/README.md，按异常挑对应一两个模块 |
| 外层重传、MTU、容量数学 | docs/decisions/NETWORK-OPPORTUNISTIC-REPAIR-MTU-20261023.md；docs/testing/NETWORK_CAPACITY_ENVELOPE.md |
| FEC 固定/自动/Game 历史优化 | docs/architecture/FEC_V2_BALANCED.md；docs/devlog/fec-network-work/；docs/evidence/fec-network-work/ |
| Windows 原生/清理/去脚本 | docs/decisions/M0-PLAN020-Windows-full-product-M0-takeover-20261021.md；r0/go_overlay/assembly/manifest-plan020-m0.json；docs/evidence/M0/ |
| W168 集成之前 | docs/history/2026-10-26-W168-WINDOWS-INTEGRATION-INDEX.md |
| Windows S1–S61 修复及 Auto 队列/采样 | docs/devlog/M0/ 中 PLAN025/Sxx 日志；docs/evidence/M0/PLAN025-*。main 已集成的实现不从旧分支反向覆盖 |
| 测试首错、host 能力、包大小/源流量 | docs/testing/NETWORK_TRIAGE.md、NETWORK_HARNESS.md；当前包证据链接 |
| 旧 Go 可借鉴功能 | 固定原项目源码 a7a82db31fe736ffedee330795a3234d358f1984 的相关模块；使用原逻辑前检查新协议/MTU/模式差异 |

## 大致历程
早期 M1–M4 分工形成 Rust 编解码/恢复/运行时/平台模块；随后独立网络/FEC 工位完成 Linux 固定档、Auto、Game 与硬件加速/成本实验；M0 将原 Go 冷层接至 Windows 原生设备和 Rust 引擎并合入 main。当前已进入稳定性与真实性能收口，不是 foundation 初始化，也不是等待 FEC 分支完工。

## 本次热入口归档
旧 AGENTS、START_HERE、M0提示词、handoff、project、registry 与 FEC任务说明原文可在 [归档基线 1bbd2426](https://github.com/lly8666/wbd-next/tree/1bbd2426125bbaeceeb3a16f3a46d5335b198313) 按同路径读取。此次只覆盖入口与任务导航，不移动原始日志/证据；不复制几十页历史进热摘要。

全新 agent 遇到不明行为先按路径检索关键词/源码再读最近相关修复，禁止从历史任务重启完整开发。历史状态/临时授权只解释当时，不覆盖 main registry 和用户新决定。
