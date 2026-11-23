# B58｜Root Android 一批完成多 App 规模、直连 CIDR 和低启动开销

**基线**：B57 `d677a8152e4c30415fe02f2783ae22f114d4574b`，[Dual64 #45202808785](https://github.com/lly8666/wbd-next/actions/runs/45202808785) 11 SUCCESS / 4 SKIPPED、[治理 #45202808814](https://github.com/lly8666/wbd-next/actions/runs/45202808814) SUCCESS；双ABI原Go/Rust/签名ARM64 APK、原Linux两个Oracle和DNS/M3 Host通过，D2真实Android↔Linux App TCP/UDP/Stop、全App和CPU仍NOT_PROVEN。

**本批三项面向实际用户的原生功能**：
1. **手选App扩容**：`SelectedAppGroup.MAX_UIDS=16`、`MAX_PACKAGES=32`；原已安装包的package/UID冷快照、UI勾选/筛选、SAF与四配置槽、`RootConnectionSettings` 序列化、Service的原uid组、`OriginalGoCommandArgs`、Go `--android-route-uids` 冷解析、rootjournal Group 16个真实`uidrange` 同批统一。共享UID不重复建路由，旧单UID/8UID/16包仍兼容；不动Go TLS/AEAD、原服务端和Rust M4。
2. **IPv4分流扩容**：原`RootDirectIPv4`及Go`rootjournal.ParseDirectCIDRs`同批从4条到16条，仍是私有WBD table19842的真实`throw CIDR`，用户可组合更多局域网/公司网段，一次性随配置槽/SAF迁移，原物理Network/owner不变。不接管系统DNS、netd、IPv6或默认系统路由。
3. **冷启动性能**：原单App/多App/20-user全App安装每加一个UID/直连前缀都调用`ip route show`+`ip rule show`读取完整FIB，次数随规则增长。现在保留`ip add`每次真实内核结果，原journal/精确owned Stop和失败清理；**所有直连前缀先装完，完整读回一次再允许第一个UID；所有UID装完，再完整读回一次才宣布Ready**。整表读取次数不再依赖60~180条all-app uidrange数量，减少进程创建和重复解析。没有新批量shell解释器、外部网络动作或Android数据面线程。启动时间需实体设备A/B测量，不能凭Host模型宣称实测速率。
4. **同SOURCE测试**：原Go fake ip kernel的16个UID/16条CIDR、20用户全App安装及最终Stop、整表查询次数界；原Go CLI 16 UID解析；正式Java UID组/32包筛选、原生产argv、16CIDR、32包配置回读，原签名APK源门复用现有Dual64。Go test由原 source-lock build及 Linux Oracle内既有命令执行，不重复dispatch。Host软件通过不等于Android真实路由功能已通过。

**剩余大类**：Android物理TCP53完整会话、netd系统DNS、IPv6、热点/USB转发、实机Android↔Linux E2E、真实全App内核/性能仍为NOT_RUN/NOT_PROVEN。工作仅在`experiment/android-temp-root-probe`、Draft PR #36；main/M0/个人实体手机/服务器不操作。本批没有新增防御安全机制，完全保留生产FakeTCP TLS/租约/原Rust数据面。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B58批量扩容16 UID/32真实包、16直连IPv4 CIDR并同步原Java/Go/rootjournal三类UID route；减少全App每条UID全表读回为直连前/最后一次完整内核读回，原journal/Stop不变，无逐包成本。"}
```
