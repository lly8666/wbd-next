# B84｜四页 APK UI 重构与官方 CN 手动更新

基线 B83 `0e1560ce8944289f1b66d687a26622fca0aed8bd`，[原产品 CI](https://github.com/lly8666/wbd-next/actions/runs/45371149902) 9 SUCCESS / 1 FAIL / 5 SKIPPED；APK 旧 Game padding source-string 断言 FAIL，原生构建和 Linux oracle PASS；功能目录和维护 SUCCESS。历史A48真实 Normal/off 原TLS/认证/租约/M4 RAW/TUN双向/owned Stop证据不变。

**2026-11-24 B84 用户要求：APK UI 收口重构。** 四个常驻页面：连接（真实M4+UID状态、当前服务器/下次配置、连接/断开/选服务器）、服务器（4个命名槽、独立凭据/CA、备份与冷切换）、应用（默认全局普通App或仅选定App，统一选择全量隧道或CN/自定义分流，未接管App保持系统路由）、设置（原传输/Health/IPv6/热点/恢复/诊断）。全量按钮清除CN/物理DNS/IPv4/IPv6/自动LAN直连例外，CN分流按钮启用已有CN IPv4+域名策略；选定App共享当前FIB策略，不声称每个UID独立不同规则。默认全局普通IPv4（原服务端、Root/系统/WBD/Manager绕过，IPv6与普通系统DNS显式选择）。配置变化只在下一次START生效；命名服务器切换复用原B49/B52完整Stop→新认证。显式手动联网更新官方CN域名库已接候选：下载v2fly最新release、核上游SHA、同四类protobuf提取、原Go/Rust冷规则解析；成功原子替换，不自动更新或改变已运行会话。主体新增功能冻结，转入测试。真实APK先构建，然后本轮一次x86 KSU guest跑新四页UI截图/交互、ART原生冷参数、Root及ARM64 NativeBridge Rust MTU/Go c-shared；不重跑TAP/旧直接ARM64 Go SIGSEGV。B84 CI和真机未验。

本轮仅 Android 冷UI、状态展示及用户触发CN数据下载，未改变原Go/Rust数据面或协议，无额外逐包校验。现有全部设置/保存/导入导出/诊断保留。CI 复用官方同源 binary group 对 Android 提取器逐条核对；正式ARM64 DEX 必须包含新UI与更新器，不含 x86 测试Activity。显式本次 commit marker 触发一个 x86 冷套件，等待正式APK构建产物后才运行，同guest截图home/server/apps/settings与真实选择；不会自动连接服务端，完整M4、实体性能仍NOT_RUN。仅实验分支 / Draft PR #36，main/M0 未动。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Four-page production Android cold UI, ordinary-app default global scope and real full/CN split presets, saved server cold switch, manual official CN release update and one-shot x86 Android UI/ART/NativeBridge tests."}
```
