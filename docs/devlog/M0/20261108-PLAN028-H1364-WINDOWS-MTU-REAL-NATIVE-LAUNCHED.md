# PLAN028 H1364｜Windows 原生同源 IP 的真实物理 MTU 收窄

- 2026-11-08，main SOURCE：`04dbda77d0bcb85ea4e01b3c3a7ba9aae42f073a`。
- 原始 Actions：[42448657827](https://github.com/lly8666/wbd-next/actions/runs/42448657827)。只启动一个 Windows↔真实 WSL2 原生 Normal 场景：官方签名 Npcap/Wintun、Go TLS443/Rust，限定测试自有 WSL vEthernet，保持同一 IP/ifindex，真实 OS 将有效 MTU 1500 收窄至 1280，后续核新认证代、原始 UDP/TCP、双端 Stop 与地址/MTU 恢复。
- 已核完成的低成本预检原始日志：`PLAN028_MTU_ONLY_EXPLICIT_MARKER=1`、`SOURCE_LOCKED_MODE_ENTRY normal N0=0 A5=RETIRED`；未跑七模式、不改产品数据面。**原生业务结果仍 IN_FLIGHT，不能提前标 PASS**。
- 验收口径按用户当轮明确指示：真实应用与认证/Stop 完成即判对应范围 PASS，不受报表、参数条件或 CI 外因假红覆盖；须保留原 CI 结论并分账。若外因使真实业务根本未运行则仍 NOT_RUN，不假设成功。
- 此轮是 Windows 同一张真实物理 WSL 虚拟网卡的 MTU 事件；它**不是**两台互相独立 Windows Wintun 客户端的同服认证/隔离资格，也不替代 Android/物理广域网或 L3 两条1800秒。

## 状态

**真实原始 Action 在执行中。** 完成后按不可变原物证增补结果及治理索引。
