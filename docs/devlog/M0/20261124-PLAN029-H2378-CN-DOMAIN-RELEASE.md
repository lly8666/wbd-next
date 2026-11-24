# H2378 CN domains and paired final release

Implement the missing offline built-in group and GUI import/update/reset. Build-time official v2fly release tag 20261123144211 (dfa5b1c2258289bdbee70d06352cca23b9bdac7f), exact upstream checksum, select official flattened geolocation-cn protobuf entry; no runtime network unless user requests update. Preserve exact/suffix/keyword/regex, no silent downgrade, cold Go canonicalization then Rust trie and small regex-lite dependency for non-trie DNS rules; no packet or thread changes. Existing custom files override, reconnect applies. Explicit update downloads versioned upstream plus checksum, validates and atomically replaces; old file retained on failure. Both actual release jobs in parallel; Go builtin/update and actual Rust rule import, GUI selftest, ARM native short suite; package Wintun only, Npcap official install. Build/GUI/native and archives pending, not qualified yet.

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6","gui-config-feedback"],"reason":"Offline built-in China domain data, manual update/import and WinForms controls; native qualification and exact release pending."}
```
