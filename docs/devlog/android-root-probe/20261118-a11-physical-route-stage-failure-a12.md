# A11 实体 ARM64 UID→TUN 路由阶段失败；A12 分层原因收据

实验分支：`experiment/android-temp-root-probe`，Draft PR #36；不修改 main/M0/registry/cursor。用户于 2026-11-18 安装 A11 同源签名 APK（SOURCE `a3e52ae39f3d0e45317263c317c56f82724ccd35`），在本人真 ARM64 KernelSU 设备上点击一键自检，并提供以下脱敏原始结果：

```text
REAL_TLS_AUTH_LEASE=NOT_RUN (needs real server and credentials)
REAL_M3_M4_APP_DATA=NOT_RUN (needs authenticated session)
SYSTEM_DNS_TAKEOVER=NOT_RUN (safety gates remain false)
NATIVE_ARM64_KERNEL=PASS (actual uname aarch64)
PHYSICAL_NETWORK=PASS (Android Network exact readback)
SOURCE_AND_APK_ASSET_SHA=PASS
ROOT_PASS
GO_ELF_HELP_PASS
TUN_PASS
RAW_PASS
UNDERLAY_PASS
ROUTE_UID_PASS
SELFTEST_SCRIPT_DONE
ROUTE_ROLLBACK_PASS
A11_UID_TUN_ROUTE_FAIL
A11_UID_TUN_ROLLBACK_PASS
A11_ROOT_CHILD_EXIT_NONZERO
REAL_APP_UID_TO_TEMP_TUN_PACKET=NOT_PROVEN
```

## 有证据的边界

1. A10 重复 PASS：原 Go ARM64 ELF help、KSU Root、非持久TUN、RAW、物理接口绑定、本APK UID 私有规则/table19843（loopback固定测试目标）的安装及清理。可以停止继续为真 ARM64 Go ELF 加大 x86 NativeBridge probe 投入。
2. A11 报告 `A11_UID_TUN_ROUTE_FAIL` **只能证明失败在临时 TUN 路由设置、添加 APK UID 规则、或其 readback 的合并分支之一**。原实现三个判断共用相同错误码，无法仅凭用户回执断言是 TUN 设备路由、UID 规则还是 readback 出错。前面的 `A11_UID_TUN_SETUP_FAIL` 未出现；原生助手已创建临时 TUN 与配置接口的脚本门，具体内核拒绝原因仍未知。
3. `A11_ROOT_CHILD_EXIT_NONZERO` 是 Shell 主动在失败分支 `exit 77`，**不是正式 Go/Rust 客户端崩溃**。`A11_UID_TUN_SEND_READY` 不存在，因此 Android App 没有发送单个目标 192.0.2.1 UDP 测试包，真正 UID→临时TUN 入场没有发生。`A11_UID_TUN_ROLLBACK_PASS` 表示本次独立测试的 UID/表/TUN 只读检查未观察到残留，但不代表真实 WBD Stop 完整 JOIN。
4. 真 WBD TLS/认证/租约、原 Rust M3/M4 双向 TCP/UDP、其他目标 App UID 策略路由、CN8503/netd DNS/tunnel TCP53/系统 Resolver 仍 NOT_RUN；两个 DNS 冷门继续 false。不可把独立 helper 当原 Rust M4 接管。

## A12：固定阶段/errno 分类，不盲目改生产路线

保留 A11 已用户实测通过的单 APK UID/test-only table19843/pref9699、固定保留IPv4目标 192.0.2.1/32、非持久 `wbdst11` TUN、Shell `trap EXIT` 原子所有权清理及“**未经过实际 `ip route get ... uid` 的 readback 就决不发包**”要求。任何测试都由用户在原 APK 内单击明确许可，不查询密码/服务器，不写系统默认路由、不修改其他应用 UID、不修改 19842/原 WBD 通道、不替换原 Go/Rust、不开放系统DNS。

