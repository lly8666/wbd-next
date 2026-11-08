# PLAN028 H1425 | bounded multi-client feature card

Catalog length gate on H1424 failed due 43 historic verification summaries exceeding 16KiB, not product or tested SOURCE. Kept all platform/status/source_sha/evidence tuples exactly unchanged, shortened only one-line descriptions; original evidence remains intact. No protocol, code, runtime, network or test change.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"Keep all historical verification provenance while compacting summaries to existing 16KiB feature card limit."}
```
