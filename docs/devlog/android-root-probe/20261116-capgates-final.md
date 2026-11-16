# Android root 权限门槛独立实验——收口报告（2026-11-16）

## 本阶段结论

**有限范围内已完成权限门槛隔离，不是项目各项功能所需权限的总验收。** 独立实验分支 `experiment/android-root-permission-gates`，native SOURCE `a5794555e44efcb4945cc928cb8308258c93d8b0`，GitHub Actions [43806012347](https://github.com/lly8666/wbd-next/actions/runs/43806012347) **success**，Android 9/API28、12L/API32、16/API36 三个 AOSP x86_64、SELinux Enforcing、adb-root UID0 (`u:r:su:s0`) 模拟器各 21 组，**63/63** 实际权限正反对照均吻合。单次构建，API28+36 canary 后再 API32，中间版本使用相同哈希制品。没有触碰 main/M0、系统 boot/SELinux、生产客户端、物理机或全局路由/netfilter 规则。

**真实系统门槛**：三个镜像 `/dev/tun` 节点均为 `crw-rw---- uid1000 gid1016`；adb-root UID0 原始广泛 CapEff 能打开。缩减 CapEff/CapPrm 后，即使有 CAP_NET_ADMIN，`open(/dev/tun)` 仍会因 DAC 权限返回 EACCES(13)。若已在降权前打开并持有 TUN fd，CAP_NET_ADMIN 单独可在该 fd 上执行 `TUNSETIFF`，自有非持久接口关闭即消失。若需要**削权后再打开设备**，本 AOSP 范围内 CAP_DAC_OVERRIDE + CAP_NET_ADMIN 有效。CAP_DAC_OVERRIDE 单独可打开但 `TUNSETIFF` 返回 EPERM(1)。这是分开的**设备节点访问**和**内核 ioctl**能力门槛。

CAP_NET_RAW 单独有效：该进程使用真实 IPv4/TCP Raw Socket 在 loopback 发送 40B SYN 并观察内核 RST；没有 CAP_NET_RAW 的进程 Raw Socket 创建 EPERM。只在 lo 回环，不证明蜂窝/CLAT/raw 外层链路。

## 7种 CapEff/CapPrm 配置 × 3种真实内核操作

| 保留能力（其他 CapEff、CapPrm 全清） | 降权后打开 TUN + TUNSETIFF | 先打开 FD，降权后 TUNSETIFF | Raw TCP lo SYN/RST |
|---|---|---|---|
| 无 | 拒绝 | 拒绝 | 拒绝 |
| NET_ADMIN | **拒绝：open EACCES** | **通过** | 拒绝 |
| NET_RAW | 拒绝 | 拒绝 | **通过** |
| NET_ADMIN + NET_RAW | **拒绝：open EACCES** | **通过** | **通过** |
| DAC_OVERRIDE | 拒绝：ioctl EPERM | 拒绝：ioctl EPERM | 拒绝 |
| NET_ADMIN + DAC_OVERRIDE | **通过** | **通过** | 拒绝 |
| NET_ADMIN + NET_RAW + DAC_OVERRIDE | **通过** | **通过** | **通过** |

以上三个模拟器都执行全部 21 个组合、对照无不符。每次能力配置均在全新进程内 `PR_SET_NO_NEW_PRIVS=1` 后执行 `capset(V3)`，读回 /proc/self/status CapEff、CapPrm、CapInh，拒绝/成功均取真实 errno/报文观察结果；**降权后不 exec 任何其他程序**，避免 adb-root fork/exec 带来的提权假阳性。成功接口核对 /sys/class/net 中自有接口存在且关闭 fd 后消失。没有调整文件权限或写系统路由、规则、sysctl。

**限制**：CapBnd、UID0、supplementary groups 和 AOSP adb-root SELinux `u:r:su:s0` 依然维持原值。这是隔离当前进程的 CapEff/CapPrm/CapInh 的实验证据，**不是整个应用最小权限可行性证明**。尤其 TUN 的 MTU、地址、UDP 38/39B 全闭环在上一阶段的广泛 adb-root 权限下验证；本轮只对削权后的 **TUNSETIFF 创建/回收**做门槛验证，未执行外部 `ip` 子进程或配置路由，因此没有新声称“已用最小权限完成 TUN 数据面”。

## SOURCE/原始证据与历史 FAIL

- 成功原生 SOURCE `a5794555e44efcb4945cc928cb8308258c93d8b0`，一次构建 workflow [43806012347](https://github.com/lly8666/wbd-next/actions/runs/43806012347)；build artifact **14197649452**，ZIP SHA256 `fdcdb50b19af840d3a52e7f3aecb2543b03fc75a1afa7d9cfb27c999e0372237`，manifest SHA256 `f949f84b7397287c8033af4847c314a0c29bde753952e91acb0e07b4d9898efb`。原生 x86_64 binary `3cb936c2dd610605a82d2dcd164d74e0369ba5e393ffae4728f345ad2bd00e39`；ARM64 **仅构建** binary `ae22bdc2fc9fb40d5114fbd6b27764238d29b07036497484df583c0fbfc04e88`。已独立检查 ZIP 内全部 8 项 SHA256SUMS。
- API28 Android9：artifact **14198052659**，ZIP SHA256 `06fbc0446dfeb3c0c6312039d59a2c4f5faef58210b18e934aeb2353a52be10c`，21/21 PASS。
- API36 Android16：artifact **14198163475**，ZIP SHA256 `5cffde8b0aeb2cab1695ad6be38c1b317b417f871f0c0354553a77d11a8ed938`，21/21 PASS。
- API32 Android12L：artifact **14197914344**，ZIP SHA256 `9be1849eae9f7388061b7d06bf811155e4dd8ffd83236c0b5b455261a7bdd2b3`，21/21 PASS。
- **历史真实失败保留**：SOURCE `63ccd028df12f39904cc6ff0421abcae6d3a14e9` [Action43805552571](https://github.com/lly8666/wbd-next/actions/runs/43805552571)，错误地预期 NET_ADMIN-only 能打开 TUN，API28/API36 实际 open EACCES FAIL、API32 被正确跳过；后续**修订 SOURCE** 区分设备 DAC 与 ioctl 才通过，不能改写旧 FAIL。

[Machine-readable matrix](20261116-capgates-matrix.json) 载有 SOURCE、artifact IDs、ZIP SHA256、7×3 预期/实测状态、原失败轨迹。

## 对产品的合理下一步与未验边界

可采纳的**设计候选**：只在冷启动 root bootstrap 获得 TUN fd/完成必要受控配置，随后数据面尽量仅持有 NET_ADMIN（后续规则需独立验证）与 NET_RAW，避免长期持有 DAC_OVERRIDE/全部 Root caps；不能现在声称正式实现可行。若用 Android App→Magisk/KernelSU/APatch，真实授权、进程 UID/SELinux 域和执行路径仍未测试。

**NOT_RUN**：Android 17/API37（CI SDK 仍不可得）；真实 App→su/拒绝/撤权，Kotlin 当前 target 前台服务、后台/通知/no VPN 标志，按应用身份执行 Bionic，最小权限下完整 MTU/UDP，Android netd fwmark/策略路由/源选择，受控 netfilter SNAT/conntrack/forward，DNS UDP/TCP 53，IPv6/CLAT，蜂窝 raw 真出口/切网，Wi-Fi 热点/USB 两下游与 eBPF offload，异常杀死恢复，ARM64/16KiB 运行以及物理能耗。不可把 loopback/TUN 门槛测试当实际互联网共享、全功能权限通过或完整 Android 客户端交付。

**处置**：本权限门槛子实验成功收口；不自行部署真机或扩大到全局 Android 路由/NAT 写测试。若继续，需独立所有权隔离的路由/conntrack 夹具与普通 app→授权 su 的实际身份测试，仍不修改主线核心。
