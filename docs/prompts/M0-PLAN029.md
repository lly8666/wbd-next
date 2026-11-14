# M0｜PLAN029长期接续提示词

你在 `lly8666/wbd-next/main` 接续已授权PLAN029。默认上轮中断：刷新main，读START_HERE/AGENTS、registry/M0 cursor、[029计划](../decisions/M0-PLAN029-CLIENT-DNS-PADDING-20261102.md)与[分流/DNS施工契约](../architecture/CLIENT_SPLIT_DNS_CONTRACT.md)，重点最新§3B、§5、§7。只补checkpoint之后必要代码/日志/Actions；先收在途结果、补中断记录，不重复dispatch、不覆盖其他改动。028限定收口，不恢复旧矩阵；030未开工。

目标：**Wintun后Rust中国IP＋域名并集分流、单DNS、真实Direct/Tunnel TCP/UDP、配置GUI与有限填充，低CPU、低延迟、无跨流HOL。** 全部029出口完成再交付，单Action绿、某个子项完成或诊断暂时受阻不等于没任务。

## 先解决真实堵点，不被旧检查挡住

1. 核最新native失败的首个边界；局部WAL/编译PASS不等于产品联网。H1690 UDP注入无交付/TCP无SYNACK只证明该路径失败，默认防火墙Block不是根因结论。按契约§3B一个Action顺序A原状→B精确owned Defender Allow→C恢复；允许必要放行，禁止全局关防火墙/恢复旧WFP guard。显式Block可能盖过Allow，必要时用有界Pktmon定位首个丢弃点。
2. 诊断最多两轮不同假设，没新信息不刷同类探针。验证共同Wintun回注后，M0可据实现成本与证据选内核TCP或Direct-only smoltcp单后端；未知根因留OPEN，不必永久BLOCKED，也不并养两套。UDP物理socket＋应用回包测试独立进行，不以UDP到本机listener失败否定Direct UDP。OS四阶段、DNS纯逻辑/GUI可独立施工。
3. 去旧guard/固定五stage/测试地址绑定，连同入口/manifest/receipt/Ready/Stop一起修。`assemblyOnly`不能要求先有实网PASS才允许实网执行：真实adapter接好就可运行测试，Applied/Ready依据当次真实状态，绝不伪造。必要Defender规则是少量owned冷资源，非旧自定义WFP体系；Stop/失败回收，只清本项目确定资源。

## 实现固定语义

- CN模式：中国域名、中国IP、LAN/direct4并集Direct；CN域名海外CDN也Direct，非CN域名→CN IP则DNS走Tunnel而业务Direct。其他route-mode原语义不变。选择性FakeIP仅CN成功A答复，不用真实IP反查污染共享CDN；TTL/引用/隔离回收遵契约。不解密DoH、不猜SNI。
- `dns.direct=223.5.5.5`、`dns.tunnel=1.1.1.1`各一个endpoint，无备用/跨方向回退；服务器bootstrap所有模式复用direct，UDP→TCP只同endpoint。DNS用途优先普通IP分类。系统DNS＋被Wintun捕获53按QNAME，无法覆盖的on-link/绑定物理/加密DNS如实说明；IPv6原有政策须真实验证。
- 少量owned捕获路由，Rust单一ingress→flow缓存/区间IP表，域名trie仅DNS查询调用；不加海量route/WFP/NRPT、Go逐包泵。普通Tunnel TCP不终止、不套额外代理栈；FEC/Game/record不重构。
- Direct UDP物理绑定异步socket，Direct TCP按已选后端两腿有界中继，支持回程/半关闭/失败；无每flow线程/全局等待。Wintun RX借用不能跨await，TX备好数据再Allocate并立即提交，不占ring等DNS/connect。
- **资源满分类处理**：Direct4096软水位、16384默认可配置硬上限，按需增长/回收；硬满只拒绝新Direct，不能因共享FlowPin满丢新Tunnel。TCP buffer压力仅暂停相关flow读取，UDP局部丢弃；DNS缓存TTL/LRU满仍可查，事务满及时失败，FakeIP无可回收槽才拒绝新合成。64MiB是共享分配上限，不是排队目标；记录队列年龄，不能存几秒数据再称不卡顿。复用到期轮/池/公平轮转，无全表频扫/逐包OS检查/大窗口预分配。
- 分流启停下次连接生效，不开发热迁移。规则更新不迁移活动flow；纯Direct不续Tunnel payload idle，Tunnel DNS可唤醒，lane轮换不销毁Direct。startup-padding按029预算，仅Tunnel；off不新增跟踪，业务不等待填充。

## 写齐后分场验证，完成后停止

