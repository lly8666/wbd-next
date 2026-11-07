# PLAN028 H1307 — original x86 Game4 proof without rerunning network for logs

**Existing product binary SOURCE `9cc5b0efc36a390d44154bcf7ae378eb1d30e7f3`; no new Go/Rust product build.**

H1305 real x86_64 both endpoints [Action42345392910](https://github.com/lly8666/wbd-next/actions/runs/42345392910), artifact13563296508, passed native Game4 FEC6 original TLS443 cold group M4 receipt: B's actual Rust AEAD/PN validated existing server Health kind0, `native_delivered=0 authenticated_health=1`, new TUN promoted and old A retired only after B ready. Old A driver non-timeout errors dropped from earlier 614 million to 14,755 with original error-only RX pacing. Real switched UDP 5/5 also passed. CI was **FAIL** because one obsolete secondary fixture Stop reason was checked after business.

H1306 [Action42345932962](https://github.com/lly8666/wbd-next/actions/runs/42345932962), artifact13563737294, reused the exact original H1305 binaries and SHA256 manifest. The complete original Go/Rust netns scene **actually finished**: same lease, 10.25.0.2→10.25.0.3, original user outer MTU1460, physical1280/TUN OS1178, old Game4 exact Stop, both full client and server native Stop, FEC6 two cohorts, 5 switched real UDP app echoes, 8 independent source-bound genuine TCP TLS ClientHello first packets with 32-byte SessionIDs, no private prefix or server early data. Old A native RX error13,465 in latest run. CI still **FAIL** after full script success because the *workflow* grepped raw product-only `V4_PUBLIC_GAME_REMOTE_M4_PROVEN` strings in the short script stdout, although success path intentionally emits only sanitary aggregate markers. Not a protocol or business failure.

H1307 reuses both uploaded original artifacts, not merely copied marker text: the offline verifier checks SAME `source_sha`, pinned original-Go donor, Go/Rust toolchain, actual SHA256 of client/server/engine x86 ELF binaries, new B AEAD Health and absence of reverse inner IPv4, all final Stop/UDP and **all 8 real first-flight TLS fields**. A successful H1307 is recorded as *x86 Game4 L0/L1 bounded SCOPED_PASS from two exact-SOURCE original Actions*. It DOES NOT change either original CI conclusion or close the unrelated ARM64 Erin 30% weak-net, Windows all physical, historical H998, ICMP3/4, Android, or L3 long-test gaps.

```feature-impact
{"kind":"none","ids":[],"reason":"Source-locked offline original artifact verification only; no changed product code, no UI/config/wire/protocol behavior, no new traffic."}
```
