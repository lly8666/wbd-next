# B5 原 Android Rust M4 CN8503 DNS 域名分流｜2026-11-21

**基线**：`24a7777af8e95020240413f73422c87fc263555d` 已由 Android dual64 11 SUCCESS/4 SKIPPED、签名 APK、原 Linux Normal/off Oracle、功能卡治理验证。旧 B3/B4 真实物理 UDP 与隧道 DNS 分别只在显式模式中启用。已安装普通 Android App IPv4 经选中 UID 路由进入唯一原 Rust M4 TUN reader；Android 系统 Resolver/netd 不在本次被改写。

## 本次功能接线

- Android Root UI 新增可选第三开关「CN8503 域名 DNS 分流」，默认 OFF；默认全隧道 DNS ON、全物理 OFF、TLS 证书校验默认 OFF 不变。三选一，取消所有选择时不重写 DNS。旧 Java 重载行为不变；Go CLI 同时出现三模式 flag 时，明确显式 CN 优先、然后物理、再隧道，以兼容旧程序。
- App `cn_dns_split` Intent → RootService owner thread → `OriginalGoCommandArgs` → `--android-cn-dns-split` → 原 Go Android cold parse。原 Go 已存在 `ReadPinnedCNFile` 解析真正上游 v2fly/domain-list-community SHA256 `45496d28e7a90472274fdf6c23afd43a0e478f9127dea241b628ca730863b1d6` 的 8503 规则；存留其完全相同的原始文本字节，只在一次冷授权交给 Rust，没有任何 Go/Java/JNI 逐包。
- 原 Go 真连接 FakeTCP SYN/SYNACK、TLS、受保护认证 /32、Native RAW/TUN attach 后调用新 Rust C ABI `wbd_m0_embedded_go_android_cn_dns_split_enable/effective`；Rust `v4_android_cn_dns` 冷编译 8431 domain + 69 full + 3 regexp 到 HashSet/RegexSet。原 API 返回规则条数 8503 作为冷读回；RegexSet 引入可重复锁版本的 Rust `regex 1.12.2`，`Cargo.lock` 同 SOURCE 锁定依赖。
- **单个原 Rust M4 TUN reader** 在真实完整 IPv4/UDP53 QNAME 上栈解析标签，CN 仅向已绑定当前 Network 的原物理 UDP `223.5.5.5:53` socket 发送，非 CN 使用原 `TunnelDnsUdpFlows` 和 M1/M3 密文走 `1.1.1.1`。既有物理 DNS ID/QNAME/源 IP/端口还原→原 TUN 写入，与原 M3 AEAD/PN/replay 认证→逆映射原 TUN 写入，分别复用原 owner；大包路径、早到 M3 回复、Stop 清理规则与两个映射同代。旧模式无匹配器，执行路径及默认完全不变。
- Go 固定 `CN_DNS_SPLIT_ENABLED/FAILED` 日志接到本会话 Root Service Event，安全诊断新增 `cn_dns_split_native_cold/live`；实际物理/隧道发送与写回沿用 B3d/B4 的真实 `dnsptx/dnsprx/dnsraw/dnsrtun`，不伪造新计数。
- Host 验证新增 Java selected/all UID、旧接口、三开关互斥、两路收据轮替；Go 同源 pinned raw 内容复制；Rust 测试合成 domain/full/regexp/边界及真的固定上游 8503 匹配；签名 APK `nm -D` 显式检查新两个 C ABI 符号，Linux stub 与 Go Pulse 保持原服务端兼容。

## 不能越界的验收结论

CI Host 的 DNS wire、真实固定 CN 规则解析、Native ARM64 构建与签名 APK、Linux Oracle 必须 **逐 Job 同 SOURCE** 判定；即使全绿也不是 Android 实体设备上 netd 系统 DNS、App 浏览器解析字节、TCP53、IPv6、Fixed/Auto/Game 或真实吞吐 PASS。普通 App 已进入 TUN 才执行本 DNS 分流，未来系统 resolver 流量的接管和 TCP fallback 另接功能卡。没有任何手机/服务器改动，没有新防篡改、强制 TLS 或防黑客门。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B5将已固定来源的CN8503完整domain/full/regexp规则冷传入原Rust M4，接通单TUN reader CN物理DNS/非CN隧道DNS真实双路径，新增App/Go/Native实际接线、Host/JVM/Rust匹配及报告，保留兼容默认。"}
```
