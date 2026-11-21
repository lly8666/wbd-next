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

## 修复版第2次真实KSU结果和测试执行顺序纠正（2026-11-17）

源码 `b5870751e668abe86cbf65a145d723d538b78438` [Android产品Action44115164331](https://github.com/lly8666/wbd-next/actions/runs/44115164331) 已经**10/10旧产品Jobs PASS**（Go/Rust Bionic、签名APK、Linux真协议oracle、Host/Rust DNS/M3）；新增第11项**FAIL**，其诊断artifact [14342342784](https://github.com/lly8666/wbd-next/actions/runs/44115164331/artifacts/14342342784) 具体证据：
- 两次Android16 API36 x86_64 KVM启动/ADB/SELinux Enforcing均PASS；签名APK内真实ARM64 Go/Rust精确SHA验证PASS，安装正式Root App SUCCESS；
- 修复后Manager二次启动成功，`ksu-shell-id.txt` 是 `uid=0(root) gid=0(root) groups=0(root) context=u:r:ksu:s0`，`CapEff=000001ffffffffff`；上一轮127 su阻断已解决；
- `adb shell am start ...RootClientActivity`返回`Starting: Intent ...`，但脚本紧接立即用`adb shell pidof org.wbdnext.rootclient` 得到空文件并exit1；`receipt.json`标`phase=REAL_PRODUCT_APK_ACTIVITY`，故NativeBridge ABI / ARM64 ELF**尚未被执行**，不能当作NativeBridge兼容性结论。此次未记录Android logcat，不能声称Activity已稳定运行。

下一源码修复把NativeBridge硬件/真实AArch64执行提到Activity PID之前，ActivityManager启动后有界20x1s PID查询，失败保留logcat+activity dump。不得把`Starting: Intent`当Activity正常显示或WBD真TLS；新SOURCE Action仍须再跑。早期两次FAIL完整保留。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"x86 KVM Android16 KernelSU二次Manager已成功真实su UID0；第2次同源产品Job被过早Activity pidof检查阻断NativeBridge，移动ABI执行优先并增加有限PID/logcat实际诊断。"}
```

## 第三轮KSU环境源锁失败与修复

`bca7c3189d9a149abffeb30fda9cb3d7242da2c0` [Action44116782883](https://github.com/lly8666/wbd-next/actions/runs/44116782883) 旧10项Host/ARM64 native/signed Root APK/Linux原真TLS oracle均PASS；第11项KSU guest **FAIL于bash -n**：line249 `unexpected EOF while looking for matching single quote`，未启动guest，更未执行NativeBridge。实际原因是用JS `String.replace`拼接包含 PID regex `$'`的代码段，`$'`会被JS解释为原始字符串后缀而破坏shell单引号。历史失败保留。

修正从上轮已通过`bash -n`的脚本 `b5870751e668abe86cbf65a145d723d538b78438` 源码按JS slice重建，NativeBridge AArch64原Go exec优先于Activity PID，Activity后做有界20s实际PID和失败logcat，新增块本地`bash -n`与PID正则检查通过。新SOURCE整脚本是否PASS只看下一Actions；未将旧KSU诊断套作正式Go TLS连接，Go/Rust产品代码未改。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"记录第三轮KSU guest bash -n匹配引号错误FAIL和NativeBridge NOT_RUN，恢复源锁脚本语法并将真实AArch64 exec提前。"}
```

## x86_64 KVM API36 KSU + ARM64 NativeBridge真实执行、库发现FAIL（2026-11-17）

