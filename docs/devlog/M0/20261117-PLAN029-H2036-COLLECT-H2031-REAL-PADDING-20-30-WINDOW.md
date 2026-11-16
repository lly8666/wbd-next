# PLAN029 H2036｜收齐 H2031 20–30条/2–3秒新策略真物理密文抓包证据

- H2031 SOURCE `b76240bedb04237780bd13377bfe7aae38785018` [原生Action43901130216](https://github.com/lly8666/wbd-next/actions/runs/43901130216) **SUCCESS**，Windows 2025原Go TLS/Rust M1/签名Npcap/Wintun vs原WSL2 Linux真实内核应用：original Rust/NPF接纳31条record共6579B；原物理eth0 tcpdump记录43个出站TCP payload segment，其中41个完整TLS外观加密record，71..589B、36种长度、跨度518B；最大IPv4 L3包707B小于该SOURCE所选1400B外层MTU。真实Windows/Linux UDP与TCP业务双向及双方owned Stop **PASS**，raw pcap删除且不入库。
- 同SOURCE产品源码的`TunnelStartupPadding`按用户最新规则：每新Tunnel TCP/UDP流随机选择**20..30条**、**2000..3000ms**两个截止条件（先达到停），每条可提议0..min(500B,当次真实外层room)，包括无room的有效record也计入条数/窗口；**不恢复每流2KiB或10%累计预算**、默认off，Direct路径不提议。这些精确策略/PRNG/总额零预算由Rust组件单测约束。
- **证据边界**：物理链路的加密record绝不能仅凭长度直接反推每条padding随机字节数，31条NPF记录不是31条同一flow，更不能用总6579B冒充填充总字节。真实TCP报文尺寸变化与MTU+业务/Stop充分验证链路生效，而逐条20..30、2..3秒的时窗资格靠源码/单测；不伪称抓包逆向出随机窗口。
- 该类明显功能已PASS_SCOPED，不再反复跑同族场景；H2035真正Game4 CN物理DNS ifindex修复原生仍按独立SOURCE在途，PLAN029整体未结项，共享CDN同IP双域名相反出口NOT_REQUIRED。
```feature-impact
{"kind":"updated","ids":["startup-flow-padding"],"reason":"H2036 records original H2031 true Windows Npcap/WSL2 eth0 encrypted M1 record-length/MTU and UDP/TCP/owned Stop PASS for 20–30-record 2–3s bounded random padding; no product edits."}
```
