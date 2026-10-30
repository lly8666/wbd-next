# PLAN027 H445｜真实Linux测试CI旧M2消费端修复

H444 native-functional [40987340896](https://github.com/lly8666/wbd-next/actions/runs/40987340896) 所有分片PASS。H443 1%真实丢包脚本输出已合法改成 `v4-public-1pct-no-M2-real-delivery.log`，Fixed首发日志仅 `PENDING_ACK`；PLAN012和并行FEC workflows还在硬读旧 `authentic-M2-recovery` 和 `APPLIED_REAL_AUTH_M2`。本批更新上述精确Oracle和同源产物消费，不降低512个应用原始发送、核内双向真实丢包、真实首次交付、真实Stop硬门。并行 Fixed/Auto 64应用包可报告仅首到/Stop，`product_qualified=false`，不挪用为Fixed Applied或Auto长窗验收。原失败仍保留。PLAN027 A/B/C未闭环。

```feature-impact
{"kind":"none","ids":[],"reason":"CI stage asserts retired no-M2 product expectations without altering real application/Stop or qualification."}
```
