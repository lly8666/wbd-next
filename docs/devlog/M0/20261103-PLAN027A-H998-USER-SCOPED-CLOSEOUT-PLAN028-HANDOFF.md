# H998｜PLAN027A 用户明确限定范围结案，交接 PLAN028（未开工）

用户在2026-11-03指示“直接收口027A，完工了。一会儿我找全新agent开工028”。该签收是**项目范围裁决**：PLAN027A 本阶段停止继续施工、已验源锁内容存档、下一任务 028 准备交接。**不得把用户批准的范围收口伪造成所有原技术退出条件达到 PASS。**旧 FAIL/NOT_MEASURED 不变；本次仅改治理、文档、功能卡，不修改 Go/Rust 产品、不再派发 Actions。

唯一归档：`docs/evidence/M0/PLAN027A-H998-USER-ACCEPTED-SCOPED-CLOSEOUT-20261103.json`。

已实测：源码 `1e8325f16e2975a9da3497ab97ac570771a97238` Windows 原签名 Npcap/Wintun ↔ Linux WSL2 原 Go TLS/Rust 11/11 个原生场景逐项 PASS；DF0 两端真正 1728/4096/65507B UDP 原报文完整组合并逐字节相等，DF1 本机内核 EMSGSIZE；双方 65536B TCP 写入/回显；真实 SYN MSS/内层 OS MTU/owned Stop；正常 1280 真实双方 MSS1240、内层1209。Game4FEC1500 的理论/源码型预算 1398；默认用户外层完整IPv4 1460、不含L2，1500 只允许显式。

ARM64 原 Go/Rust SOURCE `26ca847019d8ffddaa163d40f77c61b6cc2401f9` 构建 PASS，Normal1460、两端不对称1460/1280 原生 PASS。H997 Game4FEC1460与1500 Action **FAIL**，然而从真实系统日志可以独立看见双端 TLS/业务交付、FEC fixed6 parity offered/copied 各128，auth rejected=0，duplicate/replay rejected=44，双端 owned Stop；不能改写整 Action 成功。H995 **真实在线物理出口1500→1280** 后小报文3/3未获回复，仍属真实 FAIL；没有被冷启动1280新会话的 PASS 覆盖。用户态发送与对端观察 ICMP Type3/Code4 **NOT_MEASURED**，不可由本地 DF1 EMSGSIZE 外推。

H996 Normal同 Windows/WSL2 主机按原始相同二进制、相同场景 repair OFF→ON 60s：两腿原生 PASS/Stop；0%损伤双方 first delivery均1.0；Windows进程累计 CPU 2.5938s→1.6406s、峰值RSS 42070016→40292352B。包含冷启动/Stop，**不可声称是MTU改造带来的因果CPU增益**。单独 Game4FEC 3Mbps/25ms/0%原生 Action PASS/Stop，Windows进程CPU12.9531s、RSS70098944B，不与Normal跨VM直接做算法收益结论。H987 分阶段 5→30→5 原生弱网 PASS，但不考核用户已取消的分包丢失率门槛。原失败号仍按证据保留。

**收口遗留/交接：**028§4.1–4.2 的真实路径通知、重新认证/新generation、路由出口和新的每lane预算/OS读回必须处理上述在线路径收窄缺口；这是028的**待实现依赖**，不是027A已交付能力。远端ICMP3/4、全源等价ARM64 Game4FEC绿色Action、物理WAN和旧/新产品同VM因果性能结论未被签作合格。这些被用户明确接受为本次**范围外/待后续**，不是全产品发布资格。无新产品SOURCE时不要重新刷11个原生模式或旧两项ARM64失败Action。

入口 `docs/prompts/M0-PLAN028.md`。更新 `START_HERE.md`、`AGENTS.md`、`.governance/registry.json` 与 M0 cursor，使028处于**PLANNED / READY_FOR_NEW_AGENT**，**没有替用户启动028开发或测试**。新 agent 按最新main恢复、首先读027A本收口证据，再开始028会话/配置/网络接管，实现时禁止复制 MTU 预算公式或把此处已发现的缩窄 FAIL 描述成通过。

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"H998 用户明确批准PLAN027A限定范围交付，精确归档11个双原生PASS与H996保护性能，并保留ARM64 GameFEC动作FAIL、真实动态物理路径缩窄FAIL、远端ICMP未测；交接PLAN028但未开工。"}
```
