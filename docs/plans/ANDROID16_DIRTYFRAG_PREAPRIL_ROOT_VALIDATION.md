# Android16 pre-Apr 2026 AVD + DirtyFrag temporary-root feasibility gate

**Sole development branch:** `experiment/android-temp-root-probe`. The original completed KSU/adb-root results retain their exact SOURCE. This is a separate scenario and does not reopen full Android client development.

## Pin the historical ARM64 emulator image, not only a GSI

Google SDK `google_apis_playstore` Android16/API36 `arm64-v8a` **r07** is already listed in [the repository-history 2025-12-02 snapshot](https://github.com/eagletmt/android-repository-history/blob/7c23968450618e94727e190d3a2ad3cf8f24adf7/repository/sys-img/google_apis_playstore/sys-img2-1.xml) (`7c23968450618e94727e190d3a2ad3cf8f24adf7`), well before 2026-04-01. Exact archive: `https://dl.google.com/android/repository/sys-img/google_apis_playstore/arm64-v8a-36_r07.zip`, size **1886527965**, SDK catalog **SHA-1 `5b91ef80a5eb60d7b7167528db259c2a12d20e9c`**. Download availability and SHA256 remain NOT_VERIFIED. Do not let `sdkmanager` silently replace r07: verify archive SHA-1, then pin calculated SHA256 in the Action manifest.

Android16 can use `android15-6.6` or `android16-6.12` GKI; neither OS release nor Linux 6.x alone proves DirtyFrag vulnerability. The image is a **candidate** until guest kernel/SPL and a real vulnerability probe are observed.

## Stage 0 (implemented): one Action ARM64 host preflight

`.github/workflows/android-root-dirtyfrag-host.yml` triggers only on its own files or manual workflow dispatch. Its single `ubuntu-24.04-arm` job records actual architecture, `/dev/kvm`, Linux ARM64 emulator host availability and SOURCE, and exits with machine-readable `ENV_BLOCKED` if absent. No AVD, app, exploit or privileged guest command. This prevents a green CI status from masquerading as root. Do not repeat dispatch on environmental blockage.

**Known portability issue:** [mitschud DirtyFrag](https://github.com/mitschud/DirtyFrag) builds only `arm64-v8a` and uses ARMv8 assembly plus ARM64 GKI `.ko`, so the existing x86_64 Android16 Actions AVD and x86 host KVM cannot validate it. Google does not publish Linux-aarch64 host emulator binaries in the regular SDK repository; obtain a trusted, reviewed build or use native ARM64/KVM self-hosted lab. Lack of this runtime is `ENV_BLOCKED`, not exploit FAIL.

## Stage 1 (conditional): one old Google Play ARM64 guest

On a capable native ARM64/KVM host, boot a fresh disposable r07 AVD with a compatible ARM64 emulator; hard stop if hardware acceleration is unavailable, no snapshots or software emulation fallback. Save `ro.build.version.release/sdk/security_patch`, `ro.build.fingerprint`, `ro.build.type`, `ro.debuggable`, `ro.product.cpu.abi`, `uname -r`, page size, `id`, capabilities, `getenforce`, kernel KMI, modules/vermagic and permissions. Require Android16/API36, Linux kernel >=6.0, security patch/build not later than 2026-03-31, ARM64, Google Play `user`/`ro.debuggable=0`, non-root shell, `adb root` **denied**, no KSU ramdisk or su bridge. Otherwise `INVALID_BASELINE` or `ENV_BLOCKED`.

## Stage 2 (conditional): genuine DirtyFrag EoP, explicit bounded exercise

Before running check a real CVE-2026-43284 page-cache primitive, upstream KMI exactness, kernel module loading policy and required `IpSecManager`, `crash_dump64`, `/vendor/bin/insmod` and vendor_file paths/SELinux labels. Emulator vendor differences might make the upstream Samsung-focused exploit unusable even if the kernel is theoretically vulnerable. No substitution with ADB root or prepatched KernelSU. Fix no kernel or OS image in place to manufacture a pass.

Pin official upstream [DirtyFrag v1.10](https://github.com/mitschud/DirtyFrag/releases/tag/v1.10) release APK SHA256 `9ff05645fd239a4af2525fb74a62110e91288bf23c674b12332762dfe5846851` and [KernelSU v3.3.1 manager](https://github.com/tiann/KernelSU/releases/tag/v3.3.1) APK SHA256 `b4a059ace71de2fa65cc7f12b1c58d55fc23ab25e057ee4230ce779742abe450`; verify that Manager packages `libksud.so` before claiming compatibility. Install into isolated AVD, launch exploit from **ordinary App**, cap run ~70–120s, record UI/runner logs, user grant and resulting *App→su* child `id -u`, CapEff/CapPrm/CapBnd and SELinux domain. Simply showing `SUCCESS` on screen or a KSU manager UI is not root PASS.

User now explicitly authorizes a temporary SELinux Permissive interval **inside this new disposable AVD experiment only**. Record transitions and re-Enforcing; after test reboot fresh and verify root absent. Kernel panic/guest crash => FAIL with preserved evidence, no random retry; no physical device, system/boot permanent mutation, global netfilter flush or old KSU case rewrite.

## Stage 3 (only if Stage 2 truly passes): WBD bounded ability probes

Reuse original ARM64 Rust NDK probe at exact SOURCE/manifest/hash: `inspect` first, then owned `exercise` for real TUN read/write, raw TCP send/receive/checksum, cap and SELinux, UID-specific routing/netd underlay, DNS UDP+TCP53/IPv6, normal/abnormal owned cleanup. Compare with original KSU case *by execution path*, not as performance/CPU causal A/B. AVD never proves real hotspot/USB, offload, physical Wi-Fi/cellular/CLAT or phone energy; all stay NOT_RUN.

## Stop and disposition

Maximum one AVD per Action, max three independent Actions concurrently, boot <=5min, root attempt <=120s, full attempt <=25min. No rerun on missing host/image. Preserve FAIL and NOT_RUN, precise SOURCE, file/ZIP SHA256, old SDK snapshot, image fingerprint, kernel, App identity/caps, rule and route before-after and recovery. `ENV_BLOCKED` for missing host/emulator/image; `UNAVAILABLE` for kernel patched/missing exploit prerequisites; `FAIL` for actual guest crash/cleanup defect; `SUPPORTED_IN_SCOPE` only for verified real App→su and subsequent native operations. At this writing **root NOT_RUN; after-root WBD NOT_RUN**.

## First host result / alternate host

Real Linux ARM64 host preflight [Action43857158313](https://github.com/lly8666/wbd-next/actions/runs/43857158313) SOURCE `f0b835c70050e88041cb14afbb9b8fd6780c9e27` reported actual `aarch64` but `/dev/kvm` inaccessible and emulator binary missing, **ENV_BLOCKED/NO_ARM64_KVM**; Action CI success only validates the host script. One nonidentical host qualification on Apple Silicon macOS with HVF is permitted as a bounded alternative; see `.github/workflows/android-root-dirtyfrag-mac-host.yml`, which does not boot or exploit a guest. No further host retries without evidence.
