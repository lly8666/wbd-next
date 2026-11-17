# Android Root product-native adapter (A1 / A2 I/O seam)

Production adapter boundary, **not** the existing probe or a connectable APK.

- `android_abi.c`: compile-time Bionic ifreq/TUN/socket ABI gates for Android64.
- `crates/wbd-platform/src/android_root_io.rs`: owned TUN FD handoff; A2
  strictly bounded Bionic RAW IPv4 TX and tuple-filtered RX socket owners,
  tied to the caller's exact Android Network/ifindex/physical MTU/generation.
  TX requires a complete packet built by the original Rust owner and its
  approved route budget, RX remains untrusted until original AEAD/replay.
  No unbound fallback, global fwmark/UID bypass, TUN creation or route mutation.
  The A2 handoff binds the original authenticated Rust Entry to this exact
  Network and owns both RAW FDs and duplicated TUN FD; the live M4 loop
  has **not** been ported and no DATA is sent/received by these handles.
- `build-source-locked.sh`: NDK cross-build of **actual shared `wbd-engine`**
  and pinned original-Go product CLI overlay using Android GOOS/CGO, excluding
  native ISA-L to keep Normal/off first-connect unblocked.
- `.github/workflows/android-root-product-a1.yml`: source-locked, hash-checked
  build-only Action; genuine TLS/lease/real server delivery and Stop are NOT_RUN.

**Next A2:** wire original-Go FakeTCP TLS/authenticated cold handoff, selected
physical Android Network and Rust authenticated M4 raw/TUN workloop; A3 then
test Android16 genuine KSU App ↔ source-locked Linux WBD server, real TCP/UDP.
No VpnService, fake TLS, new protocol or probe-derived production success.

- `r0/go_overlay/internal/realityfront/bridge_v4_android_network_android.go`:
  Android-only original Go post-TLS, post-Detach physical Network/MTU bridge.
  The Linux twin rejects Android-only values and preserves its existing path.
  The root app must supply a real Network handle; none is invented here.

- A2 borrowed-I/O safety: existing `wbd-platform::r1::BorrowFence` guards
  every synchronous RAW/TUN syscall. Original Entry Stop refuses to close an
  FD with outstanding driver loans; M4 worker join is still **NOT_RUN**.
