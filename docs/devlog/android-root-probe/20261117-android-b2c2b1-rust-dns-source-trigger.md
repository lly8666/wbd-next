# Android B2c2b1 — 原Rust DNS53 产品SOURCE触发门修复（2026-11-17）

仅 `experiment/android-temp-root-probe`，不变更main/M0 registry/cursor；无远端worktree，不声称检查过未提交本地更改。开工远端HEAD `58bebfd0e8427d31a0ac2e0379f8fe82a6965fcb`，main `969ce2b1a321e3a122c7cc235db7da45a7f13a17`，Draft PR #36。

## 为什么修复

之前 `crates/wbd-engine/src/v4_android_dns_udp_flow.rs` 没有列入 `.github/workflows/android-root-product-a1.yml` 的 `push.paths`；修复负例SOURCE `fb2f1ca2038d22362f7c1cfdd6065d3760e4d873` 曾只触发治理而漏跑原生客户端同源10-job验收。随后临时修改已在路径内的Host脚本触发验证，并以SOURCE `17a5322e39893ceac567f461a8a345c25d17305b` Action #44091367458获得10/10 SUCCESS。首轮坏夹具失败 Action #44090496300 保留，绝不改写。

本包把 `crates/wbd-engine/src/v4_android_dns_*.rs` 加入真正产品工作流 `push.paths`：统一覆盖唯一TUN入口DNS观察和Rust UDP五元组inverse-map，以及后续同前缀源码，无须人为碰Host脚本。源锁Host脚本新增回归断言，防止再次只过governance。保留原原Rust AEAD/PN/Normal/off、原Go TLS/lease、Android ARM64 signed APK 和同源Linux server oracle全部Jobs。未改任何协议、UID路由、DNS wire、系统resolver、TUN reader、真实设备、main。

## 本次SOURCE和试验边界

本次提交前证据：`17a5322e39893ceac567f461a8a345c25d17305b` Action #44091367458 10/10 SUCCESS，最新HEAD `58bebfd0e8427d31a0ac2e0379f8fe82a6965fcb` 治理成功。**本次代码SOURCE新Actions初始NOT_RUN**；待由本提交的产品workflow与governance按新SHA裁决。Host/Build/Linux oracle的成功不能宣称Android实际Normal/off与同源Linux服务端连通、Android DNS hijack或物理KSU成功；P2/P3仍KVM ENV_BLOCKED，P5需授权。Rust UDP inverse模块仍未接M4 live hook，`hijack_enabled=0`。

**唯一下一步**：取本次新SOURCE的完整Actions结果；只在产品同源门通过后继续同一个原Rust M4 owner的DNS backend/RX/Stop与普通Android resolver接线，仍不提前开启DNS劫持或添加合成探针。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"修复Rust Android DNS源码变更漏触发完整同源ARM64产品Actions的路径准入，并在B2c2b Rust Host脚本固定回归；不更改业务行为或声称Android真实DNS。"}
```
