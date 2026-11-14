# PLAN029 H1802｜恢复记录：游标 evidence 必须与 last tested SOURCE 一致

- [Action 43562204291](https://github.com/lly8666/wbd-next/actions/runs/43562204291)：修正 H1801 功能卡枚举后，Feature Catalog `check` 与 38 项 Python selftest 均通过，但 Governance `validate` 输出 **BLOCKED: evidence is for a different SOURCE**；因此整个自动治理 Action 仍红。不是网络数据面回归。
- `tools/governance.py::validate_repo` 要求所有 `cursor.evidence_refs[].source_sha == cursor.last_tested_source`。保留 H1799 的 6a77d23 正确真实证据在 evidence_refs，把 H1795/TCP53 与 H1791/1460 两个旧 SOURCE 实测记录移到 `context_refs`，为满足每种引用 ≤8 上限，轮换掉两个更老诊断历史链接（它们本身仍在 git/旧 evidence）。不更改原始 JSON、不把历史结论升级为当前 SOURCE。
- `unverified=true`、`progress=in_progress`、D3-D5/P1-P2 和 GUI live effective 全部维持未完成。No manual dispatch / no old matrix / no forced ref update。

```feature-impact
{"kind":"none","ids":[],"reason":"Governance-only cursor provenance fix; no product configuration, verification scope or runtime behavior changed."}
```
