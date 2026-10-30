# PLAN027 H516: repair exact original H515 Windows compile and unchanged governance limits

Commit f213 H515 new source real runner [41055899755](https://github.com/lly8666/wbd-next/actions/runs/41055899755) FAILED before any 2-OS native traffic: Rust E0433 `Duration` not imported in `v4_windows_native_runtime.rs` at line 872. Windows Go compilation and Linux Rust unit tests passed; no new-source native product or SACK tier can be claimed. H516 imports `std::time::Duration` without altering protocol/data-plane thresholds.

Feature catalog failed because `fec-auto.json` was 16487 bytes, over immutable 16384-byte hard cap; condenses old H498/H502 summary strings while retaining full evidence refs. Governance maintenance failed exact M4 import check because the M0-owned Windows native IO cold capability changed to git object `96f24e506ea765e9719b252e850a94e4896f18b4`, already pinned by `manifest-plan020-m0.json`; register this identical SHA in `M0_AUTHORIZED_CURRENT`, preserving every original frozen M4 source blob and donor baseline. No checks were softened.

One new immutable source no-loss 10Mbps/25ms/0%/60s signed Windows/Linux original Go TLS/Rust Action is dispatched only after this source freeze; follow-up damaged 1/5/10/30% uses *exact resulting binary*, if build/real 0% successful. No blind repair, R padding or false product promotion.

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Condense duplicated historical prose to meet unchanged <=16KiB feature card gate; prior results retain exact documentation references."}
```
