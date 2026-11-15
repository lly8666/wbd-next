# PLAN029 H1876｜原TX 16分片 WinSock 事件 + Direct TCP 就绪队列试验

- H1875 [真实签名4MiB](https://github.com/lly8666/wbd-next/actions/runs/43660566940) 新Source真实功能/双owned Stop PASS，但 Direct133.730ms vs 物理47.902ms，2.792倍、+85.828ms，P2性能OPEN；单测/构建PASS不能证明新SOURCE性能，H1867 P1+9.41%另属V4/V3不同后端比较。
- 本改造选用 WinSock FD_ACCEPT/FD_READ/FD_WRITE/FD_CONNECT/FD_CLOSE。固定16个WSA manual事件分片，只有原本已存在 Rust TX 等待它们，加上Stop/Wintun/TX-notify总共19 handle（Windows64上界内）。同一分片事件由第一关联socket通过WSAEnumNetworkEvents原子复位；仅扫描此分片所登记活跃socket，其余事件用NULL参数枚举，不在每个空闲flow做周期WSAPoll。无每flow线程/事件/WFP/Go数据泵。
- TCP连接入就绪队列的识别键为NAT源port与世代generation，端口回收后旧事件token不能服务新连接，最多8个实际flow/次（有界32个含旧token检查）；活跃向量swap_remove更新port索引，保留关闭NAT逆向映射60s宽限。非阻塞connect独立30s截止，到期只令受影响flow入队。若真的读/写取得进展，当前flow按额度让出后再入队；无进展在真实socket事件前不重轮询。已有TCP传输buffer/FIN/窗口/背压不另写协议栈。
- 只有Direct kernel TCP取消10ms持续唤醒；有实际UDP或客户端TCP DNS时继续沿用其有界轮询，避免一次扩大可疑边界。Stop事件优先；系统不额外占Wintun读写者。服务端Tunnel加密/FEC完全不动。
- 需要检验一项可能的WinSock共享事件语义风险：FD_WRITE初次通知、事件原子复位及FD_READ重新使能后活跃少数连接的前进性。若原生TCP回程在高速持续传输或半关闭阶段因丢事件停顿，必须修复或回滚，不以误报PASS覆盖。
- **H1876为SOURCE候选：Windows真实网络、CPU、旧/新同VM P2、128 idle+few active尚NOT_RUN；G4 CN/GUI/IPv6/单DNS压力等029未闭环。** 首轮原生编译与已存在真实P2 Action由source marker自动触发；不再单独dispatch同一试验。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1876 16 fixed WinSock event shards integrated into original Rust TX ready-flow dispatch, preserving exact owner constraints without asserting performance until signed source-locked tests."}
```
