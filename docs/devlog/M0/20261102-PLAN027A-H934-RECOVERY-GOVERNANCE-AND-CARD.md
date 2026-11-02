# PLAN027A H934｜H932/H933治理失败的最窄修复

实际 H932 `f2a6644908ecf567bed17987e51099e5cbd0d7da` 和 H933 `49e6b89ca56482f5b1bcf45cf6cdb5e149f8ae61` 治理 Action `41441674213` / `41441864456` **FAIL**，role audit 均为 `SCOPE_AUDIT_FAILED: unbounded context_refs`（H932生成 cursor 长度9、原规范限额8）；原失败不回写成通过。本批仅裁剪成最新8条有用context（证据本身不删除），不引入新的M0工作恢复器。

功能卡原 `defaults["--outer-mtu"]="1500（默认）"` 为旧说明，虽H932新代码及另一字段已改1460，仍误导；本批精确修成1460且最大1500。原 H932/H933 feature-catalog gate 也 FAIL，先确保本次修改有明确feature-impact，不猜测不刷场景。

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"Correct stale default 1500 in feature card after user default1460 change and bound M0 cursor context_refs to governance max8; do not rewrite prior failures."}
```
