# PLAN027 H541 — H539 failed 1 stale unit expectation, source-lock corrected

H539 product SOURCE `2bcdd4a974a31f65b244716f19f6a374dc937787` Action [41084411982](https://github.com/lly8666/wbd-next/actions/runs/41084411982) original Linux Rust core 230 PASS/1 FAIL. The sole failure `h515_real_authenticated_gap_exposes_sack_until_contiguous` expected first SACK block=(1200,1300) after receiving two disjoint authentic future spans; H539 deliberately emits the **most recent** block=(1400,1500) first to avoid repeating expired old-gap shadows. This is a test-oracle expectation rather than another crypto/business bug; no tolerance/safety checking removed. Windows Rust native core/Go were PASS in this source, real Windows 0% test still in flight at timestamp.

H541 changes only Linux test expected newest then older, adds Windows native positive SACK order test with cumulative ACK and authentic-range coalescing, leaves original shared half-gap source algorithm, 250ms old-head skip and R≤0.10F unchanged. Build workflow source file comment updated solely to trigger one clean unit-corrected new SOURCE original signed Windows/Linux 0% build. Preserve failed H539 SOURCE result as FAIL; do not transfer any existing product PASS between source hashes. Real follow-up source-specific 1/5/15/30 tests remain NOT_RUN until a genuine signed source0%/Stop PASS.

H540 governance [41084726559](https://github.com/lly8666/wbd-next/actions/runs/41084726559) PASS after cross-SOURCE cursor evidence pointer corrected. H538 prior Game4 FEC fail and pending Game2 FEC original Actions preserved. User's latest target 0.4–0.6p low, 0.25–0.6p high, R/F 10% cap remains newest acceptance.

```feature-impact
{"kind":"none","ids":[],"reason":"Only align two native Rust unit tests to authenticated newest-first SACK selection already implemented H539 and retrigger exact-source build; no product algorithm or user-facing feature change."}
```
