# PLAN029 H2077｜日常范围真实收口（扩展性能/旧矩阵不冒充 PASS）

**结论：PASS_SCOPED，2026-11-17 用户限定的日常使用范围已完成。** 冻结产品 SOURCE `498a5a61a8e8eff1d8263529457f1523f3b21ff7`，只在原已验证 EXE/Rust DLL/Linux Go+Rust 基础上更正双代测试夹具，fixture SOURCE `d7b3138c93897de7044aaa1ef1c8c70b9d53ba0e`。3 条 Action 独立跑真实 Windows2025 签名 Wintun/Npcap → 原 Go TLS/Rust → WSL2 Linux 原始路由与 kernel TCP/UDP；原 ZIP/report/manifest、服务端认证日志已查，Action + native job 全 SUCCESS。没有把历史 FAIL 改 PASS，也没有假 Applied。

| 独立场景 | Action / artifact | 真实结论 |
|---|---|---|
| 真 WinForms Disconnect→新 Go Child Connect | [44035518047](https://github.com/lly8666/wbd-next/actions/runs/44035518047) / 14306069256 | 两代 OS Applied，外层1460/内层1389，物理源端口41031→41032、B认证Health /32晋级、Direct TCP32KiB半关闭回包/UDP、Tunnel TCP/UDP、owned Stop PASS |
| 服务器域名再次建链 | [44035523669](https://github.com/lly8666/wbd-next/actions/runs/44035523669) / 14306553979 | 两代原物理 UDP TC1→相同endpoint TCP53 A1（各1组），原 TLS SNI 不变；双出口业务及正常 Stop PASS |
| CN TTL2/断开重启第三问 | [44035528778](https://github.com/lly8666/wbd-next/actions/runs/44035528778) / 14306902967 | 三个原物理 DNS 查询首问/2.8s过期/新Go重连，FakeIP三次 `198.18.0.1`；重启 Direct UDP+32KiB TCP、Tunnel TCP/UDP、Stop PASS |

三个 ZIP 都有 `mode_public=PASS_ACTUAL_WINDOWS_LINUX_NATIVE_normal`，`app_duplex=PASS_ACTUAL_TWO_OS_KERNEL_UDP`、`tcp_duplex=PASS_REAL_WINDOWS_TO_LINUX_TUNNEL_TCP`、`stop=PASS_BOTH_OWNED`、两个数字 OS 内层回执 `[1389,1389]`。服务端每场各有一个真实 AF_PACKET listener、2 个物理 SYNACK、2 个 authenticated M4 sessions、每代 scoped Rust Stop、最后单 shared TUN Stop；原生服务端打印 `V4_PUBLIC_NORMAL_SERVER_TUN_PROMOTED_AFTER_CLIENT_AUTH_RX generation=2 verified_client_cold_health=1`。H2072 原 Windows 冷 Health 真 Entry 接线修复已由生产物理路径证明，无放松 TLS、AEAD+unique PN、共享 /32 门。

**旧功能回归**：H2072 影响的原 Normal/off 非二代场 [Action44031316063](https://github.com/lly8666/wbd-next/actions/runs/44031316063) 真实双 OS UDP/TCP 和 owned Stop PASS；Windows Go/Rust、Linux Rust FEC/Normal 组件及 ABI/cross-ABI 编译测试 PASS；原严格单条 MTU 函数仍拒绝多条，H2076 新双代 helper 一/三条、伪造行、错 MTU、CRLF 单测 PASS。Fixed/Auto/Game4 历史原功能不扩跑旧 028 七模式矩阵。

**旧失败保留**：H2070 Action44025145100 为真实 pre-fix B Health FAIL；H2075 Actions44032936928/44034346200/44034352986 在两代已真实 Applied、认证 B Health 通过后，被旧“必须恰好一条 MTU 回执”夹具误拒，仍保留 FAIL。H2076 只改夹具并复用未变产品二进制，三场后续业务验证完整PASS。

**范围限度**：按照029计划在 2026-11-17 的用户修订，交付仅日常 GUI/域名/TTL/单 DNS 不回退/真实 CN/非CN Direct+Tunnel/Stop。原始 D1–D5/P1–P2 全高负载 CPU/GiB、p99、RSS/队列年龄、旧 IPv6 全矩阵、五种资源同时耗尽/强制中断/慢盘等仍保持历史 NOT_RUN/局部旧证据，**不称全场景完结**。M0 只在日常范围收口后停止，不自开PLAN030。

```feature-impact
{"kind":"updated","ids":["windows-native-transport","gui-config-feedback","client-domain-bootstrap","dns-split-ipv6"],"reason":"H2077 3 independent same-product signed native GUI/domain/TTL PASS_SCOPED and original Normal regression; retain old native FAIL and extended NOT_RUN"}
```
