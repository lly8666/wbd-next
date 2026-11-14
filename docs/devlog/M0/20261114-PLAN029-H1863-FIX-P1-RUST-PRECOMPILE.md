# PLAN029 H1863｜H1861 P1失败首边界是Rust构造字面量漏类型，不是业务网络

- H1861 SOURCE `905e1cef` [native Action43617572311](https://github.com/lly8666/wbd-next/actions/runs/43617572311) 与 [Rust component43617572418](https://github.com/lly8666/wbd-next/actions/runs/43617572418) Win/Linux Rust编译均FAIL，首个`crates/wbd-engine/src/v4_client_split_wire.rs:249 let fragment_key={`缺少`FragmentKey`类型名；没有进入P1真实链路，不能用此Action当CPU反证。H1862 P2 bulk同一原SOURCE快路编译缺口仍在途，独立收其最终结果，不重复派P2。
- H1863只恢复先前既有`FragmentKey{`字面量类型，保持All普通非DNS流不查FlowPin、DNS53/未知FakeIP/分片源租约原逻辑；无任何网络参数更改。不跑全旧028矩阵，不绕过编译或整场Stop。
- 此SOURCE只带`[plan029-v3-real-p1-tunnel-ab]`，一次正常编译后单VM有序A/B 50Mbps60s、真实CPU/GiB/p99/空洞/RSS/owned Stop。真实P1在提交时NOT_RUN，029仍IN_PROGRESS。

```feature-impact
{"kind":"none","ids":[],"reason":"Repair exact Rust FragmentKey struct literal compile error from H1861 fast-path insertion; no feature status or semantic change, scoped P1 retrial only."}
```
