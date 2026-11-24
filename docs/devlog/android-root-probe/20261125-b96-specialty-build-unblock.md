# B96｜专项编译解阻、早期 CI admission、复用同源普通 App fixture

B95 SOURCE `6545a6940d7973fd8b56d6e6beebb2a67fe8380a` [Action 45432269092](https://github.com/lly8666/wbd-next/actions/runs/45432269092) 6 SUCCESS / 1 FAILURE / 10 SKIPPED。6个 baseline（CN/physical DNS/DNS loopback/inverse map/TUN DNS ingress/original M3）通过。 [arm64-native 138580511154](https://github.com/lly8666/wbd-next/actions/runs/45432269092/job/138580511154) CI-only Go 编译错误 `label route defined and not used` / `undefined: route`。B95 未进入 guest，未形成新的前台 UID/DNS 查询或 Stop 收据。不能冒称 B95 已解决 B94 的 DNS 清理和 EPERM。

B96 将误写的 `route:func` 修为 `route:=func`。在耗时 native build 之前用标准 Go AST parser 检查两个 CI adapter（无 label），bash -n、Python compile、实际普通 App fixture host TCP/UDP loopback + Android SDK javac/d8/aapt/sign。只读 UI 线程检查真实 window focus。早期 fixture artifact 记录当前 SOURCE + SHA256SUMS，9个独立 guest 下载同源已签名 APK，而不是各自重复编译/签名；真正 Go Android 编译/链接仍必需。局部 Go parser 检查器在本地合成正向声明及 B95 同型错误负例通过；没有本地完整 donor/NDK/guest 构建。B96 新 SOURCE 待 Actions。保持 B95 的9专项、24次 UID 回显与7模式逐 socket TX、3 DNS owner/query/Stop receipts，不重跑已通过的 B93 lifecycle。生产 Go/Rust 路由/协议/热路径未改、未访问手机/外部服务器/main。B94 7/7 authenticated M4 start/stop 与部分 ordinary UID echo 的历史证据有效但不代表 B96 运行通过。B95 governance feature catalog 121 tests OK 后 exit 2，仍未解。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Record B95 CI adapter build failure and restore nine real guest tests with early source and shared fixture admission."}
```
