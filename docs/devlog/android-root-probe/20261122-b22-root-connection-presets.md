# B22｜Root App 普通连接参数本机保存/恢复（真实日常功能）

基线 `a53b8a500415ecdfd43b2f20fde94fafebf4cab7`：B21真实签名APK/双ABI/Host/Linux Oracle [#44937445205](https://github.com/lly8666/wbd-next/actions/runs/44937445205) 11 SUCCESS +4 SKIPPED；Root App已有 Keystore 保存密码和RouteKey，但重开时 Server、TLS SNI、账号、端口、外层MTU、AEAD、TUN队列、Normal填充、Fixed/Auto档位和DNS模式都重置；选定App的勾选也会丢。需要补正式用户入口，而不是继续增加原生采样、防御设计或极端工况。

- 正式 `RootConnectionSettings` + `RootConnectionSettingsStore`：Java Properties 仅记录上述普通UI冷参数、TLS验证选项、全部普通应用/选中 App 的包名与当时UID，位于本APK `getNoBackupFilesDir()`。**绝不写密码、RouteKey、证书 PEM、原始Go stdout、物理网卡 Network Handle、root route/owner token**；原密码/短RouteKey仍使用原 `RootEncryptedCredentialStore` 的 Keystore记录，不增线上wire/第二TLS/密钥实现。
- Root Activity 新增手动保存按钮，完整合法 START 分派后自动保存相同连接预设（失败不阻止本次Root启动），新 Activity 首次打开恢复已有记录；物理 Network 总是通过Android `PhysicalNetwork.available` 重新枚举并由用户选择。全部普通App开关保留上次选择；选定App的勾选仅在重新扫描真实安装App且 package **和当前 UID 完全一致**时恢复，换UID/卸载不重新授权；START仍必须沿现有 `InstalledAppCatalog.stillSameGroup` 和受保护Go/真实Rust路径。**没有自动START、自动Root、旧UID路由重放或系统DNS改写。**
- 原 Root App Host gate 编译执行正式纯Java codec 测试：Fixed/Auto、DNS互斥/MTU/AEAD、Selected package+UID roundtrip、全App模式、非法输入及无秘密字段。签名APK必须同时编译正式 `RootConnectionSettingsStore` 与 Activity；Actions按本SOURCE为准。
- 默认仍 Normal/off，外层MTU1460，TLS证书身份校验OFF（主线相容），隧道DNS ON；仅恢复用户上次明确保存的合法选择。真实Android↔Linux应用TCP/UDP、系统netd DNS、性能、Auto真实切档仍NOT_RUN；不运行手机、服务器、KSU guest和额外重CI。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B22 app no-backup nonsecret connection preset plus exact installed package+UID selection restore and real Activity Host/test wiring, no automatic Root or data-plane change"}
```
