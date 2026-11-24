# Android 临时 Root：同分支隔离策略路由实测结果（2026-11-16）

## Decision

**SUPPORTED_IN_SCOPE 仅限 AOSP x86_64 模拟器内核的独立命名空间策略路由，不是 Android 系统 netd、完整 Root 客户端、真实热点/USB、NAT 或转发 PASS。** 全部代码与本报告现只提交到 `experiment/android-temp-root-probe`；之前迁回的权限缩减 63 组测试证据、失败和结论不变。唯一真实测试源码 SOURCE `42cca27e8a6b8d4e5db38e72c2b3ddd0fef61b2d`。

GitHub Actions [43808870202](https://github.com/lly8666/wbd-next/actions/runs/43808870202) **SUCCESS**：Android 9/API28、Android16/API36 先做两端 canary，再 Android12L/API32 中间复核。三个不同真实 AOSP x86_64、SELinux Enforcing、adb-root UID0 实例 **3/3 SUPPORTED_IN_SCOPE**；每实例独立 native 命令执行，没有手工推算 PASS。

### 同一 SOURCE 的内核证据

| Android/API | 独立 Action job | 源码 | 原/新 netns identity | 未标记 UDP | SO_MARK 标记后 TUN 收包 | owned 回收 |
|---|---|---|---|---|---|---|
| Android9/API28 | 133105812501 | `42cca27e...` | net:[4026531964] → net:[4026532371] | ENETUNREACH/EHOSTUNREACH | 39B | 成功 |
| Android12L/API32 | 133106653419 | `42cca27e...` | net:[4026531998] → net:[4026532851] | ENETUNREACH/EHOSTUNREACH | 39B | 成功 |
| Android16/API36 | 133105812356 | `42cca27e...` | net:[4026531840] → net:[4026533052] | ENETUNREACH/EHOSTUNREACH | 39B | 成功 |

每个实例在任何路由操作前都先核验 `unshare(CLONE_NEWNET)` 产生与进程原始 namespace 不同的 ID，再验证新 netns 的 `/proc/net/route` IPv4 主路由表为空；不满足则禁止后续修改。仅在该独立 netns 内生成 **非持久 TUN**（198.18.253.1/30），设置并用 `SIOCGIFMTU` 读回 MTU **1400**；创建自有策略路由 **table 235**、规则优先级 **12000**、fwmark **0x23500**；`SO_MARK` 读回 **144640**；无标记负对照无路由，标记后确实读到正确 src/dst/payload 的 39 字节 IP/UDP 包。关闭 fd 后由 namespace-aware RTNL `ip link show dev` 验证接口消失；仅该进程存在的 netns 在退出时销毁。Android 系统原有策略规则与所有路由 **前后逐字一致**，且无真实物理出口流量。API28 忽略其它包0个、API32/36各1个。

### 构建与制品原始哈希

这轮没有为每个 case 编译：唯一原生 Bionic x86_64+aarch64 NDK build [43808870166](https://github.com/lly8666/wbd-next/actions/runs/43808870166)，artifact **14200125029**，SOURCE `42cca27e8a6b8d4e5db38e72c2b3ddd0fef61b2d`；构建ZIP SHA256 `3f5838b3f4affa945832b84b2fca3ac46122b8b48db18baa74d0bd55dbc1a374`，manifest SHA256 `84b053f1315d655f6811c5214014b0c270406e07a064c59d7b9dd6db6fe6b0f5`；x86_64 二进制 SHA256 `c1b443392e896bc77b0887e05efec01baff8212bc5f9a06e52a62709bdc8b6e8`，aarch64 二进制 SHA256 `c48d9d1d817c2a348512f037d814a3d098437a28d63ec23ca98d78f095cfc1d3`（**ARM64 仅交叉构建**）。已独立验签式核对清单中 8 个 SHA256SUMS 项目，0 不匹配。

同一 Action 的独立 case artifact：
- API28 artifact **14199935861**、ZIP SHA256 `6c43a46fc89b7a0b3318c3aad90a8dc956a0543da0de2b0cdc480fb45c29164a`
- API32 artifact **14199532936**、ZIP SHA256 `f2f3454b7cb441aa9bf8ef7c9b19f2a9fd588d27d7f9b6559bcea42d791a0825`
- API36 artifact **14198869728**、ZIP SHA256 `48cc56040593c91a8cea90a9118d43fca4e6a05879e6e62827d10db067c24f2b`

[Machine-readable matrix](20261116-routegate-matrix.json) 载明源码/失败源、run/job/artifact、每个 ZIP SHA256 和原始操作范围。

### 历史拒绝与源差异（保留）

- 初版 SOURCE `a40fbc0b94512c4702a0724f81d3248a9a9683e3` build [43808360398](https://github.com/lly8666/wbd-next/actions/runs/43808360398) 成功，但 [Action43808360345](https://github.com/lly8666/wbd-next/actions/runs/43808360345) 两端 API28/API36 都 **ENV_BLOCKED**，API32按流程 SKIPPED。内核 unshare 已成功并返回不同 netns ID，但在未共享 mount ns 的 Android 上 `/sys/class/net` 显示的不是新网络命名空间的接口集合，旧防护错误地把其视为含系统接口而阻止任何 TUN/策略路由写入。Android 全局 route/rule 前后相同。修订 SOURCE `42cca27e...` 改用 netns-aware `/proc/net/route`、RTNL link 与 SIOCGIFMTU，不能把历史 source 结果改写为 PASS。
- 较早 SOURCE `63ccd028...` [43805552571](https://github.com/lly8666/wbd-next/actions/runs/43805552571) 的 TUN 设备 DAC 权限预测失败，以及后续 `a5794555...` [43806012347](https://github.com/lly8666/wbd-next/actions/runs/43806012347) 的 63/63 权限对照通过，仍只在原源与限定 AOSP 情境中有效。

### Remaining gates / 不可推断

- **未验证**普通 App→Magisk/KernelSU/APatch 用户批准 su/拒绝、实际 App SELinux 域、最小 capabilities 运行整个策略路由（本夹具用广泛 adb-root 权限并依赖 CAP_SYS_ADMIN 进入测试 netns，**不得作为产品权限要求**）。
- **未验证**Android 系统 netd fwmark 与动态出口选择、外层 raw 真实蜂窝/CLAT、真实热点与 USB 客户端、offload、转发 / NAT / conntrack 双向 SNAT/恢复、DNS UDP/TCP53、IPv6/切网、后台 FGS/通知、原生 ARM64/16KiB 页运行、真机耗电、异常杀进程规则清理。
- Android17/API37 旧 SDK 环境仍阻断，未执行系统镜像；没有用更低 target/SDK 冒充。
- 不改主线/M0/FEC/TLS/重传/MTU 共用内核；没有启用 Android 全局 ip_forward、清空 iptables、改 SELinux 或刷机。原分支是唯一后续 Android 开发工作分支；旧临时分支仅存历史快照，未删除历史。

**结论：** 本轮独立 netns policy-route 内核能力 PASS、系统 netd 与实际共享业务依然 NOT_RUN。后续若获合适 App→su/真实下游夹具，按独立 SOURCE 逐项验证，不得把此合格范围推广为所有功能权限已验。
