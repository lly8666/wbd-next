# Single existing TLS23 header, 2-byte marker, rolling final 8 BYTES

## Scope and resolution

**COMPLETE native x86_64 and ARM64 Go A/B tests, nine scenarios, five benchmark repetitions each; WBD main unchanged.** Corrected the previous double-header interpretation. Lab branch: experiment/lan-tail-marker-one-header-8byte. Base: experiment/lan-tail-marker-rolling8-cost at cced30927c09c946788d3178a4a48110c25be303.

For **trusted pre-existing full TLS23 records**: do NOT add another 5B TLS-like header. Preserve the one ORIGINAL 5-byte 17 03 03 header and original inner TLSCiphertext bytes, add 2B trailing mode marker, update existing header LENGTH by +2 and XOR exactly the **FINAL EIGHT BYTES OF THE FULL WIRE** using a rolling implicit record counter. This includes the 2B marker and the last 6B of the original inner ciphertext/tag. On receipt copy the wire, undo the final 8B XOR, read the 2B marker, remove it and restore the ORIGINAL 5B TLS header length (-2) before giving the packet to the original TLS endpoint.

For **non23 or retransmitted 23**: create ONE new TLS-like 5B header with type 0x17, 0x0303 and length, AES-128-GCM encrypt the FULL original 1345B record using an independent direction-specific test key and counter-derived nonce and header+unmasked selector+counter AAD, append 16B authentication tag and 2B marker; finally rolling XOR last 8B in place. No WBD protected PN reused; independent per-record implicit 64-bit counter pre-synchronized by test harness. Counter desync, stream framing, reordering, reconnect and rekeying are not implemented.

**Precisely one 5B header at a time**. Fast original 1345B TLS record -> 1347B wire (+2B). AES fallback 1345B original -> 1368B wire (+23B). Previous erroneous double-header fast -> 1352B (+7B). At 99% fast/1% AES, average extra bytes per original 1345B frame = 2.21B. At 95% fast = 3.05B, at 80% fast = 6.2B.

## Native test method

Synthetic 1345B complete TLS-23 record with **actual AES128-GCM AEAD-encrypted TLS-like body**: record header 17 03 03, TLSCiphertext length 1340, test traffic AEAD with original 5-byte TLS header as AAD, deterministic test key/nonce. This is a cryptographically self-consistent one-record TLS-style fixture but is not a full negotiated TLS1.3 session. Test verifies inner AEAD opens before transport wrap, fails on unprocessed wrapped fast record, then after 8B inverse XOR, marker stripping and original header recovery **decrypts back to byte-for-byte original TLS record plaintext and authenticates successfully**. Additional non23 and retransmitted 23 fallback tests check 1000 iterations across 0%, 80%, 95%, 99%, 100% trusted mode and all four tail styles. Tampered fast payload is still accepted (no outer MAC), but tampering with AES fallback is rejected. Confirms no double 17 03 03 prefix at transport byte 5.

Go 1.25.x, GOMAXPROCS=1, 100x 1345B originals per benchmark iteration, full TX seal + RX open, buffers allocated before timer, FIVE 1-second native repetitions per 9 scenarios, 0 B/op and 0 heap allocs/op for all modes on both architectures. One word XOR variant loads/stores the last 8B as a 64-bit little endian integer and computes a byte-order-reversed rolling mask to exactly match the separately tested 8B byte loop.

## Results, mean ns per 100 original packets, lower is faster

| Scenario | x86_64 ns/100 | ARM64 ns/100 |
|---|---:|---:|
| **Single existing TLS header, 99% fast, last 8B word XOR** | **7712.4** | **9907.8** |
| Single header 99%, last 8B byte-by-byte XOR | 8771.6 | 10747.8 |
| Single header 99%, no tail XOR | 6967.8 | 9530.0 |
| Single header 99%, last 1B XOR | 7632.8 | 9676.2 |
| Single header 95% fast, 5% AES, last 8B word XOR | 10980.6 | 13236.0 |
| Single header 80% fast, 20% AES, last 8B word XOR | 23135.4 | 25745.8 |
| Single header 100% AES, last 8B word XOR | 87967.0 | 91861.6 |
| **Old DOUBLE HEADER** 99%, same last 8B word XOR | 7668.8 | 9677.6 |
| Previous optimized full PN-XOR, different wire | 20327.6 | 24372.4 |

