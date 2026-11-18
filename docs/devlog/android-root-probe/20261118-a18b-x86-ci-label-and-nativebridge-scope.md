# A18b｜x86 APK 空标签根因修复 + NativeBridge 手动独立诊断（2026-11-18）

最新分支 A18（`d0fce829`）的 [Action44235061501](https://github.com/lly8666/wbd-next/actions/runs/44235061501) x86 CI Job 在构建内部测试 APK 时失败。下载同 SOURCE 官方 Artifact 14397406202 后检查 `android-x86-ci-app/badging.txt`：虽然 APK 正常打包且应用包名正确，`application: label='' icon=''`，旧脚本严格要求 `application-label:'WBD x86 CI Root'` 因而拒绝继续；Android/KSU App→su 本轮尚未运行。

修复方法：CI-only manifest 的 android:label 改为真实 `@string/wbd_x86_ci_label`，通过 NDK SDK 内 `aapt2 compile` 对单独 `values/ci_label.xml` 建资源表再 `aapt2 link -R`，保留对 aapt dump badging 的确切 CI 标签红门。正式 ARM64 manifest/编译流程 **没有改变**；不为过门跳过应用身份验证。

此前 [Action44233506977](https://github.com/lly8666/wbd-next/actions/runs/44233506977) `android-x86-kvm-ksu-original-native` 已实际 PASS，x86 Android16 KSU 真实 UID0 shell、APK、原生 x86 Go ELF 完整 Help 成立；同 run 的旧 `android-x86-kvm-ksu-arm64-nativebridge` 在 x86 Guest 翻译 ARM64 原 Go ELF139 FAIL，与原生 x86 无关。现只在 `workflow_dispatch` 且明确 `run_legacy_nativebridge=true` 时运行旧独立诊断，普通 push 不做错误平台的日常阻塞，历史红门与旧真实证据保留、不改成 PASS。**本次提交仍不能声称普通 App 获 KSU 授权**；下一次原生 x86 证据必须从真实 Manager UI 授权及 UID0 调用得到。D2/D3 和 ARM64 实机 WBD 仍 NOT_RUN。DNS 系统接管冷许可仍 false。实验分支 / Draft PR #36；不动 main/M0。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"修复 x86 CI-only Android APK 空 application-label：显式 aapt2 string resource，保持官方 KernelSU manager 的严格 App 身份校验；旧 ARM64-on-x86 NativeBridge139 改为需显式 manual 才运行的独立历史诊断，原生 x86 每次自动运行。"}
```
