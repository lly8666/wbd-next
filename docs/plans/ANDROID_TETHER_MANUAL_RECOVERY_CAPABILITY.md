# Android Root 下的手动恢复和 Wi-Fi/USB 共享可行性 — 2026-11-16

## 目标 / 本工作包边界

唯一分支 `experiment/android-temp-root-probe`。仍不采用 `VpnService`、不改内核/boot/system、不涉及 M0/main、不启动生产 WBD Android 客户端。原 Android16/KSU3.3.1、targetSdk37 App 经真实 su 授权及真实 UDP/DNS/TCP/TLS 网络正例不被混为共享结果。本包把 **App 重启后用户手动按键** 设为期望恢复模式，而非承诺整个 su/内核退出时自动恢复，既有独立 watchdog 保留但不作为产品硬依赖。

## 临时 Root vs 常驻 Root

Root 能否修改 TUN / raw / NAT / netd 取决于真实 UID、capabilities、DAC、SELinux 和内核功能，不因拿 Root 的方式不同而自动减配。DirtyFrag 成功后的 Root 模块和 `su` 会随重启消失，而已被 Root 写入的内核路由/iptables 状态不会因为普通 App 进程退出自动回滚；TUN 若非持久且最后 fd 关闭通常消失。Kill App 不等于撤销另一个进程现有的 capabilities。重启前重新打开 App 时若 su 失效，恢复键必须报 `SU_UNAVAILABLE`，不能声称已恢复。完整 reboot 恢复 root 和非持久规则的行为要按实际设备测。

## A. 显式的安全恢复键（已实现，待实测）

- Root helper `android-root-probe recover <real_app_uid>`：仅 AVD 中工作；精确匹配 `pref 8200 uidrange UID-UID to 198.18.254.2/32 lookup 235` 和最多一个 `198.18.254.2 ... dev wba<hex>` 的受控历史 route。其他 `pref 8200`、表235内容、当前仍存在的 wba 接口、不是模拟器、非 UID0 立即拒绝。不能删 Android 默认路由、netd 独立规则、全局网络链。
- 另有仅 CI 使用 `recover-seed <uid>`，只在原规则/表均空时植入一个精确 orphan 的 WBD /32 rule 供真实 Button 复原，**不**模拟假 Root。
- 普通 targetSdk37 `RecoveryActivity` 有真实文字 `一键恢复正常网络` Button；默认不执行恢复，只有用户点后才发起已授权 App 的 `su -c` 进程。`RESTORED`、`ALREADY_CLEAN`、`REFUSED_AMBIGUOUS/ACTIVE_WORKER`、`SU_UNAVAILABLE` 分别明示，保存 app 私有取证文件；原启动页增加入口按钮。
- 真机需要下一步添加跨进程/跨重启的 **原子 owned journal**（UID、rule、链、route、原值、签名/权限等）及精确恢复列表后才能安全开放按钮，目前显式 fail closed 而非声称真机可用。这是调试 APK，未做生产系统包/FGS。

## B. 共享 Wi-Fi/USB 经过同一 Root TUN 的可行性（已实现夹具，待实测）

