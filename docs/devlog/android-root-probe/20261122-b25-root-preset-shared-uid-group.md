# B25｜恢复原本合法的16包名／8不同UID连接预设

基线 `1a0dfe980812706668f50344d3a25f80a576cfdc`（B24 Ethernet原物理Network、刷新保持、App本地筛选与批选，SOURCE CI按Action记录）。审查发现 B22 保存预设 `RootConnectionSettings.valid()` 误把 `selected.size()` 限8、`read()` 的 selected_count 也限8；但原 App选择/原Go UID路由已经按 `SelectedAppGroup.MAX_PACKAGES=16` 且 `MAX_UIDS=8` 验证。大量共用相同Android Linux UID 的包可以正常手动START，却无法在下次打开Root App后恢复。此问题属于真实日常功能链不一致，非极端异常防御。

- 本机纯Java `RootConnectionSettings` 生产读/写沿用**16个包名/8个不同UID**原限；所选包复用 `InstalledAppTarget.validPackage`，UID 10000..1999999，不允许9个不同UID/第17包。其它服务端、AEAD、DNS、Fixed/Auto、CA、password/RouteKey/无备份路径均不改。
- 原 `RootAppPickerModelTest` 加16包共享同一真实UID批选的正例，原 `RootConnectionSettingsTest` 实际序列化/读回16包、9个不同UID/17包负例，`test-network-scope-gate.sh` 明确编译同源模型与引用原限。真正Root Start还会走 `SelectedAppGroup.from`＋`InstalledAppCatalog.stillSameGroup` 和Service双重读回；旧Root持有UID不因App重开被新授权。
- 不操作系统DNS/netd、物理Android手机、个人服务器或KSU客体；编译/Host/签名APK应以新SOURCE的Actions为准，业务应用E2E与性能仍NOT_RUN。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B25 align app no-backup connection preset with authentic selected route max 16 packages/8 unique UIDs; production Java host round trip and original cold launch identity checks retained"}
```
