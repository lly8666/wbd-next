# H2234｜低丢包高负载 TX 失速的因果定位与完整优化验收

状态：**DIAGNOSTIC SOURCE ONLY / PRODUCT OPTIMIZATION NOT YET PROVEN**。
接续 H2233，在它的独立 PR 分支之上工作，不覆盖主线 M0、PR #55 与旧 029 的证据。

## 不能变的执行契约

Go 原生 TLS 1.3、冷认证/lease/generation/OS/GUI 与 Rust 原生 long-lived owner 保留。真实 DATA 首到、乱序即交付，绝无跨流 HOL。外层 FakeTCP 的 ACK10/SACK/window 只负责 TCP-like 外观；机会式 repair 仅原密文、有预算、有次数与年龄上限，不能改成可靠有序流，不等外层 ACK 才送 fresh。AEAD/PN、租约/重放、MTU、FEC 现有门限、Stop 的 owned join 全保留。任何调优都不能用 Go per-packet 回调或隐式新线程/新 FIFO 换数字。

## H2233 已确认的两个不同损伤

1. 高速固定200ms无额外jitter，Action44764736732（SOURCE 6c1996c）：12/12 真TCP应用成功，但无损直连上行612.631 <800 Mbps，**不可称产品高速因果 PASS**。原生客户端 1% connection-generation `SharedTunReader queue_full_drops=49529`、`backpressure=75625`，5%分别9209/16262；每个 generation 累计3s上行、20s上行、20s下行，不能分配至单项。对应 1% TX worker CPU 累计12.63s（会话约65s），证明真实本地拥塞却尚不能定性为 CPU 算力不足、慢唤醒或 raw socket 拒发。
2. 15ms jitter 的 Action44768861776（SOURCE413c7ed）：容量约21Mbps（DERP/relay），相同丢包档无本地队列溢出，但有很深的 `lagged32` 乱序计数。不同 VM/source/吞吐，**不是固定vs抖动因果 A/B**。原始 iperf `-M1037` 只是 requested；7/8 有效分组从真实 `ss -tinm` 回读到四流各1025B，另一个 UNKNOWN。
3. direct 的 netem `drops/(emitted+drops)` 与 WBD 不可当作 TCP segment loss 比率：GSO skb/接口 TX包计数粒度不同。所有来源必须保留原始计数、不同维度、前后快照，不按目标1%/5%冒充真实字节损失。

## 当前代码因果图（每次不同阶段独立账户）

| 边界 | 实际唯一Owner/界限 | 必需的定位证据 |
|---|---|---|
| 内层TCP / kernel TUN | Linux TCP BBR / wbdc0队列 | 实际内层 negotiated MSS、socket RTT/cwnd/retrans/GiB、TUN rx/tx/drops |
| SharedTunReader | 同一Go进程**唯一 Rust** TUN物理读取者、每次最多8帧 | read→route计数、每路pending当前/峰值/年龄/溢出、线程CPU/runqueue wait、停顿 |
| per-route pending→M4 inbox | 每路8个待处理、64KiB、100ms及每路64-slot sync inbox | `backpressure`/实际 `queue_full_drops`/oldest age；不能扩大为跨路缓冲/等待 |
| 原 M4 TX | 单线程消费每转最多32条、原始M1 loan、AEAD/PN、FEC有界调度 | TX thread CPU/wait、source_queued→M4 copied、M4 `tx_backpressure`、原有诊断计数 |
| raw kernel socket | sendmmsg 在 Entry 锁外，真实 copied prefix | EAGAIN/outq/内核拒发、actual first-send、local queue_age；无第二次PN reseal |
| 对端原M3/RX/TUN | 原 Rust owner；乱序即成功交付 | raw_observed→unique→TUN-delivered、replay/AEAD错误与真实业务 RTT P99 |

## 本批具体诊断方式（opt-in、无逐包日志）

