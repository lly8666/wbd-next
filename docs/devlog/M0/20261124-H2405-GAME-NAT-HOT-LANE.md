# H2405 Game cold and hot lane parity

Follow-up user question: NAT and lane rotation. Linux Game4 hot replacement previously inferred whole-group physical handover from changed public client IP and native FFI independently rejected that IP change. Use the existing authenticated cold attempt to classify group vs lane and the newly authenticated exact tuple for native RX/TX. The client still uses whole-group cold on actual local physical change. A changed common record budget is not a compatible single-slot replacement. Initial Linux Game2/4 SYNs now start together; both full and hot TLS repeat the earned final ACK immediately and cold readers repair duplicates. A cold read failure closes only that association, not the live group. The existing supervisor reuses its rotation timer for two short precommit timeout retries; existing Rust M4 live verdict is read at 1Hz without new data-plane worker. No wire fields or steady DATA changes. Physical NAT and exact-source qualification pending.

```feature-impact
{"kind":"updated","ids":["game-lanes","original-lane-rotation-jitter"],"reason":"Game NAT-aware authenticated hot lane replacement and cold handshake parity."}
```
