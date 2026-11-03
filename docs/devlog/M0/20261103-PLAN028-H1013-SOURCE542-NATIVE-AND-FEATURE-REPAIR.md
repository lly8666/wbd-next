# H1013｜修正H1012真实CI失败，保留失败而不是刷绿

PLAN028 H1012 SOURCE `5427217202e2760a31d7ba3bafcc0fb680e40d38` 真实CI检查：

- 原Go protected TLS Action 41579399852 PASS；Rust native ABI 41579399913 PASS；原Go/native跨ABI及多个限定范围工作流PASS。
- 原 `NORMAL-COMMON` Action 41579399828 **FAIL**：Rust非`fec2_product_record`构建里`game_joined`字段经cfg关闭，而新私有绑定函数无条件引用该字段（E0609）。H1013将该条件独立置于`#[cfg(feature="fec2_product_record")]`，其它生产前置校验保留。
- 同源原Go TLS/Rust Linux双netns `PLAN012-COMBINED` Action 41579399829的新增`WBD_V4_PUBLIC_AUTO_IP=1`步骤 **FAIL**：确有客户端`V4_PUBLIC_LEASE_APPLIED`日志，但Python原始raw-regex使用双反斜线，错误匹配不到真实已分配IP，得到`AssertionError: []`。H1013修正为单转义IPv4字面点；没有用固定IP或假数据绕过内核回读、UDP及Stop验收。后续强制从新SOURCE重新做全部实际原生验证。
- `governance` Action 41579399691的Governance job PASS但Feature Catalog **FAIL**：Game功能卡长度约18000字符超过目录限制。H1013精简重复历史limitations的描述，但保留全部21条verification（原source/evidence/status不删），并缩小JSON缩进至1，大小降低到约15.9k字符。历史FAIL仍明确存在。
- `r0-static-qualification-audit` Action 41579399764 **FAIL**：老G2检查仍硬要求PLAN020 revision3 writer（现registry revision4），与本次产品SOURCE不同；不改历史批准文件来伪造新资格。

本次只修新源码缺陷、同SOURCE测试夹具和功能卡登记；不会将历史源码的通过结论直接晋升H1012。用户授权的028核心“单端口3设备同时原生业务/共享Rust TUN唯一reader/7模式代际交接/Windows Linux切网”仍施工中。H998物理MTU与ARM64 Game4FEC FAIL保留。

```feature-impact
{"kind":"updated","ids":["game-lanes"],"reason":"Correct PLAN028 H1012 overlong Game feature card without dropping any verification history; Rust cfg source and genuine auto-IP netns fixture error repairs are separately source-tested."}
```
