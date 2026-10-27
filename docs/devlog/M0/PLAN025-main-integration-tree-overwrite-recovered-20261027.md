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
```json
{"kind":"updated","ids":["game-fixed-fec"],"reason":"Experimental Windows GameFEC Wintun multiple-frame completion now uses exact authenticated successful prefix, prevents all-or-nothing false accounting; no formal product pass."}
```

## Windows extreme remediation S11 (C3/C4 real readback and recoverable unknown cohorts)
Reviewed source original M2 kernel firstsend, R2 RxFeedbackState dirty page history, MatureFirstSend 2s/8s metadata, Windows Fixed revision replacement constructor and cold Rust-to-Go business MTU. C4 increases authentic reverse receipt history from 512 to 1024 bounded 256-PN pages while retaining 8 dirty pages per feedback. Rev-changing native FEC formerly reset 524288 cap back to 131072; now both use 524288 metadata, not payload. Capacity-only observer errors count unknown but never kill successful DATA; a historical capacity incident persists cumulatively for strict original Go Auto cohort windows yet affects Fixed mature eligibility for only the last 8s. Permanent actual internal/auth failures stay fail-closed. New deterministic Rust tests cover capacity 8s boundary and exact live M2 ABI receipt/path bounds.
New v9 original Rust M2 effective FFI returns actual bound path/business MTU, optional repair shadows, feedback pages, mature metadata cap, opportunistic enabled and confirmed fresh/repair quota and shared process cap/pending bytes. The Go same-epoch Wintun lease wrapper rejects wrong/short/unauthorized readback; after arm original-Go checks real Rust business MTU against true native cold buffer, then 1Hz original business telemetry refreshes owner-based actual credits and memory. Go ABI size negative/default check and authoritative assembly and Go blob manifest updated.
No claims for actual Windows product or high-rate CPU/performance: this is isolated source-stage before whole batch freeze; B2 cross-FFI batch, dynamic mid-session MTU, final matrix remain OPEN.
```json
{"kind":"updated","ids":["fec-auto","outer-opportunistic-repair","path-mtu-budget"],"reason":"Experimental genuine native M2 effective MTU/credit/quality readback, 1024 bounded receipt pages and recoverable 8s capacity-unknown cohorts; no new Windows native/performance PASS."}
```

## S12 (A1 original M1/M2 hot-path clock coherence; historical TX fail remains)
Before patch: re-read exact active Rust v3_seal_entry, v5_open_record_entry, Windows FEC seal_symbol_entry, m2_next_feedback_entry and true original-Go NPF completion with S7 last64 metadata. Fresh Normal/Fixed source paths called M1 at MonoNs(0) even after original M2 due control sealed with m2_clock(). Change TX seal and its drain to use one m2_clock() snapshot, and Normal RX offer/drain similarly, without modifying replay, PN, carrier sequence, ACK, private device/generation guard or stop. Add a deterministic original source→authenticated M2 feedback→source test that ensures contiguous Rust TX sequence and non-reversed logical time.
This is a root-cause hypothesis for observed Normal seal rejection, NOT PROOF that natural Auto 428B gap is fixed. No product Actions dispatched before complete freeze.
```json
{"kind":"updated","ids":["normal-off","fec-fixed"],"reason":"Source-locked experimental Windows original M1 time continuity across DATA/parity/control TX and RX, with explicit interleaving unit test; still no native product PASS."}
```

## S13 — source-locked R2 receipt regressions brought to current v3 one-opportunity contract
Recovered exact original Action40483279229 source6d35857 receipt job122119010582: 7 PASS, 4 FAIL. Every failing assertion expected shadow.outstanding() 1 but actual 0 after a terminal repair. Re-read current wbd-recovery/receipt.rs on_send_result: Accepted, Uncertain and NotSent each remove the single optional shadow after real driver disposition; repeat must be stale. Updated only those four historical tests with new equal-strength assertions: no second PN0 repair, immutable exact ciphertext, real accepted F credit, definite NotSent refund, Uncertain still charged, no duplicate socket send, correct independent authentic new PN1 after old NotSent, distinct tunnels and clean Arena reclamation. No shared production repair policy changed or historical FAIL erased. Execution remains NOT_RUN until whole candidate SOURCE freeze.
```json
{"kind":"none","ids":[],"reason":"Historical native receipt assertion fixtures updated to shared v3 terminal one-opportunity accounting; no product code or public feature change."}
```


