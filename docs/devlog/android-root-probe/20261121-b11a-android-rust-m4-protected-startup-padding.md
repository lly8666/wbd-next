# B11a｜Android 原 Go/Rust M4 startup padding（原生功能接线）

基线 SOURCE `6180ede74857de227f1d5eb6f51722e48475bc68` 的原Go CLI已支持 `--startup-padding=off|tls|flows`，但 Android产品硬拒绝、Android Bridge对应函数为unsupported，只有Linux调用原Rust `TunnelStartupPadding`。本片只接原Native控制/数据面，不伪称App可选或实体实测。

- Go经真实TLS authenticated ColdSnapshot `StartupPaddingMode` 后调用同一个 `configureNormalStartupPadding`，Android Bridge 调原Rust C ABI并对 mode/零计数做真实冷读回。
- 同一个 Android Rust `Entry` 配置原方向分离的 TLS epoch/种子、256条flow上限，原有默认off路径仍没有额外填充。完整 IPv4 TUN读v并经过现有DNS tunnel rewrite时，只有普通不分片LINK根据原 20–30条/2–3秒选择原M3 AEAD认证填充；room取真实记录预算、外层IPv4 MTU减40与原始M1 slab上限。
- `ProtectedScopedOwner` 使用已存在 `seal_normal_off_one_padded`，不生成第二套PN、AEAD或网络线程。原 M4 sendto确定成功才累加已复制padding记录/字节，原Go停前原计数可读，Stop/join保持同一owner。
- 不对物理DNS直连、Jumbo LINK fragments、FEC2源/repair、Health填充；不移除 Android Fixed/Auto/Game拒绝门。不额外加安全检查/引入新协议。
- 本 SOURCE 将依赖 ARM64 Bionic Rust/Go双ABI、Host源码门、原Linux Oracle；实体网络和性能为NOT_RUN。B11b再在签名App暴露off/tls/flows选择。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B11a把原Go经TLS认证的Normal startup padding调用连到Android原Rust M4 same-owner sealer、真实RAW复制计数和冷读回；App选择后续，Fixed/Auto仍未接。"}
```
