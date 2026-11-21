# A16b：x86 Android 原 Rust M4 真实编译门补齐（2026-11-18）

第一轮同源码 D0 [Action44229855289](https://github.com/lly8666/wbd-next/actions/runs/44229855289) 中 `arm64-native` **FAIL**：ARM64 Rust build PASS；x86_64 Rust build 报 14 项 E0599，均为原 `ProtectedScopedOwner` Android M4 的部分方法还被 `aarch64` cfg 隐藏（包括真实 raw TX/RX/TUN、Normal/off 帧 budget 与 Stop 依赖的 firstsend identity）。这不是成功证据。本次只让**相同原方法**在 Android x86_64 中参与编译，不修改 TLS、AEAD、PN、M4 数据面、加密算法或 Stop 语义；禁用 DNS takeover 安全门保持 false。

等待新 SOURCE 的真实双 ABI Actions。x86_64 Android 正式客户端编译及 App→KSU/TLS/M4/Stop 不宣称通过。历史 FAIL 仍保留。本次仅实验分支，不动 main/M0。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A16 D0 首轮 x86 Rust 编译发现 14 项 E0599：原 Rust ProtectedScopedOwner Android M4 方法漏加 x86 cfg；仅解除同一方法的架构编译限定，保留原数据/安全逻辑。"}
```
