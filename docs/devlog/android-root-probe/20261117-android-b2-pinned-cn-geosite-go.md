# B2 Android Root 正式 Go CN Geosite：固定8503条真规则完整类型+真实DNS线报文（2026-11-17）

施工分支 `experiment/android-temp-root-probe`；基线SOURCE `9772e0c16278a4bb5e24fbe029e6b313e19d2d74`。仅软件源码/Actions，PR #36 Draft；不改main/M0/原Linux Windows协议；不碰实体KernelSU、不购买云资源。

## 从已验证真实源恢复而不另造简化列表

- 直接复用历史 `experiments/android-root-probe/ci/cn-geosite-snapshot.py`，它读取固定MIT上游 `v2fly/domain-list-community@41504eae2a11f305fe88cfc605cf6c105a80bf5a` 的ZIP，递归展开`include`、`@must`/`@-ban`及`&affiliation`，保持独立 `domain/full/keyword/regexp` 四类型。历史Android x86 KSU诊断Action43986417528真实验证`8503`条，SHA256 `45496d28e7a90472274fdf6c23afd43a0e478f9127dea241b628ca730863b1d6`，其中domain 8431/full 69/regexp 3/keyword 0；**这是域名QNAME分类，不是CN IPv4地理地址或真实Android P3联机证据**。
- 新正式原Go `r0/go_overlay/internal/v4productcli/dnsnative/cn_rules.go`：严格绑定完整TXT SHA256、规则总数及每类型数量；要求有序、不重复/缺项、域名标签有效，限6MB、regexp最多2048及Go RE2编译，失败立即拒绝而非把full/regexp降级为后缀。通过`NewPinnedCNResolver`在B1原UDP/TCP真DNS组件上按**原始DNS QNAME**只决定CN物理/国外隧道上游，CNAME解析后的真实IP不反推域名策略，不生成FakeIP。
- 对B1额外加硬门：`New(dial,nil,cnSplit=true)`现在拒绝启动，防止因配置缺CN matcher悄悄变成“所有CN都问国外隧道DNS”；`cnSplit=false`仍可刻意走单个隧道DNS上游。B1固定`223.5.5.5`/ `1.1.1.1`不变，UDP TC只允许同上游同Path TCP，出错不会跨方向回退。
- 独立B2 Actions Job通过固定 HTTPS GitHub codeload ZIP、原仓库importer、TXT SHA256和MIT License、数量来源核对；再把真8503条数据直接喂给原Go matcher，在真实host UDP/TCP DNS loopback应答上验`www.baidu.com`等CN与海外域名、bootstrap和TC保同路，另测坏SHA/截断/超限/类型语义及标签边界。Rust Go原M3/ARM64 source-lock/签名APK/Linux oracle继续回归；Go B2包被原native装配通道复制并对Android ARM64 Go test ELF交叉编译。
- B2规则文本及MIT LICENSE目前作为**独立CI artifact**生成，不是设备已安装APK内资源。未实现正式Android物理NetworkHandle→绑定DNS TCP/UDP socket、原Go CLI调用`NewPinnedCNResolver`、M4内层TUN DNS捕获/回注及Android系统Resolver/PrivateDNS，任何B2 Host成功都不升级为`ANDROID_SYSTEM_DNS_PASS`。

## 分层状态

新SOURCE尚未跑Actions，严禁把源代码存在写成规则导入/类型匹配PASS。此前B1 SOURCE `8534a91` Action44069144804 **6/6 PASS**仅证明host loopback的普通DNS线协议与同源Native/APK/Linux oracle；正式Android16 ARM64 P2/P3依旧缺可访问KVM而`ENV_BLOCKED/NOT_RUN`，实体P5最后另授权。若固定源下载/导入失败，保留失败日志，不换未经固定的新版本、不使用测试假数据冒充8503条。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B2复用固定v2fly CN geosite8503全类型SHA规则、原Go CNRules真实匹配/Host DNS socket与不可用配置fail-closed；Android实际DNS出口和App/P3仍NOT_CONNECTED。"}
```

## 首轮同源 FAIL：真实规则不保证任意 `.cn` 命中

[Action 44072465559](https://github.com/lly8666/wbd-next/actions/runs/44072465559) SOURCE `92c4be735f5f582137f001d9cc14a315f90b03cc`：固定上游Zip成功导入，`ANDROID_B2_PINNED_CN_GEOSITE_IMPORT_8503_PASS`（SHA256、8503及各类型数量均正确），原Go matcher严格类型语义和真UDP/TCP CN/隧道/TC测试可运行；B2单测`TestPinnedCNGeosite8503FullTypedSnapshotAndNoSilentFallback`期望`foo.example.cn`为真CN而失败。真实固定8503条Geosite**未保证所有`.cn`后缀必命中**，不能因为旧KSU私有netns合成`.cn`样例就自行加未源锁的泛域规则。修复把此域名改为**明确负例**，正例只验证该固定规则真实含有的`www.baidu.com`、`www.qq.com`及`baidu.com`。旧失败保留，修复SOURCE需要新Actions6+ Job全验，不能修改旧Action结论。
