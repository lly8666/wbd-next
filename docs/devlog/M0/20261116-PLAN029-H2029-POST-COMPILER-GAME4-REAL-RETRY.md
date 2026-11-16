# PLAN029 H2029｜独立Game4 CN四TLS lane同源物理场景，Normal padding并行
- 代码冻结在H2028后同一Rust/Go产品路径；H2029只新增source-scoped验收触发，不重开同IP海外CDN双域名反向出口已排除的专项。
- Game4 真实门：原 Go/TLS四lane、Rust GameAdapter、唯一Wintun、CN/IP/域名先判Direct/Tunnel、Linux物理socket DNS53/FakeIP UDP，32KiB半关闭Direct TCP、普通Tunnel TCP/UDP及真实双Stop。旧H2023真实测试没进网络（fixture`p029_p2`NameError），现在是**重跑**，不是旧成果。
- 同时另一独立H2028 Normal Tunnel场景测新用户20..30条/2..3秒填充窗口和真实Npcap/eth0密文；两场互不混用mode，原业务无填充等待。
```feature-impact
{"kind":"none","ids":[],"reason":"H2029 separate Game4 CN native physical test trigger; product implementation unchanged, no feature card update."}
```
