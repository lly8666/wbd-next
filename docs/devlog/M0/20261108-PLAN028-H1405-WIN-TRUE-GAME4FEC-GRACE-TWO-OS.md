# PLAN028 H1405｜Windows Game4+FEC 原始两代认证、真实 server 10–20秒旧代 grace、双向业务/Stop 全 PASS

2026-11-08，新测试-only SOURCE `d30936077ca44f176d62ee84a46ed673b7c9de92` [Action 42485343180](https://github.com/lly8666/wbd-next/actions/runs/42485343180) **6 jobs全部 SUCCESS**。原 `m0-wl-full-public-normal-direct` ZIP 35文件 CRC PASS SHA256 `df70657c71aabacb5aeec73707cd7dd363f70dfa4ff2ac20b24ae80f95b17b84`。一台原 Windows2025 已签名 Npcap/Wintun、一台原 WSL2 Linux server，Go TLS port443 4 lanes、Rust Game4 Fixed6+FEC，有两代原始完整 native protected server Ready、Windows 两次 OS Applied，实际IPv4 source `198.19.254.1→198.19.254.9`，默认用户外层 MTU1460、内层双方1358B real OS读回，真正 UDP 内核双向和真正 TCP 双向37字节回显 PASS。原始 Udp尾部实送/收：Windows269/270，Linux384/267；计数为两个独立双向运行时流，不是简单加总去重比率。

关键 H1403 补漏**不是产品改变**：新 B 原 protected Ready 后两方向 true app 首轮交付分别增10/8，服务端旧 A RX 原始 `grace_ms=18807` 内未被停止，B 真内层 UDP 又增169/167，真实到期输出一次 `V4_PUBLIC_GAME_GROUP_STOP_DRAINED reason=same-protected-cohort-grace-expired`，B持续、随后全服务端真实Stop，Windows两代 Rust worker/WAL exact owned Stop均成功。因原 Action源`e69e`测试提前7秒打断这个服务端 grace，那个原CI FAIL、原 server Stop NOT_TRIGGERED 仍保留；本次同一原产品源码/算法/协议靠修定时验收口径才取得新完整触发的 PASS_SCOPED。原明显 `M0_PLAN027_GAME_DUE_FAULT stage=send_records_entry`只是 `first_due_entry` 首个 due batch 的一次性观测，不是发送失败错误。

ISA-L：Win Rust DLL同 SOURCE 编译 feature `native_fec_acceleration`+静态官方 ISA-L `c387163f...`，Windows Native owner full-block单位回归实际后端与scalar byte-identical通过；Linux server原 Game4本次Stop readback `selected=prefer-native native_linked=1 tx_native_quanta=4`，**客户端真实 Windows native quanta 没有 Stop日志，故 Windows客户端实际执行次数 NOT_MEASURED，不能仅凭编译冒充用户所要求真实加速全模式资格**。Game FEC单块短/one-source合法 scalar。

另严格更正观测：本批原报告 `OS_mutation_to_new_ready_observed_ms=26703` 在**B 已真实 Ready**后等待 18.807s server old grace才算，因此**不能拿26703ms当新 TLS/接管SLA**；当次原始单调 source4 mutation 到 B Ready 精确时间 `NOT_MEASURED`，不为报表字段重复跑网络。本轮 Stop/连续交付硬门已实际完全触发，按用户外因功能准则为 **PASS_SCOPED**。独立 Linux co-client 同一个 server仍 NOT_RUN，剩余 L1/L2覆盖见专项验收，不提前宣布 PLAN028完成。

```feature-impact
{"kind":"none","ids":[],"reason":"Original Windows native driver product Game4+FEC two-generation true business and exact server grace Stop evidence; no new protocol/config/user-facing feature."}
```
