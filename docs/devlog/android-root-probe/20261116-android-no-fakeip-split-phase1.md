# Android Root 中国 IP／域名高效分流与每 App 模式，第一阶段实验（2026-11-16）

本工作仅针对原分支 `experiment/android-temp-root-probe`，**不得改动 M0/Core/Windows 生产语义**。本阶段新增 Android Root 专用政策/私有网络命名空间内核验收/实验 APK 配置 UI。正式 Android WBD Go 控制、Rust 数据面、Tethering offload 与可回滚主网络 Apply 尚未实现，禁止把这份政策证明改写成产品分流 PASS。

## 用户新版 Android 语义（有意不同于原 Windows CN 并集 Direct）

1. Split 分流模式：普通 App 的 **实际最终连接 IPv4** 匹配 CN CIDR 或 LAN/用户明确 Direct 网段则物理直连；否则走 WBD 隧道。**CN 域名即使通过直连 DNS 查询到海外 IPv4，真实业务也必须走隧道**。不能用按解析域名→真实 IP 的全局映射污染共享 CDN。无 FakeIP。
2. Global 全局模式：普通 App 的业务 IP 无论是否 CN 都走 WBD，普通域名即使 `.cn` 也用唯一 tunnel DNS；本机控制/必要恢复例外不等于普通 App 白名单。
3. WBD 服务器的 **引导域名解析始终使用一个 direct DNS 并通过物理网卡**，连接服务器本身也始终在物理出口（root 控制进程、精确绑定 Network/ifindex/source），无论用户选 Split 还是 Global。服务器与任意 App 访问同一个 CDN IP 不自动令后者物理逃逸；DNS直连与隧道目的即使相同也须按自有查询purpose区分。
4. Split 模式下 CN 域名（此实验预装 `.cn` suffix、另支持自定义 exact/suffix）用唯一 direct DNS，其余普通域名唯一 tunnel DNS；无 DNS 主备竞速、系统 DNS 兜底或跨方向回退。普通 DNS 未被自有入口捕获前**不能声称这些DNS策略已部署**，Android 私有 DNS/DoH/DoT、直接IP和QUIC加密 DNS 无法被普通QNAME分流检测。CNAME链不能把询问用途换向；同一域名回答的实际 A 地址决定业务出口。
5. 可选择默认 mode 且对明确安装的 App 包名/UID 单独覆盖 `split` 或 `global`；编译为一个 UID→模式快映射及小量 UID 范围规则，不从每个数据包读取 PackageManager；Android App 重装/多用户/共享 UID 时须重校验，冲突直接拒绝。不将下游 Wi-Fi/USB 客户端误判为本机 App UID（tether 用 iif/客户地址另做物理实验）。

## Android 低开销路线及明确边界

