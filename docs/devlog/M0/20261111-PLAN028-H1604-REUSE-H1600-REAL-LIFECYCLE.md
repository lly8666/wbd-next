# PLAN028 M0 H1604｜复用H1600同源真实轮换，不重跑网络

没有新网络Action。重新读取 `8a31375e36bb6a93860c5579e64b4a39d0b6e346` 原始artifact `13861275233` 的Bob/Carol/Dave/Erin以及server日志并独立重哈希，逐文件hash和owner事件写入 [H1604 evidence](../../evidence/M0/PLAN028-H1604-SOURCE8A313-REAL-A-B-GAME-LANE-ROTATION-20261111.json)。本源H1600五端150s真UDP/TCP成功和Alice先Stop后Bob继续仍以H1601原报告为主，不因日志marker取代实际业务。

- Bob Normal Auto：109s显式轮换，实113.319s触发；B gen2认证期旧route保留，B authenticated Health接通后promote，原A延迟17.773s准确Stop。Bob与Windows Alice为同账号独立自动/32。
- Carol Game2：103s轮换实98.086s触发；新组两lane原Go TLS/Rust M4 Ready、单服务端443，不先拆旧组；A→A+B→B overlap commit日志`new_tls_m4_before_old_stop=1`；旧A延迟14.5s准确Stop。
- Dave Game4固定FEC：实116.746s轮换时只替换lane1 `45031→60881`，其它**3条lane不重启**；server同event读回`sibling_lane_restarts=0`，原Rust/Go真实读回。其`FEC_COUNTERS`本场source40079、parity64685、recovered3、rx_conflict6原样保留；它不等于IID可靠性、也不在0%配置丢包下承诺零FEC诊断冲突。
- Erin Normal固定profile并显式outer1280：127s间隔实128.541s轮换，B先authenticated Health/OS route promote，旧A延迟10.109s准确Stop；不覆盖用户1280意图。
- 原应用五端150s **636494**真实UDP唯一双端交付无缺失、TCP双向1458有效帧、invalid0、最大活跃接收空洞63ms，Alice Windows全程维持业务，Win Stop后Bob续4 UDP，全六owner Stop。

**本源没有触发B候选失败**，不可把该成功写成“候选失败仍保A”已实测；老ARM64 H1501双1800s出现过高损候选失败后恢复，按旧SOURCE原样可作稳定组件回归，不移植成新原生Windows验证。Windows默认轮换0，不能拿Linux测试当Windows自动轮换。用户明确无需双Wintun场景，H1587旧FAIL保留为已知组合限制。H1602本源近MTU真实Action在途，不重复派发，仍PLAN028 IN_PROGRESS。

```feature-impact
{"kind":"none","reason":"Reclassification of source-locked old Action raw owner lifecycle receipts only; no code, configuration or user-facing feature changed."}
```
