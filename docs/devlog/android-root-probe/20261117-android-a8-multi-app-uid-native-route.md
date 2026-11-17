# A8 Android ARM64 原Go多UID闭环：真实App多选 → 内核组事务（2026-11-17）

施工分支 `experiment/android-temp-root-probe`、原 SOURCE `39ccce1b8c39f694e62c19926e2cee9e17f9a8f7`。PR #36 Draft，main/M0/Windows/Linux协议内核不动；仅源头软件与GitHub Actions，无真机或付费资源。

## 原产品纵切面

1. A7 真实Launcher App选择从单包Spinner改为1–16个安装包CheckBox，可见包、PackageManager UID、包名去重及共享UID合并，统一为**升序唯一1–8 UID**。System/root、自身App UID与无效包/超限fail-closed。共享UID依内核定义共同路由，UI公开限制。Activity、Service、进入`su -c`前三次核对**整组**包名↔UID；选中任意包安装状态变化触发整个真实Owner Stop，仍是事件式冷控制。
2. 原Go Linux+Android共享CLI仅在Android接受`--android-route-uids`（2..8 升序不同普通UID）并拒绝与单UID旧参数共存；Linux不接受Android参数。仅在**原TLS凭据认证、服务端真实授权租约/32、实际TUN OS读回、Rust原M4 DATA接管完成**后，Android Root执行新`rootjournal.NewGroup`，同一表19842中只装一个`default dev ownedTun`，各UID分别`ip -4 rule pref 9600+i uidrange U-U lookup 19842`，全程精确Kernel readback、出错不发布正成功收据。
3. 新Go group journal v2同旧v1`route-journal.json`、`owner.lock`互斥，0600 NoFollow、目录root-only 0700、fsync先于kernel改动；v2持久记录完整UID组/租约/物理Network，逐规则rollback和Stop、crash recover及v1→v2/v2→v1严格兼容，外国优先级或同表外来规则拒绝修改。不加系统默认/main路由、不改netd DNS、iptables、VPN/FakeIP、热路径包协议。
4. 真Go`rootjournal`Fake IP runner测试涵盖3UID commit/Stop、部分写失败、不同阶段进程死亡恢复、flock活Owner冲突、外来table/pref、UID越界/重复/无序/超8、旧/新journal跨版本、Stop删除失败保持持久收据。Java host测试真实用于产品的SelectedAppGroup包名/UID canonical/共享UID/负例；Actions仍同SOURCE构建arm64 Bionic原Go/Rust+签名APK和原Linux服务端真实协议oracle。

## 分层证据边界

当前提交阶段 A8 代码**待同SOURCE Actions结果**，不可仅凭源码宣称通过。Host Go假 Runner/Java JVM测试只证明可复现事务状态与源构建；正式Android16 ARM64 userdebug根服务、实际`ip uidrange`、PackageManager与两个普通App的双向流量、物理Network绑定、DNS TCP/UDP53、分流模式、KSU真机全部NOT_RUN。旧托管ARM64 runner`/dev/kvm` NOT_AVAILABLE，P2/P3 `ENV_BLOCKED`，不得用A8编译代替真Android E2E。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A8真实安装包多选1..16、canonical 1..8 UIDs接原Go Android-only group CLI和rootjournal version2共享表/优先级规则、锁/持久化/回滚/跨版本恢复；待同源Actions且真Android P2/P3未运行。"}
```
