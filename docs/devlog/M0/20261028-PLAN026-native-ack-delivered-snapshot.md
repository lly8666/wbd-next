# PLAN026 H319｜真实已发送 ACK 的所有权与首包确认（2026-10-28）

Rust normal/off NativeOwner 的首包和 M2 发送走独立 NPF handle，TCP-looking presentation ACK 必须从认证且写入Wintun后的最高连续字节导出，且不能凭CPU内存里的最新ACK就推断旧帧已经携带同一值。

本批修正 `v4_windows_native_runtime.rs`：

- `Counters.ack` 是 RX 认证交付后提升的最高累计端点；新增单一原子 `ack_sent` 仅在 Npcap 真正返回 Accepted 的 source、M2反馈/修复或纯ACK驱动返回后更新为**该帧实际封装的ACK快照**。
- TX 无需额外的 Go timer/FFI。当当前 `ack != ack_sent` 且无其它正在发送的帧时才发一帧纯ACK；真实已捎带的ACK被合并消除，RX在刚建包后前进也不会使最后一个ACK漏发。
- NPF Uncertain/NotAttempted 和应用内的ACK progress分离：本地发送接受不是服务端数据ACK，窗口不读取未认证的TCP wire ACK，M2继续使用原唯一的authenticated receipt。

不重写 Fixed/Auto/Game Go热路径、TLS/OS/WAL，Normal/off没有旧Go fallback。本轮只修Rust原生ACK调度策略，不声称真实Win2025双端/N0/CPU已过；持续运行结果仍以各自SOURCE/Actions为准。

```feature-impact
{"kind":"updated","ids":["normal-off","windows-native-transport"],"reason":"Rust Windows Normal/off 原生TCP外观累计ACK实际发送调度修正，且两张用户功能卡同步新源行为和未验证边界，其他模式及线上 record/密钥不变。"}
```