## S14 — original Rust M1/FEC2 sequence interleave protection
Re-read the current FixedStream source/poll and original m2_next_feedback_entry (real m2_clock), stage_fixed_parity_entry callback and settled immutable output. Added a same-epoch deterministic interleave of 16 actual FEC source seals with truthful original M2 firstsend, authenticated-data-scoped reverse control, completion, then due FEC parity. Every emitted SEQ must equal the prior accepted descriptor end and every PN is nonduplicated. The historical 9d natural Auto 428B mismatch remains FAIL until exact native Actions after the full batch, and this does not conceal burned/incomplete packets by advancing Go expectations.
```json
{"kind":"none","ids":[],"reason":"Additional deterministic source/control/parity sequence order protection for existing experimental A1 clock fix, no product default or formal qualification change."}
```

## S15 — original Windows NPF completion batch across FFI (NOT_RUN)
Read current Windows M0 original NPF pulse and ReportOriginalM2NpcapFirstsend, original M1/M2 rust owner, bounded Go original Wintun lease. Up to 4 source records per fair <=2ms turn are sent through genuine original NPF then reported as one <=32 descriptor firstsend completion ABI. Rust v10 validates all PN, contiguous SEQ, original immutable M1 ciphertext lengths, epoch/LUID/index and nonduplicated metadata BEFORE consuming pending records. Rust 0=definitely NotSent, 1=accepted kernel copy, 2=uncertain driver error; the Go failing syscall uses Uncertain and still fails closed. Correct previous single ABI remains for exact old callers. A batch error fences owner; no hidden automatic re-report or invented peer delivery. M2 feedback/peer auth sees completed results before RX dispatch.
Still pending build/test source freeze: Rust global accounting currently per row inside one Rust Entry lock; TX source seal across FFI remains per record. This is a real boundary optimization candidate, NOT a measured throughput/p99 result or natural Auto root-cause closure.
```json
{"kind":"updated","ids":["windows-native-transport","outer-opportunistic-repair"],"reason":"Experimental typed original NPF firstsend completion batch FFI, authentic Rust PN/SEQ and uncertain error handling; no formal product qualification."}
```

## S16 — preflight atomicity and native copied-prefix ABI tests (not yet run)
Completed the batch status return to report exactly how many already accepted firstsend rows were settled, even on a terminal internal error, instead of claiming that an actual prefix was zero. Rust batch fixture first verifies bad duplicate/stale/noncontiguous PN/SEQ rejects with both real M1 pending records untouched; then validates Accepted PN0/Uncertain PN1 accounts exactly one optional immutable repair shadow and burns both PN without fabricated fresh credit; replay of same metadata is rejected. Go original DLL ABI exact C 24B size/offsets and bounded max32, and error-path original-Go firstsend descriptors may never be submitted twice. Updated original Go assembly manifest for both tests; no native test dispatch before whole batch SOURCE freeze.
```json
{"kind":"none","ids":[],"reason":"Native Rust/Go batch firstsend source-locked negative and layout regression tests plus exact existing assembly manifest; no public selector/feature promotion."}
```


## S17 — native Windows Normal/FEC2 open typed fatal-status boundary (isolated pre-freeze)
Before edit re-read original v5_open_record_entry, rust v3_ready, actual M4 borrowHot, Go scopedclient opener, and Native winOwnerCall. Previously all original Normal/FEC2 Rust open errors became a simple bad-packet count, so a real BAD_STAGE, FULL, retired handle, or unreleased Stop was hidden as loss. Preserve Rust exact C ABI 1=INVALID (ambiguous crypto/replay/packet) as the existing native rejection, but all other C ABI statuses and untyped missing native session errors now terminate owner with the original exception intact, not fake network loss. The shared Rust v3_ready epoch/device/generation and authenticated Wintun lease remain mandatory on every open. Add source-locked Windows typed ABI error unwrap/return-code test; do not synthesize a packet or change replay acceptance. INVALID remains ambiguous until Rust per-cause typing is added and a real native test runs.
 
```json
{"kind":"updated","ids":["windows-native-transport","normal-off","fec-fixed"],"reason":"Experimental Windows original M1/M3 native error provenance separates fatal owner/arena/state failures from packet-invalid return; preserves existing authentication/replay hard gates and DOES NOT claim an Actions product PASS."}
```


