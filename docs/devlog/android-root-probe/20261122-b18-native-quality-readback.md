# B18｜Android 原 Rust PLAN027 30项 Quality 读回

基线 `d3142b2068d31a0756dd46ae409574c7d4c8849b`。Android Fixed 原生 `OriginalQualityTx` 已处理原 M3 PN、真实 M4 copied 和对端低频 Quality，但原 Go 只能拿到Unsupported占位；Auto的真假质量数据断点在此。

- 复用唯一Rust `OriginalQualityTx` 与原 `FixedStream` 源 k 分布，提炼 Linux/Android共用 `original_fixed_mature_snapshot`（30项：2s/8s真实包、UNKNOWN、capacity censorship、report、lag、16档k）。
- 原 Android Rust M4 提供同名 native `wbd_m0_embedded_go_public_fec2_mature_quality`，仅真实 feature7 + M4 已开后允许，`advance(now)`在查询时执行；原 Go CGo bridge 只做30个数字的低频复制，**无DATA逐包Go调用**；Linux读回消费同一布局。Host单测和APK Host source gate同批。
- 本批**尚未**开放 Auto：安卓Rust首次pending后明确拒绝新revision，下一批须在M4真实下一源包边界切档，旧parity不能丢，APPLIED不能冒用旧档报告。
- 标准TLS、M3/PN/AEAD、Normal/off默认、当前Fixed和owned Stop无实物改变。实体 Android↔Linux Auto和性能均NOT_RUN。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B18 shared original Rust PLAN027 30-field Quality/FEC-k readback wired into Android CGo; Auto not yet unlocked"}
```
