# M0｜PLAN029B 固定接续提示词

在 `lly8666/wbd-next/main` 接续029B。默认上轮中断：先读START_HERE/AGENTS、最新M0 cursor与在途Action，补遗漏留痕；不重派、不覆盖活动作者。先安全收完当前029已冻结优化批次，再完成[PLAN029B](../decisions/M0-PLAN029B-OPTIONAL-SPLIT-FAKEIP-IPV6-20261116.md)，纳入029收口、030之前；不要等029先全部关闭。计划与旧029三项语义冲突以029B为准，其他成熟修复保留。

一次写齐相关冷配置/ABI/caller、Rust实际路径、GUI/help/参数/功能卡和夹具，再冻结源码测试。三项定案：

1. `split-enable=false`或route-mode=all不创建业务分流规则、Direct actor/socket表/专属任务、FakeIP/writer；普通DATA直达原隧道。**公共DNS、bootstrap、IPv6已有检查、已启用startup-padding独立保留**，不能退回旧V2丢功能；DNS TCP确需的最小listener不等于业务Direct实例。off不是停整个Rust数据面。
2. 一个 `cn-domain-direct` bool（若最新main已有同义canonical键就复用），界面“高级CN域名分流（FakeIP）”；新配置默认false，旧配置缺键按旧语义迁移。false仍按CN域名选择直连DNS，但回复真实IP、业务按IP选出口：CN→海外走Tunnel；true复用现有FakeIP让CN→海外Direct。禁止共享真实IP反查/强制Direct集合。非CN共享海外IP仍Tunnel。重连生效，不做双表热迁移；旧FakeIP不外发。
3. 所有受管UDP/TCP DNS的AAAA在共同入口立即NOERROR/NODATA、不上游查询；A正常，不污染A缓存。普通CN/非CN不全封HTTPS/SVCB，高级CN沿原映射约束。Windows保留IPv6接管/绑定，复用首字节检查丢弃后继续公平读包；**不解绑、不新增IPv6模块/旧WFP**。Linux保留自有TUN的disable_ipv6=1，不改宿主全局。不得把无路由/未发包当IPv6已拦截。

先回读触及的实际调用链及最近FIN/就绪/公平性修复再改，不重构TCP栈、FEC/repair/外层wire，不加Go逐包回调。一个owner；必要内存按需有界，真实首到/p99/低CPU优先。规则校验在冷路径，停用模块不要求文件/资源就绪；长度、租约、generation、原密文、MTU与owned Stop保留。

按029B B0–B5做组件批量＋最少真实Windows代表：模式有效值、CN海外/共享CDN、DNS两出口、旧配置/旧缓存、IPv6真实发包混IPv4、Stop及Game入口。Linux/ARM只验受影响的现有路径。复用现有签名夹具与SOURCE/hash产物；一Action一场景，配对同VM顺序，场景间独立Actions可并行。性能看CPU/实际交付GiB、host CPU、RSS/唤醒和小TCP/UDP p99，不能跨不同出口/不同VM算CPU优化。先10Mbps容量内，必要才追加已有大流保护，不重刷弱网全矩阵；容量满停更重同族。资源真关闭且无实质退化即可，不强求百分比、不刷seed。

自主解决包内普通问题，完整实现后集中验收；两次同失败无新信息就缩小首个异常，不绕到防御框架。短devlog、原功能卡、必要evidence/cursor记录真实SOURCE与FAIL/NOT_RUN。029B退出后回029剩余任务；两者已完成时重复提示只说明已完成和残余边界，不自创新工作。
