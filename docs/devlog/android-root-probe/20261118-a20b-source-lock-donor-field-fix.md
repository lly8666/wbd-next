# A20b｜D2-S1 首个真实 Actions 失败：原 Linux manifest donor 字段误读（2026-11-18）

[SOURCE `6ed4d77468dd09807d4a8458ff6c0903b08111d2` Actions #44245057856](https://github.com/lly8666/wbd-next/actions/runs/44245057856)：同源 ARM64/x86 D0、正式 ARM64 APK、原 Linux host oracle、x86 原 Linux D2-S0 server/client/Rust、x86 Android16 KSU D1 普通 App Root/Network 均实际 SUCCESS。新 `android-x86-kvm-ksu-original-d2-s1` Job FAIL：进入原 Linux server/Android 双侧 source lock Python 前半段时 `KeyError: 'go_donor'`。D2-S0 清单键实际为 `donor_go`，与 Android 原产品 manifest 的 `donor_go` 一致。错误是 CI 收据字段名拼写，**未启动真实服务端和 Android 正式 RootService**，因此没有新的 TLS、TUN/RAW 或 Stop 结论。

本次只把 D2-S1 校验更正为 `l["donor_go"]==a["donor_go"]==固定 donor SHA`，没有放宽来源校验、TLS 认证、Native 逻辑或 UID 限制。下个 SOURCE Actions 实际测试出结果前，D2-S1 依旧 NOT_PROVEN；Android 原 TLS/M4 双向业务和 D3 owned Stop 仍 NOT_RUN。只有实验分支 PR #36 Draft，main/M0 不变，系统 DNS 接管冷许可仍 false。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A20 真 CI 源锁脚本因 D2-S0 JSON donor_go 被误读 go_donor 而 FAIL，修复字段、保留固定 donor SHA/双产物哈希红门；未宣称 Android RootService TUN/RAW/TLS 已运行。"}
```
