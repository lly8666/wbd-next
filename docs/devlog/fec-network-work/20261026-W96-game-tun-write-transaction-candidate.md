# W96 | Game OFF TUN delivery two-phase reservation — candidate

Parent: `1208c069d1fd2ca8828b99d1206846d2e0bb7f94`. W94 exact source `fb65d8136c32e3e2182a09425f517cd7b98162ce` native Action40214830539 and clean 3Mbps Game2/4 same-VM Actions40215055396/40215059452 PASS_SCOPED. W95 unchanged-load loss20/blackhole real actions are running independently; W90 six Game+fixed FEC real product FAIL/atomic rollback preserved. No high-load escalation.

## Why
`GameReceiveOwner::receive` used to mark `GameRx::first_delivery` before Linux TUN `write_authenticated_ipv4`; failed TUN writes poisoned logical dedup, so another valid lane copy could be suppressed. W94's `first_delivery_candidate` avoids pre-allocation, **not** the TUN failure. This is a correctness defect, not AEAD or FEC math.

## Minimal scope
- Only Linux Game2/Game4 OFF receive path changed to `prepare_receive` (independent lane AEAD, cross-lane candidate/duplicates, **bounded** one pending logical id per lane) → release RX owner mutex → genuine TUN write → `finish_receive` commit only on success. Pending vector is preallocated for exactly 2 or 4 authenticated lanes; no new per-packet hash/table/threads, no spin and no lock around TUN syscall. Each pending prepared source retains its original RX owned slab, no stale buffer reuse.
- TUN failure removes pending without setting shared Game delivery bit. A subsequent new authenticated lane copy may deliver. Concurrent duplicate while pending is safely suppressed; on failure, already-suppressed copies cannot be replayed since lane PN replay remains strict, but they were **not** falsely committed in logical window. This is bounded best effort without making HOL or retries for outer recovery.
- Tests cover failure-then-alternate-lane successful delivery, pending duplicate and subsequent distinct lane, successful final dedup, Stop. Existing synchronous adapter receive in in-memory native tests still treats return to caller as delivery; production Linux uses explicit TUN commit.
- Real write succeeded but `first_delivery` commit fails (e.g. extreme stale-window race) is separately counted and triggers safe stop, not silently mislabeled delivered. This does not promise all failure races vanish; after write there is no TUN rollback, so no false success claim.
- No change to Linux raw filter, Normal FEC math, outer RACK/PTO/budget, Game fixed FEC (currently withdrawn), packet wire, MTU/generation/auth, or Windows; windows TEMP_SKIPPED.

## Gate
Exact SOURCE ARM64 native unit + real Linux bounded clean 3Mbps Game2/Game4 OFF, then representative independent20+lane1blackhole after earlier W95 evidence; compare actual injection/delivery/p99, CPU/RSS, errors and Stop. No upgrade in load; record unresolved Windows and Game fixed separately. This candidate is NOT product-verified at commit time.
