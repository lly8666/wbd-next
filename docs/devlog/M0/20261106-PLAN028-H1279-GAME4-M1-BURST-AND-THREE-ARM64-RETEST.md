# PLAN028 H1279 — H1278 原生验收与 Game4+FEC M1 消费修复

2026-11-06。H1278 [Action 42191219373](https://github.com/lly8666/wbd-next/actions/runs/42191219373)；冻结 SOURCE `1e4ceb200c71ce5b7230212b568503c562cecf0e`，真正 ARM64 原始 Go TLS/FakeTCP + Rust M4，三场并行各1800秒、五认证客户端。build PASS，baseline PASS（0 alerts），heterogeneous/pressure FAIL。ZIP 三个实际 SHA-256、逐客户端真实 M4/业务/队列与CPU/重复record数据：[H1279证据](../evidence/M0/PLAN028-H1279-H1278-SOURCE1E4-THREE-ARM64-1800S-ACCEPTANCE-20261106.json)。

| 场景 | Game2 Carol服务端双lane M4提交；最长双向无收包 | Game4本地/服务器真实单lane热换代；服务器/客户端真实共享TUN queue overflow | Erin Fixed6整组成功/候选失败；上/下行空洞 | CI |
|---|---|---|---|---|
| baseline | 22组，10/30ms | 17/17；0/0 | 16/3；50/100ms | PASS |
| heterogeneous | 16组，50/90ms | 8/8；0/0；上/下行1110/2240ms gap | 10/30；2300/7410ms | FAIL |
| pressure | 17组，70/170ms | 8/8；6364/3321，真实M1超限 | 8/34；2420/2300ms | FAIL |

Game2异构和高压原 H1277 的103/95秒黑洞在新SOURCE未重现；真实UDP业务上/下行均值分别从9.33/9.32到9.90/9.90 Mbps、16.32/16.31到17.82/17.81 Mbps。服务器 `stage=protected_reply_ack_wait` 计数三场都是0，因此**不能把旧故障根因确定为TLS最终ACK丢失**，只证明补发存在时本次真实M4完整提交和业务交付正常。

新的单一窄修复：在 `crates/wbd-engine/src/v4_game_public_kernel.rs`，Game4+FEC原始Rust TX worker从一个有64包inbox的独立认证M1通道，每轮FIFO最多接收8个现成业务IPv4包（原4），与一进程唯一真实TUN reader原有最多8包batch对齐。若巨大IP/DF0包异常则用既有下一轮片段处理路径，未增强业务重传、未跨lane混用PN/密钥、未增加Go DATA/线程、未放宽TUN pending 8包/64KiB/100ms及真实队列丢包阈值。新定向Rust测试检查同轮8包 FIFO 和余包不被超量吞掉。

源锁定 `.github/workflows/m0-plan028-h1279-arm64-30min-game4-m1-drain.yml` 严格原生ARM64共用同一个 build，三个独立1800s五客户端场景，原始核验 `rotation_verdict=PASS_ALL_FIVE_SCOPED` 且 `alert_count=0`，任何失败必须保留真实 artifacts。**在新数据出现前，H1279 PERFORMANCE_UNVERIFIED**。Game4 15%loss下冷TLS延时与Fixed6 30%下2–7s空洞不是此改动能凭逻辑断言修复。

外层repeat仅真实accepted R/(F+R) record，控制C/FEC parity及IPv4/TCP/L2总开销未测。H998同socket在线MTU旧FAIL、H1259/1268 Fixed6 S2C偶发故障保持开放，Windows/物理外网/Android未覆盖。

```feature-impact
{"kind":"updated","ids":["game-lanes"],"reason":"Existing Game4+FEC original Rust M1 shared TUN worker accepts a bounded 8 instead of 4 already-ready source packets per turn; FIFO, queue length, owner/PN/FEC and wire unchanged."}
```
