# Android16 KSU：完整 CN geosite + 分流/全局双 DNS 内核 UDP/53 实测收敛（2026-11-17）

**原分支：** `experiment/android-temp-root-probe`。**已实测源码：** `09a6a7e5f8aef5c3b38abb262655561ca89e5f9a`；[KSU Action 43986417528](https://github.com/lly8666/wbd-next/actions/runs/43986417528) **SUCCESS**；[KSU ZIP工件14286390166](https://github.com/lly8666/wbd-next/actions/runs/43986417528/artifacts/14286390166)，完整ZIP独立 SHA256：`5acfa2fcaf58d3c43bc96b6c3375fb555685bd87ca9757c486d605838bfd9009`。本日志对应 [结构化实测矩阵](20261117-android-cn-geosite-dns6-kernel-matrix.json)。KSU原生执行的完整 App配置与报告在工件 `device-diag/split-settings.json`、`device-diag/split-validation.json`、`device-diag/cn-geosite-quick-summary.json`。

## 真实完成的闭环

1. **CN 域名库非示例列表。** 固定 `v2fly/domain-list-community` upstream commit `41504eae2a11f305fe88cfc605cf6c105a80bf5a`，遍历处理 include递归、属性必须/排除过滤、affiliation，保持 `domain/full/keyword/regexp` 四种匹配类型而非无差别后缀。预装 8,503 条独立域名规则（8,431 domain / 69 full / 3 regexp / 0 keyword；当前固定上游确实没有关键词），文本 SHA256 `45496d28e7a90472274fdf6c23afd43a0e478f9127dea241b628ca730863b1d6`。原MIT LICENSE随签名APK装入；不允许Android App 静默联网更新。APNIC CN IP 5,500 CIDR 编译为 4,119个区间；CN域名库与真实IPv4地址列表承担完全不同职责。
2. **从可见按钮到 Root 重新加载。** 在 Android16/API36 的 targetSdk37 普通 App 中，CI先用真实系统触摸进入Split Settings，再点顶部「一键验证 CN 域名及双DNS内核收发（不启用VPN）」按钮。它通过正常的 `saveButton.performClick()` 执行当前App原子文件保存/已捆绑资产 SHA 复查，继而用真实 KernelSU 授权 `su -c <APK nativeLibraryDir>/libwbdprobe.so splitvalidate <APP_PRIVATE_JSON>` 让原生程序独立验证保存在私有目录的规则快照和配置。证据 `APP_ONSCREEN_ROOT_CN_GEOSITE_DNS_PRIVATE_KERNEL_PASS`，不是 CI 推入JSON/伪造回调或直接ADB发起native测试。
3. **真的走了内核 TUN 与 UDP/53 往返，但只在隔离 namespace 内。** 原生 UID0 先 `CLONE_NEWNET`，核验 namespace 从 `net:[4026531840]` 切换到 `net:[4026533060]`、初始FIB为空；创建两条非持久 TUN 模拟物理出口 `198.51.100.1/30` 和隧道出口 `198.18.253.1/30`。实际从 UDP socket 发送DNS A question到各模拟对端的53端口，逐条从**对应** TUN取到内核发出的原始IPv4 UDP包，原生注入带原始事务ID和 `8.8.8.8` A的回应，最后在原Socket获得且字节级校验整个收到的DNS响应。6/6个测试通过：4个Direct、2个Tunnel；`global_changes=false`、Android宿主 `ip rule` 和所有 `ip route` 在检查前后字节级相同。
4. **无 FakeIP / 分流语义。** CN DNS QNAME 用geosite匹配，普通CN域名在split模式走直连DNS，非CN域名走模拟隧道DNS；同一 `www.baidu.com` 在global模式则走模拟隧道DNS；服务器 bootstrap 在两种模式均始终Direct。DNS返回的**真实**海外A `8.8.8.8` 对业务data的路由决策按实际IP取Tunnel；这只是路由决策校验，不宣称把业务字节发过生产WBD通道。用于同时检验Split/Global的测试UID配置**只驻内存，不写用户配置或主Android网络**。

| 实测真实内核DNS/53 case | QNAME | 预期出口 | TUN发出/注入/Socket收到（字节） |
| --- | --- | --- | --- |
| split_baidu_com_cn_dns_direct | `www.baidu.com` | Direct | 59 / 75 / 47 |
| split_example_net_dns_tunnel | `www.example.net` | Tunnel | 61 / 77 / 49 |
| split_cn_suffix_dns_direct | `foo.example.cn` | Direct | 60 / 76 / 48 |
| split_bootstrap_dns_direct | `wbd-bootstrap.example.net` | Direct | 71 / 87 / 59 |
| global_baidu_com_dns_tunnel | `www.baidu.com` | Tunnel | 59 / 75 / 47 |
| global_bootstrap_dns_direct | `wbd-bootstrap.example.net` | Direct | 71 / 87 / 59 |

## 旧回归与失败透明度

同一SOURCE的 `EMBEDDED_APK_DEVICE_DIAGNOSTIC_PASS`、`APP_UID_TUN_ROUNDTRIP_PASS`、`MAINSTREAM_DNS_TLS_PASS`、`SIGKILL_WATCHDOG_CLEANUP_PASS` 均通过；隔离 `ip route get ... uid` 10/10、IPv6 TUN、SO_MARK/策略路由、2个模拟WiFi下游+1个模拟USB下游的SNAT及conntrack回程均通过。App手动恢复按钮第一次 `RESTORED`，第二次 `ALREADY_CLEAN`，全局规则/路由保持不变。

失败历史原样保留：[Action43951593575](https://github.com/lly8666/wbd-next/actions/runs/43951593575) 旧UI私有见证在Activity `onCreate` 时冻结 `window_focused=false`；[Action43985292694](https://github.com/lly8666/wbd-next/actions/runs/43985292694) 首次成功完成真实点击及Root进入隔离 DNS 检验，但测试误将 `recv_from` 返回数据和整个 4096B 未写满buffer的尾部比较，失败。前者通过 `onWindowFocusChanged` 重新输出真实前台状态修正，后者只对 `response[..got]` 进行A记录尾校验并添加回归用例修正。**仅 Action43986417528 是本阶段同源KSU全PASS证据**。

## 未打通的生产障碍，绝不借模拟结果宣称成功

- 这里两台模拟DNS是私有network namespace里的合成对端，**没有真的联系 `223.5.5.5`、`1.1.1.1`、Android netd 系统DNS、PrivateDNS、真实外网/代理DNS**；真实DNS监听器/业务DNS数据分发与WBD TLS/lease/session/多lane还未接线。
- **真实Wi‑Fi热点、USB共享、Android Tethering eBPF/硬件offload、物理蜂窝/IPv6-only/CLAT、VPN前台任务与Doze** 均 NOT_RUN。模拟2WiFi+1USB通过只说明Linux内核转发/NAT模型可行。
- 当前「一键恢复正常网络」只清理实验性已知路由/UID规则且有AVD防护，尚缺生产级原子owned-journal来恢复真实 netd/NAT/转发参数；Root失效后按钮不能获得权限。
- **DirtyFrag未在未经Root的Android16 ARM64实体系统取得临时Root**；本次是真实KernelSU提供UID0的已Root仿真设备，不可冒充DirtyFrag利用成功。正式WBD Bionic平台适配、独立 App生命周期及实际服务器连接仍NOT_RUN。
- 本SOURCE的一键DNS按钮同源通过，但**每App长表单的文字输入/覆盖保存只在旧SOURCE `75b5596…` [Action43909181856](https://github.com/lly8666/wbd-next/actions/runs/43909181856) 有真实UI positive；本SOURCE的`per_app_text_editor_same_source=NOT_RUN`**，不应合并成同源全回归成功。

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Source-locked Android16 KSU PASS for App visible one-click pinned 8503 CN geosite hash and 6/6 real private-netns dual DNS UDP/53 kernel packet+reply checks; global Android rules unchanged, full production WBD/physical tether/DirtyFrag remain NOT_RUN."}
```
