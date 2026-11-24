# B94｜真实 Android DNS netlink、UID 两种 socket、原冷 ACK

B93 SOURCE `860f78d17944167754aaa8064584d84fc9b02b47` [Action 45422304796](https://github.com/lly8666/wbd-next/actions/runs/45422304796) 12 SUCCESS/9 FAILURE/5 SKIPPED。真实 [RootService 138548313654](https://github.com/lly8666/wbd-next/actions/runs/45422304796/job/138548313654) selected WiFi lost callback、原 Service Stop、恢复手动 START 和 Stop PASS（preauth，原 Go EXIT1 before SYNACK，不冒称 READY joined Stop）。三个 UID 组 real CN 5500 prefixes + peer throw、实际 route get/排除与 Stop 都 PASS；普通 App DatagramSocket sendto EPERM，TUN 无 App packet。七模式 Rust cold MSS 1420、inner 1389/1375/1373/1358、原 Association PASS，TLS deadline，清理 PASS。B93 [物理DNS 138546937577](https://github.com/lly8666/wbd-next/actions/runs/45422304796/job/138546937577) exact rtnetlink UID/netId/ipproto/dport53 ADD/GET/DEL PASS；Android ip help 不支持 ipproto，printer 丢失 ipproto/dport，三系统 DNS 失败、清理 PASS。

B94 仅系统 DNS cold rule transport 改为原 kernel rtnetlink，复用同一 journal/规则语义/NAT/Stop/Restore；IPv4/6精确属性二进制读回和 Host regressions，其他 route/CN batch 不变。CI 修原 server HandleSegment 返回 AckNeeded 时的真实 ACKSegment dispatch（未改协议）；逐阶段原 server admission/owner started/Stop/App TX 独立收据。普通 App Java UDP 与实际 AF_INET UDP 并行组内两种 socket、无 UID 改写，物理 host UDP echo 对照及 TUN 回显、EPERM 只读诊断；不关闭 netd/BPF/SELinux。9专项 guest 并行，已通过的 B93 lifecycle 不重跑。无远端 M4/实际 ARM64手机或性能结论。B94 新 SOURCE 待执行。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Record B93 real Network lifecycle and UID kernel evidence; implement proven Android DNS rule transport and repair original CI cold ACK dispatch."}
```
