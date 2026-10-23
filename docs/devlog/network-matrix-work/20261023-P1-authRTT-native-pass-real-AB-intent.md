# 2026-10-23 P1 authenticated RTT native PASS → exact Normal old/new AB

ARM64 native [39892105601](https://github.com/lly8666/wbd-next/actions/runs/39892105601) source `2a388f743cde0ab6d69fb47e2c3f6cd9a6127301` PASS. Product artifact `12475695809` SHA256 `ce6768331557890b37c8d158e847a108dc54a90cdf54247605f9fd7ef31dab17`. New pure recovery unit `r2_adaptive_authenticated_rtt_drives_pto_reorder_and_cache_without_unbounded_retry` PASS; prior Fixed M2 clean-cohort unit PASS; all nine native MTU/DF/Stop cases PASS.

One real same-VM AB now replays the exact Normal failure point. A is source18860 static PTO80; B is source2a388 authentic RTT timing. Same seed5205, 2Mbps each direction, UDP/TCP50/50, 99%1287B, actual 2% IID, 200ms one-way, 60s. No parameter search.

Expected discriminator is not workflow color alone: compare B vs A original_frozen_retransmitted and quota_or_capacity_blocked, UDP residual, TCP p99/backpressure, product CPU/RSS and Stop. B should no longer time out healthy traffic before ~400ms authentic receipts can return. If it still fails, inspect first remaining stage rather than increasing retries or queues.