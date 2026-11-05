# H1236 — Native Game4 real TLS hot-swap attempts are not successes

H1235 exact product SOURCE e408, Action 42001808430 x86/x86 Go TLS Rust M4 build PASS; both scene jobs FAIL because old test asserted successful source-port attempt cycles must equal 1..8. Original 12-file ZIP each SHA256 and CRC verified. Actual success 8 individual slot switches per scene, client/server 443 TLS ports matched, one original Rust GameAdapter, no sibling reauth/M4 restart/Health90. Failed original TLS candidates under real impairment were correctly deferred three times per mode, old Game4 owner retained. Actual success attempt IDs Off [1,2,5,7,8,9,10,11], Fixed6 [1,2,3,4,6,8,9,11].

True no-retry TUN UDP: Off Alice2642/2642 Bob2389/2626 Carol2642/2642; Fixed6 Alice2522/2522 Bob2516/2516 Carol2522/2522. Real kernel tc drops Bob→server Off551 Fixed6 1582, server→Bob Off512 Fixed6 1638 under both qdiscs configured 5%. Off no-FEC two independent directions theoretically deliver 0.95×0.95=90.25% of UDP echos; observed90.97%, so prior >=98% gate wrongly applied Fixed6 expectation to Off. Bob received-only RTT p99 Off8.45ms Fixed6 2.56ms, largest successful gap Off155ms Fixed6 112ms.

H1236 changes ONLY native CI/fixture (product Rust/Go exact H1235 code unchanged), keeps eight genuine protected TLS lane success and original M4/FEC/Stop checks, asserts strictly increasing cold attempt ordinals with final attempt index=8+number of pre-M4 retries, verifies all actual arming intervals 15–21s, realistic Off>=87% versus Fixed6>=98% under measured 5% two-way qdiscs and no-app-retry true business, and uploads all physical route/link readbacks. New source-locked native Action pending. H998 physical online MTU FAIL unchanged.

```feature-impact
{"kind":"updated","ids":["original-lane-rotation-jitter"],"reason":"Repair false native CI oracle: distinguish failed cold TLS attempts from 8 genuine Game4 physical slot swaps, apply correct no-FEC two-way 5pct UDP survival gate."}
```
