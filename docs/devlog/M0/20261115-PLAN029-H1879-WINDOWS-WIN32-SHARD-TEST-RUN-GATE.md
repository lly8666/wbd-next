# PLAN029 H1879｜不要把平台测试“编译”冒充“运行”：修Windows事件回归CI触发

- [H1878 Action43664394663](https://github.com/lly8666/wbd-next/actions/runs/43664394663) 的Windows Rust full engine库386项PASS，然而`cargo test -p wbd-engine --lib`不执行它的依赖`wbd-platform`中新增的`plan029_sharded_wsa_128_idle_two_active_same_event_no_lost_read`单测。已经确认Windows测试构建绿**不代表128 socket test已运行**。
- 现存`m0-plan029-h1721-native-split-capacity.yml`已在Windows2025及Ubuntu24.04上以`cargo +1.85.1 test --locked --release -p wbd-platform --lib`真正执行平台测试，但其`on.push.paths`未包含`crates/wbd-platform/src/windows_direct_tcp.rs`，故H1878未触发这个真正的Windows组件测试。H1879只补这一个触发路径；用现成双OS矩阵执行真socket单测并保留同一SOURCE，拒绝纯模拟报告。
- 不改任何产品源码、WFP、防火墙、网络构件、分流算法或签名P2测试配置。**H1879的真实新Windows128 socket测试仍NOT_RUN**，需收准确Action命名测试行；此前H1877签名4MiB P2功能PASS、性能2.787x物理仍OPEN。128 Wintun真实flow、旧/新调度同VM P2及CPU/尾时延仍NOT_RUN，PLAN029未完成。

```feature-impact
{"kind":"none","ids":[],"reason":"CI trigger only: make existing Windows platform unit gate execute previously compiled-only 128-socket sharded WinSock regression; no product or feature card change."}
```
