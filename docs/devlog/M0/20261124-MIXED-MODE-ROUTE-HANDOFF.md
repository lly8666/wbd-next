# M0 H2414 mixed Normal/Game shared /32 handoff

User report: disconnect Normal -> Game2/4 connected but reverse injection zero until reconnect after Health90. Rust defers replacement by /32, but Go only checked the same transport table. Fix cold lookup and retirement over both existing active and pending maps, using authenticated lease rather than mode, principal alone or tuple. Preserve immediate initial publish, existing Health proof, exact generation retirement, grace and 90s. Align Game exact-already-published promotion result with Normal when old A disappears before B start. No new wire, FFI exports, states, worker, timer, packet-path change. Game4 selected-slot hot replacement unchanged. Manifest hash regenerated. Tests NOT_RUN until exact SOURCE.

```feature-impact
{"kind":"updated","ids":["game-lanes","linux-raw-tun"],"reason":"Correct cross-mode cold shared-TUN owner publication and retire only predecessors of the same authenticated /32; no new user option or protocol."}
```
