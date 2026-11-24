# Android16 CN geosite + DNS 实测前，UI 输入焦点失败复核（2026-11-17）

在 SOURCE `754716b44cdc486296ed3d98277ea68ceaff06c2`，[KSU Action43944789556](https://github.com/lly8666/wbd-next/actions/runs/43944789556) **FAIL**，工件 14264028953 ZIP SHA256 `70116af1640340f26028600fee68c792c7abeb2f8b9e33d920de230d450e692a`。完整 targetSdk37 App+ARM64/x86_64 Bionic构建 PASS；带原LICENSE固定SHA的 `v2fly/domain-list-community` CN geolocation 域名快照成功导入 **8503 条**（domain 8431, full 69, regexp 3），CN APNIC 5500条CIDR也通过；真实Android16 KSU的原Root/TUN/raw/DNS/TLS/恢复/2Wi-Fi+1USB NAT、无FakeIP纯分流和 10/10 UID内核选路再次 PASS。

**失败准确原因不是内核DNS逻辑**：分流Settings真实Activity和加号按钮被打开/点击，但 App 私有 `wbd-split-ui-bounds.json` 显示 `last_action=add_invalid_package`, `override_count=0`, `package_char_count=0`；`wbd-split-settings.json`/`wbd-split-validation.json` 都不存在。之前的UI代码在焦点未确认情况下直接 ADB `input text uid:10502`，新加长 geosite详情导致 Android IME + ScrollView布局可能竞争，实际没有输入；六组 DNS UDP gate 仍 `NOT_RUN`，不可宣称通过。

修复继续采用**真实App UI + Android文本输入事件**：App为 package EditText 添加 `OnFocusChangeListener` / TextWatcher，私有见证文件只记录 `focused` 与 `package_char_count`，不泄漏用户输入。CI 必须用真实 ADB tap使控件 focused，再用Android `input text uid:10502`，等待编辑后字符串长度 9，最多四次有界重试且各次记录失败原因，之后方可点真实 Add/Save；不触及 App配置文件或执行假的 click handler。旧源FAIL与工件保留，新SOURCE的 geosite hash + DNS UDP 6/6 + Root App config全链必须成功才认定完成。

```feature-impact
{"kind":"none","ids":[],"reason":"Fix Android16 IME/ScrollView focused package EditText race using real focus witness and bounded keyboard retry, preserving rooted geosite and 6-case DNS packet acceptance."}
```
