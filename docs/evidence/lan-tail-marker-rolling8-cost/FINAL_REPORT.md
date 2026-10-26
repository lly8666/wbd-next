# Two-byte trailing marker and rolling last-byte XOR: minimal native cost study

Status: COMPLETE, scoped to native Go microbenchmarks. WBD main remains untouched. Independent experiment branch: experiment/lan-tail-marker-rolling8-cost.

## Wire studied

Every 1345B synthetic inner input becomes a custom TLS-like outer record beginning with 17 03 03 and 2-byte outer length.

Fast: outer 5B | unchanged original synthetic inner TLS-23 record 1345B | 2B trailing selector = 1352B total, +7B.
AES fallback: outer 5B | AES-128-GCM encrypted 1345B payload plus 16B tag | 2B trailing selector = 1368B total, +23B.

A trusted TEST ORACLE labels all original 23 and nonretransmitted as fast; non23 or retransmitted original 23 as AES fallback. In the 95% case, among 5 fallback records per 100 there are 3 non23 and 2 retransmitted 23; in the 80% case, 10 and 10 respectively. This study does NOT identify real TLS Finished, classify live packets, parse TCP sequences or validate true TLS application data.

The independent per-record implicit counter is NOT WBD PN. AES nonce is derived from that counter, with outer header, selector and counter bound as AES AAD; this applies to AES records only. The trailing selector is generated deterministically as a function of the same counter. Codepoint regions 0000 to EFFF select fast while F000 to FFFF select AES. Each transmitted record optionally XORs the LAST EIGHT BITS (one byte = low selector byte) or, in a separately tested alternative, the last EIGHT BYTES. Rolling formula is public; neither protects nor authenticates fast data.

## Native five-replicate benchmarks

Go native GOMAXPROCS=1, all scratch buffers preallocated, 100 packets per benchmark iteration, each 1345B, full encode AND decode with corresponding mode, five 1-second benchmark replicates per mode, zero B/op, zero heap allocations/op.

| Case | x86_64 ns/100 | ARM64 ns/100 |
|---|---:|---:|
| 99% fast, no tail XOR | 5023.4 | 9045.8 |
| 99% fast, rolling final 8 BITS | **5384.4** | **9430.2** |
| 99% fast, rolling final 8 BYTES | 6031.0 | 10143.6 |
| 95% fast, rolling final 8 bits | 8133.8 | 12782.2 |
| 80% fast, rolling final 8 bits | 18310.2 | 25299.0 |
| 100% AES-GCM, same trailer and rolling final 8 bits | 72055.0 | 91563.4 |
| Previous optimized full-body PN-XOR, independent comparison | 15203.6 | 24391.8 |

For 99% fast hybrid:
- x86: 2.824x faster than the previous optimized full-PN-XOR control measured within this run; 13.38x faster than 100% AES.
- ARM: 2.586x faster than previous full XOR control; 9.71x faster than 100% AES.
- Incremental final 8-bit rolling XOR cost compared with identical no-tail-XOR hybrid: +3.610ns/record x86 (+7.19% relative to no-XOR), +3.844ns/record ARM (+4.25%).
- Changing the XOR from last 1 BYTE to last 8 BYTES costs an additional +12.01% x86 and +7.57% ARM.
- Mean wire overhead, per original packet: 99% fast +7.16B; 95% fast +7.8B; 80% fast +10.2B; all-AES +23B.
- No claims of WBD full-process throughput, real Rust record performance or real-world TLS classification are supported.

Original raw native measurements (nanoseconds per 100 packets):
x86 noxor99 5125,4995,4999,5006,4992; tail1 99 5384,5381,5389,5389,5379; tail8 99 6021,6024,6016,6039,6055; 95% 8092,8084,8083,8094,8316; 80% 18166,18741,18276,18193,18175; allAES 71965,72121,72127,72017,72045; oldFullXOR 15107,15233,15445,15125,15108.
ARM noxor99 9069,9035,9048,9038,9039; tail1 99 9417,9454,9432,9428,9420; tail8 99 10153,10141,10135,10157,10132; 95% 12795,12787,12786,12781,12762; 80% 25314,25297,25288,25291,25305; allAES 91526,91581,91574,91560,91576; oldFullXOR 24346,24395,24400,24400,24418.

## Important integrity and fingerprint caveats

1. The 17 03 03 prefix makes a packet TLS-like, NOT TLS 1.3 compliant. RFC 8446 TLSCiphertext requires a negotiated authenticated AEAD key and ciphertext body, not arbitrary framed data.
2. The fast path contains original unchanged TLS-23 record bytes immediately after the outer 5B header, producing a fixed visible nested 17 03 03 at position 5. This is a conspicuous signature; a normal TLS 1.3 outer record would carry AEAD ciphertext here.
3. The XOR covers only the low selector byte in the user-requested last-eight-bits interpretation. The high selector byte remains exposed and distinguishes F0-FF AES from 00-EF fast. This is an explicit mode fingerprint. Even the 8-byte option does not solve nested TLS header or unauthenticated fast data.
4. The 16B AES-GCM tag makes fallback packets 16 bytes longer than fast packets for equal 1345B inner inputs, a potential length-distribution signature.
5. Fast path is unencrypted by WBD and unauthenticated. A public rolling XOR byte plus publicly computable marker cannot prevent tampering or replay. AES provides integrity ONLY to fallback branch.
6. Both sender and receiver rely on an implicit strictly synchronized independent record counter. Loss, stream reordering, retransmissions, reconnects and actual TCP segmentation are not solved. TLS content-type byte 23 alone cannot prove Finished or that every packet is independently a TLS record.

## Evidence

Go source: tools/lan_tail_marker_rolling8_test.go. Strict parser: tools/lan_tail_marker_analyze.py. Correctness suite passed on real native x86_64 and ARM64: original and retransmitted TLS 23, non23 fallback, AEAD restoration, trailing one-byte/eight-byte masking, tamper and nested visible 23 signature. All seven performance modes had five Go benchmark measurements and PASS.

x86 native GitHub Actions run 40265434221, job 121386698063, raw artifact 12626381687.
ARM native run 40265437976, job 121386710006, raw artifact 12625369332.
Both initial workflow conclusions were FAILURE only because the analyzer script had not yet been committed in those triggering workflow revisions; their Go unit tests and all benchmark outputs independently PASS. Archived raw artifacts were independently downloaded, parsed and validated on CI run 40265674143, SUCCESS. This reanalysis does not fabricate or rerun native measurements.

Disposition: experimental data only; no merge to WBD main or security claim. The CPU optimization is promising for a truly high and accurately classified fast-path fraction, but this exact protocol proposal has conspicuous wire fingerprints and lacks integrity for fast records.
