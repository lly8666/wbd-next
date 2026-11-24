# B64｜直接App TCP/53三DNS模式原Go控制与原Rust隧道接线

B63 `c088b1458f79b2c8a3868e193cc17858422fab65` [Dual64 #45312341047](https://github.com/lly8666/wbd-next/actions/runs/45312341047) 11 SUCCESS/4 SKIPPED，真实TCP loopback/双ABI/签名APK/两Linux Oracle通过；治理SUCCESS。实体NOT_RUN。

B64 App新增可选TCP53（默认关、原设置四槽/SAF及B62冷恢复快照）。启用且选原三DNS之一时，在原TLS/Admission/真实/32/Rust M4之后使用原Go DNS wire/真实kernel TCP listener。原单/组/all UID FIB实际出WBD TUN的TCP53由精确UID范围及-o TUN的OUTPUT NAT REDIRECT入本机loopback listener；普通DATA继续原Rust。按完整DNS长度帧与原QNAME，物理走已有Android Network+SO_BINDTODEVICE+source dial；隧道走认证lease/TUN-bound socket及独立19843/9599 root-only源/目的路由，固定1.1.1.1，进入原Rust M4原TCP路径；CN8503两者分流。真实kernel TCP处理连接，最多64稀疏DNS streams，无逐包Go泵、无额外TUN reader。原UID排除及LAN绕过保留。NAT批量iptables-restore --noflush（不可用走精确单规则），私有durable journal与flock、Stop/Restore精确撤规则和join listener，不改系统DNS/netd/global main。若opt-in安装失败不发布READY。

新增真实Host两上游TCP loopback和持久stream三模式测试、原journal命令/readback seam；Android netd代App发出的系统DNS/DoT/DoH未捕获，热点/IPv6未接。实体TCP53、系统行为、性能统一NOT_RUN；本SOURCE编译及CI按实际结果。main/M0与设备不动。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B64直接App TCP53三DNS模式原Go kernel TCP listener、精确UID NAT/独立隧道源路由与原Rust M4/Stop/Restore、四槽SAF接线；系统netd仍未接。"}
```
