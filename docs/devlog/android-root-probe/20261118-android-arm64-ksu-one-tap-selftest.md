# A10 正式Debug APK：真ARM64 KSU一键内核能力/回滚自检

**分支**：`experiment/android-temp-root-probe`；Draft PR #36，main/M0/registry/cursor不变。A9b 基线SOURCE `244cf4a38406633841ec704623644c7d7cc062c6` 的本机授权设备业务仍 **NOT_RUN**；原先 [Action44148161549](https://github.com/lly8666/wbd-next/actions/runs/44148161549) 10/11 PASS，总体FAIL原因是 **x86 KSU NativeBridge原Go ARM64 ELF139**；不能由此推断真AArch64机器也崩溃。

## 用户旧APK表单 invalid 的根因

RootClientActivity原Start是真正原Go TLS/auth/租约/M3/M4连接。需要真实服务器IPv4/FQDN、TLS SNI、真实用户和密码、准确64位十六进制的原32字节route-key、合规peer端口、至少一个经安卓PackageManager取到的真实已安装App。随机值必须fail-closed，不能用假的TLS凭据去验证真实TUN/RAW。A10不放宽这些校验，只把错误分支拆成具体的无敏感字段解释，新增**完全独立、无需服务器参数的手机内一键自检**。

## 一键自检安全范围

调试APK显式按钮+AlertDialog二次用户确认后，通过该APK自己的KernelSU`su -c`权限执行，其他时间不触及设备。真产品Go/Rust仍保持原同SOURCE AArch64 Bionic 16K ELF；仅在Debug APK中多签入独立AArch64小型NDK helper及SHA256标记，原`NativePayload`再经source-locked asset SHA256复制。这个helper仅做`TUNSETIFF IFF_TUN|IFF_NO_PI`非持久TUN创建/ifindex readback/close销毁、`AF_PACKET SOCK_RAW`绑定真实物理接口立即close、`SO_BINDTODEVICE`设置真实物理接口立即close，**没有任何原客户端替代协议/Java逐包/JNI假数据/VpnService/FakeIP/真实包传输**。

隔离Root 0700目录`/data/local/tmp/wbd-next-selftest`验证目录身份且有`.lock`互斥，不改产品目录`/data/local/tmp/wbd-next-root`，有已存在owner.pid则fail-closed。不泄露CLI输出：真正原Go ELF以`--help`启动，必须真实出现`android-network-handle` flag（原Go main ErrHelp可能exit1），exit139或132分开标FAIL。和原 Go/Rust业务测试必须区分：help启动PASS不等于TLS/数据通过。

冷路由测试**只改本APK的内核UID**：`ip -4 route add 192.0.2.1/32 dev lo table 19843` + `ip -4 rule add pref 9699 uidrange SELF_UID-SELF_UID lookup 19843`；仅IANA保留文档地址，无默认路由/其他App UID/Android netd/原产品table19842 pref9600..9607/系统DNS。添加前检查路由和优先级没有任何其他进程占用，否则拒绝覆盖。过程凭同一root Shell和POSIX`trap EXIT`对加入的**精确规则**进行删除，readback判断无残留，输出固定 `ROOT/GO_ELF/TUN/RAW/UNDERLAY/ROUTE_UID/ROUTE_ROLLBACK` 的PASS/FAIL码。若故意SIGKILL或系统断电，trap无法绝对恢复；出现rollback FAIL应立即停止重复操作、人工检查规则。此测试**并未验证真实目标App产生的流量可走原Rust M4/内核路由**，只有真服务器认证建链后才可以验证。

UI只保存或复制固定测试结论，不打印root原始stdout、路由具体UID/密码/密钥/远端地址。真TLS认证/租约/M4收发、生产UID路由、TCP53/netd Resolver/系统DNS接管一律NOT_RUN；`android_dns_hijack_ready=false`、`android_dns_physical_ready=false`继续不变。调试APK是一次性Actions签名，旧安装包签名不同需用户自行决定是否备份并卸载，不能偷偷清理设备或绕过Android包签名。

## CI/A10验证标准

`root-arm64-app`必须先执行单独的源范围检查（临时路由只有本APK UID、限缩table、无default/netd操作），再通过Java/ADB已有测试，并使用NDK`aarch64-linux-android28-clang`真编译TUN/AF_PACKET helper，`readelf`验证machine183/16KiB/PT_LOAD、SHA256注入签名APK校验、原Go/Rust和CN8503同SOURCE。Linux端原协议和历史KSU继续跑：原Go ELF NativeBridge exit139不得假变绿。A10实际手机上运行、TUN真实ioctl/KernelSU权限/物理网络/临时路由readback/安全回滚尚未发生前，只可写BUILD_PASS/NOT_RUN，不得写DEVICE_PASS。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A10正品签名ARM64 Debug APK内一键本机KSU/原Go CLI/独立NDK真TUN ioctl/RAW/物理绑定/仅自身UID+TEST-NET/32独立路由及trap回滚；random Start校验解释，原TLS/M4/DNS/实机仍NOT_RUN。"}
```


## A10 初次source-safe Host审计误FAIL与修复

原A10 SOURCE `bd7a60b76d3d5d096245a5619b6056056486d02e` 的 [Action44154566551](https://github.com/lly8666/wbd-next/actions/runs/44154566551) 中，原生ARM64和全部已完成的DNS/M3 Host前置项PASS。Root APK依赖的Java/Python正式诊断Host测试PASS后，**新A10源范围审计**错误地要求Java存在字面量`source`（源码实际记录固定`SOURCE_AND_APK_ASSET_SHA=PASS`），会导致APK编译SKIPPED；还有一条静态禁止`TUNSETPERSIST`的检查误命中C注释中“**No TUNSETPERSIST**”而非真正调用。修复只匹配源代码里的真实固定成功码，并禁止`ioctl(fd, TUNSETPERSIST`实际永久化调用。已对所有其他静态token逐条实际比对，保持整套UID路由隔离/rollback/禁止发送任何数据包约束不变。

同时A10的普通Java运行前加入`uname -m`原生`aarch64`核验，不能让只报告`arm64-v8a` ABI但内核仍是`x86_64`的NativeBridge guest误进入“真ARM64设备PASS”。本轮内核设备测试仍NOT_RUN，旧SOURCE的APK Job FAIL与原Go KSU ELF139绝不被盖成PASS。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"纠正A10第一轮纯静态审计误拒绝固定SHA码与无持久TUN注释，增强真实aarch64 uname内核核验；所有KSU/TUN/真实设备成功仍待新同源APK CI与用户实测。"}
```