- Android 原系统继续负责热点/USB DHCP、网段分配、系统共享开关；不自己造 AP/USB gadget，不用 `VpnService`；root worker 未来只接管经过内核数据路径的特定共享入口。
- `android-root-probe tethergate` 首先 `unshare(CLONE_NEWNET)`、验证独立且空路由表；之后**仅在这个私有网络 namespace** 创建三个非持久 TUN：合成 Wi-Fi 下游 `10.128.11.0/24`、合成 USB 下游 `10.128.12.0/24` 和模拟上游 `198.18.253.1`。在命名空间里开启转发，安装源网段/出口精确的 IPv4 SNAT、单条 FORWARD ACCEPT/ESTABLISHED 规则；绝不在 Android 主 netns 操作 NAT。
- 两个合成 Wi-Fi 设备 (10.128.11.10 / .11) + 一个合成 USB 设备 (10.128.12.10) 发 UDP packet 进入各自下游 TUN，必须在上游 TUN **读到源地址 SNAT 为同一 198.18.253.1**；向上游写返回包并在对应下游 TUN 读到 conntrack 的正确客户端目的地址。全部 3 个 roundtrip 才准 `SUPPORTED_IN_SCOPE`；`iptables/namespace/conntrack` 缺失报 `UNAVAILABLE`，不在 host namespace 退而求其次。
- 上述证明内核网络命名空间中 NAT/转发能力、两个不同下游和一个共享上游的策略模型。**不代表真正 Wi-Fi 热点或 USB downstream**，因为 Android13+ eBPF tethering offload 及 vendor hardware offload 可能直接绕过常规 iptables hook。需要真实 2 个设备、Wi-Fi/USB 数据计数及返回包，验证上游 route / netd / checksum / SNAT / IPv6/CLAT、bpf map 和 offload 才能宣布真实共享支持。
- **安全红线：**服务端单一租约地址校验不能关闭；NAT 必须使来自任何下游的包满足租约。不能全局禁 IPv6、不能变更整机默认 NAT，允许热点/USB 独立选择接入，且依照原项目 MTU 外层默认1460计算内层预算，不假定热点 MTU1500可无分片转发。

## C. Actions 源锁验证

仅复用 `.github/workflows/android-root-ksu.yml` 的单个 Android16/API36 x86_64、SELinux Enforcing、真 KernelSU3.3.1/Manager 普通 target37 App AVD，在已经验证的 App UDP/DNS/TCP、SIGKILL 后同一 AVD 下执行一次新 `tether-recovery-case.sh`：source-locked native/A PK hash、主 namespace 规则/路由前后完全一致、独立 namespace 的合成转发证据、精确 seed，UIAutomator 确实点击 RecoveryActivity 实际 Button，首次 `RESTORED`，第二次 `ALREADY_CLEAN`，最后主路由与原规则字节一致。无权限/缺内核模块必须单独 `UNAVAILABLE`；绝不把 CI success 当产品热点成功。一个 Action 一个 AV D、同 SOURCE，不发多个重复工作流。

## D. 真实剩余障碍 / 下一步选择

| 阻碍 | 当前证据与可行性 | 必须真机或继续工作 |
|---|---|---|
| 普通 App Root→TUN、DNS/TCP/TLS | 已有 API36 KSU 实测 PASS | 生产权限生命周期仍需独立适配 |
| 临时 Root 后按键恢复 | 仅受限实验按钮和精确-owned删除，CI 待验证 | 用真机持久 owned journal；权限已消失则仅能提醒用户重启/重新获取 Root |
| 2 Wi-Fi + 1 USB 下游 SNAT/TUN | 仅合成隔离网段，CI 待验证 | 两个真实设备及 USB peer / 独立热点出口捕获和回包 |
| eBPF/HW tether offload | 无 AVD 的 OEM 路径 | OEM 当前实际转发路径计数+对照；必要时由用户主动选择可撤销 offload 兼容模式 |
| IPv6-only 蜂窝 CLAT/热点IPv6 | 暂不改系统 IPv6 | 真机测 IPv6 路由/双栈、DNS Private DNS/DoH、PMTU |
| 网络切换、FGS/Doze 与功耗 | 未完整集成 | Wi-Fi↔蜂窝，原生 target37 的前台服务/用户通知/息屏/CPU 实测 |
| 生产 WBD 协议融合 | 探针不是完整客户端 | 复用原 Rust 核心、Go 冷控制策略、同源认证/TLS/租约/MTU/Stop；不可凭模拟器宣称成品 |

官方资料：<https://source.android.com/docs/core/ota/modular-system/tethering>（Android 12+ BPF 软件卸载）；<https://source.android.com/docs/core/data/tethering-offload>（HAL 硬件卸载可直接绕开应用处理器）。

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Add explicitly clicked ordinary-App owned recovery and private-netns 2xWiFi+1xUSB NAT feasibility probe with CI source/cleanup gates; physical tether NOT_RUN."}
```
