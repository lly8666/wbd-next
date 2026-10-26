# 2026-10-23 P1 exact block reasons: BurstPaced dominates; fix fallback semantics, not quota

B-only Action39897262285 on behavior-restored source d9dc reproduced the Normal residual. Block buckets exactly sum to aggregate blocked. Client: blocked265 = BurstPaced256 + Quota9. Server: blocked262 = BurstPaced258 + Quota4. Every fresh-global/fresh-shadow/grant/capacity/stale/local-other/global-other/invariant bucket is zero. Driver uncertain remains zero; Stop passes.

This proves the earliest dominant failure is transient local pacing. It does **not** justify raising repair quota: quota exhaustion is negligible, and the earlier cap-only experiment already failed.

The actual semantic bug is that a BurstPaced reserve failure was settled as NotSent and immediately rearmed by the full ~435ms PTO. With ~921ms cache, a true lost record can spend about half its lifetime waiting even though no repair was attempted.

SOURCE `396c5ae6434c18eecb16599f5966574716c604a9` changes only that branch: one short re-index at the candidate's existing <=20ms dispatch deadline is allowed for each actual repair-attempt stage; if pacing rejects the same stage again, the old PTO fallback applies. No payload queue is retained, repair_attempts is unchanged, max actual repairs stays2, quota/burst cap stay unchanged, ACK can retire the entry during the short interval, and fresh traffic never waits. Two read-only counters expose short deferrals and fallback-to-PTO.

Unique native run39897775082 is pinned; no performance run until it passes.