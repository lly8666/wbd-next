# B6｜Android 原 M4 真实 CN/非 CN 路由收据、TCP53 透传和 TC 回答

## Baseline 与兼容设置

源头：B5 同 SOURCE `f1de67886909eec9b8aa33844e5cb62bd95da280` 的 CN8503 8431 domain/69 full/3 regexp 真固定上游 Host、ARM64 Bionic 原 Go/Rust、源锁签名 Root APK、原 Linux Normal/off Oracle 与治理均 SUCCESS；手机和服务器未授权也未实测。遵用户偏好，绝不追加未请求的防篡改/强制安全检查；TLS 默认校验 OFF（可手选）、Android App 隧道 DNS 默认 ON、物理/CN 分流默认 OFF、无额外 Go/JNI 逐包、原 Stop/UID/TUN 不变。

## 一轮四项源码与 Host 目标

1. **单一 DNS 路由决策**：`v4_android_dns_route.rs` 在原 M4 唯一 `tun.read_ip_scatter` 后分别对完整普通 IP 和同一次 readv 已获得的完整 jumbo 执行同一纯分支。只用原 `observe_ipv4_dns53` 的真实入站问题类型。CN 完整 UDP DNS → 原绑定物理 UDP `223.5.5.5`，非 CN → 原 M1/M3 AEAD + TCP appearance `1.1.1.1`，其他流量原样。Jumbo 在完整拼出后才记 DNS 观察值，防止将散列 iovec 头部误记为 DNS malformed；原 LINK20 分片、AES/PN、窗口、Stop 都不变。
2. **TCP53 与物理 TC 有区别的真实收据**：原 TCP53 保持完整 IPv4/TCP 不改写直接由原 WBD 数据通道透传，只有 `send_staged()==Some(pn)`（或 Jumbo 全部帧已成功交给原 RAW）才增加 `tcpraw`。物理 DNS reply 的 TC bit=1 只有实际逆映射并写入原 TUN 才增 `ptctun`；不把该事件等同于 App 的 TCP fallback 成功、物理 TCP 直连或 DNS over TCP 代理。
3. **按真实路径的 CN/非 CN 发包实绩**：仅冷授权 CN8503 模式中 CN 请求使用原 OS scoped UDP 发送成功才增 `cnptx`；非 CN 请求原 M3 RAW 完整复制才增 `noncnraw`，和 B3d/B4 的 `dnsraw/dnsrtun/dnsptx/dnsprx` 互补。四数读取走新的 `wbd_m0_embedded_go_loop_dns_route_receipts` ABI、原 Go 4s/terminal snapshot `V4_PUBLIC_ANDROID_DNS_B6_DIAG`，App 只接受准确固定键数字并按 Start 会话区分事件。旧 `V4_PUBLIC_ANDROID_M4_DIAG` 不改一字；数值报告旧/new 分列。
4. **真实 IPv4 Host 联合验证 + 双 ABI + Linux 保持**：独立 Rust `b6_original_m4` 两测试包含 CN/非 CN 判路、all-physical/all-tunnel/disabled 原语义、TCP53 SYN 透明透传、EDNS/partial、CN 物理 synthetic ID/TC 答复逆映射回原 TUN、非 CN M3 端点/端口逆映射、真实 IP 原地址与 DNS ID 恢复、Stop 双映射清空。Android 原 signed ELF C 符号必需、Go Linux Pulse 零值字段共享、Go 业务类、Java 根进程解析和安全导出 Host 都有 CI Gate。

## 明确未越权的产品边界

这是普通 App 已经进入原 TUN 后的 IPv4 DNS53，**不是 Android 进程 netd 系统 DNS 拦截，也不是 TCP53 物理代理、DoH/DoT/IPv6 DNS 或 Fixed/Auto/Game**。TC 应答入 TUN 后，Android App 是否按 RFC 通过 TCP 重试取决于应用/系统 resolver，现阶段不给出设备 E2E PASS。Root/netd 全局重配置、真实手机/服务器、生产性能压测不在未经明确授权的源码接线中。本轮通过 CI 只能宣称 Host/BUILD/产品 Native 产物，不等于真机浏览器完整解析。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B6在原Android Rust M4唯一TUN reader统一大小DNS包CN/非CN路径；真实TCP53原M3 RAW复制与物理TC逆写TUN计数、新只读原生ABI和Go/Root独立数值收据；旧M4历史格式与默认不变，新增真实IPv4双路径Host、签名APK和Linux Oracle验证。"}
```
