# PLAN027 H860 | H859 builder fixed checkout digest before product build

- [Action41378295483](https://github.com/lly8666/wbd-next/actions/runs/41378295483) FAIL before original Go/Rust compilation, because new builder `actions/checkout` pinned `11d5960a3267500d...` (one extra `0`) instead of exact trusted `11d5960a326750d5838078e36cf38b85af677262`. Fixture-only error, **PRE_SOURCE, native NOT_RUN**. Correct one literal only and rerun one builder. All product Go and Rust diff from H859 identical, no new behavior, no scenario dispatched yet.
- Keep exact original cold stage marker security and Windows true OFF gap; don't mark preflight failure a product capacity or source test result.

```feature-impact
{"kind":"none","ids":[],"reason":"Fix one incorrect checkout action pin; product and business unchanged."}
```
