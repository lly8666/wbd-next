# PLAN029 H1875｜收 H1872 签名真P2，正确性PASS而性能仍OPEN

- [H1872 SOURCE8e59 Action43660566940](https://github.com/lly8666/wbd-next/actions/runs/43660566940) 全部SUCCESS，Windows2025原Go/Npcap签名Wintun/Rust V3 Normal CN与Linux WSL2真TUN原生构件；同一VM顺序普通物理socket与FakeIP Direct无pace TCP 4,194,304字节，双侧一致SHA/半关闭，实际物理47.902ms、Direct133.730ms，额外85.828ms（2.792倍）。负载是4MiB，旧步骤名中的1M属于历史标签，不能据标签覆盖真实JSON。
- 阶段(物理→Direct)：connect 10.753→12.509ms，upload 18.930→58.343ms，first reply 3.250→13.500ms，download 14.871→49.305ms；主要增量上传+39.413ms和下载+34.434ms，不是单一RTT。本次Tunnel UDP覆盖整个TCP生命周期，Windows和Linux真实唯一交付均120/120，Win p99 2.552ms、最长回包空洞49.147ms；两端owned Stop及确定的HyperV/Npcap/WAL恢复PASS。真实外层1460、内层Win/Linux读回1389。
- 本SOURCE H1870已写空TCP listener服务门槛、Owned Vec回程少一次copy、32/轮唤醒合并、每actor 64KiB scratch复用；H1872修旧单测后Win/Linux Rust源码锁定单测、Win Go/Rust构建及实网通过，H1870 Windows测试E0369历史失败保留。H1874治理与目录SUCCESS。
- **性能不升级**：旧H1864 4MiB 物理32.155/Direct131.544ms、4.091x，来自不同VM/时段，不是同机同算法的H1870旧/新SOURCE A/B。P2本轮仍2.792倍、+85.828ms；CPU/GiB、队列年龄、唤醒/空socket syscall次数、128 idle+少量active均NOT_MEASURED。原P1 H1867 CPU/GiB +9.41%继续OPEN，不把Direct listener改动归因于All Tunnel（All没有listener）。
- 下步优先基于可靠WinSock completion/readiness登记与代际回收实现**单owner** Direct TCP连接就绪队列，保留DNS TCP、半关闭、背压、Stop；待完整同SOURCE冻结后一次对比已有前后实现，同VM稳定真实业务/128 idle+少量active、CPU用户/内核分项、p99/队列年龄。不把简单轮询10ms→1ms冒充架构修复。029仍IN_PROGRESS，Game4 CN、GUI真Connect/Stop、真实IPv6 socket与其他D1–D5容量仍OPEN。028不扩矩阵，030未启动。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Collect H1872 real signed P2 and scoped Stop with honest performance OPEN and SOURCE provenance, replacing candidate-only feature summary."}
```
