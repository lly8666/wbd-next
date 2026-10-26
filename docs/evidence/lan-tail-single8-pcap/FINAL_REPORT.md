# Real TCP loopback packet capture and TLS 1.3 control: original single header + 2B marker + rolling last8B XOR

Status: **SUCCESS, complete 201449-byte REAL tcpdump PCAP**. This is actual Linux loopback TCP socket I/O on a GitHub x86_64 Ubuntu CI runner, NOT a real physical two-host LAN capture or WBD production Rust owner. Branch experiment/lan-tail-single8-pcap-audit, main unchanged.

## Reproducibility and artifacts

Actual run: https://github.com/lly8666/wbd-next/actions/runs/40268297939 ; native job 121395392701, conclusion SUCCESS.
Real raw tcpdump/TShark artifact: https://github.com/lly8666/wbd-next/actions/runs/40268297939/artifacts/12627636543 . Archive includes actual_tcp_loopback.pcap (201449 bytes), go_actual_socket_test.txt, independent_pcap_analysis.json, tshark_custom_tls_fields.tsv, tshark_real_tls13_fields.tsv, tcpdump counters, go, capture environment and tcp conversation metadata.

Test producer: tools/lan_tail_single_header_capture_test.go, **calls exact previous proposal's session.seal and session.open** from tools/lan_tail_single_header_8bytes_test.go, using real TCP sockets bound to 127.0.0.1 ports 38443 custom, 38444 control. Entire Go test passes both real socket transfer + restored original TLS AEAD payload. The independent stdlib-only classic-PCAP reader tools/lan_tail_single8_pcap_analyze.py reassembles actual TCP segment payload from PCAP (not copied model data). Wireshark CLI TShark was invoked on each captured TCP flow with forced TLS decode. Actual Go crypto/tls negotiates genuine TLS 1.3 on second flow including ClientHello and later application_data, without logging secrets.

An earlier failed capture run 40268125996 had source/receiver tests PASS but was deliberately NOT accepted because tcpdump was stopped before its kernel packet buffer finished draining. Retried with 5 seconds drain; latest SUCCESS, 266 captured frames, 0 kernel dropped packets, no missing TCP sequence bytes. Only this complete capture is relied upon.

## Actual observed wire metrics

| Measurement | Custom single-header, last8B rolling XOR | Genuine Go TLS1.3 reference |
|---|---:|---:|
| Full reconstructed incoming TCP stream | 135120 bytes | 42589 bytes |
| TCP payload-bearing IPv4 packets (client to server) | 100 | 34 |
| Successfully reconstructed record count | 100 | 35 |
| Outer content-type application_data (23) | 100 | 33 |
| Handshake type22 visible in captured client to server stream | 0 | 1 |
| ChangeCipherSpec type20 visible | 0 | 1 |
| Outer record legacy version 0303 | 100/100 | 34/35; initial ClientHello used 0301 |
| Full correctly delimited TLS-like records | 100/100 | 35/35 |
| First bytes of each 100 custom records | 17 03 03 | normal TLS flight varies |
| Spurious second 17 03 03 at custom byte offset5 | 0/100 | not applicable |
| Independently recovered 2B mode marker | 100/100 | not applicable |
| Lost bytes in captured sender-to-receiver TCP stream | zero | zero |

Capture size (actual raw PCAP): 201449 bytes. Actual tcpdump diagnostics: 266 packets captured; 532 received by kernel filter; zero packets dropped by kernel. On Linux loopback, received by filter can count both directions/observations; do not claim 532 distinct application records.

Explicit custom distribution observed from real TCP headers + reconstructed records:
- 80 FAST records: 1347 bytes of TCP application payload each, TLS header length field 1342; captured IPv4 packet length 1399 with observed 20B IPv4 header and 32B TCP header (TCP timestamp options present).
- 20 AES-fallback records: 1368 bytes TCP application payload each, TLS header length field 1363; captured IPv4 packet length 1420 with 20B IPv4 header and 32B TCP header.
- Total custom payload bytes: 80 * 1347 + 20 * 1368 = 135120. Original input 100 * 1345 = 134500, net extra 620B or **+0.461% original payload bytes** (mean +6.2B/record). For 99% fast mix the cost would be +2.21B/record (from prior test, NOT the ratio of this actual 80/20 capture).
- Both observed IPv4 sizes 1399 and 1420 are under typical Ethernet MTU1500 **for this fixture**, but loopback MTU is not Ethernet's 1500 and this run does not prove no fragmentation on a physical LAN with different MSS/headers.
- True TLS1.3 control reference streamed 30 * 1345-byte application writes, and after actual handshake 29 observed 1367B TCP payload packets carrying 1362B encrypted record length. Multiple other genuine handshake/alert records account for 35 total TLS records in outgoing stream. One initial ClientHello is content-type22.

Independent parser assertions:
- 100/100 custom record types exactly 23 with 0303 legacy version and correct per-record length, no duplicate head at record+5.
- 80/20 category allocations exactly matching trusted test oracle after reversing the public 64bit rolling-tail XOR, using the synchronized implicit record counter; no secret key or decryption needed for the 2B marker.
- The original inner TLS record used in fast branch had real synthetic AES-GCM encrypted bytes; roundtrip receiver removes trailer, reverses XOR, corrects +2 length and authenticates/decrypts original TLS body successfully. On the wire, however, the modified length and last 6 AES tag bytes make the record invalid for a standard TLS1.3 decrypter unless custom processing first restores it. The AES-fallback WBD-record AEAD is a separate key and NOT a true TLS session's AEAD.

## TLS-like rating, not an evasion guarantee

