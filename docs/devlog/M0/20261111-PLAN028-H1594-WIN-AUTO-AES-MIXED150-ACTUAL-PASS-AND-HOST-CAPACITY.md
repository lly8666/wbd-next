# PLAN028 M0 H1594｜Windows自动AES256 + Linux三cipher真正150s全场PASS、容量止步及同宿主路由阻断

2026-11-11，正式原始受测SOURCE `8c0421c33a4fcb9309be3530b3eec0100fc38d9d`，Action [43014043726](https://github.com/lly8666/wbd-next/actions/runs/43014043726) **整体SUCCESS**、Windows2025+WSL2 Job `130502884187` **SUCCESS**。手动下载原始artifact `13852862215` ZIP SHA256 `75db8322f08830f2d5c11a300ab4f7a10bff731862bc68f5fcffcb366164562d`，原始 `h1548-loss0-strict-native-report.json` 自身SHA256 `f3229ac51e5b33d4e36097343e63ad70d65b1920ac3191c6f2bc719286098f3b`。Windows签名Wintun/Npcap原Go TLS443→Rust M4，Windows从服务器受保护TLS获得 `10.66.0.192/32`，Win32 OS IP同值、outer1460→Wintun inner1389有效读回、请求AES256/Rust读回cipher3。Bob、Carol、Dave、Erin四Linux不同/32、ChaCha/AES128/AES256独立参数均真实TLS/Rust/TUN同服。

**150秒真实双向业务**：五客户端真实UDP首次唯一交付上下行两侧计数100%相等（合计**909284次真实UDP到达**、TCP双端累计**1444帧**）；每客户端TCP两端分别有143–147有效帧、无invalid；单个客户端最大活动UDP到达间隔（两端合并）为60.48ms。真实Linux echo在150s结束和Windows Stop后仍存活，Alice唯一签名Wintun/WAL/Rust正常退出，Bob仍完成4次内核UDP回声，余四Linux及共享server正常Stop；server `routed=456217 unrouted=0 backpressure=0 reader_joined=1 queue_*_drops=0`，原始WSL bridge/netem/WAL和Npcap driver清理成功。严格REPORT `PASS_SCOPED_H1581_WIN_AUTO_AES256_LINUX_THREE_CIPHER_TCP_UDP_150S`、兼容REPORT `TRUE_150S_FIVE_CLIENTS_NOT_600S`，**不是**600s。

**诚实容量**：宿主4逻辑vCPU/2暴露物理core，真实outer **双向合计** 20–114秒典型中位151.96Mbps，约120–145秒CPU busy跃至87.3/92.6/92.1%，同窗口outer速率从约150下降至140/123/123Mbps。宿主空闲内存最少10.638GiB；单进程逐worker CPU/RSS、queue age、p99交付时延并未量化，不归因一个Rust锁或断定内核容量已耗尽。遵循验收容量止步：同宿主不再派发额外250–300Mbps/600s更重同族场景；这不是给L2性能发PASS。原测试场景0%丢包+单程200ms，30%场景H1592只验冷TLS，不扩写30%五客户端业务。

**实测后发现小型兼容报表缺陷**：严格`600s_outer_capacity`将H1581真实150s误命名`NOT_RUN_H1565_SHORT_FIRST_FAULT`，其语义虽然NOT_RUN但指错实际场景。最小修复为按H1579冷/ H1581真150/H1574真150/纯probe分别输出精确NOT_RUN，不改已经完成的真实原始报告、兼容`qualification_scope`、产品协议或默认；补H1581源级文本门，后续编译/治理足够，不重复真实150s网络。

**硬门仍在**：H1587双独立Windows客户端同主机路由/WAL所有权真实FAIL，重复两个`0.0.0.0/1`、`128.0.0.0/1`全捕获与共享TLS server /32逃逸路由，不可靠另一个Wintun无损取代已有路由。审查原生 `internal/windowsclient/network_plan.go`、`native_unified_stage_routes_windows.go`、`native_route_backend_windows.go`，native WAL策略明确在任何同key preexisting拒绝，并不支持按来源进程/租约独立Windows路由域；既无既有成熟共享broker也无每实例隔离OS网络compartment可直接复用。放松CAS会毁掉A资源，故**不修改严格fail-closed路由**。此项未关闭，PLAN028仍IN_PROGRESS。L1其他受影响同账号两设备、nearMTU、idle/轮换、L3必要范围仍须以精确原SOURCE论证。

验证落账：[H1594 source-locked evidence](../../evidence/M0/PLAN028-H1594-SOURCE8C042-WIN-AUTO-AES-LINUX-FOUR-REAL-150S-PASS-SCOPED-20261111.json) 和 [统一覆盖表](../../testing/PLAN028_M0_ACCEPTANCE_COVERAGE.md)。历史H1576/H1586 Action FAIL、H1592冷场成功、H1587失败原记录均未改动。不扩展029/030。

```feature-impact
{"kind":"updated","ids":["windows-native-transport"],"reason":"Add exact independent native 150s automatic AES256 + Linux three cipher PASS_SCOPED source and capacity bound; adjust source-scoped reporting metadata only, no product default/protocol changes."}
```
