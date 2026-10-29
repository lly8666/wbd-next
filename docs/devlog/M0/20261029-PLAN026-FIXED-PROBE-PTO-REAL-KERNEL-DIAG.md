# M0 PLAN026 Linux Fixed real frozen send diagnostics (scope only)

Original Linux kernel artifact run 40824537833 contains 9/9 genuine post-M3 Fixed mixed-prefix and 2-slot sendmmsg failures. The real Linux TLS, fixed request/pending/applied M2, RS16 source missing recovery, raw kernel M4->real TUN UDP app and backwards M2 feedback all show positive test evidence. The failure occurs later in `fec2_probe_real_frozen_repair_one` and `fec2_probe_real_frozen_repair_prefix_two`, with BAD_STAGE=3 for single and INVALID=1 for prefix/multimsg. The original workflow suppressed `real-kernel.log` in Actions by redirecting output on exit, requiring artifact inspection.

Fast diagnosability: add bounded `eprintln!` scope fields only in the existing `m0_fec2_owner_probe` functions, never public production packet hot path or credential/epoch material. Fields phase, worker presence, feature7, native owner bound, raw_tx and sender availability, global probe clock expected PTO and actual count of releasable/candidate shadows. Strict original Go tests and actual sendto/sendmmsg/PN/driver outcomes unchanged. On exact source re-run collect `M0_FIXED_DIAG` lines from the artifact; do not infer PASS from legacy stdout or skip real Linux tests.

```feature-impact
{"kind":"none","ids":[],"reason":"Opt-in Linux original kernel Fixed failure-specific scope and PTO diagnostics only, no packet, quota, M2 or production behavior modification."}
```
