# PLAN029 H1980｜H1979 预检收件与中断恢复（不重复 dispatch）

- 刷新 `main=b7a3339f9b31074486310ce5f794022f152afb13`；按 `START_HERE.md`、`AGENTS.md`、registry/M0 cursor、029计划与分流契约 §3B/§5/§7 核对。最近 Actions 没有正在运行的原生测量。
- [H1979 源锁 Action43820149812](https://github.com/lly8666/wbd-next/actions/runs/43820149812) **success**：cheap job133141140535 真执行 `test_m0_plan029_h1977_boundary_qpc` **8/8 PASS**，包含并发 WintunSendPacket call-start/return 与 kernel read 的正反例；Windows Go job133141373797、Linux Rust job133141373904、Windows Rust job133141374009 SUCCESS。[Governance43820149761](https://github.com/lly8666/wbd-next/actions/runs/43820149761) 双job和 [maintenance43820149743](https://github.com/lly8666/wbd-next/actions/runs/43820149743) 也 SUCCESS；本 SOURCE 原生**SKIPPED/NOT_RUN**，不冒充联网PASS。
- [原 H1978 native Action43817058020](https://github.com/lly8666/wbd-next/actions/runs/43817058020) 第19步**FAIL**，原错误因果假设是 inner kernel read 必须晚于 WintunSendPacket **返回**；实际上 2条在调用**开始**之后、返回之前22.8/2.6μs就已被内核读到，H1979 修的是分析器，不是产品调度。原 Windows/WSL2 双臂各2048×1KiB+32预热真字节、SHA/FIN/owned Stop PASS；物理p50/p95/p99 269/334/381μs、Direct 521/620/682μs、0次≥8ms、0重传。**原 native FAILURE 保留**。
- 先前 H1974 另一 SOURCE [Action43808776053](https://github.com/lly8666/wbd-next/actions/runs/43808776053) 有**真实5次61–63ms Direct尾延迟和4次重传**，并未被 H1979 修好，仍 OPEN。signed-only preconnect/post-ingress flush 默认 OFF，不凭不同 SOURCE 推因果。已有 [H1848](https://github.com/lly8666/wbd-next/actions/runs/43600601863) 非CI显式 Normal CN 实网 Direct DNS/TCP/UDP、Tunnel、owned Stop 限定PASS；无需重跑同类探针。
- §3B：H1690 本地listener和默认Defender Block不能证明根因，有新的可证伪假设才做 A原状→B少量精确owned Allow→C恢复；不引旧WFP。§5 Direct满/共享FlowPin、慢盘FakeIP、DNS满、共享分配64MiB/队列年龄/公平性仍需真实压力退出。§7 D1–D5/P1–P2、真实WinForms Connect→effective→双出口→Stop、Game4 CN、IPv6真实包、填充仍 OPEN。H1866测试机无原始IPv6 default，不能以空route误称已阻断。028限定收口、030未开工。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Source-locked H1979 QPC 8/8 and Go/Rust/Governance preflight PASS, native NOT_RUN; preserve H1978 original FAIL and H1974 tail OPEN, no new dispatch."}
```
