# B4｜Android 原 M4 物理 DNS UDP/53 可选生产模式

## 任务与向后兼容

SOURCE 起点 `b9a9c1764e41dd66e0e2b2c61dc65005cb72e656`：B3d 正式签名 APK、原 Go/Rust ARM64、原 Linux Oracle 成功；物理 DNS socket、真实问答 ID/QNAME 逆映射与 TUN writer 早已存在，但 `android_dns_physical_ready` 恒为 OFF，生产 App/Go/Rust 没有授权接线。依用户要求，本轮不做防篡改、防黑客、强制 TLS、额外防御性检测；也不擅自对真实手机/服务器进行部署。

本轮新增可选模式 **physical App UDP53**，不改变默认：
- Root App 原隧道 DNS 默认 ON、TLS 校验默认 OFF，物理 DNS 开关默认 OFF。二选一，取消两者则原始 TUN 数据不做 DNS 改写。兼容旧 Java argv 重载；两个 CLI DNS flag 同时传入由显式 physical 优先，不拒绝旧调用。
- Go `--android-physical-dns` 只在 Android 原客户端配置有效，独立于 `--tls-verify-server`。原 Go 完成 SYN/SYNACK→标准 TLS→受保护 Admission /32→原 Native M4 RAW+TUN 后调用 Rust cold grant/effective，同一个 generation 在 M4 start 时开真实物理 `223.5.5.5:53` UDP Socket；不启动第二 TUN reader，不由 Go/Java 逐包。
- Rust 使用现有物理 Scope/socket `AndroidBoundPhysicalDnsUdp`、唯一 M4 reader、`PhysicalDnsUdpFlows` 有界原 5 元组/ID/QNAME 逆映射；解析器原地址/端口及 ID 恢复，写回原 TUN，Stop/Network 变化沿用已有 owner 生命周期。显式 physical 不混进 Tunnel DNS 的原 M3 逆映射计数。
- 现有 Native 只读 ABI/Go 1Hz Pulse 增加 `dnsptx`（真实物理 UDP question send 完成）、`dnsprx`（物理回复逆映射真实 TUN write）和 `dnsperr`，传至 Root Service 固定事件及按当前启动隔离的 `physical_dns_native_cold`/`physical_dns_live` 报告；原 B3d `dnsraw/dnsrtun` 不变。Go/Linux 原 Pulse 添加 Android-only 零值字段保持共享源码编译。
- 增加 Java selected/all-app/legacy/双开优先级 Host 用例、Go fixed business classes 测试、原 Rust 双 App 原解析器逆序回答/Stop 测试，调整 b2c2b Rust 固定测试收据由 7→8 项，同步源码门与 ARM64 ELF 动态导出符号检查。

## 不夸大本轮结果

这个可选模式是“**所有进入原 TUN 的普通 App UDP/53 请求走物理 223.5.5.5**”，不是利用 CN8503 规则把 CN 与非 CN 域名自动分到不同上游，不是 Android 系统 DNS/netd 通道，不含 TCP/53、IPv6、DoH/DoT；真实 App DNS 成功与手机端性能仍待同 SOURCE 授权实测。默认隧道模式仍按原 B3/B3d 走 WBD。下一片功能卡需把验证过的 CN8503 QNAME 匹配器以冷授权快照接入 Rust M4 分流，保持物理 CN 与隧道非 CN 同一代原 TUN reader，不新增 Go/JNI 逐包。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B4将既有原Rust M4真实Android物理DNS UDP socket及逆映射完成App/Go/Rust全生产链显式接线，并增加真实收发计数、旧接口兼容/Host/Rust与正式签名APK验证。保持B3隧道默认与TLS兼容设置。"}
```
