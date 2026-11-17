# A1 实施切片｜Android/Bionic 真产品装配构建及薄FD边界

本切片修改 **Android product** 的编译/链接闸门，不新增探针测试或合成业务，不修改现有Linux入口或M0算法。原Go donor固定 `a7a82db31fe736ffedee330795a3234d358f1984`，复用共享源锁安装器，Rust `wbd-engine` 采用 `m0_v4_probe,m0_v4_embedded_go` 首次Normal/off编译（本包不启ISA-L）。NDK同时验证 Android arm64、x86_64 的真实Bionic ifreq/TUN/socket ABI与16KiB ELF PT_LOAD alignment，Go以 `GOOS=android CGO_ENABLED=1` 编译原Go产品 `cmd/wbd-v4-client`，不复制Linux代码形成新分叉。

Rust `wbd-platform::android_root_io` 是 Android-only owned TUN FD / exact Android Network 物理socket绑定 API，冷阶段验证TUN模式和接口，禁止未经绑定回退、全局mark和整个root UID直连；不承担认证/数据循环。旧 `linux_raw_carrier` 不被错误启为Bionic。这些API**尚未接到**共享 Rust M4 handler，更未发生TLS、lease、正常业务交付。首次Action在提交后才会提供准确 `SOURCE` 与 BUILD_PASS/FAIL，之前维持 `IMPLEMENTED_NOT_TESTED`。

下一步：读取 A1 Action 首个真实失败/成功，按真实构建错误最小修复；通过后 A2 实际与原Go冷控制接线，再在KSU Action真正连接Linux标准WBD服务器。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A1新增Android Bionic 64bit布局/底层root TUN和物理Network绑定源码，接入原Go/Rust source-locked交叉构建；产品链路严格未测。"}
```
