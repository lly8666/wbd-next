# PLAN028 H1568 | exact original-Go Windows two-account native slot CI repair

The previous [H1381 source0a Action42952219558](https://github.com/lly8666/wbd-next/actions/runs/42952219558) was **FAIL_PRE_NETWORK**: `prepare_windows_wiring.py` already included the original-Go test-only `m0_plan028_dual_native_slot_windows_test.go`, but the H1381 workflow did `assert not dest.exists()` and failed before calling Go tests. New test-only Windows workflow accepts an existing file **only when its bytes match the exact immutable current source**, otherwise refuses, and adds exact source bytes if absent. It remains pinned to original Go source `a7a82db31fe736ffedee330795a3234d358f1984`. The independent Windows2025 action will execute actual OS named events for two distinct authenticated account/lease/alias/WAL slots, duplicate/cross-account rejection, legacy singleton hard guard. It does NOT run two signed Wintun/NPF TLS data-plane sessions or claim the Windows+Linux4 first/reverse/600s success. Existing H1567 full Windows original M3 real server kernel UDP first-reverse Action remains separate, running on SOURCE5fcc and unaltered by this workflow-only change; do not duplicate the original H1548 0%/30% seeds.

```feature-impact
{"kind":"none","ids":[],"reason":"Test-only original Windows2025 two-account kernel event owner-slot immutable-source injection repair; no runtime, TLS, Rust, Npcap/Wintun or shared TUN behavior changed."}
```

Evidence [H1568](../evidence/M0/PLAN028-H1568-H1381-WINDOWS-DUAL-ACCOUNT-NATIVE-SLOTS-20261111.json). PLAN028 IN_PROGRESS.
