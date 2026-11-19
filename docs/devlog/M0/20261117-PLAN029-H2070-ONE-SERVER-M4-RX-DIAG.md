# H2070｜服务端第二原生 RAW socket 一次性只读分层观测

H2067 **同一编译产品 SOURCE** `2fca1a93b4f9f7d3e7c5985adc356ade13332e86` 三条真实独立 Action GUI [44022456867](https://github.com/lly8666/wbd-next/actions/runs/44022456867)、域名 [44023823956](https://github.com/lly8666/wbd-next/actions/runs/44023823956)、TTL [44023829996](https://github.com/lly8666/wbd-next/actions/runs/44023829996) 原 ZIP 均为**失败**。第一代 GUI OS Applied 1460/1389、Stop PASS；第二代 41032 SYNACK/原 TLS 均 PASS，物理 TCP 数据在 WSL2 eth0 可见。Windows Rust M4 原控制发送从 H2066 的缺席改善为可见复制（B TXCopied 246/240/237，B 控制 wire bytes 295/298/280），却 **B RXDelivered=0**、Linux 同一 `10.66.0.2/32` 第二代仍 `V4_PUBLIC_MULTI_SERVER_B_CLIENT_UNPROVEN`，所以 `H2067 仅补冷 Health 足够` 这一假设被新实网否定，不能报 PASS。域名场二代真实物理 DNS TC→同 TCP53 已见；TTL2 首次和到期后二次原 Windows DNS FakeIP `198.18.0.1` 已见，第三问因 M4 阻塞仍 NOT_RUN。

H2070 不重新编译**任何**产品 DLL/EXE/SO、不改服务端协议/守卫/WFP/BPF、不增加测试矩阵；使用 H2067 归档 Action44022456867 的 exact manifest+hash，通过唯一一次真实 GUI normal Disconnect→Connect Action 触发已有原 Rust `WBD_PLAN028_EXTERNAL_STAGE_DIAG=1` 只读每500ms per-client-port 的 Linux RX 分层 counters（`kernel_raw_observed`、`tuple_candidates`、`rx_err`、`tun_delivered`、`raw_socket_readable`），与同一 Action 的 tcp443 eth0 pcap/客户机 Npcap 41032 对齐。诊断不复制密钥/载荷，不把读写异常当成功，不发特权规则，也不绕过原认证5秒候选门槛。协调 push 只 dispatch **一条**，无第四条 native。先判明 B 内核 RAW socket 不见包，还是 exact tuple/checksum/AEAD/PN 丢弃；未取得该证据前不猜修产品。

```feature-impact
{"kind":"none","reason":"H2070 only source-locked test harness opt-in read-only RAW RX diagnostic, no product or feature semantics changed"}
```
