# Scoped boundary-only padding and 11–21 second TLS1.3 fast-gate design

**Status:** lab-only proof of packet selection, MTU accounting, real TCP capture and per-100-packet microbenchmarks. This is **not wired into WBD's Go→Rust→TUN production path**.

## Scope

Keep WBD's borrowed-domain bootstrap unchanged. On a separate *inner* TLS1.3 TCP flow, protect all untrusted or unknown packets with AES-128-GCM. A trustworthy classifier and authenticated receive admission would be required to prove a packet carries only already-encrypted inner TLS1.3 steady payload; the experiments instead supply labels from a trusted offline test oracle. Only trusted packets that also pass port, TCP sequence and transport structural tests may use the deliberately public, reversible PN-XOR fast path.

After the **actual TLS1.3 client Finished flight** was observed on the outer test connection, draw a cryptographic random integer delay 11,000–21,000 ms **once per flow**. The connection still sends ordinary traffic over authenticated AES during this delay. Upon expiry, *eligible* new payload bytes can use PN-XOR. Earlier handshake byte ranges and later retransmissions carrying them remain AES **regardless of how long ago the handshake finished**. The timer is supplementary and not a security replacement for TCP source sequence boundaries, flow reassembly, or authenticated per-direction state. TLS1.3 compatibility ChangeCipherSpec, when present before encrypted client Finished, must be included in the protected packet.

## Padding rule

Only **recognized lifecycle boundary packets** may be randomly filled, including TCP SYN, SYN+ACK, FIN, RST, genuine TLS1.3 ClientHello/ServerHello/Finished source envelopes, and *test-oracle-labelled* QUIC Initial and ConnectionClose-shaped UDP packets. This is not an exhaustive classifier for all UDP application protocols; unknown types are authenticated AES **without claiming a lifecycle padding classification**. Ordinary TCP packets, TCP ACK-only, ordinary UDP and PN-XOR fast packets **never** invoke padding RNG and always add zero padding.

For each eligible AES boundary source packet:

1. Determine the original complete inner IPv4 byte length from the already validated packet.
2. Reserve complete outer IPv4/TCP overhead (80B reserved for IPv4 and maximum TCP options in this fixed lab), lab AES record overhead (31B) and the original inner length in the path MTU (1500B). This means the lab's maximum custom record size is 1420B.
3. Compute per-source-packet space = 1420 − 31 − original inner packet bytes. If space ≤ 0, pad **zero** and do not fragment.
4. Limit remaining pad space to **256B** to keep bandwidth, random-generation and AES costs bounded. Choose random pad size 16..min(256, available) bytes (or 1..available when remaining room <16), using crypto/rand.
5. Append random padding inside AES-authenticated encryption, *after* the original IPv4 packet, leaving its TotalLength unchanged. AES outer AAD includes framing fields and sequence number. After authenticating the whole outer record, the receiver reads the original inner IPv4 TotalLength and strips all trailing padding before delivering any original IP packet.

For this lab the physical outer packet must stay ≤1500B, and nonboundary records must always have zero pad. Test packets that themselves fill the maximum permitted record remain unpadded even if lifecycle-marked; MTU safety wins over appearance. This policy has a strict maximum of **256 padding bytes per known boundary packet**; at 1% lifecycle packets the upper bound is **2.56 extra bytes per original packet** on average, irrespective of original payload length, with all other costs excluded.

## Privacy and wire security limits

Randomized length reduces some fixed-size signatures but **does not conceal the presence of TLS or eliminate traffic-analysis features**, especially time, record count, direction, IP addresses, or original TLS ciphertext size patterns. The PN-XOR key stream is a public function of outer PN and a fixed public constant. It has **no confidentiality, integrity, authenticity or replay protection**; anyone can invert it. Only authenticated AES protects marked sensitive boundary source bytes in this controlled lab. A real receiver MUST NOT trust an unauthenticated mode byte; the test receiver consults the same out-of-band oracle.

The Go loopback fixture uses real mutual TLS1.3 **only before** a deliberate raw TCP handoff. The subsequent custom TLS-looking records are **not standard TLS1.3 application data** and Go AES framing is **not binary-compatible with production WBD Rust record framing**. Tests cannot establish all protocol-lifecycle detection, actual kernel retransmissions, production TCP reassembly, whole-program CPU, end-to-end throughput, or IPv6/TCP-option/path-MTU variability. Real production dynamic MTU budgets would need to include all IP options, links, versions, headers, and FEC reservations, fail closed if uncertain.

The isolated native checks deliberately include a real TLS1.3 ClientHello with test-only SNI/ALPN, genuine ServerHello flight, compatibility CCS if present, real encrypted client Finished, a late old-sequence ClientHello retransmission, a protected-edge packet byte-identical to an otherwise fast app record, a full-MTU lifecycle packet with no padding, pure ACK, ordinary TCP and UDP, TCP FIN/RST and labelled synthetic QUIC start/close. Each packet is checked after actual loopback TCP transfer, and an independent offline pcap parser measures elapsed wall time from outgoing client Finished to first eligible XOR record, counts padded and not-padded records independently, and checks all sizes against MTU. The raw pcap and test keys are ephemeral, while independent audit JSON and hashes are retained in GitHub Actions artifacts.

**No production merge or deployment authorization**; WBD main untouched.
