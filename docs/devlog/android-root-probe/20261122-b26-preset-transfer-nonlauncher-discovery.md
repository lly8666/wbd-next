# B26｜Android Root 日常连接预设 SAF 迁移＋非 Launcher 可见App入选

基线SOURCE `776cec4fcd21dcf23c167f7478c53add5e8b90a6`。已有B22/B25普通连接配置保存、16包/8UID恢复和B24 App搜索，但CI使用一次性签名证书，换新APK卸载旧版会清掉应用私有预设，需要重复填写服务器/SNI/账号/选定App/MTU/FEC/DNS。另一方面原 `InstalledAppCatalog.launchable` 和 `stillSameGroup/stillSame` 都硬编码 Launcher，合法可见但没有桌面图标的浏览器/分享处理App无法选择，即使原Go/Rust UID路由本身没有这个限制。

### 本批产品改动

- 原 `RootClientActivity` 新增 Android SAF “导出普通连接设置”/“导入普通连接设置”按钮和可见结果行。导出在打开文档选择器前冻结当前合法表单，用**完全相同的生产** `RootConnectionSettings.write()` 序列化；导入复用 `RootConnectionSettingsTransfer.read()` 封顶8192B且要求有效schema/version/原连接范围，保存到现有 `RootConnectionSettingsStore` 后才更新表单。重新枚举已安装App：仅原记录中的包名/UID与当前Android查询一致才勾选。**不恢复物理Network handle、不会自动START/Root/路由，不导出Keystore密码、RouteKey、CA PEM/Go stdout**。导出的用户名/服务器等普通设置仍是用户可识别元数据，用户自行选择存储位置；调试签名变更后秘密信息需手动重输。
- `AndroidManifest.xml` 在已有launcher窄 `<queries>` 外只增加 `ACTION_SEND text/plain` 和 `ACTION_VIEW https`，对应 `InstalledAppCatalog.discoverable()` 聚合三类当前Android可见Resolver的实际PackageManager`ApplicationInfo.uid`。显示、Service冷 `stillSameGroup`、包变化 `stillSame` 都使用该真实可见集合，后两者只为目标包提取UID，不对全列表再获取标签，降低冷启动开销。**不申请QUERY_ALL_PACKAGES、不接系统/root UID、不声称所有无Launcher应用都可选**。
- 既有原 `SelectedAppGroup` 最多16包/8不同UID、手动START且认证/32/M4就绪才允许真实KernelSU UID路由、不引入Java/Go逐包或高频查询。现有原M4 IPv4 UDP/53 DNS并非Android系统`netd`真实流入，故不能宣称系统DNS通过。
- 生产 Host gate 编译并执行 `RootConnectionSettingsTransferTest`：真实 B25 16包往返、原服务器/SNI/模式、8KiB、坏版本、坏配置、密钥/网络句柄不出口；校验 Activity 的真实SAF导入导出链和 manifest的三种定向visibility及Service统一冷PackageManager核验。SOURCE锁定签名APK与 Go/Rust/Linux Host 由新 Actions 决定；未授权手机/个人服务器操作，Android真实DNS/E2E/性能NOT_RUN。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B26 real Android SAF export/import of original nonsecret 16-package connection preset and narrow launcher+share-text+HTTPS handler selection backed by exact cold PackageManager UID recheck"}
```