1. **External syntax HIGH:** all 100 custom records were correctly framed as outer 17 03 03 application_data records; Wireshark/TShark recognized record type 23 and lengths. The prior erroneous double TLS head is GONE (0/100 at byte offset5).
2. **Genuine full connection LOW in this fixture:** from the SYN onward, custom socket starts directly with application_data type23 without a ClientHello, ServerHello, handshake key schedule or validated TLS1.3 session. The real TLS1.3 control did have its handshake. This benchmark intentionally exercises the steady-state only; a real WBD product may have an upstream separately authenticated handshake, but this capture does not demonstrate it.
3. **TLS cryptographic semantics NOT EQUIVALENT:** original fast TLS header length is altered +2 and six trailing ciphertext/AEAD tag bytes are XORed. A plain TLS 1.3 implementation cannot consume the transmitted record directly; custom unwrapping is mandatory. RFC8446 Section 5.2 and RFC9846 TLSCiphertext require genuine negotiated AEAD with the protected record header used as associated data.
4. **Passive discriminators:** synthetic constant-length input produces two strong exact sizes 1347/1368 (gap 21B), correlated with mode. Two-byte selectors are all reversible after **public**, deterministic final-8B XOR, without needing AES keys. Fast path has no outer cryptographic authentication (real inner TLS may authenticate application data after unwrapping), and the implicit per-record counter requires perfect synchronization.
5. **Can't infer whole-network indistinguishability from one pcap:** synthetic ciphertext fixture, local static key, unrepresentative control input, loopback packetization, no user TLS flow trace, no true two-host LAN. This is a concrete on-wire framing check, not a rigorous fingerprint classifier or DPI acceptance test.

## LAN suitability and efficiency

- For a controlled test-only single TCP stream with exactly aligned full TLS records and 80% true already-protected inner TLS content, this capture confirms the record framing and 2B tail transformation work, with very small byte overhead and 0 capture drops.
- Measured prior native Go minimal seal+open CPU for 99% fast, single-header, last8B word XOR: 7712.4 ns/100 original packets x86, 9907.8 ns/100 ARM; for 80% fast: 23135.4 ns/100 x86, 25745.8 ns/100 ARM; allAES 87967 ns/100 x86, 91861.6 ns/100 ARM. These are **memory in-process wall benchmarks, not network RTT/real LAN throughput**. Main TCP/network syscalls, TCP reassembly and classification may dominate.
- WBD real TUN receives full IPv4 packets (typically byte0=45), NOT bare 17 TLS records. To achieve 99% fast, need correct IP/TCP inspection, TCP byte-stream TLS record reassembly, accurate TLS Finished/admission and retransmission classification and PMTU. Without this, naive check first byte23 of a TUN packet routes essentially all such packets to AES, losing fast benefits.
- Outer complete TLS record plus two-byte marker changes original TLS length and AEAD tag; using pre-existing TLS requires exact inverse transformation at receiver. If path changes or packets reorder, independently implicit record counters must be reconciled. Replay/tamper protection on fast branch is absent at WBD layer.
- Local LAN has fewer middlebox/policy constraints than the public Internet but is not automatically a trusted threat-free network (untrusted hosts, Wi-Fi, switch abuse); if confidentiality/authenticity are requirements, prefer real mutually authenticated TLS or AEAD on every record. Do NOT claim standard TLS1.3 indistinguishability/security from appearance of the outer five bytes.

**Disposition: successful verified on-wire loopback capture and correctness, but not product LAN qualification, no WBD Rust wire merge.**


## Passive automatic Wireshark/TShark recognition, WITHOUT decode-as

Second successful independent workflow: https://github.com/lly8666/wbd-next/actions/runs/40268945000, archived result artifact 12626843821. This workflow downloads the exact original 201449-byte PCAP from run 40268297939, verifies exact file length and archives sha256, then runs TShark both (a) no TLS decode hints and (b) explicitly forced TLS decode on the custom/true TLS13 ports.

**Passive TShark auto identification from actual raw PCAP:**

| TCP flow | Auto protocol column | Auto recognized TLS record header/length | Forced TLS protocol column |
|---|---|---:|---|
| Custom singleheader last8 rolling, 100 client-to-server data-bearing packets | TLSv1.2 on ALL 100 | ALL 100 content-type23 and all 100 body lengths | TLSv1.2 on ALL 100 |
| Actual Go TLS 1.3 control (34 TCP packets with client-to-server data) | TLSv1 for 1 initial ClientHello packet, TLSv1.3 on 33 other TCP packets | 34 record lengths; only two plaintext record content types surfaced, because remaining records were encrypted | Same result |

This is **automatic recognition as TLS at the RECORD SYNTAX level**, not confirmation of a valid TLS handshake/session or TLS1.2 encryption. The 0x0303 legacy record version is normal for TLS 1.3 encrypted records too; absent an observed negotiated handshake, TShark cannot distinguish a TLS 1.3 steady-state stream simply from the record's 5-byte header. The custom fixture's TCP connection begins directly with content-type23 without the negotiated TLS handshake present in the genuine control flow. A different production connection with a real prior handshake could be labeled differently; this experiment does not measure that.

The auto/forced files, all 100 and 34 per-packet TShark protocol labels and summary are in the separate native artifact 12626843821. No application crypto secret was used to parse the custom marker: the rolling final 8B XOR and 2B marker are both publicly reversible/counter-derived. Neither passive recognition nor forced dissection proves cryptographic indistinguishability.

**Final interpreted result:** Outer TLS framing similarity is HIGH, and prior doubled-header bug is definitively absent. Genuine authenticated negotiated TLS 1.3 connection similarity is LOW for the isolated steady-state-only fixture, and an independent wire format cannot claim standards-equivalent TLS. Actual passive tool did label the custom stream as TLSv1.2 (not TLSv1.3), which is an important measurable distinction.
