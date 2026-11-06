# PLAN028 H1271 — H1270 original Fixed6 RAW RX 120s evidence and true kernel-vs-delivered counter separation

## Native source-frozen result (not rare failure closeout)

Original Go TLS+Rust native hosted x86 Action [42157023195](https://github.com/lly8666/wbd-next/actions/runs/42157023195) **SUCCESS**, exact source `31da60aff86a673c28bcf2adbd7378c30326101f`, pinned original Go donor `a7a82db31fe736ffedee330795a3234d358f1984`, product Rust engine SHA256 `2d457e05c92d4f0a7d71be7836af85a820a97a1e0b46ad4010612dc7f7750b0f`. Original immutable artifact **13474439852**, SHA256 `4100db4819d868bd836fdf91414efe418874b3865e296990c338570455342285`, **31 archived entries, ZIP CRC PASS**. No packet mock, all original TLS-authenticated, TUN and raw M4. 120 seconds true coordinated business, 10 second drain: Alice Normal Off 0%/12Mbps and Erin Normal Fixed6 30%/125ms one-way/outer1280/16Mbps. Physical bidirectional tc netem limit10000; actual Erin loss 29.9614% uplink and30.0984% downlink. Both server authenticated /32 shared-TUN leases peak report `pending_overflow=0`; Normal dual-direction all phases 100% unique app UDP.

Fixed6 original business:
| Native real phase | Actual uplink unique UDP | Actual downlink unique UDP |
|---|---:|---:|
| 30s steady | 100.000% | 99.9669% |
| 35s overload1.3x | 99.9625% | 99.9765% |
| 45s sustained-rate recovery | 99.9621% | 99.9594% |

Fixed6 client's original RAW TX default SO_SNDBUF effective212,992 bytes and server same default; original client RAW RX requested4MiB but **effective2MiB kernel-capped**. Client and server original M4 typed `sendmmsg EAGAIN=0`. No observed >=750ms plateau in the RX legacy delivered counter during the active interval; 369 actual 500ms native RX samples, cumulative poll_ready206499, poll_idle5503, max loop interval **10.670794ms**, largest original `background_raw_once` duration **1.111947ms**. Original client FEC2 RX receipt counters (end) source222394, parity280053, recovered93855, tun_failure0; these are not original kernel receive count by themselves. This original SOURCE **does not reproduce** H1268's separate 1.007s RAW ingress/1.27s downlink interruption or H1259's old 7s S2C recovery gap. It proves instrumentation works and ordinary flows are healthy in this run, not that the intermittent bug is solved. The independent H1263/H1267 C2S original raw M4 EAGAIN episodes remain genuine previous cases, not forcibly identified with S2C outages.

## Diagnostic correctness discovered in source audit

The historical numeric field `V4_PUBLIC_FEC2_EGRESS_DIAG ... side=rx raw_batches=N` reads `stats_rx.rx`. Original `background_raw_once` returns **`delivered_total` unique owner IP receipts**, which is the exact quantity added to `stats_rx.rx`. Thus its `raw_batches` field name is **misleading**: a flat value does NOT alone prove Linux raw FD saw no L3 packets, although H1268 separately observed flat FEC source/parity counts. Crucially, existing `LoopCounts.rx_chain[0]` already accumulates **`batch.observed` genuine native RAW L3 entries**, `rx_chain[1]` counts checksum/tuple-admitted ciphertext candidates, `rx_chain[5]` tracks TUN delivered IP; no new kernel per-packet instrumentation or memory needs adding.

H1271's *next-source*, strictly diagnostic-only adjustment retains the old `raw_batches` field for report compatibility but at existing **developer-opt-in 500ms RX egress logs** appends `kernel_raw_observed`, `tuple_candidates`, `tun_delivered`, and `delivered_legacy_raw_batches` from those existing counters. One native Rust unit checks that kernel RX seen37, tuple candidate21, TUN delivered9 and legacy delivered7 remain **distinct**; when legacy delivered0 with kernel observed37, the kernel was not empty. This instrumentation changes neither AEAD/PN, authenticated original delivery, FEC6 repair budget, socket buffers, thread/read cadence, Go TLS nor outer cosmetic retransmission. Set the completed H1270 120s workflow to **manual-only** to avoid repeating the same original long-ish scene just to clarify a diagnostic label.

This H1271 new source is **NOT** a demonstrated fix for the random Fixed6 RAW RX blackout. A future observed S2C gap can use the extra true kernel RX and tuple counts to distinguish "no kernel raw L3 observed", "raw L3 arrived but no tuple/checksum admission" and "tuple admitted but original Rust owner did not deliver". Do not enlarge global RX/TX buffers, change FEC2 age/parity or reuse original PN to mask a not-yet-reproduced symptom. Historical PLAN027A H998 same-socket online MTU change FAIL remains separately open.

## H1272 exact-source native accounting confirmation

The new-source [Action42158532358](https://github.com/lly8666/wbd-next/actions/runs/42158532358) **SUCCESS** on Linux x86 Rust1.85.1 passed `m0_plan028_original_raw_rx_true_kernel_vs_delivery_counter_contract` **1/1**. Exact tested SOURCE `376f5f754be17599760f3d9955543f8401bac5d3`, artifact13474674369 SHA256 `438a7aee40ba1a27f6ba7cb2def70d174c68ce481f6c1ab99245a501de463f46`; evidence `docs/evidence/M0/PLAN028-H1271-SOURCE376F-ORIGINAL-RAW-RX-TRUE-COUNTER-NATIVE-20261106.json`. This is a **native functional counter-contract unit**, not another protected live network A/B or an intermittent RX blackout fix. The earlier H1270 true original packet Action42157023195 remains tied to SOURCE31da; no ungrounded retroactive data changes.

```feature-impact
{"kind":"updated","ids":["linux-raw-tun"],"reason":"Original-Go/Rust developer-only RAW RX egress diagnostics now expose preexisting real kernel-observed/tuple/TUN and legacy-delivered distinct counters; no data-plane or user-visible transport setting change. H1270 original Action source-qualified performance result archived without promoting rare outage to PASS."}
```
