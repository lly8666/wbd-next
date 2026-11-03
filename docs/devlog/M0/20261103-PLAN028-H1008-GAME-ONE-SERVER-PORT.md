# H1008｜PLAN028 单端口 Game2/4 第一段真实产品接线

H1007 `837691d7374edbf74b79c4637d5569c7fea4b8d7`已源锁验证Go protected TLS 21/21 PASS、Linux Go V4 CLI unit+build PASS，证据见 `docs/evidence/M0/PLAN028-H1008-SOURCE837-PROTECTED-MULTIDEVICE-20261103.json`；该结果不是共享Rust TUN或真实自动IPv4在内核数据面的PASS。

本次新增源码改动聚焦 PLAN028 同一个外部服务端口：

- Game2/4客户端的2/4真实独立FakeTCP source-port仍为local-base+i，但全部指向**同一个** `peer-port`。未动TLS、cipher、FEC、PN或稳态wire。
- Game服务端仅打开一个AF_PACKET端口过滤接入口和一个`ServerAssociationTable`；用原真实5元组关联不同SYN与已经established的旧Go FakeTCP association。Server仍按受保护`LaneID`验Game完整lane组，并从真实TLS Detach安装一个Rust GameAdapter/唯一Game TUN reader；不因SYN顺序/公网IP给账号或lane授权。
- 原`ExcludeDetachedData`对每个lane重复SO_ATTACH_FILTER会把前一条BPF替换而导致Go重读已移交的其他lane密文。本次提供`ExcludeDetachedDataSet`一次合并最多4条真实tuple，仅过滤已Detatch且Rust接管的普通DATA，保留新五元组SYN/纯ACK/FIN/RST；原Normal单tuple过滤不变。共享cBPF尾部重用既有经验证的IPv4/TCP长度gate，没有Go逐包扫描或加新wire头。
- 在现有固定SOURCE构建脚本中补共享Game classic-BPF VM测试，并在真实双netns Game2/4应用回环夹具里要求两侧实际single_server_port日志；同一原Go TLS、Rust raw/TUN AppFirstDelivery及owned Stop仍是硬门，不得以虚拟单元测试冒充网络资格。

**边界**：目前Game仅一个*逻辑设备*的2/4 lanes共享一个服务端port；server仍一轮只接一个逻辑业务session，Rust跨设备共享TUN/IP索引分发与七模式A→A+B→B、真实Windows/Linux路由通知尚未接通。现有H998物理MTU在线缩窄FAIL、ARM64 Game4FEC workflow FAIL以及ICMP/CPU未证保留；用户outer MTU默认1460B，不含L2。

此提交后等待新SOURCE真正BPF/native netns Game2/4 Actions，未验暂为IMPLEMENTED_NOT_TESTED。H1007源837验收仅在Go TLS/CLI权限/文件证据内写PASS。Go Native shared server实现不得通过多个owner争读同一个TUN。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient","game-lanes"],"reason":"Exact-source H1007 protected multi-account/auto-lease Go TLS and Linux CLI PASS recorded, plus real Game2/4 single-server-port Go client/server, shared cold listener, bounded kernel detached tuple filter and native fixture candidate added; Rust multi-device shared TUN NOT_RUN."}
```
