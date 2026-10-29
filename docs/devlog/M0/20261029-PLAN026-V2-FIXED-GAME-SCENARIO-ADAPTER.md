# M0｜PLAN026 WL-V2 Fixed/Game source-locked场景适配（未测）

2026-10-29。此批只改 Windows/Linux V2 夹具的**模式选择和测试口径**，不更换生成器、tc、实际 Go/Rust TLS/Npcap/Wintun/TUN/Stop 实现，也不宣布任何新产品模式 PASS。

- 保持旧 V2 JSON 无 public_mode 时 Normal 语义和 SHA 完全不变。新增显式 `public_mode` allowlist：`normal,fixed,game2,game4,game2-fec,game4-fec,auto`，不允许 Game Auto。
- 工作流和真实`m0_wl_public_normal_e2e.py` 对照选定 `public_mode` 与提交的 scenario 身份；一模式一场景一 job，旧 Go/Rust 配对 A/B 与重用旧编译产物仍 Normal-only，拒绝在模式不同时混用。
- 旧 `scenarios/wl-normal-*.json` 的无损首到≥99.9% 不放宽；故意损伤的独立 Fixed/Game 只要求同源已测、真实 kernel 收发、双端 first>0、真实OS owned Stop，原始 FEC/Game/真实 tc/drop/outer M2 指标完整保留在各 mode report，不自造“30%线损0残余”的要求。宿主生成容量不足仍 CAPACITY_LIMITED。
- 加 3 个可复现 W168 范围场景 `fixed6 loss5`、`game2-fec fixed6 loss15`、`game4-fec fixed6 loss30`，真实双向混合包 10Mbps、75ms、20s，原始 source/stop/CPU 与原W168不是同一资格。单元测试验证身份和Game Auto拒绝。Auto网络测试必须排在Fixed/Game及双端Keepalive实现后。

这批只提供真实测试**入口**；用户要求的两端Keepalive/服务器dead/FIN休眠与Windows Game Rust-only尚未完成，所有新增场景**NOT_RUN**，不触发对应 workflow_dispatch。

```feature-impact
{"kind":"none","ids":[],"reason":"V2测试工具/场景及说明扩展，不改变产品协议、CLI默认或功能资格；新增网络场景保持NOT_RUN。"}
```
