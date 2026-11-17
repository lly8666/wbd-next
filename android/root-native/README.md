# Android Root product-native adapter (A1 / A2 I/O seam)

Production adapter boundary, **not** the existing probe or a connectable APK.

- `android_abi.c`: compile-time Bionic ifreq/TUN/socket ABI gates for Android64.
- `crates/wbd-platform/src/android_root_io.rs`: owned TUN FD handoff; A2
  strictly bounded Bionic RAW IPv4 TX and tuple-filtered RX socket owners,
  tied to the caller's exact Android Network/ifindex/physical MTU/generation.
  TX requires a complete packet built by the original Rust owner and its
  approved route budget, RX remains untrusted until original AEAD/replay.
  No unbound fallback, global fwmark/UID bypass, TUN creation or route mutation.
  **These real syscall adapters are not yet wired to the original M4 loop.**
- `build-source-locked.sh`: NDK cross-build of **actual shared `wbd-engine`**
  and pinned original-Go product CLI overlay using Android GOOS/CGO, excluding
  native ISA-L to keep Normal/off first-connect unblocked.
- `.github/workflows/android-root-product-a1.yml`: source-locked, hash-checked
  build-only Action; genuine TLS/lease/real server delivery and Stop are NOT_RUN.

**Next A2:** wire original-Go FakeTCP TLS/authenticated cold handoff, selected
physical Android Network and Rust authenticated M4 raw/TUN workloop; A3 then
test Android16 genuine KSU App ↔ source-locked Linux WBD server, real TCP/UDP.
No VpnService, fake TLS, new protocol or probe-derived production success.
