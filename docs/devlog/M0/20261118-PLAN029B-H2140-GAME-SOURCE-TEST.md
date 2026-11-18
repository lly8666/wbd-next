# H2140｜Game2/4源级门与功能卡

[H2139产品候选](https://github.com/lly8666/wbd-next/commit/e5351ed7823cad8a374627f55b0701dc61ee9e9e)已经把原Game2提前拒绝改成共享Rust V4冷分流，且all/off不写业务OS Direct/Bypass。初次[Action44218036584](https://github.com/lly8666/wbd-next/actions/runs/44218036584) **FAIL_CHEAP_BEFORE_NATIVE**，因为旧静态测试仍要求Game2拒绝。本提交仅将静态断言改为检查2/4lane共用Rust V4、all/off零业务OS路由与真实冷策略的Go单测；功能卡同步为**已接线待真原生验证**，没有产品功能PASS冒充。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Sync source tests and bounded feature card with Game2/Game4 original cold Rust V4 implementation candidate, retaining native NOT_RUN."}
```
