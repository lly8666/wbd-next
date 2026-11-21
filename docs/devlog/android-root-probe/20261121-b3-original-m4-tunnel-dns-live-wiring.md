# B3｜Android Root：原M4隧道UDP/53正式冷控制接线

## 目标与来源

同源main已合并到实验，A52 SOURCE `33fa7f7032f5bcbb54a3b6d857623cf8e31b9ec2` 11 SUCCESS/4 SKIPPED。项目功能卡 `android-root-native-client` 默认待开发的 DNS 含 1.1.1.1 隧道与223.5.5.5 CN物理。此前实际原Rust `v4_android_dns_udp_flow.rs` 的64事务槽、12秒/元组/ID/QNAME反向映射/完整IPv4和UDP校验、唯一M4 TUN reader、M3认证后回复逻辑均已编译和Host测试，但生成会话一律 `android_dns_hijack_ready:false`，Go签名用户流绝无激活入口。本轮打通第一个真实生产子链，不冒称System Resolver和CN Split。

## 产品源真实变化

1. Root UI增加明确“进入WBD TUN的普通App UDP/53 → 1.1.1.1；不覆盖Android系统Resolver”的复选框，默认ON；Service把实值透传唯一原Go argv，不走JNI/DATA回调。Java原 argv Builder维持可回退OFF，覆盖开/关 Host断言。客户端原Go解析 `--android-tunnel-dns` 仅Android且需要真实已选普通App UID路由，原Go CLI默认OFF。
2. `V4LinuxClientProductConfig.AndroidTunnelDNS` 仅在 Android 根原客户端被接受。原Go FakeTCP/TLS/受保护Admission/自动/32写入OS并回读，原Rust Commit、相同物理Network的RAW RX/TX+OwnedTun绑定之后，M4 Start之前，新 `enableAndroidTunnelDNS` 原Go→Rust native C ABI调用实际Rust `wbd_m0_embedded_go_android_tunnel_dns_enable`。Native核对客户端phase、feature3、自动/32、同代物理接口、同代RAW pair/TUN、未有workers、未有物理DNS/重复授权，清空本代旧事务，标记单一 `android_dns_hijack_ready`。随后通过只读同代 `wbd_m0_embedded_go_android_tunnel_dns_effective` 验证1，才打印 `V4_PUBLIC_ANDROID_TUNNEL_DNS_EFFECTIVE enabled=1 original_m3=1 system_resolver=NOT_CAPTURED cn_split=NOT_ACTIVE`。失败时原Go产品Close/Stop；Linux独立native bridge永远拒绝Android专属授权。
3. 原Rust现有唯一 M4 TX readv：仅捕获已进入TUN、非碎片、标准QNAME完整的应用UDP53，当前已授权时重写目的1.1.1.1、保留原查询目标/源端口/ID/QNAME于本代64槽，按原M1/M3 AEAD+PN/Seq与LINK/RAW发送。原Rust RX仅经真实M3 AEAD+unique PN/replay+完整LINK/32租约后接收来自1.1.1.1:53且synthetic源端口匹配的响应，验证QNAME、ID、地址/长度，恢复原应用DNS目标的源IP/端口、IPv4/UDP校验再写唯一真实TUN；任何未匹配包不伪造合法DNS。原owner Stop撤销映射，绝不增加Socket/新TUN reader/Go每包中继。
4. CI：签名ARM64 APK必须包含实际App→Service→Go CLI开关；同源原Android ARM64/x86 Rust必须导出两个native C ABI；原Rust DNS Host含两个来自不同原DNS解析器的真实IPv4/UDP查询与回复逆映射/Stop测试；Linux原Go/Rust Oracle保持原件；源锁脚本检查实际全链，不能凭文案生成PASS。新SOURCE CI未返回前记候选。

## B3b｜同源产品CI发现源码门误报；冷授权终端凭据
B3首次产品Action #44891389121 已证明Go/Rust双ABI构建、真实原Rust M3、B3新逆映射1/1 PASS和此前7/7 DNS测试PASS；正式APK Job的source-gate第527行误认原Rust `TunnelDnsUdpFlows::\n is_tunnel_reply_candidate` 跨行书写为未接线。B3b改用原owner类型标记与原方法标记双断言，不改任一认证/UDP生产字节。Root安全诊断新增原Go Rust native readback `TUNNEL_DNS_ENABLED` 与确切失效 `TUNNEL_DNS_FAILED` 两枚固定枚举，Service只接收已锚定原Go时戳+标记，不保存stdout/私有DNS QNAME，报告将其区分于仅勾选UI和System Resolver接管。精确原JVM测试覆盖成功、失败阶段回读。前次Action失败保留，不假追认APK PASS。

## B3c｜Root安全报告结构化区分原Rust DNS 冷授权
Android Safe Diagnostic 新增固定 `tunnel_dns_native_cold` 字段：同会话 Rust native enable + effective readback 才是 `RUST_COLD_ENABLED_APP_TUN_UDP53_ONLY`，原Go错误固定枚举得 `COLD_NATIVE_GRANT_FAILED`，没有本代证据为 `NOT_OBSERVED`。这不是系统DNS，更不是成功解析/转发证据。Host JVM测试覆盖两个连续generation时前代标志不得泄漏；旧Root与Go协议不动。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B3c保持真实M3隧道UDP53开关，增加同会话原Rust DNS native授权/失败可读诊断字段与单元回归，功能卡记录此变更。"}
```

## 明确尚未完成

**这是产品M4捕获UDP/53的真实开关，不是Android系统 DNS 接管。** Android netd/resolv 私有DNS并不一定经过已选择App UID规则：没有改变Android系统DNS/NAT，System Resolver捕获、CN8503 QNAME选择→223.5.5.5同代物理UDP/TCP、TCP53分片、AAAA/IPv6、直连真实IP路由、Fixed/Auto/Game的Android RustM4皆未据此取得功能准入。原 `wbd_m0_embedded_go_loop_dns_ingress_observed` 的 `hijack_enabled=0` 继续表示没有系统级DNS捕获资格；独立 tunnel-only cold effective=1 是不同事实。后续按功能卡逐段实现并对真实设备提供可读证据，严格区分Host、编译、同源真实网络。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B3修复原Android Rust M4 DNS双门恒false导致64槽隧道UDP53永不可用：经原Go TLS/租约/RAW/TUN真实冷授权与只读同代回执，Root UI/CLI真实开关，原M3逆映射/Stop测试和双ABI导出；系统Resolver/CN/Fixed/Game未冒充通过。"}
```
