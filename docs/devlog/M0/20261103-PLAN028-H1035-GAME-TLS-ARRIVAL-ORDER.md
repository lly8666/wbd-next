# H1035 PLAN028 — Game2/4 TLS 顺序不再由 SYN 到达决定

问题：原 Go Game2/4 服务端先收齐真实 FakeTCP 关联，再按收到的顺序逐个执行 TLS，并把第 i 个连接硬判为 lane i。客户端实际按 lane1→laneN 逐个执行 TLS。不同端口的 SYN 抵达顺序不保证一致：lane4 最先建 TCP 会让双方等待不同 TLS 连接，或者认证后的 lane ID 被误拒。

修复：限于现有单组 2/4 个真实冷 TLS 关联，并行运行相同原 Go 凭据 TLS，每组用一个可取消上下文，错误时先等全部冷任务退出再精确 Stop。只有**保护后的** `LaneID` 决定 Game 原生 Rust/peer MSS 的顺序；先核实完整同账号、同 tunnel、同 epoch、同策略、独立密钥，再改共享 TUN IP/MTU、启动原 M4。独立 n 个 SYN 槽并不等于可同时容纳多个 Game 组，本次不宣称那项已实现。

保留：一个服务器端口、每 lane 独立原 Go TLS 和 Rust AEAD/PN、原 Native GameAdapter、原 M4 Stop、Game4/FEC、原 wire 和 per-client auto lease；无逐包 Go 热路径。

验证：`TestM0V4OriginalTLSGame2And4AuthenticatedColdSet` 增加真实保护 TLS session 打乱顺序并核对身份；`TestPLAN028GameServerProtectedLaneNotSYNPosition` 覆盖任意合法 1..n ID/越界/错误组大小。同源码原 Game2+Game4 Linux netns 真产品测试沿用已有 combined native CI。待 exact SHA 结果，不对多组并存和 Windows 真切网冒称 PASS。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1035 original Go Game2/4 server protected TLS in parallel for arbitrary SYN order, verifying authenticated group and per-lane peer MSS before native Game M4; real grouped modes source tests."}
```
