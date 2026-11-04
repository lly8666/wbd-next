# PLAN028 H1093 — native ARM64/ARM64 Game4 FEC6 A→A+B→B

同架构 ARM64 client+server 真 ARM runner [Action 41771260135](https://github.com/lly8666/wbd-next/actions/runs/41771260135) SUCCESS；已解包完整 artifact `13295106610`，按 `fixed-build/manifest.json` 核实 SOURCE `5760dd1c1e77367004614e1fcd44f248f47227b8`、原 Go donor `a7a82db3`、Go1.23.12/Rust1.85.1、原两端Go/Rust SHA256 与 `fixed-kernel-result/assembly.json` 原 Go 装配。不是 QEMU-user，两个 netns 在同一个 native ARM host 上；本轮接替 H1092 的 x86/x86 完整测试任务。

真原 Go TLS+Rust Game4 fixed6 首代5个UDP、OS源IPv4切网后新代5个UDP，Game健康 lane 在受损第一lane时仍送，B TLS/Rust READY **早于** A exact Stop；Rust client/server各一 TUN reader，两代 FEC真实 parity copied>0，同安装合法 /32，外层1460B意图、新物理1280B、内层 TUN OS读回1178B。8个真实 TCP SYN/SYNACK+TLS client SessionID 32B均不同，首段 ClientHello、server首载荷ServerHello，无 WB-R1/37B prelude；记录长度667/127B为当前具体证书/SNI/版本的观察值，绝非固定包长规范。

Go TLS缺key本地失败、错key、错密码、不信任证书均过本 SOURCE focused Go unit。严格限定：**不是**已解密 Finished/证书链并与相同uTLS基线完整比较，也不是 Windows真实网卡/出入口 Npcap重绑定、全七模式物理交接、CPU/p99、远端ICMP、Android PASS；旧H998在线同连接热缩MTU FAIL、旧 ARM64 Game4FEC Action FAIL 按原 SOURCE 保留。

完整脱敏摘要与SHA [H1093证据](../evidence/M0/PLAN028-H1093-SOURCE5760-ARM64-GAME4-OVERLAP-TLS8-20261104.json)。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1093 independent SOURCE5760 true native ARM64 client/server Game4 FEC6 authenticated A→A+B→B, real 5+5 UDP, 1178 MTU, FEC and eight PCAP-reassembled first TLS flights, bounded limits."}
```
