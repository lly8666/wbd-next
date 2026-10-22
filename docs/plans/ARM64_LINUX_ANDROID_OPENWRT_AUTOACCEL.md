# Linux ARM64 first: native client/server, hardware-auto FEC and product verification

**Active scope (2026-10-22): Linux ARM64 client AND server only.** Android and OpenWrt clients have been explicitly deferred by the user. Their previously committed source and scoped BUILD receipts are preserved; do not add more Android/OpenWrt features, jobs, packages, or release qualifications during the Linux phase. Windows ARM64 is out of scope. This is a separate feature branch; do not alter the main registry, role cursor, or other workers' files.

## Exact recovery and evidence
- Starting branch HEAD at reprioritization: `b9bf7cc7f6a422b3566cf17e2cb409daf6698556`. This is **not** a product PASS.
- Previous full scoped Linux ARM64 native component/ISA-L workflow `39749018948` at `3fea6502193eda8a6864d89e5884795e6bf47ed1`: SUCCESS.
- Previous cross-platform build-only workflow `39749868699` at `b9bf7cc7f6a422b3566cf17e2cb409daf6698556`: SUCCESS; Android/OpenWrt work now deferred.
- Latest scoped Linux ARM64 `39749868638` same source: overall FAIL. ISA-L job PASS; `wbd-platform` test `r1_borrow_stop_and_acquire_race_is_fenced` intermittently FAIL due scheduling before main stop. Preserve the failure; fix test coordination without changing production shutdown semantics.
- Public Go/Rust bundle `39749665256` at `aa0a52b83b568d2335b67c4537bf5f255edc6b9d`: FAIL, the assembled original Go V4 Game product symbols are absent because 3 additional overlay files are not copied. Do not mark as compiler/silicon failure; fix source-locked assembly list and verify Go/Rust full ABI on ARM64.
- Full Linux ARM64 true app-to-app through privileged TUN/raw, authenticated receipts, owned Stop and impaired-network trials: **NOT_RUN**.
- Pinned original Go `a7a82db31fe736ffedee330795a3234d358f1984`, ISA-L `c387163fcbca62701d646149564c550c78a4f985`, Rust `1.85.1`, Go `1.23.12`.

## Product architecture to preserve
- Genuine original Go credential-bound TLS and FakeTCP lifecycle; one Rust AEAD/PN/FrozenRecord and M2 feedback owner; existing Linux AF_PACKET/raw TX/RX, TUN and generation/Stop. No duplicate public identity or new fake protocol.
- Preserve FEC2 mathematical coefficients/wire, authenticated input, low-HOL quantum, bounded caches and absent/recovered source accounting.
- Existing `aws-lc-rs` AEAD CPU dispatch. For AArch64 RustCrypto AES-HP uses `aes_armv8` runtime CPU detection with software fallback. No forced unsafe CPU ISA in shipped binaries.
- FEC2 `BackendChoice::default() = PreferNative`; when exact pinned ISA-L feature and library are present, short cases still use scalar and actual native reports only after the real encode/decode. No native feature means scalar. `RequireNative` remains diagnostic, not public default. Do not swallow runtime native errors as success.
- The pinned ISA-L ARM NEON/SVE dispatch exists, but actual NEON path and product use require independently scoped proof; x86 ratios are not ARM64 performance claims.

## Linux ARM64 implementation gates (ordered)
1. **Recover & stabilize components.** Fix ARM test scheduling nondeterminism, check exact ISA-L ARM64 actual SIMD direct call test, maintain scalar/native parity equality and x64 regression. A FAIL at previous SHA remains FAIL.
2. **Native original Go ↔ Rust build.** Assemble *all* corresponding frozen original-Go overlay files into pinned legacy clone, build Rust cdylib with pinned ISA-L, test real original-Go adapter, compile native arm64 `wbd-v4-client` and `wbd-v4-server` against the same `libwbd_engine.so`, create verifiable SHA256 manifest and run `--version` or supported inert CLI launch. BUILD is not a TLS/data-plane PASS.
3. **64-bit Linux ABI / privilege/Stop.** Verify AArch64 kernel `capget/capset`, `mmsghdr`/`msghdr`/`iovec`, `sockaddr_ll`, `ifreq`, route/MTU, batch/TUN, immutable-prefix receipts and generation-scoped Stop. Native unprivileged tests do not count as privileged raw/TUN.
4. **Real two-way functional owner.** Use genuine Go TLS + Rust AEAD + raw/TUN across two independent Linux ARM64 endpoints or a fully qualified isolated network namespace with actual kernel routing and original application bytes; repeat first-send, recovered/lost feedback, stale/duplicate, failure close, restart and Stop. Do not fake PASS based on Go tests, iptables rules, or loopback-only fixtures.
5. **Performance only after functional PASS.** One independently scoped trial per Action, same VM/job scalar/native pair, CPU cost + latency to first useful business + p99 + HOL/queue and memory. Avoid overload and don't promote cross-build or component PASS.

## Minimal deliverables / done criteria
- Build and artifact: exact SOURCE ARM64 Go client/server, Rust engine, pinned ISA-L, compiler/libraries and SHA256 receipt.
- ARM64 NATIVE_COMPONENT: AEAD/HP/FEC2, native backend reporter, negative CPU/scalar fallback, Stop/loan test.
- Linux NATIVE_OS: verified raw/TUN and actual original-Go handshake; record unavailable privileges as BLOCKED exact environment, not success.
- PUBLIC PRODUCT: authenticated client-server bidirectional application delivery + bounded fresh/recovery/Stop evidence.
- Performance: only after product functional pass, one scene per Action. Preserve original FAILs and NOT_RUNs.

## Explicitly deferred
- Android VpnService/JNI/NDK client, emulator/product/routing.
- OpenWrt musl .ipk/procd client, SDK/real-router interoperability.
- Any new Android/OpenWrt Actions are **manual only**, not part of Linux ARM64 required gates. Existing build-only results remain historical and are not OS or product-qualified.

**Immediate next action at this update:** fix source-locked Go overlay compilation and deterministic Stop race fixture, then verify the ARM64 bundle from the exact new branch SHA. Never infer future work completion from this plan.
