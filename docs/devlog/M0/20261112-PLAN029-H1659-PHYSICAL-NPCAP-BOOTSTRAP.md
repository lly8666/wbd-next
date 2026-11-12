# H1659 PLAN029 source-first bootstrap implementation

- Implemented bounded one-query physical Npcap IPv4 UDP DNS A lookup in the existing original-Go FakeTCP/Npcap owner package, no WinSock/system DNS, no pre-TLS private handshake or machine-wide WFP exemption, source/DNS tuple+ID+question/length/checksum validation. It is not yet wired to the product client; no claim of real Windows network PASS.
- Added only Windows unit packet/negative tests and assembly create ops with exact blobs. Next: discover OS physical NIC DNS servers, wire numeric/host CLI and each cold generation, preserve TLS certificate verification; then Windows source-build Action before any runtime claims.
