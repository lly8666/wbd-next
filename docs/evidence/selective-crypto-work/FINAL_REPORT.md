# Selective TLS ciphertext reuse — isolated lab conclusion (2026-10-24)

## Decision / qualification

**Scoped negative experiment: IDEAL_RECORD_CPU_BENEFIT_WITH_CONFIRMED_LAB_APPEARANCE_REGRESSION. NOT MERGE READY.** On native hosted ARM64 with a real generated TLS 1.3 ciphertext corpus and a trusted ideal test oracle, selectively authenticating an unchanged suffix reduced the *complete record seal+open CPU* by **29.4732%** compared with existing full-AEAD record. A distinct Action performing bounded native Linux loopback TCP capture confirmed that the identical 64/128B ciphertext suffix appears twice in separate outer TCP sequence positions when the same inner TLS ciphertext/inner TCP Seq is resent as a new outer packet. This is an actual trace observation of the architectural vulnerability, but the inner resend was a controlled fixture **not a genuine kernel-induced inner TCP retransmission**. Neither full product packet delivery nor actual bootstrap handshake has been measured.

CPU gain is **not sufficient for product suitability** because of this appearance leak; no padding, ciphertext-identity cache or whole-payload disguise was invented to produce an appearance PASS. Do not integrate this experimental wire into main, production default, CLI or device builds.

## Scope, frozen inputs and immutable artifacts

- Branch: `experiment/selective-tls-crypto`; first checked remote HEAD `b94098c342552113ca136a178768f7f58bc433fd` after design work. Frozen inherited base `34985d2df47ad9c08ce0828554241515a5704266`, network ancestor `040741820b2f917b5868c285c438d4cc21c6193a`; independent of network/FEC task cursors.
- Bench/codec SOURCE: `98e5b09b972196b97476b4311346cb79681773c5`, locked `aws-lc-rs=1.18.1`; `wbd-codec` default-off Cargo feature `selective-crypto-experiment`; current production `record_crypto.rs` unchanged. Lab codec is not product/Go cold admission.
- Existing A 31B/full AEAD, A-layout 33B/full AEAD, B 33B/selective after ideal TLS oracle. One AEAD per packet, continuous AAD including B, encrypted metadata kind/H/marker, 10B descriptor+PN header protection, no explicit wire mode visible before auth, 512B B minimum, 256B H cap, full fallback. FULL uses 33B even when B not eligible. No classifier heuristic/DPI/TCP reassembly.
- S0 native ARM64 release Actions **run [40108785993](https://github.com/lly8666/wbd-next/actions/runs/40108785993)** attempt 1 job `120915933711`: SUCCESS 157 passed, 0 failed, 1 ignored; artifact `12565812441`, artifact ZIP SHA-256 `19043c73f18ce01664c0c7add48669965b2258fb31dae188a9dc2c2337acbead`. Frozen benchmark ELF SHA-256 `9b18cd5c9c60820146655d0df4b0111e2f51d38fd3712acffbc1edb7a600d735`. Existing unrelated FEC pressure test ran ~710.61s in that functional workflow, not part of performance metric.
- S1 ARM64/AES128 same-VM single performance job [40109817134](https://github.com/lly8666/wbd-next/actions/runs/40109817134) attempt 1 job `120918993965`: exact binary downloaded and verified, real TLS 1.3 encrypted record generated via ephemeral in-job SSL MemoryBIO, actual client decrypt checked. Analysis artifact `12565174759`, ZIP SHA-256 `49082dd9e512d5f1285534d84a7272ed528b70b1a9b4572f0f1e752a44f0ffd5`. Raw record/cert/key not uploaded.
- Bounded separate capture [40109989226](https://github.com/lly8666/wbd-next/actions/runs/40109989226), artifact `12566246128`, ZIP SHA-256 `991d18fda3c1c9df6a17e36fd57c5fd9d97341563a19ece6b31ddcf45bead592`; native x86_64 loopback TCP, four records, controlled duplicate inner Seq fixture, not Go/raw/TUN.
- Independent x86_64 representative native S0 run [40109345476](https://github.com/lly8666/wbd-next/actions/runs/40109345476) was in progress when this report was initially drafted; its final status must be updated from Actions before a consolidated closure. It checks the same frozen 98e5 codec SOURCE.
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

Untested **product hard gates**: authenticated Go bootstrap both-end version negotiation and actual exporter key domain, real replay+generation admission and owner state, Stop cleanup, raw/TUN first-delivery no HOL, real Linux TCP retransmission, real outer repair frozen re-sends, actual MTU with OS options, host queue/drop/p99, production default via config/CLI/GUI, Android/Windows native. S0 component success is NOT product PASS; no public network experiment admission for this new format.

The x86_64 S0 job is a representative native functional cross-check, not same-machine ARM64 cost replication. No CPU comparison across VMs has been made.

## S3 bounded capture evidence / explicit distinction

Independent capture Action used real Linux loopback TCP and `tcpdump -i lo` on the wire; fixed inner TCP Seq and identical already-TLS-encrypted body were submitted twice to the lab record builder with **different outer PNs**. The analyzer reconstructs the outer TCP stream, deduplicates identical TCP Seq retransmitted segments, confirms whole TLSlike record boundaries, and checks candidate 64/128B equality across distinct outer TCP Seq positions. This is a **deliberately controlled inner-retransmission mimic**, not an inner kernel retransmission observed in netns/TUN.

- 4 captured records, two A FULL wire 1376B, two B SELECTIVE wire 1378B; 4 TCP payload segments, 0 same-outer-Seq duplicate segments.
- B occurrences in **different outer Seq** positions: same continuous ciphertext at both 64B and 128B. The FULL control encrypted blocks differ.
- An inner IP header-address canary was **not** found in visible outer stream in this small trace.
- Raw pcap 6196B; SHA-256 `42907dd45a18d5ccc08b3598417c5e9e320d6ad6395e67fc357e335177de1750`. Only digest/summary/hashes retained; raw owned files cleaned.
- This is a definite leakage mechanism and a negative appearance outcome for the *candidate wire under valid repeated input*. It is **not** a claim that arbitrary real traffic is always distinguishable, not a classifier, and does not prove real TLS-like handshake behavior either way.
- Test reference HTTPS outer handshake, packet-timing statistics, retransmission from actual kernel, and simultaneous business p99 have not been measured. Keep as NOT_RUN, not falsely PASS.

## Decision and stop

At S1 the ideal record saving is clear (>5%). At S3 a controlled packet replay with distinct outer positions creates publicly visible identical 64/128B TLS ciphertext sequences that full AEAD prevents. Under the predeclared appearance hard gate, this is enough for a **negative feasibility finding** and avoiding any expensive 50/500M real-driver/capacity suite or universal reclassifier. Host/product bottleneck limits are **NOT_MEASURED**, not HOST_CAPACITY_LIMITED; S2 workload is intentionally not executed because the candidate already violates the experiment's appearance criterion in bounded negative control.

Do not deploy, merge into main, change default, or present the experiment as a new cipher security qualification. Production keeps original fully encrypted record unchanged; no user content or bulk trace stored. A future architecture would need a fresh cost/security experiment, not reuse this one as a PASS.

## Recovery / consistency record

- S/H facts and all run IDs live only in `docs/evidence/selective-crypto-work/status.json`; no network/FEC status/next_action executed.
- The branch was advanced only via authenticated GitHub Contents API because this session had no mounted repository checkout. Remote reference plus changed files and Action SOURCE were inspected; **local git status cannot be claimed clean**.
- This report intentionally notes deferred real-path evidence as NOT_RUN and preserves all observed positives/negatives without seed rotation.
