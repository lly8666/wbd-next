# 2026-10-23 P1 20ms BurstPaced rearm falsified → first repair hard-quota priority

Same-VM Action39898816654 compared A=`d9dc8c8646e1513be4e6638c97d5e0e50af7af70` and B=`396c5ae6434c18eecb16599f5966574716c604a9` on the exact Normal 2% / one-way200ms / 60s scenario. Artifact12478455486 SHA256 `07fb62e0e5dd8672e8065a76fb6e60138f54d59df340347e91b333d1dd3e44ad`.

B is a clean negative: host contention warning disappears and its C2S netem loss is lower (1.678% vs A2.014%), yet B UDP residual is **2.736%/2.481%** vs A **2.362%/2.447%**. expired-before-any-repair stays111/112 vs108/110. B records145/159 short deferrals but239/247 pacing→PTO fallbacks. At the sparse pace floor a 1500B token needs ~45.8ms from empty, so a fixed20ms retry is structurally too early. Stop remains PASS; no capacity/driver/invariant failure excuses this.

More importantly, BurstPaced count is larger than the entire retry-candidate population. Even assigning every retry candidate one burst failure, at least A119/101 and B232/250 client/server BurstPaced events occur at **repair_attempt_stage0**. That is direct evidence the smoother is rejecting first-delivery rescue work.

Next mechanism follows task priority rather than another wait constant: revert the failed short-rearm product path to d9dc; owner-created `RepairCandidate` carries its actual pre-dispatch repair-attempt stage and preflight requires it still match the shadow entry. Stage0 remains bounded by the existing per-epoch `max(F/10,32KiB)`, process/global caps, immutable ciphertext, auth/scope and hard expiry, but may pass an empty smoothing bucket. It drains whatever tokens are present; NotSent refunds only the exact token debit, so no credit can be minted. Stage1 remains under the existing 8-MTU token pacer. Actual accepted/uncertain repairs remain max2. There is no payload wait queue and fresh traffic never waits.

This source change is native-unverified until its Action passes; no real business PASS is claimed by the unit.
