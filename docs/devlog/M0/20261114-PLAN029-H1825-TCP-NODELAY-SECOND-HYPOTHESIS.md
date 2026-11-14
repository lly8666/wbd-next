# PLAN029 H1825｜H1823 64KiB中继假设实测未解释慢路径；只测第二个独立TCP机制

- 收完 [H1823真签名Action43577224581](https://github.com/lly8666/wbd-next/actions/runs/43577224581)，其SOURCE=`db6c523d1b0b76f4adbffef88bd14fec0043c816`，V3 DLL符号真实加载、Go/Rust同源码、签名NPF+Wintun、WSL2/TUN全通过；Normal实网真实1MiB SHA256匹配、半关闭、120/120 Tunnel UDP、两端owned Stop全PASS。
- **量化否定第一假设**：H1820原4KiB上限物理312ms、Direct6485ms；H1823有界64KiB物理281ms、Direct6141ms。不是足以支持瓶颈已消失的改善，慢路径仍约21.85倍；不能将此说成加速交付。完整结果 `docs/evidence/M0/PLAN029-H1825-H1823-SIGNED-P2-64K-NEGATIVE-20261114.json`。
- 第二个、不同且可证伪的机制：Windows本地Wintun→kernel listener→物理TCP形成两个独立TCP ACK clocks；中继转交的细碎写可能因两端默认Nagle与delayed ACK相互等待。现行`TcpDirectRelay::with_budget`只设nonblocking而未对两个**自己持有的**socket设置`TCP_NODELAY`。本H1825仅在Relay构建成功时对inner/outer各设一次`set_nodelay(true)`，失败关闭该Direct flow；绝不更改Tunnel的任何socket，也不新开逐flow线程、丢掉背压或逐包查询OS。新测试在loopback动态端口验证两个relay owned socket标志而不影响两端应用socket。
- 复用已有一次`[plan029-v3-real-p2-rebuild]`原生网络场景，冻结新SOURCE后与H1823同样的真实物理基线、1MiB Direct及Tunnel小UDP比较，不扩压力矩阵。**当前新SOURCE编译、真实P2与CPU证据为NOT_RUN**。若依然差，停止该同族重复调参：保持性能OPEN，按§3B原则转向有界每腿/内核ACK时序或首个等待点证据，不刷种子。Game4 CN、GUI实际Connect/Stop、D4 IPv6、P1 +7.42% 仍未闭合。

```feature-impact
{"kind":"none","ids":[],"reason":"One-time TCP_NODELAY on two owned Rust Direct relay sockets only, with test; no public protocol/schema/feature entitlement change. New P2 native performance outcome pending."}
```
