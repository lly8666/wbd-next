# PLAN029 H1718｜中断回收 / 当前 M0 hash 锁

- 基准 `2469e23bd525cce10d172804801fa1a8d0b4cffc`。H1717 [Action43378854361](https://github.com/lly8666/wbd-next/actions/runs/43378854361) 签名Wintun下四阶段 no-WFP Win32 Apply→RuntimeMTU1280 读回→Stop **PASS_SCOPED**；Go编译 [43378854375](https://github.com/lly8666/wbd-next/actions/runs/43378854375) PASS。
- 同一SOURCE [43378854779](https://github.com/lly8666/wbd-next/actions/runs/43378854779) 旧Normal Win/Linux原TLS/Rust双向UDP/TCP+Stop PASS，仍是 `legacy1400`，非029中国域名/IP/双DNS产品资格。
- [43378854403](https://github.com/lly8666/wbd-next/actions/runs/43378854403) governance-maintenance 9 FAIL 原因是四个M0 live Go派生blob的manifest与Python审定锁滞后，且一条历史WFP断言不适于v2。仅更新这些**当前**SHA及负面断言，保留历史M4固定 donor 和12条来源约束；CI结果尚未收回，不写PASS。
- H1695 owned Defender A/B/C、H1709真实Windows TCP EOF、H1713 CN DNS→durable FakeIP→UDP回包都仅**诊断PASS**；不重复。正式 Rust NativeOwner ingress、Direct/Tunnel、单DNS、GUI有效值、padding、owned失败恢复、D1–D5/P1–P2皆未完整验收。
- 继续在真实adapter/原TLS owner已具备时执行v2事务；`assemblyOnly`不是“历史PASS许可”，Applied/Ready必须来自当次owner与网络读回；不重跑028旧矩阵或启动030。

证据：[H1718](../../evidence/M0/PLAN029-H1718-H1717-RESULT-AND-M0-LIVE-SHA-CATCHUP-20261113.json)。
