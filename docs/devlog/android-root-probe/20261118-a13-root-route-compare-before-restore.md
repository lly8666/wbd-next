# A13｜正式原 Go Android UID owned 路由：严格内核回读、保留 A12 真机失败

施工分支：`experiment/android-temp-root-probe`，目标 PR #36 → main；未改 main/M0 registry/cursor。

## 本轮新实机证据（用户 2026-11-18 提供）

A12 真实 ARM64 KernelSU 同一 APK 的脱敏回执包括 `NATIVE_ARM64_KERNEL=PASS`、`PHYSICAL_NETWORK=PASS`、`SOURCE_AND_APK_ASSET_SHA=PASS`、`ROOT_PASS`、`GO_ELF_HELP_PASS`、`TUN_PASS`、`RAW_PASS`、`UNDERLAY_PASS`、`ROUTE_UID_PASS`、`ROUTE_ROLLBACK_PASS` 和 **`A12_TUN_INTERFACE_DISAPPEARED`、`A11_UID_TUN_ROUTE_FAIL`、`A11_UID_TUN_ROLLBACK_PASS`、`A11_ROOT_CHILD_EXIT_NONZERO`**。`REAL_APP_UID_TO_TEMP_TUN_PACKET=NOT_PROVEN`。A12 固定分类仅证明隔离测试中在路由设置前，`wbdst11` TUN 已不存在；不能仅凭枚举判定是超时、FD 生存期、netd 还是其他原因，不能推出生产 Rust owned TUN 会消失。**不增探针按钮、不宣称真实流量已到达。**

`REAL_TLS_AUTH_LEASE=NOT_RUN`，`REAL_M3_M4_APP_DATA=NOT_RUN`，`SYSTEM_DNS_TAKEOVER=NOT_RUN`（DNS 安全门仍 false）。缺同源实体 WBD server/凭据/授权的实机端到端，不替代实际首次业务证据。

## A13 完整生产代码/测试改动

原 `r0/go_overlay/internal/v4productcli/rootjournal` 同时服务正式原 Go 单 UID 和多 UID group owned 路由；路由 journal/flock/Stop 已存在。检查发现：原 `ruleState` 和 `groupRuleState` 对预留优先级+表+UID 的宽匹配会把带额外 `fwmark`、`iif`、`not`、`suppress_prefixlength` 等条件的内核规则错认为自有规则；原 `routeState` 对相同 TUN 的未知 route 属性也接受。这可能导致重启恢复或 Stop 的 compare-before-restore 删除外部改过的规则。

现在两个 UID 路径复用 `strictOwnedUIDRule`：仅接受本产品 `ip rule add pref ... uidrange ... lookup 19842` 的 canonical readback（可接受 `from all to all` / `table` 文本等价）；新增匹配条件、重复 token、异 UID、异表/优先级均 fail closed。route readback 仅允许 `default dev <owned-TUN>` 和内核正常 `scope link` / `proto boot`，对 metric、via、src、mtu、重复属性等拒绝。既不放宽规则，也不修改系统 fwmark、默认表、全局 DNS、Rust 热路径或 TLS。

新增宿主 Go 回归覆盖 canonical / 外来选择器 / route 属性、单 UID 与多 UID **Stop 拒绝清除外来修改并保留 durable journal**，撤回模拟额外属性后仍可按原 owned Stop 正常清理。现有 rootjournal durable crash recovery 和 Linux original-server Normal/off oracle 保持复用。

## SOURCE/Actions/未验与唯一下一步

本次代码+夹具+功能卡在一个 commit 冻结 SOURCE；由 `.github/workflows/android-root-product-a1.yml` 的 `arm64-native` job 自动运行原 donor 装配后的 `go test -count=1 ./internal/v4productcli/rootjournal` 与 Bionic ARM64 构建；其余同源 job 原样运行。当前文件写入时**新 SOURCE Actions = NOT_RUN / pending CI**，不转述之前 SOURCE 的 10/11 为本次 PASS。x86 KSU NativeBridge 139 是独立历史红门；真实 A12 UID 流量与 WBD TLS/M4仍未验证。

