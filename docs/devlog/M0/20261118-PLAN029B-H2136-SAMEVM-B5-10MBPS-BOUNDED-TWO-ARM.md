# PLAN029B H2136｜B5 10Mbps 同 VM 实际 A/B 负载与CPU/p99 有界场景

B4 [44198794225](https://github.com/lly8666/wbd-next/actions/runs/44198794225) 与 Game4 [44197717052](https://github.com/lly8666/wbd-next/actions/runs/44197717052) 原真实功能和 owned Stop 已在各自签名原生 Action SUCCESS；本次**仅新派一个B5独立场景**，不重跑旧029 B0–B4，不添加Go逐包/性能探针，不改Rust热路径、FEC/repair/wire。

在**同一Windows runner VM、同一 SOURCE 和 EXE/DLL/WSL2二进制、顺序而非同时**两腿 A(split-enable=false,all)→B(split-enable=true,all)，Rust V3公共 DNS/bootstrap 在两档均保留（无旧V2代替），两档`--dns.direct`/`--dns.tunnel`/FEC off/startup padding off/outer repair off/MTU1460同值。每方向原生 WinTun/TUN 10Mbps、原Linux内核NetEm 25ms/loss0、60s，真实原 Windows/Linux app 生产/独立收包；每腿原Go/Rust owned Stop+WAL、source/binary sha + 1Hz Win32进程 CPU user/kernel、峰RSS、按**实际首达GiB**归一化 CPU、Windows/Linux UDP真实回声p99及最长 gap；缺任一拒绝/FAIL。纯功能 TCP仍双向真内核回显，**小 TCP p99 NOT_RUN**。CPU或p99单对>5%只标调查，不单次宣称持续退化或百分比优化；非Driver/WSL CPU。局部 zip只保留必要源锁摘要。

```feature-impact
{"kind":"none","ids":[],"reason":"H2136 adds bounded test-only Windows/WSL2 same-VM two-arm original client benchmark and static CI selection. No product Go/Rust/GUI semantics, source ABI, or hot data path changed."}
```
