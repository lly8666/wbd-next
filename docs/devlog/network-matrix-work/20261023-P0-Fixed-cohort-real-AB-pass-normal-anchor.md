# 2026-10-23 P0 Fixed cohort real A/B PASS on B; one Normal protective anchor

[Action 39890061224](https://github.com/lly8666/wbd-next/actions/runs/39890061224) ran old a58d then new 18860 on one ARM64 VM. Overall workflow FAIL is **expected A-control failure**, not B failure.

A old: client Fixed requested1/applied0/pending; server applied1. B new: **client+server requested1/applied1/pending=false**. B four real traffic cohorts each sent/delivered 11,767 with **0 missing**; p99 c2s UDP211.3ms/TCP220.7ms, s2c UDP211.4ms/TCP220.8ms under actual ~2% IID and 200ms one-way. B recovered-to-TUN FEC 1210 client /1122 server; all source/parity payload/arena/seal/M4 noncopy failures zero; Stop both sides PASS. Product process CPU 8.78s/8.78s over warmup+120s+drain, similar to A 8.77/9.00s; this is not a CPU optimization claim.

Critically, B still reports historical authentic M2 UNKNOWN/censored (client unknown2s9, server8; both censored1), proving the new logic did **not** erase old unknown evidence to manufacture APPLIED. A later contiguous genuine 2s-mature authenticated source cohort is sufficient; scope/capacity errors remain fatal while the clean cohort is formed. This closes the client pending defect at the exact P0 point.

Do not rerun Fixed. One 60s Normal/off anchor on source18860 now checks the non-FEC original business path under the same 2%/200ms near-MTU mix, explicitly requiring real outer retransmission and Stop. Its purpose is regression protection only, not performance tuning. Then P1 starts.
