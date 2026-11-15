# PLAN029 H1904 | 旧短负载静态契约首错修复

- H1903 [Action43691408975](https://github.com/lly8666/wbd-next/actions/runs/43691408975) 在Cheap workflow的H1896短流量静态测试FAIL，整个签名Win/WSL2原生Job均SKIPPED。测试期望字面 `if HIGH_RATE:MAX_SUSTAIN=14000` 和旧WSL env行，长流量源码为保证普通测试不变而变成 `if HIGH_RATE:MAX_SUSTAIN=60000 if LONG_RATE else 14000` 与 extras列表。这里是测试文字契约陈旧，非真实TCP数据面崩溃。
- H1904仅改两份Python unittest：旧H1896测试现在同时保证普通短场景仍为14000包上限、长2GiB/1.5GiB才可扩大到60000，并显式验证WBD_PLAN029_P2_HIGH_RATE_SCENE及LONG_RATE在WSL argv env同时传递；H1903新测试锁定60000长上限。所有原Rust/Go/WinSock/Wintun/64KiB队列和原业务应用均未改。
- H1903原失败保留历史，新SOURCE精确三个提交标记重新走独立Python cheap测试与同源原Windows2025签名Go/Rust、Linux WSL2真实2GiB单向500Mb/s加双向各1.5GiB合计700Mb/s的物理vDirect对照，96B Tunnel UDP六阶段和双方owned Stop。H1904网络数据和CPU效果NOT_RUN，P1/P2仍OPEN。

```feature-impact
{"kind":"none","ids":[],"reason":"H1904 only updates two existing static Python tests to the actual bounded short=14000/long=60000 UDP and explicit WSL highrate/long scene args; no production or feature card changes."}
```
