# PLAN027 H706 — unit-test selector no-zero-test correction

H705 source8ae732 first focused Rust Game2/FEC6 due sealed-frame test Action41272782294 was dispatched; its `cargo test --lib m0_plan... -- --exact` could silently match zero because Rust lib test names include module path. No source/runtime error result may be inferred from that Action until logs. Correct the single workflow's argument by dropping `--exact`, and require an observed `running 1 test` line before any print claiming private frame-boundary verification. Same Rust unit under same feature flags, no runtime change, no new Windows native GameFEC 1Mbps run, no time increase or matrix. H703 actual source653 native cancel/BlobNotFound remains preserved and is not proof of due branch.

```feature-impact
{"kind":"none","ids":[],"reason":"Only correct focused Rust unit selector, prove exactly one test actually executes rather than zero-test false green; no product/driver/protocol/config change."}
```
