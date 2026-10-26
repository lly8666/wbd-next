> **2026-10-26 用户新指令：本页旧建议已被 [持续双分支集成合同](M0-FEC-GAME-TUN-ROLLING-MERGE-CONTRACT-20261026.md) 覆盖。实验分支（含外层重传策略）作为架构权威；main Windows 接线作为 adapter。下面七路径旧主从表只作历史审查记录，禁止按旧方案直接集成。**

# M0 integration review — source-locked experimental FEC / Game / TUN (2026-10-26)

> **Unmerged integration candidate only**. Not a qualified public Windows/Linux build. No silent replacement of main-owned shared components; no historical evidence, FAIL or retired workflow deleted.

## Frozen history & inventory
- Base main: `c6866577e1d2326dd169fdbddf9acda1eb93ac86`; experiment: `de8cbc563ea3ac284ae6f58d953548ceb8f156bf`; merge base: `d8ba2cf270ff6ca5cadae6dab778c49c32636ef6`. Stage source SHA is the exact *final blob* at experiment freeze, not intermediate test candidate; latest independent experiments can continue on their own branch.
- Git-blob exact 3-way inventory: 737 experiment-only final blobs staged (47 `crates/` or `r0/go_overlay/` code files, 12 workflows, other tests/config/docs/evidence); main 13 main-only files preserved; 40 experiment-only deletions intentionally not imported, preserving prior M0 original FAIL evidence and older CI history.
- Four non-runtime items excluded from staging: `AGENTS.md`, `PROJECT_CHARTER.md`, `START_HERE.md`, `tests/network/request.json` (maintain main authority, avoid stale one-shot request). Registry/permissions/M0 cursor not changed.
- W130–W134 shared Go→Rust authenticated DATA handoff and five independent Linux ARM64 original product actions PASS_SCOPED source `6c38ed0df9da3547c7bd604b51f13443d6863181`; W137–W140 Game sparse FEC closure/deadline source `e40098f0d238adc362ab096b5bd6e5b3b4fa852e` plus scoped Actions. W135/W136 RX `recvmmsg` +3.43% / +2.09% CPU regression **reverted**, do not restore. W138 new authenticated `ConflictingBlock` increased; Game high-rate CPU PSI capacity stop, Windows/GUI/physical not qualified.
- Main latest S879 exact Windows→Linux native WL-N0 Action40295748769/1 original FAIL product exit; experimental Linux passes do not replace it.

## Seven actual both-changed git paths and resolution proposal

| Shared path | Main facts to preserve | Experiment facts to adopt if compatible | Proposed resolution / gate |
|---|---|---|---|
| `.github/workflows/m0-wl-public-normal-full.yml` | Same-SOURCE Linux build, original signed Windows/Npcap/Wintun, exact WSL2 300ms IFB/tc 10Mbps bidirectional WL-N0 / cleanup | Older short public flow and binary selection | **main as owner**. Keep main native WL-N0/ABI/owned cleanup, introduce experimental FEC/Game Actions as distinct scoped jobs; never replace WL-N0 with older short smoke. |
| `.governance/workstreams/M0/cursor.json` | H273 and pending S871–S880 main evidence; registry M0 branch=main | Experimental obsolete H timestamp/source and stale next_action | **main exclusively**. Ignore branch cursor. After source-locked combined results, create fresh S and cursor-only H, no epoch reset. |
| `crates/wbd-engine/src/v4_embedded_go.rs` | S875→S879 Linux Normal/off original Go M1 bounded arena, owner startup/current crash diagnostic | Large W130 five-mode real Go→Rust RX handoff, shared FEC runtime, W137 Game sparse parity/next-due scheduler, TUN transaction changes | **manual function-level merge**; preserve original Normal TLS+M2 and bounded source slab, graft authenticated post-detach BPF/one RX owner and independent Game deadline. Keep feature3/7 gates, keep Stop/lease budget. Native ARM64 five-mode functional batch + Windows native WL-N0 before promotion. |
| `crates/wbd-engine/src/v4_windows_owner.rs` | Rust M2 1536 bounded shadow, 2048-slot M1 original source arena, auth highwater path | Older Rust M2 768/1024 plus independent FEC code | **main 1536/2048** until measured alternative, import only compatible crypto/interface improvements; no return to ACK HOL or forged cumulative confirmation. Windows original owner ABI + real Npcap/Wintun Actions. |
| `r0/go_overlay/assembly/manifest-plan020-m0.json` | Exact original-Go frozen blob and S875–S879 Windows peer/hot-state hashes | Older manifest hashes and mode source mapping | **regenerate manifest from merged Go final blobs**, retaining original Go immutable source and no overwrite, validating each original_blob/result_blob in Actions. Neither old manifest blindly replaces the other. |
| `r0/go_overlay/cmd/wbd-client/m0_native_v4_peer_windows.go` | Original real kernel Wintun owner, independent M3 authenticated >4MiB highwater, 1536 credit and instrumented M2 failure label | Older 768 credit with FEC2 source send/receive | **main for native packet loop**, port only compatible experimental feature-7 changes after Rust/Go ABI match. Original M3 validation before movement, no false ACK, preserve owned Stop. |
| `tools/m0_wl_public_normal_e2e.py` | New exact SOURCE Linux build selection, 300ms netem IFB real duplex 60s, WL-N0 result and Stop | Legacy short smoke with old `621bc...` pinned Linux binary | **main as authority**, retain old smoke as optional functional early stage, never run legacy binary in same-SOURCE network qualification; do not drop rate/TC measurements. |

## Unresolved *semantic* boundary in otherwise nonoverlap blobs
New `crates/wbd-codec`, `wbd-recovery`, `wbd-platform`, `v4_game_lane.rs`, `v4_game_fec.rs`, Go Linux client/server/TUN, new raw detached DATA filter and default fq600 make linked references into the experimental `v4_embedded_go.rs`. The staged branch therefore may not link with main's unmerged `v4_embedded_go.rs`; **not a compile PASS**. Applying these files to main separately without a combined test would be unsafe.

## Validation and disposition
1. Freeze both parents and reconcile seven paths in one manual integration source with no old code/FAIL deletion. Test native Linux ARM64 five modes, original Windows native ABI+WAL, true two-OS WL-N0 and readiness/owner lifecycle in GitHub Actions, source-pinned.
2. Test one scenario per performance Action; STOP if host CPU/PSI capacity. Keep Game4 sparse `ConflictingBlock` and Windows/physical gaps OPEN until discriminating evidence.
3. User asked for each shared conflict separately; this PR is review-only until the seven decisions are confirmed and combined source truly passes. Do not auto-merge.
