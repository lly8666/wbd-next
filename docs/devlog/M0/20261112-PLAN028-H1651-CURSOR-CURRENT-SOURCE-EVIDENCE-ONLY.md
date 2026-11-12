# PLAN028 H1651 | Preserve governance SOURCE evidence invariant without deleting historic failures

Pre-fix main `9c7e0b5703d83c0dcc41ebf4aa9abf6d08312ec3`; [Action43165648809](https://github.com/lly8666/wbd-next/actions/runs/43165648809) **FAIL** under two required CI gates. Feature Catalog's standalone `feature-check.json` had already **PASS** on correctly-scoped `FUNCTIONAL_PASS` verification enum, but its overall job still exited2 because it also enforces governance structure. Main governance raw `structure.json` read `{"state":"BLOCKED","reason":"evidence is for a different SOURCE"}` (artifact13919607809); Feature Catalog raw artifact13919229543 has same evidence-source block. **Original FAIL must stay.**

Root cause H1650 correctly advanced M0 cursor `last_tested_source` to current fully built/signed `52767d183b61eaf2621d967b16e85e644b1de428` but accidentally retained 6 historic SOURCE `8a31375e36bb6a93860c5579e64b4a39d0b6e346` evidence paths inside its `evidence_refs`. Existing `tools/governance.py` line336 requires **every** directly referenced evidence JSON `source_sha == cursor.last_tested_source`, with no exceptions even when `unverified:true`. Fix exactly: M0 cursor direct `evidence_refs` holds only the two H1650 real raw-ZIP audited SOURCE527 files for current Windows GUI354 and formally signed Windows/Linux seven-mode native. Historic SOURCE8a pressure/mixed Five-client strict rejudge reports remain readable unchanged from `docs/testing/PLAN028_M0_ACCEPTANCE_COVERAGE.md` and their original devlogs; do not mass-delete history or change their source SHA. M0 `context_refs` still points to acceptance coverage and H1650 devlog.

No weakening `.governance/policy.json`, `tools/governance.py` or any runtime/authentication/MTU/FEC defaults; no fresh product tests needed for purely cursor index correction. Verify new Governance **and** Feature Catalog latest Action terminal SUCCESS; do not call prior FAIL PASS.

Remaining PLAN028 source527 signed AES128/256 and GUI-originated true signed Wintun original TLS + Rust M4, default1460 damaged representative, true failure-inclusive p99/independent Windows 1800s L3 are still separately open or infrastructure-limited, not reclassified. User-skipped near-derived-MTU and same-host dual-Wintun remain untouched, no PLAN029/030.

```feature-impact
{"kind":"none","ids":[],"reason":"Only current SOURCE-scoped M0 cursor evidence pointers and handoff note; no product, default or governance policy change."}
```
