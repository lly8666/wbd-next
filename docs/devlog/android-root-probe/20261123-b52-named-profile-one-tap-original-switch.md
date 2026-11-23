# B52｜四套连接配置与真实物理Network一键接续原Go/Rust

## 本批基线
B51a `09aa7049ebbb5f157ef3158687b5c943d69150fe` [Android Dual64 #45172614955](https://github.com/lly8666/wbd-next/actions/runs/45172614955) 11 SUCCESS/4 SKIPPED、[治理 #45172614991](https://github.com/lly8666/wbd-next/actions/runs/45172614991) SUCCESS；此前多配置/凭据保存已有正式ARM64 APK及Host资格，**没有Android设备快速切换或TCP/UDP应用E2E证据**。

## 生产功能实际改动
- 正式Root Activity四槽不再只是数字：每次用户进入或修改配置时，读取原本地 `RootConnectionProfileStore`，显示已保存的**名称及 Normal/Fixed/Auto/Game2/Game4 mode**；不新建后台轮询/Android Listener/Go回调。
- 新 **“连接此配置／切换到此配置”** 按钮。用户选好当前真实 Wi-Fi/蜂窝/以太网 Network、指定槽位后，查该槽现成配置及该槽专属Keystore登录；无配置/密码时直接提示先保存，不能错误借用其他服务器的密码。未运行时载入同槽Cold配置+Key并调用**同一个**旧 `RootClientActivity.start()`。
- 旧Root正运行时，直接向原 `RootClientService.STOP` 发出一次停止指令，保存目标**槽号+Network handle/ifindex/IPv4/MTU**于 B49 已有 `RootColdNetworkSwitch`。仅在 B48 真实 `previousOwnerStopConfirmed` 与旧 owner 已彻底退出、无在途START后，使用 B49 现有1Hz前台刷新精确读回真实Network；再载入冻结槽号并执行原Start恰好一次。旧Stop失败/Network变化/本页面退后台/手动STOP、START、修改配置均取消，**不会自动从Android onLost或后台事件Root重连**。
- 原Go标准 FakeTCP/TLS/认证/租约，Rust唯一M4/TUN/RAW、FEC和私有UID规则、owned Stop全部复用旧生产入口。未增加Go逐包FFI、DNS/netd劫持、后端代理、线程/定时器、额外安全加固。
- 扩充**同一个生产** `RootColdNetworkSwitchTest`，覆盖跨配置冷切换slot绑定、物理Network一致、一次性消费、旧Stop失败/取消与B49老Network开关回归；签名APK源码门同时核验Service/原Start实线。仅Host/BUILD可能PASS，实体多服务器切换和真实App TCP/UDP、性能继续NOT_RUN/NOT_PROVEN。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B52四命名Root配置实际显示名称/mode、单击连接或跨配置冷切换；原B48 owned Stop与B49真实Network核验后唯一复用原START，纯JVM/签名APK源门，不加网络热路径。"}
```
