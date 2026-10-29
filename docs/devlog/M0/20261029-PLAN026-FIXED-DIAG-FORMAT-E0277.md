# M0 2026-10-29 Linux probe diagnostics compile correction

Exact source Action40830363492 failed in the developer-only diagnostics at E0277 because GlobalReservationId implements Debug, not Display. No kernel test ran on that source. Correct the one format specifier to {:?}. Keep strict real Go Fixed kernel, actual M4 sendto/sendmmsg and origin M2 tests. No production logic or nonce/packet changes.

```feature-impact
{"kind":"none","ids":[],"reason":"Test diagnostics Rust formatter E0277 correction only, preserve all original source and real kernel test assertions."}
```
