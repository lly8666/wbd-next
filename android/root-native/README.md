# Android Root product-native adapter (A1)

Production adapter boundary, **not** the existing probe or a connectable APK.

- `android_abi.c`: compile-time Bionic ifreq/TUN/socket ABI gates for Android64.
- `crates/wbd-platform/src/android_root_io.rs`: owned TUN FD handoff and strict
  Android Network+SO_BINDTODEVICE binding of *this* raw socket only, no global
  fwmark/UID bypass, no TUN creation or system route mutation. These low-level
  routines are not yet wired to the original authenticated Rust M4 owner.
- `build-source-locked.sh`: NDK cross-build of **actual shared `wbd-engine`**
  and pinned original-Go product CLI overlay using Android GOOS/CGO, excluding
  native ISA-L to keep Normal/off first-connect unblocked.
- `.github/workflows/android-root-product-a1.yml`: source-locked, hash-checked
  build-only Action; genuine TLS/lease/real server delivery and Stop are NOT_RUN.

**Next A2:** wire original-Go FakeTCP TLS/authenticated cold handoff, selected
physical Android Network and Rust authenticated M4 raw/TUN workloop; A3 then
test Android16 genuine KSU App ↔ source-locked Linux WBD server, real TCP/UDP.
No VpnService, fake TLS, new protocol or probe-derived production success.
