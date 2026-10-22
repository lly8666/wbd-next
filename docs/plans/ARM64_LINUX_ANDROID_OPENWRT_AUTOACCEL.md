# ARM64/Linux + Android/OpenWrt clients and auto acceleration — implementation plan

Status: IN_PROGRESS on isolated branch; no existing main role/cursor/task modified. Baseline main `5fd93440c42aeba8c64b4625b0d6b0f95adaa711`. This document is a proposed implementation plan, not a claim of product readiness.

## Scope
- Native Linux aarch64 client **and** server (public Go credential TLS -> Rust record/recovery/FEC -> Linux AF_PACKET/raw/TUN, two-way, owned Stop).
- Android arm64 client via Android VpnService-owned TUN fd and protected underlay sockets; Android does **not** receive Linux raw-socket/CAP_NET_RAW privileges.
- OpenWrt arm64 client using ordinary Linux TUN/raw or, where raw is unavailable, an explicitly qualified non-privileged transport adapter. No kernel/driver deception.
- Keep existing Windows x64 and Linux x64 behavior. Windows ARM64 server/client is NOT in scope.
- Hardware acceleration is **auto preferred** across all architectures: actual CPU-supported AEAD/HP in existing libraries; FEC2 uses pinned ISA-L when compiled/available, otherwise scalar. No hard crash or bogus NativeIsaL report on unsupported targets. No unverified driver or network performance label.

## Reuse/reference inventory (do not fork protocol)
- Pinned Rust 1.85.1; `aws-lc-rs=1.18.1`, `aes=0.8.4`, `chacha20=0.9.1`.
- FEC2 `crates/wbd-codec/src/fec_v2.rs`: k<=16, Cauchy coefficients, 2-byte original-length source symbol, 12-byte repair header, max 4 parity rows/quantum, missing-only inverse. Do not use old V1 generator or ISA-L default matrix.
- Native FFI `native/isal-safe`: pinned ISA-L v2.31.1 SHA `c387163fcbca62701d646149564c550c78a4f985`. The historical frozen `7cef7e849e293373d907a3b64007b4ce8946da78` target-aware build script already accepts aarch64 Linux. Native ARM64 wrapper Action `39084579161` ARM job passed; specific NEON/SVE dispatch and FEC2/product did NOT run. Avoid floating system archives.
- `wbd-platform` Linux syscall islands currently x86_64-gnu cfg, with explicit struct layouts requiring separate aarch64 static/real ABI tests. `v4_embedded_go` additionally has x86 gates.
- Go public Linux `r0/go_overlay/internal/v4productcli/linux.go` opens owned TUN and authenticates through original Go TLS. Android needs separate OS fd/process lifecycle contract; no permission to call that Linux path.

## Implementation packages (in-order gates, each may advance independently)
1. **Architecture/cpu backend (this branch first).** Make platform-target ISA-L build explicit and source locked; add a backend preference that chooses native when genuinely linked and supported, scalar otherwise; make default runtime FEC2 owner *request* acceleration, not require it. Record Used=NativeIsaL only after C call. Verify ARM64 RustCrypto AES-HP configuration and AWS-LC built-in CPU dispatch. No new cipher.
2. **Linux ARM64 syscall ABI and Go/Rust owner.** Replace hard-coded x86-only cfg only where ABI audit proves AArch64 GNU 64-bit layout. Add native assertions for msghdr/mmsghdr/iovec/ifreq/offsets, MSG_DONTWAIT, ioctl and real Stop. Port raw/TUN and scoped route watchers. Rebuild v4 embedded Go path in arm64 native runner, run genuine Go TLS + raw/TUN before any product PASS. Do not confuse cargo cross build with native OS run.
3. **Android client.** An Android VpnService must create/protect the TUN and sockets, establish permitted routes, detach/join on Stop; an NDK Rust cdylib + JNI or an explicit minimal C ABI hands in owned FD, not a new authentication origin. Keep Go original credential TLS and immutable record path, never fake kernel WFP/raw. Must test emulator/real Android kernel VPN and native network; Gradle compile-only is NOT_RUN product.
4. **OpenWrt client.** Build with target-specific toolchain (prefer aarch64 musl) and fixed source dependencies. Validate libc, ABI, TUN, CAP_NET_RAW/socket availability and normal init/ubus/process cleanup. Produce .ipk feed integration only after real target/emulated interface proof. Never assume Android or glibc archive can link on musl.
5. **One-source Actions gates.** Cross build aarch64-linux-gnu, aarch64-linux-musl, aarch64-linux-android and x86_64 regressions; native `ubuntu-24.04-arm` crypto/FEC2/FFI/packet tests; pinned ISA-L actual encode; backend choice/fallback and equivalence. Network performance one independent scenario per Action (functional tests batched), same job prior/new for CPU. Calibrate host before increasing load. Preserve FAIL and NOT_RUN.

## Backend policy
- AEAD: `aws-lc-rs` in-process CPU-dispatched implementations; AES-HP: RustCrypto `aes_armv8` cfg for arm64 if native target supports it, otherwise software. x86 AES-NI remains library-managed.
- FEC2: Auto selection means *try vetted native when compiled+correct*, scalar otherwise; length<64 or k=1 uses scalar. `RequireNative` remains a diagnostic hard assertion and must error when unavailable. A runtime C failure must be reported as a failure, not silently change the wire outcome.
- ARM ISA-L dispatcher can choose SVE/NEON/basic using HWCAP; correctness equality and instruction-path proof are separate. Never set blanket unsafe `target-cpu=native` in distributed artifacts, never mix x86 ISA-L archives with arm64.
- No feature gating or optimization is permitted to skip authentication, reuse PN, mutate FrozenRecord, block fresh on FEC, or skip owned Stop.

## Evidence levels and exit criteria
| Level | Gate |
|---|---|
| BUILD | Exact target builds, link/ABI, dependency manifest; may not execute |
| NATIVE_COMPONENT | Actual ARM64 crypto/FEC2 scalar/native matched wire+repair, negative cases |
| NATIVE_OS | Genuine ARM Linux AF_PACKET/TUN, Go TLS -> Rust owner, owned stop |
| ANDROID / OPENWRT PRODUCT | Real platform clients through OS interface and reverse app traffic; scoped environment and cleanup |
| PERFORMANCE | Same-host one-scene original/accelerated A/B, CPU, p99, no new HOL, capacity measured |

## Known initial gaps
ARM64 product raw/TUN and Go/Rust linked runtime, Android VpnService/JNI and OpenWrt service package are **NOT_RUN**. ARM ISA-L `ec_encode_data` safe wrapper passed scoped in historical Action `39084579161`, but current main `native/isal-safe/build.rs` excludes ARM64; source lock needs integrating. Do not copy an x64 PASS onto ARM64.

## Immediate working sequence
Commit the plan and target-aware backend selector with a focused Rust native/ARM runner workflow; then audit and port Linux syscall islands; only after those gates bring up Android and OpenWrt adapters. Any missing run must remain NOT_RUN rather than claim a finished multi-platform product.
