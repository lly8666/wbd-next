# Selective TLS ciphertext reuse — isolated lab conclusion (2026-10-24)

## Decision / qualification

**Scoped negative experiment: IDEAL_RECORD_CPU_BENEFIT_WITH_CONFIRMED_LAB_APPEARANCE_REGRESSION. NOT MERGE READY.** On native hosted ARM64 with a real generated TLS 1.3 ciphertext corpus and a trusted ideal test oracle, selectively authenticating an unchanged suffix reduced the *complete record seal+open CPU* by **29.4732%** compared with existing full-AEAD record. An initial bounded native Linux loopback TCP trace confirmed repeated ciphertext across distinct outer TCP sequence positions under a constructed duplicate inner packet. Crucially, a later independent netns/veth ACK-loss Action also captured **real Linux kernel inner TCP retransmission** (207.223ms apart with identical inner Seq and TLS ciphertext) and then captured the same 64B/128B body in **two distinct new outer TCP Seq positions**. This conclusively demonstrates the candidate wire's repeated-body appearance vulnerability in an isolated lab, still not a real Go/TUN product run. Neither full product packet delivery nor actual bootstrap handshake has been measured.

CPU gain is **not sufficient for product suitability** because of this appearance leak; no padding, ciphertext-identity cache or whole-payload disguise was invented to produce an appearance PASS. Do not integrate this experimental wire into main, production default, CLI or device builds.

## Scope, frozen inputs and immutable artifacts

