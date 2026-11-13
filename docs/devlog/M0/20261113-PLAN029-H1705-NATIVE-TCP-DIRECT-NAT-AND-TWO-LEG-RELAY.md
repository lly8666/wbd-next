# PLAN029 H1705｜H1704独立Linux真实UDP回程PASS；选定内核TCP唯一后端NAT+两腿中继

[H1704 Action 43354904887](https://github.com/lly8666/wbd-next/actions/runs/43354904887) SOURCE `abcdb72af96f7ae6b5073e1cd6086653ca920aa8` SUCCESS。真Windows app从198.18.87.77:58054发Fake目标198.18.87.88，经签名Wintun唯一Rust RX→physically-bound UDP 172.19.160.1:58055 ifindex22→独立Ubuntu WSL2 Linux 172.19.166.239:46098→31B逆回→Rust 59B IPv4/UDP回Wintun→原app真实收到。精确owned一条HyperV UDP规则Stop卸除。只是显式m0_v4_probe测试ABI，独立Linux内核但同Windows宿主vEthernet，非物理互联网或正式Normal/Game4产品。

`v4_client_direct_tcp_nat.rs` 做**Direct TCP-only** SYN四元组重写：一个合成peer4 /32 owned路由和一个本机Windows内核listener，按代际proxy port绑定原目标，反向SYNACK改回应用可见原IP/FakeIP及端口。RFC1624增量TCP checksum、原IPv4 header checksum；新流只有SYN能申请，小输出/满额先拒绝，未知反向不采纳；普通Tunnel TCP不终止、不套代理栈。相应纯测试覆盖真实校验和、逆流和quota。

`windows_direct_tcp.rs` 采用原生WinSock物理source IPv4 bind＋`IP_UNICAST_IF`主机序GET验证＋非阻塞TCP connect，一个Rust `TcpDirectRelay` 两腿按需小VecDeque，单次每腿上限4KiB、每方向最多16KiB排队、半关闭，零per-flow线程。**这只是已写代码，尚未接入真实NativeOwner/统一Wintun数据面**，整体64MiB及WSAPoll/IOCP readiness仍须装配；下一阶段一台签名Windows+独立WSL Linux跑真正 app SYN→内核listener→物理TCP→逆回→owned Stop，不能从H1694旧本机SYN推断已PASS。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6","windows-native-transport"],"reason":"Collect exact H1704 real independent Linux Wintun/Rust UDP reverse PASS and stage one Direct-only Windows kernel TCP NAT and bound asynchronous physical socket relay without claiming product Ready."}
```
