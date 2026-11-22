# B41 原Android Game2/off 双 Go TLS → Rust M4 全生产冷链（设备仍待验）

## 补足B39/B40的真实 Go 调用者，而非新增公共TLS/数据面

B39的原Rust `game_group_join_original` 可接收两个独立原Go已认证lane，B40的 `android_game_group_m4_start` 可复用1 TUN + 2 RAW M3工作器，但此前Android Go CLI的Normal/Fixed/Auto入口和Root App都不调用这套Game owner。B41新增原 `realityfront.V4AndroidGame2Product` 的**私有 Go→Rust 活体绑定**：调用原 `EstablishClientV4` 对每条真正已建FakeTCP的Net.Conn完成认证，使用同一个epoch、原Go分lane冷Policy、原Game密码与AEAD exporter，调用独立 `Detach` 后 `prepareAuthenticatedClient`、 `bindAuthenticatedClientIPv4`、`v4BindPlatformUnderlay`，由既有 `V4LinuxGameClientVerifiedGroup` 验证两份同源受保护身份/独立exporter。仅此可调用原Rust `game_group_join`、`android_game_group_raw_bind`、`android_game_group_m4_start` 和源生ready/计数回读。绝无公开C cold安装、V3降级、并行Go DATA发送线程或第二套Game/AEAD实现。

新 `v4productcli/game_android.go` 是实际 `--mode game2` 的原Root Go启动者：用户显式选定 Network 的两原AF_PACKET FakeTCP本地端口必须连续，**一条**原 `rstguard` 持久化规则匹配二者（同一`rst-guard.json`/Root Restore）后各自发送真SYN并完成原TLS，原Go旧RAW接收在Rust内核接管后 `QuiesceDetachedClientReceive`，再调用原 `androidRootRouteAfterNative` 授权已验的普通App UID/FIB路由。同一owner Stop先wait Rust整组线程及M4借用，然后依次Release每个原Go lane/组、撤销UID规则和本地精确RST规则。这是源码产品调用链，**不是设备已验证或应用自动开启**。

B41只支持`game2`+`game-fec off`+`startup-padding off`+`outer-repair off`+原auto /32；`game4`、Game FEC固定、Game2 App UDP DNS、网络旋转尚无产品实现，不能靠改App下拉框声称支持。Root App仍只提供Normal/Fixed/Auto。这次Host rstguard 新增二端口单规则/恢复语义测试，同时源门验证每个原Go TLS → Rust C入口及真实M4后Root UID接线；跨平台软件资格以**B41 SOURCE Android Dual64 Actions**为准。真实物理Android双lane SYN/两端TLS、双向M3和 Stop、CPU/RSS及传输性能全部NOT_RUN/NOT_PROVEN；旧B40只证明Rust worker链接，并不证明这批Go启动。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B41 Android原Go真实双FakeTCP/TLS受保护Game2/off入口交接B39/B40 Rust组、精确双端口RST持久所有权和UID Root路由，App/实机资格另验。"}
```
