# B30｜盘点上位施工进度、标记真实缺口、主线批量推进

对照实验分支 `f115ab1840f1c50eb1922f9c34b67267ca1fd770`，原Go/Rust/Root App/Rootjournal源码、B1–B29阶段记录和同SOURCE [dual64 #44967461025](https://github.com/lly8666/wbd-next/actions/runs/44967461025) 11 SUCCESS/4 SKIPPED。已确认Normal/off、Fixed/Auto/FEC2、TUN App UDP53三模式、LAN引导、完整Root App、原native Stop皆已有产品接线；仍不能把源码Build或旧M4计数写成完整物理TCP/UDP E2E。台账见 [ANDROID_ROOT_IMPLEMENTATION_BOARD](../../plans/ANDROID_ROOT_IMPLEMENTATION_BOARD.md)。

本批主线不做伪Game开关、不写第二个DNS/Go包引擎，先修 Android rootjournal 三种UID范围的真实FIB server peer排除不一致：all-app已有私有table `throw peer/32`；selected/group缺少，导致对应App对同一物理WBD服务端IPv4仍命中TUN默认路由。按已有原root owner+恢复机制补齐，原有Host和同源build验证后再更新台账。手机与服务端未经授权不动。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B30以源码与同SOURCE Actions标记已施工能力、未验能力和真正MISSING；后续继续原Root UID路由Server-IP例外跨模式闭环，不新增防御/代理框架"}
```
