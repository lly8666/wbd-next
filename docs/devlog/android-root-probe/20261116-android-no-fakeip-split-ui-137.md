# Android API36 UIAutomator 137 测试进程被杀（2026-11-16）

第二轮源码 `89355770cc36eef42bc2c682d57dcefdbebdc7b1` [Action43897727775](https://github.com/lly8666/wbd-next/actions/runs/43897727775) overall **FAIL**，但目标37 APK、双ABI、APNIC冻结CN表、KSU App→su/IPv4TUN/raw、IPv6/策略路由、2WiFi+1USB合成NAT、Android无FakeIP纯规则及 UID内核10/10判例均已 PASS。失败仅在随后 `split-settings-ui.py` 启动第二个UIAutomator时 `adb shell uiautomator dump` rc137（SIGKILL）且输出空；尚未完成每App按钮及native配置回读，不能把当前失败改记UI PASS。

修复只对UIAutomator进程本身增加 bounded 5次、每次2.5s状态恢复；每次仍须取得有效XML后真实定位按钮，不能用猜坐标伪造交互；其它Source/路由和安全边界不变。

```feature-impact
{"kind":"none","ids":[],"reason":"Bounded UIAutomator SIGKILL/137 infrastructure retry for Android split-settings UI test, preserving actual App tap and native readback requirements."}
```
