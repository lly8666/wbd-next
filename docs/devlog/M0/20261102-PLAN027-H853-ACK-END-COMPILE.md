# PLAN027 H853 | Fix H852 pre-native Rust compiler E0425, no measurement result

- H852 dedicated source build [Action 41373112995](https://github.com/lly8666/wbd-next/actions/runs/41373112995) **FAIL BEFORE BUILD** in `cargo test --locked -p wbd-recovery --lib outer_ack::tests`: `outer_ack.rs:114` `end` local no longer in scope after delegating monotonic bound validation to `on_unretained_firstsend`. This is not a product performance/actual Linux native result; no bundle artifact or traffic job executed.
- Exact fix: replace `SentSpan {end,...}` with `SentSpan{end:self.highest_sent_end,...}` after the public method has validated and updated bound. No change to optional shadow selection, F/R/C, budget, ciphertext, generation, Stop, config or Go. Repeat only one build/unit Action using unchanged compiled source guard. H852 intended optimization remains **not measured** until native evidence; prior f5 100Mbps Rust TX ON overhead~79% remains baseline.
- Keep H848 reauth source e928 native INCONCLUSIVE, full PLAN027 partial.

```feature-impact
{"kind":"none","ids":[],"reason":"Correct Rust compile of existing shared index refactor, no additional product behavior or public parameter."}
```
