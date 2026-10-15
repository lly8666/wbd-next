# M0 · R1-M0-GO-V4-COLD-BOUNDARY-MAIN-015 · 2026-10-15

## Exact recovery and old-source boundary
M0 prior H `275fa23ed67810581c760122bc17e16ce17254f1`, seq50 checkpoint `bed61eb9fd4f0066f08f16433600379ea4f80d83`, Governance38674960955 SUCCESS. Third-wave M1–M4 workers had advanced new role-owned commits but no new formal H at this preflight, so those works were **not accepted** or overwritten. Registry remains rev2 epoch1 and active.

Pinned old Go `lly8666/wobuzhidao` SOURCE `a7a82db31fe736ffedee330795a3234d358f1984` contains real StageTransition. Server `PrepareTransition` captures old bootstrap `NextSeq()` into the RX boundary; `DetachTransition` returns bounded early queue. They are not translatable from wire numbers or latest observed seq. Rust `TunnelKey`/`LaneKey` generations must be allocated/verified locally, not derived from Go TunnelID/LaneID.

## One implementation atom
M0 CODE SOURCE **`1d6ed7603f94b106b7731dfb99eb2faff9bf155e`** adds the exact **248B WBCO version1** in-process cold session copy format to the *already authentically protected* Go `V4ColdSessionSnapshot`. Offsets:
- 0..12 magic, version, total, client/server role, Go lane, cipher and reserved=0.
- 12..60 authenticated 16B Go tunnel ID, 16B logical epoch and 16B per-lane incarnation.
- 60..96 client/server record limits (BE u16) and domain-separated SHA256 principal binding.
- 96..172 C2S 76B derived material; 172..248 S2C 76B derived material.

Go source checks snapshot private fields and never writes these keys to production disk. Rust `wbd-engine/src/cold_v4.rs` separately copies and parses the exact grammar, checking lengths, zero identities, reserved, direction keys and expected local owner generation/scope. **Its type is `UntrustedColdV4`, not an authenticated Go capability**. Successful byte parsing is not authorization; no engine command or production FecOrigin is exposed. Rust C ABI features remain zero, Go runtimeentry continues rejecting V4.

New source-locked native Actions `r0-v4-cold-native.yml` compiles pinned real Go TLS and Rust lib tests exactly once; an independent consumer runs an actual Go protected TLS peer with real session exporter, emits one **ephemeral 0600** in-runner 248B secret fixture, and runs the precompiled Rust parser over the actual Go bytes. Temporary fixture is removed and intentionally omitted from uploaded build/result artifacts. Manifest includes exact SOURCE, old Go pinned SHA and binary/input SHA; logs include only non-secret status. This is stronger than comparing manually invented vectors but is still not a live C ABI or raw carrier.

## Exact Actions on final code SOURCE
**13/13** triggered exact SOURCE Actions SUCCESS, including:
- [Go V4 TLS38675661651](https://github.com/lly8666/wbd-next/actions/runs/38675661651) **10/10** (two added cold wire tests); compiled-once Go binary sha256 `4601a7f62234ef200848e77bc87dd40decfa08f044c9806c6e3e2d76facc4b89`.
- [Go TLS→Rust native38675661675](https://github.com/lly8666/wbd-next/actions/runs/38675661675) one real Go TLS ephemeral export plus **4/4** Rust parser tests, Go/Rust binaries source SHA verified; result artifact ZIP digest `sha256:2a81b757f6c1f7042c94ff1c328f118d4a2369e899cfd6eecc5b7df937254695`.
- [Old Go control V4 deny38675661661](https://github.com/lly8666/wbd-next/actions/runs/38675661661) SUCCESS, both CLI binary builds; native Go+C+Rust ABI [38675661861](https://github.com/lly8666/wbd-next/actions/runs/38675661861) SUCCESS; Governance38675661613 SUCCESS.
- Other same SOURCE R0 audit, G2, R1 normal/FEC/wake/kernel, R2 receipt and R0 cross ABI all SUCCESS. Cross ABI only means **build/inspect**, never target-native execution.

Full artifact IDs, SHA-256, run IDs, success and scope in `docs/evidence/M0/R1-GoV4-cold-boundary-main.json`.

## Performance timing (user requested)
`docs/architecture/TEST_PLAN.md` authorizes **P0 isolated native component microbenchmark now**, with pinned source, effective config, real measurement and repeatability; no product throughput claim. Production comparison **P1** requires Go trusted cold→Rust owner installation and generation/Prepare+Detach boundary, genuine AF_PACKET TX/RX, Normal/off actual business delivery, and bounded lifecycle. Then **P2** old/new sequential A/B on the **same job/VM**, warmup10s measure60s per leg (and reverse BA if needed), with p99/CPU-s/RSS/drops/effective config/source. **P3** capacity 10→50→100→200→500Mbps only while host/injector not saturated. Current actual perf measurements remain **NOT_RUN**. The performance microbenchmark can be the next M0 independent atom, not a manufactured measured 500Mbps PASS or date promise.

## Next boundary
Production must still bind actual Go successfully authenticated session **as the caller identity**, verify Rust owner-generation allocation, both directions' install, exact RX/TX transition boundaries and explicit CommitAdmission and cleanup, then and only then permit positive FecOrigin. Current bytes alone remain spoofable by an untrusted writer; no automatic product feature activation. M1–M4 third-wave worker atoms remain isolated.
