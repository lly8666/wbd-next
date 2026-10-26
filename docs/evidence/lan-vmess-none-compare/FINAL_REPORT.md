# VMess security=none versus WBD improved public PN-XOR: native minimum test

Status: **COMPLETE, native x86_64 and ARM64 tests SUCCESS**. Isolated experiment branch, main untouched, production not wired. Based on experiment/lan-hp-mode-cost SHA 22a27057d685b3391c683f802c1d0cfec559b49d.

## What VMess actually does

Based on pinned upstream V2Fly v2ray-core master:
- proxy/vmess/encoding/auth.go blob 12ed3758ca2bf322cc3bf61bd97a4238ec041aed: SHAKE128 state seeded by 16-byte request or response body IV; chunk length is two-byte Big-Endian true length XOR next two SHAKE bytes. Optional padding generator is next SHAKE uint16 modulo 64.
- proxy/vmess/encoding/client.go: for TCP stream and SecurityType_NONE, NewChunkStreamWriter carries unchanged plaintext body and only length framing. It does not apply the optional padding generator in that stream branch.
- proxy/vmess/outbound/outbound.go blob a0463c83eb8ecf44ebbaa9d0b298c70754bfcbd0: default NONE turns on chunk length masking; ZERO turns OFF chunk framing and masking; default shouldEnablePadding(NONE) is false. Header authentication/encryption exists separately and is excluded by the steady-only test.

VMess NONE masks **length only**, NOT payload bytes. VMess ZERO just copies raw payload. Neither supplies protected business payload contents. WBD public PN-XOR touches every original payload byte but remains publicly invertible, unauthenticated and replayable.

## Experiment design

Pure Go, no V2Ray runtime dependency, but protocol data-plane operations are reproduced from the pinned upstream source and crosschecked with a SHAKE128 known-answer vector for IV 000102030405060708090a0b0c0d0e0f (first 6 SHAKE bytes 98481946de85). Exactly 1,345 original inner IPv4/TCP + TLS1.3-shaped payload bytes (synthetic test data, not real negotiated TLS), 100 packets per benchmark cycle, encode AND decode same packet, TX/RX scratch preallocated, Go GOMAXPROCS1, same compiler/version per architecture, five repetitions per mode.

Modes:
1. VMess ZERO raw bytes with 0B steady record overhead.
2. VMess NONE no length mask lower bound: 2B length + plaintext.
3. VMess NONE default SHAKE128: 2B XOR-masked length + plaintext. Independent continuing SHAKE state for TX and RX, no XOF reinitialize per chunk.
4. WBD original lab PN-XOR: 5B TLS-like outer + 1B clear mode + 8B PN + 1B kind + 1345B publicly masked body; +15B per original input.
5. WBD improved hidden-mode public PN-XOR: 5B TLS-like outer + 8B AES128 protected PN/mode + 1B kind + 1345B publicly masked body; +14B per original input. Header protection AES128 block once TX and once RX.

All five modes passed 1,000 full-byte roundtrip test iterations, including independent SHAKE known-answer test, direct wire-exposure assertions, and no Go heap allocations/allocated bytes during the benchmark cycles.

## Native measured performance, mean of 5 per mode

Wall nanoseconds to encode + decode 100 original packets (lower is faster):

| Mode | x86_64 ns/100 | ARM64 ns/100 | Wire overhead/packet |
|---|---:|---:|---:|
| VMess ZERO | 2,831.2 | 7,704.0 | 0 B |
| VMess NONE plain length | 3,312.2 | 7,940.0 | 2 B |
| **VMess NONE SHAKE128 default** | **5,246.4** | **10,533.0** | **2 B** |
| WBD clear PN-XOR | 25,077.8 | 35,181.8 | 15 B |
| **WBD improved hidden PN-XOR** | **26,481.0** | **37,659.2** | **14 B** |

WBD hidden mode costs **5.0475 times** VMess SHAKE NONE elapsed time on x86_64 (an extra 212.346ns per original packet across sender+receiver) and **3.5754 times** on ARM64 (an extra 271.262ns/packet). Compared to WBD clear-mode baseline, adding hidden PN mode costs approximately +5.60% x86 and +7.04% ARM in this separate measured implementation. Differences arise primarily because VMess never touches payload bytes for encryption, while WBD masked entire ~1345B twice.

Raw ns/100-packet cycles:
- x86 Zero [2857,2773,2846,2890,2790]; NONE clear length [3254,3367,3345,3293,3302]; NONE SHAKE [5274,5165,5207,5273,5313]; WBD clear [25142,24964,25184,24824,25275]; WBD hidden [26823,26457,25743,26349,27033].
- ARM Zero [7691,7694,7714,7694,7727]; NONE clear length [7921,7943,7977,7931,7928]; NONE SHAKE [10516,10520,10550,10505,10574]; WBD clear [35185,35153,35202,35234,35135]; WBD hidden [37835,37665,37628,37571,37597].

## Limitations and safety

This is NOT a benchmark of full VMess client/server, TLS authentication, network throughput, Linux raw sockets, complete WBD Rust record crypto, FEC or a live TLS1.3 classifier. It measures a carefully matched, minimal, Go steady business-data pipeline. The protection levels are different: VMess NONE allows exact recovery of the original inner IPv4/TCP header and every plaintext application byte without any inversion; WBD PN-XOR obscures literal bytes on wire but any observer can undo the public PN XOR, forge data or replay. Hidden PN does not protect or authenticate XOR payload. Do not claim direct whole-program CPU, complete wire compatibility, improved security or detectable traffic similarity from these measurements.

Provenance: native x86_64 GitHub Actions **SUCCESS** run 40257276765, job 121361723383, artifact 12622907753. Native ARM64 **SUCCESS** run 40257280780, job 121361735323, artifact 12622483653. Reproducer tools/lan_vmess_none_vs_wbd_test.go and tools/lan_vmess_none_vs_wbd_analyze.py. Main unchanged, no production merge.
