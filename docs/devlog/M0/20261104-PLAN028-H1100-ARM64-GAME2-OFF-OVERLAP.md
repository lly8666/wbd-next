# PLAN028 H1100 — 原生 ARM64/ARM64 Game2/off 双lane重叠交接

H1099 Governance [41779650591](https://github.com/lly8666/wbd-next/actions/runs/41779650591) SUCCESS，H1087 32B 离线 route-key/标准 TLS 收口与 H1098 Windows 原 Go 六单测/五模式 WAL 均已有源码限定证据。其余七模式真实换lane与 Windows 真实物理 NIC 尚未全部合格。

本次补七模式中尚欠的新入口：**Game2/off**，按照用户指定的 Linux 整任务轮换选 **原生 ARM64 client+server**。仅拓展已有 Game4 native rtnetlink fixture 与真实 TCP 重新组包审计器，不改产品 Go/TLS/Rust/FEC/record/wire。实际源 IPv4 10.25.0.2→.3、OS 物理 MTU1500→1280、共享 TUN 单 reader 和旧/新 Rust group 精确 Stop/交接，要求 A→A+B→B、同安装认证 /32 不变、两代各5个真实 UDP 及新内层 OS MTU readback。Wire gate：2 lane ×2 generation 共4个真实 SYN/ClientHello，SessionID各32B且不重复、ServerHello前无服务端私有载荷、无 WB-R1。与现有 Game4 fixed6 的8 ClientHello 审计共享相同解析算法，而不是改握手或固定IP包数。

独立 `m0-plan028-game2-overlap-arm64.yml` 一次固定 donor Go/Rust 构建、SHA256/ELF核 SOURCE，只跑一个原生 ARM64/ARM64 Game2/off 场景；不刷旧 027A/Game4 高档/性能矩阵。本包 **SOURCE_CANDIDATE，Action/工件未验前不可报 PASS**。下一个完整 Linux 任务切回 x86_64 双端。

H998 在线 MTU 缩窄 FAIL、旧ARM64 Game4FEC Action FAIL、CPU因果未证、远端ICMP未测和 Windows 物理 Npcap 接口切换 NOT_RUN 继续保留。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1100 original native ARM64 two-lane Game2/off true OS path overlap candidate, four genuine TLS ClientHellos, shared reader/Stop and real UDP; Action pending."}
```
