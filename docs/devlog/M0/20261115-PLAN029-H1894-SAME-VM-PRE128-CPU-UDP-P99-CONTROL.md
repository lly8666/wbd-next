# PLAN029 H1894｜同一原Windows进程两段8s空闲CPU＋UDP小包p99：避免把总负载当128连接增量

- 先收准确证据：H1893/H1892 [签名真实Windows2025/WSL2 Action43680192237](https://github.com/lly8666/wbd-next/actions/runs/43680192237) 128条**原Windows Wintun→Rust NAT→真物理Linux TCP**并行接入，真实Rust `active_peak=128`、同WSA分片1两活跃各64KiB SHA/FIN，126 idle8s，全程Tunnel UDP679/679，owned Stop与WAL PASS。原Go+Rust进程 idle CPU 0.296875/7.156 CPU-s，即单核4.149%（kernel0.203125/user0.09375）。这**不是128条TCP单独占用4.149%**；缺少同VM/同源/同进程/同UDP背景对照。全场UDP小包RTT p99 7.133ms、max gap53.641ms，可能掩盖不同phase。
- H1894只增强**签名测试**，不改原Rust产品调度、WinSock event、QBytes、MTU、背压、线程、驱动或原始TCP路径：同一个Windows原Go+Rust进程／同一代TLS/Wintun owner，既有4MiB物理及Direct测试和原Linux TCP46112 listener完成且真实Tunnel96B UDP sender仍在循环时，取第一段**8s未新建H1892 TCP128 probe** 的`time.monotonic`窗口；接着仍由H1892真Windows kernel bind/connect128条Direct，经8s纯idle和两条同分片64KiB真实SHA/FIN，取第二段8s真实`idle128`窗口；Tunnel UDP不停止也不新开任何额外socket/线程。
- Windows原1Hz `GetProcessTimes`资源文件在**原双owned Stop后**按两个独立单调时间区间取实样，每段至少3条、相同PID，同个原Win32 Go+Rust进程的user/kernel/total CPU-s归一到cpu秒/墙秒，记录pre128和128空闲占单核百分比、差值（允许负数，绝不制造降耗阈值）。前一段可能仍持有原4MiB/TCP32KiB FIN-grace元数据，**不是绝对0个活跃内核TCP，也不是随机化A/B**；只能提供同源顺序phase关联增量，不能直接推为Rust自身成本或driver ISR/DPC CPU。
- 真Windows Kernel Tunnel96B UDP sender在内存中为每个收到对应echo的packet记录单调时间和RTT，在本SOURCE预先拥有的两个Windows控制窗口上分别聚合**真实96B包p99 / 最大interreply gap**，每段至少25个有序实际回复、完整原SHA和`source_sha`，不保存payload或逐包日志；若CPU sample、时间窗或UDP包任何不完整，签名Normal scene必须FAIL，不用全场平均粉饰。只在`[plan029-v3-real-p2-bulk]`+`[plan029-v3-real-tcp128]`+`[plan029-v3-real-tcp128-control]`同时显式的main commit启用、其他普通P2/H1892原貌不动。128次原Rust真实接入及exact同分片、Linux128 accept、真实Tunnel全程679+继续被原签名Oracle要求、双Stop原范围不变。
- 该SOURCE和新的真实A/B**NOT_RUN**。不对P2 1.873x或者P1 V4 vs V3 +9.41% CPU/GiB宣称解决；真实GUI/Game4 CN/IPv6 Socket及D1–D5资源满仍OPEN，029 IN_PROGRESS、030不启动。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1894 adds source-locked test-only matched same Windows process 8s pre128-vs-real128 idle Win32 user/kernel CPU and true per-window Tunnel UDP p99 under one owner, without product path or default changes; pending real CI."}
```
