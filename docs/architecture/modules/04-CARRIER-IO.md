# 04 TCP-like carrier 与平台I/O

## 外观和收发边界

沿用旧faketcp的SYN persona、MSS/WS/SACK协商、FIN/RST和bootstrap seq接续。经查旧 `packet.go` 稳态data为IPv4 20B+TCP20B，SACK仅ACK/control使用；没有TCP timestamp就不要自行新增。设计允许未来已协商的options，但MTU按真实header算。

外层维护`tx_seq64/rx_seen_intervals`与表示用cumulative/SACK。记录TCP seq32到seq64时，选距可信当前参考最近且距离<2^31的候选；非法跨度不更新参考。收到大幅跳跃不能一次清空所有去重/恢复状态。seq回绕只影响wire编码，不重置record PN/逻辑ID。

RX的外观累计ACK可沿用原弱网适度放弃缺口策略，但只存在presentation状态；08的真实receipt是另一套状态，不准互相赋值。advertised window沿用原稳态65535及协商scale语义，不能误拿bootstrap256KiB或shadow占用缩成零窗。外观窗口不足以覆盖线路BDP时报告TCP-like退化，不门控真实新业务。

一个新record对应一个完整TCP payload单元；可处理一个payload内多个完整records，但不拼可靠有序TCP byte stream。缺尾record直接丢该残段，别卡住下一完整payload。中间设备把record任意重切成多个TCP segment不是首版支持承诺，必须显式检测/报告；在正常MTU内按一record一segment和关闭不合适的coalescing路径避免自身制造该情况。

## 发送事务

固定密文重传保持record bytes、PN、TCP起始seq和payload length。每次发送重新构造外层header的当前ACK/window/IPID（已有timestamp策略才更新timestamp），重新校验checksum。缓存密文checksum部分和pseudo-header不变量可以减少扫描，但奇偶长度拼接必须与全量参考一致。

`TxBatchOutcome`必须区分：明确成功prefix、明确未发送suffix、单个不确定项。首次提交成功才计F/first_sent并安装正常repair状态；不确定发送保留同密文和seq，计独立unknown_tx，预留预算按已占用处理，不能当新包再seal。后续若收到真实receipt可消除不确定。完全失败可短期保留同cipher再送，仍不重复记一次fresh成功。

首次发送的本地重试与网络repair分别计数；若之前可能已上网，后续发送按repair预算/两次上限保守算。避免用“系统调用重试”绕过10%。timestamp采用提交完成近似时刻并报告其界限，不把进入软件队列时间当wire发送时间。

## Linux后端

AF_PACKET非阻塞fd；RX `recvmmsg(MSG_DONTWAIT)`最多32包，TX `sendmmsg`同样ready-only。检查每message长度/截断标志、实际link type/VLAN、方向和目标tuple。`sendmmsg`返回n只确认前n个；部分成功之后的具体errno可能已丢失，suffix保留原内容再按规则处理，不假定全部已发送。

TUN普通read是一整个packet，不假称recvmmsg适用于TUN；一轮最多32次ready read，write短包作为异常，不拼接成另一包。epoll interest按WouldBlock调整，退出/控制通过eventfd唤醒。SO_RCVBUF请求后读取实际值和系统限制，若受限只报告有效值；是否改sysctl仍由原安装/配置方案控制，不静默全局改系统。

过滤尽量在已有BPF/packet filter挡掉无关流量；drop统计必须socket/driver与host分开。暂不引入AF_XDP、busy-poll、GSO；profile明确I/O占比后再单独任务。参考 [sendmmsg语义](https://man7.org/linux/man-pages/man2/sendmmsg.2.html)。

## Windows后端

Npcap RX handle仅reader使用；packet pointer在下次pcap调用前复制到owned slab。TX用独立handle/scratch，沿用旧8包/16KiB ready sendqueue起点，`sync=0`，不靠pcap timestamp pacing。成功字节包含队列header：按预计算packet结束偏移映射accepted_prefix。返回落在半个packet内是IoUncertain，不能把整suffix无脑重发。

Npcap过滤器更新/close走reader命令与quiesce，不在另一线程close一个仍在dispatch的handle。等待上限必须能响应stop；pcap timeout不是所有平台可靠的取消机制，有能力的后端使用event，其他用有界reader+明确break验证。不能把原“断开清理卡住”搬来。

Wintun：ReceivePacket后尽快copy→ReleaseReceivePacket；read-wait event由session管理，不CloseHandle。AllocateSendPacket得到的内存只有SendPacket后按API归还，失败/stop也要完成明确归属，不能泄漏一个allocation锁住后续ring。stop等待所有borrow归还后再EndSession。原signed DLL放程序同目录，Npcap沿用原安装检测。

参考：[Npcap临时buffer有效期](https://npcap.com/guide/wpcap/pcap_next_ex.html)、[Npcap发送队列](https://npcap.com/guide/npcap-tutorial.html)、[Wintun API](https://git.zx2c4.com/wintun/about/)。不以mock通过冒充安装驱动后通过。

## 测试

批量返回0/n/全长/半packet、EINTR/EAGAIN、RX截断、VLAN/无关tuple、seq32绕回、错误ACK/SACK、kernel checksum offload观测假象、stop while read、退出后无owned fd/borrow。分别计每包syscall、bytes copied、raw drop、capture drop、queue age；同机收益来自这些真实减少，不来自隐藏控制层CPU。