- Linux 线程名的 `comm` 最多15字节；历史 `wbd-original-m4-tx` 与 `-rx` 被截成同名，外部难以区分。将**现有同一线程**稳定标识成 `wbd-m4-tx` / `wbd-m4-rx` / `wbd-tun-reader` 等短名，绝不生成新 owner，不变 ABI/wire。
- `WBD_H2234_TRACE=1` 时，独立于 Rust/Go 数据面的 root Python observer 按**200ms**读真实 `/proc/<native_pid>/task/<tid>/schedstat`（CPU执行ns、runqueue等待ns、调度切片）、wchan/上下文切换以及该进程 network namespace 的 `/proc/<pid>/net/dev`（wan0/wbdc0 tx/rx/drop）。每20s case至多400个样本且不超过100秒，停止信号由该测试拥有，保存 monotonic_ns 和完整source/run。任何缺失显示 UNKNOWN，不能硬算零、不能据一个采样宣称逐包p99。
- 同case标 iperf 客端单调起止ns、实际接收goodput、MSS真实在途 `ss`、TCP重传和ARM qdisc skb/readback。原始外层 repair计数和 Rust shared-TUN Stop 继续归属于原session，不能造每case队列丢包。
- **仅本分支**的有源性能实验使用 Normal/off、GE1/5%、额外单程200ms、零额外jitter、同VM顺序 Direct/WBD。先跑两方向12s8p clean Direct；任何方向低于500Mbps则立即完整记录 `NOT_RUN_LOW_LOSS`并结束（节约Runner），至少500才做定向瓶颈观察；项目原两方向**>=800Mbps**产品因果准入资格保持不变。低于800的诊断数据真实，但不能作为高速优化效果。
- H2231 的UDP RTT/CPU/RSS另有活动PR；无需并行重新做全损伤矩阵、FEC、Windows/ARM跨平台全部重扫。不同source不做CPU改善因果比较。

## 后续「完整优化」选择树

A. **TX runnable wait持续突增而CPU并不忙**，与TUN溢出前的时间桶一致：查线程执行权、`recv_timeout`唤醒事件和轮转公平。修原唤醒/处理量子，按路新DATA无需等旧路，最老等待时间与空转唤醒一同验收。

B. **TX CPU持续接近单核上限、runqueue wait不高**：按原 M1 owner锁/AEAD/数据副本/计数索引分类CPU开销，消除可证明的重复工作并合理复用批量，保留低包速即时首发及FEC/feedback独立期限，不能直接补队列。

C. **kernel raw EAGAIN/outq持续增长**：只在原sendmmsg owner处理有界机会与额度、free fresh而不重封密文、不对外层等待确认。产品接线与真实driver回执成对施工，不能根据MBps随意上调系统全局缓冲。

D. **共享锁竞争**：减少不必要的持锁批工作或改为锁外只读不可变结构；不得复制第二套 crypto/control/packet routing 状态机。

E. **网络/测试对照本身不足**：先修真实segmentation/MSS与容量可比性，停止改产品，不把基础设施低容量或 netem skb分母当产品算法失败。

任何整改都要同时完成 Rust 双端受影响路径、caller/配置/夹具/旧功能卡、最小针对性单测与原反例；同VM冻结源码做前后 A/B，按 receiver GiB/CPU-s、小TCP/UDP实际p99、memory/wakeups/Stop和no-HOL通过。改善只转移到别处或拉长发送排队则判 FAIL。修完整原因而不是为了某条报错贴补丁。

**当前实现边界**：此文对应线程可辨认＋外部只读诊断，不代表 A–D 中任何产品优化已经完成或真实高带宽复验PASS。

## H2234 本地可重复因果诊断（一 Runner，禁止冒充 WAN）

之前的三独立Runner测试即使SOURCE完全相同，也多次因 Tailscale DERP 把无损 Direct 限在21Mbps；H2234 Action44775952603 的两方向真实参考为21.337/21.496Mbps，故原生 Linux Go/Rust 构建及ARM路由成功，但 **1%/5% WBD 未运行（NOT_RUN）**。预检正确停止了更贵的弱网矩阵；继续刷同一类随机Runner会消耗资源且不能定位本机高PPS拥塞。

复用已成熟的 H1267/H2228 原始 Go TLS、Rust kernel raw/TUN 与 netns/veth 启动约束，新增 `tools/m0_h2234_local_netns.py` + `qa-h2234-local-native-netns.yml`：

