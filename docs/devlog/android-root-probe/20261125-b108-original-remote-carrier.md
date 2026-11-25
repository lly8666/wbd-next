# B108｜原服务端双向业务：CI-only veth/tc/ADB carrier pilot

B107 SOURCE `da7eb919c7762afa33c763aee713fffb51a67c22` [Action 45550257467](https://github.com/lly8666/wbd-next/actions/runs/45550257467) 14 SUCCESS / 0 FAIL / 8 SKIP。Normal group 10/10 [138990610591](https://github.com/lly8666/wbd-next/actions/runs/45550257467/job/138990610591)，Game4 Fixed all 6/6 [138990610561](https://github.com/lly8666/wbd-next/actions/runs/45550257467/job/138990610561)，两个真实hostname bootstrap、三个App默认Resolver、实际TCP SYN/UDP TX、CN/排除物理双向业务、Stop/cleanup PASS。Network [138990610598](https://github.com/lly8666/wbd-next/actions/runs/45550257467/job/138990610598) 原handle onLost、Stop、新handle显式重新连接PASS；native PhysicalScopeInvalid=false，生产RootService READY自动恢复NOT_PROVEN。3/3 guest cleanup。ARM64 hosted [138991062082](https://github.com/lly8666/wbd-next/actions/runs/45550257467/job/138991062082) KVM_NOT_ACCESSIBLE，无真实ARM64 Android guest。

B108不复跑green专项、旧SLIRP/TAP/WiFi-TAP、边界矩阵。针对真实Android远端业务这个最重要缺口，尝试一种与历史emulator carrier不同的CI-only transport：独立Linux原服务端使用临时veth，Android实际ConnectivityManager选中的wlan0/eth0上以精确IPv4 pair/TCP443的tc egress/ingress规则转接到临时veth；两端AF_PACKET relay通过ADB reverse仅传输原完整IPv4/TCP字节，重新构建临时L2头。无虚构SYNACK、TLS/lease、M4 record、修复数据、应用reply，无协议解密、产品新代码、APK新transport、外部服务器或设备操作。它是测试载体，不证明普通emulator SLIRP或物理手机网络能透传。仅在隔离runner/guest，保留原netd其他规则；结束清理精确filter/veth/ADB reverse/进程。若内核不提供veth/clsact/u32/mirred或真实原peer收发未完成，按失败阶段记录，绝不冒称E2E。

两个独立任务并行：
1. Linux真实内核三namespace，原样复用relay源码，普通TCP端点通过双向tc/veth/relay做1MiB逐字节收发，独立确认两边真实TX/RX。非WBD业务或Android证明；只关闭隔离veth上的普通TCP offload以获得完整字节。控制通道两relay同namespace的loopback，不是外部网络。
2. Android x86实际KSU guest+独立同SOURCE Linux原服务端，原正式Java RootClientService启动，真实选中普通App UID，原RAW SYN/SYNACK、真实TLS CA验证及原Admission/lease、M4/UID READY均要求原双方marker；之后普通App TCP/UDP 8+8回显及1MiB每方向字节校验，服务端echo仅绑定其原TUN私有IP。再要求原joined Stop、UID route journal、TUN、RPDB、FIB/NAT/RST cleanup。若前阶段失败，后阶段NOT_RUN。仅Normal/off一条常见路径先证明新载体，不扩大7模式直到可用性明确。旧emulator PCAP/SLIRP收据不作为此路径证据。
本轮只改CI和文档，未改main或生产数据面。历史governance失败保留。新SOURCE待真实Actions；FEC远端恢复、READY自动重连、实体热点及ARM64实际性能仍未证明。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Accept B107 actual ordinary multi/all App and Network loss/reconnect; pilot unchanged original IPv4/TCP carrier for genuine independent Android/Linux peer and ordinary application traffic."}
```
