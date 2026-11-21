# M0 H2244｜统一、可证伪的 DATA 入口公平流控与 M4 原生批次服务契约

**2026-11-21 Draft / 设计输入；尚无任何正式产品实现或资格。** 这份设计来自**同源真正Go TLS/Rust**经 x86/ARM 双架构运行的 H2240–H2243 原生 kernel TUN/AF_PACKET/内层TCP/真正 owned Stop 事实；工作分支 PR #64，不代表用户默认变更。不能把实验成功等同于物理Windows/高速公网成功。

## 1. 具体根因，不再概括为“CPU满”

H2240：GE目标1%+单程+200ms四流时Rust SharedTun队列满20,064，而同一真实原M4 20秒只有约5.2CPU-s；单流几乎无掉包。是**输入短时供给远超过原M4按batch实际消费**，不是平均一核CPU满的单因。H2241：只暂停唯一SharedTun reader将Rust排队满25940→2185且接收goodput268→320Mbps，却使内核TUN设备真正tx_dropped从0→38670；qdisc drops0，因为TUN内部ring与qdisc是**不同层**。H2242：全部TUN CAKE每流公平＋总量450 Mbps AQM把Rust和TUN ring的丢包趋近0，可是原M4 copied/batch从x8614.4→2.9、ARM16→2.4，使CPU/交付GiB增加70–100%并降低交付。这是**公平源端整形的时间粒度与原sendmmsg批次粒度不匹配**，不是AEAD/CPU无从优化。H2243：令牌桶固定实验450Mbps、16KiB与48KiB两种短突发，子fq_codel按**内层TCP五元组**公平ECN/AQM：**48KiB双架构真正业务/Stop/Direct完整PASS**，在Rust/TUN/qdisc绝大多数丢包都被抑制的同时M4批量x86恢复15.15、ARM10.13；16KiB过小造成ARM qdisc19,850掉包和M4仅2.77/批。前后正常产品Direct均约1Gbps，但本实验固定450 Mbps总上限禁止写为默认。

## 2. 三个预算 + 只有一个速率权威

**入口源预算（内核/OS原拥有者）**：进入原TUN ring前应按内层流/租约公平地让已有TCP得到早期ECN/AQM或真正容量反馈。有限的token burst可容纳原M4一次sendmmsg的正当工作量；不能让四条流各自独立获得一个未经总量约束的600Mbps峰值，也不能通过强制每包等时的CAKE破坏真正批次。合理burst的量纲是`M4一次原生批次可服务字节`和`MTU`，不是“缓存越大越好”。**没有一个永久固定的450Mbps适用于1Gbps/10Gbps/弱网全部用户**。

**Rust SharedTun分发预算（原读线程）**：保持实际Authenticated route/lease/generation隔离、原每路8个pending/64KiB/100ms和唯一物理TUN reader，新的小流不得被一个慢租约/数据空洞堵住，尽快把授权TUN包交给原生source M1。已验证H2241单租约reader短暂停会把损失搬到内核且最长实际睡眠1.897ms；正式不得靠任何持锁wait/poll/全reader pause来获得“0 Rust drops”的漂亮计数。需要按流/租约公平，允许到期的bounded排队丢弃或ECN，且单层损失不能翻倍。不可重新封包修复PN。

**原Rust唯一 M4 服务预算（真实同一TX owner）**：唯一真实`sendmmsg`已确定copied prefix计数才表示**本地内核实际接受**；结合原owner的原原子计数、批量大小、CPU/交付GiB，可判断服务成本和短时需求。它不是对端可靠接收、不是外层ACK/FEC Health，不能用作虚假的投递成功保证。只允许在**同一个原owner**的批次结算后生成低频、来源锁定的容量事件，不逐包调用Go、不加独立稳态控制器/冷轮询器、不保留旧密文等待ACK、不新增第二个数据owner。

