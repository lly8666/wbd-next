## PLAN028 H1328 exact original ARM64 Game4 timer failure

H1327 source 23bc327bdb3254a8708d44add23c5ddb7372f0d8 Action42377946485: build native ARM64 both real OS ends PASS, one real network scene FAIL. Real server protected TLS/Rust one-by-one Game4 lane Hot 1,2,3,4,1,2 in same native M4 group; stale test expected four full generations (never triggered). Raw client lane proof was not retained; original CI FAIL preserved. Both real sibling devices' app replies and target stop simultaneously because fixture echo server ended at hard 4000 messages: 36 warmup + 1322+1321+1321 continuous UDP receipts = exactly 4000, while sends continued to 1610/1609/1610. Successful-receipt-only p99 would hide >28s terminal stop, so add exact last send timestamp and strict terminal active-sender no-receive <800ms. This artifact does not show product data plane stall; original counts still FAIL due fixture loss.

H1328 updates only test generator/workflow. Bounded receiver 6500 > 3*10pps*185s+36, no queue or product parameter change. Observe fourth protected original Go TLS/Rust M4 per-lane Ready and matching real server hot tuple for lanes 1..4, preserve group generation1 and three sibling lane slots, independently authenticated /32, real kernel UDP each client >=99.5%, max successful gap <800ms and terminal still-sending gap <800ms, source readback and final Stop. One source-locked ARM64 action only; no untriggered PASS. H1317 old 5.18s and H998 MTU historical failures remain, Windows 7 modes/L2/L3/Android outstanding.

```feature-impact
{"kind":"none","ids":[],"reason":"Source-locked original native ARM64 Game4 single-lane test fixture only: true live hot-lane semantics, bounded echo receiver and terminal no-reply oracle, no product change."}
```
