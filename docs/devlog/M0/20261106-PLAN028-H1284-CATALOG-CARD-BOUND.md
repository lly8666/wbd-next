# PLAN028 H1284 — enforce feature card 16KiB byte bound

After the source-pinned admission-v4 manifest reconciliation, feature catalog CI reported `feature card must be bounded regular JSON`. GitHub file metadata showed the Chinese UTF-8 `game-lanes.json` was 16,395 bytes, exceeding the fixed 16,384-byte limit; JavaScript string length had undercounted multibyte bytes. Compact only the final H1284 limitation to keep the same H1283 truth: 17 local Game4 hot successes versus 15 server commits, old server Stop delayed 10–20 seconds, no dual Rust hot slot claim, new qualification pending. Do not increase checker threshold.

```feature-impact
{"kind":"updated","ids":["game-lanes"],"reason":"Enforce existing UTF-8 byte-level bounded Game feature catalog without changing H1284 experimental behavior or native qualification."}
```
