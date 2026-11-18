# A21：Android 默认代理所有普通应用（2026-11-18）

用户明确要求将 Android 客户端默认行为从最多 8 个手选 App 改成全部普通 App。正式 Android Root UI 默认 allAppsDefault.setChecked(true)，仍可关闭此开关，返回已验证的 1–8 个可见 App 精确 UID 路由。

## 本次新实现
- 原 Go Bionic 客户端新增 --android-route-all-apps 和 --android-route-exclude-appids，和单 UID、多 UID 选项互斥。必须提供 2–8 个严格排序去重、范围 10000..19999 的 per-user AppID 排除项（WBD 本身及已安装 Root Manager），不是任意系统 UID。
- 新原 rootjournal.NewAllApps 使用版本3 的 0600 专用持久 journal、fsync、flock、NOFOLLOW、exact kernel rule readback、逆序 Stop/崩溃恢复与外来路由拒绝。使用私有 table19842 为 Android user 0..19 的每个普通 AppID 10000..19999 建立 UID range，按每个 user 段重复排除 WBD 与 KSU 管理员 AppID，绝不触碰 main/global default 路由，不能误拦截 root、system、isolated UID。
- Java AllAppRouteScope 通过真实 PackageManager 获取 WBD App UID 与已安装的已知 Root Manager UID（me.weishu.kernelsu、com.rifsxd.ksunext、com.sukisu.ultra），无 root 管理器则拒绝全 App；在 Service Start、su 之前再次核验一致性并监听 Root Manager 包更新停止。查询白名单包名，无 QUERY_ALL_PACKAGES 权限。
- 额外 Go rootjournal/allapps_test.go 与 Java AllAppUIDPolicyTest 验证用户空间、系统排除、原 root-owned kernel 路由事务与 Stop 精确回滚；Linux x86 原 server host job 运行 rootjournal Go 测试。CI-only 原 D2 App 继续走单选 UID，不分叉 WBD Go/Rust TLS/协议/M4。

## 安全及验收边界
“默认代理所有 Android 普通应用”不是默认修改系统 HTTP Proxy，也不代表已经接管 Android system_server、netd、root、系统 DNS、isolated UID、IPv6 全部流量。本次仅为已知安全 AppID 段。系统 DNS takeover 双冷门依旧 false；只有原 Go TLS/真实账号认证/自动 /32 租约及 Rust M4 真 DATA handoff 完成，才可以落实际全 App UID 内核路由。

历史基线 SOURCE 6249e6e1 的 Actions #44264710604 已整体 SUCCESS（同源 ARM64/x86 构建、KSU App su、原 Linux server、RootService TUN/RAW 和真实 SYN Sendto），但有效 SYNACK/TLS/租约/双向应用 TCP+UDP/完整 Stop 仍 NOT_PROVEN。TAP 主机准入 #44264710804 SUCCESS 不等于 TAP Android Guest。**本次新增全 App 范围真实 Android 内核 E2E 尚未运行，不能预告 PASS。** 只改实验分支/ Draft PR #36，main/M0 不变。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A21 Android 全普通 App UID 默认代理：Go rootjournal version3 多用户 UID range、自身/Root Manager appID 排除、精确 kernel readback+Stop，Java UI 默认全应用和 PM 二次核验，传统单 App 可切换；root/system/DNS 仍绕过，E2E 未证实。"}
```
