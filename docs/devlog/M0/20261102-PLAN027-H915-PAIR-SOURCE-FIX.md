# PLAN027 H915｜同VM Normal100 OFF PASS 被夹具 SOURCE 混淆挡住 ON 段

- H913 [run41419832546](https://github.com/lly8666/wbd-next/actions/runs/41419832546) job returns FAIL solely because pair script after **genuine first OFF leg PASS** incorrectly did `report.source == product_SHA`; actual `report.source=ae2779f8...` is fixture SOURCE, while `report.linux_binary_source=6693910f...` is correctly verified H908 binary SOURCE. This pair must preserve both identities, not overwrite either or change source manifest. Product original Windows/Linux kernel OFF100M real first=.999985/1.0, 99.48/100Mbps offered, both owned Stop, R0 F821,852,694B C1,039,610B, Windows whole CPU9.0312s RSS41.81MB, no tc drops. **ON NOT_RUN**, no causal CPU delta.
- H915 minimal fix of existing `tools/m0_wl_outer_pair.py` predicate: check `report.source == GITHUB_SHA` (fixture source) and `report.linux_binary_source == WBD_WL_BINARY_SOURCE` (product source). Keep exact signed Windows EXE sha256 verification, legacy Go TLS, Rust owner, original driver, Stop, 95% offered and F/R/C budget. Include tool path in existing workflow push filter so the exact H915 source runs the one original pair Action via the existing `[plan027-pair100]` marker.
- H914 concurrently dispatched three independent original two-OS Actions: Auto ON 41420568736, Game2-FEC6 ON 41420572398 and Game4-FEC6 OFF20M 41420575955; all still SOURCE H908 signed reuse, no rebuild, no premature PASS.
- No core product change; no second controller/mode/config. No physical machine.

```feature-impact
{"kind":"none","ids":[],"reason":"Correct fixture-vs-product SOURCE provenance in same-VM Normal high-PPS performance harness; no transport, feature or configuration change."}
```
