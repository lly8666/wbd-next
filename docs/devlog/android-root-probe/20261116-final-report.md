# Android temporary-root capability probe — final evidence and decision (2026-11-16)

## Decision / contract

**Limited emulator-native feasibility is established, not Android client or real tethering feasibility.** Real AOSP Android 9/API28 to Android16/API36 x86_64 emulators, SELinux Enforcing, all showed **SUPPORTED_IN_SCOPE** for owned nonpersistent TUN **actual IPv4/UDP kernel ingress38 bytes and egress39 bytes**, raw IPv4/TCP 40-byte loopback SYN plus kernel RST, `SO_RCVBUF` readback131072 and loopback/owned-device binding, MTU1400 readback, fd-close interface cleanup. Execution path: **adb root / UID 0 / `u:r:su:s0`** only. None proves production app→su, phone root manager compatibility, true internet/shared client access, hardware offload, or a no-VPN-icon Kotlin client. Runtime ARM64 and 16KiB page Android not measured.

**Android 17/API37 is ENV_BLOCKED, NOT_RUN as a guest**: [Action43800641050](https://github.com/lly8666/wbd-next/actions/runs/43800641050) successfully checked host /dev/kvm and SOURCE-matched artifact SHA256 but `sdkmanager` failed to find `platforms;android-37`; no downgrade or attempt to disable SELinux.

## Real-version test matrix (one AVD / one independent Action)

| API | Release | Action | Native SOURCE | Result scoped to owned TUN + loopback raw |
|---|---|---|---|---|
| 28 | Android 9 | [43801347367](https://github.com/lly8666/wbd-next/actions/runs/43801347367) | `c7fa61412a02` | TUN UDP 38/39、raw lo、owned cleanup PASS |
| 29 | Android 10 | [43802747667](https://github.com/lly8666/wbd-next/actions/runs/43802747667) | `66ab0d8a043b` | TUN UDP 38/39、raw lo、owned cleanup PASS |
| 30 | Android 11 | [43803115045](https://github.com/lly8666/wbd-next/actions/runs/43803115045) | `66ab0d8a043b` | TUN UDP 38/39、raw lo、owned cleanup PASS |
| 31 | Android 12 | [43803115102](https://github.com/lly8666/wbd-next/actions/runs/43803115102) | `66ab0d8a043b` | TUN UDP 38/39、raw lo、owned cleanup PASS |
| 32 | Android 12L | [43802346729](https://github.com/lly8666/wbd-next/actions/runs/43802346729) | `66ab0d8a043b` | TUN UDP 38/39、raw lo、owned cleanup PASS |
| 33 | Android 13 | [43802346712](https://github.com/lly8666/wbd-next/actions/runs/43802346712) | `66ab0d8a043b` | TUN UDP 38/39、raw lo、owned cleanup PASS |
| 34 | Android 14 | [43802346694](https://github.com/lly8666/wbd-next/actions/runs/43802346694) | `66ab0d8a043b` | TUN UDP 38/39、raw lo、owned cleanup PASS |
| 35 | Android 15 | [43802747725](https://github.com/lly8666/wbd-next/actions/runs/43802747725) | `66ab0d8a043b` | TUN UDP 38/39、raw lo、owned cleanup PASS |
| 36 | Android 16 | [43802747870](https://github.com/lly8666/wbd-next/actions/runs/43802747870) | `66ab0d8a043b` | TUN UDP 38/39、raw lo、owned cleanup PASS |
| 37 | Android 17 | [43800641050](https://github.com/lly8666/wbd-next/actions/runs/43800641050) | `80e2218fc3f2` | **ENV_BLOCKED** missing SDK37 platform; guest NOT_RUN |

Every positive run checked observed API and image revision, Linux kernel, SELinux Enforcing, adb-shell vs adb-root identity, SOURCE and SHA256, used a fresh AVD, ran bounded traffic, and uploaded the full case result. All successful emulators reported 4096-byte pages. Exact kernel/image revision, artifact IDs and **full ZIP SHA256 for each of 10 rows** are in [the machine-readable matrix](20261116-api-matrix.json). Results are valid only for the tested SOURCE and scope, not a complete Android system ability declaration.

Build reuse:
- API28 code SOURCE `c7fa61412a02e0adff389e761308bb1147a35fa7`, build [43801129305](https://github.com/lly8666/wbd-next/actions/runs/43801129305), artifact14195549242, manifest SHA256 `84b26b1da6c8cd66dae6480b1127a4cb3f21713c7178c851ec834cb7defb21a9`.
- API29–36 code SOURCE `66ab0d8a043bfc3e74ca8ecd4e4a91db7d9d0925`, build [43802134067](https://github.com/lly8666/wbd-next/actions/runs/43802134067), artifact14197020858, manifest SHA256 `ecae5b4668a15af72d06dd8695718cfedf12fdbf25849319ee4cda61b478d800`; x86_64 binary SHA256 `7841f6d8fda1d5b41ad271fb8948c297d084f2037c4f1669b8671abf576424ea`; ARM64 build-only binary SHA256 `5b96775e4d16a2fe607d3757070ba6d0cb83c012cea71db0f0dba9e6153a1b4f`.
- Both binary families compiled Rust1.85.1/Android NDK30.0.16248370 against Bionic API28+, ELF p_align0x4000 (static 16KiB alignment only). There is **no targetSdk37 Android APK**, only native probe manifest metadata and build target; neither Kotlin runtime nor FGS behavior tested.

Historical failures (not removed or reinterpreted): first SOURCE `7c01a89e043083883c3dac937c7b311a4bcf376f` E0308 ioctl request ABI build FAIL [43799378701](https://github.com/lly8666/wbd-next/actions/runs/43799378701); SOURCE `80e2218fc3f2a03b28a284bead32b94d623e29e2` API28 TUN egress timeout [43800641119](https://github.com/lly8666/wbd-next/actions/runs/43800641119) but raw lo PASS; SOURCE `c7fa61412a02e0adff389e761308bb1147a35fa7` API29 [43801669820](https://github.com/lly8666/wbd-next/actions/runs/43801669820), API30 [43801669682](https://github.com/lly8666/wbd-next/actions/runs/43801669682), API31 [43801669793](https://github.com/lly8666/wbd-next/actions/runs/43801669793) captured the first unrelated IPv6 packet and failed exact-match assertion even though TUN ingress + cleanup and raw lo were positive. Source `66ab0d8a043bfc3e74ca8ecd4e4a91db7d9d0925` boundedly filters non-target traffic (<=1500ms) and all affected versions later passed. These are source-specific corrective tests, not identical repeat dispatches.

## Privilege / SELinux assessment

Observed `adb shell`: UID2000, CapEff0; the default mode `inspect` is read-only. Observed `adb root`: UID0, `u:r:su:s0`, SELinux **Enforcing**, CapEff `0000003fffffffff` (API28–30) or `000001ffffffffff` (API31–36). This establishes a broad-capability elevated AOSP test context, **not a verified minimum set**. Candidate Linux privileges to isolate in an actual root-managed app process: `CAP_NET_ADMIN` to create/configure TUN, policy route, forwarding/NAT and `CAP_NET_RAW` for raw TCP + relevant binding, with readable/writable `/dev/tun` and policy-compliant SELinux domain. `SO_RCVBUF` used normal kernel permission rather than claiming `SO_RCVBUFFORCE` success. A cap-drop/SELinux-policy isolation run is NOT_RUN; root manager grants and root process lifecycle can differ from adb root. Neither `VpnService` nor system/boot/root installation was used.

## Measured vs unmeasured abilities and the real-device gate

- **SUPPORTED_IN_SCOPE**: actual kernel TUN read and write of owned, non-persistent interface; independent raw IPv4/TCP loopback send and capture; MTU1400 readback; SELinux/capability observations; `SO_RCVBUF` and `SO_BINDTODEVICE(lo)`; owned fd-close cleanup. Two short UDP packets/one raw SYN per case; no sustained throughput, product weak-network or phone energy claims.
- **READ_ONLY_OBSERVED, NOT full functional PASS**: AOSP policy/fwmark route tables (e.g. API28 fallback unreachable priority32000), global IP forwarding state and NAT chain inventory; an unrelated 48-byte **IPv6** TUN packet before target IPv4 packet in API29–36. This does not prove fwmark-selective capture, IPv6 forwarding, DNS behavior, CLAT or NAT round trip.
- **NOT_RUN**: app→user-approved `su`, no-root negative elevated exercise, least-capability drop, Kotlin targetSdk37 app/foreground-service/notification/no VPN icon, Android network binding callbacks/physical network handover, DNS UDP/TCP53 and private-DNS interactions, owned fwmark policy rules, SNAT/conntrack with two real downlink clients, hotspot+USB system tethering, OEM hardware/eBPF offload, IPv6-only cellular/CLAT, Wi-Fi AP+STA, root daemon long background run, forced-kill cleanup, real device kernel/SELinux variants, ARM64 device load, 16KiB-page runtime, battery. Do not interpret a software forwarding stub as true tether and do not alter system forwarding or flush rules.

## Next bounded validation only (not performed in this experiment)

1. On a separately authorized root-managed physical device, test ordinary app→Magisk/KernelSU/APatch user-approved `su` from a minimal target-current Kotlin wrapper, with SELinux Enforcing, explicit root denial/withdrawal, separate native process identity and foreground service lifecycle/no `VpnService`.
2. Use actual system Wi-Fi/USB tethering with two controlled downstream clients, separately inspect offload, netd marks/route, NAT+conntrack, DNS UDP/TCP53, v4/v6 and cellular CLAT; verify entry/TUN/real exit packets and end-to-end replies, never globally flush system policy.
3. Confirm owned restore after normal stop and abnormal termination, network handover callback and rebind, background service survival and true phone resource/battery; API37 SDK platform/AVD needs externally available platform image for the missing row. No new automated retries for an unavailable SDK package.

**Disposition:** Keep `android-temp-root-probe` **experimental / limited feasibility**. There is enough AOSP evidence to justify a later independent **thin app→su/root manager feasibility test**, not enough to start or certify the complete Android client or actual hotspot/USB sharing. No main/M0 or existing FEC/retransmit/TLS/MTU core was changed.
