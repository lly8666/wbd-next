# B19｜Android 原 Go Auto → Rust同源FixedStream真实切档

基线 `f3d916eaaf6254dbae5bf8841e61f558666773e8`（B18 原Rust 30项成熟 Quality 已可经 Android Go 读回）。优先日常功能/真实性能，不扩极端异常框架。

- 原Go `--mode fec-auto` 走标准 FakeTCP/TLS feature7、认证/32、同一 Rust M3 AEAD/PN、原M4 RAW/TUN与owned Stop；Root App显式新增 Auto，Normal/off仍为默认。Auto用原Go `FecV2Strong` 初始档、2Hz native Quality采样、0.5Hz策略决策，无Go逐包DATA。
- Rust `wbd_m0_embedded_go_fixed_stage_pending` 冷阶段只接受首版；运行中必须先有原native APPLIED，才接受更高 revision 为 NEXT 意图。原M4在**下一普通IP source首片**调用`FixedStream.quiescent_change`，同一IPv4数据报的后续分片不跨档；旧parity保留并按原矩阵/原revision由同一M4发完。Busy则下一个普通源包再试，不停业务。
- 每档记录真实kernel copied首源PN、该档自己的原M4 copied源+parity、Quality正例基线。原M3认证的3s-mature report 必须以新首源PN为起点或更晚且有新正例，才能让原native APPLIED生效；不会借旧报告、旧parity。Go仅在原native readback确认后更新Applied。
- Android Go Auto使用原native读回代替Linux专有M2 commit；Linux行为不变。Fixed仍无Go 2Hz采样线程；Auto使用现有低频Go策略，Game仍不开放。
- 原真实Rust Host测试新增30槽布局及新revision Quality因果，`FixedStream.quiescent_change`原组件测试复用；Android双ABI、签名APK、Linux Oracle 按本SOURCE Action为准。实体Android↔Linux Auto、业务交付、恢复率、吞吐与CPU **NOT_RUN**。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B19 Android Auto explicit original Go native Quality policy with same Rust M4 FixedStream quiescent revision, old parity intact; physical E2E untested"}
```

## B19a｜同源测试审计修正

SOURCE `27f76465e53a4cd4c172c1ca8eb1448dce40e242` 的 [CI #44934886304](https://github.com/lly8666/wbd-next/actions/runs/44934886304) 中 native ARM64/x86 与 Rust B18/B19 Host 真实测试均成功；`root-arm64-app` 在 Python Source Gate 第163行失败。原因是旧 B13 静态测试仍要求 `q.counters[1]>0` 与全局 `repair_raw>0` 文本，而 B19 原真实行为已改成**逐 revision 的 copied-source、copied-parity、matched Quality**，旧断言不可作为验收。此提交只更新上述静态断言以核对当前精确源码，不更改TLS/M3/M4/Go/Java产品代码，也不改写旧失败证据。Android物理Auto E2E/性能仍NOT_RUN。
