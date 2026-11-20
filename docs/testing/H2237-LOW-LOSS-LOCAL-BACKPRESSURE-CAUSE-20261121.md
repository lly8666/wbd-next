# H2237 | 1%局部反压与5%低容量差距：先修非CPU问题

**M0诊断独立分支，PR #57之上；不修改main、在途作者或已冻结029产品协议。**
截止首次SOURCE `c2ea61f25d7736f19d34ec319500b24cc6cb03c4`（[Action44787582885](https://github.com/lly8666/wbd-next/actions/runs/44787582885)），x86和ARM64真实原Go TLS/Rust single VM三Linux netns均12/12原生TCP通过，Stop成功。原始artifact分别14654264879、14654479755。

## 已区分的三种现象，不用“CPU满了”一言以蔽之

- **0%极限**：两平台单一M4 TX接近整核CPU，Shared TUN丢包上十万至百万，吞吐700–1000+Mbps，极端内核veth上游超供给。是CPU/发送内核链路容量问题，不是1%工况的全部解释。
- **1%固定200ms GE**：x86上传 WBD receiver299.153Mbps / Direct1077.800Mbps；原真实MSS同为1025B，WBD iperf内层TCP重传66206 / Direct29136。WBD客户端该generation SharedTun backpressure101426、queue_full_drops65760；真实M4 TX 20秒收包测试运行约8.36s、runnable等待0.46s，raw socket EAGAIN=0。大批**真实本地丢包**发生在CPU非持续满载的低损工况：不能把原因推给CPU总容量，优先看本机突发、每流fq供给、队列消费不连续，结合TCP cwnd/RTT/重传的放大。
- **5%固定200ms GE**：x86 WBD receiver上行101.715Mbps / Direct325.307Mbps，WBD本机generation queue_full_drops263，raw EAGAIN0；**与1%不是同一首个瓶颈**。需确认实际交付/线速、损失粒度、真实业务序列/ACK时序和内层TCP拥塞反应，不得以高性能0%调参替代。

新的H2236原批次外层Raw发送耗时细分：x86 1% generation真实Copied915418，M4分段 `collect0.372s seal1.424s sendmmsg5.674s settle1.282s`，其中driver同步真实syscall墙钟 `5.254s`，EAGAIN0。它不等于CPU满载；线程阻塞/内核包发送的耗时必须分离。5%收包的低负载同样有真实syscall2秒左右，不能对系统调用直接得出加快CPU就改善TCP吞吐的结论。

## 本次第一步是因果试验，而非任何产品默认限速变更

Linux现行 Go cold配置 `tun-fq-maxrate-mbps` **只允许0或600**，自有TUN `qdisc fq maxrate600mbit flow_limit256` 已有实际读回；**不修改这些产品配置或GUI**。在**同VM、同SOURCE、同200ms/GE1%内核netem**，使用真正Go/Rust/内核TCP，做独立原生客户端generation、同安装身份/真实Stop的：

1. 固定GE1%上行Direct 20s 4flow，核实本机可比较网络基础能力；
2. WBD默认每流fq600 20s 4flow上行，保存接收端真实吞吐/iperf retrans+socket MSS、原M4线程CPU/等待、原Rust Shared TUN Stop完整队列满/背压/批次耗时，和真实Linux TUN内核qdisc前后收发丢包；
3. 仅**测试夹具**在原客户端拥有的命名空间 `wbdc0` 上外部 `tc qdisc replace root fq maxrate250mbit flow_limit256` 并实际读回，不动主机/sysctl/server/别的TUN，按新原生客户端generation重做相同20s；
4. 再重做默认fq600 20s，末尾再测GE1% Direct，得到ABA和能力漂移守卫，所有对象做真 Stop和资源释放。

目标是区分“kernel TUN per-flow超供给造成本机队列拥塞与丢包、TCP降窗”与“根因仍在raw侧/内层TCP的其他局部缺陷”。**若fq250只是将吞吐固定压低、队列溢出转为更大滞留或p99变差，则必须拒绝这条路径**。有益也仅证明这个**实验性的OS侧反馈方向**有价值，不能把fq250硬写进产品、不能声称修好5%、不能跨VM比吞吐，更不能提前宣布Windows/Game修复。

## 正式修复的入选条件

须在**不损害乱序首到即交付 / 无跨流HOL / 单个Rust owner / 机会式原PN原密文外层repair / 原Go TLS / FEC / Stop**前提下，消除已证实的首个本地异常。优先设计让内层TCP内核有稳定、低延迟、有界的反馈，配合原同owner调度公平，不靠加8→64堆积、更不让第二套外层可靠流给业务排序。逐阶段真实业务需要receiver goodput、重传/GiB、本地queue_full、Linux fq drop/backlog/年龄、原线程CPU/GiB、p99的配套证据；任何只改善一个计数的修改都不能升级为产品完成。1%确认修好后，以**独立5%**同等验收追剩余差距，再传播到受影响Windows/TUN等价机制与Normal/Fixed/Auto/Game2/4；不同平台及模式需真实夹具与Stop，不得复制不适用的Linux qdisc。

0% WBD极限的sendmmsg/kernel耗时细分仍有价值，但不能取代先解决1%、5%现有非CPU异常。

## 完整原生1% A/B/A回执（SOURCE 454f33f，Action44790734647）

x86_64原生Go TLS/Rust、真正Linux kernel TUN / AF_PACKET、三netns不经DERP。静态、业务、每generation Rust Stop及server Stop全部SUCCESS；原始 [artifact14656073336](https://github.com/lly8666/wbd-next/actions/runs/44790734647/artifacts/14656073336)，源锁JSON见 `docs/evidence/M0/PLAN029-H2237-1PCT-FQ-600-250-600-20261120.json`。

Direct 1%同VM前/后实际接收端927.49/979.39Mbps。WBD固定200ms+GE1%，全程一档独立connection generation、20秒上行4流：

| 原生TUN fq设置 | 实际接收Mbps | Shared TUN queue-full | backpressure | 内层TCP重传/实际GiB | M4 TX CPU |
|---|---:|---:|---:|---:|---:|
| 产品原600 before |242.59|118281|170663|204033|10.753s|
| **仅夹具试250** |253.75|52138|85353|85096|11.304s|
| 产品原600 after |268.23|118167|174757|148979|11.227s|

三档产品owned TUN内核fq qdisc `drops=0`，而Rust Shared TUN真实满队列丢包。实验fq250使Rust满队列丢包相对600下降约56%，重传/实际GiB也下降；返回600后Rust满队列丢包回到原水平。**但是250接收吞吐在两次600基线之间，不能声称提升**，不能改全局fq默认600或把250加入实际CLI/GUI；且250仍有52138真实满队列丢包。此实验指向**入包突发与单一M4消费的速率不匹配是本地放大器，但静态限速非完整修复**。本机0%CPU单核饱和与5% queue-full近零仍然是彼此独立的问题。

## H2238 维持600Mbps峰值，仅测试内核TUN fq短突发

Linux自有TUN的现行 `tc -d qdisc` 真读回是 `quantum 2178b initial_quantum 10890b maxrate 600Mbit flow_limit 256p`；原TUN MTU1089。下一Action在同VM相同GE1%/4流/20s，做**原600/短quantum同600/原600**，新实验仅在**已验证owned client namespace的wbdc0**替换外部qdisc（quantum=1个真实TUN MTU、initial_quantum=2MTU，maxrate仍600Mbit，flow_limit仍256）；源锁真实tc readback，独立owner Stop和app/CPU/本地队列指标齐全。这只控制启动突发，不降低四个TCP流的配置峰值，不改变产品Go配置/协议/密文，也不等于FEC/repair。若真实接收端goodput、局部队列满和小流p99不能共同获益，拒绝进一步产品改动并转向内核/原M4事件级短停顿原因。不同平台的Go冷配置及模式验收仅对**确证有益的正式修复**进行。
