# PLAN029 H1702｜实际 WinSock IP_UNICAST_IF/物理源IPv4绑定局部回环验收入口

- H1701 SOURCE 37042af626f8131e5ca7a552909946e2de117735 在 [M0-WIN-LINUX43348306465](https://github.com/lly8666/wbd-next/actions/runs/43348306465) 的两项 Rust eligible-library job 中 Windows 306/0、Linux281/0 PASS；新 fragment 容量原子检查/到期拒绝/缓存ID冲突均真实执行。 [Native functional43348306514](https://github.com/lly8666/wbd-next/actions/runs/43348306514) 构建与既有样本PASS。以上**无新的实际 Direct UDP socket**。H1701 Governance成功，Feature catalog 因devlog声明同时更新两卡而只改一张失败；本批将 dns-split-ipv6 和 windows-native-transport 同时改动，status/source/evidence retained，后者仍不超过16KiB。
- 追加真实Windows socket（非Wintun）独立场景：从当前Windows2025默认IPv4路由动态选择Preferred物理 IPv4 与ifindex，测试Rust `PhysicalUdpSocket::open` 真的调用Windows WinSock `setsockopt(IP_UNICAST_IF)` 及 `getsockopt` 读回，然后用绑定同一当前物理IPv4的**本机UDP listener**做随机端口payload+reverse，检查源地址/端口与字节；DROP释放双方socket，无外部DNS、WFP、Defender、系统路由或磁盘WAL写入。新 `m0-plan029-h1702-physical-udp-bound-socket.yml` 单Action/单场景并要求源锁cargo package测试、真实marker和receipt。
- **可证边界**：此自环试验只证真实WinSock绑定和本地内核UDP收发，决不能算走出物理网卡、Wintun原业务Direct UDP、Direct/Tunnel两出口或端到端DNS；不触碰真实用户连接。后续在一个Rust NativeOwner Wintun RX/TX使用此socket并以真实WSL/LAN远端回包确认D2。
- H1694签名Wintun A/B/C 控制Defender Allow 内核TCP/UDP入站与完整TCP握手，H1697四阶段无旧WFP Win32 Apply/Stop都已有原Action PASS；新代码未将这些绿灯继承为029产品。028旧范围不重跑，030未开始。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6","windows-native-transport"],"reason":"Collect H1701 source-locked Windows/Linux Rust library PASS; add isolated real NIC IP_UNICAST_IF nonblocking bound UDP same-host echo capability test and correct feature card declarations."}
```
