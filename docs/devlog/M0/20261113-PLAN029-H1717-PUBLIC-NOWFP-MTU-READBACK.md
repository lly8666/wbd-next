# PLAN029 H1717｜修真实Ready首错：四阶段no-WFP MTU读回不能继续按旧五阶段WFP WAL

- [H1715 SOURCE f1dc Go Windows编译](https://github.com/lly8666/wbd-next/actions/runs/43374768091) **PASS**，source manifest和no-WFP产品装配纯测试通过；[旧公有Normal TLS Windows/WSL Action43374768125](https://github.com/lly8666/wbd-next/actions/runs/43374768125) **FAIL**，Ready之前首个产品阻断 `planned=1329 inspected=0: windowsclient: crash-persistent native DNS and IPv6 guard required`。此失败不归因于尚未实际执行的PLAN029 Direct/Tunnel业务流。
- 根因在唯一 `N4NativeUnifiedTxn.LiveConfiguredMTU`：仍硬编码五条旧WFP v1 WAL，并断言 `Stages[2].(n4WindowsMTUStage)`。方案§3A已废弃旧WFP guard，v2真实WAL为 `lease→mtu→dns→routes` 四条，真正Win32 MTU writer是 `Stages[1].(n4WindowsNoWFPMTUStage)`。即使四阶段Apply与OS Applied真实正确，随后健康/Ready读回也必报0，属于真实软件不兼容。
- H1717只改这一处：WAL generation/identity/schema/全部owned/按schema确切阶段名称和writer类型核验；v1仅可五阶段MTU[2]，v2仅可四阶段MTU[1]且不得存在第五守护stage。最后**真正调用Win32 stage Inspect**比较当前IPv4接口全部字段与原baseline+新MTU；不从JSON猜Ready，不写网络，不为新模式Arm WFP。原v1独立保留。
- 新纯测试覆盖v1/v2选择、foreign generation、partial WAL、intent、旧guard混入、name-only伪stage、assemblyOnly；已有H1697 **单签名Windows OS Action**在四阶段真实Apply和readback后新增同generation RuntimeMTU值1280验证，再执行准确owned反向Stop并检查parent/child WAL均消失。此源码提交前没有新Action结果，绝不写实际PASS或Normal/Game4 Ready。
- 同main有另一条H1716 Rust物理Direct UDP actor并行开发，本次不修改、不覆盖其源码或cursor历史；仍需完整Rust正式入口/DNS/GUI/填充和D1-D5/P1-P2。028按H1657、030不开始。

```feature-impact
{"kind":"updated","ids":["windows-network-wal"],"reason":"Repair the first real PLAN029 public Ready failure: schema-aware actual Win32 v1/v2 no-WFP MTU ownership readback, preserving existing v1 WFP migration and no fake Applied."}
```