- 分流数据面优先让 Linux 内核 FIB 做目的 IP 路由：为每个模式建一个 owned 路由表和若干按 UID 选择的策略规则，Split 表缺省 WBD TUN + CN/LAN Direct `throw` 前缀（落回 Android 已有物理 network lookup），Global 表缺省 WBD TUN。CN 清单更新冷路径一次性批量验证/交换，CIDR 合并为排序闭区间，本地策略使用二分 O(log N)，不用逐数据包调用 DNS/Java/Go，不产生逐网站/逐 flow 系统规则。真实 Android netd 的具体规则优先级、fwmark、源地址、IPv6、网络切换与回滚**仍需先只读盘点并验证精确 owned journal，不能复制私有namespace 的表号到主系统。**
- App 发行设置为短时 Root 探针后，初期只是生成经过 Rust `splitvalidate` 校验的配置；不直接调用主命名空间 `ip rule add`、`iptables` 或持久更改 DNS。真实 UID0 探针 `splitgate` 只有在 CLONE_NEWNET 成功、名字不同且 IPv4 主FIB完全空时才建立两个非持久 TUN、模拟物理主路由、UID10501(split)、UID10502(global)、Split CN/LAN throw、Global default，以及 root UID0 控制直连；验证 `ip route get` 10 个判例，Fd关后接口应消失。旧 `routegate`/`tethergate` 不回归修改。
- `android_split.rs` 的 `Ranges` 冷编译合并排序、二分；域名 exact/suffix 哈希索引且查询仅按标签候选 O(标签数)。不扫描DATA字符串、无 FakeIP、不修改原 Windows `v4_client_split`，历史 FakeIP 规则与产品完全隔离。Root 只读 `splitpolicy` 包含 CN域名解析到海外A业务应走隧道等15+纯逻辑正负例、模式热更时活跃连接固定决策。
- APP 内设置可录入一个 direct DNS IPv4 (默认223.5.5.5)、一个 tunnel DNS IPv4 (默认1.1.1.1)、custom CN suffix/exact、额外CN IP CIDR、已安装包名/UID的 mode 覆盖，并将配置在同目录原子写入 `wbd-split-settings.json`。Root校验成功显示 **配置语义 PASS／尚未安装系统网络**，不伪装实际VPN连接。来源来自当日 APK 包内固定 APNIC CN delegated IPv4 allocations；这是 **CN 注册分配前缀快照，不是权威地理位置数据库**；非 `.cn` 中国域名还需要有效完整可用的离线 geosite 清单和属性/regex 完整支持。本阶段拒绝不支持 keyword/regex，不偷偷降级规则。

## 安全与验收矩阵

| 验收 | 范围 |
|---|---|
| source-locked ARM64/x86_64 build | Java target37 + Rust Bionic 两ABI、实际APK含固定CN分配规则及源哈希；不得丢旧KSU测试 |
| real KSU AVD App→Root UI | 普通 App UID在实际KSU环境调用原生 `splitpolicy` 与私有netns `splitgate`，检验真实 UID policy-route `ip route get` 正负例、主路由原值byte-equal，双ABI ARM64交叉编译 |
| user app mode config | 用户选择、App包名→UID校验、重复UID冲突拒绝、手动保存原子性和 `splitvalidate` native readback；但主网 Apply NOT_RUN |
| physical phone | 验证真实DNS UDP/TCP53、PrivateDNS控制/限制、root socket `SO_BINDTODEVICE`/`SO_MARK`与netd fwmark、MTU1400/CLAT、WBD TLS/TUN、真实热点USB/ebpf offload；仍 NOT_RUN |
| recovery | 生产主网络 Apply 前需 durable owned journal、重进App手动一键恢复；此阶段没有任何主namespace长留对象 |

## 相对 Windows 源设计的刻意差异

原 `docs/architecture/CLIENT_SPLIT_DNS_CONTRACT.md` 中 `bypass-lan-cn` 的中国域名→海外地址仍Direct依赖选择性 FakeIP；Android此阶段采用“查询DNS按域名、业务出口按真实IP”的明确新版用户要求，绝不从 Windows core 复制 FakeIP。Windows split 模式 `all`、`bypass-lan`、`bypass-lan-cn` 保持原产品不变。Android UI 仅 Split/Global，默认 Split，未来可单独细化LAN模式。

### 依赖与来源

- Android OS UID路由：<https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/heads/main/service/src/com/android/server/ConnectivityService.java>
- Android Tethering BPF/offload：<https://source.android.com/docs/core/ota/modular-system/tethering>；<https://source.android.com/docs/core/data/tethering-offload>
- CN IPv4 来源: `https://ftp.apnic.net/stats/apnic/delegated-apnic-20261116`（生成 provenance 内 SHA256/记录/前缀数）。若源不可获得则构建失败而不是 silently 用样本地址。

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Android no-FakeIP split/global per-UID policy, cold CN CIDRs and DNS QNAME purpose, self-contained mode UI, pinned APNIC snapshot and real separate-netns kernel UID gate; production WBD and physical tether remain NOT_RUN."}
```
