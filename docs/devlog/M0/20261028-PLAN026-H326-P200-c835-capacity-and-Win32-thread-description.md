# M0 PLAN026 H326｜P200优化发生器后的第二次真实压测及OS线程归属修正（2026-10-28）

精确 Action <https://github.com/lly8666/wbd-next/actions/runs/40653341765>、SOURCE `c8352931e15c954aa2c5de7a31e024af3a7eeb35`：优化Python250Mbps发送器后Linux+Windows双端编译和Rust原生单测PASS，真实签名Npcap/Wintun+Linux raw/TUN启用单程200ms、各方向250Mbit/s真实netem限速及30%随机损，实际应用60秒、双方真实UDP/TCP、Stop和owned清理PASS。**性能门依然CAPACITY_LIMITED，不是250Mbps资格。** Windows发生器实际249.0087Mbps、Linux发生器198.2698Mbps（低于225门）；Windows收到117.3942Mbps、Linux收到108.3575Mbps，首次交付占对端发送的0.59211/0.43515，比只注入30%随机损的0.7还低，需要定位系统栈或产品额外丢包，而非伪称M2已恢复。

真发生器CPU：Windows20.4844 CPU秒，占单核31.514%；Linux61.2975 CPU秒，占单核94.304%，说明Linux Python生产+消费者单核已经受CPU瓶颈。WindowsGo+Rust完整进程51.3906 CPU秒，其中kernel43.5781秒，峰值RSS41967616B，**不能直接解读成Go语言CPU**。LinuxTC实测`eth0` qdisc 338431 drops、IFB qdisc 404583 drops，完整源码锁记录 `docs/evidence/M0/PLAN026-P200-sourcec835-windows-linux-generator-improved-capacity-20261028.json`。

下载Action artifact `m0-wl-full-public-normal-direct` 检查75条真实Windows进程线程采样，`thread_count_sampled`约15，但 **`named_rust_workers=0`**：仅调用Rust `std::thread::Builder::name` 没有让Win32 `GetThreadDescription`读出名称。此批在Rust native TX/RX线程启动各执行**一次**Win32 `SetThreadDescription` 并在Windows单测固定UTF-16名称，不在逐包热路增加任何锁、计时或分配。下一同机Windows源锁功能测若仍观察不到命名线程，就如实标记`NOT_MEASURED`，不捏造语言CPU。

下一步：借新版Win32线程采样分离TX/RX与其他线程，再以真实CPU／mutex等待数据判断是否拆共享owner；Linux高速流量发生器可能需要非Python源才能稳定达到250Mbps，此为测试基建，不应修改产品加密wire或增加盲目worker。

```feature-impact
{"kind":"updated","ids":["normal-off","windows-native-transport"],"reason":"精确登记P200优化发生器SOURCEc835真实双向30%随机丢包仍CAPACITY_LIMITED，修正Windows Rust native worker OS线程可观测性；不声称250Mbps成绩、Go语言CPU分摊或新SOURCE已真实运行。"}
```
