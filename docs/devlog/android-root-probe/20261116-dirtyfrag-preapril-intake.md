# 2026-11-16 — DirtyFrag pre-Apr Android16 r07 ARM64 readiness

- Branch restored: `experiment/android-temp-root-probe`, previous HEAD `4a0c5afcce53693910595f6ec86dc21ffaa816fb`. No change to main/M0 and previous KSU Action 43843733837.
- Historical Google SDK snapshot commit `7c23968450618e94727e190d3a2ad3cf8f24adf7` dated 2025-12-02 lists Android16/API36 **Google Play arm64-v8a r07**, archive SHA1 `5b91ef80a5eb60d7b7167528db259c2a12d20e9c` and bytes `1886527965`. Date and package listed, but executable AVD and vulnerability **unverified**.
- Upstream DirtyFrag v1.10 APK sha256 `9ff05645fd239a4af2525fb74a62110e91288bf23c674b12332762dfe5846851`, KSU3.3.1 Manager sha256 `b4a059ace71de2fa65cc7f12b1c58d55fc23ab25e057ee4230ce779742abe450` (GitHub release metadata). DirtyFrag ARMv8 and arm64-only GKI modules cannot run as native exploit under original x86_64 AVD.
- Local container is x86_64, lacks `/dev/kvm` and emulator. Add one dedicated new `ubuntu-24.04-arm` host preflight workflow to learn KVM/emulator reality, not to dispatch a fake app root. Result and artifact SHA to append after Action finishes; the AVD and exploit were not executed.
- User now permits temporary SELinux Permissive in *disposable new DirtyFrag AVD*; ordinary original KSU/SELinux Enforcing PASS remains unchanged. No permanent system/boot changes, no physical deployment, no vulnerable binary mirrored into repo.
- Classification before run: DirtyFrag APP→su = NOT_RUN, WBD after-root = NOT_RUN. Only future source-locked root operation may promote, not upstream claims or host preflight success.

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Record historical Android16 ARM64 r07 candidate and isolated host preflight without claiming root or post-root product ability."}
```
