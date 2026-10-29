# M0｜PLAN026 恢复后：Rust 双端 Health/Dead/FIN 低开销状态核心

2026-10-29，同一 M0 task/epoch，**本提交是部分源码施工，NOT_WIRED / NOT_RUN，不是 Keepalive 产品 PASS**。

- 与老项目 `wobuzhidao@a7a82db3` `runtimeentry/lifecycle_health.go`、`runtimeowner/{health,control_policy}.go` 对照后新增 `v4_native_health.rs`。标准15s Keepalive／90s无认证超时、至少3倍间隔、失败发送至少1s退避；认证控制包只算活性，不算真实业务；Quality带Health成功回执能合并定时，普通 M2 receipt 不算Health发送；服务端DORMANT需要真实FIN+实际业务idle；客户端FIN需要新鲜authenticated peer idle；低PPS/失联不假休眠；换lane代次重置，Stop取消deadline。
- 无线程、Go ticker、heap queue、timer对象或未认证输入旁路；每lane一个小Rust状态值，接入既有NativeOwner deadline时不额外唤醒。
- 含六组精确状态回放用例，**尚未执行**。下一步将此核心接入 Windows Rust M2/Control kind1 的真实AEAD/PN与 Linux 双端既有 native worker，并完成有效 CLI/config 与V2监测。仅有模块不等于两端有实际Keepalive或Dormant。
- 前一轮 main H349 已有 Fixed/Auto native two-worker源码候选和 V2场景，保留。Auto/Keepalive真实测试安排在 Fixed、Game 之后。
```feature-impact
{"kind":"none","ids":[],"reason":"纯内部Rust共享Health/Idle状态核心，尚无公开产品接线、参数或默认值变更。"}
```
