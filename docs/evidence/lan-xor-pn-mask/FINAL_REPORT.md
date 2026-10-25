# LAN PN-repeat XOR — near-fixed-XOR CPU, distinct repeated packet bytes — 2026-10-25

## Decision and scope

**SCOPED_NATIVE_PERF_AND_PCAP_PASS; NEAR_FIXED_XOR_COST; NO_SECURITY; NOT_WBD_PRODUCT_WIRED.**

User reduced the appearance requirement to: the same original inner packet, retransmitted as a new outer record with a **different never-reused outer packet number**, must not result in the exact same external TLS-like data bytes. This experiment implements a very cheap and *deliberately insecure* reversible mask, while preserving the existing 5-byte TLS-like 17 03 03 framing.

Branch **experiment/lan-xor-pn-mask**, independently forked from completed lab experiment/lan-xor-word-optim at **56b6049f7c3307af27a88034b518943fe739d43d**. Main, closed selective TLS AAD negative experiment, authenticated WBD AEAD data plane, Go control/bootstrap, production config and TUN untouched.

## Exact mask mechanism

For each newly encapsulated complete IPv4 packet, make **one** 64-bit mask:

    mask64 = rotl64(outer_PN,17) XOR 0x6c616e5f6e6f7365 (public constant)
    for each full 8-byte chunk of (innerLength2B || entire raw IPv4 packet):
        chunk ^= mask64 little-endian
    for the final 1..7 bytes:
        byte ^= corresponding prefix of mask64 little-endian

Wire layout remains: 5B TLS-like application_data 17 03 03 + big-endian length | 8B **CLEAR** outer PN | 2B masked inner length | full masked original IPv4 packet. 1345B input -> 1360B TLS-looking record, 15B overhead. The transform is **not cryptography**. Because rotl64/XOR-public-constant is injective, for **identical plaintext and distinct 64-bit PNs**, every full aligned 8B ciphertext chunk necessarily differs (at least one byte); 64/128B contiguous identity windows therefore also differ. This is an exact property for full 8B chunks, **not** a guarantee that every byte differs, not a property for arbitrary distinct plaintext, and not an entropy/security property. Unique PN must never wrap or reset within the compared stream. The final short tail is not independently guaranteed different, but every actual 1345B fixture has many full 8B chunks.

PN is visible on wire and the constant is public: anyone can reverse the entire mask immediately. This provides **zero confidentiality, origin authentication, integrity protection, anti-replay or anti-downgrade**. It is even easier to analyze than the previous noncryptographic rolling XOR. A normal TLS 1.3 peer cannot authenticate/decrypt these raw data records as part of the preceding TLS handshake's session.

Implementation: tools/lan_xor_tlslike_lab.rs adds pn_repeat_word_mask and tests; crates/wbd-codec/examples/lan_xor_record_cost.rs adds same native hot-loop code in bench; standalone Go capture fixture tools/lan_xor_tls13_pn_handoff.go implements same mask. Both original and new variant are lab-only. Source code includes compatibility and exact reverse-format checks.

## Exact native Actions: all four SUCCESS

