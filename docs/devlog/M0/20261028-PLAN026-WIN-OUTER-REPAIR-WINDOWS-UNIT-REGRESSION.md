# PLAN026 Windows outer repair: fix first unit counterexample without touching Fixed/FEC behavior

Original exact-source Windows library Action [40718326142](https://github.com/lly8666/wbd-next/actions/runs/40718326142) compiled but its Windows Rust unit test job failed **4 of 221**. First real failures were old `Fixed6` shadow assertions and source0 Normal test asserting **every** fresh DATA must create a shadow. This follows the new half-sampled Normal path; the original Fixed/FEC shared M2 adapter was accidentally affected. No live Windows signed native scenario ran under that failing source; retain this FAIL.

Scoped fix: `v4_windows_owner.rs` uses `MAX_M2_FIXED_FROZEN=1536` with prior original M1 arena-backed shadow when `feature7`, while Normal/off alone uses max24576 separately charged immutable `try_v3_repair_snapshot()` and Linux-style PN/generation half sampling. A pure hash helper allows the old Normal source0 unit to assert whether this exact PN was selected, then still prove authentic kind1 release and replay rejection. `v4_windows_fec2_owner.rs` tests refer to the unchanged 1536 Fixed shadow bound, not the new Normal-only capacity. Rust library and exact new source signed two-OS test must pass before any 24-scene qualification; **no unsupported PASS** and no change to Linux client/server or FEC sender.

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Constrain new Linux-v3 borrowed-snapshot candidate sampling to Windows NativeOwner Normal/off; preserve original Fixed/FEC arena-backed 1536 shadow and original auth/Stop. Update mode-specific unit expectations after first Windows Rust test counterexample."}
```
