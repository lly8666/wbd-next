# PLAN027 H618 — repair factual evidence schema and SOURCE cursor, no rewritten outcomes

After H617, main governance [41194570836](https://github.com/lly8666/wbd-next/actions/runs/41194570836) and maintenance [41194570902](https://github.com/lly8666/wbd-next/actions/runs/41194570902) FAIL on existing H615 JSON missing `schema_version=1` (and H616 similarly), not on actual native product Actions. Existing `tools/governance.py` unconditionally validates `schema_version==1`, then requires every cursor `evidence_ref.source_sha == last_tested_source`. H615/H616 source-frozen **actual product binary** is `80ee526cc7b466ec6ccbe3cc25caf2f3754996ef`, while H586/H591 old refs are historical SOURCEcb475. Minimal repair: add existing schema fields and accurate `source_sha` to H615/H616; set cursor tested source to SOURCE80ee, cite only those two same-source files. Preserve old H586/H591 historical evidence on disk and in prior devlogs, never delete the original FAIL or incorrectly upgrade to PASS. Cursor remains partial/unverified. No new governance framework or product edit. H617 independent real blackhole test already in flight, no duplicate.

```feature-impact
{"kind":"none","ids":[],"reason":"Correct existing evidence schema/source pointers and keep historical different-SOURCE evidence intact."}
```
