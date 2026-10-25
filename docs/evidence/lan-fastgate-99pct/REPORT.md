# 99% fast path versus 100% public PN-XOR: exact native same-VM comparison

2026-10-25. Branch: experiment/lan-fastgate-99pct-cost.
Base: experiment/lan-fastgate-mixed-wire at dae61abcf2dc44c05e3b803cb8985d760ab2a958.

## Decision

**SCOPED_NATIVE_99PCT_CPU_PASS. ALL-XOR FASTER BUT FAILS THE HANDSHAKE-PRIVACY REQUIREMENT.**

Target: 100 equally sized (1345B complete inner IPv4/TCP) original packets per repeating deterministic modelled stream. Exactly 99 packets contain a real TLS1.3 post-handshake encrypted application record and have a **trusted laboratory** fast-eligible label; 1 packet is an equally sized protected TLS-edge packet (its TCP payload deliberately has identical bytes as the app fixture, while its provenance/sequence is different). Protected edge MUST use authenticated full WBD AES128-GCM in the hybrid modes. This 1% is not actual measured user traffic nor guaranteed ClientHello in a live application.

Four modes benchmarked on same native VM:
- Full AES128-GCM: every packet full authenticated genuine WBD LaneTxCrypto/LaneRxCrypto record.
- Hybrid ideal oracle: 99% public PN-XOR and 1% full WBD AES128-GCM, no extra per-packet IPv4/TCP fast-gate parsing.
- Hybrid previous cheap gate: exactly the same 99/1 split but runs constant-time IPv4/TCP header, TCP sequence and TLS record bounds checks in addition to the **test-supplied trusted TLS classification label**.
- All-PN-XOR: 100% every packet XOR including the protected edge, insecure *reference* that VIOLATES the user's handshake privacy goal.

XOR uses the documented public per-packet 64bit mask: rotl64(outerPN,17) XOR public salt, applied repeatedly over 8-byte words of original IPv4 bytes+length. It has NO confidentiality, integrity, anti-replay or valid TLS1.3 application-data AEAD.

## Measurement

Native actual Rust WBD authenticated AES128-GCM record implementation (not an artificial fake AES spin), OpenSSL-produced true TLS1.3 application encrypted record inserted into the original IPv4 packet, CPU seal+open and reusable buffer copying. Rust 1.85.1 release --locked; Linux schedstat per-thread CPU ns / original 1345 byte. Four modes tested in precisely 16 timed legs per VM, forward/reverse/forward/reverse; each leg 0.35s warmup, 2s measured. Each mode has four independent CPU samples. Independent Python analyzer validates all 16-mode order, exactly 99% fast and 1% full AES packet counts, original bytes, wire lengths and 100-packet cycle, samples and CPU timings. Rust XOR unit tests 10/10 on both native architectures.

**No actual Go-to-Rust-to-TUN, no real TLS flow classification/handshake parser, no end-to-end Mbps, no application p99, no host full-process CPU, no mode capability negotiation, no XOR security.**

## Same-VM results; ns CPU per original inner byte (lower is faster)

| Mode | x86_64 | ARM64 |
|---|---:|---:|
| All packets full authenticated WBD AES128-GCM | 0.791092324 | 0.764919342 |
| All packets public PN-XOR (insecure lower bound) | **0.103160718** | **0.086885132** |
| 99% PN-XOR + 1% real AES (trusted label, no extra IPv4/TCP gate) | 0.110269620 | 0.094333144 |
| **99% PN-XOR + 1% AES, plus previous cheap IPv4/TCP fast gate** | **0.111014380** | **0.095668947** |

**Hybrid cheap-gate relative cost above all-XOR:** x86 **7.613034956%**, ARM64 **10.109687199%**.

**Hybrid cheap-gate CPU reduction versus all AES:** x86 **85.966950180%**, ARM64 **87.492936636%**.

Difference breakdown:
- The 1% genuine AEAD fallback alone yields ideal-oracle hybrid CPU extra over all-XOR of x86 **6.891093338%**, ARM64 **8.572251471%**.
- The added cheap IPv4/TCP checks cost **0.675399227% x86** and **1.416048490% ARM64** relative to same-host ideal-oracle 99% hybrid. These percentages have DIFFERENT denominators and should not be naively added.
- Both exact modes retain 15B overhead/packet on fast records; the hybrid's one authenticated fallback adds 16B over all-XOR per cycle of 100 complete IPv4 packets, i.e. **0.16 extra wire bytes per original packet** (not including routing/link payload overhead).
- x86 first timed pass had somewhat higher absolute CPU ns/B for the XOR modes than later passes; the table uses mean of all four samples with raw legs archived. This is one native runner VM per architecture, not robust multi-machine distribution, so sub-1% deltas should not be overinterpreted.

## Reproducible CI provenance

- x86_64 [40185975878](https://github.com/lly8666/wbd-next/actions/runs/40185975878), job 121146721987, source SHA **9e8af7daa03ce0e2640409c6a7aad47215dbe2dc**, SUCCESS. Artifact ID **12596197692**, artifact ZIP SHA256 **244feb7a7b527078805327ab45817c0e990843e9ff5b0a3f045b0ceea3ba4872**.
- ARM64 [40185978508](https://github.com/lly8666/wbd-next/actions/runs/40185978508), job 121146731010, source SHA **64bcde9a9948f9dcfa83cd8da2cadb26107e5dfb**, SUCCESS. Artifact ID **12595334009**, artifact ZIP SHA256 **1f6e841ab6bd4a837dc9e7470212be1a457aea55ad178002f54b162a916937c5**.
- Both have 16 valid CPU legs and 10/10 standalone XOR unit tests, and source manifests, CPU host detail, raw leg JSON lines, independent summary JSON, binary sha256 and genuine TLS1.3 corpus hash. The corpus and ephemeral keys were destroyed at job cleanup.

## Production integration and protection blockers

1. The fast-gate checks inside the benchmark use an **externally trusted synthetic TLS1.3 app label**. The earlier real TLS classifier **does not exist in WBD product**. Plain 0x17 03 03 cannot distinguish encrypted TLS1.3 handshake, alert and application contents; using size or port would incorrectly route sensitive content to public XOR. Whole per-flow TCP reconstruction and trusted proof cost excluded.
2. In hybrid mode, the 1% known sensitive records are correctly AES encrypted/authenticated, but the 99% XOR records are independently reversible and unauthenticated, leaking the inner IP/TCP header and allowing tamper/replay. A preceding TLS handshake does not authenticate future custom XOR records.
3. All-XOR benchmark **actively violates** the user's specific goal: retransmitted ClientHello/ServerHello carrying SNI/ALPN and other handshake bytes would be exposed after trivial XOR reversal. Savings of ~7.6% to 10.1% record CPU is the *price of preserving 1% authenticated fallback in this controlled workload*, not a secure-versus-secure performance tradeoff.
4. This is an ideal-oracle record CPU microbenchmark, not real WBD Go/Rust/TUN end-to-end qualified or production merge-ready. No main edits or deployment.

**Scoped decision:** for the specified 99% hypothetical eligibility, the simple fast-gated hybrid is only ~7.6% (x86_64) / 10.1% (ARM64) more record CPU than all-XOR, while retaining AES on the remaining 1% sensitive records *assuming trustworthy classification*. All-XOR is unacceptable for handshake privacy.