SOURCE `1faf0aedc7802c77c3f45986cea50710b244f5b4` [Action44118042917](https://github.com/lly8666/wbd-next/actions/runs/44118042917)：全部旧10个 Host/ARM64原生ELF/签名APK/Linux真TLS/认证租约/M4 UDP/Stop oracle **SUCCESS**；新KSU guest Job **FAIL**，完整原始artifacts [14343003956](https://github.com/lly8666/wbd-next/actions/runs/44118042917/artifacts/14343003956) 显示:
- API36 Android16 `uname=x86_64`, SELinux Enforcing, KSU root`uid=0(root) context=u:r:ksu:s0`；`ro.product.cpu.abilist=x86_64,arm64-v8a`, `ro.dalvik.vm.native.bridge=libndk_translation.so`, `ro.enable.native.bridge.exec=1`, 真系统`/system/lib64/libndk_translation.so`和`/proc/sys/fs/binfmt_misc/arm64_exe`处理器均存在。
- 同SOURCE正式APK所含原AArch64 Go ELF及Rust.so已经真实`adb push`至Root环境，`su`下原ARM64 Go的真实`execve`进入Bionic动态链接器，却报`CANNOT LINK EXECUTABLE "/data/local/tmp/wbd-product-arm64": library "libwbd_engine.so" not found: needed by main executable`。并非`Exec format error`，但`arm64_native_exec`仍NOT_PROVEN，后续真正TLS、App Activity未执行。
- 已下载同SHA实际ARM64 Go ELF，用`readelf -d`证实`DT_NEEDED=libwbd_engine.so`而**没有 DT_RUNPATH**；Rust so真实同目录，`su -c`的LD_LIBRARY_PATH在NativeBridge场景未能使加载器找到它。

本批对原Android Go CGo链接器加`-Wl,-rpath,\$ORIGIN`；正式Root App原布局就将Go主程序和真实Rust .so放同一私有root-owned目录，ELF `$ORIGIN` runpath是生产修复而非测试sidecar。Android ARM64构建须对实际产物`readelf -d`同时断言Rust`DT_NEEDED`及`RUNPATH [$ORIGIN]`，KSU真实guest验收也检测同APK ELF字节。已在本地Go CGo dummy中实测相同`CGO_LDFLAGS`得到`RUNPATH [$ORIGIN]`，**这只证明链接参数可行**，仍须下一同SHA Android Actions实测；无Go/Rust FakeTLS/PN/AEAD/Stop协议改动，历史失败保留。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"原Android ARM64 Go真正通过x86 KVM+KSU NativeBridge binfmt到Bionic，因原ELF缺RUNPATH找不到Rust.so FAIL；修原CGo $ORIGIN RUNPATH并核同SHA ELF动态节。"}
```

## ARM64 RUNPATH单条断言误判导致同SOURCE构建门FAIL（2026-11-17）

SOURCE `b3166604b972cc32eea1c0313f10ddfc82f71208` [Action44120418078](https://github.com/lly8666/wbd-next/actions/runs/44120418078)：真实Android ARM64 Go/Rust构建生成了正确格式的ELF，但是`arm64-native` Job **FAIL** 于新增过于狭窄的grep断言；该次的Root APK、同源Linux oracle、KSU NativeBridge guest全部 **SKIPPED**，不存在Android设备链接实测。已下载真实Source工件 [14345396049](https://github.com/lly8666/wbd-next/actions/runs/44120418078/artifacts/14345396049) 并在宿主直接 `readelf -d`：`DT_NEEDED=[libwbd_engine.so]`，`DT_RUNPATH=[$ORIGIN:$ORIGIN:$ORIGIN:$ORIGIN:$ORIGIN]`。Go CGO对多个cgo链接对象重复注入`$ORIGIN`，全是相同合法相对路径，没有任何其他路径；先前`grep -Fq 'Library runpath: [$ORIGIN]'`要求整个字段恰好一个，因此错误红门。原Rust和DNS Host实际测试PASS。

只更正两个 SOURCE 门`android/root-native/build-source-locked.sh`与`android/root-app/ci/x86-kvm-ksu-arm64-nativebridge.sh`，允许仅重复`$ORIGIN`的RUNPATH、拒绝其他路径：`grep -Eq 'Library runpath: \[\$ORIGIN(:\$ORIGIN)*\]'`。本地正反字符串已验PASS；不修改已经真实链接出DT_RUNPATH的Android Go/Rust生产源码。功能卡保留全部48历史verification（包括此次FAIL）与各source/evidence/status，只压缩两条旧验收scope说明便于低于16KiB硬门。当前新SOURCE未跑，不能把Host/本地grep说成Android设备PASS。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Go原Android ARM64 ELF真实$ORIGIN RUNPATH存在但CGO重复五次，新增单条grep错误FAIL；修源码锁建构与KSU两层gate允许仅重复$ORIGIN，保留全部历史验证。"}
```