## S18 — one authentic M4 lease and Rust v3_ready instead of hot redundant readbacks
Read v4WindowsRealDeviceLease.borrowHot and Windows Rust v3_ready, original Normal seal / kind1 open / M2 reverse feedback, and Windows Fixed/Auto FEC source/open wrappers. M4 native created-Wintun session keeps authentic generation and Stop RW-lock with periodic real OS identity audit. Rust seal/open/due C ABI takes same epoch/LUID/ifindex and checks PH_ACTIVE/nonquiesced device under owner Entry mutex. Removed only duplicate two extra owner-state FFIs per hot call, retaining original borrowHot and Rust validation, M1/M2/M3, AEAD/replay and copy/Stop semantics. Setup, M2 arm, WFP/WAL and protected reconfiguration still do strong readbacks. This is an unmeasured CPU-cost change, NOT_RUN native and perf. No source-level performance qualification.
```json
{"kind":"updated","ids":["windows-native-transport"],"reason":"Experimental native Windows hot-owner redundant state FFI elimination, authentic current M4 lease and exact Rust v3_ready still mandatory, no claimed native product or CPU PASS."}
```


## S19 — receipt fixture true ready-prefix prerequisite, no fake fresh credit
Reviewed the post-v3 corrected S13 R2 original receipt test against wbd-platform::r1::submit_ready and actual native callback semantics. The test previously credited a distinct second M1 PN's fresh confirmed bytes without first proving any M4 sink accepted that PN. Both PN0 and PN1 now explicitly pass through the bounded ready-only test sink and assert exact byte-equal accepted_prefix=1 before budget.on_fresh_accepted. The first NotSent and second Uncertain *repair* results still earn zero fresh credit, return/charge appropriately, and retain all no-retry and immutable cipher assertions. This is a unit receiver/driver mock, not real Npcap or a new product PASS.
```json
{"kind":"none","ids":[],"reason":"Ensure each synthetic R2 native ready-prefix fixture proves actual accepted driver-shaped initial copy before granting F; no product source or policy change."}
```

## S20 — source-locked per-mode evidence boundary (draft, not product PASS)
Previous sequential seven-mode runner could re-archive a stale prior-mode log because all modes share result/wl-public. Added pre-mode shared-file snapshot and changed-file copying; always-on original Linux raw/WSL witness, Windows NPF witness and native Go+Rust process telemetry are sliced only after the new mode begins when append-only, while truncated/replaced logs are captured entirely. Unmodified stale log is not relabeled and is explicitly listed; no password/keys/scripts are included. Tests preserve first mode original error and prove second mode copied only its new NPF/resource suffix. Original workflow already uploads `mode-results/`, so no redundant runner/checkout job added. All live network/perf qualification NOT_RUN.
```json
{"kind":"none","ids":[],"reason":"Bounded source/mode evidence snapshot and first-error isolation; no product feature/default change."}
```

## S21 — Game4 original Windows native staggered copy staging and due poll
Checked existing Linux GameAdapter::offer/stage_for_windows_native and Game4 4/20/60ms or 4/50/140ms stagger, real MonoNs next_due and original protected M4 copy callbacks. Native Windows previously required exactly all lanes in one offer; legitimate deferred Game4 copies caused BAD_STAGE, while no-FEC group never polled the due owner. Reused existing GameFec parity native due ABI for Game4 off or FEC without creating a parallel Go scheduler; removed all-lanes-immediate assumption while retaining one shared Rust logical source, independent per-lane M3 PN/seal and genuine NPF copy result. Every due copy stays scoped to original TLS joined group and Stop. Game4 test explicitly activates Linux mode2 schedule, requires first partial output, advances unit monotonic clock, checks unique lanes and that exactly remaining copies settle later. Go decoder validates bounded count and nonduplicated lane and owns returned ciphertext bytes. Dynamic configuration effective readback and NAT/TUN actual UX remain open; no performance PASS or new forced stagger mode.
```json
{"kind":"updated","ids":["game-lanes","game-fixed-fec"],"reason":"Experimental Windows Game4 accepts real Linux GameAdapter delayed replica staging/polling, keeps independent per-lane native NPF send results and replay/Stop guarantees. Scoped tests only; no product qualification."}
```


## S22 — precise S20 native witness short-file append regression fix
Latest experimental source943ccd3f Governance Action40512442796 SUCCESS, mandatory maintenance Action40512442792 FAIL 1 of 238: test_shared_previous_mode_log_is_not_laundered_into_new_mode. Recovered exact trace: small original link log was shorter than 256B, so comparing full 256B prefix after append included new bytes, falsely inferred rotation and copied stale previous mode. Compare only original min(256,old_size) prefix while independently comparing old inode/current size; preserve all existing redaction/mode boundary and long-file logic. Added second long-file append fixture. No native Windows/Linux product or performance Actions dispatched; the red run remains historical until new source-governance maintenance receipt.
```json
{"kind":"none","ids":[],"reason":"Restore precise source-locked mode evidence isolation across append to both short and long live witness logs; no product feature change."}
```


