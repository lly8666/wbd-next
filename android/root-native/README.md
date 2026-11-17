# Android ARM64 Root product-native adapter (A2)

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
  FD with outstanding driver loans. A new ARM64-only original M4 Normal/off
  worker now calls the same M1/M3 owner; Stop signals two kernel eventfds,
  synchronously joins RX/TX, then retires the original owner and FDs.
  **Source compilation is not actual device I/O or join evidence.**

- Before the first original Go FakeTCP SYN/TLS ClientHello, Android root cold
  CLI requires `--android-network-handle`; `faketcp` uses libandroid
  per-socket `android_setsocknetwork` plus exact SO_BINDTODEVICE on its
  existing IPPROTO_RAW sender, while keeping original AF_PACKET RX. This
  does not make existing Linux CLI TUN setup Android production routing.

## 2026-11-17 ARM64-only target

Only Android arm64-v8a (aarch64-linux-android / Go arm64) is developed,
compiled, packaged and qualified. Historical Android x86 stages are archived
but NOT target gates. Existing Linux/Windows x86 code and tests are unaffected.

Large cross-layer SOURCE batches combine original Go cold control, shared Rust
M1/M3, actual Bionic RAW/TUN, borrowed-FD Stop and catalog/governance.
Independent code paths are prepared concurrently, then integrated once and
validated by one ARM64 Actions run. No fake M4 ABI to force the link green.

## ARM64 A2 original M4 worker batch

`crates/wbd-engine/src/v4_android_original_m4.rs` is a **real**
ARM64-only pair of native readiness threads (not placeholder C symbols):
- Original M1 slab and single M3 replay/AEAD/Normal LINK, strict checksum/
  tuple original carrier and verified Go client /32 before TUN delivery.
- Original FrozenRecord/PN + shared IPv4/TCP writer on bound RAW socket;
  no Go/Java packet callbacks or auto-resend of an uncertain send.
- Original canonical encrypted HealthClock kind0 from the very same Rust
  owner: only native AEAD+unique PN+typed control can refresh peer activity.
- Physical Network MTU and ifindex recheck, fail-closed on changes.
- One eventfd per worker, no 10ms idle spinner; Stop signals both, joins
  both BEFORE original crypto retirement, checks original BorrowFence and
  removes owned RAW/TUN FDs only after drained.

**Remaining blockers**: source-locked ARM64 Go *full* FEC/Game/M2 linker
has missing genuine original modes; ARM64 health and Stop are not yet
device-executed. One source lock and static M4 symbol check CANNOT be
promoted into real WBD connectivity, multi-IP jumbo delivery, finished
root UI/controller, FEC/Game or Android16 KSU acceptance.

## ARM64 Normal/off original-Go product edition

Source-locked Go now uses original `wbd_v4_embedded_go` **without**
`wbd_v4_fec2_product`; the repository already provides disabled
Fixed/Auto/Game branches which explicitly reject unsupported modes.
No placeholder FEC/Game C symbols, no second TLS/AEAD or fake M2.

Original Android Normal/off `stage/readback` verifies this same
Go-authenticated nonzero epoch, feature3 and increasing revision. A green
Rust ARM64 ELF still does NOT mean a linked Go executable or real device.

The existing non-FEC original Go server adoption signature names a
`V4LinuxGameAuthenticatedLane` whose definition originally lives only in
the mature Game build. Android's Normal/off product edition now supplies
only that original protected **Normal** type and a strict policy reader,
requiring real ColdSnapshot/commit/association and refusing every FEC/Game
policy. This is type-level source closure, NOT a stub Game runtime.
