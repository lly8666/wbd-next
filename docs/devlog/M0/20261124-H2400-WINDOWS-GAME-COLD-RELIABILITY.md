# H2400 Windows Game cold reliability

User physical reports every Game mode can connect, but only after repeated attempts. H2223 native READY already has no business gate. Windows Game SYN ticker stopped before TLS DATA, initial retry excluded Game, and local source tuples were reused. Fix original per-lane sender RTO and join before Detach, reuse original cold timeout retries and reserve a whole fresh group in the existing ordinal state; handle Detach race. Linux shared Game server no longer requires NAT-preserved contiguous ports when one protected pending cohort matches; new authenticated lane1 retires incomplete previous groups only. This retains original TLS, protected epoch/policy, exact per-lane native tuple and live owner Stop. No new protocol, hot worker or security framework. Game heavy telemetry now opt-in, lightweight GUI status every two seconds. Physical NAT/weaknet qualification pending; no PASS claim.

```feature-impact
{"kind":"updated","ids":["windows-native-transport","game-lanes"],"reason":"Game cold RTO/retry/fresh tuple group and NAT-tolerant protected cohort admission; ordinary packet debug telemetry opt-in."}
```
