# M0｜PLAN029长期接续提示词

你在 `lly8666/wbd-next/main` 接续已授权PLAN029。先刷新main，读START_HERE/AGENTS、registry/M0 cursor、[029计划](../decisions/M0-PLAN029-CLIENT-DNS-PADDING-20261102.md)与[分流/DNS施工契约](../architecture/CLIENT_SPLIT_DNS_CONTRACT.md)，只补上次checkpoint后的必要代码/日志/Actions。先收已有结果，补中断记录，不重复派发、不覆盖在途改动。028已按H1657限定收口，不恢复旧全矩阵；030未自动开工。

本轮目标：**Wintun捕获后中国IP＋域名并集直连，其余走原Rust隧道；直连/隧道各一个可配置DNS，无备用；服务器域名接管后仍可解析；配置/GUI真实生效；有限新流填充不拖慢业务。** 完成全部029出口再交付，单Action绿或某一子项完成不等于没任务。

固定语义：
1. CN模式中LAN/显式direct4、中国IP、中国域名均直连。CN域名解析到海外也直连；非CN域名解析到CN IP，查询走隧道DNS但业务按CN IP直连。另两个route-mode保持原政策，不强开中国规则。
2. `dns.direct=223.5.5.5`、`dns.tunnel=1.1.1.1`各一个endpoint；所有模式取消DNS主备/NIC多resolver轮询/跨方向回退。UDP→TCP只能同endpoint。服务器bootstrap复用直连DNS（all模式也如此），不新增第三地址。用户显式更改值须真正生效，旧列表按契约迁移。
3. 稀疏DNS查询才查域名规则：只为匹配CN且解析成功的域名提供本地FakeIP，普通非CN答复保留真实IP，不能用共享真实IP反查表污染CDN。FakeIP不出本机，CNAME/hints/TTL/重启/容量边界按契约实现；加密DNS不可见如实说明，不做TLS解密或猜SNI。
4. 原Rust Wintun ingress只一处分类；IP合并区间＋flow缓存，域名只读trie；OS仍少量owned捕获route/例外，禁止数千route/WFP/NRPT，禁止Go稳态逐包泵。普通Tunnel TCP不终止、不套代理栈，FEC/Game/record不重构。
5. Direct UDP用物理绑定原生socket；Direct TCP优先本机Windows内核接入＋Rust异步物理socket中继，先跑一个真实签名Windows能力门验证SYN/逆回包/Stop，再集成；内核接入确实不成立才用契约限定的Direct-only成熟Rust栈备选。不要把IP/TCP包直接塞普通socket冒充转发；不要同时养两条后端。
6. DNS resolver用途先于IP分类，隧道DNS永不因目标CN IP改走物理；普通53被接管后按QNAME处理。DNS异步、有界、缓存合并，不阻塞Wintun。纯Direct业务不续隧道payload idle，Tunnel DNS可以唤醒；lane轮换不销毁Direct流。

开发顺序：先核最新H166x已实现代码和原旧`userspace_tcp_direct_windows.go`/`direct_udp_windows.go`，明确实际Rust接口；做最小真实Windows Direct TCP能力门；完整写齐policy/DNS/Direct/配置迁移/装配/GUI及对应夹具，再按D1–D5/P1–P2测。不要每helper跑Action，也不要堆整包未验证代码后才发现最底层Windows不能接收。bootstrap既有Npcap小包/CNAME修复复用，取消其旧备用链；startup-padding按029原有预算独立接，Direct不填，off无新增跟踪成本。

强制性能思维：查询/新flow做决策，普通DATA只读缓存；只读规则共享、缓冲按需池化、有界内存与到期轮，无每flow线程/全表频扫/逐包全局锁。用PPS、flow数、复制次数和实际byte预算估算；Direct内核CPU也算成本，Go进程包含Rust库不可按进程名归因。不能声称“用了Rust就更快”。

测试：一Action一网络场景/测量job，独立场景不同Action可并行，同VM A/B顺序；SOURCE/manifest/hash构建一次复用。先可控两DNS与真假CN/CDN共享IP出口，再生命周期/GUI/路由规模，再纯Tunnel性能保护、Direct与混合容量。Normal和Game4作必要接线代表，不重刷028全矩阵。CPU/首到/p99/最长空洞/RSS/出口都要看，宿主容量满停止加码；单worker/锁瓶颈仍是产品问题。失败不刷seed，找到首个异常点，定向复习旧逻辑再修；无稳定收益不继续抠小数点。

不变硬门：标准TLS前无私有前导、认证/账户与generation隔离、完整性、固定密文重传、统一MTU、owned Stop。默认外层1460（不含L2），内层Rust派生且GUI只读，不因规则/padding改变配置。多网卡极端/多代理共存不扩展，本轮一台机器一个代理实例。

每批更新现有devlog/功能卡/必要evidence和cursor，明确设计/已实现/已实际验收不同状态，保留历史失败。当前卡片可能过时，代码/真实SOURCE证据优先。自主大胆细心完成授权范围，不造防御框架，不钻牛角尖；029完整退出后停止并给交付报告，定时重复提示只核新事实，不自创新任务。

**最新用户决定：不接入老项目WFP体系。** 按契约§3A解除旧guard、固定五stage、Ready/Stop必须WFP完整的依赖，连带真实入口/装配/receipt/GUI一起改；不能用no-op guard伪造Applied。只保留精确owned旧WFP对象的一次性卸除迁移，不重新Arm，不动系统/第三方防火墙。DNS用本地单入口＋owned系统设置＋实际Wintun流量，不承诺拦截硬编码on-link/绑定物理/加密DNS；IPv6实际阻断另按原生设置/捕获验证，未覆盖如实报告。保留租约/generation/包长/原密文/owned清理正确性。Wintun RX借用不能跨异步等待，TX先备好数据再Allocate/立即提交，避免占ring等DNS造成跨流HOL。测试无guard仍正常起网/分流/退出，迁移不误删、DNS等待不堵其他flow，不开攻击矩阵。
