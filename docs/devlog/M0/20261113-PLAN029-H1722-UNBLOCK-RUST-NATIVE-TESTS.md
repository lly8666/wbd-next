# PLAN029 H1722｜首个并行原生Rust测试FAIL定向复修

- H1721 SOURCE `065f8f47576440c44fba92a5861c89c7a4ed70f2` [Action43388829100](https://github.com/lly8666/wbd-next/actions/runs/43388829100) 两OS编译和wbd-platform 46项通过；Rust engine **FAIL**，保留原日志。新`FakeAllocator`压力测试错误要求回收过期IP后“必须重用相同数值地址”，实际`next4`选择下一个可用，安全行为不要求数值复用。改为旧fake已失效、新fake待durable后发布。
- 全量engine另外命中 M1 RTRB 旧donor缺Cargo manifest、Windows M4 frozen Linux-stream fixture。非029核心出口，仍FAIL，不修改历史源；本批同一Windows/Linux Action明确仅跑`plan029_`名称相关用例，平台库全测，不重复028矩阵。
- 依然没有正常产品Rust NativeOwner真实Direct/Tunnel。收到本SOURCE测试结果前绝不登记PASS，不启动030。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Correct false numerical FakeIP reuse assertion and scope new concurrent Rust native test gate to PLAN029; preserve existing first failure and unrelated M1/M4 fixture outcomes"}
```
