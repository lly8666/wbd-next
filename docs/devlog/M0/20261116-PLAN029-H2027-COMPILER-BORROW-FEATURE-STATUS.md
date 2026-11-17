# PLAN029 H2027｜修E0502测试借用和功能目录状态
- H2025 [Native Action43898790386](https://github.com/lly8666/wbd-next/actions/runs/43898790386) 和原M1重复的Rust编译报告测试`E0502`：`let v=&p.seen[&key]`后再`p.propose(...)`为可变借用。H2027先保存`v.max_records`后再调用；生产逻辑、20..30条/2..3秒窗口、0..500B真MTU、无每流累计额度**不变**。
- [Feature Action43898790357](https://github.com/lly8666/wbd-next/actions/runs/43898790357) `FUNCTIONAL_PASS_HISTORICAL_POLICY`非法；改为已支持的`FUNCTIONAL_PASS`，其`scope`明确仅H2021旧不限次数/时间物理测试，绝不覆盖新窗口。
- 这两项失败都在真实网络前；旧原Action日志保留。Game4 CN真实验收仍未成功。
```feature-impact
{"kind":"updated","ids":["startup-flow-padding"],"reason":"H2027 only Rust test mutable/immutable borrow correction and valid historical-scope verification status. Product policy unchanged."}
```
