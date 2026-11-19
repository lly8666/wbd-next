# A32｜Android API36 原Go PASSWORD_FILE：Context.MODE_PRIVATE 0660 与 Go 0600 不匹配

**用户独立真机证据**：SOURCE `ec9d40fab0442fa6e5efaf38adc2ded2649913ff`、API36，23项允许列表事件：`ROOT_SHELL_ROOT_UID_VERIFIED`、`ROOT_SHELL_NATIVE_FILES_STAGED`、`ORIGINAL_GO_ENTRY`→ `ORIGINAL_GO_ARGS_REJECTED` + `ORIGINAL_GO_PARSE_PASSWORD_FILE` + `ROOT_PROCESS_EXIT_1`，无接口/TUN/RAW/TLS。证明了原 Go 真正读取参数失败，不是KernelSU没root或服务器故障。

**确认的源码契约错配**：[Android AOSP ContextImpl](https://android.googlesource.com/platform/frameworks/base/+/HEAD/core/java/android/app/ContextImpl.java) `setFilePermissionsFromMode` 在默认 `MODE_PRIVATE` 路径使用 `S_IRUSR|S_IWUSR|S_IRGRP|S_IWGRP`（0660）；旧Android Activity直接 `openFileOutput(...MODE_PRIVATE)` 后未调用chmod或读回。Go `readPrivateArgFile` 用 O_NOFOLLOW 和 `st.Mode().Perm()&0077!=0` 拒绝0660。手机实际mode未导出，因此明确是高度吻合但尚未设备读回确认的高概率根因。RouteKey文件同一旧writer，也必须一起修。

**改动**：`RootPrivateCredentialFiles` 使用底层 Android Os.open 0600/O_NOFOLLOW 写3个固定文件，fchmod同fd、fstat核对App UID/类型/硬链/精确模式/长度、缓冲区擦除；纯Java `RootPrivateCredentialContract` 公用同一权限策略，Service在su前lstat并用两种固定枚举报告本地读回成功或失败。Go原生产严格读法不改，旧Linux/Windows、TLS/AEAD、ROOT路由/Stop不改；不制作root-owned长期密码缓存。CN原signed asset已显式0600，Go安装ID单独由Go建0600，未无端改identity。

**Host与诚实边界**：生产策略在本机真实POSIX inode下验证0600通过、0660/0640/0604/错UID/符链接/硬链/空/坏route不通过；原 Go Linux原测试追加密码和route 0660拒绝、0600通过；真实APK DEX需要包含新writer+contract，原Go/Rust ARM64/原Linux oracle同SOURCE。只跑Host Actions，不碰个人Android/服务器、不重启hosted KSU/TAP/模拟NIC。A32 BUILD_PASS != API36实际修复或真实TUN/TLS/M4/Stop PASS，只有用户自行安装后下一个TXT能确认设备fd chmod/readback。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"API36实机原Go PASSWORD_FILE拒绝；查明MODE_PRIVATE默认可能0660与Go严格0600不兼容，同批修密码RouteKey可选CA的NoFollow/fchmod/fstat及su前lstat，不放宽Go。"}
```
