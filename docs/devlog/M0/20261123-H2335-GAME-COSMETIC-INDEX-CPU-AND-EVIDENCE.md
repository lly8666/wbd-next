# M0 PR #68 H2335 · Game 原密文低 CPU 1/2 可选索引同步

- main SOURCE `dfdb388536ed3732260fcc9be7c503cd9bc21394` 本轮在 `crates/wbd-engine/src/v4_game_cosmetic_outer.rs` 只允许唯一实际可保留的 Linux Game snapshot 进入 ACK BTree，其余首发仅 O(1) 推进连续原TCP Seq；Windows Game OFF/fixed6 两模式均用 Normal 1/2 选择，所有缓存/全局准入在建树前验证。两处修改已原样同步此实验分支。
- SOURCE `60a20196d9c028c20d989232b991a6a0becb30e0` 的 Windows12 Game OFF/fixed6 0/5/30% [#45130747250](https://github.com/lly8666/wbd-next/actions/runs/45130747250) 与 Linux client↔server Normal六档+Game12 [#45130747501](https://github.com/lly8666/wbd-next/actions/runs/45130747501) 仅是此前 main 同源 scoped 资格，不能继承为本 PR 当前 SHA 的通过；Game 30% 外观R/F仍远低于Normal，Windows Game原线F分母尚未独立测得。
- 保留真实已认证ACK停滞≥1秒、一个认证ACK阶段最多一个真实copy、原PN/Seq/密文最多一次、lane80ms、R/F≤10%、FEC parity独立、0%非洪泛、真实Stop、默认开关与已废弃旧M2逐record Receipt。绝不因表演比例人为造ACK或定时DATA PTO。
- 新源码的 main Win12、Linux18 已触发独立测试，本 PR SOURCE 自身没有完成这些测试。当前状态 **VERIFICATION_PENDING**，不声称PLAN029 P0/P1/P2性能或新source CPU优化PASS。


## H2336 · 新 SOURCE 完整 Linux 真网核收与同机 CPU 复测
- main 产品 SOURCE `dfdb388536ed3732260fcc9be7c503cd9bc21394` 的 [Linux 原 GoTLS/Rust client↔server 双向 18 场景](https://github.com/lly8666/wbd-next/actions/runs/45137388828)：**19/19 jobs PASS（1 二进制构建 + Normal 六档 + Game2/4 OFF/fixed6 各0/5/30%）**；所有真实 native netem、双 owned Stop、同源 SHA。旧 SOURCE `60a20196d9c028c20d989232b991a6a0becb30e0` 与本 SOURCE Game12原产物逐档比对，Game2 client/server各2、Game4各4次可选原密文复制，0/5/30均未变。即**没有候选丢失，但比例也没有随丢包增长**。真实 Game wire R/F 字节双端不齐，不应由复制包数估算。
- [真实 Linux Game2 30% 同一 runner OLD→NEW→NEW→OLD](https://github.com/lly8666/wbd-next/actions/runs/45138901381)，旧源码 `60a2019`、新源码 `dfdb388`，测试夹具 SOURCE `ef7e3c1b5e362d705056880b1c0f139ee54a9991`：4/4真实Linux GoTLS/Rust client/server、双向netem滴包读回、owned namespace完全清理、Stop、每端各2次外观均合格。客户端整进程CPU OLD=(1.99,2.01)均2.000秒，NEW=(2.01,2.01)均2.010秒，新-旧+0.010秒（+0.50%）；服务端 OLD=(2.08,2.11)均2.095秒，NEW=(2.11,2.11)均2.110秒，新-旧+0.015秒（+0.72%）。各次实际唯一首到约9.08–9.11 Mbps。**小样本 CPU 差值在计时/虚拟机波动范围，不能认定低CPU收益或显著退化；非算法独立采样。** 严格不以跨runner先前高损2.17→3.83秒比较宣称优化成败。停止类似微调，继续真实表演外观证据。
- 新 Windows签名 Game2/4 OFF/fixed6 12组矩阵 [#45137388745](https://github.com/lly8666/wbd-next/actions/runs/45137388745) 正在核收。Game4/5%某个 job 在 `git fetch` 已检出的同 SHA 时 GitHub HTTP403，**业务未开始、非产品重传失败**；旧成功不能继承，需待矩阵完成后只针对失败job重新运行。Windows Game原 F/R 统一字节总账依旧未测；Linux-client→Windows-server原生角色也不在当前构件范围。PR自身source未经新矩阵，因此目前只算 main 局部实际证据。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Mirror main H2335 Game Linux live-only shadow ACK index and Windows OFF/fixed6 half-sampled pre-admission path into PR68; same original firstcopy F and one-copy/ACK guard, independent branch native qualification pending."}
```
