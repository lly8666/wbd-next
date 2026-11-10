# PLAN028 H1513｜编译夹具漏写收口，不重复网络 seed

源代码候选 `07312d6e1743d5c28ff839fd2c9eb277c99744ed` 的 Action [42768853063](https://github.com/lly8666/wbd-next/actions/runs/42768853063) 已收：Windows Go compile/test、Linux/Windows Rust library、source-locked Linux Rust release 均成功；Linux original Go `v4productcli` 测试编译在新写的 `mixed_manual_scope_linux_test.go` 两次调用处报 `too many arguments in call to runGame`。实际函数七参数，测试误传八项；修正测试中两处多余 `nil`，未改产品逻辑。该 Action 的 Windows 五客户端业务 **NOT_RUN**，绝非 TLS/MTU/业务性能 PASS，源 H1506 原始服务端 FAIL 保留。

本轮只重试一项 200ms/loss0 原生 Windows5 场景，先过原 Go/Rust 平台构建，再核真实触发：shared server READY、受保护五账户、双端 M4/MTU、真 UDP/TCP 和原位 Stop。loss30 后续独立；不重播 seed 以掩盖故障。前序 Governance `d1bb7f3a8aba83cc680a4c1ba551888b23ea33c8` 已 PASS，功能卡证据限定原始失败和未触发项。PLAN028 IN_PROGRESS。

```feature-impact
{"kind":"none","reason":"This follow-up changes only one test invocation arity and one-source test dispatch/ledger; the prior commit already updated the existing tls-auth-multiclient feature card for the actual mixed/manual product wiring and its unverified status.","ids":[]}
```
