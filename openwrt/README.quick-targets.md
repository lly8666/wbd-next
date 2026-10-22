# ARM64 target labels

- `aarch64-unknown-linux-gnu`: normal Linux glibc client/server, native Actions.
- `aarch64-unknown-linux-musl`: OpenWrt-appropriate Rust build starting point;
  check actual OpenWrt SDK ABI and Go CGO toolchain before packaging.
- `aarch64-linux-android`: Android NDK Rust core only; NEVER reuse Linux raw
  sockets or the OpenWrt TUN owner. VPN must use Android VpnService.
- `x86_64-unknown-linux-gnu`: existing Linux baseline.
- `x86_64-pc-windows-msvc`: existing Windows baseline. Windows ARM64 excluded.

Accelerator policy: AWS-LC auto AEAD, RustCrypto AES HP runtime detection on
AArch64, pinned ISA-L ARM64 FEC2 only when built in and verified; otherwise
scalar. NEON presence is NOT proof of actual dispatched instruction.
