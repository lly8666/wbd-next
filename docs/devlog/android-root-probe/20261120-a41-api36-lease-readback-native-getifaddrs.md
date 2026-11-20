# A41｜实机保护认证及Rust原生Commit已PASS；直接修Android TUN /32真实内核读回

## 用户真实收据

用户 Android API36，SOURCE `06a670707c64f8fa9d2da021bb91a38765a3a70f`（A40），106个固定事件两次START：
`ORIGINAL_GO_TLS_HANDSHAKE_VERIFIED`、`ORIGINAL_GO_ADMISSION_VERIFIED`、`ORIGINAL_GO_POSTAUTH_COLD_OK`、`DETACH_OK`、`NATIVE_COMMIT_OK`、`LEASE_FIELD_OK`，之后两次 `ORIGINAL_GO_POSTAUTH_LEASE_READBACK_FAILED`、`LEASE_OS_FAILED`、root原Go EXIT_1。真实Root RST规则Stop_CLEARED。未观察到 `AUTHENTICATED_LEASE_OS_READBACK`、Rust M4启动或UID路由/真实业务。

## 不等日志枚举，直接修高概率Android-only实现差异

源码 `r0/go_overlay/internal/v4productcli/linux.go:readOwnedTunIPv4` 对Android也执行 `ip -j addr show dev <tun>` 且假设 Linux iproute2 的 `addr_info` / `ifindex` JSON格式。之前的 `ip -j link` MTU验证已经成功，不能概括称Android的 `ip -j` 一律不可用；但 `addr` 命令、字段形状或命令退出是这里的高概率兼容性断点。既然 `ip addr add` / `ip addr del` 均未触发A40对应失败而读回失败，直接在**原Go产品**的Android分支使用 `net.InterfaceByName` 和 `iface.Addrs()`（同一产品已在API36真机用来验证物理网卡IPv4），将OS实际IPv4地址映射为唯一正确/32；Linux仍按既有 `ip -j addr` 读回。无假LEASE收据/省略真实地址判断/降级保护认证，原Rust M4仍只会拿到真正安装的受保护租约。后续Android UID路由再次调用相同函数，因此这一处直接解决两条接线的JSON依赖。

## 测试和施工范围

增加原Go native getifaddrs地址解析真实Host单测：唯一/32、IPv6共存、空地址、/24、重复/32、unspecified、multicast负例；原Linux native真正 tagged `go test` 接入既有原服务端 Oracle（无假Android guest），Java/Go源锁门；GitHub同源ARM64原Go+Rust签名APK及Linux Normal/off Oracle保持。修复发生在实验分支的原Go产品实现 `r0/go_overlay`，**不是仅加Java日志/替身转发**；本次无需修改原Rust加密、wire或Linux/Windows；未碰main。当前安卓真机租约/内核网卡/M4仍待用户安装新SOURCE实际验证。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A41真机两次原Go保护认证、Rust Prepare/Commit及受保护lease字段成功但ip -j addr读回失败，直接修原Go Android接口地址读回改getifaddrs并加Host负例与同源CI。"}
```
