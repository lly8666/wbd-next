# 2026-10-23 P1 first-repair priority exposes wall-clock quota alias → one-epoch unused credit

Action39900235569 shows the mechanism boundary cleanly. First-repair priority reduces BurstPaced from A244/254 to B21/22, proving stage0 no longer loses to the smoother. But B QuotaExhausted jumps from12/10 to351/361, actual repairs fall685/726→602/593, and expired-before-any-repair rises110/109→146/155. UDP remains2.18%/2.62%. Both legs Stop PASS, no host warning, capacity/driver/invariant buckets zero.

This is not a reason to increase the 10% repair rate. The local quota is a hard wall-clock1s bucket: unused allowance is thrown away at rollover, while authenticated receipt/PTO timer wakes are phase-bunched. Adjacent seconds can therefore be one overloaded and one underused even when long-run repair demand is below the allowed rate.

Minimal correction: at adjacent rollover compute `unused = base_limit(old)-old.charged` and carry at most `min(unused,32KiB)` into the **next epoch only**. Current `epoch_limit = min(max_repair_bytes_per_epoch, base_current + carry)`. If an epoch spends carried credit, its charged exceeds its own base so the following carry is zero. Skipped epochs also zero it. Late NotSent refunds do not retroactively create carry. Therefore for any adjacent pair, combined charged repair bytes remain <= the sum of the two original base allowances; long-run 10%/32KiB semantics do not increase.

Pure unit creates 20,768B real unused credit from epoch0, proves epoch1 effective53,536B admits exactly52.5KiB but rejects the next1500B, then proves epoch2 returns to32,768B with no second-generation credit. No queue, no new attempt, no auth/crypto change.
