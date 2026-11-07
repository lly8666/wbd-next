# PLAN028 H1304 — authenticated Game cold group Commit proof

## Why the former test failed

Old x86_64 both ends, real [Action 42338102273](https://github.com/lly8666/wbd-next/actions/runs/42338102273), original-Go TLS 443 + Rust Game4 Fixed6: the server authenticated and joined *all four* new cold lanes, then started the actual native M4 group. Client B completed all its TLS lanes and local Rust M4, but did not receive any reverse **inner application IPv4** while old A retained the shared-TUN route, so the 5s `waitOriginalNativeM4PeerProof` expired. Generations 2 and 6 had `V4_PUBLIC_GAME_REMOTE_M4_UNPROVEN`; bounded retries hit epoch reservation/TLS timeouts. This is a real L0/L1 no-business/pure-uplink deadlock, not a reason to extend five seconds or claim local TLS READY.

## One complete source code change

The *already existing* original Rust Game authenticated Health kind0 TLV/AEAD/PN/replay path is reused as a **cold server M4 Commit receipt**; absolutely no new first-flight TLS prefix, steady per-record header, Go hot pump or FEC codec. Only the **server's fully authenticated joined group**, **after** all original M4 raw/TUN worker installation and shared TUN publication, arms **three bounded encrypted Health copies, each 400ms apart** on the existing Game TX owner. Each uses a new original PN and normal kernel TX; failed kernel copies retry but cannot grant false ready. After copies, the original randomized ~15s Health interval remains authoritative. This is a once-per-committed-group cold control receipt, not recurring probing or a new wire kind.

Client B's original native Game lane receives and validates the canonical kind0 under the correct successor AEAD/PN/replay. The existing Health `AuthenticatedActivity` retains a strict verified hint (not plain ACK, non-AEAD data or local TLS), now read once per **cold** 25ms poll through the new scoped FFI. The exact pending shared TUN route is promoted only on either **authenticated Health** or **genuine inner IPv4 TUN delivered** from B. Rust rechecks proof, group live state, generation and RouteOwner at promotion; candidate failure leaves A's published /32 and workers alive. Only exact old Stop retires old worker. Normal behavior and terminal native Health 90s remain unchanged.

Positive/negative tests cover forged ciphertext rejection, zero reverse user IPv4 with authenticated Health, cold receipt bounded/retry, local-only TLS candidate timeout and native dead/cancel. The source-locked x86 workflow also requires genuine Game4 B commit evidence, original first-flight ClientHello, native Game FEC6, switched physical path OS MTU, real UDP and exact Stop. If it fails, retain original Action FAIL and repair only the observed new stage. This is **not yet qualified** until the new Action completes.

The earlier H1302 CPU saturation analysis (true 0.6× ARM64 four-core busy92.5%) and H1300 physical egress 1260ms gap are separate, still OPEN. No ARM64 1800s run.

```feature-impact
{"kind":"modified","ids":["game-lanes"],"reason":"The existing Game2/4 cold overlap proof now uses a bounded, cryptographically authenticated native Health group-Commit receipt, preserving original wire kind0, TLS first flight, old route and Stop boundaries."}
```
