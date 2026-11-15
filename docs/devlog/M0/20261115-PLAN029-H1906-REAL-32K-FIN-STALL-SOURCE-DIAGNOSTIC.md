# PLAN029 H1906｜签名长测前暴露的真实32KiB半关闭停顿：只读证据修复

- H1905 [Action43691768429](https://github.com/lly8666/wbd-next/actions/runs/43691768429) source `e821607ac36b5e7ab90ec4265e500ddf0f037d9b`，原Windows2025 Go/签名Npcap/Wintun/Rust V3 Normal CN + WSL2 Linux原物理kernel TCP、driver/ABI/Go/Rust/Linux build全部PASS，但在现有（不是新长量）32KiB FakeIP Direct TCP原应用门槛**FAILED**：Windows Wintun lease socket已connect、sendall 32768B与`shutdown(SHUT_WR)`，20s内`recv`零回显；原Rust单TX `inner_read=32768 outer_write=32768 queued_copy=0 buffered=0 resident=65536`，WSL2 Linux TCP46112真实listener记录accepted正确物理来源，却无最终FIN及回传证明。该真实失败发生于H1903 2GiB物理/Direct long和1.5GiB各双向试验**之前**，不许将10GiB/CPU/UDP长负载标为跑过。行动总体FAIL，历史保留。
- `sendall`/Rust `TcpStream::write` 成功仅表示各自**本机**kernel send queue接受，并不意味着WSL2 Linux应用收到32768B或FIN。之前guest脚本只在完整FIN后打印收到字节，**不能用日志空白推断WSL接收=0**。当前 `PLAN029_H1888_TCP_IO_FINAL` 有两回合、一次无进展，但不能判断FIN实际何时出现在内侧/外侧；区分本地recv(0)/SHUT_WR与远程TCP ACK尤为重要。也不能指控纯crypto/FEC为根因。
- H1906仅给原Linux真实32KiB物理TCP脚本添`PLAN029_H1906_LINUX_FULL_32K_WAIT_FIN`一次原socket真实32KiB读取记录，以及`recv(4096)`原20秒超时时单条`PLAN029_H1906_LINUX_PHYSICAL_TCP_FIN_STALL`：实际bytes、完整bytes才比较SHA256、`TCP_INFO`原Linux内核状态第一字节、`SO_ERROR`、timeout=20、无payload/secret。所有额外socket诊断失败仍重抛原TimeoutError，不替换第一错误；成功原字节/FIN/回显原逻辑完全不改。
- 原Rust `TcpDirectRelay::half_close_state()`仅公开既有四boolean（inner/outer recv EOF、本地physical/inner `shutdown(SHUT_WR)`），主Rust TX仅在已存在的冷`WBD_PLAN029_P2_RELAY_DIAG=1`时累计False→True真实状态转移，Stop输出**唯一** `PLAN029_H1906_TCP_FIN_FINAL` 一行，零perpacket log、零额外WinSock系统调用、零线程/轮询/更大缓冲；既有真实two-kernel-loopback unit测试新增两内核腿双FIN同时SHUT_WR断言。注意这四个数**不是Linux收件/FIN ACK的证据**，必须结合原guest日志判断。
- H1905失败为首错，并非随手加超时或减负载。H1906候选仍**NOT_RUN**；签名原应用先验证32KiB、4MiB、Tunnel UDP，然后长2GiB物理/Direct500Mb/s和双向各1.5GiB共700Mb/s，固定同Go+Rust PID，Stop/原WAL不变。Windows/Linux Rust单测、原Go build、治理与Feature仍需SOURCE-locked收集。P1/P2、Driver ISR/DPC、GUI/Game4 CN/IPv6仍OPEN，PLAN029 IN_PROGRESS。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1906 collect real H1905 original Wintun 32KiB TCP FIN/echo failure before long test; add only failure-read Linux TCP receive/SHA/info and cold Rust local FIN transition evidence, no timeout or data-plane behavior change."}
```
