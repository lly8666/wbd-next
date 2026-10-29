# PLAN027 H390｜修正实际 CI 首错（不伪造产品证据）
2026-10-30。H389 [native Action 40935895121](https://github.com/lly8666/wbd-next/actions/runs/40935895121) **FAIL**：构建前的 `tests/test_native_regression_m3_scope.py` 强制要求旧 codec selector 仅含 F2 skip，阻止了新增非 mandatory CPU probe skip；现同步更新测试期望，并明确断言 required codec 名称均不被跳过。测试本身仍由 Actions 执行。

[governance Action 40935895112](https://github.com/lly8666/wbd-next/actions/runs/40935895112) **FAIL**：cursor.evidence_refs 要求每份证据 `source_sha` 等于 `last_tested_source`；H389 的多 SOURCE 恢复摘要不满足，不能把它当单 SOURCE PASS。现将摘要移入已有 `context_refs`，保留真正 SOURCE302d 的单源 evidence_refs；不改任何旧失败/新成功事实。新源码 CI 待收，PLAN027 产品阶段1/A/B/C/交付仍未完成。

```feature-impact
{"kind":"none","ids":[],"reason":"Repair stale codec functional-selector contract test and cursor provenance classification after actual CI failures; no product code/config change."}
```
