# PLAN026 M0 | recovered same-host ABBA, revert NPF borrowed-frame optimization

## Intent and shortest dependency
After cursor H342, inspect the actual main Actions 40707758779 artifact and source-attested A1-B1-B2-A2, decide by the predeclared CPU/Stop/first-delivery gates, then revert only the two B hot-path blobs. This devlog closes the ABBA experiment, not PLAN026's remaining modes. Source of truth: [ABBA precommit](20261028-PLAN026-WIN-NPF-SAME-RUNNER-ABBA.md) and [recovered evidence](../../evidence/M0/PLAN026-WIN-NPF-ABBA-SAME-HOST-ROLLBACK-20261028.json); older copy/wake design is [here](20261028-PLAN026-WIN-RX-WAKE-COALESCING-150M.md).

## Same-host source-controlled result
Actions [40707758779](https://github.com/lly8666/wbd-next/actions/runs/40707758779), job 122884518451, artifact 12825900107, ZIP sha256 `2011f5141fa3d1eceac18a2b96268bfc8fa7acdeea822383336ef365aa4edbeb`. Harness main `48151cc8825451f526a4cb91ba67dfc95f55e300`; compiled A `7fc38591c501ff4a06e1862c7b08d5d3dbc1be95`; compiled B `e6be9358d2272d7e1960a935be7fe772885bb034`. Exact Windows-2025 runner 1000107804 and WSL2 guest were reused sequentially with full Stop between legs, signed original Npcap/Wintun, original Go TLS→Rust NativeOwner, Linux raw/TUN. Scenario sha256 `e22a96fbd4d6de2b4dc581d7013b343e61f5775298480e185c7a5562906d516e`: 150Mbps offered each, 300ms one-way each, 0% netem, 60s.

| Leg | Win/Linux offered Mbps | Win/Linux first unique | EXE Go+Rust CPU s | CPU s/first-delivered GB | Win/Linux application RTT p99 ms | Stop |
| --- | --- | --- | ---: | ---: | --- | --- |
| A1 | 149.9624/149.9541 | 100%/100% | 11.484375 | 5.105587 | 610/610.872 | PASS |
| B1 | 149.9599/149.9088 | 99.9957%/100% | 11.390625 | 5.064803 | 657/613.375 | PASS |
| B2 | 149.9599/149.9996 | 99.9971%/100% | 10.796875 | 4.799351 | 610/620.941 | PASS |
| A2 | 149.9624/149.9998 | 99.9596%/99.9411% | 10.343750 | 4.600141 | 641/636.865 | PASS |

All four met the >=142.5Mbps per direction and >=99.9% first unique floors; actual Linux tc IFB+eth0 drops0, Linux raw/UDP socket drops0, owned Stops PASS. **Not absolute zero missing**: B1 53 Windows, B2 36 Windows, A2 499 Windows/727 Linux last-window misses. App RTT p99 is measured round trip, NOT one-way. CPU measures full original Windows Go cold control + Rust DLL and charged process kernel time, NOT driver-wide ISR/DPC or a claim of separate Go/Rust shares.

Precommitted decision **ROLL_BACK_B**. Mean A 4.852864 vs B 4.932077 CPU-sec/first delivered GB; B uses 1.6323% more, rather than >=5% less. Action step intentionally returned nonzero `ABBA_ROLL_BACK_B_NO_VERIFIED_BENEFIT_OR_REGRESSION`; the four product legs themselves all passed. Removing ~1.27GB of intermediate frame memcpy in B was real, but did not justify retaining unproven extra lifetime complexity.

## Scoped rollback and validation
Reset only `crates/wbd-engine/src/v4_windows_native_runtime.rs` and `crates/wbd-platform/src/windows_native_io.rs` to their byte-identical source-A blobs. Keep 32-record event wake batching, existing AEAD/PN and owned Wintun/NPF loan/Stop, Linux raw SO_RCVBUF and all Go cold-layer and assembly paths unchanged. Exact main product SOURCE is the **new rollback commit**, not historic A SHA; reused `[plan026-win-wake-150]` Actions selector triggers fresh Windows+Linux compilation and one original 150M/300ms signed Normal/off scenario, no recycled A binary and no fresh ABBA. Until new-source evidence settles, new rollback SOURCE is NOT_RUN, and old A/B scoped facts remain source-specific.

Outstanding: PLAN026 240s N0, idle/1pps/burst, old-Go vs Rust process A/B, Fixed/Auto/Game/Health/make-before-break native lane, physical Windows and driver ISR/DPC. Old N0 and Linux stability risks remain; this four-leg ABBA neither closes nor resets them.

```feature-impact
{"kind":"updated","ids":["normal-off","windows-native-transport"],"reason":"Roll back unproven borrowed NPF RX optimization based on same-runner exact-source ABBA CPU/first-delivered GB; preserve qualified Rust 32-record wake coalescing and unchanged user-visible Normal/off default, authentication, driver Stop and Linux path. New rollback SHA requires fresh native verification."}
```
