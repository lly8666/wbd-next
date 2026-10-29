# M0 PLAN026 source-exact real Windows FEC2 RS16 first failure and owned cleanup

2026-10-29. Source90219204 real Windows original Go credential TLS/ signed Wintun FEC2 test in PLAN020 Action40821482056 failed true original Rust M3 RS16 repair open with rc=INVALID after four first-delivered real kernel UDP checks. The test then entered t.Fatalf before explicit Rust owner Stop, so its deferred Wintun.Close blocked on native M4 loans; Go killed it at six minutes, hiding the actual reason. Current test code adds a failure-safe deferred BOTH protected Rust owner Stop AFTER real Wintun acquire and before per-mode packet tests. It preserves the strict failed RS16 assertion, real M3 auth and real Stop checks, and never emits PASS or changes production kernel behavior. Successful original manual Stop records stopped=true so cleanup is not repeated. This removes a dangerous test harness deadlock, not the underlying RS16 INVALID, which remains a real engineering failure awaiting source-lock diagnosis.

```feature-impact
{"kind":"none","ids":[],"reason":"Original Windows FEC2 real-Wintun test cleanup on first failure; keep all original M3/RS16 and Stop assertions intact, diagnose true INVALID rather than six-minute timeout."}
```
