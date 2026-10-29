# M0 H352｜PLAN026 单批源码：双端 Health 真实活性、Windows 原生 Rust Auto

2026-10-29；任务 `R0-M0-PLAN026-WIN-RUST-NATIVE-IO`，直接在 main 保持原主写租约。**本次为实际代码候选，未在本提交前手动发起产品矩阵；正式功能/网络/CPU、完整GameNative及FIN Dormant均不得预报 PASS。**

## 真实代码事实与低成本约束

- `v4_embedded_go.rs` 修正旧新Health逻辑在没有FEC feature时错误引用 `feedback_queued/native_health` 的 cfg 漏口（上一SOURCE原 Go Linux编译失败）。仅真实 original-Go TLS `arm_public_original_m2_feedback` 的 Linux 双端 worker 安装 HealthClock。真实 M3 unique-PN+AEAD收包后，RX仅在每次 `recvmmsg` 批量末发布一次认证活性/业务/对端idle到原生原子快照；TX仍是唯一可变时钟所有者，吸收该证据；无Go逐包回调、无RX每包锁。90s 后无**任何认证** peer activity 的 TX worker 才发真实 native Stop信号，不因两端payload idle而休眠。现有15s typed WBC4 Heartbeat/Receipt同包发送、`sendmmsg` copied-prefix证据不变，失败重试不制造已发送。对端合法 FIN 才能走独立 DORMANT，尚未接入 FIN 事件，不能把90s断线当休眠。
- `v4_windows_native_runtime.rs` 只在真正 Npcap successful copied business 更新local payload idle（不是已封包、stage或本地TCP ACK），并对90s无认证对端事实报真实worker error。15s Health合入原M2单条WBC4控制仍在同两Rust worker；无新轮询线程。
- **Windows NativeAuto**：新增 `v4_windows_rust_auto.rs`，在现有NativeAttachV2的唯一Rust TX worker每2s认证读回原 `WindowsOriginalM2.auto_quality[30]` 与真实FixedStream当前封块actual-k。严格>=512快/慢成熟源、90%覆盖、<=20%不确定、0.90..1.05的K对齐、真实reverse ACK/lag、HOST_CAPACITY拒绝；两个真VALID窗口升档；降档>=30s持续可信低损/5个有效窗口/>=4096源包/一次一级。No DATA=UNKNOWN，FEC Game从未调用Auto。仅通过同一 `fixed_change_revision_entry` 真正quiescent后commit请求、失败不假Applied；M2成熟copied parity/source/reverse回执组成独立Applied读回。新增3种回放：真实清洁->一档下降、真正丢失快升、host/drop/actual-k缺失冻结；保存原Go FecV2Step用于Linux冷控制，不再由Windows Native Go控制goroutine做相同Grade。Go Native只保留cold开始策略、人工调档与真实Rust读回；版本化V2保留192B V1 ABI，使用原reserved位传aggressive，绝不让Game Auto。只在Auto已有mode 2内部启用；Fixed模式没有额外grade锁。
- 同批更新当前两份原Go装配manifest的精确真实git blob；功能卡只记候选，不借用任何旧run为本次PASS；原始业务、OS/WAL、TLS、FEC2 RS16、Wintun/NPF和Stop owner没有替换。

## 尚未完成（不能掩饰为全项目写齐）

1. Windows Game2/Game4多原始NpCap连接真正交给一个共享Rust NativeAttachV3的两个worker（当前产品Game路径仍Go逐包）；需保留各lane真正TLS、GameFec固定/off、真实prefix复制与Stop。
2. 双端可配置Keepalive/dead/idle与GUI/CLI的有效读回、服务端真实 FIN + business-idle DORMANT/Wake状态机；当前默认15s/90s不等于休眠完成。Linux M2 Auto最终迁至Rust仍需源作用域确认。
3. V2 exact-source 固定/游戏场景、Auto最后连Keepalive/90s死链/FIN不误休眠、同机A/B、CPU/p99/物理证据。先完成真正代码和编译回归，再固定->游戏->Auto最后，不接受凭样例结果宣告质量。

```feature-impact
{"kind":"updated","ids":["fec-auto","idle-rotation-keepalive","windows-native-transport","linux-raw-tun"],"reason":"本批代码真实变更Windows Native Rust Auto 2s M2 actor与Go冷配置、双端原生认证Health活性/90s断线、Window NPF copied业务空闲；Game和FIN Dormant等仍未接线，所有新网络资格NOT_RUN。"}
```
