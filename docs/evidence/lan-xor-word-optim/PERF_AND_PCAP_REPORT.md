# LAN TLS-like rolling XOR — byte-identical 64-bit word optimization, CPU and wire results (2026-10-25)

## Decision

**SCOPED_LAB_PERF_AND_PCAP_PASS / NOT_PRODUCT_WIRED / INSECURE_OBFUSCATION_ONLY.**

The previous rolling-XOR implementation cost more CPU than AES-128-GCM. This authorized follow-up changes only HOW the identical rolling keystream is applied: groups of **8 bytes use u64 little-endian XOR**, with a 1..7-byte tail handled bytewise. The generator, seed, packet number, wire layout, 5-byte 17 03 03 header, output mask bytes, packet fixture and full 1345-byte inner IPv4/TCP packet remain unchanged. No SSE/NEON-specific unsafe code or new secret/algorithm. Neither the old nor the new rolling XOR provides confidentiality, authentication, integrity or anti-replay.

All code, tests and CI reside on a NEW isolated branch **experiment/lan-xor-word-optim** based on prior completed experiment/lan-xor-tlslike SHA **c5bd5f0e42ce07b74e7f166101e54b203f05ea2a**. No main merge, original secure record rewrite, WBD Go->Rust->TUN integration or device deployment.

## Exact source and finite Actions

