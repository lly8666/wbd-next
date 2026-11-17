# PLAN029 H2009｜只修 H2008 Rust 测试借用编译边界

- H2008 SOURCE `791fa076f650833c07a3b9a49aca3e1c42b67f35` 原Windows/Linux Rust [Native Action43878001800](https://github.com/lly8666/wbd-next/actions/runs/43878001800) 两端单测**FAIL**，原Rust源 [Action43878001987](https://github.com/lly8666/wbd-next/actions/runs/43878001987) Build**FAIL**：同一新 `random_record_pad_can_exceed_old_256...` 测试将 `packet[2..4]` / `packet[24..26]` 可变借用和 `packet.len()` 不可变借用写在同一表达式，Rust E0502共两处。原生网络 **NOT_RUN**，不升级为PASS。
- 本轮仅在测试内 `let packet_len=packet.len();` 预先缓存两个长度写回；**产品** `MAX_RECORD_PAD=500`、MTU/2KiB/10%/12record/默认Off/Direct不填原逻辑完全不变；让同一个原签名Normal Tunnel padding场景编译后运行，不扩其他任务或极端功能。
```feature-impact
{"kind":"none","ids":[],"reason":"H2009 fix only Rust unit-test E0502 evaluation/borrowing in H2008 new 500B padding test; product padding algorithm and config unchanged."}
```
