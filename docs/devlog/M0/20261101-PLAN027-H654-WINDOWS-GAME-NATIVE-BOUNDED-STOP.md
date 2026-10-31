# PLAN027 H654 — eliminate genuine Windows Game Rust FFI unbounded Stop/loan release

Source audit `crates/wbd-engine/src/v4_windows_game_native_runtime.rs`: old `wbd_m0_win_game_native_v3_stop` removed owned session first, then synchronously joined two actual Rust NPF/Wintun workers without timeout. A driver read that never returns holds Windows Go `product.Stop(ctx60s)` forever because its call into synchronous Rust FFI is not context-cancelable; thereafter no trustworthy loan/WAL receipt can be issued. Repeated original Windows GameFEC cancellations and Linux independent native Game/FEC success justify investigating this specific lifecycle hazard, but they do **not** prove that this was the only FEC root.

H654 source candidate: send real Stop/wake on the existing two Rust workers, poll both `JoinHandle::is_finished()` at <=10ms intervals for at most 12s, dropping native registry mutex on every poll. If either worker remains in a kernel call return `STOP_INCOMPLETE` **without removing session**, freeing NPF/Wintun leases, or falsely restoring WAL. Later retry may actually join; after both threads terminated, remove and join, only then return existing real Stop result. Negative synthetic parked worker test exercises bounded timeout and retry ownership; not a kernel PASS. No new wire protocol, Go hot worker, encryption, FEC math, MTU policy or lifetime owner.

Require **new SOURCE Windows Rust compilation, original signed Game/off Stop and GameFEC diagnostic** before acceptance. Existing Linux [Game2FEC6 original real kernel](https://github.com/lly8666/wbd-next/actions/runs/41219083345) and frozen SOURCE11f Fixed200 scenario currently in-flight are separate scope and unaffected. Windows GameFEC and B106 remain blockers, no overall completion.

```feature-impact
{"kind":"updated","ids":["game-lanes"],"reason":"Windows Game actual native Rust Stop previously joins indefinitely after removing session; candidate bounded fail-closed retryable loan retention requires source-current Windows compile and original driver regression."}
```
