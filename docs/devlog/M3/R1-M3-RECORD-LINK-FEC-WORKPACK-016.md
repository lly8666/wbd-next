# M3 · PACK-006 / workpack016 — first LINK payload-peak boundary

main assigned task `R1-M3-RECORD-LINK-FEC-WORKPACK-016` at worker base `0ecb459c9686254625a045ea19b85ae0e8d43080`. Exact task is a full capability packet, not qualification of old 015. Prior cursor seq18 still points to historical 014; old 015 compiled Debug 99/99 at SOURCE0ecb and its exact Release run38713050270 failed CPU clock accounting on old source79535. Main workflow was subsequently pinned to 0ecb; do not infer Release PASS without exact run receipt.

## Why this source correction

`link_reassembly.rs` counted held fragment bytes in `MAX_BUFFERED_BYTES`, but complete reassembly allocated a new contiguous `Vec` *while the parts still remained owned*. This can transiently exceed the 16×65535 (~1MiB) slow-path payload cap by the complete packet's length. L03/L04 specifically require counting old parts and new output together and keeping unrelated ordinary packets deliverable.

Fix adds `evict_oldest_except(target)` on completed allocation, so only older incomplete assemblies are retired until held parts + new output fit; never silently discards the completed packet when other assemblies can be evicted. Allocation failure retires only the affected completed packet. New `r1_link_sixteen_near_full_packets_completion_accounts_both_live_copies` native test stages 16×65535B datagrams, withholds tails, finishes newest, checks the oldest is retired and small packet still bypasses, plus exact reassembled business bytes.

Scope: M3-only `crates/wbd-codec/` tests and implementation, no new Go/engine/ABI feature or guaranteed product outcome. Subsequent workpacket needs source-locked C01–C04, L01–L04, F01–F06, exact old-Go/ISA-L source and native ISA hardware evidence; no broad product performance claims. Record final native run after Actions settles.

## L02 / bounded frozen-budget LINK issue plan

Add `LinkPacketPlan::new`/`issue_next(current_frame_mtu)`: immutable one-packet MTU and stride; emits at most one complete Go-compatible wire frame per owner call, borrowed logical source (no up-front 64KiB fragment Vecs), explicit terminal `MtuShrank` preserving count/required/current. Returning frame transfers wire to caller; any retry must use frozen record and original PN, not reseal/reissue. Owner must use NEW ID after plan abandoned. Native Go golden byte equivalence on ordinary/magic/WF/MTU±1/max65535 and active partial MTU1400→1000 with independent ID and surviving ordinary small business tested. This is codec-level API only, not proof of engine actual scheduling or real MTU notification. No new Go, ABI, shared workflow or root dependency.

## Native result, release recovery and remaining boundaries

