# PLAN027A H929｜H928 Rust 平台首轮编译错误最窄修复

SOURCE `57b5898eca4b65183a0ee1618596e389367b5367` 自动 `r0-fake-platform` Action `41436001334` FAIL：`ipv4_fragment.rs:102` 同一行 mutable checksum 写视图与 immutable header 读视图重叠，Rust E0502。单纯先把校验和存为局部标量，再覆盖头部；两处单测相同错误也同时修复。没有修改协议位、生命周期、Game lane、Stop 或报文容量。旧 FAIL 保留，本次仅下一 SOURCE 重新编译判定；不能称 DF0/DF1 真实客户端已通过。

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"Fix H928 Rust borrow-checker compile issue by evaluating IPv4 checksum before mutating header field; no wire or policy change."}
```
