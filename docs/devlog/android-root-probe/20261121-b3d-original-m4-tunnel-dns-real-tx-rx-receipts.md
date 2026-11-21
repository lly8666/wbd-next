# B3d｜原 Android M4 隧道 DNS 真发包/真回 TUN 接线

A54 `ea480c5e9559c6ab3e60cd77c2fe965df229a308` 的 B3 冷授权与签名 APK/双 ABI/原 Linux Oracle 通过；此前只能看到冷授权，不能判定真实发送、认证回包和 TUN 写回。

本次在原 Rust M4 TX 的同步 RAW sendto 成功处对已改写并经 M1/M3 密文封装的 DNS UDP53 IP 累计 `dns_tunnel_raw_copied`；Jumbo 仅全原 M3 LINK20 片 kernel copied 后计一次，部分发送/中止不能冒充完成。原 Rust M3 AEAD/PN/replay/重组、TunnelDnsUdpFlows 逆映射并由 AndroidOwnedTun 写入成功后才累加 `dns_tunnel_reply_tun`。启动前已授权 early DATA 同样计数，不用 Go/TLS ready 冒充业务。

扩展现有原生 DNS ingress 只读 C ABI →同一 Go Bridge Pulse→原有每秒采样 Go 固定业务类/数值日志→Root Service Event→App 本次会话 `tunnel_dns_live`。B3 兼容默认（App DNS ON、TLS 验证 OFF）不变；没有 Go/JNI 逐包、第二 reader、系统网络更改或额外安全检测。

Host JVM/Go 测试、原 Rust DNS inverse-map、source gate、ARM64 APK 和原 Linux Oracle 需以新 SOURCE Actions 结果为准。即使真实原 TUN 已写，也不能声称 Android 系统 DNS/netd 接管或 App 成功解析；CN 物理分流、TCP53、IPv6、Split、Fixed/Auto/Game 仍 NOT_PROVEN。未经另行授权不操作实体真机/用户服务器。

B3d1 跨平台构建修补：`V4PublicLoopPulse` 的 Linux stub 同步增添两个 Android-only 零值字段，保证共享 Go 源码和 Linux 原服务端 Oracle 编译。Linux 数据面、业务默认与加密协议均未改变；源码门检查双侧结构体一致。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B3d在原Rust M4同步RAW复制和原M3认证/逆映射TUN写入处记录DNS实绩，经原Go Pulse和Android App展示，不修改兼容默认或协议。"}
```
