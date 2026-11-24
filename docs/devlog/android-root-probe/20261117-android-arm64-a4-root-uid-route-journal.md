# 2026-11-17 Android ARM64 A4 原Go认证后单App UID Root路由与崩溃journal

SOURCE基线 `bd7a715992e7c9fe6765b45063c08a337568de5e`，仅 `experiment/android-temp-root-probe`。main、M0 registry/cursor、既有Linux/Windows均不改。仅 Android ARM64-v8a，不能误用x86 Android探针/VpnService/FakeIP作为产品。

## 高效、可回滚、真实的最小系统边界

1. 原始 Go FakeTCP SYN→标准TLS/凭据认证→服务端自动租约/32及OS安装读回→原 Rust M1/M3/M4 健康/Ready→FakeTCP接管；**只有这一链真实成功之后**，Android单APP UID `--android-route-uid=10000..1999999` 才可启动，默认0不改系统路由。Root进程UID0、本系统UID及其他应用绝不转到自有TUN。原Go Root进程的发送Socket仍按真实`android_setsocknetwork`+SO_BINDTODEVICE绑定Android ConnectivityManager实体Network；不污染全局路由或发包协议。
2. route: `ip -4 route add default dev <真实OwnedTun> table 19842`，内核逐条 readback 后仅对一个已授权普通 App UID `ip -4 rule add pref 9600 uidrange UID-UID lookup 19842`，再次读回；严格拒绝外来table/pref占用。支持后退：首先撤销精确UID rule，其次删除自有table route，再核对两者均为空；无法确认即报错，绝不谎称已成功停止。无main/default全局路由修改、DNS/UID范围扩权、iptable/netd篡改。
3. 跨进程所有权：固定`/data/local/tmp/wbd-next-root/route-journal.json`，目录模式0700且当前EUID持有，O_NOFOLLOW/O_EXCL写入0600 JSON，file+parent fsync **先于内核修改**；持久`owner.lock` EUID匹配+0600+非阻塞flock保护整个事务/Stop。仍运行的旧Root进程拒绝第二进程接管；上一进程崩溃自动释放锁后，新进程只能删除与旧journal的准确UID/TUN/table/pref一致的内核资源，外国/伪造状态全部fail closed。Journal成功确认删除后才放锁。
4. 单独的原 Rust `loop_physical_scope_invalid` 暴露真实M4 worker物理Network/ifindex失效，Android原Go低频`V4PublicLoopPulse`读取并立即退出监控、撤销App路由，再Stop/join原RX/TX和TUN；**不可**伪造为远端认证Health dead90或正常TLS再授权，Linux保留原控制路径不依赖该新符号。
5. Android系统可用性：当`/dev/net/tun`只有ENOENT时以同一真实TUNSETIFF请求`/dev/tun`，无需VPNService；Android默认禁用Linux专用`tc fq`（Linux原默认600mbps不动）。内核`ip -j`、uidrange规则是否支持必须设备实测，缺能力显式拒绝，不制造stub ACK。
6. `rootjournal/journal_test.go` 以可注入的真实`ip`参数Runner构造完整状态机纯Go测试：成功/重复Stop、未授权root UID/非/32/零Network拒绝、route/table污染拒绝、rule中途失败回滚、3阶段进程死亡后经旧journal精确恢复和仍活会话flock防抢占。host Go纯逻辑单测不构建Android x86；其后真Android arm64 Rust＋Go链接、C ABI、AArch64 ELF 16KiB和完整符号检查仍是硬门。

本批SOURCE尚未验收：根环境KSU、实际ConnectivityManager取Network、首连标准TLS/原/32、双向TCP/UDP、内核uidrange/iproute2、网络切换、Stop/CPU/性能、root-only APK、DNS/热点**NOT_RUN**。旧 `android/app` 是历史VpnService壳，不能作为此Root产品入口。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Android ARM64 A4仅在真原Go TLS/lease/Rust M4后安装单App UID独立可撤销route；fsync journal+flock防并发抢占/Crash恢复、原Rust物理scope独立终止，纯Go状态机测试；手机/ROOT尚NOT_RUN。"}
```
