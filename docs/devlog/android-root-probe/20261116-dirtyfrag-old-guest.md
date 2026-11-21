# Android16 pre-Apr r07 real guest canary, 2026-11-16

- Owner is solely `experiment/android-temp-root-probe` based on HEAD `640fc920cba131fe6ff9278ede81f5d4a8afdb9e`; original KSU and M0 untouched.
- macOS HVF gate [Action43858595528](https://github.com/lly8666/wbd-next/actions/runs/43858595528), SOURCE `640fc920cba131fe6ff9278ede81f5d4a8afdb9e`, confirmed macOS ARM64, SDK emulator `-accel-check` exit0 / `Hypervisor.Framework OS X Version 15.8`; governance [43858595510](https://github.com/lly8666/wbd-next/actions/runs/43858595510) success.
- Single independent guest Action now downloads **exact** 2025-12 historical Android16/API36 Google Play arm64-v8a r07 ZIP advertised on 2025-12-02 in Android SDK XML commit `7c23968450618e94727e190d3a2ad3cf8f24adf7` (archive size 1886527965, SHA1 `5b91ef80a5eb60d7b7167528db259c2a12d20e9c`), additionally records SHA256. No automatic revision substitution.
- First scene is only unrooted AVD verification: actual Android16, security patch prior to 2026-04, kernel>=6, arm64, non-root user, `adb root` rejected, SELinux and vendor helper availability. Neither KernelSU ramdisk injection nor DirtyFrag exploit runs in this preflight, so even PASS of baseline **does not prove temporary root**.
- On missing archive/boot/kernel status the Action produces `ENV_BLOCKED`, not a fake success. Only if actual unrooted baseline passes may a distinct bounded DirtyFrag scene proceed with App→su identity and WBD native probes. No physical device.

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Create exact pre-Apr Android16 ARM64 r07 fresh AVD unrooted baseline and preserve DirtyFrag/WBD NOT_RUN until real operations."}
```

## SOURCE-specific CI blocker and bounded fixture correction

- [Action43859987790](https://github.com/lly8666/wbd-next/actions/runs/43859987790), SOURCE `22211f41a5b529be46d9e8e91688580edbf5a67f`, job `133273970185`, Action `SUCCESS` but **case status `ENV_BLOCKED/HISTORICAL_SOURCE_PROPERTIES_MISSING`** after a verified historical ZIP was extracted to the wrong SDK folder. Artifact `14222638280`, GitHub ZIP digest `sha256:69363ba5b763662c68502a7ace9829ca52dbc19652d32c2fe5ecec1d61fb505c`. No guest boot/root/DirtyFrag in this Action.
- The corrected script explicitly inventories ZIP entries and only accepts a single `source.properties` at archive root or under `arm64-v8a/`; it extracts to the corresponding parent folder, still strictly requires identical historical archive SHA1/size and revision r07. One affected-source rerun; no fallback image and no root success claim.

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Record source-specific failed ZIP layout assumption and correct extraction of immutable pre-Apr Android16 ARM64 r07; DirtyFrag remains NOT_RUN."}
```

## r07 archive confirmed, AVD-manager stdin fixture defect

- [Action43860416567](https://github.com/lly8666/wbd-next/actions/runs/43860416567), SOURCE `32f86c09bcf42ea5c2431a4919f7855e7619f3dd`, job `133275461736`, artifact `14222708892`, GitHub ZIP sha256 `098fa7606a4c96418f04452cc9e4bd495ffe95458324fc1c19c9e845b86b2ace`: historical r07 archive exact bytes **1886527965**, SHA1 **5b91ef80a5eb60d7b7167528db259c2a12d20e9c**, measured SHA256 **ddb0feff5c23db9f42ceabd28f6542e8ffec639abf818bf6831a2658e6cf7905**. Actual ZIP prefix `arm64-v8a/`, source.properties `Pkg.Revision=7`, API36, Google Play, ext17.
- **Guest NOT_RUN**: `avdmanager create avd` prompted `Do you wish to create a custom hardware profile? [no]` then Java `Range [0, 0 + -1) out of bounds for length 256` because the subprocess had no stdin. Fix only affected fixture by supplying `no\\n`; independent replay still uses identical SHA1-verified image, no kernel patch/DirtyFrag invocation.
- Previous source-specific archive nesting assumption `HISTORICAL_SOURCE_PROPERTIES_MISSING` remains in earlier Action43859987790, not reclassified as success.

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Lock historical old Android16 ARM64 r07 actual sha256 and correct avdmanager interactive stdin fixture without changing guest/exploit statuses."}
```
