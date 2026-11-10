# PLAN028 H1504｜仅CI初检断言和工作流自路径修复，未消耗任何1800业务网络

第一次新源码 87d12ef01b3e67e0e70d0ee5c9827616dd715c44 已经 push。Windows [Action42753442675](https://github.com/lly8666/wbd-next/actions/runs/42753442675) 仅 cheap workflow-native contract 3 个断言 FAIL：原L3标记的 `&& '1'` 精确文本、原52min step超时表达式、旧H1453 750s clean Windows 真实日志标记被新动态语句改写；**没有运行任何Windows signed Npcap/Wintun产品业务，不能判产品FAIL**。不改旧纯离线断言的含义，恢复真实旧 marker/timeout/clean label及老marker单独时 H1450 fail-close，同时只准用户这次新预算marker结合旧marker触发一个 hosted Windows1800诊断（不等于独立Win DUT合格）。

新 ARM64 H1505 工作流确实存在，但 `on.push.paths` 拼成 h1505-arm64-1800-budgeted-health5.yml，而仓库路径是 h1505-arm64-1800-budgeted-fiveclient.yml，导致没有被 GitHub 触发。已校准为新真实文件名，仅下一次提交触发一次预算内 native ARM64五客户端1800，冻结产品 Go/Rust source1211fd51不变。

下一提交消息三标记 `[plan028-win-linux-co-client] [plan028-win-linux-1800] [plan028-h1504-win1800-budgeted]` 对用户本次独有的 H1504 1800 做不重复 CI 触发，旧单独L3标记仍被已有 guard 禁止；本次新标记必须同时存在，避免任意后续旧marker触发不安全托管长测。 Windows clean 1950、Ubuntu外部GH metadata观察均受新标记约束。原始一条 H1295 MTU180被测试fixture自动触发与此无关，保留原结果。未知网络结果仍 NOT_RUN，PLAN028 IN_PROGRESS。

```feature-impact
{"kind":"none","ids":[],"reason":"Only workflow CI contract and exact self-path repair after zero network work; original Go/Rust product frozen."}
```