At exact workpack CODE `5f8fccbc3d9e75d72d6ef12a30fcf6971ff51da1`, native Rust1.85.1 run [38997823633](https://github.com/lly8666/wbd-next/actions/runs/38997823633) PASS **101/101** with the new link-plan test, built binary `b46596c697...`, receipt log sha256 `bf003fb2...`. Own Governance run38997823643 SUCCESS. Prior source a9c935d4 100/100 and Governance38997570161 SUCCESS. New test and code are source-bound; production engine integration, performance and system delivery were NOT_RUN.

Recovery of 015: source-locked corrected CPU/wall Release run [38734823257](https://github.com/lly8666/wbd-next/actions/runs/38734823257), M0 workflow SOURCE3f1b458d, M3 worker SOURCE0ecb459c, Rust1.85.1 RELEASE compiled once, authentic 2 tunnel x2 directions, 192/896 ×4 modes ×3 rounds = 24/24, per-window CPU<=1.02×wall, schedstat_ns, CPU status SCOPED_VALID_SAME_WINDOW. Median FEC fresh/steady 192B 3.201527/1.051086 us per record (3.0459×), 896B 3.443202/1.351853 us (2.5470×). This supplements old cursor which still listed 014. 015 79535dd5 failed [38713050270](https://github.com/lly8666/wbd-next/actions/runs/38713050270), the later 0ecb exact run is successful. Only COMPONENT CPU result; not packet p99, FEC real parity decode load, Go V4 authenticated source or 500Mbps.

Workpack016 still PARTIAL: low-impact codec L02/L03 fixes are native proven; real external MTU notifications, Game/FEC-on, sustained parity fresh fairness, native ISA-L, Linux/ARM/Windows target and Go KDF V4 source/ABI qualification require additional owned testing/integration. Do not promote historical 015 results to 016 new SOURCE qualification. See evidence JSON for hashes and limitations.

## L02/L03 authorized receiver MTU transition

`ReassemblyTable::update_authorized_frame_mtu` is an authenticated owner-driven transition preserving old packet assemblies and observed stride across 1400→1000→1500. RX allows old-authorized maximum frames while a previously issued packet is in flight; current TX still uses only the latest FrameBudget. Added native test drains old ID, fully delivers new ID in smaller stride, handles late old duplicate as Discarded, ordinary small packet bypass and invalid MTU atomic failure. The RX high-water bound is per-owner scope until the owner recreates the table at lifecycle reset, never inferred from untrusted packet fields. Not a production route notification or M0 engine wiring proof.

## F01/F05 — parity-first-send ready chunk interface (not repair)

New `TxBatch::take_ready_parity_chunk` returns at most four precomputed parity rows (in the original Go row order) for an external fresh-send scheduler turn, not the retransmission/10% repair budget. PACK016 native scenario runs healthy continuous 20:20 at 256B/512B/1200B, three full blocks each: every one of 60 source arrivals produces immediate systematic, 60 real parity rows are exposed in bounded <=4-frame chunks, with exact block IDs, configured metadata and wire-byte counts, no delayed queue/slack. The method is explicitly ready-output-only: existing scalar encoding on 20th source is synchronous and needs separate measured max-continuous-CPU validation; this codec assertion **does not prove actual kernel send fairness/driver success/age**, which M0/M1 must integrate. Other FEC classes and native ISA-L remain in scope.

## F03/F04 all k×r higher erasure recovery and variable lengths

Rust native test now exercises all k1..20 × all configured parity profiles × L1/65/257 (plus k20 L1200) with e1/2/4/full-min(k,r) and leading/trailing missing patterns, nonuniform original shard lengths and reversed deterministic parity selection. Uses immutable old-Go generator coefficients already asserted in earlier golden tests. This broadens beyond prior e<=4 sample but does not constitute native ISA-L verification or a real Go V4 session.

## PACK016 L02 & F01/F03/F04/F05 checked through source 93d80cb09b4e477d5c096c89ba46da086d3b039f

- Authorized RX MTU transitions, old packet already fragmented at1400 then current1000 and later1500 with new ID, ordinary packet no HOL and invalid update atomic: SOURCE8587cff3 [native38998927569](https://github.com/lly8666/wbd-next/actions/runs/38998927569) 102/102 PASS, binary sha256 fc106c45..., prior SOURCE5f8fcc 101/101.
- FEC first-send parity chunk interface at most4 rows/turn, with three complete 20:20 blocks for each size256/512/1200B and exact systematic/parity counts: SOURCEefe878bd [native38999036805](https://github.com/lly8666/wbd-next/actions/runs/38999036805) 103/103 PASS. No claim of actual driver scheduling; encoding remains synchronous on block close.
- FEC scalar Go-generator high-erasure all k/r with variable lengths and e up to min(k,r): SOURCE93d80cb09b4e477d5c096c89ba46da086d3b039f [native38999161286](https://github.com/lly8666/wbd-next/actions/runs/38999161286) **104/104 PASS**, binary sha256 76edf08c..., log sha256 96b17611.... No ISA-L native backend yet; no produced Go oracle replacement, existing immutable Go source vector checks remain separate.
- Governance: old S/H 38998060898/38998156987 failed while control or worker moved; new 38999036867 GitHub REST403 reading old commit; 38999161387 GitHub REST403 reading main. This is a connector/API governance audit limitation, not native test failure. Under Governance v2 main-owned central scope last confirmed source a9c935 run38997674443 PASS; still need exact final central SOURCE scope PASS, do not claim CLEAN.

Remaining workpack unqualified: ISA-L native binding and target dispatch, real Go V4 authenticated provenance, production FEC-on/Game, parity output queue fairness under sustained real traffic, actual MTU notification and service time, packet p99, 500Mbps. No shared source edits.

## F05 real GF row-cooperative parity job — codec-only proof

Added `ReedSolomon20::encode_rows_active` / `final_parity_wires_range`, and `FecParityJob` owning one closed block's moved (not recopied) source payload. `take_next_rows(&codec)` computes at most 4 **new** GF row outputs per scheduler turn; unlike the previous TxBatch ready drain, it does not synchronously precompute all 20 parity rows. On complete, retained source payload is released, with monotone exactly-once row index. Exhaustive differential checks for k1..20, r4/8/10/12/16/20, lengths 1/63/64/65/257/512 and full k20 L1200 compare every output byte to existing all-at-once pinned-Go-matrix scalar format; malformed job/range cases fail closed. CPU/wall maximum continuous time, ISA-L acceleration, queue backpressure, and real FecTxOwner/engine integration are explicitly NOT qualified. The new optional job is an independent codec interface, not yet wired to production `FecTxOwner::close`; no claim of fairness or zero-latency full parity generation.

## 016 F05 cooperative true parity GF job (source `605f7de1507781f42d0bd6a002d9ee2d063b2764`)

`ReedSolomon20::final_parity_wires_range` calculates only newly requested rows using original Go-normalized 20×20 GF generator; `FecParityJob` retains a moved closed block, releases payload on completion and computes at most four *new* parity rows per call. Byte-for-byte exhaustive comparisons with legacy full-batch output cover k1..20/r4/8/10/12/16/20 and short/boundary/unaligned/1200B records. Invalid state/ranges fail closed. [Native run38999954180](https://github.com/lly8666/wbd-next/actions/runs/38999954180) **106/106 PASS** at exact source, binary SHA256 `75fc75fe...`, test log SHA256 `a2a75341...`. This new job is NOT wired into the existing `FecTxOwner::close`; old code still has one-batch synchronous parity, and no scheduler service budget/100µs, queue accounting or NIC fairness qualified.

Governance for exact source is inconclusive/FAIL because GitHub REST HTTP403 in both legacy checker run38999954233 and central scoped read run38999964044. Independent M0 request in this role folder asks for a fail-closed local-git based audit or bounded API-read repair. M3 does not alter shared audit scripts.

## F05 actual FecTxOwner cooperative source/admission/pressure bridge

`FecTxOwner::new_cooperative` and `poll_cooperative_parity` now use owned `FecParityJob` on actual 20th-source/32ms/reconfig/pressure close instead of synchronously precomputing all parity. The old `new` synchronous path is unchanged. Pending source payload bytes are included in the same `budget`, pending jobs have separate 64-job metadata bound, and backpressure returns `TxError::Backpressure` instead of silently dropping parity; no source/packet ID admitted on rejection. A poll performs at most 4 genuine GF rows and retains old source payload until the final row. Tests run 3×20 full blocks at 256/512/1200B against old real parity wires and assert source-first, no issued duplicate, budget and metadata backpressure, fake-clock/flush/reconfiguration; no driver/NIC or hardware ISA-L claim.
