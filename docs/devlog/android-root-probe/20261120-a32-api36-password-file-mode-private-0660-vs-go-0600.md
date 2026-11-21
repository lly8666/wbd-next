# A32｜Android API36 原Go PASSWORD_FILE：Context.MODE_PRIVATE 0660 与 Go 0600 不匹配

**用户独立真机证据**：SOURCE `ec9d40fab0442fa6e5efaf38adc2ded2649913ff`、API36，23项允许列表事件：`ROOT_SHELL_ROOT_UID_VERIFIED`、`ROOT_SHELL_NATIVE_FILES_STAGED`、`ORIGINAL_GO_ENTRY`→ `ORIGINAL_GO_ARGS_REJECTED` + `ORIGINAL_GO_PARSE_PASSWORD_FILE` + `ROOT_PROCESS_EXIT_1`，无接口/TUN/RAW/TLS。证明了原 Go 真正读取参数失败，不是KernelSU没root或服务器故障。

**确认的源码契约错配**：[Android AOSP ContextImpl](https://android.googlesource.com/platform/frameworks/base/+/HEAD/core/java/android/app/ContextImpl.java) `setFilePermissionsFromMode` 在默认 `MODE_PRIVATE` 路径使用 `S_IRUSR|S_IWUSR|S_IRGRP|S_IWGRP`（0660）；旧Android Activity直接 `openFileOutput(...MODE_PRIVATE)` 后未调用chmod或读回。Go `readPrivateArgFile` 用 O_NOFOLLOW 和 `st.Mode().Perm()&0077!=0` 拒绝0660。手机实际mode未导出，因此明确是高度吻合但尚未设备读回确认的高概率根因。RouteKey文件同一旧writer，也必须一起修。

**改动**：`RootPrivateCredentialFiles` 使用底层 Android Os.open 0600/O_NOFOLLOW 写3个固定文件，fchmod同fd、fstat核对App UID/类型/硬链/精确模式/长度、缓冲区擦除；纯Java `RootPrivateCredentialContract` 公用同一权限策略，Service在su前lstat并用两种固定枚举报告本地读回成功或失败。Go原生产严格读法不改，旧Linux/Windows、TLS/AEAD、ROOT路由/Stop不改；不制作root-owned长期密码缓存。CN原signed asset已显式0600，Go安装ID单独由Go建0600，未无端改identity。

**Host与诚实边界**：生产策略在本机真实POSIX inode下验证0600通过、0660/0640/0604/错UID/符链接/硬链/空/坏route不通过；原 Go Linux原测试追加密码和route 0660拒绝、0600通过；真实APK DEX需要包含新writer+contract，原Go/Rust ARM64/原Linux oracle同SOURCE。只跑Host Actions，不碰个人Android/服务器、不重启hosted KSU/TAP/模拟NIC。A32 BUILD_PASS != API36实际修复或真实TUN/TLS/M4/Stop PASS，只有用户自行安装后下一个TXT能确认设备fd chmod/readback。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"API36实机原Go PASSWORD_FILE拒绝；查明MODE_PRIVATE默认可能0660与Go严格0600不兼容，同批修密码RouteKey可选CA的NoFollow/fchmod/fstat及su前lstat，不放宽Go。"}
```

## A32a 首次CI失败保留（Host静态检查变量作用域）

[Action #44586845085](https://github.com/lly8666/wbd-next/actions/runs/44586845085) 首轮 `root-arm64-app` 在生产 Host Java真实 POSIX元数据测试 `ANDROID_ORIGINAL_GO_COLD_SECRET_0600_POSIX_HOST_PASS`、脱敏收据和原 Go/Rust ARM64原生构建之后，于Python静态源检查 `NameError: name 'cold' is not defined` **FAIL**。代码原来在第147行才定义 `cold`，A32源门第139行先用了变量；这不是设备的密码/TUN新失败，旧原生/Host结果原样保留。这次小修在最早 `go_src` 加载后立即令 `cold=go_src`，不改变任何Android生产路径、原Go/Rust或安全检查，必须新SOURCE再次验证签名APK/原Linux Oracle。治理 `Feature catalog` 在原SOURCE已经 SUCCESS，不要把失败job改口称PASS。

## A32 产品 SOURCE 最终构建与真实失败收据（2026-11-20）

- 第一次提交 `231543439a96c85bdee2bc6160d44a86fcd8c027` 的 [Actions #44586845085](https://github.com/lly8666/wbd-next/actions/runs/44586845085)：原 Go/Rust ARM64、6 Host项目、2 Linux oracle、纯Java **`ANDROID_ORIGINAL_GO_COLD_SECRET_0600_POSIX_HOST_PASS`** 和固定收据通过，**root-arm64-app FAIL**，原因是增量源断言在 `cold` 变量赋值前引用，`NameError: name 'cold' is not defined`；签名APK因任务中断未生成。Feature catalog [#44586845063](https://github.com/lly8666/wbd-next/actions/runs/44586845063) SUCCESS。保留全部FAIL，不冒称本SOURCE全通过。
- 修CI变量顺序后的生产 SOURCE `3e2c0cfd7a9dff5598f1c7a33ab6eaaff9e3d67b` 在 [Actions #44587763808](https://github.com/lly8666/wbd-next/actions/runs/44587763808) **最终 SUCCESS：11 SUCCESS，4个KSU/TAP手工任务SKIPPED**；真实 Host Java POSIX0660/0600与软硬链/错owner、诊断TEST、原 Go CLI、真实 ARM64 Go/Rust ELF、原 Linux服务端oracle、签名 APK DEX/资产 SHA，均同SOURCE PASS。
- 官方 [A32源锁签名APK工件 #14563460168](https://github.com/lly8666/wbd-next/actions/runs/44587763808/artifacts/14563460168) 的 `wbd-root-lite-arm64-debug.apk` 与 `wbd-root-arm64-debug.apk` 字节相同，SHA256 `5a211659dfe2341d4bc5a2b44ddfcf148386104f023ba8317bf58e81729deb95`。该证书是一次性debug；安装前必须旧版Stop并验证路由无残留再卸载旧版，不能强制覆盖。
- 该 SOURCE 的 [Feature catalog #44587763748](https://github.com/lly8666/wbd-next/actions/runs/44587763748) **FAIL**，原因是CI-only子提交没有同步更改功能卡（`declared feature card not updated: android-root-native-client`）；本后续纯 `docs/features`/归档提交补充同SHA验收记录并重新验证治理，不动已验收二进制。
- **没有**运行Android API36手机或KSU guest，不能由Host POSIX文件权限推断用户手机实际 mode已修正；真实 Go parse、TUN、SYNACK/TLS/32租约、Rust M4、UID routing和Stop须等用户自己安装后导出新版 `APP_PRIVATE_CREDENTIALS_0600_VERIFIED` + `ORIGINAL_GO_ARGS_ACCEPTED` 等真实阶段收据。若后续出现仍然的 `PASSWORD_FILE` 或 `INSTALLATION_ID`，继续根据精细码定位，不会泄露私有参数。
