# PLAN027 H450｜WBC4 退役控制拒绝改为无副作用

完整追踪了 H440 两端旧 kind1 M2 拒绝后的代码次序：Windows `m2_authenticated_kind1_entry` 先处理 `HealthClock` / `quality_history`，末尾才 `Err(INVALID)`；Linux `background_raw_once` 在更新 native Health RX、quality summary、外层 ACK 提示后才设置 `invalid_seen`。因此恶意混合 legacy Receipt+Health/Quality 虽返回错误却可能提前改变状态（合法AEAD+unique replay不是收货凭证）。本次改为 **Windows在任何Health/Quality副作用前拒绝；Linux M3 opener消耗PN后立即跳过，不给RX activity/quality或outer shadow加信用**；保留其他控制和真实业务不受扰，原 codec 离线probe仍在，未为旧M2启动新的高频发射或重试。H450源编译/负例回归尚待Actions。B跨OS / C矩阵和A失真仍未闭环。

```feature-impact
{"kind":"none","ids":[],"reason":"Fail-closed ordering for retired receipt; no new capability; existing feature card already states production no old receipt."}
```
