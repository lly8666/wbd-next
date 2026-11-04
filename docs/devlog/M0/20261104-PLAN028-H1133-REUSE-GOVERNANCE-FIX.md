# PLAN028 H1133 — CI exact preflight-if compatibility, preserve full product binary reuse

[H1132 Action41817588338](https://github.com/lly8666/wbd-next/actions/runs/41817588338) **FAIL_PRE_NATIVE** in `tests.test_delivery_ci.test_preflight_has_no_native_runtime_or_driver_effects`: narrow source reuse H1129 added `!contains([plan028-win-reuse-h1129])` to preflight job `if`, but the governance test correctly asserts its exact established compilation-only expression. The native Windows test was therefore SKIPPED; no product failure/Windows proof from this Action.

Restore the three original cheap Windows Go and Rust preflight expressions, keeping them compile/unit-only, no driver mutations. Preserve H1132 explicit source-frozen `[plan028-win-reuse-h1129]` run 41815388333 artifact SHA, skip only actual Windows/Linux **product binary rebuild** via exact native SHA/repository diff gate. One original signed Npcap/Wintun/WSL2 Normal real two-generation test with already-added per-generation Windows OS MTU/SYN/SYNACK verification. All Go/Rust product SOURCE unchanged (1bb73998); user outer1460 intact.

```feature-impact
{"kind":"none","ids":[],"reason":"Restore exact governance-preflight condition only while retaining already-built original Go/Rust H1129 binary reuse; no product behavior changed."}
```
