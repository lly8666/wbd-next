# PLAN029 H1947｜H1946 一次真实 P1 四臂结果，CPU 保护继续 OPEN

- 原生同 VM [Action 43777305453](https://github.com/lly8666/wbd-next/actions/runs/43777305453)，冻结 SOURCE `bc6afde542c4daecee393745a982a590c9dba27f`；Windows Go + Rust DLL、Linux peer 均同 Hash，全 runner 成功、signed Wintun/Npcap/WSL2 真实执行与 finally owned Stop PASS。
- 原始 `plan029-p1-ab/result.json` A1_all→B1_cn→B2_cn→A2_all **四臂 PASS_SCOPED**：每臂实际交付 0.6984GiB，Windows 49.9999 Mbps、Linux 49.9866/49.9874 Mbps，双端 UDP p99 有实测，双端 Stop PASS_BOTH_OWNED。
- H1937 首故障已实修：CN 冷表原为 `cn_rows=8`；新 B1/B2 都是 `cn_rows=4104 domain_bytes=180224`。A1/A2 All `cn_rows=0`，三种事实不能混。
- Windows **Go+Rust 同一进程** CPU s/实交付 GiB：A1 20.49327、B1 23.58076、B2 21.29868、A2 19.59837；All 平均 **20.04582**，CN 平均 **22.43972**，相对 +**11.942%**。A drift 4.464%、B repeat spread **10.17%**、交付 spread 0%，解释字段原文 `POTENTIAL_REGRESSION_NEEDS_REPLICATION`：**P1 性能保护 OPEN**，不误写统计显著性或 Rust 单独 CPU 归因。Windows UDP p99 [63,78,63,63]ms，不能跨臂直接相减。RSS 峰值约 39–45MiB。
- 纯 Tunnel A/B 所暴露的额外工作：CN 业务快路仍进入 `PacketIngress::on_ipv4_with_announced_fake` 的 FlowPin 查找；先对冻结源码做定向成本/公平性复查，再与其他必要产品变更合批验证，**不在无新实现时重 dispatch 同 seed P1**。没有把局部场景成功当整包 029 产品交付。H1945 Direct 首回包 pre-write 尾延迟仍 OPEN；D1–D5 / P2、Game4、GUI真出口、资源限额等退出条件仍按契约保留未完成标记。
- 证据：`docs/evidence/M0/PLAN029-H1947-H1946-REAL-P1-SAME-RUST-CN4104-CPU-ABBA-20261116.json`，历史 H1937 FAIL 与 H1945 局部 QPC PASS 不覆盖。

```feature-impact
{"kind":"updated","reason":"H1946 original signed P1 four-arm CN rows restored to 4104 with all application/Stop PASS; observed +11.942% CPU vs 10.17% B repeat drift remains P1 performance OPEN","ids":["dns-split-ipv6"]}
```
