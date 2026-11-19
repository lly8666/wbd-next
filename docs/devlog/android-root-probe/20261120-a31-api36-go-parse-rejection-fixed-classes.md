# A31｜真实 Android API36 原 Go parse 拒绝：固定类别而非暴露私密错误

用户自行安装 A30 signed APK SOURCE `e85a19883151a101f9dbc12848a6ab6dec3e0780`。22项固定收据：`ROOT_PROCESS_LAUNCHED` → `ROOT_SHELL_ENTERED` → `ROOT_SHELL_ROOT_UID_VERIFIED` → `ROOT_SHELL_PRIVATE_DIR_VERIFIED` → `ROOT_SHELL_OWNER_GUARD_PASSED` → `ROOT_SHELL_NATIVE_FILES_STAGED` → `ROOT_SHELL_OWNER_PID_WRITTEN` → `ROOT_SHELL_EXEC_ATTEMPTED` → `ORIGINAL_GO_ENTRY` (1795109008277) → `ORIGINAL_GO_ARGS_REJECTED` (1795109008279) → `ROOT_PROCESS_EXIT_1`。真实Root、ELF及原Go Run已成功，`parse("client",args)`失败。没有 interface/TUN/RAW，更未到FakeTCP/TLS/M4/应用TCP UDP、路由安装或真实Stop。旧版A20e x86 CI原Go TUN/RAW和A10独立ARM64真机内核TUN PASS仍成立；不能借此前结果把现在归咎TUN驱动或账户认证失败。

A31唯一变更：原Go`parse`拒绝后按封闭、安全常量输出`V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=...`，分类严格为 `FLAG_SYNTAX/PASSWORD_FILE/ROUTE_KEY_FILE/ROUTE_KEY_VALUE/INSTALLATION_ID/CN_GEOSITE_FILE/TLS_CA_FILE/ALL_APP_EXCLUSIONS/ANDROID_NETWORK_SCOPE/PEER_ADDRESS/REQUIRED_COLD_SETTINGS/POLICY/OTHER`；不输出原err、路径、密码、RouteKey、服务端IP或包名。RootService通过已有只读锚定matcher映射RootDiagnosticReceipt封闭枚举和时间戳，报告优先解释真实最后拒绝原因；旧A30泛`ORIGINAL_GO_ARGUMENT_PARSE_REJECTED`不重判。真实`parse`安全规则/Go Rust/原TLS/私有服务器/32 throw/Stop完全不改。Go Host包含13类/敏感字符串未知类；Java Host13类及旧泛拒绝；正式Android签名APK/原Linux oracle和治理需同SOURCE。没有用户手机/服务器测试，也不跑模拟网卡或KSU guest；未来要以用户自主安装后导出的新脱敏TXT决定具体修复，绝不预先宣称根因、启动或联机成功。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"真实API36已经证原Go入口但parse失败；新增真实原Go13种固定脱敏拒绝理由并接原Java安全收据/Host回归，不放宽校验或模拟网络。"}
```
