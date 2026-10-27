# M0 PLAN025 — recovered exact full development-tree overwrite and governance/CI repair (2026-10-27)

## User override, source integrity
User instructed `integration/w168-freeze-windows-adapter-20261026` **fully overwrite** `main`, with temporary integration authority, and resolve governance conflicts. Prior main HEAD `7a193226df20924fd3a5c52c8587c31547877b16`, source branch HEAD `9d2362d30bead0e2a36dd19233a798ec1fb2b3ae`. The developer source is already main ancestry through the existing two-parent merge. Commit `f6469a3468839efcba1242ccdeaa7ea86d6d67c2` was fast-forwarded onto main, without force; its **exact tree SHA** `553d50ad7f996559bd739b391beb10d7325724da` equals the developer branch tree. Older main-only handoff docs remain in Git history; no evidence was invalidated by deletion from the active tree.

## Recovered terminal facts before code changes
- SOURCE `9d2362d...` `40476182202/1` FAIL, artifact `12721601306` digest `sha256:be6564e470c58cba87798654a5e890d2f681a7cc5b57bf298568f8c412fdfb36`: original TLS, two-OS signed Npcap/Wintun↔Linux raw/TUN genuine bidirectional kernel UDP/TCP passed within observed scope; client at ~29s exited with **original M2 control TX sequence mismatch expected=2744012027 got=2744012455**. Dynamic 2s/8s Auto and owned full Stop target FAIL/NOT_RUN, not a product positive. New exact record `docs/evidence/M0/PLAN025-W168-Auto-natural-source9d2362d-failure-recovered-20261027.json`; root cause UNKNOWN.
- Previously source `4977f120...` `40449519463` PASS seven individually effective native modes and `a0c8eeb...` `40457048399` PASS user-requested revision2 only. Not natural quality-driven Auto, global WinForms/WFP/IPv6, 150/200Mbps, or this new main SOURCE qualification.
- The prior main merge SOURCE `02a9d938...` multiple push Actions failed Rust `E0425` (`v4_game_lane.rs:507`, non-FEC build has undefined `arena`), while FEC native `40479993126` executed **15 passed 0 failed** but its workflow incorrectly asserted exactly 13. Original FAILs not erased.
- Exact overwrite SOURCE `f6469a...`: governance Action `40482476244/1` FAIL with `evidence is for a different SOURCE` in old cursor and missing changed-devlog feature-impact; g2-scoped native `40482476243/1` FAIL same Rust `E0425`; both evidence separate from product test.

## Narrow repair, no redesign
Recovered M0 H288 cursor now acknowledges the overwritten main, uses exactly one failing SOURCE-specific JSON evidence rather than mixing historical PASS and FAIL in current evidence_refs; main registry resumes the already authorized full product task and unchanged rev3/epoch1. Four existing **experimental** feature cards mark code `available_on` main (not formal promotion). Correct a Rust `#[cfg(feature="fec2_product_record")]` binding/use imbalance in Game4 arena setup; FEC mode keeps the previous arena allocation/assignment, off build no longer references its absent local. Adjust the native ISAL harness count to the actual 15 named real tests, retain all five separately named mandatory checks. This is a compile/harness repair, not an additional product feature.

No local execution tests. Push Actions on the repaired SOURCE are required; any initial FAIL remains a FAIL for its own SOURCE. Do not re-run native Windows natural Auto solely to refresh old green, do not relax M2 strict SEQ, authentication, WAL or Stop, and do not assert unmeasured performance.

```feature-impact
{"kind":"updated","ids":["fec-auto","fec-fixed","game-fixed-fec","game-lanes"],"reason":"Recovered the true main availability of code following the user's complete dev-tree overwrite; all four entries remain experimental. Rust non-FEC cfg compile and native test-count harness repairs do not change selectors/defaults or prove new product qualification."}
```

