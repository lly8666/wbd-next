# PLAN027 H522 — correct audited H516 evidence source identity, no governance relaxation

H521 `ab437c3` committed one correct [H516 real no-loss artifact](../evidence/M0/PLAN027-H521-H516-TRUE-ORIGINAL-SACK-NOLOSS-20261030.json), but failed governance structural evidence checking: `evidence is for a different SOURCE`. Root cause our evidence used the key `original_source_sha` rather than mandatory `source_sha`, and cursor still declared historical `last_tested_source=1644...` instead of actual H516 `6f5cd093...`. The immutable H516 artifact/runner remains valid, and feature catalog structure/declaration actually passed ([Action41061396485](https://github.com/lly8666/wbd-next/actions/runs/41061396485)); failure was source metadata. H522 records `source_sha=6f5...` and exact `last_tested_source=6f5...`. Neither tests nor strict cursor/evidence invariant are changed; the separately pinned forthcoming H520 `7a5...` product remains NOT_YET_VALIDATED until real Action41060763175 finishes.

H516 genuine 0% app first100% both, Win F86,398,163B R0 C226,447B Stop PASS and exact zip hash retained. H521 one-event H520 fail-closed four-damage dispatcher remains armed against exact Action41060763175 and source7a only, not against H516 old source.

```feature-impact
{"kind":"none","ids":[],"reason":"Fix exact source provenance of already independently verified evidence and cursor; no product code or feature promotion."}
```
