# 2026-10-23 P1 BurstPaced one-short-rearm native PASS → one same-VM AB

Exact block-reason Action39897262285 showed client/server aggregate blocked265/262, of which BurstPaced was256/258 (**96.6%/98.5%**); quota only9/4 and fresh-global, shadow, grant, capacity, stale, local/global-other and invariant were zero. With PTO~435ms and cache~921ms, treating a transient local pacing rejection as NotSent+full-PTO fallback wastes much of the first-repair lifetime.

SOURCE `396c5ae6434c18eecb16599f5966574716c604a9` changes only that fallback: each repair-attempt stage may be re-indexed once at the existing <=20ms candidate dispatch deadline when the local reserve says BurstPaced. A second pacing rejection at that stage uses the original PTO. No actual attempt is charged by the pacing rejection; max accepted/uncertain repair attempts remains2. Quota, 8-MTU burst cap, long-run pace, auth/replay/scope, immutable ciphertext, fresh scheduling and Stop are unchanged.

Native Action39897775082 PASS: new `r2_burstpaced_candidate_gets_one_20ms_deferral_per_attempt_without_extra_repair`, adaptive RTT, retirement diagnostics, Fixed M2, release product build and 9 MTU/DF/Stop. Product artifact12477318789 SHA256 `0070cc62106aac883817f7600a1dc0f82340d8463a6fd38c797148c7cde1c1ea`.

Next: one same-VM A=d9dc old fallback vs B=396c short-rearm on the exact failed Normal2%/200ms/60s seed5205 scenario. No additional tuning or seed retry.
