# PLAN029 H1916｜真实签名H1915首错：32KiB全到Linux但FIN丢失

- [H1915 signed Action43706191185](https://github.com/lly8666/wbd-next/actions/runs/43706191185) SOURCE `1fabca1f1e6353ff81747671df23f3df94324ca0` 的原Windows Go/Rust/Npcap/Wintun→WSL2 Linux功能**FAIL**。原Win应用连接FakeIP、发32768B并SHUT_WR，原Rust TX转发完32768B且queued_copy=0；Linux真实内核收到完整字节却停在`PLAN029_H1906_LINUX_FULL_32K_WAIT_FIN`等待半关闭，Windows20s接收0字节后超时。Rust终结计数event_close=2、relay_progress_no_self_ticket=2、自排队0，符合H1915不再二次读EOF。完整10GiB及其物理基线**没有运行**；驱动/OS清理只报告原有Scoped PASS，不把编译PASS冒充业务PASS。失败Action artifact ID14158891595源锁归档。
- Windows WSAEnumNetworkEvents会消费同批FD_READ/FD_CLOSE，recv短数据不代表已读recv(0)。H1916只记两个独立内核腿的真FD_CLOSE hint，若发生于Connecting阶段也随对应Active generation到Relaying，并对实际刚读出的正长度数据尚无EOF时补**一张有界**就绪票据继续读EOF（如果数据量还多，则只在每次真正数据进展后继续）；读到0即按原FIFO/half-close向物理腿转送FIN，正常无close短读不再自排队。不增加每流线程、轮询、timer、系统路由、WFP或缓冲上限。
- 新Windows真实双内核TCP回环单测覆盖DATA32768+同批FD_CLOSE、有效recv(0)、物理FIN、完整反向echo与双FIN。继续运行Windows128 Socket分片、FD_READ两腿独立与旧短写背压单测；签名Rust终结诊断新增`relay_close_probe_self_ticket`并在原P2 post-Stop类型解析强制小于等于总self_ticket。
- 新H1916生产Rust SOURCE**NOT_RUN**。先跑原32KiB业务Gate，成功后再在**同一Windows VM**先物理TCP、后Direct，分别执行2GiB单向500Mbps和各1.5GiB双向700Mbps合计10GiB真实TCP，两端SHA/FIN，Tunnel96B UDP持续,p99,原进程user/kernel CPU-s/GiB和双owned Stop。源发生变化不得复用H1915失败编译产物；后续仅在完整SUCCESS的本SOURCE允许清单SHA复用。
- PLAN029 P1/P2仍OPEN，GUI/Game4/真IPv6/D1-D5未闭环，不开始PLAN030。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1916 one bounded coalesced FD_CLOSE-correlated EOF continuation repairs exact H1915 signed 32KiB real FIN stall, new native verification pending."}
```
