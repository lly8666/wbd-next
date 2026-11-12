# PLAN028 H1633｜保留H1632 wrapper失败，修一处场景来源 ID（无Native启动）

Original [H1632 wrapper Action43138076757](https://github.com/lly8666/wbd-next/actions/runs/43138076757) **FAIL**, job130918127550; failure at pre-dispatch Python canonical scene assertion. New Auto actual source scene ID `plan028-h1632-auto-on-10m250ms30-outer1460-60s` was correctly selected, but the wrapper's expected old baseline clone ID still said `plan028-h1632-normal-on-10m250ms30-outer1460-60s`. Actual original normal baseline + only ID/MTU/mode changes is intact; no GH native target Action dispatched, original signed Go/Rust/Wintun and network 30% Auto **NOT_RUN**. This is a **test-only source-lock oracle typo**, not a product FEC/AEAD/MTU failure. Correct exactly the one expected scenario_id string; keep entire source-diff guard, original single scene and test. Push will trigger exactly one new wrapper and, only if preflight is true, one independent signed Windows target; never mark wrapper SUCCESS as business qualification.

Normal Off same original product SOURCE8a damaged 30%/250ms Action43136758689 remains PASS_SCOPED genuine TCP/UDP and Stop only, first-delivery ~72.3%, missing 28% not hidden. The Auto trial explicitly opts in FEC, product default remains Off. H1630/H1631 current source 7-mode native Linux x86 PASS_SCOPED, independent A/B/C Windows L3 environment unavailable and previously user-skipped near-innerMTU/multiWintun not retried. No 029/030.

```feature-impact
{"kind":"none","ids":[],"reason":"Single source-locked test wrapper expected scenario-id typo fixed before any network dispatch; no product, native configuration or default changed."}
```