**控制逻辑**：准备用单个来源的真实ServiceCapacity估计（本地真实copied/wire-bytes与原M4可运行时间，区分raw sendmmsg等待、source backlog和实际业务外部接收），以**每epoch例如真实200–500ms聚合**而不是每包更新，对稳定真实队列占用/真实Tx需求做有界迟滞：超额积压持续才减速；积压退却但业务仍有真实需求才渐增；短突发保留在经实际验证的16–48KiB`batch-sized`量纲；没有真实需求/stop时不发出任何新控制动作，禁止假业务包。不能将当前被限速后的`copied/sec`当作唯一“可用极限”，否则自锁在低速；需要在有真实待发业务、内核qdisc/原Rust不溢出时**受约束地试探提高允许rate**，且有快速回撤。租约数量动态变化需再分配公平份额，不等某个旧租约的ACK或丢包；可以保留用户显式冷回退原fq600/无整形选项，但不得自改GUI设置。

**OS职责**：Go依旧只拥有冷OS配置/标准TLS/GUI，Rust依旧唯一稳态M4数据面。如果要调整Linux已有自有TUN qdisc，必须沿**既有冷OS控制边界**使用去重的**服务率阈值变化事件**，不是Go逐包FFI、不创建独立空闲心跳/轮询actor，也不得让内核qdisc变更阻塞Rust加密锁或完成真实DATA。跨平台Windows Wintun/Npcap没有Linux `tc`，需要实现等价的**按租约/flow公平有界入口**，不照搬不适用的CAKE/TBF语法。禁止给raw外层socket加新的可靠有序协议。

## 3. 源锁可证伪验收

先以H2243真SOURCE `30d7fff41be89aeeea240586e75e78947917f8f3` [Action44853457069](https://github.com/lly8666/wbd-next/actions/runs/44853457069) 作为双ISA真实层级基线；下一步在同一SOURCE/VM并列 0%真实高负载、GE1%和GE5%按实际skb/GSO损伤粒度、四流加**独立小TCP和UDP应用Echo并发的P95/P99及丢失/首包**验证，防止低速限速和短突发放大尾延迟。每个网络场景记录**真实接收端交付Mbps、inner TCP retrans/GiB、TUN qdisc父/子层drops/ECN、内核TUN link tx_dropped、原Rust SharedTun queue_full/age/bytes、M4 copied/batches/driver syscall/CPU/GiB、RunID/SOURCE、原native Stop**。父子qdisc计数可能重合，不能直接相加；netem真实GE随机seed在Ubuntu旧tc不支持，不能把每case的相同目标率误说成同packet loss。

**拒绝条件**：固定的≤450Mbps用户速度上限，内核新队列真丢包只是从Rust搬家，内核更长排队让UDP或首个TCP响应P99恶化；M4 copied/batch重回2–4，CPU/交付GiB明显恶化；停止/新租约发布/多租约公平或第一到达乱序交付被阻塞；任何外层伪TCP重传从`原PN原密文机会式最多一次`变成稳定可靠序列。没有通用平台全绿前不得声明正式产品优化成功。

**后续实际产品实现**：应从不依赖PR #62已否决单reader暂停的**干净分支**独立挑选验证过的公平有界批次机制，不把有害H2241分支历史直接合入main；按原Go TLS和Rust owner边界完成Windows/Linux x86/ARM的调用链和Normal Off/Fixed/Auto/Game2/4受影响分支，物理Windows独立Health/UDP/3秒上行必需重验。原已有M0主线单写者/在途PR都保留所有权。

## 4. 永久红线

标准Go/TLS1.3冷建链无私有ClientHello前导、TCP-like窗口/ACK外观（ACK只作表演层，而非业务投递确认）、乱序独立DATA**首到立即交付**，任何新业务不等旧PN/旧流/修复缺口/FEC截止；Rust唯一M4 PN/AEAD owner；原同密文PN有界机会式表演重传最多一次，绝不是外层有序可靠TCP；原FEC、MTU1460默认完整外层IPv4、认证/租约/generation/replay、真实驱动/owned Stop、安全凭据全部保留。
