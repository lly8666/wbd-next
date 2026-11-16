# 2026-11-16 Android Root 自包含诊断 APK 实测交付

**原分支** `experiment/android-temp-root-probe`，SOURCE `d5919d9d2967c29de83351b157d9c1db27a04e63`；[Android16 KSU3.3.1 真机架构 x86_64 模拟器 Action43884001753](https://github.com/lly8666/wbd-next/actions/runs/43884001753) **SUCCESS**。注意此环境使用**预配置 KSU 的 x86_64 模拟器**，不代表 DirtyFrag 获得临时 Root 或真实 ARM64 手机 PASS。

## 用户可安装文件

- 已从 [Action工件14233518488](https://github.com/lly8666/wbd-next/actions/runs/43884001753/artifacts/14233518488) 下载 CI 产物 ZIP 并独立验证 ZIP SHA256 `b3a44aa622ab9a29d38e546c83beb01b71853dddb74343724a2fcf10388e04cc`，提取其中 `diag/device-diagnostic.apk`，大小1,479,348字节，APK SHA256 **`247a8e90247ad6d1b798c68b0a658ea010007d0bebf9dda07ea4641a7cef5ff0`**。minSDK28，target37，普通包 `org.wbdnext.rootprobe`，App 标签 `WBD Root Diagnostic`，仅使用本次CI临时证书签名。
- 内置 ELF `lib/arm64-v8a/libwbdprobe.so` SHA256 `2a91f1f199697381496980cdaf3ce296ca0a842558f62497f7832e142d31b85a`；`lib/x86_64/libwbdprobe.so` SHA256 `273bf31806db9cf2034743931e72e9b7171913381c73b54fc142d599f3d2876a`，均 16KiB PT_LOAD 对齐、APK内不压缩，`extractNativeLibs=true`。SOURCE 已内嵌 assets，APK+ELF独立SHA校验相符。

## 单 SOURCE 真实 Android16 KSU 实测

旧同源 App→su、TUN UDP/DNS53/TCP HTTP、Android Network DNS/认证TLS1.3、SIGKILL、自有规则手动恢复、私有netns 2WiFi+1USB 合成NAT全部再次通过。随后**相同包名+同一签名**安装新版自包含 APK，真实 UIAutomator 点击「运行短时 Root / TUN / RAW / NAT 完整检测」，App私有 `last-device-diagnostic.json` 被真正创建，真实授权 `su` 从APK安装的 `nativeLibraryDir/libwbdprobe.so` 运行，**此用例未用 ADB push 原生文件**。

| 实测项 | x86_64 API36 | 证据边界 |
|---|---|---|
| App→su UID0 + CAP_NET_ADMIN/RAW | PASS | 真实KernelSU Manager授权；SELinux Enforcing |
| Owned TUN IPv4 UDP 双向 | PASS | 真 TUN fd、读写与关闭 |
| raw IPv4/TCP | PASS | 真 raw socket SYN/RST、SO_RCVBUF及lo接口 |
| IPv6 TUN UDP 双向 | PASS | 独立空网络命名空间真 IPv6 UDP 收发 |
| SO_MARK + 真实策略路由 | PASS | 独立空 netns 标记正例/未标记负例 |
| WiFi2客户端+USB1客户端合成 SNAT/conntrack | PASS | 独立netns三条客户端流量/返回包 |
| 主网络路由和规则恢复 | PASS | `ip -4 rule`、`ip -4 route show table all` 测试前后字节相同 |
| ARM64 原生执行 | NOT_RUN | **已构建/打包/16KiB ELF检查**，无真实ARM64硬件执行 |
| 真实热点/USB下游 VPN、BPF/HW offload | NOT_RUN | 没有实体下游、没有真实WBD数据会话 |
| 蜂窝切网、CLAT、生产 WBD/FGS | NOT_RUN | APK是Root诊断工具，不是正式客户端 |

机读总体状态 `ROOT_KERNEL_PREREQUISITES_PASS_PRODUCTION_UNVERIFIED`；`CORE_IPV4_ROOT_PROBE_PASS` 仅在 App UID→Root UID0+TUN/raw实际操作均通过时赋值；物理热点USB永远 `NOT_RUN` 直至另行实测。

## 手机使用步骤和失败定位

1. Android 9+、arm64-v8a手机；已有自己的可信Root管理器与对普通App可用的su。本APK不获取Root、不修改boot/系统、不禁SELinux。若以前装过其他CI签名的同包名 `org.wbdnext.rootprobe`，需先卸载旧调试包（会删除旧报告）再安装本次APK。
2. 打开 WBD Root Diagnostic，先点 **1. Root 授权与系统只读预检**，批准已有Root管理器的授权。检查UID/能力与SELinux域、内核/ABI/page size、TUN、`ip`/`iptables`及只读的Tethering/offload观测。
3. 点 **2. 运行短时 Root / TUN / RAW / NAT 完整检测**，保持前台，探针只创建有界owned TUN/raw localhost socket或**已隔离**的网络命名空间；不写手机主路由，不创建真实热点/USB、不建立 WBD VPN。
4. **逐项**查看 PASS/FAIL/PERMISSION_DENIED/ENV_BLOCKED/NOT_RUN，错误有 native errno、SELinux/caps、可执行文件问题、缺少 `CLONE_NEWNET`/iptables或未测实体业务的明确原因。没有Root不会尝试后续特权操作。选择 **分享报告 JSON** 或 **复制报告 JSON** 发回开发者分析，报告由用户主动分享，含设备内核/接口诊断信息，请自行检查。
5. 这份APK不是生产网络恢复工具，测试不添加永久主网路由；退出后临时fd和独立namespace随进程释放。其他Root应用遗留的主路由需其自身owned journal处理；无Root本APK也不能强行回收。

## 保留历史错误与范围

首轮 SOURCE `d2794f1cb4faa8a75a445506842e7a4bf16e0774` [Action43883692925](https://github.com/lly8666/wbd-next/actions/runs/43883692925) 因构建期 `aapt2 dump xmltree` 缺少 `--file` **FAIL**；同源 [双ABI build Action43883692972](https://github.com/lly8666/wbd-next/actions/runs/43883692972) SUCCESS。最终 `d5919d9...` 修复 CLI 后才完整PASS，旧FAIL未改写。具体不可超范围宣称完整WBD Android兼容、临时Root提权成功或OEM共享offload可用。

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Certify self-contained signed ARM64/x86_64 APK and source-locked true KSU App nativeLibraryDir UID0/TUN/raw/IPv6/mark/synthetic NAT PASS; retain ARM64 physical and real tether NOT_RUN."}
```
