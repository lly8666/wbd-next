# PLAN029 H1843｜Direct TCP 反向丢段正确性修复 + 正式产品 V3 DLL ABI（两道独立门）

- **既有签名真相不篡改**：H1839 SOURCE a50f8c5 Action43595218572，物理 1MiB 297ms，Direct 连接765ms，上传18969ms，半关闭19734ms，首回包21172ms，37.172s只回917504B、38s超时；Rust内侧累计仍滞留65,536B，Tunnel UDP贯穿得到2432+回复。此观察证明双向慢，未证明具体是回程Mailbox Full引起。H1838真 WinForms+原Go配置 Action43593580875 仅配置PASS，未等于真实OS启动。
- **明确存在的丢段缺陷**：`v4_windows_native_runtime.rs` 正常 Direct TCP 回程 `SyncSender<Vec<u8>>(256)` 在 `TrySendError::Full`、原RX `WintunTx::deliver_native_direct_response` 因 `BufferTooSmall`（内核ring暂满）返回时，原逻辑直接丢弃**已正确NAT的TCP DATA、ACK、窗口更新和FIN**。UDP可在本地拥塞丢数据报，但 TCP 不能任意丢；其系统重传RTO可能将吞吐压到数秒一阶。无丢段计数/网络因果证据，不能宣告它是19s根因。
- H1843 实际修复：一个原TX线程的`NativeTcpActor.ready`有界256 FIFO，`Full`时将取出的TCP字节放回队首，绝不换新五元组、不重封 Tunnel；Direct UDP仍受独立本地丢包语义。唯一原RX/Wintun写入线程在`BufferTooSmall`时只暂存**一条**TCP回程（精确保序），ring恢复才继续；其他TCP驱动错误fail closed，UDP仍可丢。不建每流线程，不调整普通Tunnel/Wintun ring所有权，不扩大共享内存预算；仅实际ring背压的这一条保留触发5ms有限重试，闲时仍原NPF/Stop事件无限等候。每次RX真实取走Mailbox项只唤醒原TX一次，让TCP等待邮箱腾位时及时再次调度，杜绝满时反复无意义drop。
- 新Rust单元测试验证TCP与UDP分类、队首保留顺序、256容量界限；完整Win/Linux原Rust组件及源锁**唯一**签名P2用`[plan029-v3-real-p2-rebuild]`运行。新SOURCE真实性能、Tunnel UDP终态和owner Stop截至提交均**NOT_RUN**，等Action的真实收据。若仍慢，就沿已有内核窗口/ACK跟踪继续，而非盲改参数。
- **另一独立正式产品首故障 H1841**：[Action43597050204](https://github.com/lly8666/wbd-next/actions/runs/43597050204) 通过双OS编译和MTU正确配对，但真Go在`WBD_WINDOWS_CLIENT_READY`前因当次 `wbd_engine.dll` 缺`wbd_m0_win_native_v3_start`导出退出1。签名真实OS Applied/业务/Stop**未证明**。根因工作流`m0_v4_probe`特性只按旧`WBD_PLAN029_NATIVE_V3_TRIAL`=1构建，而用户产品必须关闭该试验标记。H1843将**构建和加载导出检查**条件改为试验或`WBD_PLAN029_PRODUCT_SPLIT_SCENE`任一，仍由用户`--split-enable`决定运行时，默认产品无分流，未去掉ABI/source检验。不在H1843启动重复产品signed场景；下次用不同SOURCE专门做非CI产品真实OS完整验收。
- 保留源锁`M0`治理、FakeIP async WAL/Stop和日志压缩及内存容量既有实现。PLAN029/Game4 CN、IPv6、GUI真OS Connect/Stop、P1 CPU和该真实P2性能均OPEN，未代替PLAN028限定缺口。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Fix bounded FIFO preservation of actual Direct TCP reverse packets under TX-mailbox/Wintun backpressure, with Rust tests; require exact V3 ABI for explicit product CN signed build without trial-mode runtime."}
```
