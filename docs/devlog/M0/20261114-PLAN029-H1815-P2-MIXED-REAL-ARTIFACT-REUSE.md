# PLAN029 H1815｜P2真实内核混合，哈希复用H1814源码成品

- 已实际核 `c262636c81d688e8df8e844b668bbcc57957425d` 的 Action43571086653 artifacts：`m0-wl-windows-product-binaries-c262...` 与 `m0-plan024-linux-product` 存在。当前仅改测试夹具、工作流、文档；P2 Action以原SOURCE/hash/manifest、冻结产品代码git diff门禁直接恢复 Windows EXE/DLL 与 Linux Go/Rust Server；不重复Windows/Linux Rust/Go原生全量单测/构建、ARM64测试。不使用任意旧成功缓存，不跨网卡代际。
- P2同源独立Windows2025 runner内使用旧signed Wintun/Npcap→WSL2原Linux TUN，先 Windows 物理绑定WinSock→Linux eth0 真 TCP 1MiB基线，再 Windows已拥有Wintun lease→已宣布FakeIP→Rust native Direct TCP→Linux eth0 真TCP 1MiB，彼此负载相同轻度应用pacing；第二段同时保持 **120个96B** Windows应用→Linux TUN 的普通 Tunnel UDP 回包，校验同Windows单调时钟窗口重叠、物理Source/哈希/内核来源、两腿半关闭，随后旧D1/D2和当前产品 owned Stop。不存在另一个Wintun或Go逐包代理。负载有界而非极端吞吐。
- P1实际首轮 Action43571086653：原A腿真实约50Mbps各向、kernel TC、UDP/TCP与Stop PASS，但P1脚本要求 Linux WSL2应用携带`GITHUB_SHA`，该进程由 `wsl.exe -u root`创建、未继承，日志`source:null`，因而 coordinator `FAIL_FIRST_NATIVE_MEASUREMENT_OR_DELIVERY`；B未启动。此首错不冒充产品失败或P1完成，需下一独立修验收来源字段，只允许Linux null且仍校验原始Linux构建manifest/scenarioSHA/真实业务。
- 本H1815不是P2性能优化证明：两种socket路径的内核CPU、Go/Rust and WSL路由差异无法隔离；不假称物理公网基线或百万并发。真实Action未跑时 result=NOT_RUN。D4 IPv6、GUI Connect、Game4新Rust分流仍未全面接线。

```feature-impact
{"kind":"none","ids":[],"reason":"Add P2 genuine scoped physical-vs-Direct 1MiB TCP + concurrent Tunnel UDP fixture and exact hash-verified unchanged-product artifact reuse; no runtime/default/config changes."}
```
