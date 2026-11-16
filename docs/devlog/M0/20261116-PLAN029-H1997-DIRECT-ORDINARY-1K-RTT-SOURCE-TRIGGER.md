# PLAN029 H1997｜只测现有普通 Direct TCP 1KiB RTT p99（无产品修改）
- 用户最新指示：跑多种有代表性的 Direct 工况，看延迟是否合适。保持上次“明显差距优先、停止极端功能开发”的边界；本批仅跑现有签名原始 Windows2025 ↔ WSL2 Linux source-locked 真实场景，不开通用饱和测试。
- 已收 H1995 [Action43844626304](https://github.com/lly8666/wbd-next/actions/runs/43844626304) PASS：1MiB 人工 16KiB/4ms 节奏物理295.366ms / Direct301.871ms、同SHA/FIN、120/120 Tunnel小UDP p99 2.823ms、双Stop PASS。**这不是Direct RTT p99**。
- 本 SOURCE 仅以工作流头部注释显式 arming 一次 `[plan029-v3-real-p2-rebuild]` + `[plan029-v3-real-p2-steady-qpc]`：原Normal签名业务+同一VM单条已建连接物理和Wintun Direct各32预热+2048×1KiB真实Windows QPC kernel echo，原Linux SHA/FIN和双方 owned Stop。2048只做**一轮已存在测量**，不是复刷种子或新极端功能。
- 保持 `WBD_PLAN029_P2_POST_INGRESS_FLUSH_SCENE=0`、`PRECONNECT=0`、`BULK=0`、`HIGH_RATE=0`；没有新的 timer/线程、产品逻辑或传统WFP。观察物理和Direct p50/p95/p99、最大/≥8ms异常、Tunnel UDP p99、总回包空洞；一旦原 native 报错，按第一个失败边界保留 FAIL、Stop NOT_RUN（若未执行）。
- 源锁本轮网络证据、Action号、结论**尚 NOT_RUN**，不可把历史 H1978 无 >8ms 与 H1974 5次61ms合成“已经修好”。只从 GitHub 实际 Action 收件，不补造性能数字。
```feature-impact
{"kind":"none","ids":[],"reason":"H1997 existing signed normal Direct steady 1KiB physical-vs-Wintun p99 measurement only; no product path changes, no extreme feature development."}
```
