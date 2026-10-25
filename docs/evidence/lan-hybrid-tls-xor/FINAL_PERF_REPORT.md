# Mixed steady TLS1.3 PN-XOR + FULL AES-GCM fallback: native record CPU audit (2026-10-25)

## Decision and scope

**SCOPED IDEAL-ORACLE RECORD-CPU PASS / REAL WBD Go-to-Rust-to-TUN NOT WIRED / XOR INSECURE.**

User-defined policy: Only *confirmed inner TLS1.3 steady application TCP/IP records* use the last public packet-number repeated 64-bit XOR mask. TLS1.3 handshake and encrypted alert/close edges, ordinary TCP, pure ACK, UDP and unconfirmed packets **must continue to use WBD's existing full AES-128-GCM authenticated TLS-like record**. Other packets are not actually tunneled through a second RFC TLS channel: the full mode uses the existing WBD record_crypto real AEAD with header protection and a TLS-looking 5B header.

The per-packet category is an **offline trusted ideal oracle** in this isolated benchmark. TLS1.3 outer record 17 03 03 may be encrypted handshake, application OR alert. A real packet classifier, mode negotiation, sender authentication of the decision, epoch/Stop, downgrade prevention and receiver mode signaling were not implemented or timed. Receiver mode in the benchmark is supplied out-of-band by the test harness. Any legitimate production claim requires solving these hard constraints.

Branch experiment/lan-hybrid-tls-xor-cost based on closed experiment/lan-xor-pn-mask SHA **86a4293a3348024231f7b51cbe0f58b691494d3c**. No production WBD record edit, main change, real TUN integration, FEC inheritance or device deployment.

## Test design

- Genuine local TLS1.3 encrypted application ciphertext generated via OpenSSL MemoryBIO: completed client/server TLS1.3 handshake, server encrypts 16000 application bytes, client decrypts to exactly original plaintext; frozen 1345B IPv4/TCP packet contains real TLS1.3 header and 1300 ciphertext bytes. Ephemeral TLS key/cert and corpus removed, no uploaded raw bytes.
- Explicit negative classification control: **byte-identical inner TLS ciphertext** packets classified as (a) confirmed steady and (b) protected first/last edge. Only (a) may use XOR; (b) stays fully authenticated. Synthetic TLS handshake, plain TCP, ACK-only and UDP likewise FULL.
- Rust real WBD native authenticated AES-128-GCM seal+open; old selective AAD experiment seal+open with oracle, format FULL layout control; prior rolling-word XOR; current PN-repeat XOR; all-XOR insecure floor.
- Nine 100-packet workloads: six 1345B equal-size eligible counts 0,25,50,75,90,100; Web/TLS bulk [80 app,5 edge,3 handshake,5 plain TCP,7 ACK]; mixed [40 app,8 edge,8 handshake,18 plain TCP,16 ACK,10 UDP]; non-TLS-heavy [10 app,15 edge,15 handshake,30 plain TCP,20 ACK,10 UDP].
- Variable types have 1345B TLS and plain TCP, 360B handshake, 40B ACK, 540B UDP. Generated mix does not represent observed user traffic.
- Each of six modes run twice, same native host, forward and reverse; 0.35s warm + 1s measured per leg; **108 measurements/host**. Linux /proc/thread-self/schedstat per-thread CPU nanoseconds / actual original inner byte, hot-path reused memory buffers. AEAD integrity is actually verified on receive. All packet and mode roundtrips checked byte-exact outside measured hot loop, not per-packet memcmp inside time measurement. Independent tools/lan_hybrid_mixed_analyze.py validates selection counts and correct wire lengths.

## Final native CI receipts

