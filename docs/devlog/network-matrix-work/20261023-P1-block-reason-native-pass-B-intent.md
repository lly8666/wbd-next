# 2026-10-23 P1 exact block reason native PASS → one B-only observation

Native Action39896777307 SOURCE `d9dc8c8646e1513be4e6638c97d5e0e50af7af70` SUCCESS. Product artifact12476734780 SHA256 `4e5e3248b489877eb50eece577719c780e16b31add1bca2c76d407f04196628f`; MTU9 artifact12477038098. Classifier, adaptive RTT, retirement diagnostics, Fixed M2 and all nine MTU/DF/Stop cases PASS.

Behavioral burst experiment is reverted. Relative to the known authentic-RTT diagnostic behavior, this source only splits the existing aggregate blocked counter into ten pre-Stop read-only reasons: fresh-global, fresh-shadow, grant, BurstPaced, QuotaExhausted, capacity, stale, local-other, global-other, invariant. No packet, retry, queue, timer or auth decision changes.

One B-only exact prior scenario is therefore sufficient. If bucket sum differs from aggregate, diagnostic itself fails; otherwise modify only the dominant earliest cause.