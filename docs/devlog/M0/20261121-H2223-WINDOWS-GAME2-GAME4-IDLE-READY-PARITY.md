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

## 2026-11-21 completed genuine Actions qualification (source a25b7e5d)

All three final qualification Actions used exact experiment source `a25b7e5da4f9dc9c6287ff68054b339b682c6d8c`; no stored historical binaries were relabeled as current source.

| Gate | Exact Actions run | Result and bounded scope |
| --- | --- | --- |
| Actual Windows x86_64 Go original client source-lock + idle READY unit | [44876499450](https://github.com/lly8666/wbd-next/actions/runs/44876499450) | SUCCESS. 0/0/0, 27/0/0, two Game lane counts, fatal worker and authenticated dead90 checks; current original-Go CLI build passed. |
| Windows 2025 signed Npcap/Wintun Game2 ↔ genuine Linux WSL2 original Go TLS/Rust server | [44876703877](https://github.com/lly8666/wbd-next/actions/runs/44876703877) | SUCCESS; `WBD_WL_TRUE_PUBLIC_MODE_WIN_LINUX_DUPLEX_STOP_PASS game2` and `WL_PUBLIC_REAL_MODE_RESULT game2 PASS`. |
| Windows 2025 signed Npcap/Wintun Game4-FEC6 ↔ genuine Linux WSL2 original Go TLS/Rust server | [44876705732](https://github.com/lly8666/wbd-next/actions/runs/44876705732) | SUCCESS; `WL_PUBLIC_REAL_MODE_RESULT game4-fec PASS`, verified signed same-run OS/Stop receipt. |

The cross-OS product tests use an actual WSL2 Linux kernel on the same Windows Actions host, not an independent physical Linux host. This proves the original Windows Game client and Linux server's live E2E execution at this scope; it does **not** prove physical WAN/NAT/packet-loss/maximum-throughput qualification. Game2/FEC6 and Game4/off combinations were not separately exercised in this follow-up; they use the same new worker startup verdict, and Game4/FEC6 plus Game2/off cover both lane counts and both FEC states.

During CI, the Windows↔Linux original Go build path was corrected to copy the **already existing** current-source `internal/v4routekey` package into the immutable pinned donor's temporary Actions assembly. This changes no product wire bytes or application validation. An initial Windows unit-only run on older branch source passed but its exact-SHA dispatcher was superseded by this final build-source fix; only the three complete green runs above count as promotion evidence.

**Merge policy:** promote PR #70 after the three final successes; preserve this doclog and the updated `windows-native-transport` feature card on `main`. The unrelated experimental encrypted-DATA parser PR #69 remains separate and is not automatically merged.
