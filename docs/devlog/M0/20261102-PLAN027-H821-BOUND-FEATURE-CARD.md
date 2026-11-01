# PLAN027 H821 | Restore bounded feature card without changing source verification

- H820 main `45c06aaa0b68db30319b79fc61df6043a90c7bcf` Action `41343702249` governance/feature catalog failed. Exact feature report: `feature card must be bounded regular JSON`. The H820 writer pretty-printed an original single-line verification card, making its file 16,928 characters / over the 16 KiB file limit, not a semantic feature validation failure.
- Keep all original and H820 new verification entries and limitations **byte-content semantic unchanged**; compact the same JSON object to one line, UTF-8 size **15879 bytes** (under 16,384). No product/defaults, code path, scenario or binary changed. New governance push must pass before marking H820 closure healthy.
- H820 R original Normal source f5e8 paired OFF→ON Action `41342800664` PASS scoped; N original Normal 30% OFF Action `41343186000` PASS scoped. H820 proof remains exact-source in `docs/evidence/M0/PLAN027-H820-FROZEN-F5-R-ONOFF-AND-N-OFF30-20261102.json`.
- Game2FEC6 30% outer-OFF Action `41343702310` on SOURCE f5e8 binary is in flight; no verdict fabricated. A5 old Go experiment remains waived by user.

```feature-impact
{"kind":"verification","ids":["outer-opportunistic-repair"],"reason":"Correct only bounded JSON serialization after strict feature card size CI failure; preserve actual scoped verification records unchanged."}
```
