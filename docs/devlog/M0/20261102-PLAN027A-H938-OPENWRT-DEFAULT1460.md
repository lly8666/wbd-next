# PLAN027A H938｜额外客户端平台默认量纲检查

统一1460默认时审查Android/OpenWrt：OpenWrt opt-in procd包装器虽继承新版Linux V4 CLI默认1460，但UCI没有外层字段；本批给disabled UCI 添加唯一 `outer_mtu='1460'`，init合法数字 576..1500 且无L2，调用同一 `--outer-mtu`。不生成inner配置，不改变secret fd、原生service enable/Stop或重算预算。真实OpenWrt设备 OS/认证未测试。

Android `WbdVpnService.kt` JNI目前不存在，`Builder().setMtu(1200)` 是**内层OS占位**，不能静默替换为外层1460也不能据此宣传用户MTU已应用；README明确未来接原始TLS/Rust预算后的外层默认1460/最大1500，保留不接通安全门。

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"Make disabled OpenWrt UCI wrapper explicit default outer full IPv4 IP1460 without inner override; document that Android disconnected VpnService 1200 is an inner placeholder not an outer default or Applied proof."}
```
