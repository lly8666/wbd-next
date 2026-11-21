# Android CN Split 设置 UI 真实点击与持久化验收（2026-11-16）

原 SOURCE `38fc188f35b9b15540222c41e2245b69344a093d` 的 Android16 KernelSU3.3.1 [Action43896138626](https://github.com/lly8666/wbd-next/actions/runs/43896138626) **SUCCESS**，证明同源 x86_64 native `android_split_policy` 和内核独立namespace `android_split_uid_kernel` 各 PASS、10/10 `ip route get` UID模式判例，旧自包含Root/TUN/IPv6/策略路由/NAT正常回归。构建同时生成来源固定的 APNIC CN IPv4 前缀 **5500** 条。本正例不代表主网Apply、真实CN DNS上网或WBD产品VPN已通过。

后续补真实 GUI/配置验收：保留从真实 App 主页面入口打开 `SplitSettingsActivity`，UiAutomator 滚动输入 `uid:10502`、选择该 UID global 覆盖，同时默认split/直连 DNS 223.5.5.5/隧道 DNS 1.1.1.1；点真实「保存并经 Root 验证策略」按钮，由普通目标App UID调用已授权 su 在 APK 自带nativeLibraryDir验证原子保存的App私有 JSON，检查APNIC CIDRs>1000、uid模式、compiled CN intervals>500、bootstrap DIRECT、无 FakeIP、`installed:false`。Root 解析后留下第二份 `wbd-split-validation.json`，证明UI配置后原生实际读回而非内存mock。

另修复保存用户额外CN CIDR、共享UID别名覆盖方式；之前配置恢复过程仅在没有预装CN表时才回填手工CIDR，可能在重新打开编辑器后丢失额外规则，新行为单独保存/恢复 `custom_cn_ipv4` 并确保共享UID只有一条策略，冲突直接拒绝。

**仍未打开 Android 主路由 Apply 和 DNS listener**，本用例需要与原真实 WBD TLS/control owner、可恢复网络配置一同发布才可认定用户实际分流。旧CI首个成功证据保持历史SOURCE。

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Add real Android UI per-App mode override/save/native Root validation of source-pinned CN IPv4 snapshot; persist custom CIDRs; no main netd Apply or product VPN claim."}
```
