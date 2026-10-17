# M0-024 有界 TUN 读阻塞与 TX 部分完成收尾（2026-10-17）

SOURCE A `80b47c853499da292295671f2b1a49407c0367a5`; B CODE `9c76636a482de91381b6cc9601f0bdc6852e732a`; 配对 workflow `7b3abb35723b4a6615b10aa0098140dad7ea3eec`; 汇总 native gate `fca4456313e59c0a67f4d8b98959a62d2af71b12`。恢复时 main `80b47c853499da292295671f2b1a49407c0367a5`，main Actions 无未结束项目；原 D10 历史 FAIL 不改。

- 根因 1：原 `background_tun_once` 调用 `read_ipv4_into`，IPv6 过滤后在写入方共享的 TUN serialized 锁下再次 poll(≤750ms)。B 只在原 engine 改用已有 M4 `read_ready_batch`（poll0/O_NONBLOCK）；无新 driver，32 次观测含无效帧有界，空 EAGAIN 为正常暂态。原 BorrowFence、Stop/generation/FD 独占保留。真实 ns+TUN 注入 IPv6 后无新 IPv4，原认证 C2S 业务仍在 400ms 内到达：native `39041377796` PASS。
- 根因 2：原一项失败使 `tx_route=None` 且整体返回 error，已被 kernel copied 的 prefix 未记账。B 复用 typed `KernelSendReport`，小 `TxTurnCompletion` 分类 copied/unsent/uncertain/backpressure/route invalidation；只有明确路由/设备/MTU信号失效 M0 cache。EAGAIN 不失效。同步内核返回后归还原 FrozenRecord+Arena，确定尾项有界放弃，uncertain 不重发、不 reseal、不重取 PN/seq；新统计内部 atomics，不扩大队列和配置。
- 同一个功能 Action `39041377796` 的 Go TLS→Rust owner→真实 raw/TUN、IPv6 HOL、PN0 drop PN1 first arrival、真实 MTU/netlink、Rust 分类 0/1/32/33/partial/unknown/EAGAIN/Stop 确定性反例均 PASS。罕见 errno 为确定性模拟，不宣称真实内核强行复现。构建/产物 ID/hash 见对应 JSON。
- P10 A→B `39041159892`: A 80.3667 → B 78.9629 CPU-s/GiB (−1.7467%)，p99 C2S 91→86µs、S2C 105→100µs；P10 B→A `39041159913`: A 71.4200 → B 70.8461 (−0.8036%)，p99 C2S 84→86µs、S2C 94→94µs。都双向无缺包/非法包。
- 20pps SPARSE `39041159871`: 0 缺包，p99 C2S 334→178µs、S2C 392→215µs；CPU 小样本不定性。跨 Runner 绝对 CPU 不作因果比较。
- 补丁边界：结构修补和定向功能/成本复验完成，CPU 利好但低幅收益不确证；D10 `39032995995` 仍 FAIL/INCONCLUSIVE，不再重跑，C50/物理/全产品及原 R0-023、超 MTU、组合 M1–M4 都不因本补丁升级。无新增 CLI/GUI、wire 或产品 feature。回退仅撤销 B CODE 并保留本精确证据；会恢复历史阻塞/记账缺陷，不推荐。

下一动作：按原计划独立启动 M0 冻结 M1/M4 接线、R0-023/超 MTU/Stop 的阶段集成，不再打磨 024 CPU 小差异。

补充原始 artifact 审核：三个性能 Actions 各 A.json/B.json 的 C2S/S2C `missing_or_not_delivered`、`duplicate_received`、`invalid_received` 与 `injector_send_errors` 全部为 0；P10 用户 UDP 净荷约10Mbps/方向，IPv4内层实际约10.5526Mbps。来源为原 GitHub artifact ZIP，不是按 summary 推测。

恢复模块集成的只读来源核验：main `161a61ed3a48901866ff38d87b5f0053026af73b` 与 M1 冻结 SOURCE `a39ff711`、M4 冻结 SOURCE `b7bcde7` 相比，绝大多数已冻结 module 文件与 main 的 blob 完全一致；差异集中于 main 为原 Go owner 新增的 M1 接线 helpers，以及 M4 driver outcome/loan 的单测变体。**不重复导入已有代码，不宣称 R0-023/超MTU/Stop 组合已经通过**。下一个独立工作包应首先围绕原真实 Go→Rust owner 超 MTU 与 Stop 硬门确定最小缺口。
