# Android16 KSU Root：手动恢复和合成 Wi-Fi/USB 转发结案（2026-11-16）

**工作分支** `experiment/android-temp-root-probe`；**实验 SOURCE** `a5cca542f93e7c256145e07d7432b4dfa388e7c7`；[Action43872821388](https://github.com/lly8666/wbd-next/actions/runs/43872821388) **SUCCESS**。这是一条 Android16/API36 x86_64 Google Play AVD 中预配置 **真 KernelSU3.3.1 LKM+Manager** 普通 target37 App 测试，不是 DirtyFrag 漏洞提权、物理热点/USB 或生产 VPN 验证。

## 证据和哈希

- Artifact [14229385474](https://github.com/lly8666/wbd-next/actions/runs/43872821388/artifacts/14229385474) ZIP SHA256 **`9d6c57a88acee55a43dbd4829fe5f5bb4f7df445e78d65bf6b7f85bee399ecea`**，已下载并独立复核；native x86_64 sha256 `2dae1256f7db73e1515099f2d8f801cbba7e6c94a3acfb3848038c2fd0204622`；APK sha256 `8cacc2b0172a0ccf1ad87558365b0761a2e3e637e367e9cec1898173281e665b`；同 SOURCE。App UID10218、root native UID0、target37、SELinux Enforcing。
- 与旧测试同 SOURCE 的既有正例继续 PASS：`APP_UID_TUN_ROUNDTRIP_PASS`、`MAINSTREAM_DNS_TLS_PASS`（普通 App UDP/DNS53/TCP HTTP、系统 Network DNS、TLS1.3 证书+主机验证）及 `SIGKILL_WATCHDOG_CLEANUP_PASS`。

## 新增能力 A：App 再打开后手动一键恢复

- `ProbeActivity` 增加入口，`RecoveryActivity` 提供用户实际点击的 **「一键恢复正常网络」**；界面不会在 onCreate 偷偷清理。经独立 UIAutomator 实际定位按钮、点击、读取 App 私有 JSON，首次在已经植入仅供 CI 的遗留 `pref 8200 uidrange 10218-10218 to 198.18.254.2/32 lookup235` 场景返回 **`RESTORED`**；二次点击返回 **`ALREADY_CLEAN`**。每次由真实获得 KSU 授权的 App 以 `su -c` 调用原生 helper，UID0 和 App UID10218 一致。Android 主网络命名空间其他规则、所有路由字节级恢复到种子植入前状态。
- 原生回收只认精确的本实验旧 UID/目的 /32/表 235，拒绝别的优先级8200、其他表内容或仍存活的工作接口；不会对整机执行 `ip rule flush`、清空 iptables、修改 Android 默认路由；目前**保守限制于 AVD**，真机需先做持久、原子、自有条目 journal 才能开放这个按钮。
- 若临时 Root 已失效/`su` 不可用，普通 App **无法凭空获得清理内核规则的权限**。按钮可显示授权失败并提示重新获取 Root 或重启；不能保证无 Root 情况下一键强制恢复。用户的新要求只要求再次启动后手动清理，本包没有追加复杂的进程组死亡自动回收机制，原已通过的独立 watchdog 保留。

## 新增能力 B：两个模拟 Wi-Fi 客户端和一个模拟 USB 客户端真正经过内核转发

`tethergate` 先独立 `unshare(CLONE_NEWNET)` 且验证空 IPv4 主路由表，然后只在此新 namespace 建三个 owned 非持久 TUN：Wi-Fi subnet `10.128.11.0/24`、USB subnet `10.128.12.0/24`、模拟上游出口 `198.18.253.1`。在私有 namespace 打开 IPv4 forwarding，并配置按网段/唯一目的/唯一出口约束的 `iptables` SNAT + FORWARD/conntrack。真实注入 UDP IPv4 到下游 TUN，确认 kernel forwarding 后从上游 TUN 读到 **SNAT 成同一出口地址** 的报文，随后往上游写回复，确认 conntrack 把目的地址精确恢复到原下游。非复制输出、不是对内存中数据做字符串匹配。

| 下游模拟 | 源客户端与端口 | SNAT出口 | 出口/回包字节 |
|---|---|---|---|
| Wi-Fi #1 | `10.128.11.10:43001` | `198.18.253.1:43001` | 42 / 49 |
| Wi-Fi #2 | `10.128.11.11:43002` | `198.18.253.1:43002` | 42 / 49 |
| USB #1 | `10.128.12.10:43003` | `198.18.253.1:43003` | 41 / 48 |

三路均 `snat_pass=true`、`conntrack_reverse_pass=true`，`tether_private_netns=SUPPORTED_IN_SCOPE`，owned TUN 关闭即消失，主 netns 规则和路由前后字节完全一致。这证明多源共享一个 WBD 服务器租约/IPv4 出口的 **内核原型有路可走**，且独立 Wi-Fi/USB 两种下游可以通过同一 TUN 模型合并，并不要求为每个下游客户端新开一个 WBD 会话。

**严格边界：**`wifi-synthetic`/`usb-synthetic` 是隔离 namespace 的两个 TUN 网段，并非手机真正启用的 Wi-Fi Hotspot/USB tether；没有实物 Wi-Fi 芯片 AP、USB gadget、外部客户机、vendor tethering offload 或蜂窝基带。完整 Android Tethering 模块由系统掌控，Android 12+ 软件 eBPF 和硬件 offload 可能绕过普通 netfilter，因此本次绝不填写真实热点/USB/硬件offload PASS。<https://source.android.com/docs/core/ota/modular-system/tethering>；<https://source.android.com/docs/core/data/tethering-offload>。

## 历史失败不能抹掉

第一次 SOURCE `00a7bd66229da81087e82d2b8afaf3e2c81404d8` [Action43871859506](https://github.com/lly8666/wbd-next/actions/runs/43871859506) **FAIL**：虽有三路 SNAT + conntrack 正例，恢复按钮位于 `[24,24][296,72]`，被 Android ActionBar `[0,0][320,80]` 遮挡，导致点击没触发。后来 SOURCE `a5cca542...` 才将按钮置于 ActionBar 下方，CI 对点击区域做检查并用真实点击、App 私有结果验证两次回收，整条 Action 成功。旧 FAIL 维持原记录。

## Android 生产接入剩余真正障碍 / 不要跳步

1. **真实热点/USB 实验：**在独占 Android16 ARM64 Root 真机上，普通 App 用系统 `TetheringManager` / ConnectivityManager 观察两种共享状态和底层 Network；Root 只读盘点 ifindex、真实源网段、系统 netd 规则、IPv4/IPv6 转发和 eBPF/硬件 offload。分别真实打开系统热点和 USB 共享，用 Wi-Fi 至少两台/USB 一台下游跑 TCP/UDP 真实业务，证实包在 WBD TUN 与客户端两端都有回包与字节计数。确认 offload 不旁路后才对选中接口增量安装 owned 路由与 NAT；选择 Wi-Fi/USB 独立开关，系统仍负责 DHCP/AP/USB。
2. **生产可恢复配置：**将所有新增 iif UID route、table/mark、SNAT/conntrack 链和可变的 forwarding 参数写入有版本和原始值的原子 owned journal；App 重新打开后只删除属于当前 WBD 的对象，全部确认未被系统/其他进程改动。无 Root 要提示重新授权或重启，不尝试擦系统规则。
3. **全产品 Bionic 接线：**当前 `crates/wbd-platform/src/lib.rs` 对 `linux_raw_carrier`/`linux_tun_sink` 等使用 `target_os=linux`/GNU/musl cfg，Android Bionic Rust 已过单独探针，不代表原 Rust 长寿命驱动能直接编译、接线或符合 TLS handshake、generation、MTU1460、lane隔离/owned Stop 契约。需要专用薄平台适配与真正客户端端到端。
4. **常驻生命周期：**APK只验证普通短测，无正式 target37 FGS/通知、后台 Doze 与网络切换。Android15+ `dataSync` 前台服务有 6h/24h 限额；不能用它直接谎称可 24h 常驻，仍需符合允许类型及用户启停的受限设计。<https://developer.android.com/develop/background-work/services/fgs/timeout>。
5. **实体网络差异：**raw IPv4 经过真实 Wi-Fi/蜂窝、IPv6-only/CLAT、Private DNS/DoH、BPF/offload、运营商 NAT/空闲、SIM 切网和实际功耗均 NOT_RUN；Google Play 官方 x86_64 AVD 无法代替 OEM 真机。

**结论：**按键清理的受控原型和内核多下游共租约 NAT **同 SOURCE 功能 PASS**；未验证实体热点/USB 转 VPN，不能宣称完整 WBD Android 客户端已打通。下一步依赖一台获授权、可撤销配置的 Android16 ARM64 Root 真机，不再通过增加 AVD 用例刷真实设备资格。

[机器可读结果](20261116-tether-recovery-matrix.json)

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Source-lock API36 real-KSU App recovery-click and 2WiFi+1USB private-netns kernel SNAT/conntrack positive; keep real tether and Android full product NOT_RUN."}
```
