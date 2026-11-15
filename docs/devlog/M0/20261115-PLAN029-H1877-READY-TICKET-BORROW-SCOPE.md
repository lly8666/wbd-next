# PLAN029 H1877｜Windows Rust 编译首错：ready FIFO 借用域

- H1876 [Action43662916616](https://github.com/lly8666/wbd-next/actions/runs/43662916616) Windows library first failure `crates/wbd-engine/src/v4_windows_native_tcp_direct.rs:219 E0502`；Rust active 同一时刻可变借用 flow 并不可变遍历 active，在 source lock 到Windows native release时前置失败，Win product/4MiB/Stop **NOT_RUN**。Linux纯组件及H1876治理SUCCESS不代表Windows真业务。
- 此次将获得 `generation` 并设置 `flow.queued` 的可变借用限制在独立作用域，之后罕见达到32k ready ticket上界时才可用不可变active索引清理旧代token；入队key、上限、顺序、通知/超时完全不变。没有执行旧SOURCE失败工作流的第二次相同dispatch。
- H1877是候选，需完整Windows构建/真实P2后再判定。H1875真实业务物理47.902/Direct133.730ms，功能PASS/P2性能OPEN不改；事件分片/128 idle压力/同VM前后CPU A/B尚未验证。保留H1876原FAIL。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1877 fixes exact Windows compile E0502 in H1876 sharded socket ready-ticket compression, with no product runtime semantics changed and no premature real-network PASS."}
```
