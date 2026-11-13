# PLAN029 H1697｜H1696 SOURCE纯夹具PASS，独立签名Win32四阶段OS验收

- H1696 [Action43340808979](https://github.com/lly8666/wbd-next/actions/runs/43340808979) SOURCE c6520506837a0c06d302489bf8b61d9a5f7d0bfd Windows2025 原始Go＋exact manifest BUILD SUCCESS；新增两项no-WFP v2逐路由owned/intent WAL故障夹具PASS。原始[artifact13998997989](https://github.com/lly8666/wbd-next/actions/runs/43340808979/artifacts/13998997989) sha256 ceb4177bdd33592ae6c74a549339194fcdd706b3f334526d009dcdf7cd6bdcd1。**这只是软件夹具，不是Win32真实OS。**
- 新测试 tools/m0_plan029_h1697_real_no_wfp_os_windows_test.go 单独建立官方签名 Wintun 0.14.1、动态真实物理路由索引/下一跳（不依赖Npcap、固定测试NIC或联网DNS）、安装+generation+PnP original pin，使用真实 v2 lease→MTU→单DNS→紧凑路由 Win32 writer，测试 Apply→独立 OS Applied readback（GuardOwned=false）→Recover→OS无残留/父子WAL均无。进程内仅测试把旧 assemblyOnly=true 解除以执行真实API，正式产品 Ready/old WFP 不因此放行。失败也先完成代际owned Stop再释放Wintun并写原始结果。系统不修改Defender/旧项目WFP/第三方规则。
- 独立H1697 workflow在本次测试文件或本场景workflow改变时只运行**一个真实Windows OS网络场景Action**，不重发H1694，也不重刷028。Stage首次失败、WAL恢复结果独立写真实SOURCE JSON，no-FakeIP/Direct、P1/P2仍 NOT_RUN。H1694实际native TCP A/B/C PASS仅本地内核能力。
- **本次新实机Action未收结果，不得声称OS Applied PASS。** 完成PLAN029还需单后端Rust内核TCP物理socket、物理UDP、DNS53/FakeIP、配置GUI和padding及D1–D5/P1–P2。

```feature-impact
{"kind":"updated","ids":["windows-network-wal"],"reason":"Collect H1696 exact-source Windows pure v2 route recovery PASS and add separately scoped genuine signed Wintun no-WFP four Win32 stage Apply/Stop test; no premature product Ready."}
```
