# Android ordinary APK to real su — source-specific outcome (2026-11-16)

## Actual emulator result

One real, installed debug APK on AOSP Android16/API36 x86_64, SELinux Enforcing, with Android runtime targetSdk37 / minSdk28, app UID 10150, SELinux context u:r:untrusted_app:s0:c150,c256,c512,c768, CapEff/CapPrm/CapBnd all zero. No VpnService or system privilege declared. AOSP developer su exists at /system/xbin/su, mode -rwsr-x--- (4750), owner root:shell. The ordinary app is NOT a member of shell. Its actual ProcessBuilder -> su -c fails exec with EACCES errno13 before spawning a root child; no native TUN/raw was attempted through app-su.

Test 1: APK SOURCE f9956db60ecb113b18bc28419d15751eb437cbb8, hardcoded AOSP su path. GitHub Action 43811154343 FAILED the app-su functional gate but successfully ran the app and preserved its private JSON. Artifact 14200372347 ZIP SHA256 0bef451f31b71d8116fe329dca06051b0f9350b7906c22e8e37645547446095e; APK SHA256 230d0d053f9aa640d02a4a9d77ee0646bd51e9bda7b97136c0e0af05def2507f.

Test 2: revised APK SOURCE 2a8344f29c8f4a65a7d16fae183b0f7808082080, standard manager-friendly PATH lookup of su, and strict single-native-exercise JSON validation (native UID 0 + both TUN/raw SUPPORTED_IN_SCOPE required). GitHub Action 43811844216 FAILED the same actual app-su gate: ProcessBuilder("su", "-c", ...) IOException error=13. Artifact 14200472781 ZIP SHA256 42fb7b695b78839d54b219ad6f84c01895aca4dd06d4ccc5013a902e4c04f0ff; APK SHA256 c1b4069019723760c160df3047be83b17b192c0b67ac994e7cc65caeb37fddf6.

Both source-bound packages compiled against installed API36 android.jar (CI has no API37 platform), but generated installed APK manifest targetSdk37 without lowering target. Verified app runtime also reads targetSdk37. Real native historical artifact SOURCE 42cca27e8a6b8d4e5db38e72c2b3ddd0fef61b2d was SHA256-verified and staged by unprivileged adb shell. adb root was never called in this APK case. That native executable was NOT launched by an app-authorized su child.

## Correct scope and stop decision

**Observed PERMISSION_DENIED at app->AOSP su exec gate.** This is not a generic Android16 unsupport verdict: system engineer/developer su is different from a user-approval capable Magisk/KernelSU/APatch root manager. Running the same unmodified official AOSP emulator across other API versions does not supply the missing manager; skip redundant version matrix. Do not chmod/chgrp system su, inject supplementary shell GID, create a fake su bridge, patch boot/system, install root managers or disable SELinux to manufacture a false pass.

Root-manager-ready thin APK code is committed on experiment/android-temp-root-probe: it invokes su via app PATH; shows the real foreground Activity status; persists app UID/context, su stdout+errno, and strictly validates native TUN+raw JSON before positive qualification. A genuine rooted emulator with an already installed real user-approval manager is now the blocking external prerequisite. On such an environment, one API36 App->approve su->native owned TUN/raw canary is the only next test needed. Until then: APP_TO_SU=PERMISSION_DENIED, native app-owned TUN/raw=NOT_RUN, app background/FGS/network switch/NAT/hotspot/USB remain NOT_RUN.

Prior adb-root native TUN/raw and private-network-namespace policy route positives remain valid **only** for their original SOURCE and adb-root context. No main/M0/core, real device, global routing, firewall, boot/system or SELinux changes.