- Native x86_64 final corrected [40180809351](https://github.com/lly8666/wbd-next/actions/runs/40180809351), checkout SOURCE **548776b32b5f3847e23f8a2ae9ce81e23fd0a27f**, job 121131537365, SUCCESS, 10/10 XOR fixture tests, artifact **12593547885**, ZIP SHA256 **bf2ab5055907e31a541539de8c96932125be507ba760be499bb750da16c27db1**.
- Native ARM64 final corrected [40180812382](https://github.com/lly8666/wbd-next/actions/runs/40180812382), checkout SOURCE **b9c304c319788a3c4df5e3aa5ea5bebee4ae831a**, job 121131515427, SUCCESS, 10/10 XOR fixture tests, artifact **12594472987**, ZIP SHA256 **681acbeb67a6618006d7edb3625c822eea4a7d44e76fb79f5c1332d097b1228f**.
- Earlier diagnostic [x86_64 40180659070](https://github.com/lly8666/wbd-next/actions/runs/40180659070) and [ARM64 40180662061](https://github.com/lly8666/wbd-next/actions/runs/40180662061) successful but superseded: they did one whole-packet equality memcmp **per timed packet**, thereby introducing artificial validation CPU. Their raw receipts remain historical; **only corrected final source is used for percentages**.

## Equal-size native CPU savings versus full AES128-GCM

CPU percent saving is a same-machine record seal+open comparison, **NOT full tunnel or application CPU saving**.

| Oracle-confirmed steady TLS byte and packet fraction | x86 hybrid PN-XOR | ARM hybrid PN-XOR | x86 previous selective-AAD | ARM previous selective-AAD |
|---:|---:|---:|---:|---:|
| 0% | -0.28% | +0.04% | -3.39% | -3.22% |
| 25% | **21.55%** | **21.90%** | 1.75% | 4.77% |
| 50% | **43.69%** | **44.06%** | 6.85% | 13.55% |
| 75% | **65.44%** | **66.16%** | 12.42% | 21.93% |
| 90% | **78.82%** | **79.60%** | 15.36% | 27.46% |
| 100% | **87.30%** | **88.54%** | 16.78% | 31.00% |

Negative means cost regression; 0% near-zero effects should be treated as timing noise.

### Same-host actual CPU ns/inner byte at 90% steady TLS, lower is better

| Mode | x86_64 | ARM64 |
|---|---:|---:|
| Full authenticated WBD AES-GCM 31B overhead, ALL packets | 0.788193 | 0.769175 |
| FULL selective-AAD layout 33B | 0.815853 | 0.793766 |
| Old authenticated selective-AAD 33B | 0.667100 | 0.557922 |
| Prior hybrid word-rolling XOR, nonsteady FULL AES | 0.598324 | 0.334963 |
| **Current hybrid packet-number repeat XOR, nonsteady FULL AES** | **0.166911** | **0.156933** |
| All-PN-XOR (INSECURE FLOOR, VIOLATES NONSTEADY FULL POLICY) | 0.097194 | 0.087554 |

At 100% eligible, native x86 full 0.785816 vs hybrid 0.099801; ARM full 0.767073 vs hybrid 0.087877. At 0% eligible, hybrid matches full AES-GCM to within measurement noise.

## Realistic-size synthetic mixed categories

| Synthetic mix | Eligible packet count | Eligible inner bytes | x86 hybrid PN CPU saving | ARM hybrid PN CPU saving | x86 selective-AAD CPU saving | ARM selective-AAD saving |
|---|---:|---:|---:|---:|---:|---:|
| TLS-heavy download | 80% | 87.901% | **74.87%** | **75.76%** | 12.85% | 25.59% |
| Mixed session | 40% | 55.072% | **41.85%** | **44.27%** | 5.86% | 12.60% |
| Non-TLS-heavy | 10% | 15.717% | **11.13%** | **12.04%** | -2.52% | -0.27% |

Raw CPU ns/inner byte for each profile:
- x86 TLS-heavy Full 0.810918, HybridPN 0.203816, HybridWord 0.634793, SelectiveAAD 0.706739. ARM Full 0.785739, HybridPN 0.190433, HybridWord 0.363600, SelectiveAAD 0.584669.
- x86 mixed Full 0.910544, HybridPN 0.529466, HybridWord 0.796521, SelectiveAAD 0.857173. ARM Full 0.838962, HybridPN 0.467546, HybridWord 0.575875, SelectiveAAD 0.733254.
- x86 non-TLS-heavy Full 0.965651, HybridPN 0.858150, HybridWord 0.935856, SelectiveAAD 0.990023. ARM Full 0.876592, HybridPN 0.771067, HybridWord 0.801914, SelectiveAAD 0.878945.

## Wire budget

For 1345B complete original IP: WBD authenticated AES record is **1376B** (31B overhead), PN-repeat XOR record is **1360B** (15B overhead). Only confirmed steady TLS saves **16 outer bytes per packet**. At 0/25/50/75/90/100% eligible equal-size packets, wire savings per original packet are exactly 0/4/8/12/14.4/16 bytes. No actual TCP stream bandwidth, throughput or queue/p99 result was obtained.

## Security, classification and disposition

- **ZERO security on XOR packets:** the XOR mask is a publicly computable function of the clear PN, repeated every 8 bytes, and can be undone by any observer. No authentication, confidentiality, integrity, spoof protection or anti-replay; previously modified/replayed records were accepted. Preceding mutual TLS bootstrap cannot extend record AEAD guarantees over later raw XOR. TLS-like 17 03 03 is not genuine standards-compliant TLS1.3 ciphertext.
- **Per-packet classification cannot be inferred from TLS outer header alone:** 0x17 encrypted TLS1.3 handshake, app and alert look identical at framing level. Without authenticated endpoint-provided semantics/keys, strict guarantee that all handshake/tail packets stay AES-encrypted is unproven. The benchmark assumes perfect trusted offline classification and zero receive-mode negotiation overhead. A malicious peer able to label arbitrary packets as XOR could bypass authentication.
- Prior selective-AAD experiment keeps full AEAD authenticity but had a documented identical inner ciphertext repetition appearance regression; the present XOR changes bytes with new PN but is trivially distinguishable and reversible. Neither experiment proves TLS DPI indistinguishability.
- No WBD Go→Rust→TUN packet paths, real kernel inner TCP retransmission, application p99, actual tunnel Mbps, classifier CPU/cost, production MTU, direction/epoch/replay/Stop or device portability tests in the current mixed benchmark.

**Decision:** strong *record-level ideal-oracle* CPU advantage with high confirmed steady TLS byte fractions, weaker with mixed ordinary traffic. This does not authorize an insecure product mode or a claim of ~79% whole-process CPU saving. Main unchanged; scoped experiment complete; do not silently merge or deploy.
