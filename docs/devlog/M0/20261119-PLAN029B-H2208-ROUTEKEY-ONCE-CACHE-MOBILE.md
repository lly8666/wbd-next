# H2208｜轻量离线RouteKey一次派生、私有缓存及移动平台冷设置

用户本轮要求M0实际续做：8–32位同短Key双方离线生成原32B route-key，算法轻量且**算一次、缓存复用**；包括移动平台，服务端仍单网卡/单IPv4。

本次基于H2206 PASS_SCOPED + H2207在途代码，仅触及Go冷入口/Windows源码锁装配/移动设置辅助/CLI/文档，**不改TLS wire、原HMAC分类、Rust包热路径、FEC/Game/TUN、Stop**。

- Go v2: `PBKDF2-HMAC-SHA256` 4096次、域隔离salt `WBD-V4-ROUTE-KEY-PBKDF2-SHA256-v2\\x00`；8–32大小写敏感ASCII字母/数字，同短输入导出相同32B。旧H2207 v1 240000次未验稿不与v2混用；保留专家32B hex及0600文件兼容。
- `v4routekey.Resolve` 使用每用户+角色+serverName稳定私有路径：首次生成/输入变化才做4096次PBKDF2，写0600原子缓存；后续每次Go冷启动仅做一次HMAC核对并读取32B缓存，不在lane/reconnect/逐包循环做KDF；缺文件首次创建，损坏、权限过宽/版本不符fail closed。Linux支持`--route-key-file` (0600) 和可选`--route-key-cache-file`，不用每次把短Key写argv。
- Windows 原Go CLI source-locked复制统一Go包，GUI字段/参数目录/秘密脱敏一起加入原manifest并以精确result_blob冻结；GUI有普通短Key和可选旧hex字段，不能同时非空。
- Android主线只有`VpnService`未连JNI：新`RouteKeyStore.kt`与独立向量JVM测试只提供设置侧轻量派生、app私有noBackup AtomicFile缓存，**真实原Go JNI/Android产品联网 NOT_RUN**。OpenWrt UCI只存0600短Key文件路径，procd引用独立私有缓存，不传short secret argv，服务仍默认disabled，真实路由器NOT_RUN。
- H2208首个源码`8dabc266`：旧`assembly blob mismatch: linux.go`已通过本次manifest同步修复，[Action44366214109](https://github.com/lly8666/wbd-next/actions/runs/44366214109) cheap preflight SUCCESS；随后旧Go windows source compile [Action44366213787](https://github.com/lly8666/wbd-next/actions/runs/44366213787) 首次FAIL因`cache.go`控制字面量/NUL换行，针对首个错误已在`7dc0e6a`修好。首次[governance](https://github.com/lly8666/wbd-next/actions/runs/44366213924) Governance本体SUCCESS，功能卡因缺`feature-impact` FAIL；本次同步补齐，不抹历史FAIL。完整同SOURCE Windows/Linux/ARM/Android GUI/系统连接结果待Action实证，不擅自写PASS。
- 安全取舍：PBKDF2降至4096不是离线抗暴破保证；8位随机英数字仅约47.6bit，人工字符串更弱，KDF无法创造熵；推荐24–32位独立随机，不能宣称同256bit原随机key安全强度。缓存文件即敏感密钥，0600和Android app私有隔离，勿上传、打印、放日志。启动密钥变更两端需同步；原32B文件仍可用。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient","windows-portable","android-vpn-shell","openwrt-package"],"reason":"H2208本地短RouteKey v2轻量一次派生私有持久缓存、源锁GUI字段、Android未接通设置辅助和OpenWrt受保护短Key文件；保持原TLS和移动设备NOT_RUN。"}
```
