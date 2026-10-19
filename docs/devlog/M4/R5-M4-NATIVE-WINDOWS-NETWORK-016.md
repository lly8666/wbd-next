# M4-016 — PLAN-010 original Windows native product network (2026-10-19)

**Authority:** main registry rev2 epoch1 task `R5-M4-NATIVE-WINDOWS-NETWORK-016`, branch `work/m4-r1-platform`; M0 decision `docs/decisions/M0-windows-native-migration-2026-10-19.md` and self-dispatch `docs/decisions/M0-M4-016-Windows-Actions-self-dispatch-2026-10-19.md`. Scope only previously permitted M4 paths plus new `r0/go_overlay/internal/windowsclient/`. No worker edit of protected Rust/main workflows or legacy upstream.

## 015 closeout / source locks

Prior H26 `c6683c66f57b0b3cf4cc113c0d21266992d24186`, central G2 run 39225046360 attempt1 PASS job117969159793, artifact12172779881 SHA256 1492170198ee16f74251ad9e21af18262407e5850f3be6f1d6eaaad52d71d2e8. Original Go source `a7a82db31fe736ffedee330795a3234d358f1984`, M4 H26 source in M0 Actions 39225427878 attempt1 with all four jobs SUCCESS: attestation117970424157, Linux x64 117970498297, ARM64 117970498457, Win x64 original Go config + WinForms GUI selftest117970498310. These prove source-locked **scoped original Go build/config and GUI tests**, not native Windows network, Rust FFI or real applied ACK. Separate worker Governance 39225015969 FAIL stays recorded; no falsified green result. Product FEC2 OFF; existing 015 evidence documents source/artifact digests.

## 016 full workpack

- Frozen cold source: `lly8666/wobuzhidao@a7a82db31fe736ffedee330795a3234d358f1984`; donor 12 Windows-only exact deltas `6ec6b5836c2b70a85f2ef89c2f5ea4525c6ed340` (6 products + 6 tests); authoritative Git blobs from `docs/evidence/M0/PLAN-010-windows-native-migration.json`. Do not upgrade entire legacy checkout or root source-lock.
- Expand **one existing** `r0/go_overlay/assembly/assemble.py` and `manifest.json` with exact original/donor/final hashes (no fuzzy patch), copy donor sources into `r0/go_overlay/internal/windowsclient/`. Preserve initial 015 12 assembly operations. Negative tests wrong old blob, tamper, symlink, duplicate path.
- Native Windows single-instance Go product façade: Prepare/Apply/Cleanup/Recover/owned WAL, real API/readback, defaults DNS 1.1.1.1/8.8.8.8, IPv6, route/Direct bypass; no runtime powershell/pwsh/cmd/netsh/route. CLI/GUI recovery and config/portable must use the *same* client executable and genuine process completion. M0 owns real Rust Stop/ACK interface; do not mark cleanup finished before actual Rust Stop.
- Native Windows scope allowed normal exception/Stop/restart/one-proxy, not simultaneous third-party VPNs or extreme ghost-device automated healing. Unsupported native WFP, missing MTU ghost recovery or unavailable isolated Win host must fail closed and remain NOT_RUN.
- New request I one-file `.governance/workstreams/M4/requests/M4-016-WIN-NATIVE-001.json` only **after** code SOURCE and manifest sha256 frozen. Central G2 then M0 main-only dispatcher, control `qualification/m4-product-windows-v1@17263ad85a41639a569af914b4157520daf84ecb`. Do not repeat old 015 Actions solely for task registration.
- Native Windows 2022 and 2025 where supported, plus isolated network full product only with proven isolated recovery. Record run/attempt/jobs/artifacts, preserve FAIL, and do not infer physical/Windows 10/11 or Rust product qualification from unit tests. FEC2 production OFF.

State: work initiated, **016 product implementation/test NOT_RUN** until exact current Actions. Full product main merge M0-only after verified acceptance.
