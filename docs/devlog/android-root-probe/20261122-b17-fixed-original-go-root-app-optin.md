# B17｜Android Root App 显式 Fixed 原 Go TLS/原 Rust M4 入场

基线 SOURCE `75aef424a4cd960787a55a7611d47cdd81f0f82b`（B16 真实内层 IP 分片/PMTU）。真机受限，本轮优先闭合可用功能链，默认 Normal/off 保持不变。

- 原 Android Go `--mode fec-fixed` 走标准 FakeTCP/TLS、认证 auto /32 后，同一 `V4LinuxClientProduct.ConnectAuthenticatedPeer` 进入原 Rust feature7；经现成 Go `v4ConfigureProductFec` PENDING→Bionic FEC2 M4源/Parity/原M3 AEAD/PN→原 RAW/TUN 与 native Quality。仅解除针对 Fixed 的旧 Android 模式阻断，Auto、Game、outer-repair、重叠 generation 仍未开放。
- Fixed 本身使用单独的原 FrameBudget，跳过 Android 只供 Normal/off 的 startup-padding ABI；Fixed 要求 padding off。不为 Fixed 每500ms开启重复 Go Auto采样 goroutine，真实 Quality/APPLIED 在 Rust 继续推进，Go按需原 native Readback。
- App 增加显式 Normal/fec-fixed 下拉、profile0..6选择（默认Normal和profile1），Activity→Service→原 `OriginalGoCommandArgs` 最终落到真实Go `--mode fec-fixed --fec-profile 0..6`。Java legacy overload 保留 Normal，测试新增 profile0/6、拒绝Auto/Game/越界profile/Fixed padding。
- 生产源编译/签名APK/原Linux Oracle以本SOURCE Action定论；没有授权新设备/服务器实验。本轮是**可选产品接线**，Android实体固定模式的数据、双端应用TCP/UDP逐字节交付/吞吐/CPU均 NOT_RUN。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B17 Root App explicit native Fixed through original Go TLS and Rust FEC2 pending/quality/M4; Normal remains default, Auto/Game unavailable"}
```
