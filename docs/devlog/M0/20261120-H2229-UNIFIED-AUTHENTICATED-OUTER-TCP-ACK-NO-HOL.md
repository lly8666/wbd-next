# PLAN029 / H2229 — Windows 样式统一外层伪 TCP ACK（Linux C/S + Windows Normal/Game），稳态窗口65535，不引入 HOL

## 用户授权与不可突破边界

- 用户实体 Windows 与 Linux 业务 TCP 曾见 80–200Mbps 平台和不稳定上行建链；该相关性**不是** ACK 根因的证明。用户指定优先统一 Linux 服务端/客户端与 Windows Normal/Game2/Game4 的稳态展示 ACK，同时双方小幅提升 ACK 更新频率，Linux 服务端 TCP 稳态窗口字段 65535；保留自己的乱序即到即交付、原有表演式外层重传和无逐记录 M2。
- 这里是 **FakeTCP 外层 appearance ACK**（IP/TCP 编码头和零载荷 ACK，独立于原始真正内层 OS TCP ACK），不允许把 M3 AEAD/唯一 PN、真正 Linux/Win TUN 交付、authenticated Health、FEC 恢复、repair 信用、peer-retire 或原始 Go TLS 冷握手定义为新 ACK 的效果。该 cosmetic ACK 不是 kernel socket 的 TCP 拥塞控制或 SACK 恢复；不能凭增大发包频率声称绕过 BBR。

## 源码原状、最小产品改动

- Windows Normal `v4_windows_native_runtime.rs`：已经使用认证来源的累积 TCP byte span、最多4个 future SACK blocks、250ms cosmetic gap abandonment、DATA piggyback；仅将连续 RX 的 SACK snapshot 间隔从20ms缩为10ms（每秒最大100），仍只在有原始 protected ACK 候选且只由 native TX 发送空载荷控制。
- Windows Game `v4_windows_game_native_runtime.rs`：原有每lane `AckLedger{next,holes}` 将超额 future ranges 直接丢弃，现复用一个跨平台有界 `CosmeticAckLedger`，把相邻已认证跨度合并、不推测不存在的连续真实交付；既有纯ACK及DATA携带的 `65535` 不变。无新线程和热路径回调；Off/Fixed不碰修复/保护功能。
- Linux Normal `v4_embedded_go.rs`：原来只在 Negotiated SACK + 真实未来空洞时，每>=20ms最多发送一条 pure ACK/SACK；且 steady DATA/repair/Health `advertised_window=4096`。改为在本代际至少一份真正 AEAD 认证入站后，对累计认证进度**及**已协商 future SACK，在每10ms有界限内允许发送独立的纯ACK；原始 DATA piggyback ACK 持续，独立 ACK 仍走原 RawTx + TLS scoped path，无应用交付门槛。所有 Linux Normal steady DATA、repair、control 和 Game 头窗口调整为 `65535`。注意此为稳态展示值而非可凭空增加真的内核用户内层 TCP 收取能力。
- Linux Game2/4 `v4_game_public_kernel.rs`：原 DATA/Health/repair `ack32=1,window=4096` 完全不反映认证进度。现从不可伪造的 original Go TLS per-lane `rx_boundary` 初始化每lane ACK 账本，并由每lane独立 AEAD/Pn/原 Game-FEC + 实际内核 TUN 写入/完成提交成功推进 cumulative ACK；乱序只记有界 merged future byte spans，绝不等待一个先前包或影响原始 Game M3 乱序业务交付。缓存当前每lane ACK 和真实已复制 TX seq 的原子快照供现有 TX 复用，在同 RX owner 内最多每10ms best-effort发一份没有业务数据/密钥的纯ACK。Game current cold handoff未向独立 Rust Game lane传 SACK-negotiated 标志，因此此轮 Game pure ACK仅累积不携带虚构 SACK options；本端维护 future 并允许窗口真实闭合。以后若完整代际握手绑定 SACK 权限可单独升级。
- Game4 热换lane时同时更新 `tx_seqs` 和真实 protected `rx_seqs`，RX lane重建独立账本，不跨旧 tuple/epoch 使用旧ACK，不代替对端 TCP 数据收取。最高频率是一个 sender 10ms，有必要时第一个认证进度可立即确认；不能解释为任何 TCP RFC 强制常数，仅为受控可回退的 presentation 控制频率。

## 验证与尚待证实

- 此变更不修改 `crates/wbd-recovery/`、`crates/wbd-types/`、M2 source/bitmap、TCP 内层处理、Health90、客户端 GUI、装配 donor/blob manifest、FEC 冗余、外层重传预算/调度，也不在新 ACK 里反查路由或额外读取业务 TUN。
- 测试锁：`tests/test_m0_h2229_outer_ack_source.py` 用源码负例保持 ack 保真、65535、10ms、M3 no-HOL、原重传代码未改；Rust `v4_outer_ack_ledger` 精确验证600连续 future span 合并、跨32位、代际隔离、迟滞认证才可放弃 cosmetic 旧头以及限速；Windows原 Rust MSVC ISA-L、Go TLS/GUI自测、Linux ARM64原 Go TLS/Rust double-NAT Game2/Game4/Normal TUN 是独立原生门槛。
- H2227 [双Runner真实 TCP run attempt2](https://github.com/lly8666/wbd-next/actions/runs/44682549769) 在原代码中同对网络直连约1Gbps、WBD Normal Off 4stream 约650Mbps、3秒上行约454Mbps没有 Linux 崩溃；H2227 [后一次 DERP](https://github.com/lly8666/wbd-next/actions/runs/44697076045) 直连仅约21.7Mbps，应保持基础设施限速状态。**这些都是 H2229 改动前的基线，不是改动后通过的证据。**
- 未经 H2229 同源码原生 Actions 和用户实体 Windows Npcap↔Linux WAN 的大流量/3秒上行/中继400msRTT复验，不得声明吞吐提升、断链根因已修或不会发生 HOL。后继 3 Runner H2228 relay 场景在 ACK 报告可审核后继续安排，不能把该场景冒充已测。

```feature-impact
{"kind":"updated","reason":"H2229 changes authenticated Linux/Windows outer presentation ACK behavior in Normal/Game and steady Linux TCP window only; retains M3 out-of-order TUN delivery, original outer repair, no per-record M2.","ids":["linux-raw-tun","windows-native-transport","normal-off","game-lanes"]}
```
