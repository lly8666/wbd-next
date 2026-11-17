# PLAN029B H2113｜H2112 原签名Win2025 Wintun IPv6/IPv4混跑有界PASS

本次以 H2112 SOURCE `417e0e069659ff392d53ce0343c383fee7ae2915` 原 [Action44108913670](https://github.com/lly8666/wbd-next/actions/runs/44108913670) 终结 SUCCESS 及完整可复查原ZIP记录，绝非廉价测试自报。Windows native job134132799214、双端Go/Rust和CI均PASS。原artifact14339823791 ZIP SHA256 `a0ffa8b899dea3e55bb06a599ba110c5e56e30d3ea8adeb20ee3d75c872f5619`、27成员 CRC PASS、报告四个SOURCE均为417e且同源签名/可执行hash读回有效。

Windows 本机使用真实Winsock `AF_INET6` 16次 UDP `sendto(fd73:29b:2026::1)`，其原Go四阶段代际WAL hash、真实系统 IPv4/Wintun ifIndex=30、GUID、IPv6绑定Enabled交叉核对，**本次只创建独立测试拥有的**`fd73:29b:2026::2/128`源和目的`fd73:29b:2026::1/128`路由。原Rust Wintun Stop的首字节IPv6跳包计数=52、joined=true；这个计数**含系统背景IPv6，非16次发包的唯一逐包归因**。发包期间原Windows AF_INET/WSL2 TUN 12个IPv4应用回显全部实际收到；原TLS/OS Applied/双方内核UDP+TCP、内层MTU1389/外层1460、原双方owned Stop/WAL真实PASS。测试源地址及目标路线全部精确清理，回执`PASS_EXACT_TEST_OWNED_IPV6_ADDRESS_ROUTE_ABSENT`。ZIP的test-owned文件`stage=PRE_MUTATION_INTENT`来自cleanup读取写回原Intent，实际发送、OS路由核读及cleanup以独立日志/报告证明；保留这个来源形态，不把该字段假改成发包完成。

验收限定为**原本程序接管的Wintun测试 /128 路径**；不能推广到物理网卡显式绑定、on-link 绕行、全宿主 IPv6 防漏安全。H2105/6 release FAIL、H2107下载HTTP503、H2108脚本错误等前序原FAIL均不改写。本次推进 B3 限域证据和功能卡，不宣告029B整体、B4多代GUI/Game或B5同VM<=10Mbps A/B CPU/GiB/p99通过。M0继续029B，不重开028、030。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H2113 add reviewed exact-source signed real AF_INET6/IPv4 Wintun /128 PASS_SCOPED and global-host limitations; experimental status retained"}
```
