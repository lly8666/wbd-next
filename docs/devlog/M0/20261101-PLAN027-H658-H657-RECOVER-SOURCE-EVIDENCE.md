# PLAN027 H658 — correct SOURCE-qualified current cursor without deleting historical proofs

H657 [main governance Action41223648429](https://github.com/lly8666/wbd-next/actions/runs/41223648429) and maintenance Action41223648327 failed because the cursor was updated to new native SOURCE `dc191cf5686ddff2e433312b8ec2258954bd018f` while current `evidence_refs` continued pointing to six historical old SOURCE11f evidence files. `tools/governance.py` line336 enforces `evidence.source_sha == cursor.last_tested_source`; H657 current-source evidence also used `current_source_sha` instead of `source_sha`. This is a **real metadata/qualification failure**, not permission to weaken the validator or mark old results new.

Set H657 `source_sha` to the actual H656 native Go+Rust binary SOURCE dc191, restrict current `evidence_refs` to H657 current source only and preserve historical originals (unchanged) here:
- `docs/evidence/M0/PLAN027-H643-SOURCE11F-GAME2-AND-CANCEL-20261031.json`
- `docs/evidence/M0/PLAN027-H646-SOURCE11F-A4-C-COLLECTED-20261031.json`
- `docs/evidence/M0/PLAN027-H648-SOURCE11F-C-REAL-THREE-AND-B-GATE-20261031.json`
- `docs/evidence/M0/PLAN027-H650-SOURCE11F-FIXED-C-AND-LINUX-ISOLATE-20261101.json`
- `docs/evidence/M0/PLAN027-H652-SOURCE11F-LINUX-GAMEFEC-AND-FIXED200-20261101.json`
- `docs/evidence/M0/PLAN027-H655-SOURCE11F-FIXED200-CAPACITY-LIMIT-20261101.json`
These old reports remain on main and cited in H657/H655 and cursor text; their SOURCE11f positives, C Fixed200 capacity-limit negative, and Windows FEC canceled runs are not rewritten. H657 new-source Game2/off authentic kernel native PASS and three pending source-reused Actions preserved. No Go/Rust/driver/MTU/Stop/test changes and no new dispatch; governance rerun is push-triggered.

```feature-impact
{"kind":"none","ids":[],"reason":"Repair current-source M0 cursor/evidence provenance only; all older immutable artifacts remain source-locked on main."}
```
