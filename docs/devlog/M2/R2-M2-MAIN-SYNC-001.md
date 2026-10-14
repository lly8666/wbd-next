# R2-M2-MAIN-SYNC-001 · M0-reviewed one-off main-sync

Authority: M0 decision docs/decisions/M0-M2-recovery-root-sync.md, main registry M2 active revision2 epoch1. Original worker HEAD 2cd993a9675d38dcbe161bdebf093c0890734fdf unchanged before merge. Ingress 29ebcb19863602ae1fc059fa3524837e90944da9 verified ancestor of exact main 35dfef868b9f16f2bd63f93bc2b30fddb745fd1c.

Actual first-parent worker/second-parent main merge cfc77b9b21339defb30f4f799b1fe62f37b57772, no rebase/force/rewrite. Relative to second parent only M2's private cursor and previous receipt devlog/evidence differ (3 files); main Cargo/lock/recovery Cargo manifest and M0-authenticated receipt Rust code preserved.

Exact merge SOURCE 14/14 push Actions SUCCESS, including worker-native run38558987984 compiled once, 8/8 original r2_ tests; Governance38558988090; historical G2 corrected selector38558987961; the R0 static, Go, codec, platform, ABI regressions listed in docs/evidence/M2/R2-M2-MAIN-SYNC-001.json. Historical failed old run38538225378 stays FAIL on old SOURCE; do not retroactively green it.

This merge changes integration baseline, not the R2 algorithm. V4 live admission and true product/network remain NOT_RUN. Next independent authorized atomic task R2-M2-BUDGET-001 only after cursor H; never change shared Cargo/engine/platform.

