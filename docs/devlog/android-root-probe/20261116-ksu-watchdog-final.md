# Android KSU 真 Root 网络工作进程 SIGKILL 恢复：实测收口（2026-11-16）

## 判定与范围

源码 `d07da32f8afd8d03ce5df2f5cdbe3a54cfd7b14b`，真实 [GitHub Actions 43828757323](https://github.com/lly8666/wbd-next/actions/runs/43828757323) **SUCCESS**；Android16/API36 x86_64 一次性 AVD、SELinux Enforcing、真 KernelSU v3.3.1 LKM + Manager。此 SOURCE 先确认普通 App↔Root TUN 真 UDP 往返，然后执行 **Root native 工作进程单独 SIGKILL** 实测。没有跑新的 API 矩阵、模拟 Root 或 adb-root 冒充。

### 真实普通 App 数据面未回归

APK `org.wbdnext.rootprobe`、UID10218、`u:r:untrusted_app:s0:c218,c256,c512,c768`、targetSdk37，经真实 KSU Manager 对该包授权；App `su -c` 返回0，子进程为真实KSU UID0。App 自行发送40字节 nonce UDP，Root owned TUN 实收完整IPv4/UDP **68B**；Root 经 TUN 注入 **70B** 的IPv4/UDP回复，原 App 同一 DatagramSocket 收到42B对应nonce。测试状态 `APP_UID_TUN_ROUNDTRIP_PASS`，原正常清理验证通过。

### 独立监护在 SIGKILL 后删除孤立规则

Native `appflow` 在配置网络对象**之前** fork 独立的 KSU Root 监护进程。监护不继承 TUN fd、关闭App标准I/O、创建独立会话，并用 `pipe2(O_CLOEXEC)` 读端监测工作进程寿命。崩溃分支 `appflow-kill 10218 killd07da32f8afd8d03` 在创建非持久TUN、UID精确路由规则并输出 `WBD_APPFLOW_READY` 后，对工作进程自己的PID执行不可捕获 SIGKILL。真实命令退出码 **137**。

进程死亡后监护进程通过管道 EOF 醒来：明确检测到原工作进程留下的 `pref8200 uidrange10218-10218 to198.18.254.2/32 lookup235` 规则，并执行**仅匹配该条规则**的删除。其JSON报告：`rule_seen_after_owner_exit=true`、`rule_removed_by_watchdog=true`、`rule_absent=true`、`table235_empty=true`、`status=CLEANED`、`errors=[]`。非持久TUN fd随SIGKILL自动关闭，路由由内核自动移除，所以报告 `route_seen_after_owner_exit=false`、`route_removed_by_watchdog=false`；**不把内核清理谎称为监护进程手动删除**。

CI另外读取强杀前后的全部IPv4 rule和table all路由快照，文件**字节一致**，空表235，整体 `SIGKILL_WATCHDOG_CLEANUP_PASS`。没有写Android默认/main路由、netd/NAT、iptables，未关闭SELinux或更改手机boot/system。

### 原始制品与独立核验

- Action [43828757323](https://github.com/lly8666/wbd-next/actions/runs/43828757323)，artifact **14208026577**，97文件，ZIP SHA256 `a4d4f51c3129844a0041bc620d9a873260921a3411a7ebd9e2213d9ff932a219`。已下载独立检查。
- Native Bionic x86_64 binary SHA256 `210596706fd0702780e42c9af0757ff543f913eb4e2305d7f074c07b2fe14ce9`；本次源码和两项测试同 SOURCE。
- App实际双向UDP `appflow/summary.json` SHA256 `91374441c38380917fa84e737921499a63e3eb8680c431096ee3d0ca1ef8214d`。
- 异常退出 `appflow-crash/summary.json` SHA256 `f558f90a8a140e991b08ef890c4d3114c490f6cf4472e38c07f1139a65960b65`；独立 `watchdog.json` SHA256 `3bf424fdbff873b66dcd52f227619ec651fccbe0a9392eecd6481abdbb7dba18`。
- 强杀 rule-before 与 after SHA256同为 `eee931a3c3f8996ab3289d4fb148c405ec4017431b7722d84a4ce93662471d15`，route-before 与 after SHA256同为 `df6c86f5d1c6fef1cdaeb6523725ee6ebd4ea4dae6ca0a1556d9d8067f4ddaa2`。

### 边界

这一项是**KSU shell夹具**对相同Root native网络工作进程单独SIGKILL，不等于普通App被force-stop、整个Root进程组同时死亡、监护进程也死亡或手机重启时的恢复。硬件前置限定QEMU模拟器、实际UID＋单个合成/32路由，生产Android Root service尚未接入。真实Android netd选择实际外网、NAT/conntrack、热点USB、FGS、真机ARM64/OEM/蜂窝、IPv6等仍NOT_RUN。主线/M0不动。

机器可读矩阵：[20261116-ksu-watchdog-matrix.json](20261116-ksu-watchdog-matrix.json)。后续应处理受控网络出口与生命周期，而不是重刷Root/权限可行性。

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Source-lock actual Android16 KSU App↔TUN UDP and independent watchdog orphan UID rule removal after true worker SIGKILL exit137; keep product netd/NAT/OEM and wider crash scope NOT_RUN."}
```