原 `A11_UID_TUN_ROUTE_FAIL` 将继续输出，用于和历史回执对照；新增只允许固定枚举：
- `A12_TUN_INTERFACE_DISAPPEARED`、`A12_TUN_ROUTE_ADD_FAIL` 与五种分类 `A12_TUN_ROUTE_ERR_EINVAL/EPERM/DEVICE/EXISTS/OTHER`；
- `A12_UID_RULE_ADD_FAIL` 与固定 `A12_UID_RULE_ERR_EINVAL/EPERM/EXISTS/OTHER`；
- `A12_UID_RULE_SHOW_UNAVAILABLE`、`A12_UID_RULE_READBACK_FAIL`；
- `A12_TUN_ROUTE_SHOW_UNAVAILABLE`、`A12_TUN_ROUTE_READBACK_FAIL`。

暂时只读捕获原安卓 `ip` 命令 stderr 到内核 root 所有、0700 受锁定测试目录下的私有临时文件；按已知错误固定字面量识别 EINVAL/EPERM/DEVICE/EXISTS/OTHER，然后原样删除临时文件。**绝不把原 stderr、用户IP、任何 UID 值/包内容或用户名输出到 APK/logcat/上传收据**。在 Root 用同一 TEST-NET 目标的程序中只诊断，不尝试未经证据支持的路由 fallback、系统 netd 操作或放宽发包前的内核选路门。

A12 新源码的 Host Java脚本测试、静态隐私/安全策略、同SOURCE NDK ARM64 16KiB signed debug APK、原 Go/Rust/Android16 KSU NativeBridge/原 Linux oracle 都要重新验证；但CI build PASS只证明**可以上机测试**，A12 根因分类是否出现仍然只取决于用户真机回执。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"封存用户真 ARM64 A11 route阶段失败+rollback PASS、没有实际发包的准确红门；A12仅加固定分层ip/UID路由errno收据、私有临时错误文件清理、安全同源码signed APK，不修改正式Go/Rust和系统DNS。"}
```

## A12 签名 APK 构建实绩（尚无新设备回执）

同源码 `e1e085ed722121f83d1a48e906824bfe49ff3b45`
[Android ARM64 Actions #44213162334](https://github.com/lly8666/wbd-next/actions/runs/44213162334)
的 `root-arm64-app` job **SUCCESS**；记录
`ANDROID_ARM64_A12_GRANULAR_ROUTE_FAILURE_DIAG_AUDIT_PASS`、
`ANDROID_ARM64_A11_REAL_UID_TUN_PACKET_SCRIPT_HOST_PASS`、
`ANDROID_ARM64_ROOT_DEBUG_ONLY_TUN_RAW_SELFTEST_ABI_SHA_PASS`、
`ANDROID_ROOT_ARM64_APP_AND_NATIVE_ASSETS_SOURCE_LOCKED_BUILD_PASS sdk=36`。
原 Go/Rust ARM64 原生源锁构建、CN8503、Rust DNS/M3 和 Linux 原服务端 oracle 同源 Job SUCCESS，产品协议与 DNS 双冷门均未改。

签名 A12 APK artifact ID `14386339734`，实际完整 APK SHA256
`24d4d84c6713bbe8616205f622bc0db5560918069597a5b8922a4b2275bf74e3`，
自 `android-root-original-arm64-app-e1e085ed722121f83d1a48e906824bfe49ff3b45`
提取后验证 ZIP 中 `SOURCE`、内部原Go/Rust、NDK AArch64 helper SHA256 与新固定枚举字节。
[完整 Action44213162334](https://github.com/lly8666/wbd-next/actions/runs/44213162334) **10/11 Jobs SUCCESS，整体FAIL**；唯一红门仍是 x86_64 KVM KSU NativeBridge 正式原Go ELF `ORIGINAL_WBD_ARM64_EXIT=139`，隔离真实Go CLI cshared测试 `ORIGINAL_GO_CSHARED_HELP_EXIT=0`。用户真ARM64手机已于A10真实报告 `GO_ELF_HELP_PASS`，两种不同执行环境不可混淆，未作跳过/绿化。当前能声称的是 **A12 BUILD_PASS**，用户 A12 真机新事件与 UID→TUN 包仍 **NOT_RUN**，不得把 Host/Cuttlefish Admission 成功写成实体机包已到达。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"将用户A11实体失败保留红门，同时冻结A12同源Java/NDK正式签名APK构建PASS、artifact/SHA与实机NOT_RUN。"}
```