**下一步只做一件事：**核对本 SOURCE Actions 和正式原 Go/Rust 构建/route 测试收据；随后在具备授权的 Android16 ARM64 KernelSU + 同 SOURCE 真实 Linux 服务端及有效凭据条件下，跑 Normal/off 的真实 TLS→认证/租约→双向 TCP/UDP→owned Stop。无凭据/实体机授权时保持 NOT_RUN，不再扩展合成按钮。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A12 用户真实 ARM64 回执表明测试 TUN 路由前已消失，真实 WBD仍 NOT_RUN；A13 收紧正式原 Go rootjournal 单/多 UID owned readback 与Stop，不允许删除带额外选择器的外来规则，新增 host 回归。"}
```

## A13 同源 Actions 实际结果更新（2026-11-18）

冻结的 **代码 SOURCE `466b641527f61ac64cc4f9c7c813835dc477b50c`**；
[Android ARM64 root 产品 Action #44215447605](https://github.com/lly8666/wbd-next/actions/runs/44215447605)。
当前已直接核验 `arm64-native` **SUCCESS**，其原 donor 装配后的
`go test -count=1 ./internal/v4productcli/rootjournal` 实际输出
`ok github.com/lly8666/wobuzhidao/internal/v4productcli/rootjournal 0.037s`；
`root-arm64-app`、`linux-original-server-normal-off`、DNS/codec host 和
`arm64-cuttlefish-host-admission` **SUCCESS**。最后的 x86 NativeBridge
任务核对时仍 `in_progress`，整条 Action 结论**尚未结束 / NOT_RUN 不可改 PASS**。
host-only Cuttlefish admission 不是 Android16 ARM64 真机业务。手机 TLS/M4 仍 NOT_RUN。

原 SOURCE 的治理 Action #44215447468 **FAIL** 是本轮卡片超过
16 KiB 的仓库格式限制，而不是原生回归 FAIL；后续仅 docs commit
`809b0ed8ef99448d0d4d0b1ecd01e26af84cc9e3` 已将卡片收敛到
16,338 UTF-8 bytes（不删除历史 verification），但独立提交未同步修改
devlog 而触发第二次 feature-impact 声明门 FAIL。本次进一步同时修改功能卡和
本 devlog，保留相同 feature-impact，按真实最新 governance Action 再确认结果。
原生产品构建仍严格指向上述冻结代码 SOURCE，不拿 docs-only HEAD
伪装成已重编的 APK。

## A13 SOURCE 最终冻结 / red gate 与治理收据

同源码 [Action #44215447605](https://github.com/lly8666/wbd-next/actions/runs/44215447605)
**最终 10/11 Jobs SUCCESS，overall FAIL**。成功的是原 Go rootjournal host Go tests、
NDK ARM64 Go/Rust/source-locked signed APK、Linux 原 WBD 真实服务端 Normal/off oracle、
DNS/M3 host 与 Cuttlefish host-admission；唯一 FAIL：
`android-x86-kvm-ksu-arm64-nativebridge`。该 job 官方原 Go ELF
`ORIGINAL_WBD_ARM64_EXIT=139`、纯 Go ELF 139，
`ORIGINAL_GO_CSHARED_HELP_EXIT=0`，退出码10；
这是 x86 KVM NativeBridge 限制，不否定用户真实 ARM64 手机已给的 Go help PASS。
**实体 Android16 原 WBD TLS/租约、双向 App TCP/UDP 和 Rust owned Stop 仍 NOT_RUN。**

文档 HEAD 与冻源分开：`466b641527f61ac64cc4f9c7c813835dc477b50c`
是所有这些新原生构建和测试的 SOURCE；后续两次文档更正未重编 APK。
最新卡片现保留所有 64 项历史 verification，并追加带冻结 SOURCE 的 A13
`BUILD_PASS` 记录。此前 #44215447468 因卡片字节超限 FAIL、
#44215876974 因 docs-only 未同期声明 feature-impact FAIL，
不能删去失败历史；本轮以卡片和 devlog 同 commit 修正并由最新治理门确认。
唯一下一步仍是真 ARM64 授权条件下原 WBD Normal/off TLS→租约→TCP/UDP→joined Stop，
没有凭据/实机执行则 NOT_RUN。
