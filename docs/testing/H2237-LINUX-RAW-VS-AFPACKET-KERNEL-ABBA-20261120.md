# H2237｜同机真内核 raw IP HDRINCL 与 AF_PACKET `SOCK_DGRAM` ABBA 可行性对照

状态：**TEST_ONLY / NOT_PRODUCT / RAW_M4_STILL_CANONICAL / NO_WBD_PERFORMANCE_GAIN_CLAIM**。

H2234/H2235/H2236 已确认的真正源锁：

- 真原Go TLS1.3/Rust原M4/原TUN/原收发/真实Stop，x86与ARM原生各自12/12 Linux 三network namespace真实TCP业务PASS。H2236 [Action 44787582885](https://github.com/lly8666/wbd-next/actions/runs/44787582885) SOURCE `c2ea61f25d7736f19d34ec319500b24cc6cb03c4`，0%客户端raw发送链内真正同步Linux`sendmmsg`占x86约96.7%、ARM约95.6%墙钟；1/5%仍约90%。Checksum/头部仅x862.1%、ARM2.5%（0%）。正常 original M4单线程接近单核满载，Shared TUN入口本地溢出。计时**不是纯内核CPU profiler**。
- Linux原生现用 `AF_INET/SOCK_RAW/IPPROTO_RAW + IP_HDRINCL + SO_BINDTODEVICE`，同一个内核`sendmmsg`真正copy prefix，已经有最多32条有界ready新DATA、原PN/AEAD、严格租约/MTU/Stop。
- 不允许把改善内核PPS的候选直接升级为产品。`packet(7)` 的 `AF_PACKET/SOCK_DGRAM` 是 **L2 device-level** 机制，kernel根据 `sockaddr_ll` 构造L2头；跟`raw(7)` 的IPv4本地路由、邻居解析、Netfilter OUTPUT、原socket错误/PMTU语义并不等价。参考 <https://man7.org/linux/man-pages/man7/packet.7.html> 和 <https://man7.org/linux/man-pages/man7/raw.7.html>。

## 本 Action 做什么

单独 TEST_ONLY C程序预制32份严格checksum真实IPv4/TCP＋1024B公开确定性测试payload；原 `sendmmsg` A/B两种方式都用**同一L3头＋同一固定payload的两个iovec**，同固定源/目的IPv4和seq/tcp外观，不接原Go/Rust密码、WBD用户内容或原生产运行时。一个原生x86或ARM VM的客户端、router、server是三个独立Linux netns＋两个veth L2段，真实路由、router MAC内核回读；不会经过DERP，也不因用户公网 NAT变化选路。无任何WBD业务或原客户端所有权被转交给这个程序。

**两组ABBA**：先100kpps受控入包（raw、packet、packet、raw），再无节奏限速探测峰值（相同ABBA），每腿至多200000个原始1064B IP/TCP报文，3s上限。真实原始netns `ip -s -j link` 前后：client真实TX、router入/出、server真实RX/drops；不能用sendmmsg copied前缀替代真收到。短命 tcpdump只捕真实router最初4个**公开测试帧**，独立校验IPv4/TCP两层checksum和L3字节散列：等seq的raw/packet字节必须一致。原始pcap在生成摘要后删除，源锁/Action/接收计数与hash存文本 artifact。

100kpps实验必需两种模式都至少90%内核真实server NIC RX；低于则实验 **FAIL/不算产品性能**。无节奏实验额外记录但可以因内核qdisc overrun不合格，不能把曾经accepted的报文计算成goodput。观察同一VM内、相同L3发送字节与实际接收下的进程CPU秒/送达GiB及真实RXpps；若AF_PACKET包率或效率没有明显可重复优势，应停止探索而不是投入新的生产载体。

## 接入生产前的硬门槛（未定案）

若候选显著胜出仍需新原生owner设计：生成级网络权限与同真实Go认证控制/lease、原路由守护revision、真实IFINDEX与下一跳邻居MAC有效性/失效、收发方向一致性、PMTU/DF、原始密文borrow Stop fence、MSG_DONTWAIT copied prefix/partial/ambiguous/eagain、原IP/TCP字节一致和潜在Netfilter bypass的安全边界；任何前置条件不达标立即回到原raw传输，不允许默认packet模式或私自绕过安全策略。直接连接/海外出口/IPv6不增加额外Linux模块或跨流等待。GUI配置保持旧键语义，功能卡/原现有签名验收需覆盖模式/caller。Windows走Wintun/Npcap另一真实驱动，**不可仅把Linux结论复制为Windows PASS**。

若产品真优化，先在同VM同源码具备两个冷可选驱动的原GoTLS/Rust真实0/1/5使用**相同本机Line+CPU/实收GiB/满队列/小TCP与UDP P99/Stop**有序ABBA，绝不比较跨VM或探针开关不同的比率。再单独原生ARM、真实双段Direct WAN与物理Windows、Normal/FEC Fixed/Auto、Game2/4及已开启的分流模式，最后一并验收。

**底线**：no HOL乱序首到、原Go标准TLS1.3控制、原Rust只有一个M4数据面owner、原TCP-like ACK10/window65535/SACK展示、原ciphertext受预算机会式外层repair、不按序重传、不Go逐包、不扩大队列掩盖等待、AEAD/PN/MTU/lease/generation和owned Stop均未改。

本文件及本测试**不代表已经实现了Linux AF_PACKET生产发送者**。