## 2026-11-18 恢复最新远端：NativeBridge真实SIGSEGV与分层诊断

SOURCE `32e32e8ccceb1adf1d895e9327d378faa5353a7a` [Action44121481475](https://github.com/lly8666/wbd-next/actions/runs/44121481475) completed/**FAIL**。旧10个产品Job（Android ARM64 Go/Rust ELF/签名APK、Host M3/M4/DNS、同源Linux真TLS/租约/UDP/Stop oracle）全PASS，但新增KSU guest运行**FAIL**。原始[artifact14346456086](https://github.com/lly8666/wbd-next/actions/runs/44121481475/artifacts/14346456086)不抹除。

真实Android16 API36 x86_64 KVM+官方KernelSU `uid=0(root),context=u:r:ksu:s0`；libndk_translation.so与binfmt_misc/arm64_exe存在。签名APK同SOURCE原Go与Rust ARM64共享库一致，真实Go ELF的`DT_NEEDED=libwbd_engine.so`、`RUNPATH=[$ORIGIN:$ORIGIN:$ORIGIN:$ORIGIN:$ORIGIN]`均PASS；不再发生找不到Rust.so，**但真正`--help`进程SIGSEGV exit139**，不证明是翻译器、Rust或Go哪一方，也不证明正式WBD业务完成。Android App→Root真TLS/租约/TUN/Stop与Android↔Linux server E2E继续NOT_RUN。

本批只添加同SOURCE构建的测试专用两个`android/arm64` ELF：NDK最小C + 纯Go CGO0。guest真实顺序执行NDK自身、纯Go、NDK`dlopen`真实Rust `libwbd_engine.so`并`dlsym`已导出函数（**不调用WBD原业务或伪造密码/AEAD**）、最后再执行与签名APK逐字节相同的正式 ARM64 原Go/Rust主程序。收集每一个退出码、真实marker、原进程实际输出、Android `logcat -b crash`和最近tombstone有界摘录，明确定位翻译器/Go runtime/Rust loader/原合体程序四层。诊断侧车**绝不放入正式APK**，旧红门和Source lock保留；本批新源码实际Android run提交前NOT_RUN，实体KSU终验仍要用户另授权。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"恢复最新真实KSU NativeBridge原ARM64 Go+Rust SIGSEGV 139失败并保留证据；新增测试专用NDK/纯Go/Rust动态载入层次与Android崩溃收据，不伪装正式TLS或业务。"}
```

## 2026-11-18 分层真实KSU结论：NDK/Rust加载PASS，Go runtime本体SIGSEGV

SOURCE `e284b720b4a7e806b24f1438f72ac2f6aaa63198` [Actions44126602143](https://github.com/lly8666/wbd-next/actions/runs/44126602143)：原10项构建/Host/Linux原协议oracle **10/10 PASS**；新增第11项真实Android16 API36 x86_64 KVM/KernelSU/ARM64 NativeBridge **FAIL**，原始[artifact14348032201](https://github.com/lly8666/wbd-next/actions/runs/44126602143/artifacts/14348032201)中真实退出码和系统crash：
- NDK纯C ARM64 Android进程`--self`：**exit0**，且真实`WBD_ANDROID_ARM64_NDK_MIN_EXEC_PASS`；
- 同NDK ARM64进程`dlopen("/data/local/tmp/libwbd_engine.so",RTLD_NOW)` + `dlsym`实际Rust原M1导出函数（仅寻找函数、不造数据包）：**exit0**，`WBD_ANDROID_ARM64_RUST_DLOPEN_PASS`；
- 同SOURCE且无Rust依赖的最小**纯Go CGO0 ARM64**可执行程序：**SIGSEGV exit139**，尚未进入`main`或打印证据；
- 与正式签名APK逐字节匹配、`DT_NEEDED=libwbd_engine.so`和`$ORIGIN`已实证的真正Go/Rust原客户端`--help`：**SIGSEGV exit139**；
- 真Android`logcat -b crash`显示两者均由`/system/bin/ndk_translation_program_runner_binfmt_misc_arm64`实际启动，`SIGSEGV SEGV_MAPERR`均访问`fault addr=0x2`（/memfd:exec in translated code）。该事实极大缩小为当前NativeBridge执行路径与独立Go runtime的不兼容，**不能反推出真实ARM64设备也会崩溃，更不能把NDK/Rust加载PASS算WBD TLS/租约PASS**。
- 该次脚本在原Go失败处中断，签名APK Activity尚**NOT_PROVEN**；以往x86 KSU探针仍不等于ARM64客户端。

当前下一测试分支严格是**测试专用 Go c-shared `android/arm64` ELF**，通过已PASS的NDK ARM64桥接启动程序`dlopen`并调用其仅返回常数的Go `//export`符号，验证是否“直接Go CLI/binfmt”特有的问题。附加同份纯Go在`GODEBUG=asyncpreemptoff=1,GOMAXPROCS=1`下的真实进程对照；结果分别收据，不将辅助Go sidecar打入生产APK或冒充原WBD协议。另修改KSU脚本即使正式Go崩溃也继续启动签名APK原`RootClientActivity`，独立采集PackageManager/UI真实PID（无凭据、不请求Root START），随后仍因原Go SIGSEGV保持**整Job FAIL**，绝不伪造NativeReady。当前这些新SOURCE的Android结果**NOT_RUN**，main/M0/原Linux Windows协议完全不动。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"KSU分层真结果NDK ARM64/Rust dlopen退出0，独立Go和正式Go SIGSEGV139，二者同由binfmt runner故障地址0x2；增加测试专用Go c-shared/Go runtime选项对照及失败后独立APK Activity验收，不引入假WBD业务。"}
```

## 2026-11-18 真实Go c-shared和正式APK Activity对照：MIDR_EL1 SIGILL

SOURCE `201ea3d4874f0b2396ef05797ae7a57fd7e69e38` [Actions44129262070](https://github.com/lly8666/wbd-next/actions/runs/44129262070)：原10个Host/正式Bionic ARM64/signed APK/Linux真实TLS oracle Jobs **10/10 PASS**；KSU ARM64 NativeBridge第11项**FAIL**，原始[artifact14348094207](https://github.com/lly8666/wbd-next/actions/runs/44129262070/artifacts/14348094207)可复核。
- API36 Android16 x86_64 KVM/官方KSU Root；真实NDK ARM64最小执行`0`、原Rust`dlopen+dlsym=0` PASS。纯Go`139`，加`GODEBUG=asyncpreemptoff=1 GOMAXPROCS=1`仍`139`，原Go/Rust`--help`仍`139`。
- 独立Go `-buildmode=c-shared`库由NDK ARM64启动器**成功dlopen**，但调用仅返回常数的Go导出函数时**SIGILL exit132**；`logcat -b crash`栈`/system/lib64/libndk_translation.so (berberis::UndefinedInsnThunk)` → 真`internal/cpu.getMIDR.abi0+0`。Go1.23.12 ARM64运行时在 HWCAP_CPUID 时调用`getMIDR()`、执行`MRS MIDR_EL1`；该翻译器不能执行它。纯Go/正式Go的SIGSEGV139可能还有其他独立原因，不能断言已修全部。
- 独立Android**正式签名**`org.wbdnext.rootclient/.RootClientActivity`真实安装、`am start`+PID有界查得**2884**，收据`product_app_launch=PASS`；**仅UI Activity**，普通App Root->原Go真TLS/租约/TUN/Stop和Android↔Linux E2E仍**NOT_RUN**，Job如实FAIL。
- 本批诊断将固定Go1.23.12 `GOROOT`**复制到隔离测试目录**，`internal/cpu/cpu_arm64_hwcap.go`中将MIDR探测判定仅对**测试版Android**增`&& os != "android"`。原工具链、签名APK、Go TLS/租约、Rust真AEAD/Stop、M0/main均不改。源片段必须与固定版本精确匹配，只改一次并记录前后SHA。分别构建实验CGO0与c-shared ABI的ARM64真ELF并在KSU guest跑，若失败仍保留根因红门，不能以隔离工具链成功宣告原WBD产品兼容。新SOURCE Android guest 结果提交前NOT_RUN。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"留存Android16 KSU真实APK Activity PASS、Go c-shared调用在NativeBridge getMIDR处SIGILL132以及原Go139；仅以复制的Go1.23.12工具链做安卓MIDR条件隔离，不影响生产。"}
```
