# B79a｜B77–B79 构建收口与 Android FakeIP 范围决定

- 基线 `ddf7c8c992737180bacfbfe5758daf7846434152`，只写实验分支 / Draft PR #36。main 核对为 `c0166202af7fb3f70baf15a749df664c04502305`，未写。
- 用户要求继续大类功能并行研读、合批接线，不展开极端工况或额外防御开发。高级 CN FakeIP = **OUT_OF_SCOPE**，Android 明确不实现；普通 CN8503 DNS 与真实 CN IPv4 内核 FIB 保留。同步功能卡、施工台账、唯一方案、接续提示词及 App README。
- 基线 [产品 CI](https://github.com/lly8666/wbd-next/actions/runs/45337793395) 5 SUCCESS / 2 FAIL / 8 SKIPPED。ARM64 Bionic `v4_embedded_go.rs:3906` E0609，使用已有 `original_identity.server` 的真实方向字段，不新增字段或检查；CN 快照下载 404，改用 APNIC 官方 2026 日期归档 `delegated-apnic-20261116.gz` 解压同一日期文本，来源摘要同步；[官方归档](https://ftp.apnic.net/stats/apnic/2026/) 已列出该文件。
- [维护 CI](https://github.com/lly8666/wbd-next/actions/runs/45337793250) 826 测试中 1 FAIL，更新原 Game padding 平台 cfg 断言为包含 Android；[功能目录 CI](https://github.com/lly8666/wbd-next/actions/runs/45337793208) FAIL 因缺标准 feature-impact 块，现补本记录。不删除原测试、不另建工作流。
- A48 历史 ARM64 真机原 TLS/认证/租约/M4 双向、UID、Stop 已观察，用户报告数据通了；本 SOURCE 构建与设备/性能仍待验证。下一大类：复用 main 已收口的原 Normal-v3 外层机会式重传接线（原 Rust M4/ACK/SACK/实际复制），不另造协议或把未接线开关暴露给用户。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B77–B79 Bionic padding direction, APNIC archived CN IPv4 source and platform test fix; Android advanced CN FakeIP explicitly OUT_OF_SCOPE, ordinary DNS and kernel CIDR retained."}
```
