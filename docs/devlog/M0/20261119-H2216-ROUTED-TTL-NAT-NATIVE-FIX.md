# H2216 — routed TTL Native RX mismatch after double NAT (2026-11-19)

## Physical evidence (user-supplied header-only capture; raw captures NOT committed)
- Original Windows11 FakeTCP sender TTL=128, received on Linux at TTL=116; Linux original Rust Legacy sender TTL=64, received at Windows at TTL=52. Both directions traverse ~12 routed hops.
- Under the same TCP443 association, original Go TLS+credentials succeeded; server native reported authenticated and Windows TXCopied>0 but RXDelivered=0; client timed out first+reverse; server Health90 followed.
- Rust platform `rx_ipv4_tcp::parse_data_packet` and `parse_ack_packet` compared the received IPv4 TTL to exact origin persona initial TTL. This rejects every ordinarily routed packet even when IP/TCP checksums are valid.
- Pinned original `wobuzhidao/internal/faketcp/packet.go` parser did not impose exact TTL equality. This is a Rust-port regression. No evidence requires disabling certificate verification or changing route keys.

## Minimal functional correction
Accept `observed_ttl != 0 && observed_ttl <= persona.ttl()` in both DATA and presentation ACK parser. Keep tuple, IPv4/TCP checksums, packet bounds, AEAD/PN replay, session epoch and owner unchanged. A router may decrease TTL; it must not be used as a cryptographic identity check.

## Test qualification
`h2216_public_nat_ttl_tests` regenerates checksums and tests 128→116 Windows and 64→52 Legacy both DATA/ACK plus zero/above-origin invalid and IP checksum corruption. `tools/h2216-routed-double-nat-native.sh` runs original Go + real Rust kernel/iptables namespaces with one server behind TCP443 DNAT and three independent client SNAT gateways, real multi-mode UDP app echo and owned Stop. CI artifacts use same source SHA, Windows amd64 GUI/Wintun allowlisted ZIP and Linux native ARM64 server/client tar. CI status must be checked; native physical Windows↔ARM64 WAN and DPI NOT_RUN.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H2216 fix platform routed IPv4 TTL acceptance on Rust native DATA/ACK after double NAT without changing AEAD; real Linux kernel NAT regression and source-matched field-trial artifacts"}
```
