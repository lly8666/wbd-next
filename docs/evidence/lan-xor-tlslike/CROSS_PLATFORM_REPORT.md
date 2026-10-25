# LAN XOR TLS-like experiment — cross-platform audit and honest closure (2026-10-25)

All observed evidence is on the isolated experiment/lan-xor-tlslike branch; existing negative selective-AAD experiment status, main, network/FEC cursors, Go/Rust production codec, CLI and devices unchanged.

## Full run ledger — preserve failure, no seed chasing

| Run | Frozen SOURCE | Host | Result | Precise meaning |
|---|---|---|---|---|
| [40173004832](https://github.com/lly8666/wbd-next/actions/runs/40173004832) | f914b396d3251978bc11c9899e385c7bcac1ebe6 | x86_64 | SUCCESS | 5/5 Rust unit; native TCP (no TLS handshake) 4 records, fixed repeats, rolling does not |
| [40173451200](https://github.com/lly8666/wbd-next/actions/runs/40173451200) | 00e7138177058c1d4286eb867983af5afb6ba98d | x86_64 | SUCCESS | Genuine Go mutual TLS1.3 handshake then raw XOR; independently captured 4 steady records |
| [40173618918](https://github.com/lly8666/wbd-next/actions/runs/40173618918) | e6d98d39d94abf20a0dedbdcd92987e5fda1502d | ARM64 | **FAIL** | 5/5 native Rust unit PASS; raw TLS handoff **broken pipe** in Go TCP write; **wire capture not qualified**. Job 121109547810. Artifact 12591750206 ZIP SHA afd795ea02c73ae5207f1de86502ebbda42f946f478f7b7bbc0c4fabecf2cd94 |
| [40173724240](https://github.com/lly8666/wbd-next/actions/runs/40173724240) | 28ce2f2c4bdbc1ee966593565631a976326fec98 | x86_64 | SUCCESS | Exact same bounded TLS/steady scenario after **explicit encrypted two-sided READY barrier** |
| [40173739049](https://github.com/lly8666/wbd-next/actions/runs/40173739049) | dcce18a418c55fed1a787d254fce5f97a3b421da | ARM64 | SUCCESS | Native ARM64 Rust 5/5 PASS + Go genuine TLS1.3 mutual handshake + rolling XOR real TCP capture PASS |

After the first ARM64 failure, the only functional fix was to exchange **C_READY and S_READY inside the authenticated TLS channel before either peer unwraps tls.Conn.NetConn()**. Prior handshake completion had not established a two-peer switch barrier; the first ARM64 run ended with broken pipe. The failure was preserved, not reclassified as PASS. No new XOR algorithm, mask seed, fixture TCP Seq, packet size or classification logic was introduced. One source-driven ARM64 rerun plus x86_64 paired native source check; no iterative seed search.

## Final exact positive capture receipts

**x86_64 fixed handshake barrier Action**: [40173724240](https://github.com/lly8666/wbd-next/actions/runs/40173724240), attempt 1, job 121109856012, artifact **12591042778**, ZIP SHA **4d1f93184cd0dee62f349a77dbae4aa923216b62be44bbb81ba2b7ff85cc6bee**. Pcap 8465B SHA **b63a92b160debbba42a974ea8a619263110ba59706eef0737079642bbfd2b3fe**. Capture saw 6 prior client TLS handshake-stage records (including encrypted C_READY exchange), 7 outer TCP payload segments, then 4 1360B new outer TLS-like records in distinct Seq positions. Fixed XOR same 64/128B; rolling XOR different 64/128B. Four inner IPv4 roundtrips PASS.

**native ARM64 fixed handshake barrier Action**: [40173739049](https://github.com/lly8666/wbd-next/actions/runs/40173739049), attempt 1, job 121109902166, artifact **12591416126**, ZIP SHA **c01dea791a3ee3ec2a7fa28a6ccd519cdc91fc3e99007b49f3bc6169f38a97c3**. Native Rust 5 passed / 0 failed / 0 ignored. Pcap **8301B**, SHA **3ad5e28786abb23bbe67fd08e599590c2ce875407d759708e8283997964135e3**. Capture saw **6 TLS handshake-stage records** followed by **4 new 1360B TLS-like steady records**, **7 TCP payload segments**, 0 outer same-Seq duplicates. Fixed XOR identical 64/128B; rolling XOR different 64/128B. Four 1345B synthetic IPv4 packets roundtripped. Source includes TLS READY fix; exact fixture, parser and Rust codec code unchanged.

All pcaps are owned bounded temporary recordings and were deleted at Action exit; only summary/digests and build receipts uploaded. The failure artifact is retained as an independent provenance receipt.

## Protocol and limits

- Standalone 5B 17 03 03 plus length, 8B CLEAR PN, 2B masked inner length and XOR-masked *whole* synthetic IPv4 packet. 15B overhead; no AEAD tag. Fixed XOR 0xa5 or noncryptographic rolling SplitMix/xorshift64* mask keyed by publicly known lab seed and PN.
- The Go fixture first mutually authenticates via **real TLS 1.3**, exchanges a switch barrier over authenticated TLS records, then sends the synthetic raw IPv4 fixture on underlying TCP. The resulting XOR data frames are **not RFC TLS records**, are **not protected by the TLS session**, and would fail standard TLS record authentication.
- The original IPv4 data is constructed fixture, not real raw/TUN product packets; no actual real kernel inner retransmission in these new tests. Notably, integrity tampering and replay are **explicitly demonstrably accepted** by the XOR lab codec. Avoid claims of secrecy, authenticity or anti-replay.
- NOT_TESTED: original WBD Go TLS admission and exporter identity, Rust product ABI, real TUN client/server, Stop/generation, semantic downgrade/replay, OS MTU, Windows/Android, production user opt-in or config, CPU and throughput/p99, live retransmission or real DPI indistinguishability.
- This experiment passes a **narrow on-wire bounded fixture** only. No product admission or performance claim; no merge to main. Previous full-AEAD remains untouched.

Scoped outcome: **native x86_64 + ARM64 lab pass after explicit secure switch barrier; no product qualification; deliberately insecure XOR mode remains standalone**. No pending experiment Actions or autonomous product-wiring request.
