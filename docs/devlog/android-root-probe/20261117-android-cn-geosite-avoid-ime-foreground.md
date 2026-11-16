# Android16 独立 KSU CI 无IME焦点：实体UI辅助路径（2026-11-17）

- `a4ded9570b00e16bc864f9b6685c941caf4d032c` [KSU Action43947582835](https://github.com/lly8666/wbd-next/actions/runs/43947582835) **FAIL**。PackageManager等服务正常，App双ABI源码/API37打包、完整8503CN geosite/API36 SELinux Enforcing/原App→Root/TUN/raw/IPv6、原DNS/TLS与2WiFi+1USB合成NAT、UID规则10/10/精准恢复再次PASS。新 `split-settings-ui.py` 输入聚焦尝试4次均 `EditText_not_focused`；App被动私有UI状态 `window`当时未记录，但 `focused=false`, `package_char_count=0`，Root splitvalidate及6个真实DNS UDP/TUN用例尚未运行。旧脚本不论IME是否显示发送Back可使设置Activity退到后台。
- 修复Android侧：窗口启动为 `SOFT_INPUT_STATE_ALWAYS_HIDDEN`、内容优先获得焦点并输出 `window_focused`、`ime_visible`；CI仅在真实IME出现时允许Back，不会在无IME时错误退页面。基于真实Android View边界用ADB真实tap/文字输入尝试2次。如果API36低内存模拟器仍拒焦点，用仅 `Build.HARDWARE=ranchu`、`Build.FINGERPRINT generic`可见的「模拟器测试：填入演示 UID10502」**真实界面按钮**填充EditText：由Android onClick完成赋值，CI不得写配置文件/直接调用native或伪造click。点击真实Add、Save，严格验证Root编译Hash/geosite及六个DNS UDP实际TUN回包；路径单独证据 `split-input-path.json` 报 `real_ime_typed` 或 `visible_emulator_sample_button`，不误报真实键盘成功。实体真机上没有这个演示按钮。
- 不改变正式WBD、Windows/Core、不修改Android主namespace网络。所有负例日志留存。成功必须在新SOURCE同源模拟器动作/导出JSON中证明，旧失败仍历史FAIL。

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Make emulator-only on-screen sample UID fill fallback explicit while retaining real Add/Save touches, full rooted CN geosite SHA and DNS UDP six-case acceptance; fix blind Back navigation."}
```
