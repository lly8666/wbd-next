# PLAN027 H919｜修复 H918 治理门之证据引用上界

- [H918 governance Action41427002301](https://github.com/lly8666/wbd-next/actions/runs/41427002301) **FAIL**: `SCOPE_AUDIT_FAILED: unbounded evidence_refs`. `tools/governance.py validate_cursor(max_refs=8)` 要求 cursor 的 evidence_refs 最多8；H918 新增四份已结束真实两OS证据时将热引用增至11。
- H919 仅把 cursor hot references 按已有顺序保留最后八份，同产品源 `6693910f...`；所有其他签名证据在原独立路径仍在，H917 normal burst 原 GitHub Action 的 **FAIL** 与 original native child/Stop PASS 不重新定性。
- 没有产品代码、夹具算法、scenario及性能job变更；H918 正在检查便宜 Python canonical source gate，结果另收，不制造原生 PASS。

```feature-impact
{"kind":"none","ids":[],"reason":"Respect existing bounded cursor reference-index contract after observed governance fail; source-scoped evidence files and original tests unchanged."}
```
