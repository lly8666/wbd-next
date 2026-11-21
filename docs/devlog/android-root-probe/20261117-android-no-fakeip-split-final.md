# Android Root 无 FakeIP CN 分流／全局／每 App 配置 — 2026-11-17 同源验证收口

**原实验分支** `experiment/android-temp-root-probe`；功能源码 SOURCE `75b5596e0bfdddce0b340a901f996bcacf70493f`；[Android16 KSU3.3.1 AVD Action #43909181856](https://github.com/lly8666/wbd-next/actions/runs/43909181856) **SUCCESS**，job `133446091413`。结果只适用于该 SOURCE、Android16/API36 x86_64 已 KernelSU Root 的模拟器；本功能目前属于 `POLICY_AND_PRIVATE_KERNEL_UI_PASS`，**不属于正式 Android VPN / DNS / 热点已接线**。

## 需要的产品语义（Android 用户要求，刻意不同于 Windows FakeIP 域名并集规则）

| 客户端 | DNS 请求 | 实际业务连接 |
|---|---|---|
| Split，查询中国域名（现阶段 `.cn`＋自定义 exact/suffix） | 单 direct DNS（默认 `223.5.5.5`），物理出口 | 解析出中国 IPv4/LAN/explicit direct IPv4→物理；**解析出海外IPv4→WBD 隧道**，不准因QNAME是中国域名而直连海外IP |
| Split，查询普通非CN域名 | 单 tunnel DNS（默认 `1.1.1.1`） | 实际中国IPv4/LAN/explicit direct→物理，其余→隧道 |
| Global App | 普通域名走 tunnel DNS | 普通业务 IPv4 统一入 WBD，不因目的为CN DNS或WBD服务器IP逃逸 |
| WBD 根控制进程的 ServerBootstrap DNS | **所有模式强制唯一 direct DNS + 物理直连** | 服务器控制连接始终物理出口，避免递归；不能将服务器IP加入普通App无条件白名单 |

本实现不提供、不生成、不使用 FakeIP；DNS域名只决定其**自有查询出口**，普通业务在首个流量决策时以真实A结果最终目的IP与UID模式为准；既有flow固定决定避免热更新中途迁移，QNAME不反查真实IP导致共享CDN污染。直连/隧道DNS不互相failover。

## 真 CI 做了什么

- **两 ABI 构建**：Android Bionic x86_64 与 arm64-v8a 交叉编译/16KiB PT_LOAD对齐检查，targetSdk37 APK自包含对应 `libwbdprobe.so`，Android普通App→已授权KernelSU `su` UID0，在 APK 安装的 nativeLibraryDir 执行，无外置二进制预置到 `/data/local/tmp`。
- **18/18 规则正负例**：CN/海外/Global per UID目的IP、CN域名DNS直连、CN域名海外A业务仍走Tunnel、Global CN域名Tunnel DNS、WBD ServerBootstrap在两个模式始终Direct、内部自有DNS用途优先于resolver IP、suffix边界、无FakeIP、空CN数据fail-closed、已存在流量pin不会因规则模式更新中途切路。
- **10/10 实际内核路由检查**：Root线程先执行 `CLONE_NEWNET`，确认 namespace 变化及 `/proc/net/route` 新namespace主FIB为空后，建2个临时TUN（模拟物理与Tunnel）；内核 `uidrange` 选择 Split/Global 表、Split 中 `throw` CN/LAN、未匹配海外IP走Tunnel；`ip -4 route get <dst> uid <uid>` 精确核实10组，附带 UID0控制socket走模拟物理出口，以及普通App访问同一WBD服务器IP不凭空直连；退出不改真实 Android netd 主网络。
- **真 App UI/保存/Root 读回**：使用**同一模拟器先前UIAutomator真实快照的按钮边界**，从运行中的 App 真正 `adb shell input tap` 打开 `SplitSettingsActivity`；页面的实际 `getGlobalVisibleRect` 每次滚动、增加App行及布局变化时更新，依次输入 `uid:10502`、选择独立 `global` 覆盖、点击添加与保存，必须观察 `add_clicked` 和 `save_clicked/save_started` 等真实 Activity 事件。随后通过 App私有文件确认 `wbd-split-settings.json`，并由普通 App 调 KSU Root原生 `splitvalidate` 读取并写 `wbd-split-validation.json`。两者都存在才 PASS。这里的 10502 是用于策略保存的**模拟 UID**，不是已安装第三方真实App出网实测。
- **CN IPv4离线快照**：固定 `delegated-apnic-20261116`，其输入文件 SHA256 `f5bc4f8969b76afce7622820711e446db09da71c981cdf1f6cf49c3573fbc557`；8798条 `CN` `allocated/assigned` 记录，经排序CIDR collapse为5500前缀，设备原生Cold `Ranges` 合并成 **4119** 区间。原CIDR文本 SHA256 `34d4bed7c72789ed6bd6ff5372e4a222cda1cdc47d5b553615486cb61f8c9959`。这代表**APNIC中国注册分配前缀**，不保证完整或精确 IP 地理定位；不能以此声称 Windows GeoIP/GeoSite完整覆盖。
- **旧功能未回归损坏**：App→KernelSU/IPv4 TUN/raw、IPv6隔离TUN、SO_MARK route、实际DNS/HTTP/TLS1.3原有代表测试、3个合成 Wi-Fi/USB NAT conntrack正反流、一键恢复精确rule（`RESTORED/ALREADY_CLEAN`）在此 SOURCE 再次 PASS；主 Android `ip -4 rule` 和 `ip -4 route show table all` 前后快照相等。

## 机器证据及下载

- CI ZIP artifact [14248485146](https://github.com/lly8666/wbd-next/actions/runs/43909181856/artifacts/14248485146)，下载后独立 SHA256 **`1c2ab9e5f85b8a2d88bdcfaca2ae12cce59aef92d5794a898ef005e5926b3827`**。
- 签名 APK ZIP 内 `diag/device-diagnostic.apk`，大小 **1,717,060 bytes**，独立 SHA256 **`7df7800f58b7028171a2547b25ef074e6aadb1adff682cc4beac6d7f19c45a9b`**，与CI `diag/manifest.json` 完全一致；双ABI ELF均作为 `ZIP_STORED` 内置，assets内固定CN CIDR和源码SHA正确。
- 设备机读 `device-diag/summary.json`：`EMBEDDED_APK_DEVICE_DIAGNOSTIC_PASS`、`android_split_policy=PASS`、`android_split_uid_kernel=PASS`、`split_settings_ui=PASS`、`errors=[]`；Native UI输出具体 `compiled_cn_ipv4_intervals=4119`、`dns_direct=223.5.5.5`、`dns_tunnel=1.1.1.1`、`per_app_modes=[{uid:10502,mode:global}]`、`server_bootstrap_dns=DIRECT_IN_ALL_MODES`、`fakeip=false`、`installed=false`。

## 保留每个第一失败，不把历史 FAIL 改 PASS

| SOURCE / Actions | 原始错误 | 当前处理 |
|---|---|---|
| `3ca59ead...` [43897451393](https://github.com/lly8666/wbd-next/actions/runs/43897451393) | Java `v` 局部变量重复，APK编译FAIL | 后续仅改为 `cidr`，历史FAIL保留 |
| `89355770...` [43897727775](https://github.com/lly8666/wbd-next/actions/runs/43897727775) | 第二个UIAutomator进程 `137` 杀掉 | 后续使用首次真实按钮快照 |
| `dcf3ceec...` [43898866446](https://github.com/lly8666/wbd-next/actions/runs/43898866446) | UIAutomator有限重试仍连续无XML | 改成同启动周期真实UI缓存＋实际控件布局座标 |
| `1cc066e7...` [43900940103](https://github.com/lly8666/wbd-next/actions/runs/43900940103) | 打开设置/点击，但未拿到Root原生校验两份JSON | `appsView` Layout高度改变导致 Save 坐标可能陈旧；新增真实Add/Save事件、重排后坐标读回与失败取证 |
| **`75b5596e...` [43909181856](https://github.com/lly8666/wbd-next/actions/runs/43909181856)** | **完整PASS** | 真实触摸+持久化+Root原生JSON及此前网络全回归PASS |

## 尚不能对用户虚报完成的部分

1. **未把真正 WBD 原 Go鉴权/TLS 与Rust DATA/TUN数据面、Android网络生命周期和通知接进App**；未对主Android netd安全 Apply由UID路由表/路由优先级，也没有生产 owned journal + 重新启动一键恢复；此处的路由表236/237仅私有netns专用，不可照搬到物理机。
2. **没有正式 Android DNS捕获/UDP+TCP53 resolver worker**，不能声称真的把某CN查询送到223.5.5.5物理/某海外查询送到1.1.1.1隧道；这次验证的是策略方向判定而非实际生产流量。系统PrivateDNS/应用DoH/DoT/DoQ会限制按QNAME识别。
3. **CN域名列表目前只有 `.cn` 后缀 + 用户在UI添加的 exact/suffix**。Windows `geolocation-cn` 还含大量 `.com/.net` 与 `include` / attribute / keyword / regexp 语义；未把完整有来源固定的 GeoSite 数据导入 Android。未知规则不会默默当suffix；生产上需要正确解析它们，或者诚实呈现当前仅部分覆盖。
4. **IPv6真实目的流量策略、IPv6-only蜂窝/CLAT、WBD服务器物理 socket绑定/Server IP轮换、Android UID多用户/共享UID、热点USB真实下游和eBPF/hardware offload绕流** 尚未实机验收。`ARM64` 原生ELF已打包，**这版新APK还没在 ARM64 物理手机运行**。
5. 当前「保存并经Root验证策略」明确报告 `installed=false`，**只保存/验证，不下发主网络规则，不会切断手机上网**。本签名为CI临时密钥，安装前如有旧相同包名不同签名需卸载旧包（旧报告会随卸载删除）。

后续优先顺序：完整离线 CN geosite快照/匹配 → 实际直连/隧道双DNS worker → 真实Android WBD原鉴权/数据面接线 → 安全owned netd Apply+手动恢复 → 实体App及Wi-Fi/USB测试。所有负测以本轮报告为基线，不把 `POLICY_AND_PRIVATE_KERNEL_UI_PASS` 等同 `PRODUCT_VPN_PASS`。

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Certify source-locked Android16 KSU no-FakeIP split/global 18 pure tests, 10 real private UID kernel routes and actual App save→root native config readback, preserving physical DNS/WBD/tether NOT_RUN."}
```
