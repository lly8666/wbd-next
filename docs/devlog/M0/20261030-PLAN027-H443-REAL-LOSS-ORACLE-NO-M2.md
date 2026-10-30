# PLAN027 H443｜1% 真丢包测试旧回执硬断言退役

H442 [PLAN012 run40986297854](https://github.com/lly8666/wbd-next/actions/runs/40986297854) Linux original TLS/Rust source build实际运行：Fixed与Auto原始内核FEC均交付首到64、并保留Stop，旧测试仍强制要求 Fixed `Applied=1`；1% loss 512源实际丢包计数在独立 qdisc/应用回路后，末端检查 `authenticated_ack>0` 失败，值实际 `[0,0]`。既然逐record旧M2已退役，这个值为0才诚实，不得把外层ACK或真实首发造作旧应用确认。H443把独立脚本断言改为旧M2零报告、真实失包/首到/首发/Stop仍严格需过；Fixed短烟雾的配置读回明确 Pending，不报告 Applied，更不改任何原始内核生产码。Auto短64源报告 Pending 维持。PLAN027整单仍未完成，特别是Fixed替代 Applied 认证证据与真实双端 B/C。

```feature-impact
{"kind":"none","ids":[],"reason":"Retired-obsolete smoke oracle only; no product evidence or feature capability is promoted."}
```
