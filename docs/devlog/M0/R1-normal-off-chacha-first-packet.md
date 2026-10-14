# M0 R1 Normal/FEC-off ChaCha-only first authenticated business packet

2026-10-14 | M0 active main G2 revision2 epoch1 | TASK R1-M0-NORMAL-OFF-CHACHA-001

Source inputs, *worker refs unchanged by M0*:
- M1 worker head e511f13359afa267a7ca7dc02f25892ef8f1d3ce, exact tested source 46571e69baa83bd01061ccbf03f03de7f4ab277d, native run38538248506 10/10 M1-only. Bring exact owned `memory/mod.rs` and `runtime/mod.rs` to main via M0-owned integration.
- M3 worker head ef35e6d886013c7be3da5fcdd88caa42b6de3f5b, code SOURCE5a14bb9e1c39be8569b5ebcc98b775a6b882bedb, worker compiled-once native38550461756 11/11 (5 real ChaCha HP8 + 6 FrameBudget) and separate pinned Go wire vectors, all 7/7 triggered runs matching code SOURCE success. Import M3 codec/path budget/record implementation without claiming AES/replay.
- M4 worker head a8dd64dd25817b695280274495e1350ceccc4cae, tested SOURCE bcf0bcacd51029abe5c8af429a000ee8853ceb3d, native run38538117103 6/6 (5 fake, Linux UDP smoke), not a raw TCP-like driver. Import M4 `r1.rs` and the sole `pub mod r1;` export; R0 fixture unchanged.
- M0 remote main entry 795d0e53bbba6fc2665d1477ecf2edad4c599920; cursor sequence25 checkpoint55de2cd0→HEAD only H with Governance38549178834 SUCCESS/CLEAN; no active runs or open PR. M3 independently legally completed main sync and real ChaCha, cursor seq3. M1 and M4 remain ready_for_integration; M2 independent R2 receipt not used for this first-packet test.

One integrated SOURCE in `main` now supplies M1 allocated unique buffer, M3 genuine authenticated in-place ChaCha+HP8, M1 frozen handle and bounded fresh/repair owner, M4 borrowed read-only ready sink, RX M1 allocated buffer, authenticated M3 Open and identical delivered business bytes. Negative cases: forged tag/header cannot deliver, PN burned on seal capacity failure, frozen repair ciphertext reused without another Seal, fresh not blocked by repair, M4 borrow/stop pending never frees M1 memory, fixed FEC/off consumes exactly 31B record overhead and zero additional 20B LINK/56B FEC. `InProcessSink` copies into receiver as a simulated completed OS-copy; **no syscall raw carrier, no live Go V4 exporter/KDF, no Windows native send, no replay bitmap**, and no throughput/physical benchmark. Code leaves ABI features=0 and Go V4 disabled; config/CLI/GUI unaffected because this is a test-only Rust internal integration proof.

A dedicated Actions workflow `.github/workflows/r1-normal-off-chacha.yml` builds exactly one Rust1.85.1 Linux x64 test binary once and ships immutable binary+manifest to separate consumer job; both source code files and lock SHA256 are verified before two actual tests. Other R0 native/governance regression workflows have independent source/run identity; no cross-SOURCE pass composition. Prior signed evidence remains associated with original workers. A failed integrated CI run remains a failure and is recorded before repair, not renamed. Exit only when same main SOURCE first packet workflow + impacted regressions pass and evidence S/H are pushed. Product/performance/physical remain NOT_RUN.

## Observed native Actions and constrained qualification

Exact main code SOURCE `873169078353fcf6b653e613bd6181eaf0da4c5e` triggered **10/10 same-SOURCE completed SUCCESS workflows**:
- r0-static-qualification-audit GitHub run38552615756 attempt1 = success
- governance GitHub run38552615684 attempt1 = success
- g2-scoped-bootstrap-native GitHub run38552615659 attempt1 = success
- r0-link-fec-mtu GitHub run38552615730 attempt1 = success
- r1-normal-off-chacha GitHub run38552615723 attempt1 = success
- r0-native-abi GitHub run38552615774 attempt1 = success
- r0-fake-platform GitHub run38552615848 attempt1 = success
- r0-wire-codec GitHub run38552615746 attempt1 = success
- r0-record-wire-framing GitHub run38552615733 attempt1 = success
- r0-cross-abi GitHub run38552615735 attempt1 = success

Most important: [native first-packet run 38552615723](https://github.com/lly8666/wbd-next/actions/runs/38552615723) first builds one Rust1.85.1 Linux x64 binary (job115813956843), uploads artifact11887855168 digest0621d6..., and separate consumer job115814309653 checks immutable binary SHA256 `189c07e6949f8918e76676329258a50f983a8ae14baef5c539295702c4249e63`, Cargo.lock SHA256 `4147b1175268099e3f42a98bc23aeb08e762f24fa3d718a1d819322efa683b36` plus source parts before **2/2 actual native tests PASS, exit 0**. Log SHA256 `5912b055c18af209e73580e67c81b56c8b116454bbcda4c73a70723fa144edcc`. Result artifact11887422163 digest5b019b... Verified published run IDs/results directly from GitHub; no mixed-source qualification.

First packet sends ciphertext through real imported M4 `submit_ready` but an **in-process sink simulates OS buffer copy**, not a deployed TCP-like carrier or production Go admission. M1 owned TX/RX arenas/frozen handles and M3 real in-place ChaCha+HP8 are genuinely linked. Stop/borrow and negative tamper/failure PN checks pass within this scope. No evidence for AES, RX replay bitmap, Windows ARM native execution, real raw-driver network delivery, live V4 Go exporter/KDF, FEC on, product readiness, CPU improvement or physical. Production capability features stay 0 and Go V4 DISABLED. Evidence receipt: `docs/evidence/M0/R1-normal-off-chacha-first-packet.json`. 
