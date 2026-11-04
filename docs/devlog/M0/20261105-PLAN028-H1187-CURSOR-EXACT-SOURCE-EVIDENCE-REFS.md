# PLAN028 H1187 — repair governance current-SOURCE cursor references

Native original Go TLS/Rust x86 Game4 FEC6 5% kernel-loss Action 41894255832 is genuinely success, with 158/2330 physical drops, 200/200 inner UDP at 20.033ms received-only RTT p99, real source4 and MTU 2x rotation, continuous independent Normal Auto320, authenticated old/new exact Stops and final TUN Stop. Source of those artifacts remains `5c89564a15f4f74567977d744547b15ce6339c96` and evidence `docs/evidence/M0/PLAN028-H1186-SOURCE5C895-NATIVE-X86-GAME4-NETEM5-REAL-200UDP-P99-PASS-20261105.json`.

First H1186 evidence collection commit `b9da4274a23feb7352822b38eabc7f67f681db54` erroneously appended a historical ARM `SOURCEbaa1` evidence path to current M0 `cursor.evidence_refs` while `cursor.last_tested_source` was x86 `SOURCE5c895`. `tools/governance.py validate_repo` correctly rejected it as `evidence is for a different SOURCE`; this also chained the feature catalog job red despite its own 38 unit tests and feature-change check passing. H1187 corrects **only current cursor references** to the one current x86 original SOURCE. Historical ARM evidence is retained unchanged in the repository; never spoof provenance or reclassify it as x86.

Signed Windows Game4 native H1185 Action41894548875 independently running, not re-dispatched. No Go/Rust/product/source change. H998 old hot MTU shrink and old ARM Game4 failure remain.

```feature-impact
{"kind":"none","ids":[],"reason":"Correct only current M0 cursor cross-SOURCE evidence reference to obey source-locked governance; retained historical ARM evidence separate."}
```
