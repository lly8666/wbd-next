# PLAN027 H416｜修复 Windows 双 feature 编译边界

回收 H415 Windows Rust owner ABI Action 40968771695：确凿 FAIL，12 个 E0609 均来自未启用 FEC2 编译时访问受 `fec2_product_record` 守护的 auto_quality 字段。保留失败，不冒充通过。把唯一低频 v2→Auto 聚合分支以原本 feature gate 包围，Normal/off 保留原路和不启用 Auto。其他 H415 实现、四窗口/16 历史、预算和新 FEC2 mode2 均未改。

后续必须取 H416 exact-SOURCE Windows/Unix Actions；Linux 对端、生产 M2 完全退役、A/B/C/交付仍 OPEN。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Restore non-fec2 Windows compiler feature boundary for low-rate Auto metrics; H415 Windows E0609 CI failure retained."}
```
