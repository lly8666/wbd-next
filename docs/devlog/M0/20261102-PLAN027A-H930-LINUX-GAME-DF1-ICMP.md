# PLAN027A H930｜现有 Linux Game TUN owner 的 DF1 本地 ICMP

H929 `6af3e6ed2003965e214b5947091ce83492f6011d` Rust platform/native-functional/g2 与治理单元/编译已 PASS，真实 native MTU/端到端 DF 未运行。

沿当前唯一 `ScopedTunSink` 真实 owned Linux fd，在 cold start 用 socket `SIOCGIFADDR` 读取**实际已配置 TUN 本地 IPv4**（不从外层 carrier IP/目的地址推测）。仅当 Linux OS 原本的 MTU/EMSGSIZE 未在 TUN 前拒绝 DF=1 大包且该包完整合法到达现有 Game TX worker，调用共享 RFC1191 纯 encoder 并经这个同一 TUN kernel writer 写本地 ICMP Type3/Code4；含原IPv4头+8B、下跳MTU、校验和；禁止错误回错误/多播/非首片。最多20次/秒，未获 OS IP 或额度拒绝只计单包、不得 Stop/复用原 PN/密文。原速率业务不查询 OS，不重写正常链路。

新增单 worker exception 计数：`df0_ip_fragments/icmp3_code4_kernel_sent/icmp3_code4_rejected`；`kernel_sent` 不声称应用交付。Windows/Game/FEC 的 OS-qualified PMTU、两端模式边界、弱网和 p99 都仍 NOT_RUN；Game 自身网关 TUN 地址必须在真实 Linux VM 证明。

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"Wire RFC1191 local DF1 Type3/Code4 through original Linux Game scoped TUN fd with cold OS-owned IPv4 address, bounded 20/s credit and kernel write success accounting; preserve existing Game/FEC owner and Stop."}
```
