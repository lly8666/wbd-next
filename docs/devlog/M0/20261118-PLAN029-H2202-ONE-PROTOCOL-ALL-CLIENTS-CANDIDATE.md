# H2202｜唯一强制加密控制格式；Windows与Linux统一用户配置，跨平台SOURCE候选

用户明确不要兼容旧协议。本次删除V4 extension的ControlPadded开关和V1 version读取，BE16 extension version固定2，byte23承载off/tls/flows。无论业务pad off/on，两向受保护Admission的成功消息各独立BE16+32..500B crypto/rand随机填充，Go reader在detach之前全部读完。17处真正V4 server受保护Admission拒绝状态，改成同样有界随机长度的 `status | BE16 | random tail`，不再暴露固定1B应用负载；旧1B客户端回复拒绝解析。TLS原握手/Go server证书验证/route-key/当前Rust TLS-like业务PN、AEAD、FEC/Stop未改。注意TLS record包长/认证失败时序/真实应用仍可能被指纹识别，无法承诺绝对不被DPI检测。

Windows此前CLI/WinForms只在本地Rust cold使用StartupPaddingMode，Go TLS请求未完整传入。修复当前Normal、Fixed/Auto及Game2/4原Go TLS入口，把模式送入V4ClientOptions，Game客户端及Windows server全部核对lane一致，禁止错配而仍生效。同步Windows manifest-plan020-m0原Git blobs，解决原H2201只Linux SOURCE编译时Windows装配可能旧哈希的问题。本地空mode按off，配置兼容不代表旧线上协议兼容。

测试预备：`TestH2202...` Go TLS三档/版本1拒绝/恶意长度/熵失败/失败回包、原证书与KDF冷不可变；Linux双真ISA各12真实内核场；Windows2025真实GoTLS与当前CLI、WinForms/Rust DLL；Android NDK+APK、OpenWrt musl构建。真实Windows NPF/Wintun联通、安卓实体JNI/VpnService、OpenWrt设备及公网DPI未有新SOURCE产物则只保留NOT_RUN。H2201旧SOURCE Linux24/24 PASS_SCOPED继续保持历史，不迁移成H2202产品资格。

```feature-impact
{"kind":"updated","ids":["startup-flow-padding"],"reason":"H2202 user mandates one V4 protected TLS control version; unconditional bounded random request/success/reject response; Windows Normal/FEC/Game config projected into authenticated admission; Linux native, Windows Go+GUI, Android and OpenWrt build matrix forthcoming, all new-source qualifications NOT_RUN until real Actions."}
```
