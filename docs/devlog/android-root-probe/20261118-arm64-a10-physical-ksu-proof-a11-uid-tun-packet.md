# A10 实体ARM64 KernelSU用户回执 + A11真实自有UID→临时TUN逐字节验证

**工作分支**：`experiment/android-temp-root-probe`，Draft PR #36；不得修改main/M0/registry/cursor，不得将非WBD测试helper打包为正式TLS/Rust M4替代。

## 来自用户自有实体 ARM64 KernelSU 手机的 A10 收据（用户报告）

用户于 2026-11-18 使用 [A10签名APK SOURCE 9a0bca2](https://github.com/lly8666/wbd-next/actions/runs/44155431882) 按本机一键测试，提供以下**脱敏原文**（未经开发者远程ADB独立复验）：

```
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
```

结论仅是**用户报告的真ARM64 KernelSU手机 A10 本机能力验收PASS**：原Go ELF --help启动、Root授权、物理Network、真内核TUN ioctl 创建+关闭、RAW socket、SO_BINDTODEVICE、独立只针对本APK UID 的 pref9699/table19843 规则读回及回滚。无需继续为真实ARM64原Go ELF139下注：之前 x86_64 NativeBridge 的139 是跨架构guest的已知结果，不能代表这台实体手机。仍**不是**生产目标App路由或真实TLS/租约/Rust M3/M4/DNS PASS。

## A11 无服务器真实自有App UID → 临时TUN UDP包入场

A11沿用 A10 同SOURCE 正式Go/Rust APK，增加**独立且有界**的诊断段：原安卓APK进程用`java.net.DatagramSocket`（不绑定物理Network、不用VpnService）从**自身真实Linux UID**只发送一次固定16字节内短UDP负载 `WBD_A11_TUN_UID` 到 IANA文档IPv4地址 `192.0.2.1:43999`。不需服务端，不生成/伪造TLS/认证/AEAD/业务包。

Root shell在单独已验证0700测试目录启动独立 AArch64 NDK C helper，真正 ioctl(`TUNSETIFF IFF_TUN|IFF_NO_PI`)创建非持久`wbdst11`。只给该临时TUN加 `198.18.0.1/30` benchmark源IP，向新表19843安装 `192.0.2.1/32 dev wbdst11`，只给**APK自己UID**添加`pref9699 uidrange APK_UID-APK_UID lookup19843`；无全局路由、网络DNS、物理接口持久更改或任何别的用户App UID。严格检查已有路由/规则/TUN占位则拒绝触碰。安装/readback后还要`ip -4 route get 192.0.2.1 uid APK_UID`含`dev wbdst11`才能发`UID_TUN_SEND_READY`，Java才允许发送。权限/route get不支持则NOT_PROVEN而非发包绕过门。

C helper只`poll`最多9.5秒，在真实TUN FD读取一个IPv4 packet，对真实dst`192.0.2.1`、UDP目标端口43999、固定负载逐字节匹配，**不记录任何原始包、UID、IP源、密钥、socket日志**。Root shell同步join helper，`trap EXIT`先撤单UID规则再删仅此/32路由、停止helper关非持久TUN FD，然后 readback 检查pref9699/table19843/wbdst11均消失。任何失败必须`FAIL/NOT_PROVEN`和可见rollback标记；被`SIGKILL`/设备掉电无法绝对保证trap成功，用户遇到rollback FAIL必须停止继续测试。该脚本不劫持普通其他应用、无任意真实互联网发包，仅保留文档目标测试IP。

**PASS门**：`A11_UID_TUN_SEND_READY` + 本APK真实UID Java UDP send + `A11_UID_TUN_PACKET_PASS`（C真实TUN读取并逐字节验证） + `A11_UID_TUN_ROLLBACK_PASS`（UID规则、表、虚拟网卡均撤销）才允许`REAL_APP_UID_TO_TEMP_TUN_PACKET=PASS`。纯`route get`或`UID_TUN_ROUTE_PASS`**绝不等于真实收到包**。此测试只能证实系统内核UID路由接到受控TUN，不代表其他目标App UID、原Rust M4 TUN/RAW或服务器TLS/Stop。系统DNS/物理TCP53/netd Resolver/CN分流双门仍false，未入场。

## 构建门槛与接下来

新增纯JVM真实root脚本静态/行为测试 + 源范围审计，同时以NDK aarch64 Bionic 16KiB原编签名APK；不能把 Host PASS 等同设备PASS。开发者无权远程操作用户设备，本批不执行用户手机命令；需用户在新APK中再次明确授权、点一键测试并复制固定事件结果。署名为一次性Actions调试证书，更新旧APK可能需用户先备份并手动卸载旧版，不能脚本静默卸载。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"冻结用户提供的A10实体ARM64 KSU原Go/TUN/RAW/路由回滚PASS回执，独立A11真实本APK UID UDP→TEMP TUN逐字节收包/专用表精确rollback源码与CI，仍不宣称原TLS/M3/M4/DNS已验证。"}
```
