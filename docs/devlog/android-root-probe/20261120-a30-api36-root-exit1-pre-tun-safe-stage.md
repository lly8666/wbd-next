# A30｜API36 用户实测 EXIT_1/PRE_TUN 与只读分段诊断

**输入来源**：用户自己安装并运行源锁 Android Root Lite v2 APK `6bcdbc6c7c27b71a8ea47c25f8385cd177daa985`、报告 Android API36，主动提供固定枚举V1 TXT（无服务器地址/私钥/用户名/包名）。事件顺序包含 NETWORK_SCOPE_VERIFIED、APP_UID_GROUP_VERIFIED、默认 ROUTE_SCOPE_ALL_ORDINARY_APPS_IPV4、NATIVE_SOURCE_VERIFIED、ROOT_GRANT_REQUESTED、ROOT_PROCESS_LAUNCHED (1795106883788ms) → ROOT_PROCESS_EXIT_NONZERO (1795106884129ms)、ROOT_EXIT_BEFORE_GO_RAW、OWNER_CLEANUP_FINISHED。相隔 341ms；UI退出码1 PRE_TUN。**不能把 Java ProcessBuilder启动su视为root获授权或原Go已执行；Java finally清理不证明真实内核uidrange/Stop已清理**。既无 TUN/RAW，也无WBD原FakeTCP/TLS/32租约/M4数据；当前不推断服务器/TLS/密钥错误。该实际 Android 应用运行资格只证明早期pre-TUN失败，不替代未来产品E2E。

**A30 源码切片**：不改变 app现有 Root原二进制执行、私有0700目录、owner PID/starttime/代际精确Stop、标准TLS/原Go/Rust M4/MTU/路由。真正的 `su -c` shell 仅echo固定WBD_PUBLIC_ROOT_*阶段：命令进入、EUID0、私有目录读回、旧owner守卫、Go/Rust文件复制、owner.pid写入、exec请求。真正的 Android Bionic Go原 `v4productcli.Run` 打印常量 GO_ENTRY、ARGS_REJECTED/ACCEPTED、INTERFACE_FOUND、TUN_OPEN_ATTEMPTED/OPENED。Java生产RootService通过原 `OriginalGoMilestones.matches` 只接收精确只读标记，导出报告只打印枚举+13位ms+SOURCE/API/固定阶段分类，拒绝任意原stderr/原生行、IP/UID/密码/key/设备信息。对带START_DIAGNOSTIC_STAGES_V2的新 session 的非零退出进行保守最后可证节点分类，V1旧报告仍未分类，不把旧数据误判为KernelSU错误。

Host同一Java报告回归用户旧11个固定事件及14类V2非零退出与敏感文本拒绝，Go/ARM64同源签名APK与原Linux oracle保留准入门，CI x86 KSU/TAP guest均手工opt-in。**这次无权在此聊天操作用户真机或服务器**；新签名APK需用户自行备份旧收据、确认无原生Root/UID残留再卸载旧调试版。下一次真实收据若仍fail，按最末阶段收窄 Root目录/SELinux/ELF/Go参数/物理接口/TUN；不擅自修TLS或wipe内核规则。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"用户真实Android API36首报Root子进程exit1 PRE_TUN；添加原root脚本和Go入口安全固定阶段以高效分类，旧收据语义保留，证据不泄露凭据。"}
```
