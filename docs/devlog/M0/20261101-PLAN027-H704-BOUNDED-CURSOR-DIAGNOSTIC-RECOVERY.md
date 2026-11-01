# PLAN027 H704 — bounded cursor metadata recovery, not a product test

Recovered H703 main Governance/Feature catalog Actions41271563450 and41271563388 failed **structure-only**: current M0 cursor was 8,870 UTF8 bytes, exceeding the pre-existing `max_cursor_bytes=8192`. The runner role and identity both passed. H703 signed-source controller Action41271563397 succeeded and one actual `1Mbps/0% Game2 fixed6` source653744 prebuilt original Action41271574007 was already dispatched and is in-flight. Do not start a duplicate, or treat governance failure as a GameFEC product failure. This commit compresses only historical repeated text in `.governance/workstreams/M0/cursor.json` while keeping all existing eight exact source6ece evidence refs, in-flight run IDs, original SOURCE manifests, user-requested first due INVALID and separated Stop focus. Earlier H685–H703 devlogs and exact real PASS/FAIL evidence remain unmodified, no erasure or source promotion. All A/B/C and GameFEC final obligations remain PARTIAL.

```feature-impact
{"kind":"none","ids":[],"reason":"Existing bounded cursor governance-only correction after measured 8870B>8192B, leave actual products, feature records, native Action, SOURCE, scene, and all prior failure evidence unchanged."}
```
