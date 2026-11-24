# H2402 cold final ACK and live group separation

H2401 server-local attempt identity also distinguishes a full fresh Game4 sibling whose completion arrives before lane1 from the old live group's single-slot hot rekey. Windows repeats the original cumulative TLS final ACK twice immediately at Detach (no extra RTT) and replies only to already-consumed bootstrap retransmissions while the Go reader still owns capture; no steady Go sender. Ignore late pure cold FIN/RST at handoff as Normal already does; never fabricate native data. Existing TLS/AEAD, driver ownership and Stop remain. New-source CI and physical qualification pending.

```feature-impact
{"kind":"updated","ids":["game-lanes","windows-native-transport"],"reason":"Game cold final ACK recovery and exact cold attempt versus live hot rekey separation."}
```