## S23 — original Game2/4 effective MTU low-frequency live budget readback
Read original M4 Wintun protected per-lane lease, current Rust game_effective_payload_mtu and current Go Game native ring. Go previously cached a single effective MTU at Bind and retained the same input scratch indefinitely, so a changed owner-path budget would stay stale until Stop. Added 1Hz only original TLS/M4 borrowed Rust group effective native budget query and tightly capped Game2/4 Wintun scratch shrink/grow, explicitly refusing invalid capacities. A malformed/oversize Wintun frame with successful kernel read counts as an explicit local drop instead of killing healthy Game siblings; genuine driver error remains hard failure, no false NPF copy receipt. Added shrink/grow/invalid guard regression. This only synchronizes the Go adapter to an already-updated real Rust budget; end-to-end kernel OS route/MTU event and actual Winsock/WSL changes remain UNWIRED/NOT_RUN. No jumbo or fake Applied.
```json
{"kind":"updated","ids":["game-lanes","path-mtu-budget"],"reason":"Experimental protected 1Hz Game2/4 native Rust effective MTU readback and bounded Wintun scratch/drop behavior, without claiming OS MTU reconfigure or product runtime/performance qualification."}
```


## S24 — B2 original M1 SOURCE seal zero-wait protected four-frame native batch
Read actual original-Go Wintun ReceiveReadyIPv4, Normal v3_seal_entry/Fixed stage_fixed_source_entry, S15 Rust M2 firstsend batch, protected M4 real Wintun session and Stop fences. Windows original source was doing one separate Go→DLL→Rust owner lock for each first-delivery DATA packet even though S15 only batched its NPF results. Added one C ABI v11 typed max4 INPUT/OUTPUT arrays in the original owner; all four IPv4 lengths/inner wire budgets/epoch/M4 identity are preflighted before M1/FixedStream consumes any PN. Each live Wintun packet is copied once into a fixed reused <=4 input array; no wait to fill: if only one packet exists, seal/sync-copy it immediately. Go sends the returned distinct PN/SEQ cipher records sequentially through the same genuine original NPF endpoint, and submits exact accepted/uncertain firstsend prefix to pre-existing v10 M2 callback before reverse peer receipts. A failed stage or post-seal seq discrepancy remains terminal Stop, not a gap skip, fake PN repair, Go retransmission owner or forged ACK/F credit. Reused fixed arrays cut per-source Go ciphertext allocation in active pump. Added Rust C layout (2056/2064B) and actual owner PREVALIDATE-all/strict consecutive-PN-four test, Go layout and fake/cold owner negative tests; exact assembly manifest pins its two registered changed original-Go client files, and the existing authoritative Windows prepare helper still copies the other new named overlays. Existing single-record ABI retained for other authentic protected callers.
This is pre-freeze source only: Windows actual native C/Go production compilation, seven-mode real functional, natural Auto historical 428B mismatch, CPU attribution, one-Action performance and MTU reconfigure remain NOT_RUN. No threshold reduction.
```json
{"kind":"updated","ids":["windows-native-transport","normal-off","fec-fixed"],"reason":"Experimental original Windows Go/Rust source zero-wait bounded 4-record M1/FixedStage FFI with authentic generation/driver completion; no product approval or performance qualification."}
```


## S25 — low-cost Windows same-process CPU vs Go-only allocation and source-stage telemetry
The same-source Windows native original-Go client already emits one 1Hz original Rust M2 effective/readback + NPF ingress native telemetry and the runner separately samples GetProcessTimes/GetProcessMemoryInfo for the WHOLE Windows EXE (including Rust DLL and OS syscall CPU). Added one Go runtime-only MemStats snapshot at the same existing one-second tick with explicit json field labels: heap alloc/objects, malloc count, total GC. This is NOT a Rust heap or Go-only CPU attribution. Added truthful original-source stage 1/2/3/4 actual batch counts, stage failures, and maximum synchronous M2 NPF completion batch observed (not promised throughput). No per-packet OS status, heap or logging added beyond bounded counters; no separate 1ms timer created. Original Go assembly manifest client/test hashes updated. Explicit Windows-only negative stats fixture. One representative short ETW/WPR CPU stack diagnostic is still NOT_RUN; no falsely allocated Go/Rust CPU split or p99 from one-way uncalibrated OS clocks.
```feature-impact
{"kind":"updated","ids":["windows-native-transport"],"reason":"Add bounded original native source/M2 packet batch observability and correctly scoped once-per-second Go-only allocation/GC telemetry; no product performance qualification or runtime policy change."}
```
