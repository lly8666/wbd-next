# A20d｜原 Linux 服务端真 TUN PASS；Android 私有凭据阶段脚本修正（2026-11-18）

[SOURCE `cff0129c6d789aa0f059b8f0e4c51ffc23456a1c` Actions #44249969581](https://github.com/lly8666/wbd-next/actions/runs/44249969581) 真验证：D0 同源 Android ARM64/x86 原 Go+Rust ELF、正式 ARM64 签名 APK、D1 x86 Android16 KernelSU App UID→su/PhysicalNetwork、D2-S0 原 Linux x86 server/client/Rust 构建均 SUCCESS。D2-S1 在原 Linux 原始 server ELF 源 SHA 核验且恢复执行权限后，**真正由原 Go server 在 Runner 内创建内核 TUN `wbdvs4`，官方独立收据 `linux_real_original_server=PASS`**。这与先前只执行 --help 不同。

仍 FAIL：D2-S1 在 `D2_S1_APP_PRIVATE_SECRETS` 以 rc31 退出；原正式 Android RootClientService 此时尚未 START/TUN/RAW，TLS/M4 均 NOT_PROVEN。旧脚本把长 `case/$(stat ...)/$uid` 连多层 shell 引号直接传给 `adb shell su -c`，Android UID 解析/私有目录建置无阶段细分，**不能凭退出码推断具体问题**。本次更正为有 source 文件的 CI-only `x86-d2-install-credentials-android.sh`：KSU 已真实授权的 root 从 D1 创建的 0700 root-owned 目录运行，同 SHA256 核验无密钥脚本；固定检查真实 uid0、App files 路径、UID 范围、三个秘钥文件与 symlink、最终 app UID 和0600 ownership/readback；每个失败单独固定码（30–42），不在 App Intent、stdout 或 Github Artifact 中泄露密码、证书私钥、路由密钥、IP/UID。成功只记录单枚举 `D2_CI_APP_PRIVATE_SECRET_STAGING_PASS`。密钥仍临时作业内随机生成。

为避免 root 创建错误 SELinux 标签，原 **CI-only** `X86CiAppSuActivity` 在 D1 的普通 App UID、正式 NativePayload.stage 验签之后调用自身 `getFilesDir()` 先建私有 files（这一步不在 ARM64 release）。正式 `RootClientService`、原 Go/Rust M4、安全 DNS 冷许可、独立目标 `org.wbdnext.rootprobe` UID 路由均不改。

**下一次 Actions 还没有跑出新 SOURCE 的结果**；真实 Android RootService TUN/RAW/SYNACK/TLS/租约/M4/数据/Stop 未通过，严格依 receipt。只动实验分支 Draft PR #36，main/M0 不变。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A20d SOURCEcff0129c D2-S1 原 Linux server 真实 TUN PASS 但 Android App 私有密钥准备 rc31；修复嵌套 adb su shell 为 source 锁定 KSU Android 单脚本、定码 UID/SELinux/App 0600 检验，普通 App 创建 files Dir，真实 RootService/TLS/M4 未宣称通过。"}
```
