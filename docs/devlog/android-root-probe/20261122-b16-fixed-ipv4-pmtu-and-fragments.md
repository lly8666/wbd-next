# B16｜Android Fixed 原 IPv4 DF0 分片、Options/已有片与 DF1 PMTU

基线 SOURCE `f076f18dd20350f1ca5656400043a374cfd9f2f8`（B15 Host/原生构建通过，但 Fixed Go 产品入口仍关闭）。本轮从真实产品数据流找出 B15 遗留：按 `source[6]&0x3f` 判断会把 DF1 当 DF0；只支持 IHL20，且没有 ICMP3/4。因此常见 DF1 TCP 大包被错误分片，而不是得到 MTU 反馈。

- 新增纯生产模块 `v4_android_ipv4_mtu.rs`：DF0 大 IPv4 包沿原 IPv4 ID、MF、绝对偏移和头校验和分片，IP Options 中 copy-bit=1 的参数在后续片保留；已经是 IPv4 片的大包只继续拆片。UDP/TCP end-to-end 校验和及 payload 原样，不使用 Normal LINK20。
- DF1 大包回给本机原 TUN 一条标准 ICMPv4 Type3 Code4，携带原IP首部和前8字节以及唯一 Rust Fixed 冷预算推导的 next-hop inner MTU；不发送错误的 FEC2 来源，不新开 worker/FD/路由或主动 PMTU 探测。
- 五个实字节编码测试由 Android-only 文件搬到 Host 可运行的**同一纯生产 Rust 模块**：完整4020B分片与逐字节恢复、DF1 PMTU/IP/ICMP checksum、IPv4 options copy-bit、已有MF/offset、坏 option。B2C2b原CI脚本追加 `cargo test --lib b16_`，不为本片单独造重型环境。
- Android Fixed 编码好的每个片仍经原`send_android_fixed_source`→同源FixedStream/M3 AEAD/PN→同一RAW TX，最多8片一轮；Normal/off小包原路径未动。OriginalGo Fixed/Auto 产品入场仍关，真机/两端应用交付 NOT_RUN。没有工程必要的异常流量框架不做。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B16 actual original Android Fixed M4 IPv4 DF0 continuation and DF1 ICMP PMTU use same TUN and FEC2 owner; real Host byte tests added"}
```
