# PLAN027 H680 — observed feature-catalog size audit corrected, 2 native runs unchanged/in flight

H678 commit36e60b [Feature catalog Action41237882436](https://github.com/lly8666/wbd-next/actions/runs/41237882436) FAIL: `feature card must be bounded regular JSON`; latest `docs/features/entries/normal-off.json` 18,494 UTF8 bytes exceeds existing **16KiB** cap after real 10Mbps source6ece result. H679 inherited this failure Action41238039170; separate Governance jobs and H678/H679 native dispatch succeeded. This H680 change **only** reformats card and condenses redundant historical limitation prose; preserves all 20 verification records in exact content/order, all 24 limitation entries, old SOURCE/run/FAIL including f031 loss ratio, H669 initial182 missing, and H677 source6ece 10M result. Full original prose is still available at prior commit/H678 and linked evidence files; no old failures erased, no new performance qualification.

Real [H678 5-minute source-locked Windows/WSL2 Action41237900545](https://github.com/lly8666/wbd-next/actions/runs/41237900545) and separate [H679 current source6ece signed Windows Game2 fixed6 Action41238055914](https://github.com/lly8666/wbd-next/actions/runs/41238055914) are in flight; preserve exact source/build, never redispatch while running. No product/runtime/harness/MTU/source/binary/test modification. PLAN027 task remains PARTIAL.

```feature-impact
{"kind":"updated","ids":["normal-off"],"reason":"Retain identical existing 20 verification objects and all 24 limitation entries but compact repetitive historical prose and JSON layout to satisfy existing 16KiB feature-card bound after genuine H677 10Mbps evidence; no product or test behavior change."}
```