- 真正的客户端／Linux IP router／服务端是同一台x86 Runner的**三个独立network namespaces**，两个彼此独立的veth L2，路由器唯一设置真实双向 `tc netem`，不经过Tailscale或DERP，不用Go/模拟通道充当数据包；反方向无NAT。所有原始Go产品与Rust库只构建一次。
- 以原H2228真实四流iperf3路径测试：先0%无附加延迟Direct上传/下载12秒8流；仅两方向都>=500Mbps才做GE 1%/5%、各方向额外200ms固定延迟、无jitter、Direct/WBD顺序四流20秒。申请 `-M1037`，必须用运行中真正的 `ss -tinm` 核对内核MSS，存储逐case router qdisc skb/实际接口/原始iperf receiver bytes。500Mbps只是高PPS本地诊断最低负载，不改变真正跨机>=800Mbps产品因果准入。
- 每个丢包档只启动**一个原始Go TLS/Rust客户端generation**；20秒上传与20秒下载之后真实SIGTERM并等待该generation的 SharedTunReader Stop，记录队列满和backpressure，绝不把两个方向的会话累计计数误写成独立case。真实server最终Stop也必须通过，未知/未关闭不能宣称Pass。
- 在WBD每个20秒case由独立root Python进程以200ms采样原始TID的调度状态与netns `wan0/wbdc0`，同源monotonic_ns对齐每次iperf接收goodput和TUN/Socket读取；probe未捕到或 `schedstat` 不提供可靠数据时明确UNKNOWN，不能将0当没有调度问题。原始Go/Rust热路径无新增线程、无逐包日志、无重传和排队改变。
- 此阶段**只能**证明同VM的原生本地TX消费/内核损伤/时延机制，不包含真实跨VM公网RTT争用、Windows Npcap或host CPU的独立容量结论。正式性能收益仍须把修前修后产品在同组/同source网络下按接收端GiB、低速P99与资源完成A/B；最后才用高容量真实跨机、实体Windows验证。

任何失败应根据「首个异常」收紧真实内核建链、原应用socket、TUN/Stop或监控，不引入伪网络控制器或扩大公有通用防御框架。

## H2234 第一次真正本机高吞吐 SOURCE（Action 44779139886）

SOURCE `7084b2e8ec32295ee58ad937abcdec191e12844a`，原始artifact 14650594764；独立三 Linux netns，x86 Go TLS+Rust native/TUN/AF_PACKET、内核GE1/5%，**10/10真TCP iperf业务成功**，真实本机Direct无损 receiver 50.989/51.321Gbps，不是物理WAN。整体FAIL只因验收脚本错误要求客户端才有的 `V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=server`；原server日志实际有 `V4_PUBLIC_SHARED_TUN_STOP generation=1 ... reader_joined=1`、`V4_PUBLIC_SERVER_MASQUERADE_STOP_DRAINED owned_rule_deleted=1`，且 `V4_PUBLIC_MIXED_NORMAL_STOP_DRAINED reason=server-close remaining_flows=0`。后续仅使用真实这三类共同证据，不把原Action改写为PASS。

真实接收Mbps：1% Direct上1072.342/下1109.121，WBD上273.831/下268.228；5% Direct上683.481/下521.719，WBD上111.999/下143.868。1% 原生客户端连接 `SharedTunReader queue_full_drops=105610 backpressure=157522 routed=868367`；5%分别663/1440/439700；服务端跨工况累计 `queue_full_drops=112836`。1%客户端raw `eagain_turns=0`，原M4 TX线程26–28s约11.523s CPU /0.429s可运行等待，原M4 RX为1.958s CPU /0.291s可运行等待，原读TUN为2.057s CPU/0.450s可运行等待；不是简单的CPU调度饥饿或内核raw发送缓存满。该线程统计不区分逐包AES/锁/其他代码；同源显著本地Shared TUN溢出，已把首个候选收紧到本地TX数据处理效率。

**下一源码**在同样local三netns中先加入真实0% WBD原生两向20秒4流基线，独立客户端generation/Stop，再跑1%/5%；新增 x86_64和原生aarch64两个**不同Runner的单机三netns**任务，只对各自平台的内层Direct与WBD同源同机比较，严禁直接比较跨架构绝对CPU或将ARM看成NAT穿透保证。两种架构都保持原Go TLS/Rust owner、真实Stop、同形损伤；最后确定优化有效才推广到Windows以及Game/Fixed/Auto。

## H2234 SOURCE 2f62f983：同源x86与ARM原生0/1/5真实结果

