# PLAN026 — preserve original Windows M2 small output buffer no-PN contract with merged Health

2026-10-29. Windows Rust SOURCE `3967e61f487617b7307254cb3a5f042bc1688122` original ABI Action [40910103907](https://github.com/lly8666/wbd-next/actions/runs/40910103907) and full Windows library unit Action [40910104098](https://github.com/lly8666/wbd-next/actions/runs/40910104098) both directly compiled but **failed** exactly one existing regression: `m0_windows_m2_short_feedback_output_does_not_burn_original_tx_sequence`; `244 passed; 1 failed` under Windows native Rust. Expected `m2_next_feedback_entry(..., out[64]) -> Ok(None)` with NO consumed PN/stream span, actual `Err(INVALID=1)`. This was a real source-specific test failure, not signed two-OS kernel product verdict.

Cause: merged Health+Receipt encoder was incorrectly bounded by `min(path_budget.record_payload_mtu, out.len()-FIXED_WIRE_OVERHEAD)`; the tiny C ABI output buffer caused `encode_control` to return CodecError::BudgetExceeded mapped to INVALID, **before** the already existing correct output-size preflight. The ABI caller output size is NOT the authenticated carrier record MTU.

Minimal fix: feed `budget.record_payload_mtu` unchanged into the authenticated record encoder (true path MTU and 512 codec still cap optional random padding), then compute `needed = tlv.len()+FIXED_WIRE_OVERHEAD` and if `needed > out.len()` return FULL; existing method maps FULL to `Ok(None)` and resets feedback draft WITHOUT spending owner M1 AEAD PN or TCP-appearance sequence. The original regression checks the exact next real data seq. Never relax MTU or allow short buffer to burn a PN. The new exact-SOURCE Rust units and signed Game2 native run must independently pass.

```feature-impact
{"kind":"updated","ids":["windows-native-transport"],"reason":"Correct original Windows short C-ABI M2+Health receipt preflight: path-bound authenticated encoding must precede separate buffer-length backpressure, preserving no PN/seq burn on short output."}
```
