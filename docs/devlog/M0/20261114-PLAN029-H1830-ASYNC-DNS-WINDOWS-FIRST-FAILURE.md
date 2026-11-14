# PLAN029 H1830｜收H1829首个失败、精确修异步DNS夹具

- H1829 SOURCE 6bd21ed8d7777302e079bb8302cb1327d50610d4 的 native-functional、governance、Windows ABI/编译、原生Go/Linux无场景作业PASS_SCOPED；[Windows/Linux Rust组件Action43582814402](https://github.com/lly8666/wbd-next/actions/runs/43582814402) FAIL。Windows79项中78项PASS、1项为旧 `DirectDns` 缓存命中立即回包断言：新日志writer正确要求真正fsync ACK才允许发CN合成A，因此此断言已过时；不是实际网络FAIL。
- 同SOURCE [原始Windows/Linux无场景Action43582814365](https://github.com/lly8666/wbd-next/actions/runs/43582814365) 的 Windows Rust全库375 PASS/2 FAIL、Linux Rust322 PASS/1 FAIL；额外根因是新journal unit构建9 FakeIP地址范围却要求100 hard slots -> `FakeAllocator::new(...).unwrap()` 返回 `InvalidPool`。真实Windows Go产品/native-public-two-os job为SUCCESS但无029 DNS场景；不能伪报联网通过。
- H1830精确修两项测试：9个地址配9项硬上限；缓存命中首次答复必须在有真实pending identity、未announced、无回包后，poll真实writer持久化完成，并由 `DirectDns::poll` 发出原始ID的合成A，随后验证有效旧映射命中无需再次同步。无代码绕开durable ACK、无DNS回退/新thread/poll1ms产品调参。保留旧失败完整链接。
- 本批新SOURCE Windows/Linux组件、签名DNS真网、慢磁盘/Stop、压缩重启及所有029退出条件 **NOT_RUN**。先收source自动CI，非每个helper新dispatch；FakeIP单writer内部仍需审真实Stop时`Drop::join`潜在长fsync等待及崩溃原子替换时序。
- 其他并行已知缺口：H1827/H1828 Direct进展/驻留buffer P2速度+RSS需真SOURCE验证；Game4 CN split/GUI签名入口/IPv6，P1纯Tunnel相对CPU变化仍OPEN。028限定收口，030不开工。

```feature-impact
{"kind":"none","ids":[],"reason":"Correct two stale/invalid Rust unit fixtures for asynchronous durable-before-FakeIP reply, without changing product behavior or public schema."}
```
