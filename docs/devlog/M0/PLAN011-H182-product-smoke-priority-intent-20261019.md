# M0 PLAN-011：先可用产品主流程，再普通场景烟测（2026-10-19）

用户最新要求：极端工况不必每次批量跑；先原始 Go client/server Normal/off 产品完整连接、正常收发、真 C2S kind1/原 M2、配置回执和 Stop/恢复，使用常用场景排除大问题。现 main H182 `be0a12e2dc000f51df336f6440c693a2dc676191`，cursor checkpoint S194 `3f313ad09e85b90e009d1e1d457a04f66663cce4`；只继承真实 netns SOURCE `1607114df1a6ab1f436b0a64ac77ae9e44edf2af` [Action 39242631401](https://github.com/lly8666/wbd-next/actions/runs/39242631401) 4-job PASS，包含 8 PN/1 真 reverse kind1/2s M2 covered8、真实 Stop。H182 Governance [39243301192](https://github.com/lly8666/wbd-next/actions/runs/39243301192) 因 GitHub REST 403 remaining=0 FAIL，非治理资格，不抹去。M4 016在其分支自主开发，不写其 cursor、请求或源码。M1 Game015及 M3 FEC2 原生功能已有已验收，不重刷；产品 FEC2 OFF。

本次先建 **轻量 common smoke**：单个 SOURCE-locked Linux netns job，原Go TLS +真正 Rust 原 owner; 正常业务8包、真双向C2S kind1→M2成熟 2s、Stop/Cleanup 的常用路径；无大 UDP 65KiB、MTU live缩减、150ms/弱网性能、ABBA、极端PnP及长时间压测。复用一个公共netns夹具，仅以环境标志在完成正常功能后提前退出，保留独立极端手动诊断，不改保护/限额协议。已有旧大矩阵失败保留且不是新 smoke 的隐藏绿灯。脚本/Go/Rust执行验证严格 Actions 不在本地；main自己的 shared workflow 可修改，M4 Windows 016 只消费其工位自测，M0不强制重复。

测试侧清单：必要且一次性：单用户名口令验证→Normal 8x双向业务→真反向回执成熟覆盖→Stop释放；正常错误另增加一个坏kind1/错误revision，不追求笛卡儿极端。若新Workflow绿灯也只宣称实验性 Normal/off Linux；真实 CLI/GUI 原始 Go产品 applied/rejected、Windows native网络、物理、FEC2、整产品仍未测，继续 R0-025 收口。
