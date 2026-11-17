# A7 ARM64 Root：真实已安装 App 包名选择和 UID 漂移撤权（2026-11-17）

仅 `experiment/android-temp-root-probe`；SOURCE 基线 `4fcf36e28a313b126d6ad09159469bfa9113ebe8`。继续用户授权的 Actions-first 正式客户端开发，不动 main/M0、不碰实体设备、PR #36 保持 Draft。

## 产品施工

1. 正式 `RootClientActivity` 移除可任意输入10k–1999999的UID表单，改为枚举当前Android用户可见、真正已安装且具有Launcher Activity的App：`PackageManager.queryIntentActivities` + `ApplicationInfo.uid`，按包名去重，显示 `label [package] UID`，排除Root/系统/WBD自己UID；无可选App一律拒绝Start。用户可手动刷新列表，包名不由诊断UI伪造。
2. Android11+ Manifest声明**仅** `<queries><intent MAIN+LAUNCHER>`；不用 `QUERY_ALL_PACKAGES`。Java host gate和APK构建脚本分别检查严格包名、UID边界与声明。非启动类/不可见包暂不提供，不声称枚举全部App。
3. 按真实App包名和UID创建Service启动请求；在Activity点击、Service接收，以及原Go/Rust同SOURCE assets校验后/进入 `su -c` 之前三次核对当前PackageManager的包名→UID。卸载、包更新或组件变化广播只对**当前Root会话指定包名且相同owner generation**请求原Root Stop；避免过时UID仍继续享有WBD隧道路由，监听无需轮询。原Go标准TLS/授权/租约、原Rust M4/Stop、Root journal及单UID table19842均未改。
4. 因内核按UID而非package分类，**共享UID的一组APK无法逐包独立分流**。UI明确披露同UID连带效应；需要物理Android guest实测同UID负例，而不是虚报按包独立性。

## 证据边界

A7 JVM正反门、Manifest最小可见性/签名APK、同源ARM64 Go/Rust与原Linux oracle需等待此次新SOURCE Actions结果。Android16 ARM64真实PackageManager应用清单、Android14+动态BroadcastReceiver、目标App删除/升级时系统uidrange内核回收、正式Go/Rust Android↔Linux真实TLS/业务及实体KSU仍 **NOT_RUN**；host编译不能升级为P3。在GitHub托管的ARM64 Linux runner，先前经A6 Action44056494256实测 `aarch64` 但无可用 `/dev/kvm`，P2/P3仍为 `ENV_BLOCKED`。

**下一步**：A7同源5 Job Actions门；之后需要能启动真实Android16 ARM64 userdebug guest的KVM runner才能做P2/P3联机及2个不同UID/同UID-App负例。软件没完成前不安排实机测试。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A7正式Root客户端改用Android PackageManager真实可见已安装App选择，3次包名UID复核、目标包变更世代限定停止和最小queries；保留P3 NOT_RUN。"}
```
