# PLAN027 H584 — one PN sample, not two

Recovered original product SOURCE `502c2480b15569d28fe923862e9eb1ba2e5ef8a4`: zero Action41175027533 and real 1/5/15/30% Actions41175749992/41175751556/41175753126/41175754386, each original Windows signed NPF/Wintun Go TLS+Rust ↔ Linux raw/TUN, UDP/TCP and owned Stop SUCCESS, all frozen binaries. Exact original 1% F/R/C Win86422351/180902/190164 and Linux85007253/186692/NOT_MEASURED; R/F Win0.2093%, Linux0.2196%. Unique candidates Win219/Linux410, BurstPaced0 both. Original stronger loss R/F Win2.6316/8.1853/8.0440%, Linux2.3583/7.7020/7.0201%. No host-matched CPU improvement claim.

Root: BOTH owners already select approximately half of original DATA by deterministic lane/generation-bound PN at the definite first-send snapshot (one original immutable ciphertext cache, <=1.5s), then incorrectly apply an independent `cosmetic_half_gap` 50% filter to the authenticated ACK/SACK index's genuinely missing record PNs. This discards sparse opportunities twice while no token shortage exists. Remove only the second independent ACK filter on Windows/Linux and obsolete helper; retain first-send 50% sample, forward 32 mature-gap cursor, 50ms reorder guard, real ACK validation, original bytes, once-only PN, bounded FIFO, byte/8MTU budget, actual driver result and Stop. No new protocol, timer, scan or ratio estimator.

NEW SOURCE is NOT_RUN until a single fresh frozen build+zero/Stop passes, then independent reused 1/5/15/30% original Actions; no claim that 1% user target R/F0.4–0.55% was achieved. Game2/4 FEC native short-run old SOURCEd5e PASS; Windows Game Health 15s/90s and rotation B, GoA A5 original failure and C network representatives still OPEN. 200M Normal/off same-family capacity FAIL unchanged.

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Both owners remove a second independent deterministic half filter after authenticated true ACK-gap qualification. Original first-send half sampled frozen cache and all integrity/byte/Stop limits unchanged; new SOURCE test outstanding."}
```
