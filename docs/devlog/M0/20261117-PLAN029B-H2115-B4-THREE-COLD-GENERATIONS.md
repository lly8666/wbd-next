# PLAN029B H2115｜B4三代冷配置与旧FakeIP拒绝：原Go+Rust纯回归

H2114 `bd12a57d78ea7bcc6055f71ef1fedfe123ac6914` [governance44118837452](https://github.com/lly8666/wbd-next/actions/runs/44118837452) Feature catalog/Role双项PASS；历史H2113旧卡片超过16KiB的原FAIL仍保留。H2112真签名 Wintun/128 IPv6混跑 + Stop的 `PASS_SCOPED` 亦保持独立。

H2115在已有产品Go Windows `m0_plan029_cold_split_windows_test.go` 增加**真实公共冷构造函数**三代连续配置的测试，不发网络包、不伪造WinForms OS：高级 CN `bypass-lan-cn+cn-domain-direct=true`需有规则/旧FakeIP journal路径→第二代普通 CN `false`保留域名直连DNS的规则但无journal→第三代`split-enable=false;route-mode=all`保留原Rust V3双DNS、代际唯一DNS TCP synthetic /32，但不含CN/Direct/域名/FakeIP writer；停用业务时即使Direct cap超限、旧规则文件不存在也必须能建。持久旧FakeIP journal仅作为TEST-ONLY哨兵文件；断言第二/三代冷构造不读取/删除/修改它，不冒充原操作系统Stop。Rust `v4_client_split.rs`纯测试把第一代已宣告海外A的FakeIP、第二代新CN策略、第三代all隔离：旧198.18/16在新代均`RejectUnknownFakeIP`，即使fast all tunnel，也不能拿旧假地址当Tunnel目标；同海外真实A正常Tunnel，CN IP下一代仅按路由表处理。

同Go原产品仅**新增单测**，不修改分类/IPC/TLS/FIN/FEC/OS写入；真实B4尚需WinForms连接按钮实际多代、每代OS Applied/owned Stop、缓存刷新和晚回调代表，Game仍独立NOT_RUN。按原M0 SOURCE cheap/Windows/Linux Go Rust单元检查后再考虑一次真签名场景；不刷已通过的B3也不将纯测试提升为B4物理PASS。B5同VM<=10Mbps CPU/GiB/p99仍OPEN。

```feature-impact
{"kind":"none","ids":[],"reason":"H2115 adds Go Windows and Rust split pure regression tests for existing three-generation isolation semantics only, no product runtime change"}
```
