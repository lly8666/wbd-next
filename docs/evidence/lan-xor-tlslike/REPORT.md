# LAN XOR / rolling-mask TLS-like frame — isolated capture report (2026-10-25)

## Decision and tested source

**BOUNDED_LAB_PASS / NOT_WBD_PRODUCT_WIRED / INSECURE_OBFUSCATION_ONLY.**

New LAN experiment on experiment/lan-xor-tlslike, based on prior selective-AAD experiment closure ca72b345de5846a5c58f28d6be24b4e2fcd057b1. Does not reopen its negative status, change main, the authenticated production record, Go bootstrap, configuration or deployment.

**Native Action [40173004832](https://github.com/lly8666/wbd-next/actions/runs/40173004832)**, attempt 1, job 121107650547, Ubuntu 24.04 x86_64, Rust 1.85.1, exact tested SOURCE **f914b396d3251978bc11c9899e385c7bcac1ebe6**: **SUCCESS, 5 passed / 0 failed / 0 ignored**. Artifact 12591221570, ZIP SHA-256 cad4e7ceecda9ef9dd37c4ac1e839b766b55422d7e497ed889cd7c0b41e6661c.

## What was implemented

- Standalone Rust lab: tools/lan_xor_tlslike_lab.rs; independent bounded PCAP parser: tools/lan_xor_tlslike_pcap.py; CI: .github/workflows/lan-xor-tlslike-capture.yml.
- One complete synthetic original IPv4/TCP packet becomes one TLS-like application_data framed record: 5-byte 17 03 03 + big-endian body length, 8-byte clear lab PN, 2-byte XOR-masked inner length, whole XOR-masked inner IPv4 packet. **15 bytes** overhead per packet, 1345B original -> **1360B wire**. This is not an RFC TLS ciphertext record, and it does not carry a normal TLS AEAD tag.
- Fixed XOR mode: 0xa5 across inner-length field and original IPv4 bytes. Rolling XOR mode: packet-local noncryptographic SplitMix/xorshift64* sequence using demonstration seed and changing outer PN. The mode is selected by known fixture order out of band. No production negotiated capability, no cryptographic strength, no authenticated key or secret: the hardcoded seed is **public fixture data**, and even hiding it would not confer security.
- Linux establishes an actual loopback TCP socket before the 4 records are sent. **No actual Go TLS authenticated bootstrap or TLS handshake in this Action**. This is not WBD full Go -> Rust -> TUN traffic.

## Actual native functional tests

Rust unit tests **5/5 PASS**:
1. Both modes encode and decode exactly, correct 17 03 03 header and record lengths.
2. Same full inner packet under different outer PNs: fixed XOR repeats 128B; rolling XOR differs over the checked 64B and 128B windows.
3. Invalid frame type/length and truncated IP are rejected structurally.
4. Malicious XOR modification of a payload byte **still produces accepted modified output**: deliberately demonstrates the lack of integrity.
5. Exactly the same record can be decoded repeatedly: deliberately demonstrates the lack of replay protection.

A PASS on (4) or (5) is a *negative security finding*, not security qualification.

## Bounded actual native TCP capture

The Action recorded real Linux tcpdump loopback TCP traffic, then independently reconstructed the original TCP byte stream by outer sequence offsets and framed all records without relying on the Rust encoder's own report.

| Observation | Fixed XOR pair | Rolling XOR pair |
|---|---|---|
| Two new records at different outer TCP Seq | YES | YES |
| 17 03 03 header, valid stated record length | YES | YES |
| 1360B for each 1345B input IPv4 packet | YES | YES |
| Same consecutive 64B in payload region | **YES** | **NO** |
| Same consecutive 128B in payload region | **YES** | **NO** |
| Encoded packet round-trip restored | YES | YES |

Capture: **4 outer TCP payload segments**, **4 reconstructed complete records**, **0 same-outer-Seq retransmit segments**. Outer lab PNs 0, 1, 2, 3. Exact 8-byte synthetic IP-address canary not found in visible outer TCP stream. The inner packet is a **constructed same-IP-sequence fixture**, not independently observed kernel inner TCP retransmission.

Owned raw pcap: **6128 bytes**, SHA-256 **4cb2dacea41088e6fcce1a3a3128e4de369d4e06e5b3ffccca1f21de1f471174**. Raw pcap was cleaned at Action exit; summary/manifest/binary digest retained in artifact 12591221570. No user packet payload, test secret or real certificate committed.

## Limitations, disposition

**NOT_TESTED:** real Go TLS handshake/cold authenticated admission; post-bootstrap mode switch; product capability/downgrade policy; epoch/direction/replay/Stop; Rust product ABI and TUN/raw first delivery; native kernel inner TCP retransmission; ARM64/Windows/Android; end-to-end CPU, throughput, PPS, p99, queue/drop; TLS equivalence and classification resistance. **No CPU savings claimed** from this functional/capture Action.

**Fixed XOR** predictably leaks repeated body bytes. **Rolling XOR** removes the narrow measured direct repeated-body pattern under different outer packet numbers, but it is still simple reversible obfuscation: **no confidentiality, data authenticity, anti-replay or traffic-analysis guarantee**. Real standard TLS endpoints would not decrypt these records, and a sophisticated observer can distinguish the format. Header resemblance is not TLS protocol equivalence.

This is intentionally only a standalone LAN experiment, **not production merge-ready**. Replacing WBD's authenticated AEAD would violate existing integrity and replay admission gates without an explicit separately designed and authorized policy. No modifications to main or upstream network/FEC jobs. Do not reinterpret this as a successful full product test.
