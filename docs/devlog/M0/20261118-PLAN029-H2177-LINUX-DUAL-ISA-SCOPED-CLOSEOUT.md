# PLAN029 H2177｜Linux x86_64 / ARM64 原客户端＋服务端 5×2 最小真网络收口

用户请求：把PLAN029非Windows部分功能在Linux服务端＋客户端分别运行x86_64和ARM64真实相关测试，尽量高效。最终签名SOURCE **`3cc095e38d98fd1a9b2a8f00835b113bc434c9e1`**，[Action44258876671](https://github.com/lly8666/wbd-next/actions/runs/44258876671) **completed SUCCESS**；两个独立Job各自原生托管CPU（非QEMU，非实体ARM板），真正运行 `ubuntu-24.04` x86_64 和 `ubuntu-24.04-arm` aarch64。共 **10/10场`PASS_SCOPED_NATIVE_LINUX_TWO_ENDPOINTS`**。

## 原始事实和工作量

每ISA严格固定main SOURCE `3cc095e`、上游原Go `a7a82db31fe736ffedee330795a3234d358f1984`、原ISA-L `c387163fcbca62701d646149564c550c78a4f985`，**各仅一次编译原Go TLS wbd-v4-client / wbd-v4-server＋libwbd_engine.so**、通过 Go/Rust定向单测与平台本机SHA256验证。各ISA复用同一编译产物，顺序五个独立linux network namespace真实client/server TLS会话，并每场Stop/彻底删除namespace；不重跑历史Windows的Game20/20或loss/1800秒矩阵。两原生Job每架构五个模式实际业务运行总和约43秒（构建另计）：
- Normal 原Go TLS/Rust raw/TUN：双向普通Linux kernel UDP+TCP app echo、双向ICMP、内层MTU/DF真实边界；
- Fixed FEC与Auto FEC：同一原双端内核业务、FEC原Applied与Stop；
- Game2（FEC off）：两独立保护lane、原Rust M4封包/内核复制；双向TCP/UDP与Stop；
- Game4（fixed6）：四独立认证lane、原Game FEC source52 parity offered96 parity真正kernel copied96 **每端每ISA**、双向TCP/UDP、原Rust M4 Stop。

各场外层请求MTU1460、自有新TUN txqlen2048/FQ600Mbps和`disable_ipv6=1`真实读回，**没有修改宿主全局IPv6**。严格验证`auth_rejected=0`，原Game M4分类`offer/slab/record/policy/raw/raw_backpressure/raw_route/raw_mtu`八类严重错误全0；`lane_copy_drop`如实记数，不当成AEAD拒绝：每端 Game2 4个、Game4 28个冗余副本跳过。真实应用收发、首交付、核内copy、Stop/namespace cleanup一一为正证据。

[原生签名证据](../../evidence/M0/PLAN029-H2177-LINUX-X86-ARM64-TWO-ENDPOINT-FIVE-NATIVE-PASS-20261118.json) 绑定Action、真实Job ID `134647080386` aarch64、`134647080671` x86_64，各自 artifact ID `14407256901`/`14407112219`，每个artifact含原build manifest三SHA、五场完整`receipt.json`、真实双向app日志、Game kernel counters、原Stop日志和总结JSON。x86与ARM64产品二进制SHA不同，但**同SOURCE且各架构内部五场完全同一二进制**。新功能卡`linux-raw-tun`仅提升这次Linux两ISA的受限真实功能资格。

## 首个失败不抹除

H2171 `c3fba1e` [44254638755](https://github.com/lly8666/wbd-next/actions/runs/44254638755) 原TCP FIN后getpeername和sudo wrapper READY测试误判；H2172 `68ae680` [44255354198](https://github.com/lly8666/wbd-next/actions/runs/44255354198) 静态ISA字符串顺序测试首红；H2173 `8442d1c` [44255699692](https://github.com/lly8666/wbd-next/actions/runs/44255699692) 非Game FEC selector实际空字符串，不是`off`；H2174 `0302519` [44256427127](https://github.com/lly8666/wbd-next/actions/runs/44256427127) 错把原Game一共享端口443 AF_PACKET listener按2/4 lane各socket等待导致根本不发SYN；H2175 `62431ac` [44257618077](https://github.com/lly8666/wbd-next/actions/runs/44257618077) 首次真Game2业务已通、却误把4个原GameTx冗余copy跳过当auth/OS失败。此次H2176以严谨分类门取代混淆，**旧历史冻结ARM64`rejected=0`测试没有变更，正式原Go/Rust网络产品数据面本次所有提交均未改**。失败记录保留，最新PASS只属于该10场真实SOURCE。

## 出口限定

当前真实本机原生x86和aarch64均是**每架构自己的客户端＋服务端**，没有X86直接连ARM互通；ARM原生hosted不代表物理ARM路由器。不提供WinGUI、Windows Npcap/WFP、Win专属CN/Direct/FakeIP的Linux资格；Linux Windows-only启动填充`tls/flows`本次未接入或测试，AAAA/宿主全局IPv6、物理NIC、多路由、极限延迟/高压/1800秒、CPU/RSS/p99仍NOT_RUN。Linux自有TUN禁IPv6是设备级守卫，不是假装实现IPv6全覆盖。PLAN029/029B完整技术退出仍**OPEN**，030 **NOT_STARTED**。

```feature-impact
{"kind":"updated","ids":["linux-raw-tun"],"reason":"Promote only the exact H2176 signed ten original native Linux x86_64/aarch64 client+server functional sessions with same-source Go/Rust binary hashes, kernel TCP/UDP, FEC6 parity, authenticated Game M4, per-owned-TUN IPv6 and exact Stop; explicitly exclude unrun Linux/Windows/cross-ISA/performance scope."}
```
