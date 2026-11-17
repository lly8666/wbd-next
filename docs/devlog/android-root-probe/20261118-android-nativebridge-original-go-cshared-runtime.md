# Android16 KVM KSU NativeBridge：真正原Go客户端经NDK→Go c-shared运行时入场（2026-11-18）

开工只读远端 HEAD `4c17720bab333a317ab7d7125d337b3c01c4bfe8`，main当时 `a91b158ace18880db1a3dce078cc71ab912c4102`，Draft PR #36；仅修改 `experiment/android-temp-root-probe`，无远端工作树可供检查未提交文件，不动M0/main/registry/cursor。旧失败证据保留。

## 上轮真实Android结果

[Actions #44131422225](https://github.com/lly8666/wbd-next/actions/runs/44131422225) SOURCE `4c17720...` 最终 **10/11 Jobs PASS，完整Action FAIL**：原Go/Rust Android Bionic ARM64 ELF、签名APK、Host DNS/M3/M4和同SOURCE Linux真TLS/租约/双向UDP/Stop oracle PASS；第11项真实 Android16 x86_64 KVM+KSU3.3.1/ARM64 libndk_translation 环境为：
- NDK ARM64二进制真执行 exit0，原Rust `libwbd_engine.so` 真 dlopen+dlsym exit0；
- Go1.23.12 原 c-shared `//export` 调用会执行不受翻译器支持的 `MRS MIDR_EL1`，SIGILL132。将固定Go1.23.12 GOROOT**复制到测试隔离目录**，仅跳过Android MIDR探测后，Go c-shared实际导出函数调用 exit0，确认Go runtime可从NDK入口启动。
- 即便隔离MIDR，直接执行纯Go ELF仍SIGSEGV139；与正式APK同SHA的原Go/Rust ELF直接 `execve --help` 亦SIGSEGV139。原Root APK真实Activity启动和PID PASS，但完整正式Android WBD会话/TLS/租约/TUN/系统DNS/Stop **NOT_RUN**。
- 原日志、原artifacts [14351110896](https://github.com/lly8666/wbd-next/actions/runs/44131422225/artifacts/14351110896)永久不覆写。不能从c-shared单函数成功断言真实Go CLI、WBD数据面或直接二进制可用。

## 本批仅一条可判真的产品运行时入场

- `r0/go_overlay/cmd/wbd-v4-client/ksu_cshared_entry_android.go` 是**测试专用**条件编译 `wbd_ksu_cshared_test`：直接调用**原封未修改** `v4productcli.Run("client", []string{"--help"})`，必须观察到真实Go标准`flag.ErrHelp`。没有假TLS、假server、手工账户、额外JNI/per-packet或侧车Go协议替代实现。
- 构建仍沿原Go donor+共享Rust同SHA/source-lock装配，新增诊断`-buildmode=c-shared`；只对此库使用**复制且仅改一次MIDR探测**的Go1.23.12工具链。正式APK内原Go ARM64 ELF、Rust共享库和TLS/认证/租约/PN/AEAD/Stop代码不变。Rust `DT_NEEDED` 与仅相对 `$ORIGIN` `DT_RUNPATH` 必须实测，测试导出符号不能混入正式客户端 ELF 或签名APK。
- 以已有真正通过的 AArch64 NDK NativeBridge launcher `dlopen` 测试c-shared全量真实客户端库、`dlsym(WBD_AndroidRootOriginalGoHelp)`、实际调用原`Run`并检查原Go真实CLI flag 文本和Go返回标记。独立记录退出码/Android crash；即使此诊断 PASS，只说明**原Go CLI冷启动和共享Rust载入**，不代表普通App su、内核RAW/TUN、DNS或Android↔Linux原业务通过；正式ARM64 Go ELF direct exec红门仍保持。
- 同SOURCE要求原10项产品Jobs + 新KSU Android guest Job全量Actions，判错绝不篡改旧FAIL；不使用x86 Android正式客户端，不部署实体设备。新的SOURCE提交之前状态 **NOT_RUN**。

通过该真实原Go CLI入口后，才按实际运行限制推进 original Go认证租约/RAW/TUN与同源Linux server的Normal/off真实业务，继续保持DNS系统接管冷关闭。若c-shared也FAIL，优先按真实Go/NDK动态链接或信号日志定位，不增加极端探针矩阵。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"承接KSU真NativeBridge Go c-shared隔离MIDR后PASS但原ARM64 Go ELF139阻断，新增同源码原Go Run(client,--help)测试专用共享库及NDK实际调用/ELF与APK源锁，正式客户端不变。"}
```

## 真实Android原Go共享入口失败与最小兼容路径（同源码记录）

原入口 SOURCE `0c550361dbdfa5c6ddc58aa28e7161b6a9aa7b2a` 的 [完整 Action #44136737310](https://github.com/lly8666/wbd-next/actions/runs/44136737310) **10/11 Jobs PASS、总 FAIL**。原Go/Rust ARM64完整链接/符号/SHA、签名Root APK、Host M3/M4/DNS/CN8503、Linux原TLS/租约/UDP/Stop oracle均PASS；x86_64 KVM Android16 KSU第11项FAIL，原始[artifact 14352851799](https://github.com/lly8666/wbd-next/actions/runs/44136737310/artifacts/14352851799)保留。

真实Android16结果：KSU uid0、原NDK ARM64 exit0、原Rust `libwbd_engine.so` dlopen exit0、隔离Go1.23标准库MIDR后的常数函数c-shared exit0；**本SOURCE新增原Go完整客户端c-shared的真实NDK `dlopen` 与 `dlsym`成功，但导出原 `v4productcli.Run(client,--help)` 调用前 SIGILL exit132**，没有打印原Go flag/help完成标记。此次tombstone经 `logcat -b crash` 精确指向 `/data/local/tmp/libwbd-original-go-cshared-midr.so (github.com/klauspost/cpuid/v2.getMidr.abi0+0)`，NativeBridge `UndefinedInsnThunk` 对应 `MRS MIDR_EL1` 指令 `0xd5380000`，与之前已隔离的 Go stdlib `internal/cpu.getMIDR` 并非同一个检测模块。正式原Go可执行文件 `--help` 仍SIGSEGV139，Root APK Activity PID仍PASS，Android WBD业务全 NOT_RUN。

下一 SOURCE 仅将**测试专用的原Go c-shared**编译tags增加上游CPU探测库标准 `noasm` 后端，避免 `klauspost/cpuid/v2` 的 MIDR_EL1 指令；沿用隔离Go1.23 GOROOT，对正式 `wbd-v4-client-arm64`、签名APK、Go标准TLS/凭据与 Rust AEAD/PN/Stop **零修改**。CPU探测asm禁用可能改变测试库的性能/CPU特性报告，绝不拿它作为原生ARM64手机性能或安全验收。原Action失败、完整业务未测与新SOURCE待测都原样保留。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"新KSU实测完整原Go c-shared进入真实导出时SIGILL132，tombstone为独立klauspost/cpuid/v2 MIDR_EL1；仅测试库增加noasm CPU探测备选路径，官方Go/Rust客户端不变。"}
```
