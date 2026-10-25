# Hidden mode bit inside existing 8B PN: x86_64 and ARM64 minimal Go A/B

Date 2026-10-25. Isolated branch experiment/lan-hp-mode-cost; base experiment/lan-flowstart-no-synth-retrans SHA 1accc0fb65a1bf42edeee1d22b52e10ae3844033. main untouched. This is an independent Go experiment, not WBD Rust production integrated.

## Decision

**COMPLETE_SCOPED_NATIVE_SIX_REPLICATES_EACH_X86_ARM; ZERO_PER_PACKET_HEAP_ALLOCS; NOT PRODUCTION.**

One TLS-like 5B prefix 17 03 03 | length, original lab encoding:
5B header | clear 1B mode (0=Go AES128-GCM, 1=public PN-XOR) | clear 8B PN | body.

Proposed encoding:
5B header | 8B AES-128-header-protected (top 1bit mode + 63bit monotonically unique PN) | body.
No extra exposed mode byte; one less byte of outer record. On TX, seal or mask the body first, derive an AES128 block mask from the first 16 bytes of post-seal/post-XOR body using **independent test HP key**, xor that with the 8B mode/PN combined word. RX derives the identical mask from the first 16B body, unmasks once, branches to AES or XOR only once. AES authenticates the original UNMASKED combined mode/PN field and outer length/type as AAD, and uses that PN for AEAD nonce. Per-lane scratch for HP AES block, AAD, nonce is reused; no new per-packet allocation. 63-bit PN range is not a full-64-bit existing-WBD-wire-compatible drop-in. Decoder and sender must agree on modified record format, key derivation, PN range, and authenticated mode admissions; none of these negotiated/product aspects was implemented in this test.

All tests used 1345-byte synthetic original IPv4/TCP packet with an opaque TLS1.3-shaped payload, **not a freshly negotiated TLS13 flow**. Offline test oracle explicitly chooses 99 XOR and 1 full Go AES record per repeating 100 packets; other controls all AES or all XOR. Both benchmark classes seal AND open, copy plaintext only into pre-allocated data slabs; no network, no TUN, no FEC, no classifier or full WBD process CPU. The HP primitive is a single AES128 block encryption on each TX and RX; Go standard library cipher implementation runs on the actual native CPU. GOMAXPROCS1, six 1-second Go benchmark reps per mode, Go wall nanoseconds/op for a 100-original-packet cycle, not schedstat CPU time.

Native source:
- tools/lan_hp_mode_cost_test.go, including tests TestMaskedModeBothDirections, TestMaskedModeAesTamperAndXorIsUnauthenticated, TestSingleCipherBlockMaskAndNoPlainMode and eight benchmarks.
- tools/lan_hp_mode_cost_analyze.py independent strict audit expecting exactly six samples per 8 benchmark modes.
- GitHub Actions native x86 actual runner [run 40200548326](https://github.com/lly8666/wbd-next/actions/runs/40200548326) and ARM native [run 40200552303](https://github.com/lly8666/wbd-next/actions/runs/40200552303). Both Go correctness tests passed and all 48 native benchmark measurements successfully printed and archived in artifacts **12601238990** (x86) and **12601177583** (ARM). These runs subsequently showed **FAILURE IN PYTHON REPORTER SYNTAX ONLY**, not in Go test or timed microbenchmark.
- The archived unchanged raw benchmark artifacts were re-downloaded and successfully validated by a separate [native-data artifact audit Action 40200979162](https://github.com/lly8666/wbd-next/actions/runs/40200979162) (SUCCESS), artifact **12601354511**, ZIP SHA256 **0a6e42084dd0f35809f5976578afc17de5bf4ea0fe83258e4de61fcaab7f33b9**. This is an x86-host analyzer of measurements originally executed on the native x86 and ARM machines, not an ARM test re-run.

## CPU microbenchmark result (mean of 6; lower is faster)

Nanoseconds per 100 original 1345B inner packets, encode + decode, preallocated reusable buffers:

| Profile | x86 old clear mode | x86 hidden mode | x86 change | ARM old clear mode | ARM hidden mode | ARM change |
|---|---:|---:|---:|---:|---:|---:|
| 99% PN-XOR + 1% real AES-GCM | 36,201.00 ns | 34,066.33 ns | **-5.90%** | 37,034.17 ns | 39,678.00 ns | **+7.14%** |
| 100% AES-GCM | 58,270.83 ns | 58,366.67 ns | +0.16% | 86,752.67 ns | 85,811.67 ns | -1.08% |
| 100% public PN-XOR | 36,015.33 ns | 33,527.83 ns | -6.91% | 36,495.67 ns | 39,075.83 ns | +7.07% |

All 8 benchmark modes, 6 replicates each: **zero Go heap B/op and zero Go allocations/op** after optimized per-lane scratch reuse. Per-read mode overhead alone (no payload seal or open) was:
- x86 old 0.4883 ns vs protected 6.3777 ns; extra **5.8894 ns per record**.
- ARM old 0.76745 ns vs protected 10.320 ns; extra **9.55255 ns per record**.

Do **not** conclude that adding AES header protection inherently accelerates XOR from the x86 negative delta. This Go code changes record offsets/layout from 14B to 13B, memory alignment and compiler scheduling; a 6-replicate same-run comparison shows a measured outcome, not causality/architecture-invariant guarantee. Crucially, the header protection AES encrypt runs once on TX and once on RX for each record, even though the measured whole operation sometimes appears faster due to other differences. Actual incremental cost on ARM 99% traffic is around +26.44 ns per original packet across the full send+receive pass, i.e. +7.14% for this specific Go fixture. No native production Rust WBD record CPU or whole program latency was measured.

## Security and protocol caveats

- Header protection hides the explicit mode bit from casual inspection, but **is not an authenticator**. Bit flipping a protected header field is possible; a receiver must be sure via independent authenticated fast-mode admission that XOR records are allowed. Go bench tests both modes with an offline oracle; no live mode admission was designed.
- **Pure PN-XOR remains fully public, invertible, malleable and replayable**. This experiment intentionally does not implement packet payload prefix encryption, replay handling or MAC, and does not prove passive traffic indistinguishability from genuine TLS1.3, let alone confidential IP/TCP headers.
- AES header mode and packet number are bound to the AES AEAD AAD; altering protected AES PN or tag fails authenticated open. XOR deliberately allows altered ciphertext (test confirms vulnerability).
- Changing from a clear 1B mode + 8B PN to an 8B protected combined word reduces each test record by **1 byte**, but its 16B AES-GCM tag when AES and lack of tag when XOR still cause a measurable size difference (assuming known original payload sizes).
- A test key is statically fixed and independent of application keys; actual production HP key material must be securely KDF-derived from authenticated session keys and bound to direction and epoch. Don't reuse AES-GCM payload AEAD key as HP key.
- The last 63 bits PN allocation no wrap, mixed record format and real Go→Rust owner lifecycle have no product implementation. Avoid treating bench result as merge- or deployment-ready.

## Disposition

**Keep only on isolated experiment branch. Main untouched. No production fast-mode authorization, no full secure tunnel claim, no changes to outer borrowed-domain bootstrap.**
