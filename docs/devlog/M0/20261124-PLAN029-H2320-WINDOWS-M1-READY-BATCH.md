# H2320 — Windows Normal/off M1 ready batch, PLAN029 P0

Baseline H2318 compiled on Windows. Existing original M1 TX queue reserves 32 ready slots and a 50ms expiry; native stage captures only already-ready 8/16 packets. Before this increment each packet sealed, drained a one-record LoanBatch, checked it, cloned the pending frozen handle and recycled the loan container, despite one outer NPF batch.

Queue original Normal/off M1 records using one stable budget and monotonic timestamp under the existing Entry lock, then drain/recycle once per ready 8/16 (or sparse 1) source batch. Cold TX scratch capacity 8→16 fits the already-supported experimental TX16. Same original AEAD/PN/Seq, pending driver settlement, original frame/MTU, no extra wait, queue, thread, telemetry or recovery changes. Fixed source/parity and existing Go one-record ABI preserve their behavior. The helper also services the existing single-source path. No source batching across owner turns.

Expected: for a full 8/16 source turn, 7/15 fewer LoanBatch creations and releases, ready drains, time and budget derivations. Not a measured speedup; NPF kernel service may still dominate. Native Windows unit tests include 16→1→8 ready turns with alternating padding, continuous PN/Seq, copied bytes identical to the pending frozen record, uncertain settlement and owned Stop. The automatic H2311 native matrix now runs the actual unit and watches the owner/carrier files. Real performance NOT_RUN. H2319 prevents 49 historical network workflows from launching on this normal source push; historical assertions remain intact.

```feature-impact
{"kind":"none","ids":[],"reason":"Internal batching of existing ready Normal/off source records; no protocol/configuration/feature change or performance promotion."}
```
