# Android Root Actions-first 等价性审查（2026-11-17）

范围：`experiment/android-temp-root-probe`；修改长期方案/永久提示词，不改 main、M0、原生产品或实体设备。

## 旧测试没有证明 adb root 等于 KSU su

[真实KSU Action43986417528](https://github.com/lly8666/wbd-next/actions/runs/43986417528) SOURCE `09a6a7e5f8aef5c3b38abb262655561ca89e5f9a`、Job `real-ksu` PASS、artifact `14286390166`。`.github/workflows/android-root-ksu.yml` 使用 Android16 API36 **x86_64** AVD/KernelSU3.3.1；`ksu-boot-and-test.sh` 特别不执行 `adb root`，普通 targetSdk37 App `org.wbdnext.rootprobe` 经真实 Manager 对自身包名授权 `su`，原生执行返回 UID0、`CapEff=000001ffffffffff`、`u:r:ksu:s0`，全局 SELinux Enforcing。`appflow-case.sh` 真实普通App UDP 经受控 UID→TUN 往返、`mainstream-case.sh` 另证 app TCP/DNS/NetD绑定与 Android系统 TLS 到 host、TUN/RAW/route/owned恢复，全部只是这一侧能力/诊断应用；DNS6/6位于私有 namespace，未跑正式 WBD/TLS服务器。

`adb` 在 Action 中是传输/读回工具，`adb shell su -c` 仍调用 KSU `su`，**不等于 `adb root`**。没有相同 SOURCE/操作的 `adb root` 与普通 App KSU `su` 成对 A/B 测量。因此 `KSU_DIAGNOSTIC_SCOPED_PASS`、`ADB_ROOT_EQUIVALENCE=NOT_PROVEN`、`ANDROID_ARM64_WBD_APP_E2E=NOT_RUN`；不能援引 UID0 推断能力/SELinux/Profile/NETD等价。KernelSU Root Profile 支持修改 su 后 UID/GID/groups/Capabilities/SELinux 域。

## 最新已核证的事实

[Action44041601960](https://github.com/lly8666/wbd-next/actions/runs/44041601960) SOURCE `bb30ed3d864460dc22af67aaade1d17c47182c58`：原ARM64 Bionic Go/Rust与Root APK BUILD_PASS，同SOURCE Linux原 Go/Rust client↔server真实TLS/自动租约/双向UDP/Stop LINUX_ORACLE_PASS，**Android业务未运行**。
[Action44042235770](https://github.com/lly8666/wbd-next/actions/runs/44042235770) SOURCE `37f1b8abc77cc878d245b5b6dd1995c435ba259e`：native/M3/APK/Linux oracle四Job PASS，macOS ARM64 Android16 AOSP emulator QEMU主线程/CPU卡死、ADB一直无设备、超时，guest项目 ENV_BLOCKED / NOT_RUN，不是WBD产品故障。

## 新分层合同（权威细则见方案 `8.0）

P0 Bionic BUILD；P1 同源Linux真实协议；P2 Android16 **ARM64 userdebug真guest**，`adb root` 只用于正式原 Bionic ELF 的原生系统/网络协议测试，不能代表 App su；P3 **正式签名APK**从普通App UID真实 `ProcessBuilder("su","-c",...)` 经受控CI Root provider 获权限，在 Android Framework/netd/Network handle/TUN/RAW与原Linux server 做真协议/双向TCP+UDP/Stop，才可称 Android App Root E2E；提供者可不叫KSU，但只对已测操作行为等价；P4软件A/B/C/D场景Actions通过；P5实体 ARM64 KernelSU（单独授权）对真实Root UI、SELinux/能力、热点USB/offload/CLAT/功耗终验。

P2/P3两侧比较必读原 App UID/上下文、worker UID/GID/groups/CapEff/CapBnd/NoNewPrivs/SELinux、网络namespace、真实Network handle/`android_setsocknetwork`/SO_MARK/RAW/TUN/UID FIB、真实TLS认证租约/业务/Stop readback，未配对均 NOT_PROVEN。优先检验可用 ARM64 Linux KVM runner / ARM64 Cuttlefish userdebug 镜像/官方host包，当前未有已验证的runner；无则 ENV_BLOCKED，不延长macOS模拟器超时或改x86目标。最终实体设备必须晚于软件Actions测试完成。

**唯一下一步**：ARM64 KVM/Cuttlefish轻量环境准入→P2原Bionic真协议→P3普通App受控su真授权；不冒充 E2E。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"用户选择Actions行为等价方案：旧KSU只证明单侧App su能力，未测adb-root对照；改长期方案/提示词为P2 ARM64 native与P3正式App su分层，KSU实体最后终验。"}
```
