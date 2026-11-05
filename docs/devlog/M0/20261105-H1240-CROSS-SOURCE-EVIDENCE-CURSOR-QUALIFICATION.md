# PLAN028 H1240 — multi-SOURCE PASS evidence cannot share a verified cursor

H1239 committed actual separate source-specific PASS H1237 (source ac8) and Windows H1238 (source f3c), plus partial audit source f3c. Initial cursor incorrectly claimed `unverified=false` with evidence refs mixing ac8 and f3c and audit result PARTIAL, which the repository governance correctly rejected. H1240 retains all immutable real PASS evidence, but cursor points only to latest f3c evidence and partial audit and is unverified/partial for the *full PLAN028*. This is a governance-only fix, no original Go TLS or Rust changes. Full PLAN028 still has outstanding physical/path and Windows mode scopes.

```feature-impact
{"kind":"none","ids":[],"reason":"Fix multi-source cursor scope, keeping H1237 and H1238 independent PASS evidence without a fictitious full Plan028 PASS."}
```
