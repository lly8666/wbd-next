# A20c：D2-S1 Linux 原 ELF 动态工件执行权限 + CI 目标 App UID 修复（2026-11-18）

**证据**：[SOURCE 6eb57c57 Action #44246119539](https://github.com/lly8666/wbd-next/actions/runs/44246119539) 的 x86 Android16 KSU 原生 D1、同源码双 ABI D0、ARM64 正式 APK、原 Linux oracle 与 D2-S0 x86 原 Linux server/client/Rust 均实际 SUCCESS。新增 D2-S1 正式 RootService Job FAIL，官方 Artifact #14401438278 `receipt.json` 显示 `exit_code=126`、`phase=D2_S1_INIT`，source 双侧 SHA 校验已 PASS，**原 Linux server/TUN/Android RootService 还没启动**。下载的 D2-S0 ZIP 内原 Linux ELF 保留 Git Unix `0755`，但 `actions/download-artifact` 在新 Runner 提取文件不保留可执行权限；脚本直接执行导致 exit126。修复：必须先对两侧所有原二进制按 SOURCE/manifest/SHA256SUMS 验原始字节，再**仅对**已验证的 `wbd-v4-server`、`wbd-v4-client` 真实文件加用户可执行位（0700）并 `test -x`，不修改任何 ELF 内容、哈希或 Go/Rust 逻辑。

同时审计了 A20 的 CI-only `X86CiOriginalStartActivity`：之前它取 launcher 列表的第一 App，可能错误选中 KernelSU Manager 自己作为路由目标，**这不应发生**。现要求 Job 单独构建、按同 SOURCE 与 SHA 锁定、安装独立 `org.wbdnext.rootprobe` 普通用户 App；CI-only Activity **只能**从正式 `InstalledAppCatalog.launchable` 中挑出这一 exact package，再走正式 `SelectedAppGroup.from/stillSameGroup` 的 UID 验证，不再使用首个任意 App。任何找不到独立测试 App 的情况 fail closed。正式 ARM64 APK 不包含 CI-only Activity，也不受影响。

新 SOURCE 的 D2-S1 原 Go TUN/RAW/SYNACK/TLS 尚无新结论；**这不是通过**。仍需要在下一次 Actions 真实运行到生产 RootService 与原 Linux server。系统 DNS 两道接管冷许可 false；无 VpnService/FakeIP/新数据面；实验分支/PR #36 Draft，main/M0 均不改。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A20c 真实 D2-S1 先因 Actions artifact 下载 Linux 原 ELF 执行位丢失而 126，严格 SHA 锁定后恢复源锁 ELF 执行位；CI-only 只能选择独立 org.wbdnext.rootprobe App 作路由 UID，不再可能误路由 KSU Manager。"}
```
