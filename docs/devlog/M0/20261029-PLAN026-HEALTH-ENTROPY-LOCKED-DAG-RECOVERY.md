# PLAN026 M0 — restore locked workspace graph for control RNG

SOURCE aca2407c first compile attempt Action40908898001 failed **before Rust type checking**: direct `aws-lc-rs` in `wbd-engine/Cargo.toml` modified the locked R1 dependency graph; first commit omitted lockfile, second SOURCE53cff added lockfile but triggered actual `R0_STATIC_AUDIT_FAIL: crate wbd-engine dependency is not the locked one-way R1 graph`. Both are build/architecture negatives, not product code FEC/Game/Health runtime FAIL.

Repair without loosening R1 governance, rustfmt/lock or adding any new crate: restore engine Cargo.toml and Cargo.lock **byte-exact from source8a7caa1**, keep aws-lc-rs in its already-pinned preexisting `wbd-codec` dependencies, expose one safe `wbd_codec::fill_control_entropy` helper using the EXISTING audited CSPRNG and forward only control-send low frequency jitter/padding calls. Core Game OFF staged Wintun commit, NPF one-lane isolation, merged Health+Quality implementation remains unchanged. No new wire kind, security / MTU checks intact. The new SOURCE must pass `cargo --locked` before product native proof.

```feature-impact
{"kind":"none","ids":[],"reason":"Restore unchanged engine locked dependency graph after source53cff compile-only and architecture policy failure; use already-pinned codec aws-lc control CSPRNG without changing any public feature behavior or marking native PASS."}
```
