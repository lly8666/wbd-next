# H2401 Game NAT-independent cold attempt

H2400 first direct main patch fixed Windows cold RTO, retries, fresh tuple group and diagnostic logging. Its initial NAT fallback is replaced with deterministic server-local correlation: the existing epoch store captures the original authenticated fresh lane1 incarnation at reservation before the protected reply, and siblings with the same logical epoch inherit it. The shared listener stages only matching cold attempt markers. Old incomplete attempts retire independently; live M4 owner remains unchanged. No TCP tuple adjacency or source-IP equality, no new wire fields or RTT. Matching explicit-epoch Game siblings may reserve while first lane awaits its final ACK; native activation still requires all genuine committed owners. Historical H2400 cheap red was a source string oracle that required the obsolete tuple key; updated tests cover actual reservation, new marker, sibling-before-final-ACK and stale-attempt separation. Native/physical acceptance pending.

```feature-impact
{"kind":"updated","ids":["game-lanes","windows-native-transport"],"reason":"NAT-independent authenticated cold attempt correlation and Windows cold TLS repair; old incomplete group separated without tuple heuristic."}
```
