# PLAN028 H1278 — H1277 原生验收及最终 TLS ACK 交接窄修复

2026-11-06。H1277 [Action 42184350422](https://github.com/lly8666/wbd-next/actions/runs/42184350422) 的 SOURCE `ccbaef36a98be86ff159f96584ddd1f5a06d474f`：build 成功，baseline 1800s 五客户端全部业务与真实换代 **PASS**（alerts=0），heterogeneous 和 pressure 场景真实完成但 FAIL。三个未过期的完整压测 ZIP digest 与各真实计数归档于 [H1278 H1277 evidence](../evidence/M0/PLAN028-H1278-H1277-THREE-1800S-ARM64-POSTRUN-20261106.json)，不同 SOURCE 不混算。

## 先验收后改代码

- Baseline：五客户端真实换代 Alice27、Bob25、Carol Game2 21、Dave Game4逐lane15/服务端15、Erin16；真实应用 gap 最大仅90ms，queue overflow=0，baseline **仅此场景 scoped PASS**。证明 H1276 Game4 775.92s 单向崩溃得到恢复，不意味着其他压力资格已过。
- 异构：Carol Game2 Gen10 两条真实客户端认证 lane 56713/56714 于 08:07:41 本地 M4 Ready；服务端只 staged 56713，56714 于 08:07:55 TLS timeout，真实双向空洞 103.23/103.32s，Server M4 **未完成**。Dave 11 次本地热lane/服务器只确认10次；Erin虽换代10次却有5.36/4.33s业务断流且30次cold candidate失败。alerts=7，FAIL。
- 高压：Carol Gen3 (50420/50421) 于 08:02:39 本地 READY，服务端第二lane 50421 于08:02:52 TLS timeout；Gen11 (64632/64633) 于08:08:53 本地READY，服务端64633于08:09:07 timeout。真实双向空洞94.75/94.84s。Dave仅5次Game4 lane成功，服务端共享TUN其租约pending overflow=6031，Alice=7；Erin仅6次整组成功，5.37/4.33s真实空洞；FAIL。
- 服务器平均CPU（单核百分比）/峰值RSS：baseline 67.911%/173300KiB，hetero 87.856%/187924KiB，pressure 103.574%/230392KiB。原始accepted表演重传 R 分别184867571/436162982/400029429 B；平均0.82163/1.93850/1.77791 Mbps；R/(F+R)分别0.69774/1.11228/0.53701%。**控制C、FEC parity、IP/TCP/L2物理链路完整开销均未测**。业务p99为成功交付样本，不能隐去断流。

## 产品级交接故障假说与可证伪修复

服务端原始 `BootstrapStream.Write` **等待TCP累计ACK**才将 TLS response 冷提交推进到 M4。客户端最后 TLS response 已收到、原生 Rust M4 Ready 后，若该ACK在TC物理丢包中消失，服务器重发仍是旧 TLS payload，而新的 Go Socket BPF 已严格排除 DATA，导致服务器最终15s timeout。相同窗口的受保护身份、客户端端口与服务器流日志吻合；**此时尚无服务器阶段字段足以证明所有 timeout 恰好处于最终 ACK 阶段，故仍为针对性假说，待H1278新日志证实**。

`r0/go_overlay/internal/faketcp/raw_detached_data_linux.go` 新增状态封闭的 `RepeatDetachedBootstrapACK`：仅在已 `ClientAssociationDetached` 且原TLS流存在时，使用原序号、原累计ACK和原源端口发送**零payload、无seq/PN推进**的原始ACK；已Stop或未认证状态不允许发。原始Game2/4组、Game4单lane热换代、Normal Off/Auto/Fixed6均复用同一个 4.48s 内最多六次的冷交接 ACK guard（80/240/560/1120/2240/4480ms）；上下行原Native Rust DATA/crypto完全不改，无新ACK协议、明文认证、第二恢复器。Rust shared-TUN 8包/64KiB/100ms上限不变。增加服务端 `ErrV4ProtectedReplyAckWait` 分辨 *TLS原final reply 写入/ACK等待* 的失败，而不是再笼统地报认证超时。

原始 FakeTCP Sender 累计ACK屏障、只读被验证的末尾ACK、Stop后无网络写入的 ARM64 独立预检 [42190296562](https://github.com/lly8666/wbd-next/actions/runs/42190296562) **PASS**。该单测不证明全30分钟、也不证明全部高损拥塞情况。

新 `.github/workflows/m0-plan028-h1278-arm64-30min-tls-last-ack-scoped.yml` 将新 SOURCE 原生ARM64双端编译锁定；三台并行真实 1800s、五TLS用户、共享443/TUN、TC随机损伤、业务 UDP+TCP、30分钟桶、Stop/租约、M4 server端口、p99、CPU/RSS、R bytes 和共享队列全部自动采集；任何 client/server 换代不一致、业务断流/丢包告警或overflow仍严格FAIL。**尚未完成后禁止宣布产品PASS**。

已保留未解决 H998 原同socket在线MTU收缩FAIL、H1259/H1268原 S2C 偶发黑洞；Android/公网物理/控制C/全IP完整成本未覆盖。

```feature-impact
{"kind":"updated","ids":["game-lanes","linux-raw-tun"],"reason":"Finite original protected TLS last-ACK repeat after native M4 to avoid server pending ACK barrier; all legacy original protocol fields and native steady DATA unchanged. Existing Linux Game and Normal cold handoff implementation/limits documented."}
```

## H1278 strict assembly and governance follow-up (metadata only)

Initial H1278 Action [42190949906](https://github.com/lly8666/wbd-next/actions/runs/42190949906) stopped **PRE-BUILD** at `FEC2_ASSEMBLY_REJECTED: overlay result blob mismatch: internal/v4productcli/linux.go`; no native scenarios executed and no product PASS/FAIL inference. The pinned exact Git blob was corrected, with no bypass of assembly validation, in source `1e4ceb200c71ce5b7230212b568503c562cecf0e`. The replacement [Action 42191219373](https://github.com/lly8666/wbd-next/actions/runs/42191219373) has built successfully and its three true ARM64 1800s scenes are running; full evidence still awaited. The feature card now keeps historical H643/H635/H1277 details in this and prior devlogs rather than exceeding the repository's 16KiB machine-checked card bound. This accompanying source/feature metadata correction does not reclassify any product failure or change the frozen running-source binaries.
