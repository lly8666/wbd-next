# M0 real protected Go V4 cold snapshot · 2026-10-15

## Baseline and legacy source provenance

Recovered main `64c34997a25507626d23bd362529ca219074f0ce`, M0 sequence49 checkpoint `7a3d782807c38f0ba2bb5d16ccb1ba3a892ef56b`; cursor-only H Governance38673568891 SUCCESS. Four third-wave Worker branches unchanged and authorized registry revision2 epoch1.

Contrary to a fully missing-legacy-source hypothesis, main already has **production non-test Go V4 admission overlay** at `r0/go_overlay/internal/realityfront/admission_v4.go`, copied into precisely pinned old Go repo `lly8666/wobuzhidao` SOURCE `a7a82db31fe736ffedee330795a3234d358f1984` at Go1.23.12 Actions. Protected TLS peer tests and direction exporter already existed; the **old runtimeentry explicitly refuses V4** with `ErrR0V4DataPlaneUnavailable` and retains V3 old production default. Do not invent a TLS handshake in Rust.

## Scoped main CODE SOURCE

M0 SOURCE **`e68aff9e4c84e86e7708cb364be401065de1127f`** adds private, only-after-success `coldAuthenticated` marker to `V4ClientSession`/ `V4ServerSession`, set only after real V4 protected reply/exporter derivation (server after DetachTransition). New `ColdSnapshot()` is value-copy-only with inaccessible fields binding authenticated principal, exact old TunnelID16, logical epoch16, incarnation16, lane1..4, cipher, record limits and key pair in c2s/s2c. Defensive validation rejects nil, constructed sessions, missing protected success, bad version/lane/epoch/tunnel/keys and spoof/mutation. Returned getter copies cannot alias Go mutable storage.

Added three actual TLS1.3/uTLS/FakeTCP protected peer tests: all three record ciphers and client/server matching snapshot/keys, false/corrupted sessions; two independent lanes with shared epoch but distinct keys and incarnation; explicit release/new logical tunnel has newly random epoch. Extended previously source SHA-bounded Go compiled-once runner test-count `5→8` without altering the old Go pin. No new wire byte format, C ABI function, positive Rust origin constructor, server transition boundary, or V4 product enablement is asserted.

Exact CODE SOURCE triggered **3/3 Actions SUCCESS**: [Go V4 protected TLS #38674639200](https://github.com/lly8666/wbd-next/actions/runs/38674639200) **8/8** compiled once, independently SHA-attested consumed Go test binary `cc943b85b...`; [old runtime/CLI V4 deny #38674639147](https://github.com/lly8666/wbd-next/actions/runs/38674639147) **SUCCESS**, builds old runtime and client/server CLIs and proves V4 remains disabled; Governance38674639141 SUCCESS. Exact artifacts, old pin, and hashes in `docs/evidence/M0/R1-GoV4-authenticated-cold-snapshot-main.json`.

## Next true handoff boundary (not implemented)

The snapshot does **not** provide a current Rust `TunnelKey`/`LaneKey` allocation generation; old-Go `LaneID` and installation TunnelID cannot act as Rust owner generations. A reviewed versioned Go→Rust cold byte command must receive source from this protected snapshot, copy secrets immediately inside Rust without retaining Go pointers, bind exact trusted 16B logical epoch, both directional derived 76B materials, unique Rust owner generation, negotiated record persona/MSS and exact server `PrepareTransition`/ `DetachTransition` RX/TX sequence boundaries. Only after two owner installs and CommitAdmission may it produce a production positive `FecOrigin`. Server epoch store `ReleaseLane` must be linked to scoped closing/abort; rolling back on partial failure needs a verified test, not GC.

**No public production FecOrigin / product enable**. Real AF_PACKET RX/TX, Windows/ARM native, physical/sustained500Mbps/p99/CPU/RSS, end-to-end live Go V4 are NOT_RUN. This is a true cold Go authenticated proof producer but no trusted Rust command consumer yet.

## Next M0 atom

Implement separately and verify a minimal versioned cold command+test with source provenance and fake owner generation, rejecting missing/mismatched origin, epoch/direction/nonce and copied-buffer races, while preserving existing ABI features=0. Do not blindly serialise a private Go pointer or guess sequence boundaries. Third-wave Workers independently own their assigned atoms; no reassign without new H.
