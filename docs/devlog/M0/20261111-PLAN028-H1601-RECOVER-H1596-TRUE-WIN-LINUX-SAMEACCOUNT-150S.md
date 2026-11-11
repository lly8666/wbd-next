# PLAN028 M0 H1601｜接上 H1600 完整同账号跨OS验收与范围限定

最新 main `8a31375e36bb6a93860c5579e64b4a39d0b6e346`，Action [43027983611](https://github.com/lly8666/wbd-next/actions/runs/43027983611) **整体 SUCCESS**，原生 Windows2025/WSL2 Job `130550174873` **SUCCESS**；同SOURCE治理 `43027983689` 和治理回归 `43027983768` 均 **SUCCESS**。已下载真正原始 artifact `13861275233` ZIP SHA256 `4a5e88ea353015487a5d2f3249b8b30522d5e3e57fcbd99e76c0cd48df39b61d`，解包重哈希 `h1548-loss0-strict-native-report.json` SHA256 `cb790d21612e4b99725b93fb3cb983b681c7ae48b16e5473ff0bcbdf4e615fcb`。源锁二进制和范围见 [H1601 evidence](../../evidence/M0/PLAN028-H1601-SOURCE8A313-H1596-WIN-LINUX-SAMEACCOUNT-150S-20261111.json)。

**真正支持的结果**：唯一Windows签名Wintun实例 Alice（受保护TLS原Go auto `10.66.0.203/32`、AES256 Rust cipher3、OS /32）和 Linux Bob **同账号不同安装ID**（独立Linux原Go 0600 installation file，受保护auto `10.66.0.130/32`、原生TUN OS readback），同服务端同时在线而地址不碰撞。其余 Carol/Dave/Erin 是独立账号 + AES256/ChaCha/AES128/FEC显式模式。五客户端真内核 UDP 双向唯一交付共 **636494**（双端都一致，未交付数0）、TCP双向每客户端143–150帧（合计客户收发1458）、invalid0，持续真150s。最大活跃UDP交付间隙63ms。Alice Stop后真实Bob Linux UDP再4包，四Linux和共享Rust TUN final Stop全部PASS（server reader_joined1、unrouted0、backpressure0、所有queue drops0），WAL残余空、WSL/netem/Npcap清理成功。

**性能范围**：200ms单程、无loss，业务发生器显式倍率`0.7`（先前`0.6`不合法，原失败Action`43024873684`与错误保留）；六OS应用实际读回均0.7。内核计数的外层**上下行双向合计** 20–121s中位约108.834Mbps（两向各约54Mbps），VM overall CPU busy峰52.7%，可用内存最低10.762GiB，原数据有256/1120B小中包和真实TCP。不等于单客户端内层速度、不是近derived MTU边界、没有产品worker CPU/RSS与p99队列年龄；不是600/1800s或30%五客户端。与旧1.0×约152Mbps、CPU峰92.6%的不同run不能当同VM CPU A/B收益比较。

**失败与范围**：H1598 SOURCE496 `43024873684` 真实认证/OS/早期UDP先通过但发生器0.6非法导致150s失败；H1599 SOURCE798 `43027647645` YAML parenthesis解析失败（业务未跑）；H1600修复 Action成功，不删除原FAIL。用户要求**不跑同一Windows多Wintun**，H1587 `43001721886` 老独立Wintun/WAL全局路由CAS产品失败留历史且作为未支持/未验限制。不能以跨OS同账号成功声称双Wintun OS安全。当前只证明一Win原生Wintun+四Linux TUN真实共存和退出隔离。

已发现测试包型只到1120B，未触及真实Wintun派生inner1389、或Erin较小inner预算；下一步若受影响入口需补短**按各客户端OS实际MTU读回**近边界真应用，不能用Rust公式假设。生命周期轮换/idle的新源代表及Windows L3也未完。Linux ARM64旧同一原Go/Rust部分有两条1800s实网长测（SOURCE1211 Action42738333653/42738333604），仅按未改组件复用，不把旧SOURCE二进制和Windows结果挪到新源。

```feature-impact
{"kind":"updated","ids":["windows-native-transport"],"reason":"Add source-locked genuine 150s same-login Windows+Linux independent auto IP, cipher, actual UDP/TCP and owned Stop, while explicit multi-Wintun OS restriction remains."}
```
