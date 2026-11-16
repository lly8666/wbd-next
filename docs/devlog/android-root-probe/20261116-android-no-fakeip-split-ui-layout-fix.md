# Android 无 FakeIP 分流设置 UI 第四轮失败复盘（2026-11-16）

- SOURCE `1cc066e7e5063baec7631ac3f221028fd50f64be`，[Android16 KSU Action 43900940103](https://github.com/lly8666/wbd-next/actions/runs/43900940103) **FAIL**，工件14242465052；APK双ABI/source/签名、TUN/raw、IPv6、SO_MARK、CN split policy、10/10 真实隔离netns UID rule、合成2WiFi+1USB NAT、精确恢复均 PASS。
- 在第二次 UIAutomator 137 的规避版本里，CI 确认从**真实首屏快照**点击并打开 `SplitSettingsActivity`，按照 Android `getGlobalVisibleRect` 的私有证据完成输入、添加、保存坐标触摸，但 **没有等到 App 的 `wbd-split-settings.json`+Root `wbd-split-validation.json` 均成功**。此前脚本只显示整体超时，没有保留独立的配置/原生错误；不能将点击动作算保存成功。
- 发现一个可信 UI 错误路径：`appsView` 添加一项后高度变化可能推动后方 `saveButton`，而原控件坐标只有在 ScrollView 滚动时刷新，导致使用旧坐标点到错误位置。
- 修复：`SplitSettingsActivity` 在 `LinearLayout` layout 变化和 Add/Save 两次实际 onClick 时更新 App 私有 `wbd-split-ui-bounds.json`；记录 `last_action`、覆盖数、可见坐标、私有状态摘要（不存输入的包名和密码）。CI 在 Add 后必须观察 `override_count=1`，确认重排完成后才实际 tap Save；Save 后必须观察 `save_clicked/save_started/save_completed`。失败时归档 `run-as` 配置/校验 JSON、控件状态及最后 logcat，明确 App 配置错误、Root 验证失败还是坐标击中失效。
- **政策、APNIC5500 CN IPV4数据、真实 Android netd 资源保持不变**；实验仍只保存/验证，不 Apply 主路由/DNS、不接产品 WBD。

```feature-impact
{"kind":"none","ids":[],"reason":"Diagnose split-settings real UI post-Add layout stale button geometry; ensure live App click state and forensic native readback on failure."}
```
