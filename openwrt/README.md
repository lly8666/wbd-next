# OpenWrt ARM64 client

The native Rust Linux aarch64-musl `wbd-engine` and codec build can be validated
in Actions. An actual OpenWrt client also requires the **same-source public
original-Go authenticated client**, the target libc/loader compatibility and
TUN/AF_PACKET/raw permissions. They are not established by Rust cross-build.

This opt-in OpenWrt package does not auto-start, change the host network, or
store credentials. It consumes explicit source-locked product artifacts from
an approved build rather than compiling/fetching floating code in an OpenWrt
package phase. Provide `WBD_ARM64_STAGE=/absolute/path` containing:
- `wbd-v4-client` — target AArch64 musl public Go TLS client
- `libwbd_engine.so` — ABI-compatible target AArch64 musl Rust owner
- `SHA256SUMS` — exact hashes of both files

Copy `openwrt/package` into the OpenWrt feed, build with the SDK for aarch64,
then validate the resulting .ipk on a real OpenWrt device (or qualified image).
`@TARGET_aarch64` may need to be adjusted to a board's actual OpenWrt TARGET
symbol; do not claim that a generic Linux build is a working router package.
The client requires `/dev/net/tun`, an actual underlying interface, raw socket
permissions (CAP_NET_RAW/root), `ip`, and a matching C runtime.

**No service autostart:** original-Go V4 CLI currently takes a password as a
command-line argument. It is inappropriate to generate a procd service that
publishes credentials via process argv. Add a tested fd-based secret input and
owned procd Stop before enabling auto-start; do not substitute hard-coded
test keys. Credential verification and real bidirectional kernel traffic must
PASS on the target, otherwise OPENWRT_PRODUCT=NOT_RUN.
