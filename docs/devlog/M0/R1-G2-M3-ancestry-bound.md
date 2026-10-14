# M0 scoped ancestry bound repair — 2026-10-14

Task R1-M0-G2-M3-ANCESTRY-001. Source M3 native55/55 and main authenticated FEC2/2 are independently qualified. The worker H Governance failures 38569000801/38569111816/38569516952 are genuine G2 metadata failures, not codec failures. Original main control tool limited per-page GitHub comparison to 64 even though actual anchored M3 history has 67 exact commits at HEAD 56907bdb.

M0 increases ONLY the upper accepted page length to 96 (below exact 100-commit GitHub response limit) and factors the prior per-commit checker without changing role ownership, allowed paths, merge approval, replay of every commit path, rename checking or live control ancestry. Extra exact negative unit cases reject 97, truncation 67→64, divergence, duplicate/invalid SHA. Dedicated Actions on main uses same per-commit code against the live M3 branch and immutable commit list, recording full counts and refusing concurrent move.

M3's worker checkout still contains its previous tool code. This M0 main-only patch is NOT an assertion that a future M3 worker Governance run already passes. An authorized and separately attested main-to-worker tool synchronization remains necessary; no worker ref reset/force-push, no provisional waiver, no product/pass.
