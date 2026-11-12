# PLAN029｜中国IP＋域名、单DNS与低开销Direct架构修订

用户2026-11-12明确授权方案/提示词修改。审阅main `8605115cbe3f51e1b383a664cf3d8283f049542e`、029新增Wintun后分流、原Go Direct TCP/UDP与当前bootstrap代码。此次**只改设计/任务入口/功能登记，不改产品、不派发网络测试、不覆盖M0产品checkpoint或伪造PASS**。

结论：CN模式按IP＋域名并集直连，direct/tunnel各单endpoint，取消所有备用与跨方向回退；服务器bootstrap复用direct。仅对已解析成功的CN域名采用本地映射，防止共享CDN真实IP反查污染；非CN普通Tunnel不经过TCP代理栈。Direct TCP首选Rust本地Windows内核接入＋物理socket，先实际Windows小门验证，不盲目扩写；Direct UDP按原物理绑定/回包语义移入Rust。禁止回接Go gVisor热泵/海量route/WFP。普通代理模式语义和原硬门保持。

详细参数、资源边界、兼容限制、DNSSEC/加密DNS、CNAME/hints、TTL/映射重启、开发顺序、D1-D5/P1-P2均在 [CLIENT_SPLIT_DNS_CONTRACT](../../architecture/CLIENT_SPLIT_DNS_CONTRACT.md)，029与长期提示仅引用，不制造两套规范。同步registry目标、cursor next_action与功能卡；原在途Actions、SOURCE及测试状态保留，新增功能为NOT_RUN。

理论：200Mbps/1400B约1.79万pps，500Mbps约4.46万pps；CIDR约6209条二分约13次比较，flow命中常数查找，域名匹配只随DNS查询量。主要新增CPU风险是Direct TCP双内核腿/复制，不能承诺无开销；同VM真实出口A/B和系统CPU都需测量。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6","gui-config-feedback"],"reason":"User-approved PLAN029 design supersedes backup DNS and CN-IP-only routing with CN IP/domain union, one resolver per egress and low-overhead Rust direct path; implementation and network qualification remain NOT_RUN."}
```

验证：提交前运行现有governance/feature catalog检查、JSON与文档链接/矛盾检查；本次不运行产品Actions作为功能验收。原H166x实际结果由在职M0继续收集。
