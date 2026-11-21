# 2026-11-21 / H2223 Windows Game2/4 cold READY parity with Normal

## Root cause and actual product call path

Main at `18a1a0b620f0223ce9cb6dc771de9bd6f5204f20` already adopted H2223 Normal idle startup: `m0WindowsRustNativeStartupVerdict` checks native `WorkerError` and does not require `TXCopied/RXDelivered/TXAfterRX`. Windows Game2/4 original Go TLS -> `m0WinRustGamePeer.BindNativeRing` -> original native `N4RealWindowsProduct.Apply` -> `N4WindowsNativeProductController.Connect` -> `VerifyBidirectionalAuthenticatedFirstDelivery` still called `m0WinRustGamePeer.VerifyPeerFirstAndReverse`. That Game method **wrongly** required `TXCopied >= 2*lanes`, `RXDelivered >= 1`, `TXAfterRX >= lanes` within 25 seconds. It turned legitimate idle Game activation into a false timeout before the real public `WBD_WINDOWS_CLIENT_READY`.

## Minimal product fix

- Use the *same* Normal `m0WindowsRustNativeStartupVerdict` in the Game2/4 Rust-native method. Take exactly one bounded `NativeGameIOStats` readback, which also proves C ABI `Version/Size` and `Workers=2`, and stop requiring any application traffic.
- The original credential-verified TLS and M3 keys, exact 2/4 lane native capture/ring owner, original Windows WAL/OS Apply, live OS readback, numeric Wintun MTU CAS, authenticated 90s-dead error, generation Stop and real data-plane quality probes are retained.
- Go's independent historical steady packet A/B verifier remains intentionally unchanged; do **not** silently weaken business acceptance, fabricate traffic, fake `RXDelivered`, or bypass physical network tests.
- Retain the existing public `N4NativeProductLiveOwner` method name `VerifyBidirectionalAuthenticatedFirstDelivery` for API compatibility despite H2223 activation-only semantics.

## Tests and result policy

- Windows Go regression: Game2 and Game4, empty `0/0/0`, historic `27/0/0`, first-copy `1/0/0`, real-traffic snapshot, native worker errors and dead90 handling. The existing Normal H2223 tests remain active.
- Signed Windows native Game2 and Game4 ↔ genuine Linux WSL2 server original Go TLS/Rust E2E: full fresh-source DLL/EXE/ELF build, kernel Npcap/Wintun/TUN, original authenticated data-plane and owned Stop, no old-product-binary reuse.
- A green Go compile/unit-test alone is **not** a real Game business success. Record exact Action run conclusion and physical limits before merge.
- Only after test PASS, merge the game parity branch into `main`; **do not** implicitly merge unrelated experimental outer-parser PR #69.

```feature-impact
{"kind":"updated","ids":["windows-native-transport"],"reason":"Game2/4 native cold READY now shares existing Normal H2223 worker-only verdict after authenticated native/OS application; business counters remain independent E2E evidence."}
```
