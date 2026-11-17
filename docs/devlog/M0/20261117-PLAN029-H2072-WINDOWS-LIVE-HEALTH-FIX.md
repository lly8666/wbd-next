# PLAN029 H2072｜Windows native 真 Entry Health 冷启动接线补遗漏

上轮真实 [H2070 Action 44025145100](https://github.com/lly8666/wbd-next/actions/runs/44025145100) 已结束 **FAIL**，原产品 SOURCE `2fca1a93b4f9f7d3e7c5985adc356ade13332e86`。B 二次 GUI SYNACK/TLS；Linux B 的原生 M4 RAW13/tuple10/TUN10；但服务端仍无 B 规范认证 Health，保留旧 A /32。第二次 OS Applied、真实 Direct/Tunnel TCP/UDP、TTL 重启第三答均 NOT_RUN。旧 FAIL 不提升。

**实际首处源码遗漏**：核对 [H2067 的原 commit](https://github.com/lly8666/wbd-next/commit/2fca1a93b4f9f7d3e7c5985adc356ade13332e86)，Windows `v4_windows_native_runtime.rs` 仅有 `HealthClock.arm_client_cold_ready` 的**合成单测**，而非 `start_native` 实际 Entry 调用。Linux `v4_embedded_go.rs::start_loop` 已在原 M4 启动时 arm；Windows `v4_windows_owner.rs::m2_next_feedback_entry` 只有 `m.health.tx_due` 时发规范 AEAD kind1 Health。即 H2067 的文档“已加实际冷 Health”高估了真实提交。

**本次源改**：在 Windows `start_native` 确认 Wintun、Npcap 实句柄，排除已启动同一 owner 后，锁实际 Entry 并以 `m.health.arm_client_cold_ready(m2_clock().0)` 激活原有五次冷 Health，再启动原 native TX/RX。沿原 PN/AEAD/重放/加密 kind1 TLV；Linux B 必须有真实 authenticated hint 才可晋级 /32。无 WFP/协议/ABI/线程/安全门槛改动。H2067 单测注释明确它只测时序，不冒称生产接线。

**本 SOURCE 未编译/未做真实 Windows 原生测试**，不得称已修好联网；本次未重复 dispatch。后继只复用已批准三个日常场：先 GUI 真 Disconnect→Connect 一场（B Health/ /32、OS1460/内层1389、两出口 TCP/UDP、两端 Stop 都要 PASS），该场通过才同产品 hash 复用独立域名二次 UDP TC→同 TCP53 与 TTL2 Stop/重开第三答。若仍失败，下一轮一次 B M3 open/TLV/hint 数字诊断，不重刷 H2070 旧 RAW 探针。极端满载、慢盘/崩溃、旧 IPv6 矩阵按最新用户限定不新增。

```feature-impact
{"kind":"updated","ids":["windows-native-transport"],"reason":"H2072 now calls HealthClock on live Windows native Entry; only source implemented, native verification NOT_RUN, H2070 failure retained"}
```
