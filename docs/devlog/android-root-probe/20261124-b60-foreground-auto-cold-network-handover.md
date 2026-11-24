# B60｜前台自动冷 Network 恢复：原 Go/Rust 全链复用

**起点** B59b HEAD `91ce8023f586e6a3c0a57e20b1995a4d8f325f38`；最近实际产品 SOURCE `ccc5d47868c34dfee2c2c422207e53573ee9c360` [Dual64 #45220240360](https://github.com/lly8666/wbd-next/actions/runs/45220240360) 11 SUCCESS/4 SKIPPED：B59 Host/双ABI/签名ARM64 APK/原Linux Oracle通过，Android真机及新版本 E2E/性能未验。

本批在原 B49/B52 手动切换基础上新增用户显式开启、仅当前前台 Activity 有效的**自动冷重连**。原生产 Service `ConnectivityManager.NetworkCallback` 的 selected physical loss/link/capabilities/blocked 仍请求原 Go/Rust owned Stop；仅在旧会话已 READY、Rust M4/UID 路由 joined Stop 真实收据、旧 Go 进程退出并归还原 Root owner 后，复用当前已有1Hz前台 UI refresh 重新选择 Android 当前真实物理 Network；当前系统 active physical 优先，只有一条 LAN-only 实体网络时也可选。然后仅调用原 Activity `start()`：真实 Network handle/ifindex/IPv4/MTU、原 PackageManager App/UID、私有凭据、FakeTCP/TLS/Admission、/32、Rust M4、内核私有路由继续由现有产品拥有。

开关默认 OFF；没有后台 Root 重启、第二TUN/RAW reader、Go/Java逐包处理、新计时器或新协议。手动 STOP/恢复/切换 Profile、离开前台、无新 Network、旧 joined Stop 失败或 START 失败则取消当前接续，没有无限重试/无缝热迁移。新 native 一代成功后可响应下一次真实 selected Network 变化。Host Java 执行原生产一次性决策的 Stop/Network/取消条件，源码门核 Service→Activity→原 START，双ABI/签名APK/Linux Oracle 按本 SOURCE Actions 判软件资格。实体切网、真实App TCP/UDP、CPU/延迟仍 NOT_RUN；不操作个人设备、服务器、main/M0，不重复 hosted KSU/TAP。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B60原Root App可选前台自动冷Network恢复，复用Service原NetworkCallback、owned Go/Rust Stop与完整Activity START；仅Host/正式APK软件门，无新数据面。"}
```

## B60a｜保留原 B52 START 按钮的确切生产接线

B60首版给原普通 START 按钮额外写了 `autoHandover.cancel()`；现有 `start()` 在实际成功派发时已经按前台选项 `arm()`，失败时也会 `cancel()`，因此该调用重复，并让旧 B52 源锁断言 `connect.setOnClickListener(v->{coldSwitch.cancel();start();})` 无谓失败。本次只去掉一个冗余 Java 调用，自动冷重连接线和原 Go/Rust 完全不动；原 SOURCE 保留，CI 仅采新 SOURCE 实际状态。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B60a消除原普通START处多余的自动重连取消调用，兼容B52已有生产按钮源码门，B60重连策略及Go/Rust路径不变。"}
```