[Action 44782492146](https://github.com/lly8666/wbd-next/actions/runs/44782492146)，同源码 `2f62f983a5f970ea2bfc236ac0804f4cd6271322`，但x86和ARM为**独立不同VM**。各自是实际Go TLS/Rust单机三Linux netns/真TUN/AF_PACKET/veth L3 router/GE200ms 1%或5%。两者不是同 VM AB，绝不可用绝对Mbps/CPU差值称产品优化。

x86原生 12/12 TCP应用PASS，服务端真实Rust reader加入+masquerade清理+generation全部Stop均PASS；0% Direct接收上/下 59.117/60.866Gbps（本机虚拟veth，不是WAN），0% WBD接收1243.940/1262.757Mbps、1% Direct1022.444/1045.247 WBD318.160/390.649、5% Direct695.628/515.724 WBD194.443/218.730Mbps。0%客户端整个会话 Shared TUN `queue_full_drops=1040343`，1%=25528，5%=447；raw eagain依旧为0。0% WBD上传约20秒，M4 TX线程 `cpu_run_ns≈19.98e9`，`runnable_wait_ns≈0.31e9`，即**单个TX owner单核计算已饱和、非主要runqueue饥饿**；RX下载在同档需16.25 CPU-s，也要防止上传加速仅转移瓶颈。

ARM64原生12个TCP中11个成功，唯一FAIL是5% **Direct** 下行iperf3控制连接因 `Connection reset by peer`，分类 `DIRECT_KERNEL_TCP_IPERF_ERROR_NOT_WBD`；不得归咎WBD或把整轮改成成功。0% Direct上/下99.035/98.792Gbps，WBD965.246/977.186Mbps，1% Direct1057.633/1054.031 WBD331.836/352.595Mbps，5% Direct上传703.597（下载FAIL） WBD上150.439/下163.422Mbps。ARM客户端 Shared TUN 0% queue-full=849572、1%=36990、5%=538；0% WBD TX约20秒 CPU20.21秒/runqueue wait0.37秒，raw eagain0。这证明本地瓶颈存在于两种原生架构，但不能以此计算架构性能提升。

**关键定案**：0%最严重的本地queue-full/内层TCP重传发生在TX线程连续单核忙时，应优先分解原single-owner M4 CPU耗时，不能靠调线程优先级/无限队列/外层按序重传修。0% WBD高吞吐不能冒充“无本地丢包”；应用好吞吐不是无损或p99好。

## H2235 批次级耗时探针（仅开发冷开关）

在现有原Rust M4 TX线程内，用一个栈本地有界计数器汇总已真实完成的M4 batch；仅 `WBD_H2235_M4_STAGE_DIAG=1` 读取少量 `Instant`（**每批**，不逐包、不持锁做系统调用），Stop时打印一次 `V4_PUBLIC_M4_BATCH_STAGE_STOP`：

- collect：现有64 inbox取包、原M1 loan/copy所有同turn工作耗时（每轮累计，不产生额外消息）
- prepare：原 `background_tun_once` 开始至准备进入M1/AEAD owner（TUN路由/来源检查）
- seal：原Entry锁内M1/AEAD/PN/FEC冷/热逻辑至FrozenRecord真实ready
- sendmmsg：原Entry锁外Linux内核同步`send_kernel_multimsg`完成
- settle：原copy prefix回执/feedback/候选shadow/borrow归还的owner结算

只算返回至末尾的batch（早退场景仍另以原error/Stop和H2234外部线程统计看，不以该计数覆盖总CPU）。资料包括批次数、真实copied条数、各段总ns/max ns。独立的原外部/proc TID统计为总CPU与调度等待上限，**两者不要求数值相等**。被打开的观测可能改变调度，不能拿新instrumented SOURCE vs旧未instrumented SOURCE跑分当真实收益。

分析后才能对**确定的具体CPU主导阶段**做成组完备优化；每项持续保留single-owner、fresh-first、no HOL、Go cold TLS、机会式原PN原密文最多一次repair、ACK10/FEC/Stop，以及跨平台的受影响调用链/模式/文档。Windows Npcap和Linux TUN并非同一个driver，先复制经证明的架构原则，再分别实测；Game2/4和Normal Fixed/Auto需要各自原生验收，不能因为Normal off过关就宣布全部过关。
