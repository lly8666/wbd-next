# M0 PLAN029 H2284：旧H2228高速三Runner差异校准与双组三机容量（2026-11-22）

## 核实的最新实验来源
最新主线只是控制面恢复资料；产品代码仍只在Draft PR#68的实验分支 `experiment/m0-029-throughput-arm-fair`。本次控制面事实为精确 SOURCE `8b37f34e2158108ee0aa5a9d7fff462ea2d28a93` [H2284 Action44932436553](https://github.com/lly8666/wbd-next/actions/runs/44932436553) attempt1 **7/7 SUCCESS**，下一研发实验 commit仅证据 `8865be2314cf7c9cfedebccc1f31a995b7789a73`。原H2228旧八流高速证据 `docs/evidence/M0/PLAN029-H2228-THREE-ARM-RELAY-GE200-REAL-TCP-20261120.json`，源2a2f809，2026-11-20真实三 Runner旧Linux x86客户端/ARM中继/Linux x86服务端经独立VXLAN/L3无NAT的BBR 64MiB内核TCP / 8个iperf3流0ms/0%上传848.551、下载861.757Mbps，原WBD完整矩阵FAIL。

## 新旧夹具差异已经实证
新 H2276–H2283 快启动三Runner（真Windows2025 Winsock端、独立ARM relay、另一ARM Linux端），旧基线主要只有4bulk TCP、Win和ARM默认Socket Buffer约128KiB、部分旧case每流最多24MiB，在400ms RTT时测得数Mbps；它不仅与旧8流大内核窗口BBR环境不同，而且多数旧短流尚未覆盖160小TCP P99窗口，无法直接归因WBD。H2282在相同三机固定400ms通过OS socket 8MiB调整，把 A/B两组默认~8Mbps拉至227/340Mbps但P99升高；H2283改2MiB，A/B约145/138Mbps且P99大致保持，说明夹具供应/内核窗口是主要限制之一，不能把旧8Mbps说成Rust端故障。

H2284明确复用旧H2228的 **8 TCP并行容量条件**，在用户指定**两个相同三Runner组**上用Windows Winsock→ARM kernel real TCP连续25秒，每流最大512MiB，双方8MiB的真实OS socket readback，分别测干净Windows→ARM直连、0ms0%经ARM Linux kernel DNAT/SNAT中继、双向+200ms0%经同一中继，保留160小TCP回显/3台整机CPU和中继最热核、真实tailscaled proc CPU、真实内核双方向netem发包（未DROP）、ARM实际接收字节、分组及SOURCE SHA。两组真正direct candidate，全部业务受理成功，原始ZIP完整。
- **A组** 直连1286.230、干净中继680.275、400ms中继492.618 Mbps，P99分别79/250/532ms；在中继0ms阶段保留直连 **52.89%**，未达到完整800Mbps干净双路容量门；中继CPU全核39.99%，最忙核48.03%，tailscaled合计约1.53核。
- **B组** 直连1067.682、干净中继995.493、400ms中继599.637 Mbps，P99 94/94/485ms；在中继0ms阶段保留直连 **93.24%**，组内direct及relay均通过800Mbps门；中继CPU全核49.14%，最忙核57.58%，tailscaled约1.88核。两组每档160/160真实小TCP回显、超过1秒均0，ARM实际接收多个GiB。
- 两组raw真实上行的Windows端CPU最高约81.5% allcore，relay最热核只有58%，不能再笼统说“所有CPU都没上来”。A组中继出现明显额外容量/p99劣化，而B组不出现，**在两组均direct候选的情况下，Tailnet底层网络调度/额外跳数仍有波动**；不能挑B最好值宣布原WBD千兆成绩。B组提供合格的初步底层capacity，而A组保留不合格诊断。没有证据证明旧VXLAN本身快于新内核NAT，因为旧是Linux x86/BBR+64MiB、而新是Windows/ARM/8MiB，架构/负载均不同。
- 项目真实产品优化仍OPEN：H2284并未启动原Go TLS/Rust、Windows Wintun/Npcap或ARM原TUN。已有H2274 Linux ARM原Rust FEC2 on/off同机1/5%候选提高goodput及P99，尚不能代替跨Windows三机验收。下一任务 H2285 专门在同两套独立三Runner以源锁定原Windows Npcap/Wintun→ARM原Go TLS/Rust验证确实跨机的FakeTCP握手、真TUN接收、0/1/5%业务吞吐、每层本机drop、3机CPU/P99及owned Stop。需先验证 Windows原Npcap发向WSL2 vEthernet的 L2帧怎样安全经Linux仅内核转发到远端ARM（不能把Tailscale IP直接假装物理Npcap出口），同时还需原Arm真实AF_PACKET以太wan0与原GoTLS认证；若前置不可达，fail closed，不拿Win裸Winsock冒充产品。之后再做原FEC2 OFF→fixed→OFF或批处理单因素优化，按CPU/吞吐/P99共同判定。

治理：M0 PLAN029仍partial/open；PR#68 Draft；所有历史失败原 SOURCE 保留。完整结构化 H2284 证据在实验分支 `docs/evidence/M0/PLAN029-H2284-DUAL-THREE-RUNNER-EIGHTFLOW-CAPACITY-20261122.json`。
