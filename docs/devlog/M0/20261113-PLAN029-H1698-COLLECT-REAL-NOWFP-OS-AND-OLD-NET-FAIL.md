# PLAN029 H1698｜真实无旧WFP四阶段 Win32 PASS，保留旧网络首错

- 收真实 [H1697 Action 43342274385](https://github.com/lly8666/wbd-next/actions/runs/43342274385) Windows2025 SOURCE adb0ae78f5e28211a65d565b66d64e59cd7c8087，官方Wintun 0.14.1 SHA/签名核对、原Go exact assembly。原始[artifact 14000591536](https://github.com/lly8666/wbd-next/actions/runs/43342274385/artifacts/14000591536) ZIP sha256 2c37e54956d7be09470148853ac9feb1f11493a93925d9840db8f37b8129e407。JSON经独立读取：apply RETURNED_OK，applied PASS_INDEPENDENT_LIVE_V2_FOUR_STAGE_READBACK，cleanup PASS_EXACT_OWNED_FOUR_STAGE_STOP_NO_OLD_WFP，old_wfp_guard NOT_CREATED。动态物理ifindex14/source10.1.0.71/下一跳10.1.0.1，当前进程签名Wintun ifindex19，精确owned route_keys=4。一次真实Win32 lease、MTU、单DNS、server/32+两/1+DNS/32路由全部独立读回，逆序Stop后OS检查无残留，parent/child WAL均消失。
- **这是真实OS Win32接口资格，不是产品双出口**：仅在本测试临时解除 assemblyOnly，正式 N4PrepareRealWindowsProduct 依旧未允许未连接Rust DNS/Direct时假称Ready。实际 Wintun packet IO、普通 DNS53 Dispatcher、FakeIP、Rust物理TCP/UDP和GUI未在此Action内执行；无旧WFP对象新增。以后正式Ready要在同generation收到真实native owner/应用与OS收据，不靠历史绿票。
- 同时收 [H1696 native two-OS Action43340809026](https://github.com/lly8666/wbd-next/actions/runs/43340809026)：原正常公有产品场景 FAIL，在 Windows CLI Ready 前退出，首个明显错误仍是旧 windowsclient: crash-persistent native DNS and IPv6 guard required，Normal应用数据、性能和029分流均未运行。该旧执行路径与本次 **测试专用 no-WFP v2 正例并存**，不得将任何一方改写或用 Action 绿色盖住旧失败。
- H1694 A/B/C 对照已证本机Windows内核TCP在精确owned Defender Allow下真实SYN/Accept/DATA/反向FIN可行；故只选内核接入。下一步须将其以少量owned监听资源接入正式Rust分流，解决DNS和FakeIP、配置GUI与padding，再验D1–D5/P1–P2。029继续IN_PROGRESS，不重跑028全矩阵或自动030。

```feature-impact
{"kind":"updated","ids":["windows-network-wal"],"reason":"Collect exact SOURCE signed Wintun real four Win32 stage no-old-WFP Apply/OS readback/owned Stop PASS and preserve separate legacy public two-OS Ready failure."}
```
