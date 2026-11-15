# PLAN029 H1896｜持续真实直连 TCP CPU/GiB 优先，保留现有调度

- 背景：H1892 [签名128条原Wintun TCP Action43680192237](https://github.com/lly8666/wbd-next/actions/runs/43680192237) 126 idle+2 same shard active，双Stop和持续Tunnel小UDP PASS；H1895 [同一原Go+Rust进程8秒空闲对照 Action43682118984](https://github.com/lly8666/wbd-next/actions/runs/43682118984) 前128 3.057% vs 有128 2.402%单核CPU、Tunnel p99分别1.494/1.016ms，两个顺序短窗口并非因果ABBA，不能归因4.15%给128 idle TCP。
- 本SOURCE唯一新增显式签名试验标记 `[plan029-v3-real-p2-bulk] [plan029-v3-real-p2-sustain]`：原4MiB/半关闭/物理比较/Tunnel UDP/Stop功能门槛完整保留；在同一个签名Windows Wintun owner内另用一个Windows内核TCP socket从真实租约10.66.0.2发往CN FakeIP46118，同一个WSL2 Linux物理内核TCP监听真实交付。与ABBA及TCP128测试互斥。纯CI测量夹具，**不改Rust/Go产品数据路径、WSA事件或任何实际转发参数**。
- 同TCP连接两方向各2秒16MiB warmup；其后上传30秒×8MiB/s、下载30秒×8MiB/s，各240MiB有效真实交付。Windows/WSL2均校验SHA和字节数，原Linux确认全部上传才ACK，Windows确认实际完整下载才结束；两端FIN及Windows/WSL2原owned Stop检查不放松。64KiB绝对perf_counter定速，不逐段打印日志；速率保守8MiB/s，发现CPU/生成器拥塞只标诊断，不自动加速。
- Windows只在阶段边界用GetProcessTimes读**原Go+Rust进程PID**，分别记录原进程用户态／内核态CPU秒、秒/GiB、CPU单核百分比、每阶段真实交付及MiB/s。另读一个前置8秒无新TCP而96B Tunnel UDP活跃的同机CPU对照；扣减只作为非因果估计单独存储。Go/Rust分函数、驱动ISR/DPC、Linux guest CPU没有测量，不许冒认。
- 96B真实Tunnel UDP Windows/Linux贯穿约72秒，旧普通3200报文上限不改，仅sustain显式场景使用9000（WSL启动参数显式传env）；整个30s上传及下载分别按同Windows QPC高分辨率钟算至少250包、p99和最大间隔，阶段内取消每128包进度输出。最终原owned Stop之后再核对各240MiB/SHA、CPU/P99、source、源PID、两边真实FIN，才可签发scoped PASS。
- 新五个独立纯Python快测覆盖64KiB块、真实字节/哈希/EOF、微型绝对速率、原进程CPU/GiB维度/估算边界、唯一来源收据和原工作流静态契约。H1896 **NOT_RUN**，签名真实Windows/WSL2与CLI Stop未验收不得升级性能判据。
- 后续三类测量严格分开：1) 本次持续Direct＋固定Tunnel小包；2) H1895已验证的0/128闲置两窗口CPU对照，补反序才能做归因；3)最新纯Tunnel同VM V4/V3 CPU/GiB。先测大成本再只改一个热点；不同VM的4MiB比分不能宣称获益。P1/P2、D1-D5、GUI、Game4 CN、IPv6仍OPEN，PLAN029 IN_PROGRESS，PLAN030未启动。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1896 adds source-locked 30s per direction original Wintun Direct TCP sustained throughput and Go+Rust Win32 process user/kernel CPU/GiB with concurrent per-stage Tunnel UDP p99; no product data-plane modifications."}
```