- New reference implementation and equivalence tests: tools/lan_xor_tlslike_lab.rs, first implementing commit **e946de9db308b1afa996d79d872f8d38688e9969**.
- Paired CPU code in crates/wbd-codec/examples/lan_xor_record_cost.rs, code commit **8a840f6544b92599ef3336bac3ccbf9a44243fa9**; independent summary verifier tools/lan_xor_perf_analyze.py, commit **4a9596781b547b7072bffad813bb01d17aaf0666**.
- Wire fixture tools/lan_xor_tls13_word_handoff.go (real mutual TLS1.3 then raw data, includes Go old/optimized byte-equivalence preflight), independent classic-pcap analyzer tools/lan_xor_tls13_word_pcap.py.
- x86_64 native same-VM CPU: [Action 40176827919](https://github.com/lly8666/wbd-next/actions/runs/40176827919), SOURCE **25a183f7a469a158ebf750fd1f194991f8a7d65b**, job **121119204057**, **SUCCESS**, 7 passed / 0 failed, artifact **12593036310**, ZIP SHA256 **dc663f629302904986e9824993a83657a9060e0200d7a545e7bf7f55470f07bb**.
- ARM64 native same-VM CPU: [Action 40176831540](https://github.com/lly8666/wbd-next/actions/runs/40176831540), SOURCE **91325bf1a123f6c3d3a9cfcc76d7ba3fcc5d4e46**, job **121119214546**, **SUCCESS**, 7 passed / 0 failed, artifact **12592491759**, ZIP SHA256 **c22b645eb1a1bfd5f478f269aaada39cac9c30a26c00dcf7ae221749ed742c0b**.
- x86_64 native real TLS13->raw capture: [Action 40176869208](https://github.com/lly8666/wbd-next/actions/runs/40176869208), SOURCE **0fbdef60a4e27905d093d1a9f830faeb0559ddd1**, job **121119328917**, **SUCCESS**, artifact **12593105987**, ZIP SHA256 **eb9cb384e2c2b0cafd9649df27bdbb1c5b26c6c1a5dd5946d10daf007bc312c0**.
- ARM64 native real TLS13->raw capture: [Action 40176873117](https://github.com/lly8666/wbd-next/actions/runs/40176873117), SOURCE **9a4d873040703dd44ef14deb7986716b3b9a65e2**, job **121119340511**, **SUCCESS**, artifact **12592846516**, ZIP SHA256 **48401dbf4c8dfdb918c37f7d0bc8610f65068d4276a25a6c888bbd0ff171ffe5**.

## CPU methodology

Every CPU result comes from a **single same-host sequence**; never compare x86_64 measurements numerically against ARM64 as if a paired machine.

- Real optimized release Rust 1.85.1, source-pinned one VM; **exact same 1345-byte constructed complete inner IPv4/TCP packet**, same reusable wire and output buffers and equivalent record seal + open path.
- Live Linux thread CPU time from /proc/thread-self/schedstat, divided by actual original inner bytes; single worker, no network/Go/TUN or queue/driver work in timed loop.
- Preflight asserts the optimized sealed XOR bytes **exactly equal** the previously captured bytewise-rolling-XOR fixture for identical PNs and packets; every mode roundtrips. Standalone tests check lengths **0..9 edge cases, 15,16,17,63,64,65,127,128,129,1347,16397** and multiple PNs including max u64, and verify involution. 7/7 tests passed on both native hosts.
- Warm 0.7 seconds per leg then record 6 seconds per leg. Predeclared symmetric **12-leg order**: AES, ChaCha, fixed XOR, original rolling XOR, optimized rolling word XOR, clear, clear, optimized, original, fixed, ChaCha, AES. Two measurements/mode; average of their measured CPU ns per inner byte.
- Authenticated AES/ChaCha use the existing WBD AEAD+header-protection code with 31B wire overhead; all XOR modes and clear have 15B overhead. These are NOT equal-security modes.
- Entire record CPUs, not isolated instructions; no full-VPN throughput extrapolation.

## Same-host measurements — CPU ns / original inner byte (lower is better)

| Mode | Native x86_64 | Native ARM64 |
|---|---:|---:|
| Clear TLS-like frame | 0.032593 | 0.037480 |
| Fixed XOR | 0.085126 | 0.082194 |
| Existing AES-128-GCM full authenticated record | 0.787178 | 0.754171 |
| Existing ChaCha20-Poly1305 full authenticated record | 1.438706 | 2.678906 |
| Old rolling XOR, bytewise chunks | **3.000111** | **3.101395** |
| **New rolling XOR, 64-bit word application** | **0.584623** | **0.287203** |

**Same-job results and legitimate comparisons:**
- x86_64: optimized vs old rolling **80.5133% lower CPU**; optimized vs AES-128-GCM **25.7318% lower CPU**. New vs old ~5.13x faster.
- ARM64: optimized vs old rolling **90.7395% lower CPU**; optimized vs AES-128-GCM **61.9180% lower CPU**. New vs old ~10.80x faster.
- Both suites retain byte-for-byte identical reversible XOR bytes; the speedup is an implementation optimization, not a new cipher, keystream, or new traffic concealment.
- Two-leg spreads: x86 optimized 0.700%, old rolling 0.753%, AES 0.042%; ARM optimized 0.0168%, old rolling 0.0090%, AES 0.0465%. Artifacts retain all twelve legs, packet counts, CPU and wall time, host CPU manifests, binary digests, and machine-readable summary.
- Cross-job older numerical rates were NOT used in percentages. The same-VM A/B measurement replaces informal comparison to the previous completed perf report.

## Real TLS13 handshake -> bounded TCP capture on native x86 and ARM

Each independent Go lab first completes **real mutual TLS 1.3 certificate-verified handshake**, exchanges authenticated C_READY/S_READY switch barrier and then bypasses the outer TLS record layer to send exactly **six** TLS-looking records containing the **same constructed IPv4 packet**:
- Fixed/fixed PN0/1 (repetition negative control).
- Old bytewise rolling/rolling PN2/3.
- Optimized 64-bit rolling/rolling PN4/5.
- Independent classic-pcap parser reconstructs actual **outer TCP bytes by sequence offsets**, not output-only generated buffers, and validates the 6 separate record boundaries, 17 03 03 + valid declared lengths and distinct outer TCP Seq positions.

| Capture | x86_64 | ARM64 |
|---|---|---|
| TLS client-to-server records preceding raw handoff | 6 | 6 |
| Fresh TLS-looking steady-state records | **6**, each 1360 bytes | **6**, each 1360 bytes |
| Actual outer TCP payload segments | 9 | 9 |
| Same outer TCP Seq duplication in capture | 0 | 0 |
| Fixed XOR 64/128B repeat at different outer positions | YES / YES | YES / YES |
| Old rolling XOR 64/128B same-span repeat | NO / NO | NO / NO |
| **Optimized rolling word XOR 64/128B same-span repeat** | **NO / NO** | **NO / NO** |
| Full original IPv4 fixture recovered at receiver | YES 6/6 | YES 6/6 |
| Go old/word XOR byte equality at same PN | PASS | PASS |

Actual source-independent pcap:
- x86_64 **11349 bytes**, SHA256 **e369035267e78a4555b36a72d9c0b32b73bdf9e325bd88237953b032b0754750**.
- ARM64 **11349 bytes**, SHA256 **438daeebd52cc9248d44cfb6f77b6f0ee3ecafeb85c47a3d48bbbb03db051777**.
- Raw pcap, ephemeral TLS private key/certificate never committed; owned raw pcap removed on Action exit, only hashes, summaries and provenance uploaded.

## Limitations and stop boundary

- These captures check **one specific repeated 64B and 128B window** of a fixed packet pair, not full traffic classification, entropy indistinguishability, legitimate TLS 1.3 record decryption or resistance to a knowledgeable observer. Keystream is intentionally cheap, predictable/noncryptographic; an earlier authenticated handshake DOES NOT authenticate subsequent XOR data. Tampering/replay remain possible, and there is no cryptographic secrecy.
- Word XOR output byte equality means **no new appearance benefit** over original rolling XOR, just lower CPU. No claim that this is secure TLS/REALITY/Vision or that a network censor cannot recognize it.
- No real WBD Go bootstrap negotiation, exporter/generation/Stop/anti-downgrade, actual Rust production codec ABI, real TUN packets, real kernel inner retransmit in this new experiment, Windows/Android, real network transfer, application throughput/pps/p99/queue/drop, CPU on actual user devices, or multi-client lifecycle was tested.
- Observed CPU advantage over AES is **record-level only**. The secure AEAD includes integrity/authentication that XOR does not; never replace the product security default based on this comparison.
- Scope complete. No merge or deployment, no main modification and no inherited FEC/network work.

**Final scoped decision:** BYTE_IDENTICAL_OPTIMIZATION_PERF_POSITIVE_ON_NATIVE_X86_ARM_AND_NARROW_PCAP_REGRESSION_PASS; remains lab-only insecure obfuscation.
