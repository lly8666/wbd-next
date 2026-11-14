# PLAN029 H1819｜独立 P1 复用成品，与P2并行，但同VM A/B不并发

- 新SOURCE只改P1 scenario静态校验、cursor/devlog，无生产 Rust/Go/ABI/MTU/WFP变更。Action H1818 P2已通过 cheap（当时native在途），其原 `c262636c81d688e8df8e844b668bbcc57957425d` Windows原Go EXE＋Rust ISA-L DLL以及Linux原Go+Rust server source/hash验证分支此时已经接线。当前H1819消息`[plan029-v3-real-p1-tunnel-ab] [plan029-v3-real-p1-reuse]`，同一H1814成品但另一个Windows2025独立runner。 
- P1 Action内部先A旧V4真正纯Tunnel50Mbps双向、25ms/0%、60s、owned Stop，再B新Rust V3/all纯Tunnel相同量/同一个源SHA产品、owned Stop；不是两组同时抢网卡。同Windows原Go+Rust进程CPU/实际交付GiB、真实单端UDP RTT p99/最长间隔，非跨OS单向p99、不隔离分流算法因果。
- 这次专门加断言场景是中等负载，96/1200B，各自Packet权重和100，不能被旧200/500Mbps或重丢包矩阵替换。未出实际Action结果前P1仍NOT_RUN。P2是真实物理TCP vs Rust Direct大TCP＋小Tunnel UDP，二者结论必须独立。
```feature-impact
{"kind":"none","ids":[],"reason":"Trigger one source-locked independent P1 replay through previously verified native artifact reuse, with moderate scenario static checks; no product data-plane changes."}
```
