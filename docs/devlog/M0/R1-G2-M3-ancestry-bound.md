# M0 scoped ancestry bound repair — 2026-10-14

Task R1-M0-G2-M3-ANCESTRY-001. Source M3 native55/55 and main authenticated FEC2/2 are independently qualified. The worker H Governance failures 38569000801/38569111816/38569516952 are genuine G2 metadata failures, not codec failures. Original main control tool limited per-page GitHub comparison to 64 even though actual anchored M3 history has 67 exact commits at HEAD 56907bdb.

M0 increases ONLY the upper accepted page length to 96 (below exact 100-commit GitHub response limit) and factors the prior per-commit checker without changing role ownership, allowed paths, merge approval, replay of every commit path, rename checking or live control ancestry. Extra exact negative unit cases reject 97, truncation 67→64, divergence, duplicate/invalid SHA. Dedicated Actions on main uses same per-commit code against the live M3 branch and immutable commit list, recording full counts and refusing concurrent move.

M3's worker checkout still contains its previous tool code. This M0 main-only patch is NOT an assertion that a future M3 worker Governance run already passes. An authorized and separately attested main-to-worker tool synchronization remains necessary; no worker ref reset/force-push, no provisional waiver, no product/pass.

## Exact root-boundary Actions proof

Final main CODE SOURCE [`c00356739359db90a864f0894d8cdd965b2df132`](https://github.com/lly8666/wbd-next/commit/c00356739359db90a864f0894d8cdd965b2df132): [Governance #38582967916](https://github.com/lly8666/wbd-next/actions/runs/38582967916) SUCCESS; [live M3 every-commit audit #38582968224](https://github.com/lly8666/wbd-next/actions/runs/38582968224) SUCCESS. Audit ran all 67 actual anchored commits: 40 worker path checks and 27 explicitly verified main ancestor exceptions, original strict 2-parent sync restrictions unchanged. Ten tests rejected mismatched commit lists, arbitrary duplicate SHA, 97 commits, behind/diverged and malformed input. Workflow artifact 11903487977 digest sha256:cbe5e8da6c7f6fe570b59f4d6f52709f3992a10aff4847cc13bf2ee6aaa6e86b. Source-exact receipt `docs/evidence/M0/R1-G2-M3-ancestry-bound.json`.

**OPEN:** M3 worker's own branch has not received the control-tool correction, so prior H still FAILED; this attests the same exact worker HEAD read-only from main, not a governance waiver. A subsequent controlled G2 branch tool-sync/activation is required. M0 did not move M3 or other worker refs.
