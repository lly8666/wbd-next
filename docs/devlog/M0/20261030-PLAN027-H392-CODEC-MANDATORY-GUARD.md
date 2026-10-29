# PLAN027 H392｜非必需 CPU 测量隔离增加强制用例保护
2026-10-30。H389 native build 前自测失败，H390 修正了旧 selector 期望，H391 修正 cursor 9 refs 超限；现为 `native_group_selection` 增加负例：如果未来将 `r1_steady_release_same_source_fresh_vs_reused_owner_cost` 列入 required，则禁止继续 skip，必须 FAIL，而不是静默漏测。与 F2 mandatory 的现有守卫对称。此源码变更将触发原 native functional Actions 一次编译/按组消费；其结果必须取回，不因代码合理就假称 PASS。

仍无生产 M2 退役/新 Quality owner/A/B/C 证据；Windows 原 SOURCE18cf scoped PASS 与 H388 SOURCE9105 native codec FAIL 均保留。

```feature-impact
{"kind":"none","ids":[],"reason":"Fail-closed native codec test selection and source-locked selftest; no product runtime, config or feature card changed."}
```