- Branch: `experiment/selective-tls-crypto`; first checked remote HEAD `b94098c342552113ca136a178768f7f58bc433fd` after design work. Frozen inherited base `34985d2df47ad9c08ce0828554241515a5704266`, network ancestor `040741820b2f917b5868c285c438d4cc21c6193a`; independent of network/FEC task cursors.
- Bench/codec SOURCE: `98e5b09b972196b97476b4311346cb79681773c5`, locked `aws-lc-rs=1.18.1`; `wbd-codec` default-off Cargo feature `selective-crypto-experiment`; current production `record_crypto.rs` unchanged. Lab codec is not product/Go cold admission.
- Existing A 31B/full AEAD, A-layout 33B/full AEAD, B 33B/selective after ideal TLS oracle. One AEAD per packet, continuous AAD including B, encrypted metadata kind/H/marker, 10B descriptor+PN header protection, no explicit wire mode visible before auth, 512B B minimum, 256B H cap, full fallback. FULL uses 33B even when B not eligible. No classifier heuristic/DPI/TCP reassembly.
- S0 native ARM64 release Actions **run [40108785993](https://github.com/lly8666/wbd-next/actions/runs/40108785993)** attempt 1 job `120915933711`: SUCCESS 157 passed, 0 failed, 1 ignored; artifact `12565812441`, artifact ZIP SHA-256 `19043c73f18ce01664c0c7add48669965b2258fb31dae188a9dc2c2337acbead`. Frozen benchmark ELF SHA-256 `9b18cd5c9c60820146655d0df4b0111e2f51d38fd3712acffbc1edb7a600d735`. Existing unrelated FEC pressure test ran ~710.61s in that functional workflow, not part of performance metric.
- S1 ARM64/AES128 same-VM single performance job [40109817134](https://github.com/lly8666/wbd-next/actions/runs/40109817134) attempt 1 job `120918993965`: exact binary downloaded and verified, real TLS 1.3 encrypted record generated via ephemeral in-job SSL MemoryBIO, actual client decrypt checked. Analysis artifact `12565174759`, ZIP SHA-256 `49082dd9e512d5f1285534d84a7272ed528b70b1a9b4572f0f1e752a44f0ffd5`. Raw record/cert/key not uploaded.
- Bounded separate capture [40109989226](https://github.com/lly8666/wbd-next/actions/runs/40109989226), artifact `12566246128`, ZIP SHA-256 `991d18fda3c1c9df6a17e36fd57c5fd9d97341563a19ece6b31ddcf45bead592`; native x86_64 loopback TCP, four records, controlled duplicate inner Seq fixture, not Go/raw/TUN.
- Independent native x86_64 representative S0 [40109345476](https://github.com/lly8666/wbd-next/actions/runs/40109345476) attempt 1 job `120917611078` **PASS**: 157 passed, 0 failed, 1 ignored (same frozen 98e5 codec SOURCE); artifact `12565888233`, ZIP SHA-256 `a61779add3bc8c6d8522dda645f0ef522b969babb998ba932f5b3b6d92bc9cb9`. This is native functional cross-check, *not* x86 record CPU profiling.
- The generated test corpus and application data were not committed. Owned raw capture/temp TLS cert/key cleaned by trap.

## Actual S1 record-only measurements

One scenario: native GitHub-hosted ARM64, AES-128-GCM, single TLS ciphertext suffix of 1300B inside 1345B candidate inner IPv4/TCP packet, no FEC, no outer repair (not applicable to standalone record tool). Each leg warms 2s and measures 15s, order frozen `A → A-layout → B → B → A-layout → A` within **same job/VM and same native binary**. Record seal/open, HP, allocation of no extra record in the hot loop, prefix rearrangement and output copy are included. The genuine TLS ciphertext was created and decrypted successfully outside timed loops; classifier lookup is a zero-cost ideal oracle descriptor. The RFC authenticity of TLS record cannot make plaintext classifier on arbitrary real TCP traffic free.

| Metric | A legacy | A-layout all FULL | B selective |
|---|---:|---:|---:|
| CPU ns / inner byte (pair mean) | 0.7752137366 | 0.8053942386 | 0.5467331362 |
| Estimated CPU s / GiB of offered inner bytes, based solely on same record benchmark | 0.832379 | 0.864787 | 0.587050 |
| Wire bytes / 1345B inner packet | 1376 | 1378 | 1378 |
| A forward/backward percent variation | 0.067236% | — | — |
| B savings vs A | — | — | **29.473239%** |
| B savings vs A-layout | — | — | **32.116086%** |
| A-layout overhead vs A | — | **+3.893185%** | — |

Measured RSS reported 1964KiB in each of six process legs, not an isolated extra-workspace allocation upper bound (the corpus and tool setup are separate from production). `copy_bytes_per_packet_tx_rx` was reported as 2690 for all legs based on modeled per-round transfer count; it was **not independently instrumented** and cannot prove zero-copy or exact copies at the driver. Native ISA/scalar backend was not independently included in S1 numerical output; preserve build host manifest/flags for inspection. No per-cycle counter observation; use measured CPU ns, do not infer cycles.

The bench reads a bounded reused input corpus; repeating identical plaintext/ciphertext in a timed microbenchmark **does not constitute a real appearance trace**. The separate S3 fixture generated distinct output PN/outer positions and genuine TLS record bytes.

**Net product CPU fraction, realistic oracle lookup/reconstruction, p99/real first delivery, memory in a running client and queue/drop figures remain NOT_OBSERVED**. An upper-bound oracle result cannot be advertised as a 29.47% whole-tunnel saving. It is valid evidence of the best-case record primitive savings.

## S0 correctness scope and unresolved gates

Native ARM64 feature tests passed: AES-128-GCM, AES-256-GCM, ChaCha20-Poly1305; FULL/SELECTIVE and insufficient B fallback; MTUs 1500/1400/1280 (record budget), kind/head/descriptor/B/tag tamper rejects, wrong key rejects, out-of-order authenticated records without a crypto-layer replay claim, failed PN consumption, frozen record clone byte-exact. The explicit record decode returns after AEAD, does not admit a product replay window and does not grant direction/generation capability.

Untested **product hard gates**: authenticated Go bootstrap both-end version negotiation and actual exporter key domain, real replay+generation admission and owner state, Stop cleanup, raw/TUN first-delivery no HOL, real Go/TUN product-path TCP retransmission, real outer repair frozen re-sends, actual MTU with OS options, host queue/drop/p99, production default via config/CLI/GUI, Android/Windows native. S0 component success is NOT product PASS; no public network experiment admission for this new format.

The x86_64 S0 job completed as a representative native component functional PASS, not same-machine ARM64 cost replication. No CPU comparison across VMs has been made.

## S3 bounded capture evidence / explicit distinction

Independent capture Action used real Linux loopback TCP and `tcpdump -i lo` on the wire; fixed inner TCP Seq and identical already-TLS-encrypted body were submitted twice to the lab record builder with **different outer PNs**. The analyzer reconstructs the outer TCP stream, deduplicates identical TCP Seq retransmitted segments, confirms whole TLSlike record boundaries, and checks candidate 64/128B equality across distinct outer TCP Seq positions. This is a **deliberately controlled inner-retransmission mimic**, not an inner kernel retransmission observed in netns/TUN.

- 4 captured records, two A FULL wire 1376B, two B SELECTIVE wire 1378B; 4 TCP payload segments, 0 same-outer-Seq duplicate segments.
- B occurrences in **different outer Seq** positions: same continuous ciphertext at both 64B and 128B. The FULL control encrypted blocks differ.
- An inner IP header-address canary was **not** found in visible outer stream in this small trace.
- Raw pcap 6196B; SHA-256 `42907dd45a18d5ccc08b3598417c5e9e320d6ad6395e67fc357e335177de1750`. Only digest/summary/hashes retained; raw owned files cleaned.
- This is a definite leakage mechanism and a negative appearance outcome for the *candidate wire under valid repeated input*. It is **not** a claim that arbitrary real traffic is always distinguishable, not a classifier, and does not prove real TLS-like handshake behavior either way.
- Test reference HTTPS outer handshake, packet-timing statistics, retransmission from actual kernel, and simultaneous business p99 have not been measured. Keep as NOT_RUN, not falsely PASS.

## S3 follow-up: actual kernel-produced inner TCP retransmission in owned netns

To distinguish a constructed same-inner-Seq test packet from actual Linux TCP behavior, a second single-purpose Actions capture used two owned netns and veth interfaces, real TLS 1.3 application ciphertext generated/decrypted by a local TLS session, and a one-direction 100% ACK-loss qdisc **after the TCP handshake**. The kernel autonomously retransmitted the same TCP-sequence data. The analyzer demanded two independent capture events with equal Seq/TLS payload and **at least 100ms packet time separation** (no per-capture synthesize step).

- Original native-kernel capture [40110713400](https://github.com/lly8666/wbd-next/actions/runs/40110713400) succeeded, but its inherited outer analyzer mislabeled the source as manually repeated. That wrong summary metadata is preserved as a defect/intent rather than quietly erased. Original artifact `12566642021`, ZIP SHA `6174cac7040b5698bc7357e29ae4cb80fe0d98dd3c00ce4e99b5aebdd96d6fe9`.
- Minimal evidence-source/packet-time guard fix (no change to frozen codec or loss seed) verified in [40110917872](https://github.com/lly8666/wbd-next/actions/runs/40110917872), attempt1 job `120922265170`, **SUCCESS**. Artifact `12566463062`, ZIP SHA-256 `0dc786ab6c0bf532497001ad1dfc30fc5db70b7f856ed8cb79b437d75d6803a6`.
- Actual captured same inner TCP Seq `140851678`, payload repeat time gap **207.223ms** against 100ms minimum, B TLS ciphertext suffix **1317B** repeated. Inner pcap 9852B, SHA-256 `e651e9d84c6275fb16b32bdccf4e7ba3d201c0d40f2e548a671072127827ff56`.
- Original authenticated FULL A for the two actual inner packets and SELECTIVE B for those same original inner packets were separately sealed under new outer PNs and passed through a local Linux TCP loopback socket. Native outer pcap reconstructed whole 4-record stream and confirmed 64B and 128B equality of the selective ciphertext body at *different outer TCP Seq offsets*. Outer pcap SHA-256 `40852aeff4e2ba938f3a77df13503cbc81c790bed6950b7c12204579a524ebc9`.
- Corrected classification: `CAPTURED_TIMED_NATIVE_LINUX_NETNS_TCP_RETRANSMISSION_NOT_TUN_PRODUCT`. This is genuine inner TCP kernel retransmission in an **isolated test fixture**, but still NOT an original authenticated Go→Rust raw/TUN full-tunnel session. It proves a concrete, reproducible candidate record appearance leak, not universal network traffic detectability.
- Owned raw inner/outer pcaps, TLS keys/corpus and transient packet pair were deleted on Action cleanup. Only hashes/structured metadata and tool binary SHA were uploaded.

## Decision and stop

At S1 the ideal record saving is clear (>5%). Both the first controlled replay S3 and the follow-up **real Linux kernel inner retransmission** capture show identical 64/128B TLS ciphertext in distinct new outer TCP Seq positions. Original full AEAD does not expose this repeated interior ciphertext. Under the predeclared appearance hard gate, this is enough for a **negative feasibility finding** and avoiding any expensive 50/500M real-driver/capacity suite or universal reclassifier. Host/product bottleneck limits are **NOT_MEASURED**, not HOST_CAPACITY_LIMITED; S2 workload is intentionally not executed because the candidate already violates the experiment's appearance criterion in bounded negative control.

Do not deploy, merge into main, change default, or present the experiment as a new cipher security qualification. Production keeps original fully encrypted record unchanged; no user content or bulk trace stored. A future architecture would need a fresh cost/security experiment, not reuse this one as a PASS.

## Recovery / consistency record

- S/H facts and all run IDs live only in `docs/evidence/selective-crypto-work/status.json`; no network/FEC status/next_action executed.
- The branch was advanced only via authenticated GitHub Contents API because this session had no mounted repository checkout. Remote reference plus changed files and Action SOURCE were inspected; **local git status cannot be claimed clean**.
- This report intentionally notes deferred real-path evidence as NOT_RUN and preserves all observed positives/negatives without seed rotation.
