# H594 — post-A5-retirement CI contract correction

H593 correctly deleted obsolete A5 workflow/test runner but its rewritten CI test accidentally substituted live WBD_WL_PUBLIC_MODES into six old A5-only negative checks: tests then rejected valid historical source selectors in the **active** mode. Restore meaningful negative test: absent WBD_WL_PERF_AB env/runner and retained strict source-SHA and native binary validation. Feature card reached >16KiB UTF-8 after accumulating historical Action notes; remove only obsolete duplicated H513–H573 prose (original evidence/devlog/action remain immutable). Live latest cb475 source run/caps and H593 limitations remain. No runtime code, test re-dispatch, old Go fix or network operation.

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Reduce stale duplicated feature-card historical prose to governance size; no product change."}
```
