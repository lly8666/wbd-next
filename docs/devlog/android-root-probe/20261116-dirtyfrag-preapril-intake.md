# 2026-11-16 — DirtyFrag pre-Apr Android16 r07 ARM64 readiness

- Branch restored: `experiment/android-temp-root-probe`, previous HEAD `4a0c5afcce53693910595f6ec86dc21ffaa816fb`. No change to main/M0 and previous KSU Action 43843733837.
- Historical Google SDK snapshot commit `7c23968450618e94727e190d3a2ad3cf8f24adf7` dated 2025-12-02 lists Android16/API36 **Google Play arm64-v8a r07**, archive SHA1 `5b91ef80a5eb60d7b7167528db259c2a12d20e9c` and bytes `1886527965`. Date and package listed, but executable AVD and vulnerability **unverified**.
- Upstream DirtyFrag v1.10 APK sha256 `9ff05645fd239a4af2525fb74a62110e91288bf23c674b12332762dfe5846851`, KSU3.3.1 Manager sha256 `b4a059ace71de2fa65cc7f12b1c58d55fc23ab25e057ee4230ce779742abe450` (GitHub release metadata). DirtyFrag ARMv8 and arm64-only GKI modules cannot run as native exploit under original x86_64 AVD.
- Local container is x86_64, lacks `/dev/kvm` and emulator. Add one dedicated new `ubuntu-24.04-arm` host preflight workflow to learn KVM/emulator reality, not to dispatch a fake app root. First Action has now completed; see exact status and digest below. The AVD and exploit were not executed.
- User now permits temporary SELinux Permissive in *disposable new DirtyFrag AVD*; ordinary original KSU/SELinux Enforcing PASS remains unchanged. No permanent system/boot changes, no physical deployment, no vulnerable binary mirrored into repo.
- Classification before run: DirtyFrag APP→su = NOT_RUN, WBD after-root = NOT_RUN. Only future source-locked root operation may promote, not upstream claims or host preflight success.

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Record historical Android16 ARM64 r07 candidate and isolated host preflight without claiming root or post-root product ability."}
```

## First actual Action evidence and one justified alternate host

- SOURCE `f0b835c70050e88041cb14afbb9b8fd6780c9e27`; [Action43857158313](https://github.com/lly8666/wbd-next/actions/runs/43857158313) `SUCCESS` **of host-only script**, one job `133264265259`, artifact `14220913351`, GitHub declared artifact digest SHA256 `ae90e4e76177830968dd2ca4d35f8c6fcb21372cdf9dce9a6bef95ee268e6718`. Job log actually says `host_arch=aarch64`, `host_kvm_read_write=false`, `host_emulator_path=null`, status `ENV_BLOCKED`, reason `NO_ARM64_KVM`. No guest boot or DirtyFrag run. This is a real negative infrastructure measurement, not a product FAIL.
- Alternate host proposal limited to **one** Apple Silicon `macos-15` runner with Hypervisor.framework (HVF), official macOS ARM64 emulator binary; new isolated `.github/workflows/android-root-dirtyfrag-mac-host.yml` is a read-only host gate, not a repeat of the Linux run and not an exploit. If native HVF unavailable, stop without software emulation, further reruns, or KSU substitution.

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Record precise first Linux ARM64 host KVM ENV_BLOCKED Action/artifact and one independent Apple Silicon HVF preflight; no Android guest/root claim."}
```
