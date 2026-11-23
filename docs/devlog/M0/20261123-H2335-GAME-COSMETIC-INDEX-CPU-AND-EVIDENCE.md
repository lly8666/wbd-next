# M0 PR #68 H2335 · Game 原密文低 CPU 1/2 可选索引同步

- main SOURCE `dfdb388536ed3732260fcc9be7c503cd9bc21394` 本轮在 `crates/wbd-engine/src/v4_game_cosmetic_outer.rs` 只允许唯一实际可保留的 Linux Game snapshot 进入 ACK BTree，其余首发仅 O(1) 推进连续原TCP Seq；Windows Game OFF/fixed6 两模式均用 Normal 1/2 选择，所有缓存/全局准入在建树前验证。两处修改已原样同步此实验分支。
- SOURCE `60a20196d9c028c20d989232b991a6a0becb30e0` 的 Windows12 Game OFF/fixed6 0/5/30% [#45130747250](https://github.com/lly8666/wbd-next/actions/runs/45130747250) 与 Linux client↔server Normal六档+Game12 [#45130747501](https://github.com/lly8666/wbd-next/actions/runs/45130747501) 仅是此前 main 同源 scoped 资格，不能继承为本 PR 当前 SHA 的通过；Game 30% 外观R/F仍远低于Normal，Windows Game原线F分母尚未独立测得。
- 保留真实已认证ACK停滞≥1秒、一个认证ACK阶段最多一个真实copy、原PN/Seq/密文最多一次、lane80ms、R/F≤10%、FEC parity独立、0%非洪泛、真实Stop、默认开关与已废弃旧M2逐record Receipt。绝不因表演比例人为造ACK或定时DATA PTO。
- 新源码的 main Win12、Linux18 已触发独立测试，本 PR SOURCE 自身没有完成这些测试。当前状态 **VERIFICATION_PENDING**，不声称PLAN029 P0/P1/P2性能或新source CPU优化PASS。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Mirror main H2335 Game Linux live-only shadow ACK index and Windows OFF/fixed6 half-sampled pre-admission path into PR68; same original firstcopy F and one-copy/ACK guard, independent branch native qualification pending."}
```
