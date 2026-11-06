# PLAN028 H1284 source-lock assembly manifest reconciliation

First native x86 and ARM64 H1284 runs at SOURCE `250beac0d6f2a204d75c59703eef12b7c8f1ff24` all stopped BEFORE Go/Rust compile with `FEC2_ASSEMBLY_REJECTED: overlay result blob mismatch: internal/realityfront/admission_v4.go`. This is not a performance or protocol result. The source code from the same commit changed the exact original-Go `admission_v4.go` blob to `404c9e56d6f982d404d10eb2680bdabdc6ec4c7e`, while manifest was pinned to `4605f21aaeadd07985c86ef2880e8635605ec601`.

This H1284 follow-up updates ONLY the existing assembly operation's `result_blob` to its actual audited blob SHA. Legacy source pin, Rust source, upstream Go paths, binary flags, authenticated native runtime, manifests, test thresholds and normal/Game protocols remain unchanged. The new commit SOURCE must be used for all fresh binary builds and scenes. Prior failed Actions remain FAIL at their own SOURCE, never converted into tests.

```feature-impact
{"kind":"none","ids":[],"reason":"Fix exact-source pinned assembly manifest metadata to match already declared H1284 native authentication implementation, without changing any feature behavior."}
```
