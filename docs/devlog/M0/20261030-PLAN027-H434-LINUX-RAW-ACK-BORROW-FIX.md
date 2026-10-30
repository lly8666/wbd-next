# PLAN027 H434｜Actions E0502 原生批量Raw parser 借用修复

真实 SOURCE 419030c8 fake-platform Action40980648310 编译失败 E0502 `linux_raw_carrier.rs` 两处：`parse_data_packet` 持有对原可变 slab 的不可变借用，copy_within 后才读取 `presentation_ack32`。在两个原始 kernel batch parser 分支先复制8字节以内的 POD 标量 ACK32，再原位移动密文；无新堆分配、无每包锁/时钟、无TLS或数据面变动。H433已另行修正不合法 OuterAckIndex 65536上限和未公开route epoch getter。本批只修源码可证的借用错误，Actions旧FAIL不能抹掉，最新 SOURCE CI 另取结果。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Fix two E0502 Rust borrowed-packet parsing errors in Linux raw ACK support before in-place ciphertext compaction, sourced from actual Actions."}
```
