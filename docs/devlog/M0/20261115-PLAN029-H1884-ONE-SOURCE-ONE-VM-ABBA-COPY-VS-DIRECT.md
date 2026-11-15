# PLAN029 H1884｜同二进制、同 Windows VM、同 Wintun owner 的四次真实 TCP A–B–B–A

- 先收源H1882：[签名Windows2025/WSL2真4MiB Action43667025249](https://github.com/lly8666/wbd-next/actions/runs/43667025249)：物理47.233、Direct115.862ms(2.453x)、Tunnel UDP120/120，p99 2.324ms、双owned StopPASS，后端FIFO和半关闭正常。但上一H1877 2.787x来自不同VM/时段，**不能宣称数据直送已因果降耗**。
- 本SOURCE将Rust单flow旧复制作为单个TcpDirectRelay的显式测试参数：生产`TcpDirectRelay::new/with_budget`永久使用新fast_forward=true，旧复制只在`m0_v4_probe`被构建且`GITHUB_ACTIONS=true`、`WBD_PLAN029_NATIVE_V3_TRIAL=1`、`WBD_PLAN029_P2_MIXED_SCENE=1`、`WBD_PLAN029_P2_ABBA_SCENE=1`共同满足时允许，且只在独立的P2预留目标TCP端口46116分配四个有世代的Direct NAT flow，次序copy→bypass→bypass→copy。首个H1760功能32KiB探针仍使用46112，不改变路由/DNS/端口策略。没有给正式用户配置添加新开关，也不保留一个全局热更新状态。
- 真实Windows/WSL2负载：一条同VM物理TCP4MiB baseline、接续四条独立的FakeIP Direct TCP各4MiB、同一个Linux物理核 TCP监听接收**五次**完整SHA/FIN、原Windows应用四次真实受控收发、同一Tunnel UDP持续120/120覆盖第一至第四条Direct流，全局原Client/Server Stop恢复所有owned设置。每次 Direct 的耗时、连接/上传/等待/回传、源lease、FakeIP/应用NODELAY、SHA和半关闭单独保留；取首尾两次A平均与中间两次B平均，提供B−A和B/A但不硬编码性能门限。单VM/source/binary/cold policy可归因于两种**同代码路径模式**；不是严格不同Git commit的二进制对比，也不是驱动CPU归因。
- Rust单线程actor仅在四个测试port接受真实原Wintun SYN后打`PLAN029_H1884_ABBA_ADMITTED`四条非敏感日志，最终原Go-owned Stop后再次读取这四个确实出自Rust原生日志的ordinal/mode，不准仅靠Python给4个试验写A/B标签。原feature/ABI外全保持16个WSA共享分片、single Rust TX、64KiB每向queue、8MiB global resident预算、短写/阻塞队列和半关闭，A/B不从Linux应用读原始客户端密钥。
- 新源码Windows/Linux Rust组件和签名真实ABBA都**NOT_RUN**，异常留首错，不将假设收益升级P1/P2。真正的P1 CPU/GiB +9.41%（V4/V3不同后端）另行；Win128 real Wintun idle+few active、GUI/Game4 CN/IPv6 socket、DNS容量仍未闭环，PLAN029 IN_PROGRESS，PLAN030不启动。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1884 explicit private-probe source-locked same-Windows-VM original-Wintun 4MiB real Direct TCP copy/bypass A-B-B-A experiment and verified per-flow admission; no ordinary product switch or performance promotion before signed tests."}
```
