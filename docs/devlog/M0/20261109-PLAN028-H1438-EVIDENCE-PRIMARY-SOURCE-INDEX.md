# PLAN028 H1438 — citable evidence primary SOURCE

H1436 combined native ARM64 and Windows+Linux L3 originally recorded both exact source SHA in nested platform objects, but the governance cursor references evidence only if it also declares top-level `source_sha` equal to `last_tested_source`. This missing **index** caused original H1437 feature catalog and governance structural FAIL before product checks, not a product failure. Add exact ARM64 original `eef2a813...` as primary tested SOURCE; Windows `d6aeb646...` remains distinct nested `NOT_QUALIFIED`. Existing original ZIPs, all pass/fail history and the H1437 in-flight one-Windows native Action are unchanged. No changes to governance validator or feature catalog policy.

```feature-impact
{"kind":"none","ids":[],"reason":"Exact source index on existing two-platform evidence; no product or feature change."}
```
