# M0 protected Go V4 snapshot immutability · 2026-10-15

## Why now and authority
After M0 cursor seq55 H `088b8860051bbf2de2c3c7e5afd03198620e182f` Governance [38682166946](https://github.com/lly8666/wbd-next/actions/runs/38682166946) SUCCESS, remote main unchanged. Main registry rev2 epoch1 M0 active. M2 worker still head `018a07c8`, its G2 code/evidence/H Governance **FAIL** and native44/44 is NOT accepted. Main-authorized one-file exact checker path remains available to independent M2; no M2 branch edited.

The next M0 critical path is real Go V4 protected `ColdSnapshot` → Rust owner. Before creating a trusted ABI, code inspection exposed a trust-source TOCTOU: `V4ClientSession.ColdSnapshot()` and `V4ServerSession.ColdSnapshot()` reconstructed a positive snapshot on every call from mutable exported `Negotiated`, `Epoch`, TLS.Keys. Prior checks rejected malformed edits, but **valid-looking** post-TLS cipher, 1399-byte limit, incarnation/key/principal changes could silently become new positive cold material with no new handshake. That is unacceptable evidence provenance.

## One scoped atom
CODE SOURCE `81703542068158414654a05aa82df0a2718052e1` freezes private `verifiedCold` only from actual protected TLS completion on client and only exposes server result after successful protected reply + `DetachTransition`. Both `ColdSnapshot()` getters now validate the current public session view and independently held TLS Keys against the frozen source; they return the original copy or reject `ErrAdmissionParams`. The source cannot be minted from a caller flipping `coldAuthenticated` on an otherwise assembled session. Existing adversarial Go test extended in-place to preserve the strict 10-case exact-source R0 runner count; no fake Rust or Python Go compatibility substitute.

## Exact Actions
Four on **same CODE SOURCE** `81703542068158414654a05aa82df0a2718052e1` attempt1:
- [Go V4 real protected TLS 38683175022](https://github.com/lly8666/wbd-next/actions/runs/38683175022): **10/10** Go V4 tests, compiled once and consumed hashed artifact.
- [Go control callsite 38683175032](https://github.com/lly8666/wbd-next/actions/runs/38683175032): source-pinned four binary control coverage, build/consume SUCCESS.
- [Go protected ephemeral TLS → Rust 38683175062](https://github.com/lly8666/wbd-next/actions/runs/38683175062): actual pinned Go protected ephemeral test **1** plus Rust release native parser **4/4**, build-once binaries, hashed build/consume artifacts. Session keys in runner temporary 0600 fixture deleted, not uploaded.
- [Governance 38683175016](https://github.com/lly8666/wbd-next/actions/runs/38683175016): SUCCESS.

Run/attempt, artifact IDs, digests, Go/Rust log hashes and exact test boundaries in paired JSON evidence. No performance AB/BA claimed (this is a correctness atom).

## Done and next
This source-immutability atom is complete with exact source evidence. **NOT** a real Go→Rust activated owner: no Rust capability/nonce trust created by parsing bytes; `OWNER_RUNTIME_READY=false`, production R0 ABI capabilities remain 0, no positive FecOrigin. P1–P3/500Mbps, raw live, native Win/ARM, physical are NOT_RUN. No M2 acceptance waiver.

**Exactly one next M0 atom:** wire actual protected Go `ColdSnapshot` to fresh Rust owner generation, with exact Prepare/Detach/CommitAdmission B01–B04 sequencing/leases in native Actions, never self-claim auth based on arbitrary 248-byte payload.
