# PLAN027 M0 — first bounded outer ACK/SACK retirement primitive (not live wiring)

2026-10-30. Recovered latest main, registry M0.goal, cursor H377 and PLAN027. Main HEAD before code `05b29a9582eb93500e77c79172859ff749b6b630`. Latest original-source CI governance and maintenance both SUCCESS at Actions 40925207285/40925207309; do not repeat older tests. The exact new code commits are `0730d317d2ab93ea9f94662b404fe5d1dac89576` and `4edec16e3f0e4449b83ff083aba2a28179c73650`.

## Actual code change

Added `crates/wbd-recovery/src/outer_ack.rs`, exported in `lib.rs`. It is a pure, scoped, bounded outer presentation ACK/SACK retirement and missing-gap *hint* index, not a replacement already wired into either product. It binds a specific `LaneKey` and epoch, expands 32-bit TCP sequence numbers around the observed definite first-send high water mark, rejects ACK/SACK outside the actual sent interval or wrong generation, only retires complete frozen-record spans, and yields at most 32 gap opportunities after a caller-specified reorder guard. Its 24,576-entry hard maximum, oldest-sequence expiry and optional full-cache skip never block fresh DATA. No per-packet bitmap or separate actor, no TLS/AEAD/PN/driver changes. Untrusted outer ACK/SACK is deliberately **not** a business-delivery, authenticated-live or Auto-loss signal. Four pure tests cover SACK gap/guard, 32-bit rollover/epoch isolation, partial/stale/malformed ACK and full-cache expiry.

**This is an intermediate implementation only.** Neither Windows nor Linux calls this index yet; the existing online M2 per-record Receipt and hot dependency remain active, and replacement low-rate Quality/Health, original frozen-cache retirement and one-shot repair are NOT yet complete. Do not claim PLAN027 §0 item1, A/B/C or full product PASS from this code. The new SOURCE requires CI; all prior exact-source seven-mode and Auto/Health evidence remains historical. No new throughput matrix or manual Action dispatch was started.

## Next product batch

1. Add owner-side retirement of frozen shadow by these scoped ACK hints and real gap candidate selection, respecting global 1s F/R/C ledger and one-shot original ciphertext. Integrate presentation ACK/SACK at Windows and Linux outer carrier ingress, keep control/Health separate.
2. Implement bounded mature directional Auto quality windows and reports, actual first-send accounting, and old-Go Health/idle behavior; only after both sides/config/cards/fixtures are ready, retire all live per-record M2 Receipt emit/consume paths.
3. Freeze new SOURCE, reuse compiled artifacts and execute PLAN027 A, then remaining B lifecycle, C capacity matrix, necessary fixes and delivery. A failure of any necessary stage remains OPEN, not a completion exemption.

## Recovery note

Previously failed Windows WAL Action40915929426 is a real original signed Game2/4 Stop failure: original Go test observed `Game2 client native Stop: ... C ABI rc=5`, then its failure-path `TUN.Close` waited for a goroutine and the Go test timed out after 8 minutes. It is separate from the successful Game2-only Action40915929519 and remains a B lifecycle regression to investigate after the prioritized PLAN027 feedback replacement; do not mislabel it as a mere governance issue.

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Added source-only scoped bounded outer ACK/SACK hint index and pure tests as PLAN027 replacement foundation; live M2 retirement and network qualification remain pending."}
```
