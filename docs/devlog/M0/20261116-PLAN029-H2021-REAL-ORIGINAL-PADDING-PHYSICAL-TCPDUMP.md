# PLAN029 H2021｜真实eth0 tcpdump验 Normal Tunnel逐record 0..500B/仅MTU

- SOURCE独立原Normal `[plan029-v3-real-tunnel] [plan029-v3-real-startup-pad]` 单场，不同于同时在途的Game4 CN H2020。原Go TLS→Rust M1/NPF→原Linux Kernel TUN真实TCP/UDP双向+owned Stop，不换协议、不加额外发包器。
- 在真正Windows NPF进入前启动原WSL2 eth0 `tcpdump`（短期bounded PID）, 截取Windows物理source→真实Linux peer TCP443，不读解密内容。下线后Python一次检查真实以太网IPv4/TCP payload的`17 03 03`格式、明确record length、实际L3总长≤outer MTU、至少5条、3个不同长度且跨度≥50B；所有原始pcap在finally删除，报告只保留计数/大小分布。
- 原Rust原NPF凭真实`send_batch`被kernel接纳prefix生成padding bytes/records回执，和原应用TCP+UDP、Stop一起交叉确认。**单个密文包无法反推具体填充字节，不能将物理长度差直接当明文padding**；报告保留准确能力边界。无流预算新策略的随机0和500端点已由H2016组件确认，但不宣称实网随机恰好抽到500。
- 真实Action PASS之前此批NOT_RUN。H1799旧256/2KiB下16条50B为历史通过，不冒充本版。
```feature-impact
{"kind":"none","ids":[],"reason":"H2021 adds real eth0 tcpdump strict ciphertext length/MTU and original accepted M1 pad cross-check to existing one Normal Tunnel true two-OS and owned Stop scene; no product code."}
```
