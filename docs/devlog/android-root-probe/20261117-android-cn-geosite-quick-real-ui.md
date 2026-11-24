# Android CN geosite 一键隔离 DNS Root 实测入口与输入法隔离（2026-11-17）

历史源 `4d55f415826635ff8b9f96c97d3768c6c3ea2871` [KSU Action43949393201](https://github.com/lly8666/wbd-next/actions/runs/43949393201) **FAIL**，但本SOURCE目标37 APK签名/双 ABI NDK/8503条CN geosite真实APK SHA锁/APNIC CN快照与既有 Root/TUN/IPv6/UDP DNS/TLS/合成2WiFi+1USB NAT/恢复/UID FIB 10/10 均 PASS。新分流 UI 测试尝试IM E焦点未就绪，转而真实tap模拟器显示样本UID按钮；App私有见证仍 `last_action=opened`、`package_char_count=0`，即sample按钮触摸也被模拟器未接收，**new `splitvalidate`/6组DNS gate 实际NOT_RUN**。旧主配置UI每App输入保存曾在独立SOURCE `75b5596...` [Action43909181856](https://github.com/lly8666/wbd-next/actions/runs/43909181856)获得 PASS，但不能冒充此次SOURCE的App键盘已通过。该历史失败工件14265978422、ZIP SHA256 `5ac67113116d08fb9636cae877cffc90bca7da2e5e1881952effd216be0c9369`。

## 新增可视诊断按钮（真实用户入口）

- 在 `SplitSettingsActivity` 标题后、所有长输入列表之前加入**一键验证 CN 域名及双DNS内核收发（不启用VPN）**按钮。它的真实 `onClick` 触发既有 `saveButton.performClick()` 路径，实际构造当前配置、fsync SHA校验的 geosite副本+配置的原子保存、以普通App现有KSU授权su启动native验证。用户真机也能点，不需要先输入模拟 UID；它从不安装主 Android netd规则/启用真实VPN。
- `android_split::validate_file` 在**内存中**实例化用于内核DNS收发的Split UID0/Global UID10502，不写这些模拟 UID 到用户磁盘配置或真实 Android路由；恢复原始用户base/overrides后再报告真实 `per_app_modes`。这样不论当前用户默认模式是什么，都对 geosite DNS直连+真实海外A业务Tunnel、普通海外域名Tunnel DNS、global CN域名Tunnel DNS和两模式WBD bootstrap Direct的六类Kernel UDP/53双TUN收发执行完整正负例。
- CI新 `cn-geosite-quick-ui.py` 复用本启动周期最初真实 `uiautomator` 按钮快照进入 Activity，观察真实窗口焦点+顶部验证按钮 `getGlobalVisibleRect`，执行一次真实 `adb shell input tap`，再通过App私有数据和 `su` native JSON 验证 geosite SHA/8503+规则、6/6个真实内核DNS事务/4Direct+2Tunnel/海外A=8.8.8.8，`installed=false`且真实223.5.5.5/1.1.1.1及正式WBD **NOT_RUN**。不写App配置、不直调原生程序、不虚构UI点击。
- 旧 `split-settings-ui.py` 保留作为独立的 per-App IME编辑测试资产，**此同SOURCE CI不再声称每App文字输入已回归**；最终 machine summary 分别写 `split_settings_ui=PASS_QUICK_ROOT_DNS_CONFIG` 与 `per_app_text_editor_same_source=NOT_RUN`。历史 `75b5596` 的真实 perApp UI positive 继续保留，不将其误作当前 SOURCE证据。

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Add real on-screen one-tap App->su full CN-geosite and 6 synthetic netns DNS UDP tests; use isolated temporary Split/Global mode fixtures without persisting demo UID; record perApp text editing NOT_RUN on new SOURCE."}
```
