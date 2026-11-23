# B53｜Android Root 四套已命名连接统一 SAF 备份／恢复

继B52 `aeebc9103919906a33ed9768f0dc56dd55020345` 的前台一键跨Profile Stop→START 接线（产品CI [#45182581375](https://github.com/lly8666/wbd-next/actions/runs/45182581375)，本SOURCE另判），日常调试版APK更换签名会丢私有NoBackup配置。原B26仅能逐套导出目前的 `RootConnectionSettings`；B50已保存4个常用Profile却无批量迁移入口。

本批增加**真实4槽整体非密钥配置备份/恢复**：
- `RootConnectionProfileBundle` 只有本地文件头与四段长度，由**原 `RootConnectionProfile.write/read`** 包住原B22/50 `RootConnectionSettings` Codec；保留四槽名字、Server/SNI、账户、IPv4 MTU、普通App UID选择、all-app绕过、三DNS、FEC/Normal/Game、Health、直连CIDR，无密码、RouteKey、TLS CA、旧 Android Network handle。最大36KB，单次SAF交互；不新增运行时协议、TUN Reader、RAW Socket、线程或Worker。
- 正式Root App新增“导出全部4套配置”“恢复全部4套配置”Android SAF按钮，导出从真实配置槽取不可变快照，导入完整解码后逐槽复用原 `RootConnectionProfileStore.save/delete`；空槽仍空。导入覆盖的槽会删除**原本该槽本机Keystore记忆**，避免把旧Server密码套到新Server；原Go/Rust当前会话、私有UID规则、原PhysicalNetwork完全不变。导入后的槽必须由用户在本机重新保存凭据才可使用B52一键连接。写入异常时提示检查可能已写的槽，不假称四槽事务原子。
- 纯Host `RootConnectionProfileBundleTest` 真实运行原四槽Settings/Profile Codec，覆盖Normal/Fixed/Game、空槽、模式/名称/UID/MTU/Health、超上限与残余输入，正式APK源码门检查端到端按钮/SAF/原存储调用。仅按本SOURCE的Auto Actions证明Host与编译；实体手机、应用E2E、性能依旧NOT_RUN。

不会改动 Linux/Windows 原生协议、TLS、加解密或安全默认值；main/M0不写。保留 B52 首次 Governance FAIL 的准确证据，不升级旧SOURCE资格。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B53四套Root命名连接统一SAF导入/导出，用原B50/B22设置编解码与原本地ProfileStore；覆盖旧槽时清该槽Keystore、无密钥或Network数据导出，原Go/Rust不变。"}
```

## B52软件 FAIL 的最小兼容修复（保留原始证据）

B52a SOURCE `aeebc9103919906a33ed9768f0dc56dd55020345` [Android Dual64 #45182581375](https://github.com/lly8666/wbd-next/actions/runs/45182581375) 的 `root-arm64-app` **FAIL**：在新 `onResume` 增加四槽名刷新之后，B24旧源码门仍要求 `chooseNetworks → chooseInstalledApplications → ui.post(refreshStatus)` 三个调用相邻。新代码依然有完整真实Network/App UID刷新及单个1Hz状态循环，原纯JVM冷切网测试也通过。B53同SOURCE仅把**原断言**更新成 `chooseNetworks → chooseInstalledApplications → refreshNamedProfileChoices → ui.post(refreshStatus)`，不删Network/App旧检查，不加新线程/协议。B52a原FAIL不升级；B53独立正式签名APK必须重新验证。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B53随批对齐B24原UI onResume源码门到B52命名槽刷新后的真实顺序，保留网络/UID/1Hz回归与B52a实际FAIL，不动Go/Rust。"}
```
