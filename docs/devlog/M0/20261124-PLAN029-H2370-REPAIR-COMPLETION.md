# H2370 — settle an actual dispatch after its eligibility deadline

H2368 45328644632 built both native products, group a complete (1.251/1.364/1.304 Mbps, P99 1453/1125/1594 ms; 0/10/0 actual copied). Group b A 1.511Mbps; B original log from artifact 14891501069: driver 2 accepted, 250B; shadow accepted-retired 1, outstanding 1, queued 0. First failure H2316 parser equality; ARM subsequent timeout and relay missing summary are secondary. No throughput qualification.

Root mechanism: ReceiptState::on_send_result reused dispatch preflight including time limits, so a valid already-submitted send can complete past deadline and leave a live shadow unretired. RX can independently discard a shadow during the syscall; legitimate actual driver copy then cannot count as a shadow retirement. Both are source-supported possible causes of the observed mismatch, exact event ordering not captured. Fix completion identity separately from preflight deadline; no second opportunity, no resurrect, no new first-send work. Windows settlement preserves definite driver accepted fact even if original budget settlement is stale (charge not refunded), logs explicit copied-shadow-stale and broker-unresolved counts. Parser verifies exact driver=retired+explicit stale, historical logs remain strict. Add late completion and parser regressions. No changes to budget, packet format, defaults or timers. Re-test 1% and native regressions before 5%.

```feature-impact
{"kind":"none","ids":[],"reason":"Correct existing one-shot repair completion semantics and native Stop accounting; no new product capability or setting."}
```
