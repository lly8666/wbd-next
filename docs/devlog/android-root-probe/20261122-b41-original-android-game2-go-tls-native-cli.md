# B41 原Android Game2/off 双 Go TLS → Rust M4 全生产冷链（设备仍待验）

## 补足B39/B40的真实 Go 调用者，而非新增公共TLS/数据面

B39的原Rust `game_group_join_original` 可接收两个独立原Go已认证lane，B40的 `android_game_group_m4_start` 可复用1 TUN + 2 RAW M3工作器，但此前Android Go CLI的Normal/Fixed/Auto入口和Root App都不调用这套Game owner。B41新增原 `realityfront.V4AndroidGame2Product` 的**私有 Go→Rust 活体绑定**：调用原 `EstablishClientV4` 对每条真正已建FakeTCP的Net.Conn完成认证，使用同一个epoch、原Go分lane冷Policy、原Game密码与AEAD exporter，调用独立 `Detach` 后 `prepareAuthenticatedClient`、 `bindAuthenticatedClientIPv4`、`v4BindPlatformUnderlay`，由既有 `V4LinuxGameClientVerifiedGroup` 验证两份同源受保护身份/独立exporter。仅此可调用原Rust `game_group_join`、`android_game_group_raw_bind`、`android_game_group_m4_start` 和源生ready/计数回读。绝无公开C cold安装、V3降级、并行Go DATA发送线程或第二套Game/AEAD实现。

新 `v4productcli/game_android.go` 是实际 `--mode game2` 的原Root Go启动者：用户显式选定 Network 的两原AF_PACKET FakeTCP本地端口必须连续，**一条**原 `rstguard` 持久化规则匹配二者（同一`rst-guard.json`/Root Restore）后各自发送真SYN并完成原TLS，原Go旧RAW接收在Rust内核接管后 `QuiesceDetachedClientReceive`，再调用原 `androidRootRouteAfterNative` 授权已验的普通App UID/FIB路由。同一owner Stop先wait Rust整组线程及M4借用，然后依次Release每个原Go lane/组、撤销UID规则和本地精确RST规则。这是源码产品调用链，**不是设备已验证或应用自动开启**。

B41只支持`game2`+`game-fec off`+`startup-padding off`+`outer-repair off`+原auto /32；`game4`、Game FEC固定、Game2 App UDP DNS、网络旋转尚无产品实现，不能靠改App下拉框声称支持。Root App仍只提供Normal/Fixed/Auto。这次Host rstguard 新增二端口单规则/恢复语义测试，同时源门验证每个原Go TLS → Rust C入口及真实M4后Root UID接线；跨平台软件资格以**B41 SOURCE Android Dual64 Actions**为准。真实物理Android双lane SYN/两端TLS、双向M3和 Stop、CPU/RSS及传输性能全部NOT_RUN/NOT_PROVEN；旧B40只证明Rust worker链接，并不证明这批Go启动。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B41 Android原Go真实双FakeTCP/TLS受保护Game2/off入口交接B39/B40 Rust组、精确双端口RST持久所有权和UID Root路由，App/实机资格另验。"}
```

## B41a 首次SOURCE失败的精确修正

SOURCE `dd693e34df6426cb3b06a41cd6138865d9c0915a` [Dual64 #45033149984](https://github.com/lly8666/wbd-next/actions/runs/45033149984) 7个并行Host Job SUCCESS，但`arm64-native`在Go/Cgo而非Rust M4失败：新 `bridge_v4_game_native_android.go` 的 `import "C"` 前原Go业务说明与C头文件注释相连，Clang把带 Unicode 箭头的Go文本当作C预处理输入（unexpected character U+2192）。因此其后APK/Linux oracle均SKIPPED，**原B41不得标记Go/Build PASS**。B41a仅调整此前已经实际写入的Cgo前导注释到Go普通注释范围，所有TLS/RAW/TUN/UID算法与工作器不变。最终资格看本次修复SOURCE新的同源Actions，失败历史保留。

## B41b 第二次SOURCE失败：Host门证明CLI分发实际上未提交

B41a `487e246251ba854707fd97d44688bb1e4f6e63b0` 的 Android `arm64-native` 确实通过同源ARM64/x86_64 Go/Rust链接（说明双TLS控制端可编译），六个Host Job也通过；但签名APK前置 `android/root-app/ci/test-network-scope-gate.sh` **FAIL**。该门第一个B41检查发现最终 `linux.go` 中既无 `return runAndroidGame2(...)`，Android平台条件仍拒绝所有Game：第一次Git Tree分阶段提交中，原CLI文件改动被后来创建的基于旧Tree的阶段覆盖。因此B41a签名APK并未执行，独立Linux Oracle当时仍在跑。软件编译成功不得冒充Game2入口已经启用。

B41b以 **B41a最终HEAD为基础** 重新实际写入同一个原CLI `linux.go`：Android选中 `game2/off` 且FEC/StartupPadding/App DNS/轮换全未开启时，实际分流 `runAndroidGame2(ctx,cfg,ifindex,tun,&connected)`；Game4/其他未连模式继续拒绝，Linux保持原native game路径。保留真实源门及首次失败，**不删断言、不为了绿色CI伪造ELF或App按钮**。后续B41b新SOURCE同源Actions重新验收Go双ABI、签名Root APK与原Linux Oracle；设备和CPU仍NOT_RUN。

## B41b同源软件收据完成：确实接到原Go CLI和签名APK

原Go产品SOURCE `7fc34e6a7848662cb5bc6eb0d639f96007014369` 的 [Android Dual64 #45033871118](https://github.com/lly8666/wbd-next/actions/runs/45033871118) 已 **completed/success：11 SUCCESS / 4 SKIPPED**。`arm64-native` 是两ABI真实NDK Go/Rust ELF编译、Go Game2原始包导入和Rust符号链接成功；`root-arm64-app` 包含先前B41a失败的**完整真实CLI分发源门**，以及无VpnService的签名ARM64 APK和原Go/Rust符号/加载检查，均SUCCESS。`linux-x86-original-server-d2-s0`、`linux-original-server-normal-off`与`arm64-cuttlefish-host-admission` Host门也均SUCCESS。B41b [Feature catalog #45033871248](https://github.com/lly8666/wbd-next/actions/runs/45033871248) SUCCESS（Governance Job SKIPPED）。旧B41 `dd693e` 的Cgo前导FAIL及B41a `487e246` 的真实CLI分发未提交的APK源门FAIL均保留，不覆盖。

**严格成果：**现在显式手工Android CLI `--mode game2` 的确在同源源码编译内走原Go双真实TLS控制入口→原Rust Game2 B39/B40组M4→既有Root UID路由；签名App UI仍**没有**Game2模式选项。CI的`arm64-native`证明代码/动态符号编译和链接，不证明实体设备能完成真实两条TLS、每lane内核RAW和TUN数据、双向Game2回包、Rust receipt/stop或速度CPU。Android guest/实体手机均NOT_RUN。
