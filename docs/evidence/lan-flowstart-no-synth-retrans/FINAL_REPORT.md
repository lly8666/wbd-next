# Flow-start 11–21s randomized gate and removal of synthetic handshake retransmissions

Date: 2026-10-25. Scoped isolated branch experiment/lan-flowstart-no-synth-retrans; derived from passed experiment/lan-gated-boundary-pad SHA a992565780c85bb1dad2fa9d8f939ff0e63989f4. Product, WBD main, existing outer borrowed-domain TLS startup, and Go→Rust→TUN path unchanged.

## Status

**COMPLETE_SCOPED_NATIVE_X86_ARM_A_B_PCAP_AND_GO_PERF_PASS; NOT PRODUCTION; REAL CLASSIFIER / SECURE MODE ADMISSION UNSOLVED.**

One random deadline 11,000–21,000 milliseconds per INNER TCP flow, starting when its initial TCP SYN packet is dispatched into this test tunnel. All pre-deadline traffic continues through AES; no user traffic is delayed. Fast PN-XOR requires that BOTH the clock has passed AND genuine TLS1.3 Finished is observed AND original sender TCP sequence range is beyond the protected handshake boundary AND a trusted offline test label attests inner application ciphertext. Time alone never permits XOR. Old TCP seq retransmissions remain AES if they actually occur.

In A, two deliberately created synthetic ClientHello repeats are sent (once at startup, once after fast-stage eligibility). In B, exactly those two ARTIFICIAL packets are omitted. The Linux operating system's real TCP retransmission is NOT disabled and must NOT be disabled, because retransmission provides TCP reliability. The unit suite tests that an old ClientHello TCP sequence is rejected from XOR even after hold expiry.

All marked connection lifecycle packets are AES-GCM with random 0–256B trailing content authenticated inside the outer AEAD record. Unknown and ordinary AES packets and every PN-XOR fast packet get exactly zero fill. An at-capacity lifecycle packet gets no extra padding. Dynamic MTU is unsolved for production; this IPv4 experiment reserves worst-case 80B outer IPv4+TCP header; forces Linux loopback MTU1500, tries disabling GSO/GRO/TSO and clamps owned TCP MSS1200. Independent offline pcap parser asserts actual IPv4 TotalLength <= 1500 and no IPv4 fragmentation, not just record size.

## Native actual loopback TCP capture A/B

Both platforms establish genuine mutual-authenticated TLS1.3 on outer TCP, then intentionally use a raw TCP TLS-looking custom AES/XOR record stream, which is NOT an RFC TLS1.3 application ciphertext data channel. The offline inner packet corpus has an actual ephemeral OpenSSL TLS1.3 ClientHello with publicly identifiable test SNI+ALPN, ServerHello, compatibility CCS (when present), encrypted client Finished and decrypt-tested real TLS1.3 application ciphertext. It is a trusted-test-oracle classifier, NOT a deployed TLS DPI. The post-bootstrap Go AES-128-GCM fallback on-wire record differs from the real WBD Rust AES wire implementation.

| Native machine | A: 2 injected repeats | B: no injected repeats | maximum actual IPv4 packet size |
|---|---|---|---|
| x86_64 | 28 records = 23 AES, 5 XOR; 13 lifecycle padded; 14 ordinary/fast unpadded; 1 full-MTU lifecycle unpadded | 26 records = 21 AES, 5 XOR; 11 lifecycle padded; 14 ordinary/fast unpadded; 1 full-MTU lifecycle unpadded | 1500B in both captures |
| ARM64 | 28 records = 23 AES, 5 XOR; 13 lifecycle padded; 14 ordinary/fast unpadded; 1 full-MTU lifecycle unpadded | 26 records = 21 AES, 5 XOR; 11 lifecycle padded; 14 ordinary/fast unpadded; 1 full-MTU lifecycle unpadded | 1500B in both captures |

Both no-synthetic-repeat captures retain normal TLS ClientHello / ServerHello / Finished fully authenticated and AES encrypted; fast packet mode bytes are 1 and permitted AES mode bytes 0. Test SNI absent from entire recovered OUTER TCP stream, AES tamper fails, native server recovers all original inner packets and strips authenticated padding; public PN-XOR bytes are trivially reversible; unknown packet types, pure TCP ACK, middle data all confirmed UNPADDED. Independently audited capture pcap timestamp from first inner SYN to first fast record:
- x86 A: **15741.141ms** (selected 15708ms); B: **15630.784ms** (selected 15598ms). Real Finished occurred at 109ms / 90ms since flow start.
- ARM A: **18766.913ms** (selected 18737ms); B: **14583.088ms** (selected 14550ms). Real Finished occurred at 110ms / 91ms since flow start.
Independent different random hold times are selected for each capture. No timer accuracy is required besides staying approximately 11–21s; no traffic waited for AES.

Two artificially transmitted repeat AES records consumed **1406B** in x86 A and **1439B** in ARM A including their independently randomized padding. Overall custom record stream lengths were x86 A17900B, B16337B; ARM A17651B, B16389B. Whole-capture byte-length differences are NOT identical to duplicate-frame lengths because independent random padding varies on unrelated lifecycle packets.

