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

```json
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

```json
{"kind":"updated","ids":["normal-off","fec-fixed"],"reason":"Experimental Windows FEC state capacity recovery and authenticated half/full serial wrap; no new product or performance PASS or default changes."}
```

## Isolated Windows remediation S2 (C1 fresh / optional repair)
Re-read current Windows original M2 trusted NPF completion and GlobalRepairAllocator::on_fresh_accepted contract, ReceiptState::on_sent and current v3 opportunities. Original Go queried shadow outstanding on *every* packet and paused fresh at1536, despite independent repair cache meaning. Rust v3_seal duplicated gate. Both are removed, while exact accepted M4 result still feeds F credit and only optional immutable cache is abandoned at saturation. New native-scoped Rust regression makes >1536 actual first sends with shadow fixed<=1536, same generation; original ciphertext/peer ACK remain protected. This is not proof of 500Mbps or total memory envelope. Repair budget C2 and Auto C3 remain open.
```json
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Experimental Windows v3 firstsend no longer gated by optional 1536-entry repair shadow; product performance requires future exact frozen SOURCE native Actions."}
```

## Windows extreme remediation S3 (narrow B1/B2 cold-proc and FEC parity buffer cost)
Reviewed original Windows PrivateOwnerBridge single absolute source-pinned loaded DLL, Fixed stream FFI caller and live original M4 CreatedWintun.Identity. Implemented owner-local concurrent cached proc lookup instead of each Fixed call FindProc; still rejects absent symbols. Cached immutable iphlpapi ConvertInterfaceLuidToGuid LazyProc but kept actual current native Identity/holder Verify for now (protected session lease coalescing NOT YET DONE). Replaced 8KiB per-poll Go parity batch allocation with sync.Pool while preserving complete Rust C struct overwrite and per-row deep-copied ciphertext before return. Added Windows-only real DLL proc cache negative/positive test to existing authoritative product assembly prepare helper.
This is a low-cost partial optimization hypothesis and not measured CPU improvement. All formal product and extreme A/B results remain NOT_RUN; no test dispatch until entire batch source frozen. Prior S1/S2 feature-impact blocks remain archived as JSON factual records of their source commits, not falsely reasserted as current diff.
```json
{"kind":"updated","ids":["fec-fixed"],"reason":"Experimental Windows FEC native DLL lookup and parity buffer reuse optimization, no new config/default or claimed CPU/product qualification."}
```

## Windows extreme remediation S4 (C2 repair absolute safety caps, v3 RTT cache)
Reviewed wbd_recovery::budget v3 epoch credit (9% of definitely M4-accepted fresh) and GlobalRepairAllocator hard cap. Original Windows hard limits 65,536B/s per direction and 131,072B/s process could not support 50M/30% or dual 500M lines irrespective of proportional policy; 32KiB grant was also only one safety cap, NOT itself a periodic 50ms rate. Updated max direction7MB/s, process14MB/s, per grant262144B and outstanding reservation pool524288B/256. All percentage shares and actual accepted send accounting remain unchanged. Shadow uses already-enabled adaptive RTT-derived expiry capped by shared R2 logic, no unconditional 2s payload retention.
These are safety envelopes, not startup allocation, guaranteed throughput or performance PASS. FEC/Go product and high-load matrix remain NOT_RUN; C3 quality memory index, batch FFI and verified effective readback still OPEN.
```json
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Experimental Windows v3 repair absolute process/direction caps above intended bidirectional workload, retaining all relative firstsend and per-origin correctness limits; no product PASS."}
```

## Windows extreme remediation S5 (C3 maturity debt / constant-cost indexes)
Re-read current MatureFirstSend firstsend/check_clock, deadline on_due and Windows original FEC2 drain/readback hot path. Replaced two per-data BTreeSet time indexes with FIFO VecDeque ordered by genuine monotonic firstsend time; PN lookup still BTreeMap (no sampling of denominator). Original Windows deadline drain now bounded to 256 events or 200us per owner call instead of drain-until-empty under Entry lock; native Go requests due at most every 2ms fair pulse, not 100ms. Rust owner max quality live entries raised to 524288 lazily, no 8s payload caching. Existing 64-per-call M2 deadline API and 512 firstsend threshold unchanged; actual service rate/capacity and natural Auto remain NOT_RUN pending full candidate Actions.
```json
{"kind":"updated","ids":["fec-auto"],"reason":"Experimental Windows Auto due service and indexing cost bounded without relaxing mature firstsend denominator or claiming natural dynamic Applied PASS."}
```

## Windows extreme remediation S6 (A4/D Game real copy accounting and fail isolation)
Reviewed actual GameAdapter::inner_mtu, original independently protected lane TCP MSS, WinGameGroup bound Wintun path_mtu, Rust stage/drain and native NPF callback flow, and latest shared GameFEC M4 receipt code. Original code capped all Windows Game modes at 1200B and treated off Game packet transfer to Go stage callback as if kernel-copied; Game local send error and one FIN/RST killed entire 2/4-lane group.
Current isolated fix: private wbd_m0_win_owner_v4_game_effective_mtu is measured from TLS MSS, existing owned Wintun path MTU and actual 1536 wire ABI, reserving 31 record +16 Game and optional 14 FEC bytes. Go reads exact Rust effective MTU once after all joined/qualified lanes, sizes packet ring and open/stage validation; Rust test now includes legitimate 1300B IPv4 and insists actual Wintun set_path_mtu before group join. For FEC-feature product binary both Game/off and Game fixed now STAGE ciphertext without pretending Go array accepted it; every real NPF success/failure settles a unique Rust staged ticket; original per-lane FEC copied count only on real success. First failed/FIN lane is retired locally without blocking healthy siblings, and all-lane loss stops group. Startup positive still requires actual send >=2 on each lane, not just global count. Added scoped failed-copy/healthy follow-on Rust and native Go unit checks.
Remaining: currently one effective MTU snapshot per live group, not true dynamic mid-session path MTU rotation; Game FEC Wintun batch still all-copied or not (partial prefix not implemented), ETW/performance not measured. This partial is NOT a completed package and no product Actions were run.
```json
{"kind":"updated","ids":["game-lanes","path-mtu-budget","game-fixed-fec"],"reason":"Experimental Windows Game payload budget from trusted shared Rust readback and per-lane actual NPF outcomes / local failure isolation; no complete public or extreme-network PASS."}
```

## Windows extreme remediation S7 (TX evidence and Auto capacity non-HOL)
Re-read exact 9d2362d failing source M2 control TX mismatch expected2744012027 got2744012455 and original m2_next_feedback_entry. The specific preseal output-buffer guard already existed in failed SOURCE; do not relabel as root fix. Added original Go single send-owner bounded last64 TX metadata events (source/control/parity PN, SEQ, expected, wire size, monotonic elapsed, actual NPF result) and strict mismatch error context, with no ciphertext, payload, identity or keys. This is a diagnostic to distinguish staged/burned owner sequence from actual kernel-copy completion; original mismatch still hard FAIL. Fixed maturity observer capacity path to count capacity-censored without killing *already successful* genuine M4 firstsend; other authorization/clock/state errors fail closed. No natural Auto policy change. Added isolated Go unit audit bound check, exact Go manifest pending in this same S commit.

```json
{"kind":"updated","ids":["fec-auto"],"reason":"Experimental bounded original Windows TX sequence trace plus independent capacity-limited quality observation; no downgrade of mismatch hard gate or product PASS."}
```

## Windows extreme remediation S8 (E mode evidence and no mixed-scenario performance)
Recovered the old source6d Action40483279255 final FAIL and exact audit in merged PR32; original mode-batch.json and fixed/game mode reports existed during run but the workflow uploaded only normal-report and report. Preserved the *first failure* and independent 1Hz Windows Go-process-with-Rust-DLL resource JSONL, UDP/TCP app logs and native link witness into allowlisted per-mode artifacts under mode-results/<mode>/, with SECRET argument and JSON-field redaction. Explicitly NO copied TLS keys, launch scripts, IP/route key, WAL credentials or private config. New helper/source-scoped unit checks verify redaction, no cross-mode overwrites and missing capture status. Artifact uploader now includes every mode's report and mode-batch, and excludes raw unredacted per-mode logs. Real functional batch remains one compiled artifact reuse; optional WL-N0 measurement requires exactly ONE selected mode per Action.

These are fixture delivery corrections only; no current Windows performance claims, runner platform result or interval-latency measurements. Exact end-to-end SOURCE native run is still NOT_RUN.
```json
{"kind":"none","ids":[],"reason":"Mode artifact/monitoring and upload-only changes; no product selector/default/qualification or public feature changed."}
```

## Windows extreme remediation S9 (B1 authentic M4 Wintun lease, not forged OS identity)
Reviewed original Go private owner bridge, windowsownerlease.CreatedWintun.HoldCurrentNative (validates current NativeIdentity/IP Helper and M4 reservation Hold), exact TLS/generation fenced v4WindowsRealDeviceLease and quiesceAndStopRustOnly ordering. The original lease pins an authentic native adapter throughout the session; B1 adds RW in-flight borrow guard rather than inventing a device token. Owned Stop takes write lock, drains active calls and revokes before hold release. Per-packet Normal/Fixed/Auto/FEC/Game use guarded session borrow through actual Rust FFI, while establishment/bind, protected reconfiguration and Stop retain full OS validation. A roughly 1Hz OS audit invalidates the session on external identity changes; original driver errors remain fatal. Rust generation/device and Game lane assertions stay active. Unit test covers in-flight borrowing vs revocation and no per-packet syscall for the pinned adapter. Existing prepare_windows_wiring.py list includes the test.

This is an optimization hypothesis, not measured CPU/GUI/physical product PASS; no stand-alone native Actions before full source freeze.

```json
{"kind":"updated","ids":["windows-native-transport"],"reason":"Experimental authentic Win32 verified Wintun session lease borrowing for Rust FFI; native/runtime/CPU still unverified."}
```

## Windows extreme remediation S10 (Game FEC real Wintun completed-prefix accounting)
Reviewed shared GameReceiveOwner PreparedGameFecBatch (one authentic Game symbol can produce multiple recovered IPv4 frames), original rust finish_fec_group, Go native ring WriteAuthenticatedIPv4 loop and bridge ABI. The former allCopied bool suppressed the fact that some earlier frames had already reached Wintun when a later write failed. Replaced ABI with validated exact prefix count bounded by real staged output length; invalid oversized counts cannot consume pending batch state, a partial result cannot commit full Game logical first delivery, and the Go native per-mode receipt counts only genuinely copied IPv4 prefix before failing closed. Preserve AEAD/replay, generation, Stop, original multi-lane dependency isolation. Rust scoped negative tests cover valid 0/partial/full/oversized prefixes; prior zero-copy and full-copy unit paths updated. Actual loss/recovery and p99 remain NOT_RUN.

This is exact completion accounting, not an implementation of suffix requeue; on partial Wintun failure the worker still exits explicitly rather than rerunning already copied frames. Future resume would require new authenticated staged suffix contract; do not fake it as done.
```feature-impact
{"kind":"updated","ids":["game-fixed-fec"],"reason":"Experimental Windows GameFEC Wintun multiple-frame completion now uses exact authenticated successful prefix, prevents all-or-nothing false accounting; no formal product pass."}
```
