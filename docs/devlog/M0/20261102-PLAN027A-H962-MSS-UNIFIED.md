# PLAN027A H962｜正式V4双端消除1360固定MSS：冻结验收源码

已复核最新main（用户先修MSS），H957真实阶段Game [41462417865](https://github.com/lly8666/wbd-next/actions/runs/41462417865) 和ARM64 [41462378097](https://github.com/lly8666/wbd-next/actions/runs/41462378097) PASS，H958 DF [41463910871](https://github.com/lly8666/wbd-next/actions/runs/41463910871) FAIL 保留。此前Windows outer1460 inner1389而Linux inner1329；Linux应用真实对端MSS1360减record31，Windows正式装配未覆盖原 Go FakeTCP MSS，是强根因。

H959A/B：同一已验证原Go Git blob完整覆盖`packet/client_association/association`等源码供Windows两个manifest和Linux/ARM64安装器；V4 Product no DefaultMSS1360 fallback；客户端/服务端关联均冻结SYN/SYNACK本地MSS至重发，原SYN外观及TLS身份不变。旧上游通用单测矢量仅`_test.go`显式初始化，不进入产品。H960：Windows先从真实出口`net.InterfaceByIndex.MTU`加配置外层调用Rust原ABI，再创建Normal或Game关联；新预算也收窄record offer/OS planned inner。H961：Linux发/收原始TCP options MSS数字，严格双端native夹具要求Windows真发SYN/收SYNACK、Linux真发SYNACK/收SYN、双方物理路由及Rust收窄一致。

本次H962补唯一规范、配置/GUI只读状态、功能卡和测试。Go原FakeTCP字节级可见`1400→1360`,`1460→1420`,`1500→1460`，原本固定外观不是产品补丁。本SOURCE native**尚NOT_RUN**，不得把理论1389/1389写作新实测。只有必要真Go/Rust构建后复用exe/DLL/Linux，不重复历史全部性能。H958失败及旧source PASS永不改写。

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"H959-H962 current V4 Rust cold physical MSS/actual SYN/SYNACK unified Go source; feature remains IMPLEMENTED_NOT_TESTED until current source native proofs."}
```
