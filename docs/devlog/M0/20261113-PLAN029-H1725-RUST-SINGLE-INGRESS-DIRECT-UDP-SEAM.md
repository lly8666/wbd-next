# PLAN029 H1725｜首次接入原Rust NativeOwner的同一Wintun数据循环（非产品v3资格）

- `v4_windows_native_runtime` 的原唯一 Rust TX WintunReader 在每个最多8输入RX quantum先调用 `NativeSplitWorker`；Tunnel进入原有M3/AEAD/FEC封装，已判定物理Direct UDP由同 Rust TX 绑定 source+ifindex 异步WinSock actor发送，不能被错误塞进Tunnel。一个 quantum 无论全部Direct也不会无限循环。
- Rust TX 在已有原线程中最多8个ready UDP回包，完整L3组装后经`sync_channel(256)`非阻塞寄给**原唯一Rust RX Wintun TX worker**，通知已有Event；只有RX最终Allocate/Send，ring不跨DNS/connect等候。无第二Wintun读者、无Go逐包泵；Direct socket就绪检查每轮最多16个/10ms，空闲Tunnel路径保持原行为。满/发送失败仅UDP局部drop，不堵Tunnel。
- 私有`m0_v4_probe`冷V3配置一次复制CIDRs及domain规则到Rust内存，仅原认证owner能启动；Direct TCP及两方向DNS尚缺产品owned实现时本入口明确拒绝，不允许产品Ready。原公开V2逻辑/旧PASS不动，当前生产双出口/D1–D5/P1–P2仍**NOT_RUN**。
- 新Windows/Linux Rust组件单SOURCE测试由同一个现有并行Action触发，尚待结果，不宣称网络PASS。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Wire a probe-scoped Direct UDP socket/return mailbox into the original Rust NativeOwner single Wintun ingress, fail-closed for unwired TCP/DNS; product dual-exit remains NOT_RUN"}
```
