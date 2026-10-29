# M0 PLAN026 Linux Fixed real kernel stage attribution, without code-path changes

Run `40829858879` (exact source H354 21e9bd4) verified 9/9 genuine original TLS source+repair, TUN UDP, authenticated M2 feedback and PTO candidate counts. Every single case has workers=false, feature7, true original bound raw_tx/sender and one genuine candidate after 31ms. Both mixed/multimsg have exactly two genuine candidates, no releases and global clock advances normally across 9 scopes. Thus previous failures are **after PTO selection**, not in Go TLS/RS16, timestamp expiry or candidate generation. Single rc=3; mixed/multimsg rc=1.

Instrument only developer feature m0_fec2_owner_probe with bounded numeric native raw generation/stopping and exact first failing quota-grant/frozen-reserve or kernel-send outcome. No credential, packet, Go callback, M2 fabricated ACK or release-code change. Fix Fixed real kernel Action script to print failed real-kernel.log directly on nonzero exit, while retaining archived artifact and strict status; avoids repeated archive download, preserves test assertions.

```feature-impact
{"kind":"none","ids":[],"reason":"Test-only exact-owner Linux Fixed frozen candidate post-PTO diagnostics and fail-visible CI logs, no application or production transport change."}
```
