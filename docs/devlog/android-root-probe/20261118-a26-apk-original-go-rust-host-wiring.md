# A26｜正式 ARM64 APK 接线原 Go/Rust，Actions Host-only

最新用户指令：**不做模拟网卡绑定测试、不做真机测试**。原实测 [A25 #44285914998](https://github.com/lly8666/wbd-next/actions/runs/44285914998) 已确认 Android16 KSU/TUN/RAW/SYN sendto 与原 Linux server 启动，但宿主 TAP RX 不可验证，原 Linux RAW SYNACK/TLS/M4 E2E NOT_PROVEN；保留该历史事实。

**本次施工（新 SOURCE 尚待同源 Actions 收据）**：原 RootService 真正传给原 Go `exec` 的 CLI 参数提为纯 Java `OriginalGoCommandArgs`，Host JVM 对原生产类执行 Normal/off、自动 /32、外层1460B、原 Android Network handle、IPv4/DNS peer、TLS CA、app-private secret paths、单/多/全 App UID 及互斥/无效参数用例；没有改变原标准 TLS、认证、Rust M4，凭据仍不出现在 argv。Actions 在原正式 ARM64 APK **已签名**后，核对实际 classes.dex 的生产类、同源原 Go ELF / Rust `.so` SHA、Bionic 183、原 Go 对 Rust DT_NEEDED、源锁和原 Go CLI 注册 flags；结果为新增 `wiring-receipt.json` 并随 APK artifact 上传。

三条 x86 guest/KSU/TAP job 默认禁跑，只有未来用户另行明确 `workflow_dispatch` 才触发；本轮仅原双 ABI native/ARM64签名 APK/Host Go-Rust/Linux oracle。不触碰模拟网卡、真机、远端 Linux/Windows 个人服务器、main/M0；Draft PR #36 不合并。**收据仅表示 BUILD/WIRING PASS，不是 Android↔Linux SYNACK、TLS租约、Rust M4 App TCP/UDP 或 Stop；本批设备/网络这些均 NOT_RUN。**

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"依用户最新范围直接完成正式ARM64 APK到原Go/Rust CLI/资产接线与Actions host可验证合同，显式关闭自动x86 guest/TAP执行，不做模拟网卡或真机测试。"}
```
