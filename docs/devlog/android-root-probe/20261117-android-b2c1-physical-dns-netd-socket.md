# Android Root B2c1：真实Network选择范围的物理DNS UDP/TCP socket netd预连接绑定

施工分支：`experiment/android-temp-root-probe`，基线SOURCE `e14c69352ff28605b28271bdaf28ee278cc80669`，PR #36 Draft。延续B2b同源CN8503签名资产/原Go冷SHA校验、无VpnService/FakeIP，原Linux server不改变。

## 施工切片与边界

新增`r0/go_overlay/internal/v4productcli/dnsnative/physical.go`：严格`PhysicalScope{NetworkHandle,InterfaceName,IfIndex,MTU,LocalIPv4}`，每次Dial前核内核`net.InterfaceByName` index/MTU/up及`nic.Addrs()` IPv4；物理路径只允许原CN `223.5.5.5:53`，连接仅`udp4`或`tcp4`，指定当前本地IPv4，强制`net.Dialer.ControlContext`在连接前对真实fd进行绑定回调。回调失败/来源漂移不尝试OS默认出口、不切换到`1.1.1.1`。内部局部测试钩子才允许覆盖为localhost临时端口。

新增`physical_android_cgo.go` (`android&&cgo`)：真实 NDK `android_setsocknetwork(C.net_handle_t(handle), fd)`、`SO_BINDTODEVICE`与同一fd的接口名称readback，错误fail-closed。非Android或Android无CGO的`physical_android_stub.go`明确拒绝，不能偷偷建无绑定socket。`linux.go`真正原Go Android客户端在冷物理网络与MTU验证后构造该Dialer，保存在代际配置中但**不打开DNS socket**、不调用`Resolve`，打印 `V4_PUBLIC_ANDROID_PHYSICAL_DNS_COLD_SCOPE_CHECKED socket_opened=0 dns_capture=NOT_CONNECTED`；原Go TLS/租约、Rust M4和App多UID路由语义保持。

独立`b2c-physical-scoped-dns-host` Actions Job使用真实host Linux `lo` 内核接口的ifindex/MTU/IPv4，以及本地UDP及TC→TCP真实DNS服务端，验证每种socket的fd回调顺序及类型；选错Tunnel、海外服务器、协议、异常ifindex/MTU/IPv4、绑定拒绝均拒绝且不发任何UDP。NDK ABI源码需同SOURCE的原Go/Rust Android ARM64 Bionic CGo Native正向编译。记录hash与资格票据：只有`B2C_PHYSICAL_HOST_SOCKET_PASS`和`ANDROID_BIONIC_NDK_BIND_CROSS_COMPILE_PASS`，不能宣称Android已将某个socket绑定到真实WiFi。

严格NOT_CONNECTED/NOT_RUN：Android用户原App普通DNS UDP/TCP53 ingress、root netd Resolver重定向、Linux原服务端的隧道DNS出站、Rust M4 TUN逐包接管、CN IPv4真实内核direct/split规则、真实Android16 physical Network的`android_setsocknetwork`许可/readback及KSU授权。托管ARM64 host KVM不可访问，P2/P3 `ENV_BLOCKED`，实体P5最终单独授权。本次不改main/M0/原Linux协议、不触实体手机/云购入。

**当前源码尚未跑同源Actions，不得提前写PASS。**

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B2c1原Go Android物理DNS NDK netd套接字预连接绑定、真实Network接口IPv4冷范围验证及host真实UDP/TCP回环fail-closed门，不宣称TUN/Resolver/Android设备DNS已接。"}
```
