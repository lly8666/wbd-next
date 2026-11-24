# B23｜Android Root App 严格 TLS CA 的导入即保存／重开恢复／手动清除

基线 `98827b80dbe6b1cf3f9b5b91f40552e455c42712`（B22 的本机连接参数恢复）。B22可以恢复严格TLS开关、Server/SNI/账户，但用户手动导入的PEM仅留在 Activity文本框，未在重新打开时读回；旧Go冷路径要求同一CA文件，否则用户下次严格TLS认证会在无导入CA状态下失败。这是现实功能接线缺口，不是极端边缘防御。

- 原 `RootClientActivity.acceptTLSCA` 在已有大小/X.509检查通过后立即调用 **原A32** `RootPrivateCredentialFiles.write` 写同一个 App 私有0600 `wbd-server-ca.pem`；`RootClientActivity.start` 仍原样在严格模式冷层重新交付确切PEM，不改标准 TLS、验证默认OFF、SNI、Root密钥、Rust M3/PN。
- `RootClientActivity.recallSavedTLSCA` 在 UI onCreate 读取原文件，复用现存PEM证书有效格式/X.509解析，恢复 CA 文本供下一次手动 START使用。不存在、读取失败或无效时忽略，不自动建立网络连接、不影响普通账号/RouteKey保存。
- 新按钮“清除本机已导入的TLS CA”仅清除本 App 原0600证书文件与当前表单；**不删除密码/RouteKey、Android系统TrustStore、其他App/根内核规则**。更改当前证书设置并不表示原生TLS是否已通过或需要改动服务端证书。
- 使用原Root App Host脚本确认Activity真实 import/recall/clear 与原0600 writer的调用链，现有 `RootPrivateCredentialContractTest` 验原CA文件owner-only元数据；新SOURCE的签名APK、原生双ABI及Linux Oracle按实际Action验收。没有实体 Android/服务器测试，正常隧道与性能依旧NOT_RUN。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B23 reuse actual original-Go 0600 TLS CA file for immediate local import persistence, Activity reopening recall and clear action, no new trust store or packet path"}
```
