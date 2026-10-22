# PLAN021 — Actions-qualified test-channel modes and next network-condition cases

Applies to task `R0-M0-PLAN008-PRODUCT-VERTICAL-INTEGRATION-025`. 2026-10-21 user G3 override: positive functional GitHub Actions on the **same source/binary/feature** opens the entry for actual network-condition trials. Entire physical/production/performance matrix no longer blocks opening. This is the test-channel execution ledger, **not** a new release/production certification.

## Current candidate function selectors and claim boundary

| Runtime / feature | Public selectable path | Evidence before PLAN021 source run | Test-channel disposition |
|---|---|---|---|
| Windows original-Go Rust V4 Normal/off, one lane | `--native-v4-product` explicit operator selection, pinned signed Wintun / original credentials | Windows2022 `39618823911/1` PASS_SCOPED original TLS/Rust M3 actual signed Wintun UDP both directions, native lease/MTU/DNS WAL; isolated real TEST-NET persistent WFP Arm/foreign CAS/Stop; full /1 and true public OS transaction NOT_RUN | `TRIAL_CANDIDATE`; opens `OPEN_FOR_NETWORK_TEST` **after** PLAN021 changed-source native Action+Governance SUCCESS; WFP/real routes can fail during actual first full attempt and then must be reported as FAIL/UNSUPPORTED |
| Windows WinForms native client | Real compiled WBD.exe and original tagged V4 child; UI only trusts genuine OS Applied/Disconnected receipt | `39618823911/1` compiled GUI fake-child state PASS, genuine OS path NOT_RUN | Expose UI test entry with source-locked portable binary when supported; do not say OS GUI Applied PASS without the real child running and OS receipt |
| Linux original-Go V4 Normal/off | Original credential Go TLS + Rust native TUN owner | Prior source-locked Linux scoped Actions | Test by same qualified source/binary; physical and weaknet separate |
| Linux original-Go V4 Fixed/Auto initial | Authenticated FEC2 M2 original Go CLI + Rust kernel path | `39397459128` positive **initial** Fixed and Auto real public app 64 each direction, stop; no loss/dynamic Auto later revision NOT_RUN | Eligible for mode-specific network trials using its tested V4 binary; re-run under loss/long-duration using explicit source |
| Linux original-Go V4 Game2/4 public | Requires one real credential session with 2/4 authenticated independent M4 lanes and public CLI selector | `39397459128` Game2/4 NEGATIVE unwired; private Game kernel PASS alone is not public | `EXPOSED_NOT_WIRED` until its own positive public V4 Actions; do not equate legacy Go V3 Game PASS with V4 |
| Original-Go legacy V3 Fixed/Auto/Game2/4 | Existing V3 CLI (not V4) | `39373130689` real public modes PASS, some scenarios netem; distinct source/protocol | Testable independently as legacy V3, labeled V3, never counted as V4 |
| Windows V4 Fixed/Auto/Game2/4 | Needs Windows original-Go native multi-lane/FEC2 owner and public GUI selector | NOT_RUN/NOT_WIRED on Windows | `EXPOSED_NOT_WIRED` (not secretly OFF by the old qualification-before-trials policy; a real missing implementation still must be built and tested before it can work) |

## Network-condition campaigns after the trial admission is qualified

Use source-locked binary and complete run/attempt/job and artifact SHA; each functional scenario may include a cheap boundary batch, each performance Action exactly one configuration/seed/VM. Capture *actual* inputs and output, don't infer them.

1. Windows Normal/off first: real WFP IPv6/DNS rules, two `/1` + physical underlay route and server escape, independently confirm no IPv6 leak, original credential TLS/Rust Wintun UDP both directions; 1x Connect / Stop / reconnect, foreign/stale WAL CAS rejection, forced crash recovery; real WinForms Applied and Disconnected strings only after full OS readback. Do not install host-global policy on a shared hosted runner; use operator-controlled dedicated network environment.
2. Network conditions: no loss, IID1%/5%, RTT10/150/300/600ms, reordering, burst loss, sparse payload, 64/256/1200/inner-MTU±1, actual legal large UDP/TCP; 80s outage and reconnect; report source, topology, drop counters and actual first-delivery.
3. FEC2: Normal off/fixed/auto, every fixed profile, Auto ordinary/aggressive on real authenticated owner, initial and second revision; source/repair/parity counters and decode/Stop under packet loss; reject unknown/foreign unauthenticated receipts.
4. Game2/4: distinct authenticated lane owners, independent/fully correlated lane loss, lane1 stalls vs later logical packet, first-delivery non-HOL, native Stop/stale rejection; separate V3 vs V4 binaries.
5. Resource and correctness: 10→50→100→200→500Mbps only within observed host capacity, stable CPU-s/RSS/queue age and real p99 probes; unsupported host/lab `UNSUPPORTED`, missing run `NOT_RUN`, failure `FAIL`, no projected estimates as PASS.

## Truthful reporting

One exact CI **function PASS is the admission**, not the complete condition matrix. `OPEN_FOR_NETWORK_TEST` means manual invocation is allowed, **not** network device changed, GUI Applied, production auto-enabled or all modes passed. Keep credential security, original Go TLS/Rust AEAD, protected receipt, owner lease and generation, exact WFP/route/MTU/DNS WAL, foreign CAS, cancellation and Stop. No debug flag may force success/skip OS readback. Preserve all old failures including the S662 Windows old GUI assertion FAIL and legacy G2 rev2 bootstrap FAIL.