99% single header last8 word variant: 2.636x faster than previous whole-body public PN-XOR comparator x86 and 2.46x ARM, only in this Go memory microbenchmark. Removal of the extra 5B header saves 5 wire bytes but caused approximately +0.568% x86/+2.378% ARM measured CPU time compared to the old double-head fixture, due to the needed original length reconstruction and compiler/path differences. No claim of a causal speedup from removing the outer header. Tail8 word over no tail added 7.446ns per packet x86 and 3.778ns ARM. Tail8 word over tail8 byte loop reduced elapsed time approximately 12.08% x86 and 7.82% ARM. All conditions are same native Go compiler and runner within each arm of the test, not WBD Rust production.

Per-mode native five raw ns/100:
- x86: single99word [7727,7705,7712,7714,7704]; single99loop [8739,8742,8872,8749,8756]; single99no [6966,6971,6969,6963,6970]; single99last1 [7644,7630,7614,7611,7665]; single95 [11012,10965,10961,11000,10965]; single80 [23137,23133,23127,23136,23144]; allAES [88075,87847,87994,88020,87899]; oldDouble [7668,7674,7663,7670,7669]; oldFullXOR [20317,20360,20349,20291,20321].
- ARM: single99word [9904,9913,9910,9909,9903]; single99loop [10771,10748,10729,10745,10746]; single99no [9530,9533,9527,9532,9528]; single99last1 [9683,9676,9703,9659,9660]; single95 [13257,13240,13225,13227,13231]; single80 [25752,25756,25745,25737,25739]; allAES [91970,91849,91788,91854,91847]; oldDouble [9680,9677,9675,9686,9670]; oldFullXOR [24360,24387,24367,24384,24364].

## Critical protocol limitations

- The fast on-wire 5B TLS header's length is modified by +2 and its final six original TLS AEAD ciphertext/tag bytes are XORed with a **public predictable rolling mask**. Thus it is **not an end-to-end decryptable TLS1.3 TLSCiphertext on the wire** by an ordinary TLS endpoint. Only the custom receiver can undo the transform and restore the authenticated original header before delivering it. The unit test specifically demonstrates this. RFC8446 Sec 5.2 identifies the original 5B header as AEAD AAD. Simply adding a trailer *outside* the claimed length would instead leave stray non-record bytes and break TLS record framing.
- The fixed two-byte marker is protected only by public counter-derived XOR, not by any keyed MAC on the fast path; fast records can be forged or modified and the intended family can be reversed if the counter is deduced. A randomly distributed last8 mask in lab does not prove fingerprint resistance.
- 2B marker fast/AES distributions are disjoint before XOR. AES fallback adds 21 more wire bytes than fast records for identically sized input, so size distributions can reveal mode. Client/server counter must be strictly synchronized even across disconnects, retransmissions or concurrent paths.
- A clear 23 first byte alone does NOT verify inner TLS1.3 finished/application data or where complete TLS records begin in a TCP byte stream; the test uses an explicit trusted label and full records. No live TLS classifier, kernel real TUN, Go-Rust WBD owner, routing/MTU/FEC/Windows path, production authorization or replay check exists.
- The AES fallback is a custom WBD AEAD envelope masquerading as TLS-like, **not actual TLS1.3** negotiated keys or valid TLS record semantics. The fast path remains unauthenticated by WBD's transport. Do not deploy as a confidentiality/security protocol based on this test.
- Native Go benchmark wall time for in-memory seal+open only, not full-process CPU or throughput.

## Reproducible evidence

Source: tools/lan_tail_single_header_8bytes_test.go and tools/lan_tail_single_header_analyze.py.
Native x86 success: GitHub Actions run https://github.com/lly8666/wbd-next/actions/runs/40266693532, archived artifact 12625998188.
Native ARM success: run https://github.com/lly8666/wbd-next/actions/runs/40266697434, archived artifact 12626815966.
Both correct and perf CI jobs passed, including independently parsed five repetitions for all 9 modes, no duplicate header, original AEAD integrity restored after unwrap, zero Go heap allocations/op.

Disposition: **isolated performance experiment COMPLETE, WBD main unchanged**, not an approved real TLS1.3 framing implementation.
