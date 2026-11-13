# PLAN029 H1715｜收H1714 Win编译首错，精确修复不重派网络场景

- [H1714 SOURCE 28953781f5767af133de80381ac82fe1df03e87b Native Win WAL Action43374441963](https://github.com/lly8666/wbd-next/actions/runs/43374441963) Windows原Go compile **FAIL**，首个实际错误：新`native_real_product_service_windows.go`两个`context.WithTimeout(...30*time.Second)`引用`time`但未导入。只增`time` import，保持本代authenticated owner+独占Wintun+四真实stage的无旧WFP admission及真实Applied/Stop硬门不变。H1714没有进入Win32实际Apply，不能当作产品失败或通过。
- [H1714 Feature Catalog Action43374441898](https://github.com/lly8666/wbd-next/actions/runs/43374441898) FAIL 原因`dns-split-ipv6.json`已超16KiB; 保留全部原验证行、source/evidence和limitations，改为JSON紧凑编码约15977字节，不删历史失败，不改实网结果。WINDOWS网络功能卡追加该编译失败受限证据。
- 保留 [H1713 Action43368431989](https://github.com/lly8666/wbd-next/actions/runs/43368431989) 签名Wintun真实CN DNS→Linux CNAME/A→持久FakeIP→app实际Direct UDP回包 PASS（m0_v4_probe诊断，非认证Normal/Game4）；H1697真实noWFP四Win32OS Apply/Stop/H1709真实Direct TCP FIN局部PASS亦保持原SOURCE边界。此批仅SOURCE编译修复，不另外派网络Action。
- 正式NativeOwner唯一Rust ingress两个DNS出口、非CN/共享CDN及GUI/padding/性能D1-D5/P1-P2仍未验收，029继续IN_PROGRESS，028 H1657范围不重开、030未启动。

```feature-impact
{"kind":"updated","ids":["windows-network-wal","dns-split-ipv6"],"reason":"Preserve H1714 exact Windows Go source compiler and feature-size failures; fix missing time import and retain complete bounded JSON feature-card history for H1715 retest."}
```
