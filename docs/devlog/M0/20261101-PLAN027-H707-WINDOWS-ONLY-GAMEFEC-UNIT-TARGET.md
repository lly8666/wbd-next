# PLAN027 H707 — correct Windows-target-only GameFEC unit, previous two zero-test results remain unqualified

Read actual `crates/wbd-engine/src/lib.rs`: `v4_windows_owner` and its private `v4_windows_game_owner` compiled only under `#[cfg(all(feature="m0_v4_embedded_go", target_os="windows"))]`. H705 Linux Action41272782294 returned success with `running 0 tests` from `--exact` unqualified matcher. H706 Linux Action41272851612 (without `--exact`) correctly rejects `running 0 tests`: even a matching name cannot run a Windows-gated module on Ubuntu. Neither is proof of original Game2 FEC ciphertext envelope or root, and no runtime product change.

H707 corrects **only** original single Action runner to Windows-2025, Rust x86_64-pc-windows-msvc toolchain1.85.1, features `m0_v4_embedded_go,fec2_product_record`, same exact existing source-authentic GameAdapter/M3 sealed FEC6 due parity test, actual `wbd_platform::ipv4_tcp::build_bytes` at Windows path MTU1400, source input1228B and legal1329B. Requires observed `running 1 test` before PASS, preserves actual nonzero test exit and printed lane/PN/recordLen/MTU/error. Not real Npcap/Wintun or Stop; no new native GameFEC Action, no new deadlines, no source runtime/protocol/ABI modification.

```feature-impact
{"kind":"none","ids":[],"reason":"Correct focus unit to Windows compiled target after observed Linux zero-test green/failed audits, preserve all original source/current GameFEC product FAIL; no runtime or configuration changes."}
```
