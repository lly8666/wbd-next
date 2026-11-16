# PLAN029 H1987｜精确 owned Defender 孤儿规则的代身份验证／CAS 恢复

- 收 H1986 原SOURCE `6d2ba3f5906a7dd4b71f5cf853ae6fb1da893b7c` [治理43827991490](https://github.com/lly8666/wbd-next/actions/runs/43827991490) 与 [维护43827991504](https://github.com/lly8666/wbd-next/actions/runs/43827991504)，均 **SUCCESS**；H1985三个真实Windows纯回归与单条精确 Defender COM 规则PASS已另有证据，但不是产品 D5 完整场景。
- H1982 之前已经阻止“主 WAL 丢失但剩下一条 Defender sidecar时默认为已恢复”的错误，不过连可独立校验的、原 owner 已fsync的 `phase=owned` 侧证也永久拒绝恢复。H1987 保留两条路由 sidecar 有残留时整批失败关闭；**只有单独** `statePath+.plan029-defender-tcp` 才先做常规文件/Lstat、限额、SHA、原安装代身份、重算同一 rule Name/Description，再交现有真实 Win32 COM backend 进行精确 Lookup→CAS RemoveOwned→再次不存在→删除本项目侧证。
- `intent` Add后中断但实际规则在、凭据损坏、别代重算不匹配、foreign/篡改 COM readback、API失败都不能当成可删除的项目资源，保留 sidecar 和错误，不全局关闭防火墙、不恢复旧 WFP。该操作不试图凭空恢复 Wintun/route/MTU/DNS。
- 新纯 fake 后端 `TestPlan029DefenderOrphanOwnedCASNotIntentOrForeign` 检 exact owned 仅一删、intent 不删、foreign 不删、SHA有效但身份key变更不删；在原 H1661 Windows **同一条** narrow COM 测试中让真实 `N4NativeRecoverState` 以无主WAL入口恢复一条 owner-owned Defender Allow，不新增第二条OS规则、不派发实网。所有本SOURCE测试/COM仍 **NOT_RUN**，等待原push自动收件。
- 同步三个 Go overlay 文件的当前生产 PLAN020/M0 `result_blob` SHA，以及一条旧 M4 检查的**M0 reviewed current** entry SHA；原 M4 donor、PINNED_FILES/旧manifest 不变。H1978 原 native FAIL/H1974 五次61ms OPEN，实际 GUI Connect/Stop、Game4 CN、D1–D5/P1–P2、IPv6/资源/填充仍需退出；无完成交付。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1987 exact generation-owned standalone Defender sidecar after primary WAL loss may be CAS recovered only with checked receipt and live COM exact rule. Intent, foreign, corrupt, route orphans stay fail closed. Native networking NOT_RUN."}
```
