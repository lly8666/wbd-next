# PLAN027 H887｜Auto/Normal 共用修复后的原生 repair-paced wake 测试契约

- Recovered H886 SOURCE `e5f2e32977f3b4c6098c8ff2b1d957e0e00dd00f` governance-maintenance Action41396919281 negative test FAIL, not native product failure: `tests/test_m0_plan027_auto_normal_outer_repair.py` still asserted that original Rust NativeOwner TX had text `let shadow_due=m.shadow.next_deadline();`, deleted by H884 purposefully. H884 now uses `m2_repair_deadline(m.shadow.next_deadline(),m.repair_retry_after_ns)` to prevent already overdue shadow from causing Wait(0) while the existing real 5ms burst pace is active. The same TX path handles Normal and Auto: no separate Auto retransmission implementation.
- H887 fixes only this stale exact-source expectation: require new single call, presence of paced future deadline precedence, absence of the old obsolete text, and keep existing actual `m2_next_repair_entry` and complete-result code evidence. Separate Windows Rust unit test already checks the two actual clock cases (paced5ms versus overdue wake0).
- H886 Game4 outer OFF true signed original Windows/Linux native Action41396919297 remains independent/in progress. H884 Normal true sameVM 30%-loss Action41395887599 and H883 Windows-origin105 Action41395214862 remain independent/in progress. This commit explicitly uses `[plan026-coding]` to avoid rerunning a new full native batch solely for an outdated test text; no second game/normal scene, physical deployment or product claim.

```feature-impact
{"kind":"none","ids":[],"reason":"The shared Normal/Auto paced wake is already in H884 source; only update a stale assertion that looked for the removed old shadow deadline text. No product/CLI or feature-card change."}
```
