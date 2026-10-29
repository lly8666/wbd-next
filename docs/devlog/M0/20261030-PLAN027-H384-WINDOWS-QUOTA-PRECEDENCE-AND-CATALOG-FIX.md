# PLAN027 H384｜修复实测Windows额度回归与声明格式
2026-10-30。已从 Windows native Action40929275175 发现 `m0_windows_original_m2_effective_readback_is_actual_runtime_budget` FAIL：`direction_epoch_limit>0` 断言未满足。定位 H381 额度重写后 `fresh/10\n.max(SPARSE_FLOOR_BYTES)` 在 Rust 中把方法绑定到字面量除数；修复为 `(fresh/10).max(SPARSE_FLOOR_BYTES)`，保留稀疏额度与10%F硬上限。此改动必须由新SOURCE native 验证，不能把纯解释算PASS。
Governance H383 Action40929504232 Feature catalog FAIL `invalid feature-impact kind`，据 `tools/feature_catalog.py` 将三批 devlog `kind:update` 统一改成合法 `kind:updated`。未篡改性能和旧产品 FAIL，PLAN027 A/B/C 仍未完成。

```feature-impact
{"kind":"updated","ids":["fec-auto","outer-opportunistic-repair"],"reason":"Correct low-F v3 repair quota precedence bug exposed by real Windows native Action and repair invalid H381-H383 feature-impact metadata values; follow-up source-locked CI required."}
```