## Recovered Actions from repaired source `6d358570793fb31490279925c3054cf50552f8ae`
- Main Governance `40483279152/1` **SUCCESS** (not product PASS); FEC2 native ISAL exact 15-test `40483279168/1` **SUCCESS**; r0 cross ABI `40483279285/1` and native ABI `40483279423/1` **SUCCESS** scoped.
- Governance maintenance `40483279301/1` **FAIL** in historical `test_m4_frozen_windows_main_import.py`: frozen M4 34-file test compared three post-PLAN020 M0-owned modified live files to old M4 blobs. Frozen original `assembly/manifest.json` is still pinned; active `manifest-plan020-m0.json` correctly pins the three current exact blobs. This follow-on changes only the test comparison to assert **both** frozen historical manifest and active M0 manifest, and retains byte equality on every unchanged M4 path. No original-Go source was reverted, no skip added.
- `40483279381` G2 bootstrap FAIL `G2 registry revision changed` (needs its own source-aware contract review); native functional receipt `40483279229` FAILED four genuine r2 budget/repair cases while other named subsets passed; PLAN012 PREENABLE `40483279286` FAIL, not product PASS. Windows preflight `40483279255` still in progress at this recovery observation. These independent failures remain open; do not suppress or infer success from Governance green.

## Source `24c480bdf5b8dab757dab08e6c1a41768cc80ca2` maintenance resolution
- Main Governance Action `40483931968/1` **SUCCESS**; governance maintenance Action `40483931609/1` **SUCCESS**, including preserved M4 historical exact pins and three PLAN020 current overrides.
- Standalone G2 bootstrap Action `40483279381/1` was not a Rust compile failure after cfg fix: Rust workspace compiled, then `tools/g2_bootstrap_bundle.py` rejected current rev3 with hardcoded `revision==2` / four active workers. Rev3 assigned M4 reserved epoch2, and M1–M3 main historical cursor snapshots remain rev2, so refusing genuine live state was an obsolete pre-PLAN020 fixture assumption.
- Following patch updates only that G2 identity fixture to validate explicit current rev3 M0 active, M1–M3 active, M4 reserved with zero grant and untouched historical rev2 cursor, plus negative tests. Keep non-product bootstrap scope, exact binary manifest and native execution, never make failed role edits pass.

## Windows extreme remediation isolated S1 (2026-10-27)
PR32 merged to main as 4e6d9d634bee75c965594dea51cf7bca87408a8b. Main registry rev3 M0 epoch1 PLAN025, cursor H291 checked. No queued/in-progress runs at initial recovery. Historical source6d35857 Action40483279255 final FAIL and source9d2362d natural Auto M2 TX sequence FAIL remain exact.
Pre-edit re-read latest Rust Windows FEC2 source5ff5da and prior 9d2362d/ca0a7a9, original M2 owner source7f9e4 and Go window sourcec1e98830 recent 8642ad4. Source A2 Arena.allocate after fec2_tx.take discards stream on capacity error. Go A3 uses stale cumulative int32 negative before authentic owner verification; target half-wrap/full-wrap replay boundary.
S1: preallocate before FixedStream ownership take and assert full->release->same-generation actual firstsend. Detach stale Go presentation ACK after genuine M3-verified far-window arrival and allow independently authenticated serial near moving high across half/full wrap. Strict AEAD, Wintun copy and no fake ACK retained. Updated active PLAN020 assembly manifest exact Go bytes. Remaining A1 and C1 through E are OPEN, no full product Actions until entire batch frozen.

```feature-impact
{"kind":"updated","ids":["normal-off","fec-fixed"],"reason":"Experimental Windows FEC state capacity recovery and authenticated half/full serial wrap; no new product or performance PASS or default changes."}
```

## Isolated Windows remediation S2 (C1 fresh / optional repair)
Re-read current Windows original M2 trusted NPF completion and GlobalRepairAllocator::on_fresh_accepted contract, ReceiptState::on_sent and current v3 opportunities. Original Go queried shadow outstanding on *every* packet and paused fresh at1536, despite independent repair cache meaning. Rust v3_seal duplicated gate. Both are removed, while exact accepted M4 result still feeds F credit and only optional immutable cache is abandoned at saturation. New native-scoped Rust regression makes >1536 actual first sends with shadow fixed<=1536, same generation; original ciphertext/peer ACK remain protected. This is not proof of 500Mbps or total memory envelope. Repair budget C2 and Auto C3 remain open.
```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Experimental Windows v3 firstsend no longer gated by optional 1536-entry repair shadow; product performance requires future exact frozen SOURCE native Actions."}
```
