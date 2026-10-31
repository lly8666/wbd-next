# PLAN027 H561 — bounded feature catalog with source-scoped evidence

Earlier H560 Governance role check passed but Feature catalog failed because changing cards without a feature-impact block in the same changed devlog. This batch edits two source-scoped limitations (each card is below real UTF-8 16KiB bound), preserves all historic source-specific FAIL/evidence references, and declares exactly those two features. No product source/config/binary changes, no Action re-dispatch. H559/H560 failures remain historic. SOURCE525 original signed native 0% [41166008870](https://github.com/lly8666/wbd-next/actions/runs/41166008870) in progress at last check, full A/B/C incomplete.

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair","windows-native-transport"],"reason":"Shorten latest source-scoped H555 limitations for real UTF-8 file bound and explicitly declare both changed feature cards, without changing source, historical verification or qualification status."}
```
