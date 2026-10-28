# M0 恢复和 PLAN026 Fixed/Auto/Game Rust-only 稳态接线研究（2026-10-29）

用户明确授权 Normal/off 暂时收口，转为详细研究 Windows FEC2 Fixed/Auto 和 Game2/4 原生接线，以最少worker、低CPU、业务完全绕过Go热传输为目标；要同时研究 Linux 已有Rust路径。检查 main `START_HERE.md`、M0 registry.goal/cursor、真实Windows NativeOwner+现有FEC/Game+Go产品调用方、Linux FixedStream/Game native worker与现有精确证据后，形成有执行次序的[设计决定](../../decisions/M0-PLAN026-FEC-GAME-RUST-STEADY-WIRING-RESEARCH-20261029.md)。

Normal/off保留精确事实：Linux双真实原始Go TLS/Rust 24场 `b9c2c170` [40733603221](https://github.com/lly8666/wbd-next/actions/runs/40733603221) 22 PASS + 2 `INCONCLUSIVE` (100M 1%/50ms and5%/50ms pacing catchup)，48端真实R非零/<=10%。Windows↔Linux `bf84929b` 24 runs查询时23 success、40736177552仍IN_PROGRESS；不能称24全部绿；本批不启动新Normal压力测试、不删除历史FAIL。

设计要点：复用 `v4_windows_fec2_owner.rs`/FixedStream 和 `v4_windows_game_owner.rs`/GameAdapter 在**同一个Windows Rust NativeOwner、一个Wintun、一个Rust TX/一个Rust RX、一组shared NPF TX、每lane受控NPF RX**上做type-aware调度与真 M4结算。把Windows Fixed/Auto和Game现有Go包pump移出默认产品，Go只负责真实FakeTCP/TLS/OS/WAL/配置冷控制，无稳态逐包FFI/Go channel。LinuxGame现有1TX+每lane1RX结构只作语义oracle，Windows利用Win32 events限量公平drain 2/4 lanes，不抄线程数。Auto仅一个policy owner，保护actual-k、2s/8s成熟质量、revision；FEC source首发不等parity；Game共享一次逻辑LINK/FEC，副本每lane独立AEAD/PN，copy due和真实kernel receipt。多模式 ABI V2、Stop及未来替换lane权限一次设计到位。

未写产品代码；Fixed/Auto/Game NativeOwner native qualification **NOT_RUN**，此提交无性能结论。下一批如实施，需一次完整产品/ABI/调用方/测试/manifest冻结源码后集中Actions和同机A/B，不得把旧七模式Go pump功能PASS迁移至Rust-only新路径。

```feature-impact
{"kind":"none","ids":[],"reason":"Documentation and code-path research only. No executable product, default, mode capability, CLI/GUI, feature status, or source-qualified performance result changed."}
```
