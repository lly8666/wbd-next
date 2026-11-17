# Android16 x86_64 KVM + KSU3.3.1 + ARM64 Native Bridge 正式产品环境恢复（2026-11-17）

**用户优先级**：先将历史成功Android16 KSU模拟器跑通，验证过去源码开发的真正ARM64原Go/Rust客户端，再继续功能。唯一工作分支`experiment/android-temp-root-probe`，Draft PR #36；不动main/M0/registry/cursor。开工远端HEAD `bcc04a5259c22ff8032b7a4348c4fc229c6c361a`，main当时 `417e0e069659ff392d53ce0343c383fee7ae2915`；没有远端未提交worktree可读，不声称查过未提交代码。

## 历史真实依据与新的事实边界

[旧KSU Action43986417528](https://github.com/lly8666/wbd-next/actions/runs/43986417528) 真实PASS：固定 Google Play Android16 API36 **x86_64** AVD，GitHub-hosted Ubuntu24.04 x86_64 **/dev/kvm**，`leemikepop/avd-kernelsu-x86_64` 固定提交`c6c6057d807976d3dee6dbe9197189654cbd1a2a`，KernelSU3.3.1 manager+CI ramdisk，真实普通targetSdk37 App经Manager受控授权、独立root进程，以及旧**x86_64 Rust probe**的TUN/RAW/UID/私有DNS真实内核权限。**没有可信执行原ARM64 Go程序或完整WBD业务的证据**。历史[ARM64 KVM Action44108696248](https://github.com/lly8666/wbd-next/actions/runs/44108696248) 虽Host/ARM64 native build/Linux TLS oracle 10/10 PASS，但ARM64 hosted /dev/kvm 不可用，Android guest P2/P3 NOT_RUN。

## 本批产品验证操作

- 修改 `android-root-product-a1.yml` 增加`android-x86-kvm-ksu-arm64-nativebridge`独立 job，在原Go/Rust ARM64+签名APK同SOURCE构建后下载**同一 GitHub Actions run/hash**的两个产物；验证外层APK资产字节和本SOURCE真实AArch64 ELF machine=183，不能使用旧x86 probes顶替。
- 重用上述固定KSU AVD安装/ramdisk、双次冷启动和Android16 SELinux Enforcing；测试真实 `adb device`、PackageManager、KernelSU `su -c id`（仅shell root），安装正式`org.wbdnext.rootclient` APK并真实启动Activity。采集guest CPU ABI/NativeBridge属性/系统库/内核binfmt信息，并真的将**原Go ARM64 ELF + Rust ARM64 shared lib**推入guest由KSU下`execve --help`，任何`Exec format error`、缺库或ABI不支持均非PASS；收集同SOURCE JSON receipt、app/ADB/guest日志。
- 历史`android-root-ksu.yml`路径变更也触发一次真实旧probe KSU运行（x86_64旧probe，仅独立对照），不得冒充原ARM64产品。实验环境对KernelSU Shell root vs 普通App授权的区别及实际业务 NOT_RUN 原样记录。未知的 Native Bridge 是否支持独立ARM64 ELF，不因声明中有arm64-v8a就推断可运行。
- 本批测试启动前状态**NOT_RUN**；真实Android16原ARM64 FakeTCP/TLS/lease/Rust M4/TUN/DNS App→Linux E2E未执行，无同源环境证明前不会把旧Linux原协议oracle充当Android业务证据。真实手机KSU仍需要新授权。

**下一步**：看完 x86_64 KVM/KSU/NativeBridge 的真实Actions日志与Bionic ELF启动返回；支持则补同SOURCE Android↔Linux原服务端 Normal/off DNS/UID/Stop真实测试，不支持则保留明确阻断证据、修复实际运行环境（不能把JNI翻译误当作arm64原生进程exec）；之后继续CN8503/TCP53/Resolver业务。不要为了刷绿引入x86版正式客户端或假TLS。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"按用户最新优先级复用历史x86_64 KVM+KernelSU AVD验证同源码原ARM64 Go/Rust产品NativeBridge真实execve和签名APK安装/Activity，历史probe PASS与产品Android E2E严格分开。"}
```

## 首次同SOURCE Android KSU 运行结果与时序修复

正式产品源码 `ee31c0e46df5fb48df3a47dce525216e53949833` 的旧 [KSU Action44113392897](https://github.com/lly8666/wbd-next/actions/runs/44113392897) **SUCCESS**：重跑历史真实Android16 API36 x86_64 KVM/KSU3.3.1，普通App→Manager授权Root，旧x86诊断进程真实TUN/RAW/UID/UDP53/TCP/私有TLS、SIGKILL/Stop等PASS。该历史**x86诊断**不是正式WBD的ARM64 Go/Rust TLS业务PASS。

同SOURCE新的 [ARM64产品KSU NativeBridge Action44113392855](https://github.com/lly8666/wbd-next/actions/runs/44113392855) **FAIL**：artifact 14342865202确认同SHA原Go/Rust ARM64 ELF与签名APK字节一致，两次Android16 KVM guest真启动/ADB device、SELinux Enforcing均PASS，但第二次冷启动后Manager需重装、`ksu-shell-id.txt`出现`/system/bin/sh: su: inaccessible or not found`(exit127)，执行NativeBridge前就失败。原旧KSU同SHA artifact里`fixture-shell-su.txt`记录`uid=0(root) context=u:r:ksu:s0`，且其历史脚本在重装Manager后显式`am start -n me.weishu.kernelsu/me.weishu.kernelsu.ui.MainActivity`。本次源锁修复该二次Manager启动并限定18次2秒的真实`su`readiness；没有修改产品 Go/Rust、协议或Root权限假信号。下一SOURCE未跑前NativeBridge及正式App Root↔Linux真业务均**NOT_RUN**。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"旧KSU普通App真实环境同源PASS，ARM64正式产物首轮双启动后缺Manager二次激活su导致FAIL；修复真实Manager第二次开机初始化并保留原FAIL。"}
```