- Native x86_64 paired CPU [40177705366](https://github.com/lly8666/wbd-next/actions/runs/40177705366), checked-out SOURCE **3266927b7dd77408f3742207173055486190049d**, job **121121883616**, **SUCCESS**, Rust fixture 10/10, artifact **12593271865**, ZIP SHA256 **a74a681c3f7716adb10b7e25420cfe6d18041bec16c4b2b22e293300850b510b**.
- Native ARM64 paired CPU [40177708017](https://github.com/lly8666/wbd-next/actions/runs/40177708017), checked-out SOURCE **01bf8ea29d1bab31d158107cca01bd78849ae95b**, job **121121892057**, **SUCCESS**, Rust fixture 10/10, artifact **12592923076**, ZIP SHA256 **20e7b15aecbab0a6613936966766af48e392a871fe01987b4c4fd3905c6199a7**.
- Native x86_64 TCP capture [40177730105](https://github.com/lly8666/wbd-next/actions/runs/40177730105), checked-out SOURCE **52d75502faa19acd9d098d9eea52448051d29b5f**, job **121121960717**, **SUCCESS**, artifact **12592303188**, ZIP SHA256 **9e9aeab6e2e0c543840cd7f1f4e3a8a332903eec60c0a502e50e0f19e0c5996e**.
- Native ARM64 TCP capture [40177732221](https://github.com/lly8666/wbd-next/actions/runs/40177732221), checked-out SOURCE **070926f30f88459bce98907f4d28cca5fd136501**, job **121121967224**, **SUCCESS**, artifact **12592552702**, ZIP SHA256 **b731e2aa687c7a0ae42213fac9429267ca8205c0f3852ed1bb82a869d84ef209**.

All four work against the same unmodified Cargo.lock and functional mask code, with CI-only workflow changes between job trigger commits. No user machine deployment.

## CPU measurement methodology

One native release Rust (1.85.1) executable per host, actual CPU nano from /proc/thread-self/schedstat, actual **1345-byte identical synthetic original IPv4/TCP packet**, complete record seal + open including buffer copies, reused buffers, no TUN/socket/Go or allocation per packet in benchmark loop. 0.7s warmup followed by **6 seconds measured per leg**. Predeclared symmetric **14-leg order**: AES-GCM, ChaCha20-Poly1305, fixed XOR, old rolling, optimized word rolling, new PN-repeat, clear, clear, new PN-repeat, optimized word rolling, old rolling, fixed, ChaCha, AES. Two independent same-VM measurements per mode; per-mode mean ns/inner byte. All 10 native unit tests passed each host, including extreme PN values, short tails, reversible transform and all-full-8B-block-different assertions.

The AEAD comparisons involve **non-equivalent security**: AES/ChaCha authenticate the record and its headers while XOR deliberately does not. WBD authenticated AEAD has 31B overhead/1345B packet versus XOR 15B, but no full product cost is inferred.

### Same-host CPU cost (ns per original inner byte; LOWER BETTER)

| Mode | x86_64 | native ARM64 |
|---|---:|---:|
| No obfuscation / clear frame | 0.033924 | 0.035990 |
| Fixed XOR | 0.085111 | 0.080585 |
| **New PN-repeat 64-bit XOR** | **0.085056** | **0.080420** |
| Last 64-bit rolling xorshift (per-block state step) | 0.576679 | 0.288401 |
| Original bytewise rolling XOR | 3.320454 | 3.115255 |
| AES-128-GCM fully authenticated WBD record | 0.773900 | 0.755218 |
| ChaCha20-Poly1305 fully authenticated WBD record | 1.434706 | 2.681691 |

- New PN-repeat versus last fast word-rolling XOR **85.2507% lower CPU on x86_64, 72.1151% lower on ARM64**.
- New PN-repeat versus AES128-GCM **89.0094% lower record CPU on x86_64, 89.3514% on ARM64**.
- New PN-repeat and fixed XOR are **essentially identical cost** on both machines; small tiny differences (0.000055 / 0.000165 ns/B) are not evidence of robust faster-than-fixed-XOR performance.
- New mask versus no obfuscation is still ~2.51x x86 and ~2.23x ARM in this short record microbenchmark, mainly because data gets copied and touched.
- Symmetric legs x86 new mask 0.085028454/0.085083513 ns/B (spread 0.06473%); ARM 0.080415397/0.080425233 (spread 0.01223%). The artifact keeps every raw measurement and per-VM host manifest. No cross-machine percent differences presented.

## Genuine native TCP capture and independent wire parser

Each Go standalone lab first performs a **real mutual-authenticated TLS1.3 handshake** with self-contained ephemeral test certificate, performs the C_READY/S_READY barrier *inside* the TLS connection, then unwraps the underlying TCP and sends eight **fake TLS-looking raw** records. The independent Python parser reassembles the *observed* outer TCP stream by exact sequence offsets; it does not inspect only encoder buffers.

- Eight constructed-identical 1345B inner IPv4/TCP packets at **new outer PN 0 through 7 and distinct outer TCP Seq positions**, all 1360B outer TLS-like 17 03 03 records. First two fixed XOR; two original bytewise rolling; two previous 64-bit rolling; final two PN-repeat. All eight decoded correctly at peer.
- Actual native x86_64 and ARM64 traces: **6 preceding client-direction TLS handshake-stage records, 11 TCP payload segments, 8 steady new records**, zero observed same-outer-TCP-Seq duplicate segments.
- Fixed XOR produced **identical** 64B and 128B payload intervals for the two same-original-packet records (negative appearance control).
- Old rolling, last optimized rolling and **new PN-repeat** each produced **different** 64B and 128B intervals for their controlled same-packet, new-PN pairs.
- In both independent pcaps, every one of the PN-repeat pair's full 8-byte masked blocks differed; this validates the more precise per-block invariant.
- Exact x86_64 owned pcap **14233 bytes**, SHA256 **35315c728c55a6621e10e0a53785193cfb8f5f59c48a8327dc558e9914a49be1**; ARM64 owned pcap **14233 bytes**, SHA256 **cefee91f8d9387c6c1495cc5e62e6dfff46e0433d3d7ed3a8ecdcc3f52732db0**. Both raw pcaps cleaned from temporary directory after each Action; only hashes, summary, binary/build receipts retained in respective artifacts.

## Limitations / stop boundary

**Measured scope is only one microbenchmark and two bounded synthetic IPv4-over-loopback captures.** No actual WBD Go->Rust->TUN bootstrap or data-plane integration, genuine TLS 1.3 application-data cryptographic record compliance, real native inner TCP retransmissions, packet mix, packet size sweep, Windows/Android, full WBD PPS/throughput/p99, memory pressure, product MTU, admission generation/Stop, security protection or traffic classification was measured.

The user requested simple bytes-differ appearance, not encryption. The present code **meets that narrow bitwise inequality** but can be reversed from the visible PN in trivial constant time, and records are **not standard TLS application ciphertext**. A sophisticated observer can detect the periodic 8-byte difference pattern. Any product enablement would require explicit security downgrade design and separate tested WBD path, not an automatic merge.

**Scoped disposition:** performance-positive PN-repeat mask candidate in standalone lab; near fixed-XOR CPU floor for this record implementation; no outstanding work inside the current bounded experiment, no merge or deployment.
