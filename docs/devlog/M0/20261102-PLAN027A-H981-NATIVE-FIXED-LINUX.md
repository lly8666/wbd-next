# PLAN027A H981｜每条原生Actions必须用真实数值证明Fixed 14B

H980 对正式Windows Rust Native V4原Go入口修复旧FEC1 56B误扣并修正双文件精确manifest blob；新源码唯一Windows/Linux产品编译来自 [41494436902](https://github.com/lly8666/wbd-next/actions/runs/41494436902)。H981仅新增测试代码/独立工作流，不改产品；该run必须最终SUCCESS并存在完整EXE/DLL/Linux product工件，方能dispatch五个各自单模式real Npcap/Wintun+WSL2场景（Fixed1460、Fixed1500、Normal1460、Auto1460、Game4FEC1460），每个仍复用H980签名二进制与源SHA，跳过编译。Fixed的硬门不看Action是否绿色，而要求原始发SYN和SYN-ACK中实际MSS字节、对端真实解析MSS、两端物理约束、双向record offer/协商wire、Windows Wintun和Linux TUN OS回读及真实业务、Stop；无其他物理限制Fixed1460=1375、Fixed1500=1415，不让旧1333假冒成功。

独立ARM64 Linux原GoTLS/Rust客户端与服务端两个真的netns，**只编译一次这一CPU架构**，共测Normal1460、Fixed1460、Auto1460、Fixed1500、非对称Fixed client1500/server1280。每次同一二进制真实TCP选项、方向化peer MSS、Rust record、`ip -j` TUN、DF边界ping、应用双向业务和Stop，精确源artifact归档。新结果未运行前均NOT_RUN，保留旧green Fixed1333语义FAIL及H979廉价装配FAIL，不重跑高负载矩阵。外层默认1460、显式最大1500。

```feature-impact
{"kind":"none","ids":[],"reason":"Source-scoped native qualification harness, one-shot prebuilt Windows replay and independent current-source ARM64 genuine Linux client/server; no product code or feature result promotion."}
```