Provenance:
- x86 native SUCCESS [GitHub Actions run 40192615875](https://github.com/lly8666/wbd-next/actions/runs/40192615875), job 121166657682, exact source SHA 8e8ad79abf8e931d0c20509d24294b53e9b70ab3; artifact ID 12598895626; uploaded ZIP SHA256 ea0eb6d5b05bdc43e4b1e4657c1437c91ac5b96fb83405af33c731d9d97e6ab3.
- ARM native SUCCESS [GitHub Actions run 40192618992](https://github.com/lly8666/wbd-next/actions/runs/40192618992), job 121166667161, source SHA fe02d035ddd65cfdceddf84f7a5756822e821767; artifact ID 12598806919; uploaded ZIP SHA256 07b5da59f36bd297dd8e5494712c95d1be078720b1a591af5f4cce756a99a38c.
- Every job completed 6/6 new/old native Go unit tests, two actual independent TCP capture policy/MTU audits, three Go benchmark replicates for each of two modes. Raw capture and ephemeral keys/ciphertext corpus deleted; reports retain only hashes, classification metadata, pcap summaries and benchmarks.

## Native Go same-host performance A/B: controlled 1 ClientHello + 99 fast packets per connection

One cycle: genuine-length-matched original inner IPv4 ClientHello-size packet (40+517=557 bytes), then 99 1345B fast inner TLS record payloads, with (A) or without (B) 2 extra 557B copies. CPU-ish metric is Go ns/op elapsed BENCHMARK WALL TIME per cycle and includes Go seal, open, random padding, allocations, copies. Three two-second measurements each native host, not full WBD/TUN or Linux schedstat thread CPU. Actual pcap tests separately used genuine OpenSSL-sourced inner TLS bytes; microbench CH bytes are synthetic length-matched, not full TLS parse.

| Architecture | A mean ns/flow-cycle | B mean ns/flow-cycle | measured reduction | approximate Go heap saved/flow | allocations saved |
|---|---:|---:|---:|---:|---:|
| x86_64 | 65566.3 | 64624.3 | **1.44%** | 4567B | 10 |
| ARM64 | 124744 | 122476 | **1.82%** | 4563B | 10 |

Raw ns/cycle:
- x86 A [62288,64988,69423], B [64013,64164,65696].
- ARM A [124059,125834,124339], B [122628,122409,122391].
Variation, especially among x86 samples, makes ~1%–2% a weak estimate rather than guaranteed production speedup. Removing artificial resend from a normal connection that never produces such artificial packets saves nothing, so this is test-fixture cleanup and not a replacement for kernel TCP loss recovery.

## How mode detection should work

This LAB record format is fixed-width: TLS-looking 5-byte header | 1-byte explicit mode (0 = AES-GCM authenticated FULL, 1 = unprotected/public PN-XOR fast) | 8-byte public packet number | chosen encrypted/masked body. Receiver switches to a decoder by the explicit field in O(1), **not** by payload size, entropy, guessing TLS 0x17 03 03 or trying both decryptors. Unknown modes are rejected. Real AES-GCM authenticates the prefix as AAD (and binds PN into nonce), so changing AES mode/PN/ciphertext fails; the unit negative-test checks this. The Go receiving test harness knows the expected mode via out-of-band original Spec: it rejects a mismatch. This is **not** a production trusted mode-admission design.

Public PN-XOR has **no integrity, origin authentication, secrecy or anti-replay**. Any observer can recover original inner IPv4 packet and any attacker can corrupt or forge an XOR data frame. A secure product must install flow-specific fast-mode permission through an AEAD-authenticated control/negotiation, track direction, original TCP sequence safe range and epoch, default unknown to AES; to prevent forged fast data/replay it needs a keyed MAC or real AEAD per-record. A mere clear mode flag does not safely grant authorization. TLS1.3 encrypted handshake/application/alert may share the same outer 17 03 03 type and size, and cannot be reliably classified just from TCP packet size.

## Additional optimization priorities

- **No per-packet timers or RNG on steady traffic**: keep one random hold deadline, a per-flow trusted boolean and direction-specific TCP byte boundary; lazy deadline compare during existing flow lookup. Avoid sleeping user-data senders while waiting; the sleep in this controlled capture generator exists only to exercise the post-deadline sample.
- **No real retransmission disable**: avoid intentional application duplicate sends, preserve kernel TCP loss recovery; when any genuine old handshake TCP seq retransmission arrives, keep full AES fallback. Reuse classification decisions in bounded flow cache, not repeated TLS parsing on steady packets.
- **Padding only for explicitly known lifecycle packets**: max 256B, bounded by IPv4/TCP/options/path MTU with no fragmentation; ordinary ACK, middle TCP and UDP, and fast XOR send zero fill. The test Go code still allocates ~302–312 heap objects per cycle and ~420KiB allocated bytes, suggesting pooled buffers/zero-copy as a potential separate optimization, NOT yet benchmarked in the real WBD Rust data path.
- **Fast mode cannot be enabled simply by random age**: require trustworthy inner TLS1.3 completion and byte safe range; incomplete TLS parser/flow/protocol => AES. Production classifier and control-message mode authentication remain unimplemented.
- Timing and length randomization do not conceal packet counts, IP addresses, timing, overall TLS use or clear mode header. The PN-XOR leg is reversible and unsecured. No verified end-to-end application throughput, loss/RTT, kernel inner TCP retransmit policy, full WBD CPU, p99 or protocol security.

**Disposition: isolated lab complete, main unmodified, not merge-ready.**