先最小真实能力定位，再把所选后端/OS事务/DNS/FakeIP/配置/GUI/夹具同批写齐，冻结SOURCE再测，不每helper发Action。一Action一网络场景/测量进程，独立场景不同Action可并行；同VM A/B顺序，SOURCE/manifest/hash编译一次复用。不重造watchdog；沿现有finally/journal保证失败也恢复网络。

按契约D1–D5/P1–P2测真实两出口、CDN反例、单DNS/解析失败、bootstrap、正常Stop/部分Apply失败/中断恢复代表、GUI实际生效。资源满用测试专用小额度覆盖，保持其他flow/Tunnel前进、压力解除恢复；不要耗尽整台VM造故障。纯Tunnel开关A/B、Direct普通socket基线、直连大TCP＋Tunnel小UDP看唯一交付、p99/最长空洞、CPU每GiB、RSS、队列字节/年龄。Go进程含Rust不能按名字归因。宿主容量满停止更重同族；单worker/锁瓶颈仍需修。Normal/Game4必要接线代表即可，不全笛卡尔积。

不变：标准TLS握手外观、认证/账户/generation/完整性、原密文重传、Rust统一MTU、owned Stop。默认外层1460不含L2，内层自动只读；单机一个代理，不扩多代理攻防。不把“尚未合格”当不能开发执行的权限限制。

每批更新短devlog/功能卡/必要evidence和cursor，分清设计、实现、实测；保留失败与NOT_RUN。自主判断，找第一异常、定向复习成熟旧逻辑再修，不无目标调参/刷seed/抠噪声。全部029退出条件具备后给交付报告并停止；重复提示仅核新事实，不自创新任务。

## H1827用户确认的优化与实测后继（2026-11-14）

- **先收后测**：H1823签名P2同VM物理TCP 281ms、FakeIP Direct 6141ms；H1825的两socket TCP_NODELAY新SOURCE签名P2 [Action43578369480](https://github.com/lly8666/wbd-next/actions/runs/43578369480) 物理296ms、Direct6360ms，均1MiB同SHA/半关闭/120个Tunnel小UDP/两端Stop真实交付。两条各一次假设未消除约22倍慢，不能再无差别放大量子/调Nagle/刷同类Action。P1 CPU/GiB +7.42%只约0.009核绝对差，架构归因未成立。
- **第一批**按计划§4A：修Rust stage_sources只返回Tunnel数造成Direct-only满批被误判0的调度错误，Direct socket accept/connect/read/write进展、逆向限额满和是否有待处理工作分开反馈给原Rust TX owner；有实质工作立刻下一次公平轮转，真正WouldBlock再等，不能把10ms改1ms空转。共享WinSock事件/完成驱动是后续正式方向，不可逐flow线程。
- **P2夹具**把connect、上传、半关闭、首回包、下载时间独立输出；原16KiB每包睡4ms需醒目标记非峰值吞吐。Tunnel小UDP必须覆盖直连大TCP整个生命周期，不是旧120次短暂重合；唯一交付、p99、最长空洞、Stop与SOURCE均保留。
- **第二批**一条有界FakeIP持久化队列/单后台写者，TX不直接write_all/sync_data/压缩。等到实际durable ACK才给相关DNS合成FakeIP；错误局部SERVFAIL，续期合并、Stop取消、不让旧generation晚回调发布。16MiB长期开启时由写者安全低频压缩有效映射/隔离保护并校验重启恢复。
- **第三批**按真实保留容量对Direct TCP缓冲计费，按需池化或低频空闲收缩，64MiB是实际分配硬预算不是len或排队目标。小额度测试复核新Tunnel、旧Direct、DNS在压力时继续与恢复；然后才做定向P1 CPU因果测量。**完整029仍含**正式无Actions门Normal V3、Game4 CN、GUI签名Connect/Stop、D1–D5/P1–P2与IPv6/中断恢复、有限padding；这些没有证据不得交付。

## H1832正式启动/GUI已实施候选，实测待收（2026-11-14）

H1831签名Windows/WSL2真D3多A/CNAME+CN FakeIP和物理Direct UDP、Tunnel及owned Stop已在SOURCE `268fdc150937416a51991b440a961a5dc96a1a3e`PASS_SCOPED（Action43585387611），DNS应用等待531ms/1次，非独立fsync耗时。H1832新增明确`--split-enable`（默认off）及`--cn-rules-file`；GUI保存为可移植相对路径、原Go下一generation在非GitHub Actions也可选同一个Rust NativeSplitWorker，已有四阶段OS WAL/Rust真实Applied逻辑不造假。Game2/4尚未接线时收到显式split应Fail Closed，不恢复旧Game纯Tunnel冒充CN。**本H1832新SOURCE Windows/GUI真实起网Stop和规则有效值尚NOT_RUN**，先收正在跑的H1831 D3、不重复dispatch；再源锁验证单GUI/Normal代表，Game4、IPv6、P1/P2等继续。
