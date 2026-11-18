# H2182｜Linux Game startup-padding 原生模块 cfg 首错

H2181 [原生 Action44266160914](https://github.com/lly8666/wbd-next/actions/runs/44266160914) 已在真实Ubuntu ARM64 aarch64编译时给出`E0432/E0433`：`crates/wbd-engine/src/v4_game_lane.rs`及`v4_embedded_go.rs`需要的`crate::v4_client_startup_padding`原先被`lib.rs`的`#[cfg(any(target_os="windows",test))]`隐藏。H2181新增Linux Game加密原send逻辑已支持linux cfg，但**crate根模块未同步**；原生网络步骤未执行，不能宣称Linux padding有效。保留原失败。

H2182只把`lib.rs`该模块编译门扩展为`#[cfg(any(target_os="windows",target_os="linux",test))]`、在测试中加入对应源守卫。没有新加密、协议或随机策略算法，也不在COLD前设置、不改变Windows现有ABI；Linux Normal/Fixed/Auto `tls/flows`依然明确拒绝。重复触发只限于新SOURCE正式Go/Rust构建+后续互补场，H2177真实10/10旧SOURCE仍独立保存。完整029/029B技术OPEN、030未启动。

```feature-impact
{"kind":"updated","ids":["startup-flow-padding"],"reason":"Correct missing crate-root target_os=linux cfg for the already staged original Linux Game startup-padding source; no change to runtime policy or false native qualification."}
```
