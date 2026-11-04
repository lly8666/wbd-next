# PLAN028 H1153 — repair one workflow parser error before native mixed scene

H1152 [Action41847324156](https://github.com/lly8666/wbd-next/actions/runs/41847324156) returned workflow-parse FAILURE with **zero jobs**. The generated first-step test regex contained literal `$'`; treating that as JavaScript string replacement syntax copied the remainder of the YAML into the replacement and left a second `retention-days`/unindented shell fragment. The previous original H1151 workflow was structurally sound. This failure occurred before Go build or native packet processing, and must not be recorded as a product test failure.

H1153 rebuilds exactly the H1151 known-valid workflow blob and adds the new protected five-policy unit using literal-function string replacement, yielding a single 9,813-byte YAML with one artifact clause, one source build and one x86/x86 native real UDP scenario. Product Go/Rust and ephemeral physical netns fixture are untouched; H1152 `var err` Normal shared owner method fix is retained. Do not run historical matrix, no extra per-helper Action.

```feature-impact
{"kind":"none","ids":[],"reason":"Only repair a malformed new mixed-mode workflow YAML before it ever scheduled a runner; application source and native scene unchanged."}
```
