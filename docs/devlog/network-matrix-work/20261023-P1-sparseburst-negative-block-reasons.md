# 2026-10-23 P1 sparse-burst AB negative; revert and split blocked reasons

Same-VM Action39896018098 falsified the 32KiB burst hypothesis. Old21b1 UDP missing150/139; new dce9 missing137/146, both >1%. expired0 old109/114 vs new112/119; aggregate blocked old268/280 vs new312/326; product CPU essentially unchanged; Stop both PASS. TCP tail did not improve.

The aggregate `repair_blocked` was then audited and found to conflate four stages: fresh ledger/shadow registration, global grant, scoped reserve, and pointer invariant. Therefore it could not prove BurstPaced was dominant. The dce9 burst behavior is reverted exactly to the pre-experiment budget implementation.

New SOURCE `d9dc8c8646e1513be4e6638c97d5e0e50af7af70` is diagnostic-only relative to old21b1 behavior: ten read-only pre-Stop buckets distinguish fresh-global, fresh-shadow, grant, local BurstPaced, local QuotaExhausted, capacity, stale, local-other, global-other and invariant. Existing aggregate remains and bucket sum is intended to account for every increment. No packet content, scheduler mutation, retry increase, crypto/auth change or new queue. Unique native run39896777307 is outstanding.
