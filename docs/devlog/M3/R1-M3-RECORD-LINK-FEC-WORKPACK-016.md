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
