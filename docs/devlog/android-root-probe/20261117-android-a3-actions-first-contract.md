# Android A3：Actions-first 与同源 Linux 服务端 oracle（2026-11-17）

- 用户授权仅Android分支开发及Actions测试。所有软件功能先Actions，实体Android16 ARM64 KSU及热点/USB/功耗最终专项另行授权；main/M0与PR Draft状态不变。
- 入场SOURCE `d7e2e2936b283bf1ad4c02dbcec2e59c92297e61`、原Go donor `a7a82db31fe736ffedee330795a3234d358f1984`。Android Action 44035987188 的原M3 oracle、原Go/Rust ARM64 CGo和APK三Job BUILD_PASS；真Android联网NOT_RUN。
- 此次新增同SOURCE Action Job `linux-original-server-normal-off`，必须先下载并哈希核验Android ARM64原Go/Rust资产，再构建原Linux Go/Rust client/server，跑真实Linux netns标准ClientHello、认证、自动/32租约、Rust M4双向UDP及owned Stop。原pcap只在runner中用于结构审计，不上传。
- 新SOURCE尚未执行，Linux server oracle及Android KSU guest、正式双向TCP/UDP、系统DNS/App、Game/生命周期和实体热点USB均NOT_RUN；后续依据真实Actions日志记PASS/FAIL/ENV_BLOCKED，不预先宣称成功。
- 唯一下一步：观察本SOURCE Actions；Linux oracle有证据后筹备真正ARM64 KSU Actions guest/runner，完成 Android APK↔Linux server A3 真连接；不存在运行环境就ENV_BLOCKED而非提前操作实体手机。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"用户Actions-first全功能再实体终验；新增同SOURCE Linux真服务端原Go/Rust oracle，Android E2E未测。"}
```
