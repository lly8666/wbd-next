# PLAN029 H1841｜P2已定位到内侧TCP64KiB回程背压；产品入口首次失败属MTU场景参数错配

- **签名P2真实结果（SRC a50f8c5）**：[H1839 Action43595218572](https://github.com/lly8666/wbd-next/actions/runs/43595218572) Windows2025 Npcap/Wintun＋原Go/Rust和Ubuntu WSL2。正常物理TCP 1MiB 297ms（上传281ms）；FakeIP Direct TCP 连接0.765s，上传1MiB至约19.734s、半关闭，首回包至21.172s，37.172s仅收到917504/1048576，38s主动上限触发FAIL。每16KiB有人为4ms睡眠，单路正常约0.3s不可能解释30+秒。原本H1837没有阶段记录；H1839诊断确认**持续慢速前进**而非单个等待锁完全死死卡住。没有完整响应、p99和Stop验收，不能把P2记PASS。
- Linux物理Guest真实第二连接读到了完整1048576、正确SHA/EOF，确实`sendall+shutdown`了完整回程。Rust单冷诊断1Hz最后值：含先前32KiB流的`inner_read=outer_write=outer_read=1081344`，但`inner_write=1015808`，差精确65536，`buffered=65536`、`resident=98304`，流仍active。**可证队列不会无限增大，且当时Windows内侧TCP是限制腿**；不能据此单独证明Windows ACK/窗口/超时重传何者主因。Tunnel小UDP交付进度连续至至少2432条，但失败时未产出完整唯一交付/p99/最长空洞。客户端finally原 Rust+WAL Stop日志PASS，P2场景`stop=NOT_RUN`。
- 后续实质施工应以原生Wintun方向ACK速率、Windows内侧TCP窗口/重传和回写进度直接量化；禁止再次盲改量子、Nagle、扩大64KiB队列或重起相同无差异P2。必要时做**同VM同SOURCE顺序少量无/有Tunnel负载**，才有证据归因跨流HOL或独立TCP代理慢。
- **H1840产品入口第一失败**：[Action43595752905](https://github.com/lly8666/wbd-next/actions/runs/43595752905) 的Go/Win+Linux Rust构建成功，但独立真实非CI产品Normal scene在Python顶层`configured_native_test_mtu()`被拒绝，**未进入原Go应用/OS Apply**。本批新marker把外层源选择为`default1460`，却漏了对应`WBD_WL_TUN_MTU=1460`，保留旧1400；其精确一致性保护正确拒绝，不是产品分流或Windows内核故障。H1841只给该新场景增加同一TUN参数1460、原始outer=default1460不变，另给`tests/test_m0_native_ci_scope.py`补双选择器同marker且值一致测试，防止第二次漏项。绝不修改`configured_native_test_mtu()`或重构OS。
- H1841只带`[plan029-real-product-cn]`标记，再触发独立真实Normal非CI入口一次；**不带P2 marker**，不重派H1839失败阶段。实际GITHUB_ACTIONS=false、V3 trial=0的Windows原Go冷source、Signed OS/Wintun、Direct/Tunnel双出口和真实Stop**NOT_RUN直到新Action完成**。H1838真实WinForms/Go配置PASS；用户直接点击GUI Connect/Stop、Game4 CN、IPv6、P1、slowfsync还OPEN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Record exact H1839 signed 1MiB relay backpressure and H1840 pre-network MTU-selector first failure; source-lock single nonCI product retest with matching default1460/1460 scenario and a static regression guard."}
```
