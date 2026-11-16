# Android16 pre-Apr r07 real guest canary, 2026-11-16

- Owner is solely `experiment/android-temp-root-probe` based on HEAD `640fc920cba131fe6ff9278ede81f5d4a8afdb9e`; original KSU and M0 untouched.
- macOS HVF gate [Action43858595528](https://github.com/lly8666/wbd-next/actions/runs/43858595528), SOURCE `640fc920cba131fe6ff9278ede81f5d4a8afdb9e`, confirmed macOS ARM64, SDK emulator `-accel-check` exit0 / `Hypervisor.Framework OS X Version 15.8`; governance [43858595510](https://github.com/lly8666/wbd-next/actions/runs/43858595510) success.
- Single independent guest Action now downloads **exact** 2025-12 historical Android16/API36 Google Play arm64-v8a r07 ZIP advertised on 2025-12-02 in Android SDK XML commit `7c23968450618e94727e190d3a2ad3cf8f24adf7` (archive size 1886527965, SHA1 `5b91ef80a5eb60d7b7167528db259c2a12d20e9c`), additionally records SHA256. No automatic revision substitution.
- First scene is only unrooted AVD verification: actual Android16, security patch prior to 2026-04, kernel>=6, arm64, non-root user, `adb root` rejected, SELinux and vendor helper availability. Neither KernelSU ramdisk injection nor DirtyFrag exploit runs in this preflight, so even PASS of baseline **does not prove temporary root**.
- On missing archive/boot/kernel status the Action produces `ENV_BLOCKED`, not a fake success. Only if actual unrooted baseline passes may a distinct bounded DirtyFrag scene proceed with App→su identity and WBD native probes. No physical device.

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Create exact pre-Apr Android16 ARM64 r07 fresh AVD unrooted baseline and preserve DirtyFrag/WBD NOT_RUN until real operations."}
```
