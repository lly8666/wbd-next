# Follow-up: REAL mutual TLS 1.3 handshake, then raw XOR steady records

**2026-10-25 isolated capture PASS; WBD PRODUCT NOT WIRED, INSECURE DATA.**

[Actions run 40173451200](https://github.com/lly8666/wbd-next/actions/runs/40173451200), attempt 1, job 121109016325, SUCCESS. Precise tested SOURCE 00e7138177058c1d4286eb867983af5afb6ba98d. Evidence artifact 12591700086 (ZIP SHA256 d0874c344095201c5c204a428802a0afb9e48b622c49a0fa1c2b544d3e264876).

See also [first standalone TCP experiment](REPORT.md), [first Actions run 40173004832](https://github.com/lly8666/wbd-next/actions/runs/40173004832).

## What was actually run

- A newly written Go standalone loopback fixture (tools/lan_xor_tlslike_tls_handoff.go) creates an ephemeral TLS 1.3 client/server certificate and trust root **in memory**, verifies **both endpoints**, and completes both Go crypto/tls.Handshake calls. TLS 1.3 session tickets are disabled for this fixture.
- After the completed real TLS handshake, both test endpoints deliberately unwrap tls.Conn.NetConn() and send/receive **raw TCP bytes**, encoding the same **complete synthetic original 1345B IPv4/TCP packet** four times as four 1360B records with TLS-like 17 03 03 headers. Test order: fixed XOR twice, PN 0 and 1; packet-local rolling XOR twice, PN 2 and 3. Peers independently reverse the mask and assert byte-for-byte IPv4 restoration.
- The independent bounded parser tools/lan_xor_tlslike_tls13_pcap.py reconstructs the **actual captured** Linux TCP stream by outer sequence positions and parses TLS records, checks initial real handshake-stage records precede precisely four steady records.
- Original WBD Go cold connection, exporter keys, Rust data path and TUN are **NOT** involved. This fixture is NOT a production-ready handshake-to-XOR integration.

## Verified TCP capture receipt

| Evidence item | Real result |
|---|---|
| Client direction TLS records preceding steady state | **5**, including initial type 0x16 handshake and encrypted handshake |
| New steady TLS-like application_data records | **4**, each 1360B and beginning 17 03 03 |
| Distinct outer TCP Seq record start positions | YES, all 4 |
| Outer captured TCP payload segments | **6** |
| Same outer TCP Seq duplicate retransmit segments | **0** |
| Fixed XOR on identical IPv4 packet at different outer positions | repeated continuous **64B and 128B** |
| Rolling XOR on identical IPv4 packet at different outer positions | **no** repeat in either 64B or 128B checked windows |
| Receiver reconstruction of each original IPv4 packet | PASS, all 4 |

Raw pcap **8354B**, SHA256 **76078bd86a100a93ad3f3559e51fc9f120c35db66975d2402a6a2dda9df9709f**. Owned pcap cleaned at Action exit, summary/manifest/binary digest retained in artifact only. No certificate, key or raw trace committed.

## Important qualification

A genuine authenticated TLS 1.3 handshake before this data **does not make the subsequent XOR records real TLS traffic**. They no longer pass through the TLS record AEAD keys and cannot be decrypted by a regular peer using the outer TLS session. The rolling mask is intentionally noncryptographic and reproducible from known plaintext/packet numbers. No data confidentiality, integrity, replay protection, anti-downgrade, spoofing resistance or network fingerprint indistinguishability is established; payload tampering and replay are accepted by the laboratory codec.

**NOT_TESTED:** WBD authentic Go->Rust->TUN after cold admission; proper capability negotiation, generation/Stop/replay admission, real inner kernel retransmit, production MTU, Linux ARM/Android/Windows portability, whole-app throughput/CPU, p99/queue/drop and any adversarial classifier. No claim of CPU savings or main branch readiness.

Conclusion: **real TLS1.3 handshake -> fake-TLS-header XOR steady-state sequencing is technically demonstrated in a bounded local fixture**; full WBD product implementation and network security qualification remain open outside this scoped experiment.
