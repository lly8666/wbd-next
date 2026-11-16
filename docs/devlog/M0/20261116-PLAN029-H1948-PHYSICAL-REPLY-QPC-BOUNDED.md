# PLAN029 H1948｜真实 TCP 首到前段：物理 socket 首写、首读与内层回注 QPC

- 继续冻结 H1945 [Action43771212764](https://github.com/lly8666/wbd-next/actions/runs/43771212764) 实测：384/384 同 Windows QPC；FIN-first 应用半关闭→Rust inner.write p99 17.317ms、inner.write→app recv p99 0.476ms；payload-first 分别 15.845ms、0.450ms。Windows 内层写后不是 10–40ms 尾延迟主段，但**前段根因未定**。
- H1947 [Action43777305453](https://github.com/lly8666/wbd-next/actions/runs/43777305453) 同 VM 真实 All/CN/CN/All，每臂业务/Stop PASS、CN4104；Windows Go+Rust CPU/GiB CN +11.942%，B 重复漂移10.17%，P1 性能保护 OPEN，不能再无新实现刷同一测试。
- 本 SOURCE 在原 Rust Windows 内核 TCP **两腿有界 relay** 内，测试签名限定仅记录每条流的**第一次真实 physical TcpStream::write 成功**与**第一次真实 physical TcpStream::read 成功**的 Win32 QPC（立即采样）；保留 H1945 首次内层 write 时间和应用首 recv 时间。未启用场景时 trace `Option=None`，不新增 QPC 系统调用、线程、定时器、阻塞等待、per-flow 日志或另一套 TCP；记录只在 owned Drop 一次性输出，1024 条封顶。
- Python 夹具只在原 H1945 同 VM、两种 Linux 实应用的 SHA/FIN/384+384 TCP 和 owned Stop 后，核验物理 write→read→inner.write 与原 app source-port+QPC 匹配384条。若缺失、频率不一致、顺序倒置、端口重复歧义则判 FAIL。physical write→read **包含真实 Linux 处理、外层网络和内核 WinSock 调度**，不是跨 Windows/Linux 同时钟单程；physical read→inner write 才观察 Rust 就绪/转发开销，前一段长不能直接认定 Linux 或 WAN。
- 新 SOURCE **NOT_RUN**，只请求一次原 4MiB+两顺序各384 TCP、贯穿 Tunnel 96B UDP、原双端 owned Stop 的签名 P2；不重复 H1945/10GiB、不加额外网络工作流。先找首个有效失败边界再修，不把此诊断当首到优化证明。其余029：完整D1–D5、P1 CPU、Game4/GUI、IPv6、padding与资源压力依契约保持 OPEN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1948 signed Win32 first physical TCP write/read QPC adds a bounded new first-byte boundary; pending native, H1945 pre-write latency and H1947 P1 CPU remain OPEN."}
```
