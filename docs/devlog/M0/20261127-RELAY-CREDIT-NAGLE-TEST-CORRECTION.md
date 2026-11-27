# Relay pending credit: Nagle-tail regression fixture correction

d09f6158ca9fe1d587e9c57b4cd6fe1674ebba49 native45992330840: x86 job140483030842, ARM140483030436 both compile and run core, 350 passed/1 failed. Exact named relay_pending_admission_tracks_unsent_not_outstanding_bytes at conn.rs:10638, left96 right0. Cross-host45992330791 prepare140483030012 failed exact-source native qualification; all three execution jobs skipped. No normal/paused application or cross-host candidate measurements; do not call this a performance regression or PASS. Original logs reviewed. Inherited governance red is separate.

Actual code: big() uses MSS1000 and Nagle enabled, pacing off; the 4096-byte test manually reopens the send window and flushes. Existing flush_send_queue sends four full segments then holds 96-byte short tail while data outstanding (Nagle/SWS condition). This is a flawed expectation in the new test, not evidence of failed relay credit. Forward correction preserves original 4096 fill/zero credit, asserts pending96/unacked4000/available4000 after flush, feeds actual packets and receiver ACK (including delayed ACK expiry if needed), asserts pending0/unacked96/available4096 and delivers actual tail to verify full payload. Existing product behavior, ceiling candidates, flags, and tests gates unchanged. No new runtime change. Exact new source native and original uncapped ABBA must qualify, slow-consumer actual upstream pause still not proven. No repeat dispatch of failed SHA.

```feature-impact
{"kind":"updated","ids":["dual-rust-tcp"],"reason":"Record failed relay-credit regression and correct Nagle tail expectation while preserving actual ACK-driven credit and payload checks; no product change."}
```
